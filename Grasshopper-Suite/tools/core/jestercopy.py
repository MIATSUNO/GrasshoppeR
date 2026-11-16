#!/usr/bin/env python3
"""
jester.py — núcleo da Jester
=============================
Clonador de sites. Faz BFS restrito ao domínio-alvo para páginas HTML e
baixa SEMPRE todo arquivo referenciado (script, css, json, txt, imagem,
vídeo, áudio, fonte, documento, arquivo), esteja ele no domínio-alvo ou
em um host de terceiros (CDN, serviço de imagens/vídeos etc.).

Uso típico (chamado pelo jester.sh):
    python3 core/jester.py exemplo.com --out jester_output

AVISO: use apenas em domínios seus ou com autorização explícita do
responsável. Respeite direitos autorais e termos de uso do site.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.robotparser
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from url_utils import (
    Kind,
    normalize_candidates,
    get_host,
    strip_www,
    same_site,
    safe_urljoin,
    classify_link,
    extension_of,
)
from api_detector import ApiDetector

USER_AGENT = "Jester-Cloner/1.0 (+uso-autorizado-apenas; fins de backup/offline)"
CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", re.I)
JS_PATHLIKE_RE = re.compile(
    r"""['"]((?:\.{0,2}/)[^'"]{2,200}\.(?:js|mjs|css|json|png|jpe?g|gif|webp|svg|"""
    r"""mp4|webm|mp3|wav|woff2?|ttf|otf|pdf|txt))['"]""",
    re.I,
)

STOP = threading.Event()


def _sigint_handler(signum, frame):
    print("\n[Jester] Ctrl+C recebido — finalizando tarefas em andamento e salvando o que já foi baixado...")
    STOP.set()


signal.signal(signal.SIGINT, _sigint_handler)


def find_node_extractor() -> tuple[str, str] | None:
    """Localiza node + tools/extract_links.js, se disponíveis. Opcional:
    se faltar qualquer um dos dois, o Python usa seu próprio regex e
    a Jester não perde funcionalidade essencial."""
    node_bin = shutil.which("node")
    if not node_bin:
        return None
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.normpath(os.path.join(here, "..", "tools", "extract_links.js"))
    if not os.path.isfile(script):
        return None
    return node_bin, script


def find_fastfetch_binary() -> str | None:
    """Localiza o acelerador compilado em Go (tools/fastfetch), se existir.
    É puramente opcional: se não existir ou não puder ser executado, a
    Jester continua funcionando inteiramente em Python, sem erro algum."""
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(here, "..", "tools", "fastfetch"),
        os.path.join(here, "..", "tools", "fastfetch.exe"),
        shutil.which("jester-fastfetch") or "",
    ):
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.normpath(candidate)
    return None


def fetch_sitemap_pages(fastfetch_bin: str, base_url: str, timeout: int) -> list[str]:
    """Usa o acelerador em Go para ler sitemap.xml/robots.txt e devolver
    páginas que talvez não tenham nenhum link apontando para elas a
    partir do index (páginas 'órfãs'). Falha silenciosa: devolve []
    se o binário não existir, travar ou o site não tiver sitemap."""
    if not fastfetch_bin:
        return []
    try:
        proc = subprocess.run(
            [fastfetch_bin, "sitemap", base_url, "--timeout", str(timeout)],
            capture_output=True, text=True, timeout=timeout * 4,
        )
    except Exception as exc:
        print(f"[Jester] (sitemap via Go indisponível: {exc} — seguindo só com o crawler normal)")
        return []
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    return lines


def sanitize_segment(seg: str) -> str:
    seg = re.sub(r"[\x00-\x1f]", "", seg)
    seg = seg.replace("\\", "_")
    if seg in ("", ".", ".."):
        seg = "_"
    return seg[:150]


def local_path_for(url: str, out_dir: str) -> str:
    parsed = urlparse(url)
    host = strip_www(get_host(url))
    path = parsed.path or "/"

    if path.endswith("/"):
        path += "index.html"

    root, ext = os.path.splitext(path)
    if ext == "":
        # URL "limpa" sem extensão (rota tipo /sobre) -> trata como página HTML
        path = path + ".html"
        root, ext = os.path.splitext(path)

    if parsed.query:
        q = re.sub(r"[^A-Za-z0-9_\-]+", "_", parsed.query)[:80]
        path = f"{root}__{q}{ext}"

    segments = [sanitize_segment(s) for s in path.split("/") if s not in ("", ".", "..")]
    rel = os.path.join(host, *segments) if segments else os.path.join(host, "index.html")
    full = os.path.normpath(os.path.join(out_dir, rel))

    out_dir_norm = os.path.normpath(out_dir)
    if not (full == out_dir_norm or full.startswith(out_dir_norm + os.sep)):
        # bloqueio de path traversal — salva num nome seguro genérico
        full = os.path.join(out_dir_norm, host, "_blocked_" + str(abs(hash(url))) + ".bin")
    return full


class Jester:
    def __init__(
        self,
        target_host: str,
        out_dir: str,
        max_workers: int = 8,
        max_pages: int = 0,
        max_files: int = 0,
        delay: float = 0.1,
        timeout: int = 15,
        respect_robots: bool = True,
        min_free_mb: int = 15,
        fastfetch_bin: str | None = None,
        node_extractor: tuple[str, str] | None = None,
    ):
        self.target_host = target_host
        self.out_dir = out_dir
        self.max_workers = max_workers
        self.max_pages = max_pages
        self.max_files = max_files
        self.delay = delay
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.min_free_mb = min_free_mb
        self.fastfetch_bin = fastfetch_bin
        self.node_extractor = node_extractor

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        self._pages_lock = threading.Lock()
        self._visited_pages: set[str] = set()
        self._files_lock = threading.Lock()
        self._downloaded_files: set[str] = set()
        self._external_lock = threading.Lock()
        self._external_pages: set[str] = set()
        self._fail_lock = threading.Lock()
        self._failed: list[str] = []
        self._failed_files: dict[str, str] = {}  # url -> motivo (candidatos a retry turbo)
        self._recovered: set[str] = set()

        self.api_detector = ApiDetector(target_host, on_found=self._on_api_found)

        self._robots: urllib.robotparser.RobotFileParser | None = None
        if respect_robots:
            self._load_robots()

        self.stats = {"pages": 0, "files": 0, "bytes": 0}

    # ------------------------------------------------------------------ robots.txt
    def _load_robots(self):
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"https://{self.target_host}/robots.txt"
        try:
            resp = self.session.get(robots_url, timeout=self.timeout)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                rp.parse([])
        except requests.RequestException:
            rp.parse([])
        self._robots = rp

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots or self._robots is None:
            return True
        if not same_site(get_host(url), self.target_host):
            return True  # robots.txt do alvo não vale para hosts de terceiros
        try:
            return self._robots.can_fetch(USER_AGENT, url)
        except Exception:
            return True

    # ------------------------------------------------------------------ callbacks
    def _on_api_found(self, url: str):
        print(f"  [API] {url}")

    def _log_fail(self, msg: str, retry_url: str | None = None, retry_reason: str = ""):
        with self._fail_lock:
            self._failed.append(msg)
            if retry_url:
                self._failed_files[retry_url] = retry_reason
        print(f"  [FALHA] {msg}")

    def _check_disk_space(self) -> bool:
        try:
            free = shutil.disk_usage(self.out_dir).free / (1024 * 1024)
        except OSError:
            return True
        if free < self.min_free_mb:
            print(f"[Jester] Espaço em disco insuficiente (<{self.min_free_mb}MB livres). Parando com segurança.")
            STOP.set()
            return False
        return True

    # ------------------------------------------------------------------ fila thread-safe
    def _mark_page_pending(self, url: str) -> bool:
        with self._pages_lock:
            if url in self._visited_pages:
                return False
            if self.max_pages and len(self._visited_pages) >= self.max_pages:
                return False
            self._visited_pages.add(url)
            return True

    def _mark_file_pending(self, url: str) -> bool:
        with self._files_lock:
            if url in self._downloaded_files:
                return False
            if self.max_files and len(self._downloaded_files) >= self.max_files:
                return False
            self._downloaded_files.add(url)
            return True

    # ------------------------------------------------------------------ extração de links
    def _extract_links(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "lxml")
        links: set[str] = set()

        tag_attrs = [
            ("a", "href"), ("img", "src"), ("script", "src"),
            ("link", "href"), ("source", "src"), ("video", "src"),
            ("video", "poster"), ("audio", "src"), ("iframe", "src"),
            ("embed", "src"), ("object", "data"), ("area", "href"),
            ("track", "src"),
        ]
        for tag, attr in tag_attrs:
            for el in soup.find_all(tag):
                val = el.get(attr)
                resolved = safe_urljoin(base_url, val) if val else None
                if resolved:
                    links.add(resolved)
                # srcset (img/source): "url1 1x, url2 2x"
                srcset = el.get("srcset")
                if srcset:
                    for part in srcset.split(","):
                        candidate = part.strip().split(" ")[0]
                        r2 = safe_urljoin(base_url, candidate)
                        if r2:
                            links.add(r2)

        # meta og:image / og:video / twitter:image
        for meta in soup.find_all("meta"):
            prop = (meta.get("property") or meta.get("name") or "").lower()
            if prop in ("og:image", "og:video", "og:audio", "twitter:image"):
                r = safe_urljoin(base_url, meta.get("content"))
                if r:
                    links.add(r)

        # CSS inline: <style>...url(...)...</style> e atributos style="..."
        for style_tag in soup.find_all("style"):
            for m in CSS_URL_RE.finditer(style_tag.get_text() or ""):
                r = safe_urljoin(base_url, m.group(1))
                if r:
                    links.add(r)
        for el in soup.find_all(style=True):
            for m in CSS_URL_RE.finditer(el.get("style") or ""):
                r = safe_urljoin(base_url, m.group(1))
                if r:
                    links.add(r)

        return links

    def _extract_css_links(self, css_text: str, base_url: str):
        links = set()
        for m in CSS_URL_RE.finditer(css_text or ""):
            r = safe_urljoin(base_url, m.group(1))
            if r:
                links.add(r)
        # @import "outro.css";
        for m in re.finditer(r"""@import\s+['"]([^'"]+)['"]""", css_text or "", re.I):
            r = safe_urljoin(base_url, m.group(1))
            if r:
                links.add(r)
        return links

    def _extract_js_links(self, js_text: str, base_url: str):
        links = set()
        for m in JS_PATHLIKE_RE.finditer(js_text or ""):
            r = safe_urljoin(base_url, m.group(1))
            if r:
                links.add(r)

        # reforço opcional via Node (entende import/require/import() dinâmico/
        # sourceMappingURL — coisas que o regex do Python sozinho não pega bem)
        if self.node_extractor and js_text:
            node_bin, script = self.node_extractor
            try:
                proc = subprocess.run(
                    [node_bin, script, "-"],
                    input=js_text, capture_output=True, text=True, timeout=10,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    import json as _json
                    for raw in _json.loads(proc.stdout):
                        r = safe_urljoin(base_url, raw)
                        if r:
                            links.add(r)
            except Exception:
                pass  # falha silenciosa — o regex do Python já cobriu o essencial
        return links

    # ------------------------------------------------------------------ gravação em disco
    def _save(self, url: str, content: bytes):
        path = local_path_for(url, self.out_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(content)
        self.stats["bytes"] += len(content)
        return path

    # ------------------------------------------------------------------ workers
    def _process_page(self, url: str):
        new_pages, new_files = set(), set()
        if STOP.is_set() or not self._check_disk_space():
            return new_pages, new_files
        if not self._allowed(url):
            print(f"  [robots.txt bloqueou] {url}")
            return new_pages, new_files
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            self._log_fail(f"PAGINA {url} -> {exc}")
            return new_pages, new_files

        if resp.status_code >= 400:
            self._log_fail(f"PAGINA {url} -> HTTP {resp.status_code}")
            return new_pages, new_files

        ctype = resp.headers.get("Content-Type", "")
        final_host = get_host(resp.url)
        saved_path = self._save(resp.url, resp.content)
        self.stats["pages"] += 1
        print(f"[PAGINA {self.stats['pages']}] {resp.url}  -> {saved_path}")

        looks_html = "text/html" in ctype or "xhtml" in ctype
        if not looks_html:
            # sem content-type claro: olha só os primeiros bytes (nunca o
            # corpo inteiro), para não decodificar arquivos binários grandes
            head = resp.content[:500].decode("utf-8", errors="ignore").lower().lstrip()
            looks_html = head.startswith("<!doctype") or "<html" in head
        if not looks_html:
            return new_pages, new_files

        html_text = resp.content.decode(resp.encoding or "utf-8", errors="ignore")

        try:
            discovered = self._extract_links(html_text, resp.url)
        except Exception as exc:
            self._log_fail(f"PARSE {url} -> {exc}")
            discovered = set()

        self.api_detector.scan(html_text, resp.url)

        for link in discovered:
            kind = classify_link(link, self.target_host)
            if kind == Kind.FILE:
                new_files.add(link)
            elif kind == Kind.PAGE:
                new_pages.add(link)
            else:
                with self._external_lock:
                    self._external_pages.add(link)

        time.sleep(self.delay)
        return new_pages, new_files

    def _process_file(self, url: str):
        """Retorna sempre (new_pages, new_files) — mesmo formato de _process_page,
        para que o loop em run() não precise adivinhar o tipo do resultado."""
        new_pages: set[str] = set()
        new_files: set[str] = set()
        if STOP.is_set() or not self._check_disk_space():
            return new_pages, new_files
        try:
            resp = self.session.get(url, timeout=self.timeout, stream=False)
        except requests.RequestException as exc:
            self._log_fail(f"ARQUIVO {url} -> {exc}", retry_url=url, retry_reason=str(exc))
            return new_pages, new_files

        if resp.status_code >= 400:
            # 4xx é falha definitiva (não adianta retry); só 5xx entra na
            # lista de retry turbo, pois pode ser instabilidade passageira.
            retry = url if resp.status_code >= 500 else None
            self._log_fail(f"ARQUIVO {url} -> HTTP {resp.status_code}", retry_url=retry, retry_reason=f"HTTP {resp.status_code}")
            return new_pages, new_files

        saved_path = self._save(resp.url, resp.content)
        self.stats["files"] += 1
        size_kb = len(resp.content) / 1024
        print(f"  [ARQUIVO {self.stats['files']}] {resp.url}  ({size_kb:,.1f} KB) -> {saved_path}")

        ext = extension_of(resp.url)
        text_content = None
        if ext in (".css", ".js", ".mjs", ".json", ".txt"):
            try:
                text_content = resp.content.decode("utf-8", errors="ignore")
            except Exception:
                text_content = None

        if text_content:
            self.api_detector.scan(text_content, resp.url)
            if ext == ".css":
                new_files |= self._extract_css_links(text_content, resp.url)
            elif ext in (".js", ".mjs"):
                new_files |= self._extract_js_links(text_content, resp.url)

        time.sleep(self.delay)
        return new_pages, new_files

    # ------------------------------------------------------------------ loop principal
    def run(self, start_url: str, extra_seed_pages: list[str] | None = None):
        os.makedirs(self.out_dir, exist_ok=True)
        self._mark_page_pending(start_url)

        with cf.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            pending = {executor.submit(self._process_page, start_url)}

            # páginas extras vindas do sitemap.xml (via acelerador Go) —
            # geralmente páginas "órfãs" sem link apontando para elas
            for seed in extra_seed_pages or []:
                if same_site(get_host(seed), self.target_host) and self._mark_page_pending(seed):
                    pending.add(executor.submit(self._process_page, seed))

            while pending and not STOP.is_set():
                done, pending = cf.wait(pending, return_when=cf.FIRST_COMPLETED)
                for fut in done:
                    try:
                        new_pages, new_files = fut.result()
                    except Exception as exc:
                        self._log_fail(str(exc))
                        continue

                    for p in new_pages:
                        if self._mark_page_pending(p):
                            pending.add(executor.submit(self._process_page, p))
                    for f in new_files:
                        if self._mark_file_pending(f):
                            pending.add(executor.submit(self._process_file, f))

            if STOP.is_set():
                for f in pending:
                    f.cancel()

        return self.finish()

    def turbo_retry(self):
        """Varredura final com o acelerador em Go: tenta de novo, em lote e
        com alta concorrência, os arquivos que falharam por instabilidade
        de rede. Totalmente opcional — se o binário não existir ou algo
        der errado, simplesmente não faz nada e os arquivos continuam
        listados em falhas.txt como estavam."""
        if not self.fastfetch_bin or not self._failed_files:
            return 0, 0

        targets = dict(self._failed_files)
        lines = []
        for url in targets:
            dest = local_path_for(url, self.out_dir)
            lines.append(f"{url}\t{dest}")

        print(f"\n[Jester] Retentativa turbo (Go) para {len(lines)} arquivo(s) que falharam...")
        try:
            proc = subprocess.run(
                [self.fastfetch_bin, "fetch", "--workers", str(self.max_workers * 2), "--timeout", str(self.timeout)],
                input="\n".join(lines), capture_output=True, text=True, timeout=self.timeout * len(lines) + 30,
            )
        except Exception as exc:
            print(f"[Jester] Retentativa turbo indisponível ({exc}) — mantendo falhas.txt como estava.")
            return 0, 0

        recovered, still_failed = 0, 0
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status, url = parts[0], parts[1]
            if status == "OK":
                recovered += 1
                self._failed_files.pop(url, None)
                self._recovered.add(url)
                self.stats["files"] += 1
                print(f"  [RECUPERADO] {url}")
            else:
                still_failed += 1
        return recovered, still_failed

    def finish(self):
        if self.fastfetch_bin:
            # a lista self._failed (texto) é mantida como histórico completo
            # da execução; só os contadores/arquivos recuperados são atualizados
            self.turbo_retry()

        api_path = os.path.join(self.out_dir, f"api+{self.target_host}.txt")
        n_api = self.api_detector.write_report(api_path)

        fail_path = os.path.join(self.out_dir, "falhas.txt")
        with open(fail_path, "w", encoding="utf-8") as fh:
            annotated = [
                (m + "   [RECUPERADO depois via retentativa turbo]")
                if any(u in m for u in self._recovered) else m
                for m in self._failed
            ]
            fh.write("\n".join(annotated))

        ext_path = os.path.join(self.out_dir, "paginas_externas_ignoradas.txt")
        with open(ext_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(self._external_pages)))

        failed_remaining = len(self._failed) - len(self._recovered)
        return {
            "pages": self.stats["pages"],
            "files": self.stats["files"],
            "bytes": self.stats["bytes"],
            "apis": n_api,
            "failed": failed_remaining,
            "recovered": len(self._recovered),
            "external_pages": len(self._external_pages),
            "api_report": api_path,
            "fail_report": fail_path,
            "out_dir": self.out_dir,
        }


def resolve_start(candidates: list[str], session: requests.Session, timeout: int):
    last_exc = None
    for cand in candidates:
        try:
            resp = session.get(cand, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"Não consegui acessar nenhuma variante de {candidates!r}: {last_exc}")


def main():
    parser = argparse.ArgumentParser(description="Jester — clonador de sites (uso autorizado apenas).")
    parser.add_argument("target", help="URL ou domínio alvo (ex.: exemplo.com, www.exemplo.com, https://exemplo.com)")
    parser.add_argument("--out", default="jester_output", help="Diretório de saída")
    parser.add_argument("--workers", type=int, default=8, help="Conexões simultâneas")
    parser.add_argument("--max-pages", type=int, default=0, help="Limite de páginas HTML (0 = sem limite)")
    parser.add_argument("--max-files", type=int, default=0, help="Limite de arquivos (0 = sem limite)")
    parser.add_argument("--delay", type=float, default=0.1, help="Pausa entre requisições (segundos, por worker)")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout de rede (segundos)")
    parser.add_argument("--ignore-robots", action="store_true", help="Ignora robots.txt (só use em domínio próprio)")
    parser.add_argument("--min-free-mb", type=int, default=15, help="Aborta se o espaço livre cair abaixo disso (MB)")
    parser.add_argument("--no-turbo", action="store_true", help="Desativa os aceleradores opcionais em Go e Node (sitemap, retry em lote, parsing extra de JS)")
    args = parser.parse_args()

    fastfetch_bin = None if args.no_turbo else find_fastfetch_binary()
    if fastfetch_bin:
        print(f"[Jester] Acelerador Go encontrado: {fastfetch_bin}")

    node_extractor = None if args.no_turbo else find_node_extractor()
    if node_extractor:
        print(f"[Jester] Extrator Node encontrado: {node_extractor[1]}")

    candidates = normalize_candidates(args.target)
    probe_session = requests.Session()
    probe_session.headers.update({"User-Agent": USER_AGENT})

    print(f"[Jester] Resolvendo alvo: {args.target}")
    try:
        first_resp = resolve_start(candidates, probe_session, args.timeout)
    except RuntimeError as exc:
        print(f"[Jester] ERRO: {exc}")
        sys.exit(1)

    target_host = strip_www(get_host(first_resp.url))
    print(f"[Jester] Domínio-alvo confirmado: {target_host}")
    print(f"[Jester] Página inicial: {first_resp.url}")

    jester = Jester(
        target_host=target_host,
        out_dir=args.out,
        max_workers=args.workers,
        max_pages=args.max_pages,
        max_files=args.max_files,
        delay=args.delay,
        timeout=args.timeout,
        respect_robots=not args.ignore_robots,
        min_free_mb=args.min_free_mb,
        fastfetch_bin=fastfetch_bin,
        node_extractor=node_extractor,
    )
    jester.session = probe_session  # reaproveita a sessão já conectada

    parsed_first = urlparse(first_resp.url)
    base_url = f"{parsed_first.scheme}://{parsed_first.netloc}"  # netloc preserva a porta, se houver
    sitemap_seeds = fetch_sitemap_pages(fastfetch_bin, base_url, args.timeout) if fastfetch_bin else []
    if sitemap_seeds:
        print(f"[Jester] sitemap.xml revelou {len(sitemap_seeds)} página(s) adicionais a clonar.")

    summary = jester.run(first_resp.url, extra_seed_pages=sitemap_seeds)

    print("\n" + "=" * 60)
    print("[Jester] Clonagem concluída.")
    print(f"  Páginas HTML salvas ....... {summary['pages']}")
    print(f"  Arquivos baixados ......... {summary['files']}")
    print(f"  Dados transferidos ........ {summary['bytes'] / (1024*1024):,.2f} MB")
    print(f"  Endpoints de API achados .. {summary['apis']}  -> {summary['api_report']}")
    print(f"  Páginas externas ignoradas  {summary['external_pages']}")
    if summary.get("recovered"):
        print(f"  Recuperados via turbo (Go)  {summary['recovered']}")
    print(f"  Falhas ..................... {summary['failed']}  -> {summary['fail_report']}")
    print(f"  Pasta de saída ............. {summary['out_dir']}")
    print("=" * 60)


if __name__ == "__main__":
    main()

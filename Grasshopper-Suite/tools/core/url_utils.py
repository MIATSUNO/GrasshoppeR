"""
url_utils.py — Jester
----------------------
Normalização de entrada de domínio/URL e classificação de links como
"page" (outra página HTML do MESMO domínio-alvo, deve ser seguida pelo
crawler) ou "file" (qualquer recurso — script, estilo, dado, mídia,
fonte, documento — que deve ser baixado sempre, esteja ele hospedado
no domínio-alvo ou em um host de terceiros/CDN).

Regra central pedida pelo operador:
  - Página de OUTRO domínio  -> nunca é seguida/clonada.
  - Arquivo (qualquer extensão da lista ASSET_EXTENSIONS), mesmo em
    outro domínio (ex.: CDN de imagens/vídeos) -> sempre baixado.
  - Página do MESMO domínio -> baixada e enfileirada para crawling.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse, urljoin

# --------------------------------------------------------------------------
# Extensões reconhecidas como ARQUIVO (sempre baixar, nunca seguir como página)
# --------------------------------------------------------------------------
SCRIPT_EXT = {
    ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".php", ".php3", ".php4", ".php5", ".php7", ".phtml",
    ".asp", ".aspx", ".jsp", ".cgi", ".pl", ".py", ".rb",
}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}
DATA_EXT = {
    ".json", ".xml", ".txt", ".csv", ".tsv", ".yaml", ".yml",
    ".log", ".md", ".webmanifest", ".map", ".rss", ".atom", ".ics",
}
IMAGE_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp",
    ".tiff", ".tif", ".avif", ".heic", ".heif",
}
VIDEO_EXT = {
    ".mp4", ".webm", ".mov", ".avi", ".mkv", ".flv", ".m4v",
    ".mpg", ".mpeg", ".3gp", ".wmv", ".ogv",
}
AUDIO_EXT = {
    ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".wma", ".opus", ".mid", ".midi",
}
FONT_EXT = {".ttf", ".otf", ".woff", ".woff2", ".eot"}
DOC_EXT = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods",
}
ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}

ASSET_EXTENSIONS = (
    SCRIPT_EXT | STYLE_EXT | DATA_EXT | IMAGE_EXT | VIDEO_EXT
    | AUDIO_EXT | FONT_EXT | DOC_EXT | ARCHIVE_EXT
)

# Extensões que claramente indicam "página navegável" (ou nenhuma extensão,
# o caso mais comum de URL limpa tipo /sobre, /contato, /blog/post-1)
PAGE_EXTENSIONS = {".html", ".htm", ".xhtml", ".shtml", ""}

# Content-Types que, quando a extensão não decide, confirmam que é página
PAGE_CONTENT_TYPES = ("text/html", "application/xhtml+xml")


@dataclass(frozen=True)
class Kind:
    PAGE = "page"
    FILE = "file"
    EXTERNAL_PAGE = "external_page"  # página de outro domínio -> ignorada


def normalize_candidates(raw: str) -> list[str]:
    """
    Recebe a entrada do operador em QUALQUER um destes formatos:
      - https://exemplo.com
      - http://exemplo.com/caminho
      - www.exemplo.com
      - exemplo.com
      - exemplo.com/caminho/pagina.html
    e devolve uma lista de URLs candidatas para tentar, na ordem de
    preferência (https primeiro, depois http).
    """
    raw = raw.strip()
    if not raw:
        raise ValueError("Entrada vazia: informe um domínio ou URL.")

    # Remove espaços e caracteres de controle acidentais
    raw = re.sub(r"[\s​]+", "", raw)

    if re.match(r"^https?://", raw, re.IGNORECASE):
        return [raw]

    # Sem esquema: pode vir como "www.exemplo.com", "exemplo.com" ou
    # "exemplo.com/caminho"
    return [f"https://{raw}", f"http://{raw}"]


def get_host(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    netloc = netloc.rsplit("@", 1)[-1]   # remove userinfo, se houver
    if netloc.startswith("["):           # literal IPv6, ex.: [::1]:8080
        end = netloc.find("]")
        return netloc[: end + 1] if end != -1 else netloc
    return netloc.split(":", 1)[0]       # remove porta


def strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def same_site(host_a: str, host_b: str) -> bool:
    """Considera exemplo.com e www.exemplo.com como o mesmo domínio-alvo."""
    return strip_www(host_a) == strip_www(host_b)


def safe_urljoin(base: str, link: str) -> str | None:
    """urljoin defensivo: ignora esquemas não-HTTP (mailto:, javascript:, tel:, data:)."""
    link = (link or "").strip()
    if not link or link.startswith("#"):
        return None
    lower = link.lower()
    if lower.startswith(("mailto:", "javascript:", "tel:", "data:", "about:", "blob:")):
        return None
    try:
        joined = urljoin(base, link)
    except ValueError:
        return None
    parsed = urlparse(joined)
    if parsed.scheme not in ("http", "https"):
        return None
    # remove fragmento (#âncora) — não baixamos âncoras internas da mesma página
    joined = urlunparse(parsed._replace(fragment=""))
    return joined


def extension_of(url: str) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1].lower()


def classify_link(url: str, target_host: str, content_type: str | None = None) -> str:
    """
    Decide se `url` é:
      - Kind.FILE           -> sempre baixar (script, css, json, txt, mídia, fonte, doc...)
      - Kind.PAGE            -> página HTML do domínio-alvo -> baixar e seguir
      - Kind.EXTERNAL_PAGE   -> página HTML de outro domínio -> ignorar (não seguir)
    """
    ext = extension_of(url)
    host = get_host(url)

    if ext in ASSET_EXTENSIONS:
        return Kind.FILE

    if ext in PAGE_EXTENSIONS:
        if same_site(host, target_host):
            return Kind.PAGE
        return Kind.EXTERNAL_PAGE

    # Extensão desconhecida (ex.: ".action", ".do", URLs com parâmetros
    # estranhos): tratamos como arquivo se for de outro host (mais seguro
    # para não deixar de capturar recursos de CDNs exóticos), e como
    # página se for do próprio domínio — mas se o content-type HTTP
    # disser text/html, isso tem prioridade sobre a extensão.
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in PAGE_CONTENT_TYPES:
            return Kind.PAGE if same_site(host, target_host) else Kind.EXTERNAL_PAGE
        if ct:
            return Kind.FILE

    if ext == "":
        return Kind.PAGE if same_site(host, target_host) else Kind.EXTERNAL_PAGE

    return Kind.FILE if not same_site(host, target_host) else Kind.PAGE

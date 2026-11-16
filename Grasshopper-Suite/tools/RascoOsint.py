from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import uuid
import random
import re
import sqlite3
import subprocess
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

for _stream in (sys.stdout, sys.stderr):
 try:
     _stream.reconfigure(encoding="utf-8")
 except Exception:
     pass

try:
 import requests
 from rich import box
 from rich.console import Console
 from rich.panel import Panel
 from rich.progress import (
 BarColumn,
 Progress,
 SpinnerColumn,
 TextColumn,
 TimeElapsedColumn,
 )
 from rich.prompt import Confirm, InvalidResponse, Prompt
 from rich.rule import Rule
 from rich.style import Style
 from rich.table import Table
 from rich.text import Text
except ModuleNotFoundError as exc:
 print(f"Dependência ausente: {exc.name}")
 print("Instale com: pip install requests rich")
 sys.exit(1)
APP = "RASCO"
VERSION = "1.0"
SCAN_PREFIX = "M1AT§UN0-RS"
BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "Rasco_Relatorios"
DB_FILE = BASE_DIR / "realb/Rasco.db"

MAX_USERNAME = 50
BODY_LIMIT = 300_000

console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


@dataclass
class Config:
    timeout: float = 10.0
    retries: int = 2
    delay: float = 0.25
    workers: int = 6

BANNER = r"""


⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⣀⣤⣶⣶⣶⣤⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣤⣶⣶⣶⣤⡀⠀⠀⠀
⠀⢀⣾⣿⣿⣿⣿⣿⣿⣷⡀⠀⠀⠀⠀⠀⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣷⡀⠀
⠀⣾⣿⠟⠉⠀⠀⠀⠉⠻⣿⣷⡀⠀⠀⠀⠀⢀⣾⣿⠟⠉⠀⠀⠉⠻⣿⣷
⢸⣿⠃⠀⠀⣠⣤⣤⣄⠀⠀⢻⣿⡇⠀⠀⢸⣿⡇⠀⠀⣠⣤⣤⣄⠀⠀⢸
⣿⣿⠀⠀⣾⣿⠟⠻⣿⣷⠀⠀⣿⣿⠀⠀⣿⣿⠀⠀⣾⣿⠟⠻⣿⣷⠀
⣿⣿⠀⠀⣿⣿⠀⠀⣿⣿⠀⠀⣿⣿⠀⠀⣿⣿⠀⠀⣿⣿⠀⠀⣿⣿⠀
⢸⣿⣇⠀⠻⣿⣶⣶⣿⠟⠀⣰⣿⡇⠀⠀⢸⣿⣇⠀⠻⣿⣶⣶⣿⠟
⠀⠻⣿⣷⣄⠀⠀⠀⠀⣠⣾⣿⠟⠀⠀⠀⠀⠻⣿⣷⣄⠀⠀⠀⣠⣾⠟
⠀⠀⠈⠻⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣿⣿⠟⠁
⠀⠀⠀⠀⠀⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
▒▒▒                                  ▒▒▒▒
 ▒▒▒▒▒▒▒ ▒▒▒▒▒▒ ▒▒▒▒▒ ▒▒▒▒▒▒▒   ▒▒▒▒▒▒▒  
  ▒▒  ▒▒ ▒▒  ▒▒ ▒▒    ▒▒       ▒▒  ▒ ▒▒  
  ▒▒▒▒▒  ▒▒▒▒▒▒   ▒▒▒ ▒▒       ▒▒ ▒  ▒▒  
  ▒▒  ▒▒ ▒▒  ▒▒ ▒▒▒▒▒ ▒▒▒▒▒▒▒  ▒▒▒▒▒▒▒   
  ▒▒  ▒▒     ▒▒              ▒▒▒▒        
  ▒          ▒▒  ┌┬───▼────┐             
             ▒   ││HTTPS://│             
                 ││   ▲    │             
                 │  ◄─┼─► ││             
                 │    ▲   ││             
                 └─▼─▼┼▼─▼┴┘
                 
                 ⠀⠀⠀⠀⠀[ R A S C O ]
                 
⠀⠀⠀⠀⠀⠀⠀⠀⠀> SYSTEM ON
⠀⠀⠀⠀⠀⠀⠀⠀⠀> ACCESS GRANTED
""".strip("\n")


def render_banner() -> Text:
    out = Text()
    for ch in BANNER:
        if ch == "▒":
            out.append(ch, style="bold cyan")
        elif ch in "┌┬┐│└┴┘─┼":
            out.append(ch, style="bright_white")
        elif ch in "▼▲◄►":
            out.append(ch, style="bold yellow")
        elif ch.isalnum() or ch in ":/":
            out.append(ch, style="bold green")
        else:
            out.append(ch)
    return out


# ============================================================
# CATÁLOGO DE SITES
# ============================================================

DEV = "Desenvolvimento"
SOC = "Redes sociais"
MUS = "Música"
GAM = "Jogos"
VID = "Vídeo"
ART = "Arte e design"
WRI = "Escrita e blogs"
CRE = "Criadores e links"
COM = "Comunidades"
LNG = "Idiomas"
REF = "Referência"
SEC = "Segurança"


@dataclass(frozen=True)
class Site:
    name: str
    category: str
    url: str                              # {u} = username
    probe: str | None = None              # URL alternativa (API) usada na checagem
    absent: tuple[str, ...] = ()          # textos que indicam perfil inexistente
    present: tuple[str, ...] = ()         # textos que confirmam o perfil
    absent_status: tuple[int, ...] = ()   # HTTP extra que significa "não existe"
    pattern: str | None = None            # regex do username aceito pelo site
    weak: bool = False                    # página dinâmica: detecção limitada
    quick: bool = False                   # entra na varredura rápida


SITES: list[Site] = [
    # ---- Desenvolvimento -------------------------------------------------
    Site("GitHub", DEV, "https://github.com/{u}", quick=True,
         pattern=r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"),
    Site("GitLab", DEV, "https://gitlab.com/{u}",
         probe="https://gitlab.com/api/v4/users?username={u}",
         present=('"username"',)),
    Site("Bitbucket", DEV, "https://bitbucket.org/{u}/"),
    Site("Codeberg", DEV, "https://codeberg.org/{u}"),
    Site("SourceForge", DEV, "https://sourceforge.net/u/{u}/profile"),
    Site("Dev.to", DEV, "https://dev.to/{u}"),
    Site("Hashnode", DEV, "https://hashnode.com/@{u}"),
    Site("Hacker News", DEV, "https://news.ycombinator.com/user?id={u}",
         absent=("No such user.",)),
    Site("Lobsters", DEV, "https://lobste.rs/u/{u}"),
    Site("Docker Hub", DEV, "https://hub.docker.com/u/{u}",
         probe="https://hub.docker.com/v2/users/{u}/"),
    Site("Kaggle", DEV, "https://www.kaggle.com/{u}"),
    Site("PyPI", DEV, "https://pypi.org/user/{u}/"),
    Site("npm", DEV, "https://www.npmjs.com/~{u}"),
    Site("RubyGems", DEV, "https://rubygems.org/profiles/{u}"),
    Site("Crates.io", DEV, "https://crates.io/users/{u}",
         probe="https://crates.io/api/v1/users/{u}"),
    Site("Replit", DEV, "https://replit.com/@{u}"),
    Site("CodePen", DEV, "https://codepen.io/{u}"),
    Site("LeetCode", DEV, "https://leetcode.com/{u}"),
    Site("Pastebin", DEV, "https://pastebin.com/u/{u}"),

    # ---- Segurança -------------------------------------------------------
    Site("Keybase", SEC, "https://keybase.io/{u}"),

    # ---- Redes sociais ---------------------------------------------------
    Site("Instagram", SOC, "https://www.instagram.com/{u}/",
         weak=True, quick=True),
    Site("X (Twitter)", SOC, "https://x.com/{u}", weak=True, quick=True),
    Site("TikTok", SOC, "https://www.tiktok.com/@{u}",
         weak=True, quick=True),
    Site("Facebook", SOC, "https://www.facebook.com/{u}",
         weak=True, quick=True),
    Site("LinkedIn", SOC, "https://www.linkedin.com/in/{u}", quick=True),
    Site("Reddit", SOC, "https://www.reddit.com/user/{u}/",
         probe="https://www.reddit.com/user/{u}/about.json", quick=True),
    Site("Threads", SOC, "https://www.threads.net/@{u}", weak=True),
    Site("Pinterest", SOC, "https://www.pinterest.com/{u}/", quick=True),
    Site("Snapchat", SOC, "https://www.snapchat.com/add/{u}",
         pattern=r"[A-Za-z][A-Za-z0-9._-]{2,14}"),
    Site("Telegram", SOC, "https://t.me/{u}", quick=True,
         absent=('<meta property="og:title" content="Telegram: Contact @',)),
    Site("Mastodon", SOC, "https://mastodon.social/@{u}"),
    Site("Bluesky", SOC, "https://bsky.app/profile/{u}.bsky.social",
         probe=("https://public.api.bsky.app/xrpc/"
                "app.bsky.actor.getProfile?actor={u}.bsky.social"),
         absent_status=(400,), pattern=r"[A-Za-z0-9-]{3,18}"),
    Site("Tumblr", SOC, "https://{u}.tumblr.com",
         pattern=r"[A-Za-z0-9-]{1,32}"),
    Site("VK", SOC, "https://vk.com/{u}", weak=True),
    Site("Imgur", SOC, "https://imgur.com/user/{u}"),
    Site("Disqus", COM, "https://disqus.com/by/{u}/"),
    Site("Gravatar", CRE, "https://gravatar.com/{u}"),

    # ---- Vídeo -----------------------------------------------------------
    Site("YouTube", VID, "https://www.youtube.com/@{u}", quick=True),
    Site("Twitch", VID, "https://www.twitch.tv/{u}", weak=True, quick=True),
    Site("Vimeo", VID, "https://vimeo.com/{u}"),
    Site("Dailymotion", VID, "https://www.dailymotion.com/{u}"),
    Site("Rumble", VID, "https://rumble.com/user/{u}"),

    # ---- Música ----------------------------------------------------------
    Site("SoundCloud", MUS, "https://soundcloud.com/{u}", quick=True),
    Site("Bandcamp", MUS, "https://bandcamp.com/{u}"),
    Site("Last.fm", MUS, "https://www.last.fm/user/{u}"),
    Site("Mixcloud", MUS, "https://www.mixcloud.com/{u}/"),
    Site("Audiomack", MUS, "https://audiomack.com/{u}"),
    Site("Genius", MUS, "https://genius.com/{u}"),
    Site("Spotify", MUS, "https://open.spotify.com/user/{u}", weak=True),

    # ---- Jogos -----------------------------------------------------------
    Site("Steam", GAM, "https://steamcommunity.com/id/{u}", quick=True,
         absent=("The specified profile could not be found",)),
    Site("Chess.com", GAM, "https://www.chess.com/member/{u}",
         probe="https://api.chess.com/pub/player/{u}"),
    Site("Lichess", GAM, "https://lichess.org/@/{u}"),
    Site("Minecraft", GAM, "https://namemc.com/profile/{u}",
         probe="https://api.mojang.com/users/profiles/minecraft/{u}",
         present=('"id"',), absent_status=(204,),
         pattern=r"[A-Za-z0-9_]{3,16}"),
    Site("itch.io", GAM, "https://{u}.itch.io",
         pattern=r"[A-Za-z0-9_-]{2,40}"),
    Site("Newgrounds", GAM, "https://{u}.newgrounds.com",
         pattern=r"[A-Za-z0-9_-]{2,40}"),
    Site("osu!", GAM, "https://osu.ppy.sh/users/{u}"),

    # ---- Arte e design ---------------------------------------------------
    Site("Behance", ART, "https://www.behance.net/{u}"),
    Site("Dribbble", ART, "https://dribbble.com/{u}"),
    Site("DeviantArt", ART, "https://www.deviantart.com/{u}"),
    Site("ArtStation", ART, "https://www.artstation.com/{u}"),
    Site("Flickr", ART, "https://www.flickr.com/people/{u}"),
    Site("500px", ART, "https://500px.com/p/{u}"),
    Site("Unsplash", ART, "https://unsplash.com/@{u}"),

    # ---- Escrita e blogs -------------------------------------------------
    Site("Medium", WRI, "https://medium.com/@{u}"),
    Site("Substack", WRI, "https://{u}.substack.com",
         pattern=r"[A-Za-z0-9-]{2,40}"),
    Site("WordPress", WRI, "https://{u}.wordpress.com",
         pattern=r"[A-Za-z0-9-]{3,40}"),
    Site("Blogger", WRI, "https://{u}.blogspot.com",
         pattern=r"[A-Za-z0-9-]{3,40}"),
    Site("LiveJournal", WRI, "https://{u}.livejournal.com",
         pattern=r"[A-Za-z0-9_-]{2,32}"),
    Site("Wattpad", WRI, "https://www.wattpad.com/user/{u}"),
    Site("Archive of Our Own", WRI, "https://archiveofourown.org/users/{u}"),
    Site("Goodreads", WRI, "https://www.goodreads.com/{u}"),

    # ---- Criadores e links -----------------------------------------------
    Site("Linktree", CRE, "https://linktr.ee/{u}"),
    Site("Carrd", CRE, "https://{u}.carrd.co",
         pattern=r"[A-Za-z0-9-]{2,40}"),
    Site("About.me", CRE, "https://about.me/{u}"),
    Site("Patreon", CRE, "https://www.patreon.com/{u}"),
    Site("Ko-fi", CRE, "https://ko-fi.com/{u}"),
    Site("Buy Me a Coffee", CRE, "https://www.buymeacoffee.com/{u}"),
    Site("Gumroad", CRE, "https://{u}.gumroad.com",
         pattern=r"[A-Za-z0-9-]{2,40}"),

    # ---- Comunidades e entretenimento -------------------------------------
    Site("Letterboxd", COM, "https://letterboxd.com/{u}/"),
    Site("MyAnimeList", COM, "https://myanimelist.net/profile/{u}"),

    # ---- Idiomas ---------------------------------------------------------
    Site("Duolingo", LNG, "https://www.duolingo.com/profile/{u}",
         probe="https://www.duolingo.com/2017-06-30/users?username={u}",
         present=('"username"',), absent=('"users":[]',)),

    # ---- Referência ------------------------------------------------------
    Site("Wikipedia (EN)", REF, "https://en.wikipedia.org/wiki/User:{u}",
         probe=("https://en.wikipedia.org/w/api.php?action=query"
                "&list=users&ususers={u}&format=json"),
         present=('"userid"',)),
    Site("Wikipédia (PT)", REF,
         "https://pt.wikipedia.org/wiki/Usu%C3%A1rio:{u}",
         probe=("https://pt.wikipedia.org/w/api.php?action=query"
                "&list=users&ususers={u}&format=json"),
         present=('"userid"',)),
]

CATEGORIES = sorted({s.category for s in SITES})


# ============================================================
# STATUS E APRESENTAÇÃO
# ============================================================

# status interno -> (rótulo, estilo, símbolo)
STATUS_UI = {
    "FOUND": ("ENCONTRADO", "bold green", "●"),
    "MAYBE": ("TALVEZ", "bold yellow", "◐"),
    "NOT FOUND": ("NÃO ENCONTRADO", "grey50", "○"),
    "MANUAL": ("VERIFICAR", "bold blue", "◇"),
    "RESTRICTED": ("RESTRITO", "red", "■"),
    "CAPTCHA": ("CAPTCHA", "magenta", "▲"),
    "RATE LIMITED": ("LIMITADO", "yellow", "◆"),
    "TIMEOUT": ("TEMPO ESGOTADO", "red", "◌"),
    "ERROR": ("ERRO", "bold red", "✖"),
    "SKIPPED": ("IGNORADO", "grey50", "–"),
}

COUNT_KEYS = list(STATUS_UI.keys())
ISSUE_ORDER = ["MANUAL", "RESTRICTED", "CAPTCHA", "RATE LIMITED",
               "TIMEOUT", "ERROR"]
LINK_STATUSES = {"MANUAL", "RESTRICTED", "CAPTCHA"}

TILES = [
    ("FOUND", "ACHADOS"),
    ("MAYBE", "TALVEZ"),
    ("NOT FOUND", "AUSENTES"),
    ("MANUAL", "VERIFICAR"),
    ("RESTRICTED", "RESTRITOS"),
    ("CAPTCHA", "CAPTCHA"),
    ("RATE LIMITED", "LIMITADOS"),
    ("TIMEOUT", "TEMPO"),
    ("ERROR", "ERROS"),
    ("SKIPPED", "IGNORADOS"),
]

MODE_LABEL = {
    "rapido": "Rápida",
    "completo": "Completa",
    "categoria": "Por categoria",
    "demo": "Demonstração (offline)",
}

# Mensagens de erro / detalhe (centralizadas)
MSG = {
    "rate": ("Limite de requisições atingido (HTTP 429). Aguarde alguns "
             "minutos ou reduza os workers / aumente o atraso."),
    "captcha": ("O site pediu verificação anti-bot. O Rasco não contorna "
                "CAPTCHA — abra o link manualmente."),
    "denied": ("Acesso negado (HTTP {code}): o site bloqueia consultas "
               "automáticas. Abra o link manualmente."),
    "server": "Erro no servidor do site (HTTP {code}). Tente mais tarde.",
    "unexpected": "Resposta inesperada do site (HTTP {code}).",
    "redirect": ("Redirecionamento sem destino final (HTTP {code}). "
                 "Confira manualmente."),
    "login": "O site exige login para mostrar o perfil. Confirme manualmente.",
    "weak_found": "Detecção limitada neste site; confirme manualmente.",
    "manual": ("Página dinâmica: não dá para confirmar automaticamente. "
               "Abra o link para verificar."),
    "pattern": "Username fora do formato aceito por este site.",
    "timeout": "Tempo esgotado: o site demorou demais para responder.",
    "ssl": "Falha de certificado SSL/TLS ao conectar.",
    "redirects": "Loop de redirecionamentos.",
    "dns": ("Não foi possível resolver o endereço (DNS): site fora do ar "
            "ou você está sem internet."),
    "refused": "Conexão recusada pelo servidor.",
    "reset": "Conexão interrompida pelo servidor.",
    "conn": "Falha de conexão: verifique internet, VPN ou proxy.",
    "corrupt": "Resposta corrompida ou incompleta do servidor.",
    "other": "Erro inesperado ({name}).",
}


class Ask(Prompt):
    illegal_choice_message = "[prompt.invalid.choice]Escolha uma das opções."
    validate_error_message = "[prompt.invalid]Valor inválido."


class SimNao(Confirm):
    choices = ["s", "n"]
    validate_error_message = "[prompt.invalid]Responda com 's' ou 'n'."


# ============================================================
# BANCO DE DADOS
# ============================================================

@contextmanager
def db_session():
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    with db_session() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id TEXT UNIQUE,
                username TEXT,
                mode TEXT,
                started TEXT,
                duration REAL,
                total INTEGER,
                found INTEGER,
                maybe INTEGER,
                not_found INTEGER,
                manual INTEGER,
                restricted INTEGER,
                captcha INTEGER,
                rate_limited INTEGER,
                timeout INTEGER,
                skipped INTEGER,
                errors INTEGER
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id TEXT,
                username TEXT,
                site TEXT,
                category TEXT,
                status TEXT,
                confidence INTEGER,
                http_status INTEGER,
                note TEXT,
                url TEXT,
                checked_at TEXT
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_results_scan "
            "ON results(scan_id)"
        )


def save_scan(scan_id, username, mode, duration, results):
    c = count_results(results)

    with db_session() as db:
        db.execute("""
            INSERT INTO scans (
                scan_id, username, mode, started, duration, total,
                found, maybe, not_found, manual, restricted, captcha,
                rate_limited, timeout, skipped, errors
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            scan_id, username, mode,
            datetime.now().isoformat(timespec="seconds"),
            round(duration, 2), len(results),
            c["FOUND"], c["MAYBE"], c["NOT FOUND"], c["MANUAL"],
            c["RESTRICTED"], c["CAPTCHA"], c["RATE LIMITED"],
            c["TIMEOUT"], c["SKIPPED"], c["ERROR"],
        ))

        db.executemany("""
            INSERT INTO results (
                scan_id, username, site, category, status, confidence,
                http_status, note, url, checked_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """, [
            (scan_id, r["username"], r["site"], r["category"],
             r["status"], r["confidence"], r.get("http_status"),
             r.get("note", ""), r["url"], r["checked_at"])
            for r in results
        ])


# ============================================================
# UTILITÁRIOS
# ============================================================

def make_scan_id(username):
    raw = f"{username}-{datetime.now().isoformat()}"
    digest = hashlib.sha1(raw.encode()).hexdigest()[:8].upper()
    return f"{SCAN_PREFIX}-{datetime.now():%Y%m%d}-{digest}"


def valid_username(username):
    return bool(
        username
        and 2 <= len(username) <= MAX_USERNAME
        and re.fullmatch(r"[A-Za-z0-9_.-]+", username)
    )


INVALID_USERNAME = (
    "[red]Username inválido.[/red] Use de 2 a 50 caracteres: letras, "
    "números, [bold]_[/bold], [bold].[/bold] ou [bold]-[/bold]."
)


def generate_variations(username, limit=8):
    seps = "_.-"
    values = {username, username.lower()}

    stripped = username
    for s in seps:
        values.add(username.replace(s, ""))
        stripped = stripped.replace(s, "")
    values.add(stripped)

    for s in seps:
        if s in username:
            for other in seps:
                if other != s:
                    values.add(username.replace(s, other))

    ordered = sorted(v for v in values if valid_username(v))
    if username in ordered:
        ordered.remove(username)
    return ([username] + ordered)[:limit]


def count_results(results):
    counts = {k: 0 for k in COUNT_KEYS}
    for r in results:
        key = r["status"] if r["status"] in counts else "ERROR"
        counts[key] += 1
    return counts


def fold(text):
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode().lower().strip()


def build_url(template, username):
    return template.replace("{u}", quote(username, safe=""))


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9_-]", "_", text)


def short_url(url):
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/")


def select_sites(mode, category=None):
    if mode == "rapido":
        return [s for s in SITES if s.quick]
    if mode == "categoria":
        return [s for s in SITES if s.category == category]
    return list(SITES)


def find_category(text):
    wanted = fold(text)
    for cat in CATEGORIES:
        if fold(cat) == wanted:
            return cat
    for cat in CATEGORIES:
        if wanted and wanted in fold(cat):
            return cat
    return None


# ============================================================
# ANÁLISE DE RESPOSTAS
# ============================================================

CHALLENGE_WORDS = (
    "captcha", "recaptcha", "hcaptcha", "cf-chl", "challenge-platform",
    "verify you are human", "verify you're human", "security check",
    "bot verification", "attention required", "checking your browser",
    "just a moment...",
)

STRONG_CHALLENGE = (
    "verify you are human", "verify you're human", "checking your browser",
    "attention required", "cf-chl", "just a moment...", "security check",
)

LOGIN_WORDS = (
    "sign in to continue", "log in to continue", "login required",
    "please sign in", "faça login para continuar",
    "entre para continuar",
)

LOGIN_PATHS = ("login", "signin", "sign-in", "sign_in", "signup",
               "sign-up", "register")
MISSING_PATHS = ("404", "notfound", "not-found", "not_found", "error",
                 "search")

ABSENT_TITLE = re.compile(
    r"not found|doesn.?t exist|does not exist|couldn.?t (be )?find|"
    r"could not be found|no such (user|page)|n[ãa]o (encontrad|existe)|"
    r"indispon[ií]vel|^\s*404\b|error 404|page unavailable",
    re.I,
)

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OG_RE = re.compile(
    r"<meta\b[^>]*(?:og:title|twitter:title|profile:username)[^>]*>",
    re.I,
)


def normalize(text):
    return re.sub(r"\s+", "", text.lower())


def read_body(resp, limit=BODY_LIMIT):
    chunks, size = [], 0
    for chunk in resp.iter_content(chunk_size=16384):
        chunks.append(chunk)
        size += len(chunk)
        if size >= limit:
            break
    return b"".join(chunks)[:limit].decode("utf-8", errors="replace")


def extract_title(body):
    match = TITLE_RE.search(body[:100_000])
    if not match:
        return ""
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()


def looks_like_challenge(code, headers, low):
    if headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    if code in (403, 429, 503) and any(w in low for w in CHALLENGE_WORDS):
        return True
    if code == 200 and len(low) < 20_000:
        return any(w in low for w in STRONG_CHALLENGE)
    return False


def redirect_outcome(requested_url, resp):
    """Detecta quando o site redirecionou para fora do perfil."""
    if not resp.history:
        return None

    o, f = urlparse(requested_url), urlparse(resp.url)
    oh = o.netloc.lower().removeprefix("www.")
    fh = f.netloc.lower().removeprefix("www.")
    op = o.path.rstrip("/").lower()
    fp = f.path.rstrip("/").lower()

    if (any(k in fp for k in LOGIN_PATHS)
            and not any(k in op for k in LOGIN_PATHS)):
        return "login"

    if fp == "" and (op != "" or oh != fh):
        return "away"

    if (any(k in fp for k in MISSING_PATHS)
            and not any(k in op for k in MISSING_PATHS)):
        return "away"

    return None


def retry_after(resp, default=2.0):
    try:
        return min(float(resp.headers.get("Retry-After", default)), 10.0)
    except (TypeError, ValueError):
        return default


def analyze_response(site, username, requested_url, resp):
    """Retorna (status, confiança, detalhe)."""
    code = resp.status_code

    if code == 429:
        return "RATE LIMITED", 0, MSG["rate"]

    if code in (404, 410) or code in site.absent_status:
        return "NOT FOUND", 0, ""

    body = read_body(resp)
    low = body.lower()

    if looks_like_challenge(code, resp.headers, low):
        return "CAPTCHA", 0, MSG["captcha"]

    if code in (401, 403, 999):
        return "RESTRICTED", 0, MSG["denied"].format(code=code)

    if code >= 500:
        return "ERROR", 0, MSG["server"].format(code=code)

    if 300 <= code < 400:
        return "MAYBE", 40, MSG["redirect"].format(code=code)

    if not 200 <= code < 300:
        return "ERROR", 0, MSG["unexpected"].format(code=code)

    # ---- HTTP 2xx: procurar evidências ----

    outcome = redirect_outcome(requested_url, resp)

    if outcome == "login":
        return "MAYBE", 40, MSG["login"]

    if outcome == "away":
        return "NOT FOUND", 0, ""

    flat = normalize(body)

    if any(normalize(m) in flat for m in site.absent):
        return "NOT FOUND", 0, ""

    title = extract_title(body)

    if title and ABSENT_TITLE.search(title):
        return "NOT FOUND", 0, ""

    uname = username.lower()
    title_hit = uname in title.lower()
    og_hit = any(uname in tag.lower() for tag in OG_RE.findall(body[:100_000]))
    present_hit = any(normalize(m) in flat for m in site.present)

    if site.probe and site.present and not present_hit:
        return "NOT FOUND", 0, ""

    if any(w in low for w in LOGIN_WORDS) and not title_hit:
        return "MAYBE", 40, MSG["login"]

    evidence = title_hit or og_hit or present_hit

    if site.weak:
        if not evidence:
            return "MANUAL", 0, MSG["manual"]
        return "MAYBE", 55, MSG["weak_found"]

    score = 85 if (site.probe and site.present) else 75
    score += 8 if title_hit else 0
    score += 6 if og_hit else 0
    score += 6 if present_hit else 0

    return "FOUND", min(score, 96), ""


def explain_exception(exc):
    """Traduz exceções de rede em (status, mensagem amigável)."""
    ex = requests.exceptions

    if isinstance(exc, ex.Timeout):
        return "TIMEOUT", MSG["timeout"]

    if isinstance(exc, ex.SSLError):
        return "ERROR", MSG["ssl"]

    if isinstance(exc, ex.TooManyRedirects):
        return "ERROR", MSG["redirects"]

    if isinstance(exc, ex.ConnectionError):
        text = str(exc).lower()

        dns_hints = (
            "name or service not known", "getaddrinfo failed",
            "nodename nor servname", "temporary failure in name",
            "no address associated", "name resolution",
        )

        if any(h in text for h in dns_hints):
            return "ERROR", MSG["dns"]
        if "refused" in text:
            return "ERROR", MSG["refused"]
        if "reset" in text or "aborted" in text or "closed" in text:
            return "ERROR", MSG["reset"]
        return "ERROR", MSG["conn"]

    if isinstance(exc, (ex.ChunkedEncodingError, ex.ContentDecodingError)):
        return "ERROR", MSG["corrupt"]

    return "ERROR", MSG["other"].format(name=type(exc).__name__)


# ============================================================
# CHECAGEM DE UM SITE
# ============================================================

_local = threading.local()


def get_session():
    session = getattr(_local, "session", None)

    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)
        session.max_redirects = 6

        adapter = requests.adapters.HTTPAdapter(
            pool_connections=8,
            pool_maxsize=8,
            max_retries=0,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        _local.session = session

    return session


def new_result(site, username, url):
    return {
        "site": site.name,
        "category": site.category,
        "username": username,
        "url": url,
        "status": "ERROR",
        "confidence": 0,
        "http_status": None,
        "note": "",
        "response_ms": None,
        "weak": site.weak,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def check_site(site, username, cfg):
    url = build_url(site.url, username)
    target = build_url(site.probe, username) if site.probe else url
    result = new_result(site, username, url)

    if site.pattern and not re.fullmatch(site.pattern, username):
        result.update(status="SKIPPED", note=MSG["pattern"])
        return result

    session = get_session()

    for attempt in range(cfg.retries + 1):
        if cfg.delay > 0:
            time.sleep(cfg.delay + random.uniform(0, 0.15))

        started = time.perf_counter()
        wait = 0.0
        resp = None

        try:
            resp = session.get(
                target,
                timeout=cfg.timeout,
                allow_redirects=True,
                stream=True,
            )

            result["http_status"] = resp.status_code

            status, confidence, note = analyze_response(
                site, username, target, resp
            )

            result.update(status=status, confidence=confidence, note=note)

            if status == "RATE LIMITED":
                wait = retry_after(resp)
            elif status == "ERROR" and resp.status_code >= 500:
                wait = 1.5 * (attempt + 1)
            else:
                return result

        except requests.RequestException as exc:
            status, note = explain_exception(exc)
            result.update(status=status, confidence=0, note=note)

            if status != "TIMEOUT":
                return result

            wait = 1.0

        except Exception as exc:  # defesa: nunca derrubar a varredura
            result.update(
                status="ERROR",
                confidence=0,
                note=MSG["other"].format(name=type(exc).__name__),
            )
            return result

        finally:
            result["response_ms"] = int(
                (time.perf_counter() - started) * 1000
            )
            if resp is not None:
                resp.close()

        if attempt < cfg.retries:
            time.sleep(wait)

    return result


# ============================================================
# VARREDURA
# ============================================================

def run_scan(usernames, sites, cfg):
    jobs = [(site, u) for u in usernames for site in sites]
    results = []
    interrupted = False
    started = time.time()

    workers = max(1, min(cfg.workers, len(jobs)))
    executor = ThreadPoolExecutor(max_workers=workers)

    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=None, complete_style="cyan",
                  finished_style="green"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("[green]●[/green] {task.fields[found]}"),
        TimeElapsedColumn(),
        console=console,
    )

    futures = []

    try:
        with progress:
            task = progress.add_task(
                "Varrendo perfis públicos", total=len(jobs), found=0
            )

            futures = [
                executor.submit(check_site, site, u, cfg)
                for site, u in jobs
            ]

            found = 0

            for future in as_completed(futures):
                try:
                    r = future.result()
                except Exception as exc:
                    r = {
                        "site": "?", "category": "?", "username": "?",
                        "url": "", "status": "ERROR", "confidence": 0,
                        "http_status": None,
                        "note": MSG["other"].format(name=type(exc).__name__),
                        "response_ms": None, "weak": False,
                        "checked_at": datetime.now().isoformat(
                            timespec="seconds"),
                    }

                results.append(r)

                if r["status"] == "FOUND":
                    found += 1

                progress.update(task, advance=1, found=found)

    except KeyboardInterrupt:
        interrupted = True
        for f in futures:
            f.cancel()

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    order = {u: i for i, u in enumerate(usernames)}
    results.sort(key=lambda r: (order.get(r["username"], 99),
                                r["site"].lower()))

    return results, time.time() - started, interrupted


def demo_scan(username):
    results = []

    for site in SITES:
        roll = random.random()
        status, conf, code, note = "NOT FOUND", 0, 404, ""

        if site.pattern and not re.fullmatch(site.pattern, username):
            status, code, note = "SKIPPED", None, MSG["pattern"]
        elif site.weak and roll < 0.7:
            status, code, note = "MANUAL", 200, MSG["manual"]
        elif roll < 0.20:
            status, conf, code = "FOUND", random.randint(75, 96), 200
        elif roll < 0.28:
            status, conf, code, note = (
                "MAYBE", random.randint(40, 70), 200, MSG["login"])
        elif roll < 0.32:
            status, code, note = "CAPTCHA", 403, MSG["captcha"]
        elif roll < 0.35:
            status, code, note = (
                "RESTRICTED", 403, MSG["denied"].format(code=403))
        elif roll < 0.37:
            status, code, note = "TIMEOUT", None, MSG["timeout"]
        elif roll < 0.39:
            status, code, note = "RATE LIMITED", 429, MSG["rate"]

        results.append({
            "site": site.name,
            "category": site.category,
            "username": username,
            "url": build_url(site.url, username),
            "status": status,
            "confidence": conf,
            "http_status": code,
            "note": note,
            "response_ms": random.randint(80, 900),
            "weak": site.weak,
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        })

    return results, 1.25, False


# ============================================================
# INTERFACE
# ============================================================

MENU = [
    ("1", "Varredura rápida", "redes e sites mais populares"),
    ("2", "Varredura completa", "todo o catálogo"),
    ("3", "Por categoria", "escolha um grupo de sites"),
    ("4", "Com variações", "testa variações do username"),
    ("5", "Demonstração", "offline, dados simulados"),
    ("6", "Histórico", "últimas varreduras"),
    ("7", "Comparar", "o que mudou entre duas varreduras"),
    ("8", "Catálogo", f"{len(SITES)} sites suportados"),
    ("0", "Sair", ""),
]


def show_banner(clear=True):
    if clear:
        console.clear()

    console.print(render_banner(), highlight=False)
    console.print(Rule(
        f"[bold]{APP}[/bold] [dim]v{VERSION}[/dim] · "
        "radar de username em fontes públicas",
        style="cyan",
    ))
    console.print(
        "[dim]Uso educacional / pesquisa autorizada. "
        "Sem bypass de CAPTCHA ou login.[/dim]\n"
    )


def show_menu():
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="right", style="bold cyan")
    grid.add_column(style="bold")
    grid.add_column(style="dim")

    for key, label, hint in MENU:
        grid.add_row(f"[{key}]".replace("[", "\\["), label, hint)

    console.print(Panel(
        grid,
        title="MENU",
        title_align="left",
        box=box.SQUARE,
        border_style="cyan",
        padding=(1, 2),
    ))


def conf_bar(confidence, width=10):
    filled = round(width * confidence / 100)
    style = "green" if confidence >= 80 else "yellow"

    bar = Text()
    bar.append("█" * filled, style=style)
    bar.append("░" * (width - filled), style="grey37")
    bar.append(f" {confidence:>3}%", style="bold")
    return bar


def link_text(url, max_len=48):
    label = short_url(url)
    if len(label) > max_len:
        label = label[: max_len - 1] + "…"
    return Text(label, style=Style(color="cyan", underline=True, link=url))


def status_text(status):
    label, style, icon = STATUS_UI.get(status, STATUS_UI["ERROR"])
    return Text(f"{icon} {label}", style=style)


def site_label(r):
    name = r["site"] + (" †" if r.get("weak") else "")
    return Text(name, style="bold")


def show_results(results, show_all=False):
    multi = len({r["username"] for r in results}) > 1

    hits = sorted(
        (r for r in results if r["status"] in ("FOUND", "MAYBE")),
        key=lambda r: (-r["confidence"], r["site"].lower()),
    )

    issues = sorted(
        (r for r in results if r["status"] in ISSUE_ORDER),
        key=lambda r: (ISSUE_ORDER.index(r["status"]), r["site"].lower()),
    )

    absent = [r for r in results if r["status"] == "NOT FOUND"]
    skipped = [r for r in results if r["status"] == "SKIPPED"]

    # ---- achados ----
    if hits:
        table = Table(
            title=f"PERFIS ENCONTRADOS ({len(hits)})",
            title_style="bold green",
            title_justify="left",
            box=box.HEAVY_HEAD,
            header_style="bold",
            border_style="green",
            expand=False,
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("Site")
        if multi:
            table.add_column("Username", style="magenta")
        table.add_column("Categoria", style="dim")
        table.add_column("Status")
        table.add_column("Confiança")
        table.add_column("Perfil", overflow="fold")

        for i, r in enumerate(hits, 1):
            row = [str(i), site_label(r)]
            if multi:
                row.append(r["username"])
            row += [
                r["category"],
                status_text(r["status"]),
                conf_bar(r["confidence"]),
                link_text(r["url"]),
            ]
            table.add_row(*row)

        console.print(table)
    else:
        console.print(Panel(
            "Nenhum perfil encontrado neste catálogo.",
            border_style="grey50",
            box=box.SQUARE,
        ))

    # ---- atenção / pendências ----
    if issues:
        table = Table(
            title=f"ATENÇÃO ({len(issues)})",
            title_style="bold yellow",
            title_justify="left",
            box=box.SIMPLE,
            header_style="bold",
            expand=False,
        )
        table.add_column("Site")
        table.add_column("Status")
        table.add_column("Detalhe", overflow="fold", ratio=1)
        table.add_column("Link", overflow="fold")

        for r in issues:
            link = (link_text(r["url"])
                    if r["status"] in LINK_STATUSES else "")
            prefix = f"[{r['username']}] " if multi else ""
            table.add_row(
                site_label(r),
                status_text(r["status"]),
                Text(prefix + (r.get("note") or "-"), style="dim"),
                link,
            )

        console.print(table)

    # ---- não encontrados (linha compacta) ----
    if absent and not show_all:
        names = sorted({r["site"] for r in absent}, key=str.lower)
        console.print(Text.assemble(
            (f"○ Não encontrado em {len(names)} sites: ", "grey50"),
            (", ".join(names), "grey42"),
        ))

    if skipped:
        names = sorted({r["site"] for r in skipped}, key=str.lower)
        console.print(Text.assemble(
            (f"– Ignorados ({len(names)}): ", "grey50"),
            (", ".join(names) + " — username fora do formato do site",
             "grey42"),
        ))

    if any(r.get("weak") for r in results):
        console.print(
            "[dim]† site de página dinâmica: a detecção automática é "
            "limitada.[/dim]"
        )

    # ---- tabela completa opcional ----
    if show_all:
        table = Table(
            title="TODOS OS RESULTADOS",
            title_style="bold",
            title_justify="left",
            box=box.MINIMAL,
            header_style="bold",
        )
        table.add_column("Site")
        if multi:
            table.add_column("Username", style="magenta")
        table.add_column("Categoria", style="dim")
        table.add_column("Status")
        table.add_column("HTTP", justify="right")
        table.add_column("ms", justify="right", style="dim")

        for r in results:
            row = [site_label(r)]
            if multi:
                row.append(r["username"])
            row += [
                r["category"],
                status_text(r["status"]),
                str(r.get("http_status") or "-"),
                str(r.get("response_ms") or "-"),
            ]
            table.add_row(*row)

        console.print(table)


def proportion_bar(results, width=48):
    groups = [
        ("green", {"FOUND"}),
        ("yellow", {"MAYBE"}),
        ("blue", {"MANUAL"}),
        ("grey37", {"NOT FOUND", "SKIPPED"}),
        ("red", {"RESTRICTED", "CAPTCHA", "RATE LIMITED",
                 "TIMEOUT", "ERROR"}),
    ]

    total = len(results) or 1
    bar = Text()
    used = 0

    for style, statuses in groups:
        n = sum(1 for r in results if r["status"] in statuses)
        if not n:
            continue
        size = max(1, round(width * n / total))
        size = min(size, width - used)
        bar.append("█" * size, style=style)
        used += size

    if used < width:
        bar.append("█" * (width - used), style="grey37")

    return bar


def show_summary(results, duration, scan_id, label):
    counts = count_results(results)

    tiles = [
        (key, name) for key, name in TILES
        if counts[key] or key in ("FOUND", "MAYBE", "NOT FOUND")
    ]

    grid = Table.grid(expand=True, padding=(0, 2))
    for _ in tiles:
        grid.add_column(justify="center")

    grid.add_row(*[
        Text(str(counts[key]), style=STATUS_UI[key][1])
        for key, _ in tiles
    ])
    grid.add_row(*[Text(name, style="dim") for _, name in tiles])

    body = Table.grid(expand=True)
    body.add_column(justify="center")
    body.add_row(grid)
    body.add_row("")
    body.add_row(proportion_bar(results))
    body.add_row(Text(
        f"{len(results)} verificações · {duration:.1f}s · {label}",
        style="dim",
    ))

    console.print(Panel(
        body,
        title="RESUMO",
        title_align="left",
        subtitle=scan_id,
        subtitle_align="right",
        box=box.SQUARE,
        border_style="cyan",
        padding=(1, 2),
    ))


def category_report(results):
    cats = {}

    for r in results:
        if r["status"] == "SKIPPED":
            continue

        c = cats.setdefault(r["category"],
                            {"total": 0, "found": 0, "maybe": 0})
        c["total"] += 1

        if r["status"] == "FOUND":
            c["found"] += 1
        elif r["status"] == "MAYBE":
            c["maybe"] += 1

    if not cats:
        return

    table = Table(
        title="PRESENÇA POR CATEGORIA",
        title_style="bold",
        title_justify="left",
        box=box.MINIMAL_DOUBLE_HEAD,
        header_style="bold",
    )
    table.add_column("Categoria")
    table.add_column("Sites", justify="right")
    table.add_column("Achados", justify="right", style="green")
    table.add_column("Talvez", justify="right", style="yellow")
    table.add_column("Presença")

    ranked = sorted(cats.items(),
                    key=lambda kv: (-kv[1]["found"], -kv[1]["maybe"], kv[0]))

    for name, c in ranked:
        ratio = (c["found"] + c["maybe"]) / c["total"]
        filled = round(ratio * 12)
        bar = Text()
        bar.append("▰" * filled, style="cyan")
        bar.append("▱" * (12 - filled), style="grey37")
        bar.append(f" {ratio:>4.0%}", style="dim")

        table.add_row(name, str(c["total"]), str(c["found"]),
                      str(c["maybe"]), bar)

    console.print(table)


def show_hints(results):
    counts = count_results(results)
    total = len(results)

    if not total:
        return

    network = counts["TIMEOUT"] + counts["ERROR"]
    blocked = (counts["RATE LIMITED"] + counts["CAPTCHA"]
               + counts["RESTRICTED"])

    if network / total >= 0.8:
        console.print(Panel(
            "Quase todas as consultas falharam.\n"
            "• Verifique sua conexão com a internet\n"
            "• Desative VPN / proxy ou libere o Python no firewall\n"
            "• Tente um timeout maior:  [bold]-t 20[/bold]",
            title="DICA",
            border_style="yellow",
            box=box.SQUARE,
        ))
    elif blocked / total >= 0.3:
        console.print(Panel(
            "Muitos sites limitaram ou bloquearam as consultas.\n"
            "• Reduza a velocidade:  [bold]-w 3 -d 0.8[/bold]\n"
            "• Espere alguns minutos antes de repetir a varredura",
            title="DICA",
            border_style="yellow",
            box=box.SQUARE,
        ))


def show_catalog():
    table = Table(
        title=f"CATÁLOGO ({len(SITES)} sites)",
        title_style="bold",
        title_justify="left",
        box=box.HEAVY_HEAD,
        header_style="bold",
    )
    table.add_column("Site", style="bold")
    table.add_column("Categoria", style="dim")
    table.add_column("Rápida", justify="center")
    table.add_column("Detecção")

    for s in sorted(SITES, key=lambda s: (s.category, s.name.lower())):
        if s.weak:
            mode = Text("limitada †", style="yellow")
        elif s.probe:
            mode = Text("via API", style="cyan")
        else:
            mode = Text("padrão", style="green")

        table.add_row(s.name, s.category,
                      "●" if s.quick else "", mode)

    console.print(table)
    console.print(
        "[dim]† página dinâmica: pode retornar 'VERIFICAR' em vez de "
        "um resultado definitivo.[/dim]"
    )


# ============================================================
# RELATÓRIOS
# ============================================================

def csv_safe(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def export_json(path, results, username, scan_id, duration, label):
    data = {
        "application": APP,
        "version": VERSION,
        "scan_id": scan_id,
        "username": username,
        "mode": label,
        "duration_seconds": round(duration, 2),
        "generated": datetime.now().isoformat(timespec="seconds"),
        "summary": count_results(results),
        "notice": (
            "Resultados são pistas de fontes públicas e exigem "
            "verificação manual."
        ),
        "results": [
            {k: v for k, v in r.items() if k != "weak"} for r in results
        ],
    }

    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )


def export_csv(path, results):
    fields = [
        "site", "category", "username", "status", "confidence",
        "http_status", "note", "url", "response_ms", "checked_at",
    ]

    # utf-8-sig: o Excel abre acentos corretamente
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for r in results:
            writer.writerow({f: csv_safe(r.get(f)) for f in fields})


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rasco — __USER__</title>
<style>
:root{--bg:#0e1117;--card:#161b24;--line:#262d3a;--txt:#e6e9ef;
--dim:#8b94a7;--cyan:#4dd0e1;--green:#4caf50;--yellow:#f5c542;
--red:#ef5350;--blue:#64b5f6;--mag:#ce93d8}
*{box-sizing:border-box}
body{margin:0;padding:28px;background:var(--bg);color:var(--txt);
font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif}
h1{margin:0 0 4px;color:var(--cyan);letter-spacing:.15em}
.sub{color:var(--dim);margin-bottom:22px}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px}
.card{background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:10px 16px;min-width:96px}
.card b{display:block;font-size:22px}
.card span{color:var(--dim);font-size:11px;letter-spacing:.08em}
.tools{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}
input,select{background:var(--card);color:var(--txt);
border:1px solid var(--line);border-radius:6px;padding:8px 10px}
table{width:100%;border-collapse:collapse;background:var(--card);
border-radius:8px;overflow:hidden}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);
text-align:left;vertical-align:top}
th{background:#1d2431;font-size:12px;letter-spacing:.06em;color:var(--dim)}
tr:hover td{background:#1a202b}
a{color:var(--cyan)}
.b{padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600;
border:1px solid currentColor;white-space:nowrap}
.s-FOUND{color:var(--green)}.s-MAYBE{color:var(--yellow)}
.s-NOT_FOUND,.s-SKIPPED{color:var(--dim)}.s-MANUAL{color:var(--blue)}
.s-CAPTCHA{color:var(--mag)}.s-RATE_LIMITED{color:var(--yellow)}
.s-RESTRICTED,.s-TIMEOUT,.s-ERROR{color:var(--red)}
.bar{display:inline-block;width:80px;height:7px;background:#2a3140;
border-radius:4px;vertical-align:middle;margin-right:6px}
.bar i{display:block;height:100%;background:var(--green);border-radius:4px}
.dim{color:var(--dim)}
.note{margin-top:18px;color:var(--dim);font-size:12px}
</style>
</head>
<body>
<h1>RASCO</h1>
<div class="sub">Scan <b>__SCANID__</b> · username <b>__USER__</b> ·
__LABEL__ · __DURATION__s · __DATE__</div>

<div class="cards">__CARDS__</div>

<div class="tools">
<input id="q" placeholder="Filtrar por site, categoria ou detalhe…">
<select id="st"><option value="">Todos os status</option>__OPTIONS__</select>
</div>

<table id="t">
<thead><tr><th>Site</th><th>Categoria</th><th>Username</th><th>Status</th>
<th>Confiança</th><th>HTTP</th><th>Detalhe</th><th>Perfil</th></tr></thead>
<tbody>
__ROWS__
</tbody>
</table>

<p class="note"><b>Aviso:</b> um username igual em sites diferentes não prova
que os perfis pertencem à mesma pessoa. Resultados são pistas e exigem
verificação manual. † = site de detecção limitada.</p>

<script>
const q=document.getElementById('q'),st=document.getElementById('st');
function f(){const t=q.value.toLowerCase(),s=st.value;
document.querySelectorAll('#t tbody tr').forEach(r=>{
const ok=(!t||r.textContent.toLowerCase().includes(t))&&(!s||r.dataset.s===s);
r.style.display=ok?'':'none';});}
q.oninput=f;st.onchange=f;
</script>
</body>
</html>
"""


def export_html(path, results, username, scan_id, duration, label):
    esc = html.escape
    counts = count_results(results)

    ordered = sorted(
        results,
        key=lambda r: (
            0 if r["status"] == "FOUND" else
            1 if r["status"] == "MAYBE" else 2,
            -r["confidence"],
            r["site"].lower(),
        ),
    )

    rows = []

    for r in ordered:
        label_text, _, icon = STATUS_UI.get(r["status"], STATUS_UI["ERROR"])
        cls = r["status"].replace(" ", "_")
        conf = int(r["confidence"] or 0)
        name = esc(r["site"]) + (" †" if r.get("weak") else "")

        bar = (
            f'<span class="bar"><i style="width:{conf}%"></i></span>{conf}%'
            if conf else '<span class="dim">-</span>'
        )

        link = (
            f'<a href="{esc(r["url"], quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">abrir</a>'
            if r["url"] else ""
        )

        rows.append(
            f'<tr data-s="{esc(r["status"])}">'
            f"<td><b>{name}</b></td>"
            f'<td class="dim">{esc(r["category"])}</td>'
            f"<td>{esc(r['username'])}</td>"
            f'<td><span class="b s-{cls}">{icon} {esc(label_text)}</span></td>'
            f"<td>{bar}</td>"
            f"<td>{esc(str(r.get('http_status') or '-'))}</td>"
            f'<td class="dim">{esc(r.get("note") or "")}</td>'
            f"<td>{link}</td>"
            f"</tr>"
        )

    cards = "".join(
        f'<div class="card"><b>{counts[key]}</b><span>{name}</span></div>'
        for key, name in TILES
        if counts[key] or key in ("FOUND", "MAYBE", "NOT FOUND")
    )

    options = "".join(
        f'<option value="{esc(k)}">{esc(STATUS_UI[k][0])}</option>'
        for k in COUNT_KEYS if counts[k]
    )

    page = (
        HTML_TEMPLATE
        .replace("__USER__", esc(username))
        .replace("__SCANID__", esc(scan_id))
        .replace("__LABEL__", esc(label))
        .replace("__DURATION__", f"{duration:.1f}")
        .replace("__DATE__", datetime.now().strftime("%d/%m/%Y %H:%M"))
        .replace("__CARDS__", cards)
        .replace("__OPTIONS__", options)
        .replace("__ROWS__", "\n".join(rows))
    )

    path.write_text(page, encoding="utf-8")


def export_reports(kinds, results, username, scan_id, duration, label):
    """Grava os relatórios pedidos. Retorna lista de (tipo, caminho)."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Atenção: with_suffix() quebraria nomes com ponto (ex.: "fulano.dev").
    stem = f"{safe_name(username)}_{datetime.now():%Y%m%d_%H%M%S}"
    written = []

    if "json" in kinds:
        p = REPORT_DIR / f"{stem}.json"
        export_json(p, results, username, scan_id, duration, label)
        written.append(("JSON", p))

    if "csv" in kinds:
        p = REPORT_DIR / f"{stem}.csv"
        export_csv(p, results)
        written.append(("CSV", p))

    if "html" in kinds:
        p = REPORT_DIR / f"{stem}.html"
        export_html(p, results, username, scan_id, duration, label)
        written.append(("HTML", p))

    return written


# ============================================================
# HISTÓRICO E COMPARAÇÃO
# ============================================================

def show_history():
    with db_session() as db:
        rows = db.execute("""
            SELECT scan_id, username, mode, started, total, found, maybe
            FROM scans ORDER BY id DESC LIMIT 15
        """).fetchall()

    if not rows:
        console.print("[yellow]Nenhuma varredura no histórico ainda.[/yellow]")
        return

    table = Table(
        title="HISTÓRICO (últimas 15)",
        title_style="bold",
        title_justify="left",
        box=box.HEAVY_HEAD,
        header_style="bold",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Scan")
    table.add_column("Username", style="magenta")
    table.add_column("Modo", style="dim")
    table.add_column("Data")
    table.add_column("Sites", justify="right")
    table.add_column("Achados", justify="right", style="green")
    table.add_column("Talvez", justify="right", style="yellow")

    for i, (sid, user, mode, started, total, found, maybe) in enumerate(
            rows, 1):
        table.add_row(
            str(i), sid, user, mode or "-",
            (started or "").replace("T", " "),
            str(total), str(found), str(maybe),
        )

    console.print(table)


def compare_scans():
    with db_session() as db:
        scans = db.execute("""
            SELECT scan_id, username, mode, started, found, maybe
            FROM scans ORDER BY id DESC LIMIT 20
        """).fetchall()

        if len(scans) < 2:
            console.print(
                "[yellow]São necessárias pelo menos duas varreduras "
                "no histórico.[/yellow]"
            )
            return

        table = Table(
            title="ESCOLHA DUAS VARREDURAS",
            title_style="bold",
            title_justify="left",
            box=box.SIMPLE_HEAD,
            header_style="bold",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("Scan")
        table.add_column("Username", style="magenta")
        table.add_column("Modo", style="dim")
        table.add_column("Data")
        table.add_column("Achados", justify="right", style="green")
        table.add_column("Talvez", justify="right", style="yellow")

        for i, (sid, user, mode, started, found, maybe) in enumerate(
                scans, 1):
            table.add_row(str(i), sid, user, mode or "-",
                          (started or "").replace("T", " "),
                          str(found), str(maybe))

        console.print(table)

        valid = [str(i) for i in range(1, len(scans) + 1)]

        # padrão: mais recente (B) vs. anterior do mesmo username (A)
        default_a = "2"
        for i, s in enumerate(scans[1:], 2):
            if s[1] == scans[0][1]:
                default_a = str(i)
                break

        pick_a = int(Ask.ask("Varredura [bold]A[/bold] (antiga)",
                             choices=valid, default=default_a,
                             console=console))
        pick_b = int(Ask.ask("Varredura [bold]B[/bold] (nova)",
                             choices=valid, default="1", console=console))

        if pick_a == pick_b:
            console.print("[yellow]Escolha duas varreduras diferentes."
                          "[/yellow]")
            return

        scan_a, scan_b = scans[pick_a - 1], scans[pick_b - 1]

        def load(scan_id):
            rows = db.execute(
                "SELECT username, site, status FROM results "
                "WHERE scan_id = ?", (scan_id,)).fetchall()
            return {(u, s): st for u, s, st in rows}

        data_a, data_b = load(scan_a[0]), load(scan_b[0])

    if scan_a[1] != scan_b[1]:
        console.print(
            f"[yellow]Aviso: usernames diferentes "
            f"({scan_a[1]} × {scan_b[1]}).[/yellow]"
        )

    positive = {"FOUND", "MAYBE"}
    changes, same = [], 0

    for key in sorted(set(data_a) | set(data_b),
                      key=lambda k: (k[1].lower(), k[0])):
        a, b = data_a.get(key, "—"), data_b.get(key, "—")
        pa, pb = a in positive, b in positive

        if pb and not pa:
            change = ("NOVO", "bold green")
        elif pa and not pb:
            change = ("SUMIU", "bold red")
        elif pa and pb and a != b:
            change = ("MUDOU", "bold yellow")
        else:
            same += 1
            continue

        changes.append((key, a, b, change))

    if not changes:
        console.print(Panel(
            f"Nenhuma diferença de presença entre as varreduras "
            f"({same} sites iguais).",
            border_style="grey50", box=box.SQUARE,
        ))
        return

    table = Table(
        title=f"{scan_a[0]}  →  {scan_b[0]}",
        title_style="bold",
        title_justify="left",
        box=box.HEAVY_HEAD,
        header_style="bold",
    )
    table.add_column("Mudança")
    table.add_column("Site", style="bold")
    table.add_column("Username", style="magenta")
    table.add_column("A")
    table.add_column("B")

    def label(status):
        if status in STATUS_UI:
            return Text(STATUS_UI[status][0], style=STATUS_UI[status][1])
        return Text(status, style="dim")

    for (user, site), a, b, (txt, style) in changes:
        table.add_row(Text(txt, style=style), site, user,
                      label(a), label(b))

    console.print(table)
    console.print(f"[dim]{same} sites sem mudança de presença.[/dim]")


# ============================================================
# FLUXOS
# ============================================================

EXPORT_MENU = {
    "1": ("json",),
    "2": ("csv",),
    "3": ("html",),
    "4": ("json", "csv", "html"),
    "0": (),
}

EXPORT_CLI = {
    "json": ("json",),
    "csv": ("csv",),
    "html": ("html",),
    "todos": ("json", "csv", "html"),
    "nenhum": (),
}


def ask_username(label="Username"):
    while True:
        value = Ask.ask(
            f"[cyan]{label}[/cyan] [dim](vazio = voltar)[/dim]",
            default="", show_default=False, console=console,
        ).strip().lstrip("@")

        if not value:
            return None

        if valid_username(value):
            return value

        console.print(INVALID_USERNAME)


def choose_category():
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", style="bold cyan")
    table.add_column()
    table.add_column(style="dim")

    for i, cat in enumerate(CATEGORIES, 1):
        n = sum(1 for s in SITES if s.category == cat)
        table.add_row(str(i), cat, f"{n} sites")

    console.print(Panel(table, title="CATEGORIAS", title_align="left",
                        box=box.SQUARE, border_style="cyan"))

    pick = Ask.ask(
        "Categoria",
        choices=[str(i) for i in range(1, len(CATEGORIES) + 1)],
        console=console,
    )

    return CATEGORIES[int(pick) - 1]


def run_flow(mode, username, cfg, *, category=None, variations=False,
             show_all=False, export=None):
    """
    export=None  -> pergunta ao usuário (modo interativo)
    export=tupla -> exporta direto (modo linha de comando)
    """
    usernames = (generate_variations(username)
                 if variations and mode != "demo" else [username])
    sites = select_sites(mode, category)

    if not sites:
        console.print("[red]Nenhum site selecionado.[/red]")
        return

    label = MODE_LABEL[mode]
    if mode == "categoria":
        label += f": {category}"
    if variations and mode != "demo":
        label += " + variações"

    scan_id = make_scan_id(username)

    info = Table.grid(padding=(0, 2))
    info.add_column(style="dim")
    info.add_column(style="bold")
    info.add_row("Alvo", ", ".join(usernames))
    info.add_row("Modo", label)
    info.add_row("Verificações", str(len(sites) * len(usernames)))
    info.add_row("Scan ID", scan_id)

    console.print(Panel(info, title="VARREDURA", title_align="left",
                        box=box.SQUARE, border_style="cyan"))

    if mode == "demo":
        results, duration, interrupted = demo_scan(username)
    else:
        results, duration, interrupted = run_scan(usernames, sites, cfg)

    if interrupted:
        console.print(
            "\n[yellow]Varredura interrompida — exibindo resultados "
            "parciais.[/yellow]"
        )

    if not results:
        console.print("[yellow]Nenhum resultado foi coletado.[/yellow]")
        return

    console.print()
    show_results(results, show_all)
    console.print()
    show_summary(results, duration, scan_id, label)
    console.print()
    category_report(results)
    show_hints(results)

    try:
        save_scan(scan_id, username, label, duration, results)
    except sqlite3.Error as exc:
        console.print(
            f"[yellow]Aviso: não foi possível salvar no histórico "
            f"({exc}).[/yellow]"
        )

    # ---- relatórios ----
    if export is None:
        console.print("\n[bold cyan]RELATÓRIOS[/bold cyan]")
        console.print(
            "[1] JSON   [2] CSV   [3] HTML   [4] Todos   [0] Pular"
            .replace("[", "\\[")
        )
        choice = Ask.ask("Exportar", choices=list(EXPORT_MENU),
                         default="4", console=console)
        kinds = EXPORT_MENU[choice]
    else:
        kinds = export

    if kinds:
        try:
            for kind, path in export_reports(
                    kinds, results, username, scan_id, duration, label):
                console.print(f"[green]{kind}:[/green] {path}")
        except OSError as exc:
            console.print(
                f"[red]Não foi possível gravar o relatório em "
                f"{REPORT_DIR}:[/red] {exc.strerror or exc}\n"
                "[dim]Verifique permissões da pasta e espaço em disco."
                "[/dim]"
            )

    console.print("\n[bold green]✓ Varredura concluída.[/bold green]")
    console.print(
        "[dim]ENCONTRADO/TALVEZ são pistas que exigem verificação manual. "
        "CAPTCHA e login nunca são contornados.[/dim]"
    )


def handle_choice(choice, cfg):
    if choice in ("1", "2", "5"):
        username = ask_username()
        if username:
            mode = {"1": "rapido", "2": "completo", "5": "demo"}[choice]
            run_flow(mode, username, cfg)

    elif choice == "3":
        username = ask_username()
        if username:
            category = choose_category()
            run_flow("categoria", username, cfg, category=category)

    elif choice == "4":
        username = ask_username()
        if not username:
            return

        variations = generate_variations(username)
        total = len(variations) * len(SITES)

        console.print("\n[cyan]Variações:[/cyan] " + ", ".join(variations))

        if SimNao.ask(
                f"Serão {total} verificações. Continuar?",
                default=True, console=console):
            run_flow("completo", username, cfg, variations=True)

    elif choice == "6":
        show_history()

    elif choice == "7":
        compare_scans()

    elif choice == "8":
        show_catalog()


def interactive(cfg):
    choices = [key for key, _, _ in MENU]

    while True:
        show_banner()
        show_menu()

        choice = Ask.ask("[bold cyan]Opção[/bold cyan]",
                         choices=choices, default="2", console=console)

        if choice == "0":
            console.print("[dim]Até logo.[/dim]")
            return

        console.print()

        try:
            handle_choice(choice, cfg)

        except KeyboardInterrupt:
            console.print("\n[yellow]Operação cancelada.[/yellow]")

        except sqlite3.Error as exc:
            console.print(
                f"[red]Erro no banco de dados:[/red] {exc}\n"
                f"[dim]Arquivo: {DB_FILE}[/dim]"
            )

        except OSError as exc:
            console.print(f"[red]Erro de arquivo/sistema:[/red] "
                          f"{exc.strerror or exc}")

        console.print()
        console.input("[dim]ENTER para voltar ao menu…[/dim]")


# ============================================================
# LINHA DE COMANDO
# ============================================================

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="rasco",
        description=f"{APP} v{VERSION} — radar de username em fontes públicas",
        add_help=False,
    )

    p.add_argument("username", nargs="?",
                   help="username a procurar (sem argumento: menu)")
    p.add_argument("-m", "--modo", choices=["rapido", "completo", "demo"],
                   default="completo", help="padrão: completo")
    p.add_argument("-c", "--categoria",
                   help="varre só uma categoria (ex.: musica, jogos)")
    p.add_argument("-v", "--variacoes", action="store_true",
                   help="testa também variações do username")
    p.add_argument("-e", "--exportar", default="todos",
                   choices=list(EXPORT_CLI), help="padrão: todos")
    p.add_argument("-w", "--workers", type=int, default=6,
                   help="requisições simultâneas (1-20)")
    p.add_argument("-t", "--timeout", type=float, default=10.0,
                   help="timeout por requisição, em segundos (2-60)")
    p.add_argument("-r", "--tentativas", type=int, default=2,
                   help="novas tentativas em falhas temporárias (0-5)")
    p.add_argument("-d", "--atraso", type=float, default=0.25,
                   help="pausa antes de cada requisição, em segundos")
    p.add_argument("--tudo", action="store_true",
                   help="mostra a tabela completa, inclusive não encontrados")
    p.add_argument("--sites", action="store_true",
                   help="lista o catálogo e sai")
    p.add_argument("-h", "--ajuda", "--help", action="help",
                   help="mostra esta ajuda")

    return p.parse_args(argv)


def clamp(value, low, high):
    return max(low, min(high, value))


def main(argv=None):
    args = parse_args(argv)

    cfg = Config(
        timeout=clamp(args.timeout, 2, 60),
        retries=clamp(args.tentativas, 0, 5),
        delay=clamp(args.atraso, 0, 5),
        workers=clamp(args.workers, 1, 20),
    )

    try:
        init_database()
    except (sqlite3.Error, OSError) as exc:
        console.print(
            f"[yellow]Aviso: histórico indisponível ({exc}). "
            "A varredura continua sem salvar.[/yellow]"
        )

    if args.sites:
        show_catalog()
        return 0

    if not args.username:
        interactive(cfg)
        return 0

    username = args.username.lstrip("@")

    if not valid_username(username):
        console.print(INVALID_USERNAME)
        return 2

    mode, category = args.modo, None

    if args.categoria:
        category = find_category(args.categoria)

        if not category:
            console.print(
                f"[red]Categoria '{args.categoria}' não encontrada.[/red]\n"
                "[dim]Disponíveis: " + ", ".join(CATEGORIES) + "[/dim]"
            )
            return 2

        mode = "categoria"

    show_banner(clear=False)

    run_flow(
        mode, username, cfg,
        category=category,
        variations=args.variacoes,
        show_all=args.tudo,
        export=EXPORT_CLI[args.exportar],
    )

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())

    except KeyboardInterrupt:
        console.print("\n[yellow]Programa encerrado.[/yellow]")
        sys.exit(130)

    except Exception as exc:
        console.print(f"\n[red]Erro inesperado:[/red] {exc}")
        console.print(
            "[dim]Se persistir, rode novamente com outro username ou "
            "apague o arquivo Rasco.db.[/dim]"
        )
        sys.exit(1)


# py -3.13 -m pip install requests rich

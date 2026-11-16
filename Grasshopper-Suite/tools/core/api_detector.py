"""
api_detector.py — Jester
-------------------------
Varre HTML e JavaScript baixados em busca de referências a endpoints de
API (fetch, axios, jQuery.ajax, XMLHttpRequest, caminhos /api/, /v1/,
/graphql etc.) e consolida tudo em um único arquivo:

    api+<dominioalvo>.txt

e também imprime cada endpoint novo encontrado na tela, em tempo real.
"""

from __future__ import annotations

import re
import threading
from urllib.parse import urlparse

from url_utils import safe_urljoin, get_host, same_site

_API_PATTERNS = [
    re.compile(r"""fetch\(\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""axios(?:\.default)?\.(?:get|post|put|delete|patch|head)\(\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""\$\.(?:get|post|ajax|getJSON)\(\s*\{?\s*(?:url\s*:\s*)?['"]([^'"]+)['"]""", re.I),
    re.compile(r"""\.open\(\s*['"]\w+['"]\s*,\s*['"]([^'"]+)['"]""", re.I),
    re.compile(r"""['"]((?:https?:)?//[^'"]*?/(?:api|graphql|rest)[^'"]*)['"]""", re.I),
    re.compile(r"""['"](/(?:api|graphql|rest)(?:/[^'"]*)?)['"]""", re.I),
    re.compile(r"""['"]([^'"]*?/v\d+(?:\.\d+)?/[^'"]*)['"]""", re.I),
    re.compile(r"""data-api(?:-url)?=['"]([^'"]+)['"]""", re.I),
]

# Caminhos que, mesmo sem bater em nenhum padrão acima, quase sempre são API
_API_HINT_SEGMENTS = ("/api/", "/graphql", "/rest/", "/v1/", "/v2/", "/v3/", "/wp-json/")


class ApiDetector:
    def __init__(self, target_host: str, on_found=None):
        self.target_host = target_host
        self.on_found = on_found  # callback(url) para log em tempo real
        self._found: set[str] = set()
        self._lock = threading.Lock()

    def scan(self, text: str, base_url: str) -> list[str]:
        if not text:
            return []
        new_ones: list[str] = []
        candidates: set[str] = set()

        for pattern in _API_PATTERNS:
            for match in pattern.finditer(text):
                candidates.add(match.group(1))

        for raw in candidates:
            resolved = safe_urljoin(base_url, raw)
            if not resolved:
                continue
            path = urlparse(resolved).path.lower()
            # filtra falsos positivos óbvios (arquivos estáticos capturados
            # sem querer pelo regex genérico de /v1/, /v2/ etc.)
            if path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2")):
                continue
            with self._lock:
                if resolved in self._found:
                    continue
                self._found.add(resolved)
            new_ones.append(resolved)

        # também detecta diretamente pelos segmentos de caminho típicos de API
        for seg in _API_HINT_SEGMENTS:
            for m in re.finditer(r"""['"]([^'"]*?%s[^'"]*)['"]""" % re.escape(seg), text, re.I):
                resolved = safe_urljoin(base_url, m.group(1))
                if not resolved:
                    continue
                with self._lock:
                    if resolved in self._found:
                        continue
                    self._found.add(resolved)
                new_ones.append(resolved)

        if new_ones and self.on_found:
            for url in new_ones:
                self.on_found(url)
        return new_ones

    def all_found(self) -> list[str]:
        with self._lock:
            return sorted(self._found)

    def write_report(self, path):
        endpoints = self.all_found()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# Jester — endpoints de API detectados para {self.target_host}\n")
            fh.write(f"# Total: {len(endpoints)}\n\n")
            for url in endpoints:
                fh.write(url + "\n")
        return len(endpoints)

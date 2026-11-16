"""Defensive diagnostics for hosts the operator is authorized to test.

All results are JSON-serializable. Network and validation errors raise clear
standard exceptions, except TCP connection failures, which are returned as
results. Timeouts apply to socket operations; system DNS resolution through
getaddrinfo may not honor a socket timeout on every platform.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import math
import re
import socket
import ssl
from urllib.parse import urlsplit

MAX_PORTS = 32


def _host(host):
    if not isinstance(host, str) or not host or host != host.strip():
        raise ValueError("host must be a single hostname or IP address")
    if any(ch.isspace() for ch in host) or any(ch in host for ch in "/@?#[]\\%"):
        raise ValueError("host must be a single hostname or IP address, not a URL or range")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if ':' in host or len(host) > 253 or re.fullmatch(r'[0-9.]+-[0-9.]+', host):
            raise ValueError("invalid hostname or IP address")
        try:
            labels = host.rstrip('.').encode('idna').decode('ascii').split('.')
        except UnicodeError as exc:
            raise ValueError("invalid hostname") from exc
        if any(not label or len(label) > 63 or label[0] == '-' or label[-1] == '-' or
               any(not (c.isascii() and (c.isalnum() or c == '-')) for c in label)
               for label in labels):
            raise ValueError("invalid hostname")
    return host


def _port(port):
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")
    return port


def _timeout(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number of seconds")
    return float(timeout)


def dns_lookup(host):
    """Resolve one host using the system resolver; return unique IP addresses."""
    host = _host(host)
    found = []
    for family, _, _, _, sockaddr in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM):
        if family in (socket.AF_INET, socket.AF_INET6):
            entry = {"family": "IPv4" if family == socket.AF_INET else "IPv6", "address": sockaddr[0]}
            if entry not in found:
                found.append(entry)
    return {"host": host, "addresses": found}


def http_headers(url, timeout=5.0, cafile=None):
    """GET one HTTP(S) URL without following redirects, returning status and headers.

    HTTPS verifies the certificate and hostname; cafile optionally adds a custom
    CA bundle. Repeated headers are preserved as [name, value] pairs.
    """
    _timeout(timeout)
    if not isinstance(url, str):
        raise ValueError("url must be an HTTP or HTTPS URL")
    try:
        parts = urlsplit(url)
        port = parts.port
        host = parts.hostname
    except ValueError as exc:
        raise ValueError("invalid URL or port") from exc
    if parts.scheme.lower() not in ("http", "https") or not parts.netloc or not host or parts.username is not None or parts.password is not None:
        raise ValueError("url must be an HTTP or HTTPS URL without credentials")
    _host(host)
    if port is not None:
        _port(port)
    if parts.scheme.lower() == 'https':
        connection = http.client.HTTPSConnection(host, port=port, timeout=timeout, context=ssl.create_default_context(cafile=cafile))
    else:
        if cafile is not None:
            raise ValueError("cafile is only supported for HTTPS")
        connection = http.client.HTTPConnection(host, port=port, timeout=timeout)
    path = parts.path or '/'
    if parts.query:
        path += '?' + parts.query
    try:
        connection.request('GET', path, headers={'User-Agent': 'Grasshopher-Network-Diagnostics/1.0', 'Connection': 'close'})
        response = connection.getresponse()
        return {"url": url, "status": response.status, "reason": response.reason,
                "headers": [[name, value] for name, value in response.getheaders()]}
    finally:
        connection.close()


def tls_certificate(host, port=443, timeout=5.0, cafile=None):
    """Inspect a verified TLS certificate for a single host (hostname checked)."""
    host, port, timeout = _host(host), _port(port), _timeout(timeout)
    context = ssl.create_default_context(cafile=cafile)
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with context.wrap_socket(raw, server_hostname=host) as secure:
            cert = secure.getpeercert()
            der = secure.getpeercert(binary_form=True)
            return {"host": host, "port": port, "tls_version": secure.version(),
                    "cipher": list(secure.cipher()) if secure.cipher() else None,
                    "certificate": cert, "sha256": hashlib.sha256(der).hexdigest(),
                    "verified": True}


def tcp_connect(host, port, timeout=3.0, *, authorized=False):
    """Try one TCP connection to the first resolved address; no data is sent.

    Caller must explicitly affirm authorization. A failed connection is reported
    as connected=False; invalid input or name-resolution failure raises.
    """
    if authorized is not True:
        raise ValueError("explicit authorization required: pass authorized=True")
    host, port, timeout = _host(host), _port(port), _timeout(timeout)
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    if not infos:
        raise OSError("host resolved to no TCP addresses")
    family, socktype, proto, _, sockaddr = infos[0]
    with socket.socket(family, socktype, proto) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(sockaddr)
        except OSError as exc:
            return {"host": host, "address": sockaddr[0], "port": port,
                    "connected": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"host": host, "address": sockaddr[0], "port": port, "connected": True, "error": None}


def tcp_ports(host, ports, timeout=3.0, *, authorized=False):
    """Sequentially test a supplied list of at most 32 ports on one host.

    Each test makes at most one TCP connection, without sending application data.
    Port lists are validated in full before any network operation.
    """
    if authorized is not True:
        raise ValueError("explicit authorization required: pass authorized=True")
    _host(host)
    _timeout(timeout)
    if not isinstance(ports, (list, tuple)) or not 1 <= len(ports) <= MAX_PORTS:
        raise ValueError("ports must be a list or tuple of 1 to 32 explicit ports")
    for port in ports:
        _port(port)
    return {"host": host, "results": [tcp_connect(host, port, timeout, authorized=True) for port in ports]}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Defensive diagnostics for authorized hosts")
    sub = parser.add_subparsers(dest='command', required=True)
    dns = sub.add_parser('dns', help='resolve a single hostname')
    dns.add_argument('host')
    http = sub.add_parser('http', help='fetch headers without following redirects')
    http.add_argument('url')
    http.add_argument('--timeout', type=float, default=5.0)
    http.add_argument('--cafile')
    tls = sub.add_parser('tls', help='inspect a verified TLS certificate')
    tls.add_argument('host')
    tls.add_argument('--port', type=int, default=443)
    tls.add_argument('--timeout', type=float, default=5.0)
    tls.add_argument('--cafile')
    tcp = sub.add_parser('tcp', help='test explicitly listed ports on one authorized host')
    tcp.add_argument('host')
    tcp.add_argument('ports', nargs='+', type=int)
    tcp.add_argument('--timeout', type=float, default=3.0)
    tcp.add_argument('--authorized', action='store_true', help='affirm authorization to test this host')
    args = parser.parse_args(argv)
    try:
        if args.command == 'dns':
            result = dns_lookup(args.host)
        elif args.command == 'http':
            result = http_headers(args.url, args.timeout, args.cafile)
        elif args.command == 'tls':
            result = tls_certificate(args.host, args.port, args.timeout, args.cafile)
        else:
            result = tcp_ports(args.host, args.ports, args.timeout, authorized=args.authorized)
    except (ValueError, OSError, http.client.HTTPException) as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

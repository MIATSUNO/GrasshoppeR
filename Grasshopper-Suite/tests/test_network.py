import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import network_tools as net

# Deliberately public, self-signed localhost certificate and key, for tests only.
CERT = '-----BEGIN CERTIFICATE-----\nMIIDJTCCAg2gAwIBAgIUfw4LMmVYPLInxHnSK1GvJSACwcMwDQYJKoZIhvcNAQEL\nBQAwFDESMBAGA1UEAwwJbG9jYWxob3N0MB4XDTI2MTExMzIxMzg1MFoXDTM2MTEx\nMDIxMzg1MFowFDESMBAGA1UEAwwJbG9jYWxob3N0MIIBIjANBgkqhkiG9w0BAQEF\nAAOCAQ8AMIIBCgKCAQEAwmtFKZyfKEzwKnjaM3IobvK5HYeWnTDMPvxX+24tz8wj\nc/XE52cUb11DjM3DaY1TvJCSzl9m2XVRQrqoKnQbs37Q8xlvK6OhJlSghN5pvt46\noNG/u4885Mo3SZlFT+P9k3Y0jGTCRYMGvGiX2PsZYSPEKUjJ7o/aoOggnXeTEjm3\nyN2yjpJP17mI5Z94K8k25aucf9an5bX2SyEfUxNWFRw98lvVzw/FJBYSPduXcJhl\nYzXBQhfq0v5fjDO0IVlAiiNm2uUNZa9vqhYsPXCWn8gqMo2B2OZ1nbeLTJtitPhA\nOxaGClSTuGE7ZdXCrcH3IkJQ1Te2Z+0y6eCKvXdPmQIDAQABo28wbTAdBgNVHQ4E\nFgQU9jNZkUxHeCpGDAe2yVBN/bkl298wHwYDVR0jBBgwFoAU9jNZkUxHeCpGDAe2\nyVBN/bkl298wDwYDVR0TAQH/BAUwAwEB/zAaBgNVHREEEzARgglsb2NhbGhvc3SH\nBH8AAAEwDQYJKoZIhvcNAQELBQADggEBADTyc6Zr7qi9/fxxjX31Os+7wqOOlPyq\nkAd0dV0Yx9s1igZ8HOrulWmBcpgpjr/YXRze2J1O4F4GSsndOn22fpF7Ia2vocbQ\nuzgf4xBQGgqVxIV9V2OLwx6r6eC/Y2o/sga1+AQGQfIW+QmqXIxoJyMAIwSpn2wq\nVhFmzM4bvA/yZMtkZpLX1bkG9cKWlrQOObPC/J6LEH6Kx8YpaACvqZl1G1Dcifnd\n5YXxArguYatxKsqaWhcHqwFWDCWkwIfOObZzDgIoq6kWNPQnWgR6N3cMk6QEvVAr\nRjEb22nsMd85x2l7lwOmfPBo5K54kOwcEA+9zcfKpoL9spID86ez7Ek=\n-----END CERTIFICATE-----\n'
KEY = '-----BEGIN PRIVATE KEY-----\nMIIEugIBADANBgkqhkiG9w0BAQEFAASCBKQwggSgAgEAAoIBAQDCa0UpnJ8oTPAq\neNozcihu8rkdh5adMMw+/Ff7bi3PzCNz9cTnZxRvXUOMzcNpjVO8kJLOX2bZdVFC\nuqgqdBuzftDzGW8ro6EmVKCE3mm+3jqg0b+7jzzkyjdJmUVP4/2TdjSMZMJFgwa8\naJfY+xlhI8QpSMnuj9qg6CCdd5MSObfI3bKOkk/XuYjln3gryTblq5x/1qfltfZL\nIR9TE1YVHD3yW9XPD8UkFhI925dwmGVjNcFCF+rS/l+MM7QhWUCKI2ba5Q1lr2+q\nFiw9cJafyCoyjYHY5nWdt4tMm2K0+EA7FoYKVJO4YTtl1cKtwfciQlDVN7Zn7TLp\n4Iq9d0+ZAgMBAAECgf9/UdofphhhcmeiNZxJYWxmCNtLVPNAsPREGBbshJSVWkDd\nb9XDG0sGozNzKLN2kr1Qf5BxSSJrLNxKfT9W9GXJTQNvycUQwj4gG/7P0XFVNBnk\nHd6yHA7rLBvvPUozrdru9wbyttZPlb758IUaU7zX7W3im27VpaxHZu/0/DNHexM4\neZ2qZqVJ1GVuVqprtQBJpyBAuSj0/10lSPMWC+WX5w3nVFeL+Ysm54v+raexMVdt\n2H7ffySqwM6fdCe3s1pBz/p9DOl+l/lU0x3aQ8jsxkULK5JvETtwR+hOjPQg3XPY\nSPFI0fmsC5XBIAhyasqgHJqryMkyCLL4e9XeRcECgYEA7yFQz6g+iWMcd6Cr7r8F\nA+7oktZJqg8POonKAN50umY4/ZPJQuDbIWc408xwxZQ+qWNhFuIBYBEKQ/OSp6G8\nleRs+8aj9G+Ru8JAQoi+6ZaVYENVvWc0BCsn5luDVSEtOUSFUi87MA7XpHfCN1i7\n5VVzHT86xkopdDi88g0kuqECgYEA0CJ5DltYalFgss8DulnMB5r70iXFxqr3yOXW\nUxrDIRTQs7lgfs98zf6aqz3+3JhAB41TccWRhCu0A4GhnelsdZKaMOY/ar1Nn0DI\n78WsC5KJdCqOjYrooHhEcjAleX3GoMrWjBYZEay2eOzW3Zps2ojG6RhVkbPp7ZBC\nNA6aKfkCgYBDeDfvzz2Nz/wJOLkqDJVirbbLL1DrfYJDdvsa0alHqm3sBhWkHANX\n4mLjR2yOIqynaFXNegj/TO+DiqbXS0gFVsT1KO+7mPsaac1tuF19VLJizbzUStkf\nT/nbAfkFPO4gmVewf4kInzdyvSN8MDobk8d9+gggSG53z0ZoWRMC4QKBgASwAhH0\ntLUQSCE+0FKuGw5Ay1McTqv+xb3cj0sn2yUvltO1ZRr2CVWKWmlo6AiH1UlWQX7a\neECFy3QYw08PJsYvGxHm3Z7FzK29g8kCprFMB5R6MOO3MS4MB16a/v0RfBu69cIJ\n7V6ciS+IBf7Pr4vscK5nQeYaKzaSfSs2+PnhAoGAVpA1TvPXe9vnFCZWqwaGZU33\nYDFs7oU5M5LY+XOe5pM4MM2dBCsizMMBCl4cPbUflp7sz2dtcHaoq7RL+26IDJrP\nUePIi3n217aGCHtfmHfdv7FPVRDXmuCqH7kYUCmZm8gLCoodJ3Y+tfbeNbPtuIg8\ntSMaeZkzgwhxdDO5fP4=\n-----END PRIVATE KEY-----\n'


class Handler(BaseHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
            pass  # Header-only and TLS-inspection clients may disconnect early.

    def do_GET(self):
        if self.path.startswith('/redirect'):
            self.send_response(302)
            self.send_header('Location', '/target')
        else:
            self.send_response(200)
        self.send_header('X-Test', 'one')
        self.send_header('X-Test', 'two')
        self.end_headers()
        self.wfile.write(b'local test')

    def log_message(self, *args):
        pass


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cert = str(Path(cls.tmp.name) / 'cert.pem')
        key = str(Path(cls.tmp.name) / 'key.pem')
        Path(cls.cert).write_text(CERT)
        Path(key).write_text(KEY)
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.https = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cls.cert, key)
        cls.https.socket = ctx.wrap_socket(cls.https.socket, server_side=True)
        cls.threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (cls.http, cls.https)]
        for t in cls.threads:
            t.start()

    @classmethod
    def tearDownClass(cls):
        for server in (cls.http, cls.https):
            server.shutdown()
            server.server_close()
        for t in cls.threads:
            t.join()
        cls.tmp.cleanup()

    def cli(self, *args):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([sys.executable, str(Path(net.__file__)), *map(str, args)],
                              text=True, capture_output=True, timeout=10, env=env)

    def test_dns_localhost(self):
        result = net.dns_lookup('localhost')
        self.assertEqual(result['host'], 'localhost')
        self.assertTrue(result['addresses'])
        self.assertTrue(all(x['family'] in ('IPv4', 'IPv6') for x in result['addresses']))
        json.dumps(result)

    def test_http_headers_and_redirect_not_followed(self):
        url = f'http://127.0.0.1:{self.http.server_port}/redirect?x=1'
        result = net.http_headers(url)
        self.assertEqual(result['status'], 302)
        self.assertEqual([v for k, v in result['headers'] if k.lower() == 'x-test'], ['one', 'two'])
        self.assertIn(['Location', '/target'], result['headers'])
        json.dumps(result)

    def test_https_and_tls_verified_custom_ca(self):
        port = self.https.server_port
        result = net.http_headers(f'https://127.0.0.1:{port}/', cafile=self.cert)
        self.assertEqual(result['status'], 200)
        cert = net.tls_certificate('127.0.0.1', port, cafile=self.cert)
        self.assertTrue(cert['verified'])
        self.assertEqual(len(cert['sha256']), 64)
        self.assertIn(('IP Address', '127.0.0.1'), cert['certificate']['subjectAltName'])
        json.dumps(cert)

    def test_tls_untrusted_rejected(self):
        with self.assertRaises(ssl.SSLCertVerificationError):
            net.tls_certificate('127.0.0.1', self.https.server_port)
        with self.assertRaises(ssl.SSLCertVerificationError):
            net.http_headers(f'https://127.0.0.1:{self.https.server_port}/')

    def test_tls_hostname_mismatch_rejected(self):
        real_create = socket.create_connection
        def local_connection(address, timeout=None, *args, **kwargs):
            return real_create(('127.0.0.1', address[1]), timeout, *args, **kwargs)
        with patch.object(net.socket, 'create_connection', side_effect=local_connection):
            with self.assertRaises(ssl.SSLCertVerificationError):
                net.tls_certificate('wrong.invalid', self.https.server_port, cafile=self.cert)

    def test_tcp_open_closed_and_authorization(self):
        port = self.http.server_port
        with self.assertRaisesRegex(ValueError, 'authorization'):
            net.tcp_connect('127.0.0.1', port)
        with self.assertRaisesRegex(ValueError, 'authorization'):
            net.tcp_ports('127.0.0.1', [port])
        result = net.tcp_connect('127.0.0.1', port, authorized=True)
        self.assertTrue(result['connected'])
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))  # bound but deliberately not listening
            closed = sock.getsockname()[1]
            response = net.tcp_ports('127.0.0.1', [port, closed], authorized=True)
            self.assertEqual([r['connected'] for r in response['results']], [True, False])
            self.assertTrue(response['results'][1]['error'])
        json.dumps(response)

    def test_validation_prevents_network(self):
        with patch.object(net.socket, 'getaddrinfo', side_effect=AssertionError('network touched')):
            for ports in ([], list(range(1, 34)), [80, 0], [True], '80-90'):
                with self.subTest(ports=ports), self.assertRaises(ValueError):
                    net.tcp_ports('localhost', ports, authorized=True)
            for host in ('192.168.0.0/24', 'a,b', 'a b', 'http://localhost', '127.0.0.1-127.0.0.2'):
                with self.subTest(host=host), self.assertRaises(ValueError):
                    net.tcp_connect(host, 80, authorized=True)
            for timeout in (0, -1, float('inf'), float('nan'), True):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    net.tcp_connect('localhost', 80, timeout, authorized=True)

    def test_cli_local_commands(self):
        commands = [
            ('dns', 'localhost'),
            ('http', f'http://127.0.0.1:{self.http.server_port}/redirect'),
            ('http', f'https://127.0.0.1:{self.https.server_port}/', '--cafile', self.cert),
            ('tls', '127.0.0.1', '--port', self.https.server_port, '--cafile', self.cert),
            ('tcp', '127.0.0.1', self.http.server_port, '--authorized'),
        ]
        for args in commands:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsInstance(json.loads(result.stdout), dict)
        denied = self.cli('tcp', '127.0.0.1', self.http.server_port)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn('authorization', denied.stderr)


if __name__ == '__main__':
    unittest.main()

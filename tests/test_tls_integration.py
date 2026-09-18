# Copyright (c) 2025, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""Integration tests for IMAPClient(..., ssl=True) over a real socket pair.

These exercise the actual TLS-from-connect code path (tls.IMAP4_TLS socket
wrap), which unit tests with mocked IMAP4 objects cannot cover. They mirror
tests/test_starttls_integration.py, but with TLS established at connection
time instead of via the STARTTLS command.
"""

import os
import socket
import ssl
import sys
import threading
import unittest
from pathlib import Path

from imapclient.imapclient import IMAPClient

CERT_DIR = Path(__file__).parent / "certs"
CA_FILE = CERT_DIR / "ca.pem"
SERVER_CERT = CERT_DIR / "server.pem"
SERVER_KEY = CERT_DIR / "server.key"

CAPS = b"IMAP4rev1 AUTH=PLAIN"


class FakeTLSServer:
    """Minimal IMAP4 server that speaks TLS from the moment it accepts.

    Serves one connection per instance. TLS handshake failures (expected
    when the client rejects the server certificate) are recorded in
    tls_error rather than error so tearDown can ignore them.
    """

    def __init__(self):
        self.error = None
        self.tls_error = None
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(str(SERVER_CERT), str(SERVER_KEY))
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            conn, _ = self.sock.accept()
            try:
                conn = self.ctx.wrap_socket(conn, server_side=True)
            except ssl.SSLError as e:
                self.tls_error = e
                conn.close()
                return
            conn.sendall(b"* OK [CAPABILITY " + CAPS + b"] fake server ready\r\n")
            f = conn.makefile("rb")
            while True:
                line = f.readline()
                if not line:
                    break
                parts = line.split(None, 1)
                tag = parts[0]
                cmd = parts[1].strip().upper() if len(parts) > 1 else b""
                if cmd.startswith(b"CAPABILITY"):
                    conn.sendall(b"* CAPABILITY " + CAPS + b"\r\n")
                    conn.sendall(tag + b" OK CAPABILITY completed\r\n")
                elif cmd.startswith(b"LOGOUT"):
                    conn.sendall(b"* BYE fake server signing off\r\n")
                    conn.sendall(tag + b" OK LOGOUT completed\r\n")
                    conn.close()
                    return
                else:
                    conn.sendall(tag + b" OK done\r\n")
        except Exception as e:
            self.error = e


@unittest.skipIf(
    sys.version_info < (3, 9),
    "imaplib.IMAP4 gained the timeout parameter in Python 3.9",
)
class TlsSocketTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeTLSServer()
        self._saved_cert_file = os.environ.pop("SSL_CERT_FILE", None)
        os.environ["SSL_CERT_FILE"] = str(CA_FILE)

    def tearDown(self):
        if self._saved_cert_file is not None:
            os.environ["SSL_CERT_FILE"] = self._saved_cert_file
        self.server.sock.close()
        self.assertIsNone(self.server.error)

    def _client(self, **kwargs):
        return IMAPClient("localhost", self.server.port, ssl=True, **kwargs)

    def test_ssl_connect_with_default_context(self):
        client = self._client()

        sock = client._imap.sock
        self.assertIsInstance(sock, ssl.SSLSocket)
        # IMAPClient's documented default: hostname checking and certificate
        # verification ON. imaplib's own None-fallback is unverified.
        self.assertTrue(sock.context.check_hostname)
        self.assertEqual(sock.context.verify_mode, ssl.CERT_REQUIRED)

        self.assertIn(b"IMAP4REV1", client.capabilities())
        client.login("user", "pass")
        client.logout()

    def test_ssl_connect_with_custom_context(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        client = self._client(ssl_context=context)

        self.assertIs(client._imap.sock.context, context)
        client.login("user", "pass")
        client.logout()

    def test_ssl_connect_untrusted_cert_fails(self):
        # Without the test CA in the verification path, the default context
        # must reject the server's self-signed certificate.
        del os.environ["SSL_CERT_FILE"]

        with self.assertRaises(ssl.SSLError):
            self._client()

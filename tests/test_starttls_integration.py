"""Integration tests for starttls() over a real socket pair.

These exercise the actual imaplib starttls code path (socket wrap plus
read-buffer refresh), which unit tests with mocked IMAP4 objects cannot
cover. This is the path that broke on Python 3.14, where IMAP4.file
became a read-only property.
"""

import os
import socket
import ssl
import sys
import threading
from pathlib import Path

import pytest

from imapclient.exceptions import IMAPClientError
from imapclient.imapclient import IMAPClient

CERT_DIR = Path(__file__).parent / "certs"
CA_FILE = CERT_DIR / "ca.pem"
SERVER_CERT = CERT_DIR / "server.pem"
SERVER_KEY = CERT_DIR / "server.key"

PRE_TLS_CAPS = b"IMAP4rev1 STARTTLS AUTH=PLAIN"
POST_TLS_CAPS = b"IMAP4rev1 AUTH=PLAIN"


class FakeSTARTTLSServer:
    """Minimal IMAP4 server that upgrades to TLS when told STARTTLS.

    Serves one connection per instance. Post-TLS CAPABILITY responses omit
    STARTTLS, mirroring what real servers advertise once the connection is
    secured.
    """

    def __init__(self):
        self.refuse_tls = False
        self.error = None
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(str(SERVER_CERT), str(SERVER_KEY))
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _reply_caps(self, conn, tag, caps):
        conn.sendall(b"* CAPABILITY " + caps + b"\r\n")
        conn.sendall(tag + b" OK CAPABILITY completed\r\n")

    def _serve(self):
        try:
            conn, _ = self.sock.accept()
            conn.sendall(
                b"* OK [CAPABILITY " + PRE_TLS_CAPS + b"] fake server ready\r\n"
            )
            f = conn.makefile("rb")
            while True:
                line = f.readline()
                if not line:
                    break
                parts = line.split(None, 1)
                tag = parts[0]
                cmd = parts[1].strip().upper() if len(parts) > 1 else b""
                if cmd.startswith(b"CAPABILITY"):
                    self._reply_caps(conn, tag, PRE_TLS_CAPS)
                elif cmd.startswith(b"STARTTLS"):
                    if self.refuse_tls:
                        conn.sendall(tag + b" NO TLS refused\r\n")
                        continue
                    conn.sendall(tag + b" OK Begin TLS now\r\n")
                    self._serve_tls(self.ctx.wrap_socket(conn, server_side=True))
                    return
                elif cmd.startswith(b"LOGOUT"):
                    conn.sendall(b"* BYE fake server signing off\r\n")
                    conn.sendall(tag + b" OK LOGOUT completed\r\n")
                    conn.close()
                    return
                else:
                    conn.sendall(tag + b" OK done\r\n")
        except Exception as e:
            self.error = e

    def _serve_tls(self, conn):
        f = conn.makefile("rb")
        while True:
            line = f.readline()
            if not line:
                break
            parts = line.split(None, 1)
            tag = parts[0]
            cmd = parts[1].strip().upper() if len(parts) > 1 else b""
            if cmd.startswith(b"CAPABILITY"):
                self._reply_caps(conn, tag, POST_TLS_CAPS)
            elif cmd.startswith(b"LOGOUT"):
                conn.sendall(b"* BYE fake server signing off\r\n")
                conn.sendall(tag + b" OK LOGOUT completed\r\n")
                conn.close()
                return
            else:
                conn.sendall(tag + b" OK done\r\n")


@pytest.fixture
def server():
    srv = FakeSTARTTLSServer()
    saved_cert_file = os.environ.pop("SSL_CERT_FILE", None)
    os.environ["SSL_CERT_FILE"] = str(CA_FILE)
    yield srv
    if saved_cert_file is not None:
        os.environ["SSL_CERT_FILE"] = saved_cert_file
    srv.sock.close()
    assert srv.error is None


@pytest.fixture
def client(server):
    return IMAPClient("localhost", server.port, ssl=False)


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="imaplib.IMAP4 gained the timeout parameter in Python 3.9",
)
def test_starttls_with_default_context(client):
    client.starttls()

    sock = client._imap.sock
    assert isinstance(sock, ssl.SSLSocket)
    # IMAPClient's documented default: hostname checking and certificate
    # verification ON. imaplib's own None-fallback is unverified.
    assert sock.context.check_hostname
    assert sock.context.verify_mode == ssl.CERT_REQUIRED

    assert b"STARTTLS" not in client.capabilities()
    client.login("user", "pass")
    client.logout()


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="imaplib.IMAP4 gained the timeout parameter in Python 3.9",
)
def test_starttls_with_custom_context(server):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    client = IMAPClient("localhost", server.port, ssl=False)
    client.starttls(context)

    assert client._imap.sock.context is context
    client.login("user", "pass")
    client.logout()


@pytest.mark.skipif(
    sys.version_info < (3, 9),
    reason="imaplib.IMAP4 gained the timeout parameter in Python 3.9",
)
def test_starttls_refused_raises_imapclient_error(server):
    server.refuse_tls = True
    client = IMAPClient("localhost", server.port, ssl=False)

    with pytest.raises(IMAPClientError):
        client.starttls()

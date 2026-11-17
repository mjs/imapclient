import imaplib
import select
import socket
import ssl
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from imapclient.imapclient import IMAPClient, SocketTimeout


class IdleSocketTests(unittest.TestCase):
    @contextmanager
    def connection(self, tls=False, buffered=False):
        client_sock, peer = socket.socketpair()
        stream = None
        try:
            client_sock.settimeout(2)
            peer.settimeout(2)
            if tls:
                certs = Path("tests/certs")
                server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                server_context.load_cert_chain(
                    str(certs / "server.pem"), str(certs / "server.key")
                )
                client_context = ssl.create_default_context(
                    cafile=str(certs / "ca.pem")
                )
                peer = server_context.wrap_socket(
                    peer, server_side=True, do_handshake_on_connect=False
                )
                client_sock = client_context.wrap_socket(
                    client_sock,
                    server_hostname="localhost",
                    do_handshake_on_connect=False,
                )
                with ThreadPoolExecutor(max_workers=1) as executor:
                    handshake = executor.submit(peer.do_handshake)
                    client_sock.do_handshake()
                    handshake.result(timeout=2)
            stream = client_sock.makefile("rb")
            imap = imaplib.IMAP4.__new__(imaplib.IMAP4)
            imap.sock = client_sock
            if sys.version_info < (3, 14):
                imap.file = stream
            imap._readbuf = []
            imap.debug = 0
            imap._cmd_log, imap._cmd_log_idx, imap._cmd_log_len = {}, 0, 10
            if buffered:
                # Use the socket reader from Python versions before 3.14.
                imap.readline = stream.readline
            client = IMAPClient.__new__(IMAPClient)
            client._imap = imap
            client._starttls_done = False
            client._cached_capabilities = (b"IDLE",)
            client._timeout = SocketTimeout(connect=2, read=1.25)
            yield client, peer
        finally:
            if stream is not None:
                stream.close()
            client_sock.close()
            peer.close()

    def modes(self):
        return (False, True) if hasattr(select, "poll") else (False,)

    def test_closed_peer(self):
        for poll in self.modes():
            for tls in (False, True):
                for buffered in (False, True):
                    with self.subTest(poll=poll, tls=tls, buffered=buffered):
                        with self.connection(tls, buffered) as (client, peer):
                            peer.close()
                            with patch("imapclient.imapclient.POLL_SUPPORT", poll):
                                with self.assertRaisesRegex(
                                    IMAPClient.AbortError, "EOF"
                                ):
                                    client.idle_check(timeout=0.05)
                            self.assertEqual(client.socket().gettimeout(), 1.25)

    def test_live_peer_without_data(self):
        for poll in self.modes():
            for tls in (False, True):
                with self.subTest(poll=poll, tls=tls):
                    with self.connection(tls) as (client, _):
                        with patch("imapclient.imapclient.POLL_SUPPORT", poll):
                            self.assertEqual(client.idle_check(timeout=0.01), [])
                        self.assertEqual(client.socket().gettimeout(), 1.25)

    def test_live_peer_with_response(self):
        for poll in self.modes():
            for tls in (False, True):
                for buffered in (False, True):
                    with self.subTest(poll=poll, tls=tls, buffered=buffered):
                        with self.connection(tls, buffered) as (client, peer):
                            peer.sendall(b"* 1 EXISTS\r\n")
                            with patch("imapclient.imapclient.POLL_SUPPORT", poll):
                                self.assertEqual(
                                    client.idle_check(timeout=0.05), [(1, b"EXISTS")]
                                )
                            self.assertEqual(client.socket().gettimeout(), 1.25)

    def test_partial_response_keeps_reader_behavior(self):
        for poll in self.modes():
            for buffered in (False, True):
                with self.subTest(poll=poll, buffered=buffered):
                    with self.connection(buffered=buffered) as (client, peer):
                        peer.sendall(b"* 1 EX")
                        with patch("imapclient.imapclient.POLL_SUPPORT", poll):
                            if buffered or sys.version_info < (3, 14):
                                with self.assertRaisesRegex(
                                    IMAPClient.AbortError, "unterminated line"
                                ):
                                    client.idle_check(timeout=0.05)
                            else:
                                self.assertEqual(client.idle_check(timeout=0.05), [])
                                peer.sendall(b"ISTS\r\n")
                                self.assertEqual(
                                    client.idle_check(timeout=0.05), [(1, b"EXISTS")]
                                )
                        self.assertEqual(client.socket().gettimeout(), 1.25)

    def test_data_after_empty_read_is_not_consumed(self):
        for poll in self.modes():
            with self.subTest(poll=poll):
                with self.connection() as (client, peer):
                    peer.sendall(b"x")
                    with patch("imapclient.imapclient.POLL_SUPPORT", poll):
                        with patch.object(
                            client._imap,
                            "_get_line",
                            side_effect=IMAPClient.AbortError("socket error: EOF"),
                        ):
                            self.assertEqual(client.idle_check(timeout=0.05), [])
                    self.assertEqual(client.socket().recv(1), b"x")
                    self.assertEqual(client.socket().gettimeout(), 1.25)


if __name__ == "__main__":
    unittest.main(verbosity=2)

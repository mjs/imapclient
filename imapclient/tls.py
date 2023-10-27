# Copyright (c) 2023, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
This module contains IMAPClient's functionality related to Transport
Layer Security (TLS a.k.a. SSL).
"""

import imaplib
import io
import socket
import ssl
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Buffer


def wrap_socket(
    sock: socket.socket, ssl_context: Optional[ssl.SSLContext], host: str
) -> socket.socket:
    if ssl_context is None:
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

    return ssl_context.wrap_socket(sock, server_hostname=host)


class IMAP4_TLS(imaplib.IMAP4):
    """IMAP4 client class for TLS/SSL connections.

    Adapted from imaplib.IMAP4_SSL.
    """

    def __init__(
        self,
        host: str,
        port: int,
        ssl_context: Optional[ssl.SSLContext],
        timeout: Optional[float] = None,
    ):
        self.ssl_context = ssl_context
        self._timeout = timeout
        imaplib.IMAP4.__init__(self, host, port)
        self.file: io.BufferedReader

    def open(
        self, host: str = "", port: int = 993, timeout: Optional[float] = None
    ) -> None:
        self.host = host
        self.port = port
        sock = socket.create_connection(
            (host, port), timeout if timeout is not None else self._timeout
        )
        self.sock = wrap_socket(sock, self.ssl_context, host)
        self.file = self.sock.makefile("rb")

    def read(self, size: int) -> bytes:
        return self.file.read(size)

    def readline(self) -> bytes:
        return self.file.readline()

    def send(self, data: "Buffer") -> None:
        self.sock.sendall(data)

    def shutdown(self) -> None:
        imaplib.IMAP4.shutdown(self)

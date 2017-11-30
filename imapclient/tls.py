# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
This module contains IMAPClient's functionality related to Transport
Layer Security (TLS a.k.a. SSL).
"""

import imaplib
import socket
import ssl


def wrap_socket(sock, ssl_context, host):

    if not hasattr(ssl, 'create_default_context'):
        # Python 2.7.0 - 2.7.8 do not have the concept of ssl contexts.
        # Thus we have to use the less flexible and legacy way of wrapping the
        # socket
        if ssl_context is not None:
            raise RuntimeError(
                "Cannot precisely configure the SSL connection, upgrade to "
                "Python >= 2.7.9 to fine tune the settings."
            )

        return ssl.wrap_socket(sock)

    if ssl_context is None:
        ssl_context = ssl.create_default_context()

    return ssl_context.wrap_socket(sock, server_hostname=host)


class IMAP4_TLS(imaplib.IMAP4):
    """IMAP4 client class for TLS/SSL connections.

    Adapted from imaplib.IMAP4_SSL.
    """

    def __init__(self, host, port, ssl_context, timeout):
        self.ssl_context = ssl_context
        self._timeout = timeout
        imaplib.IMAP4.__init__(self, host, port)

    def open(self, host, port):
        self.host = host
        self.port = port
        sock = socket.create_connection((host, port), self._timeout.connect)
        self.sock = wrap_socket(sock, self.ssl_context, host)
        self.file = self.sock.makefile('rb')

    def read(self, size):
        return self.file.read(size)

    def readline(self):
        return self.file.readline()

    def send(self, data):
        self.sock.sendall(data)

    def shutdown(self):
        imaplib.IMAP4.shutdown(self)

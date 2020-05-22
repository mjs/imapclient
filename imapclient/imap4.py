# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import socket
from . import conn

class IMAP4WithTimeout(conn.IMAP4):

    def __init__(self, address, port, timeout):
        self._timeout = timeout
        conn.IMAP4.__init__(self, address, port)

    def _create_socket(self):
        return socket.create_connection((self.host, self.port), self._timeout.connect)

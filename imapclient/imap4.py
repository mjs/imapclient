# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import imaplib
import socket


class IMAP4WithTimeout(imaplib.IMAP4):

    def __init__(self, address, port, connection_timeout):
        self._connection_timeout = connection_timeout
        super(IMAP4WithTimeout, self).__init__(address, port)

    def _create_socket(self):
        return socket.create_connection((self.host, self.port),
                                        self._connection_timeout)

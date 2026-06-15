# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import imaplib
import socket
from typing import Optional


class IMAP4WithTimeout(imaplib.IMAP4):
    def __init__(self, address: str, port: int, timeout: Optional[float]) -> None:
        self._timeout = timeout
        super().__init__(address, port, timeout=timeout)

    def _create_socket(self, timeout: Optional[float] = None) -> socket.socket:
        return socket.create_connection(
            (self.host, self.port), timeout if timeout is not None else self._timeout
        )

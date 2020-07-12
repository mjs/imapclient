# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from .imapclient import IMAPClient

try:
    from unittest.mock import Mock
except ImportError:
    try:
        from mock import Mock
    except ImportError:
        raise ImportError(
            'mock library could not be loaded. Please install Python 3.3 or newer '
            'or install the `mock` third-party package through PyPi.'
        )


class TestableIMAPClient(IMAPClient):
    """Wrapper of :py:class:`imapclient.IMAPClient` that mocks all
    interaction with real IMAP server.

    This class should only be used in tests, where you can safely
    interact with imapclient without running commands on a real
    IMAP account.
    """

    def __init__(self):
        super(TestableIMAPClient, self).__init__('somehost')

    def _new_tag(self):
        return 'tag'

    def _connect(self):
        pass

    def _create_conn(self):
        return MockConn()


class MockConn(Mock):

    def __init__(self, *args, **kwargs):
        super(Mock, self).__init__(*args, **kwargs)
        self.sent = b''  # Accumulates what was given to send()

    def send(self, data):
        print(data)
        self.sent += data

    def get_line(self):
        return b'* OK [CAPABILITY IMAP4rev1 SASL-IR LOGIN-REFERRALS ID ENABLE IDLE LITERAL+ STARTTLS AUTH=PLAIN] Dovecot ready.'
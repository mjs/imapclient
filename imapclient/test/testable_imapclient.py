# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from mock import Mock
from imapclient.imapclient import IMAPClient


class TestableIMAPClient(IMAPClient):

    def __init__(self):
        super(TestableIMAPClient, self).__init__('somehost')

    def _create_IMAP4(self):
        return MockIMAP4()


class MockIMAP4(Mock):

    def __init__(self, *args, **kwargs):
        super(Mock, self).__init__(*args, **kwargs)
        self.use_uid = True
        self.sent = b''  # Accumulates what was given to send()
        self.tagged_commands = {}
        self.debug = 0
        self._starttls_done = False

    def send(self, data):
        self.sent += data

    def _new_tag(self):
        return 'tag'

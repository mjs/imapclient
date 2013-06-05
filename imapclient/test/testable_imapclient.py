# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from mock import Mock
from imapclient.imapclient import IMAPClient


class TestableIMAPClient(IMAPClient):

    def __init__(self):
        super(TestableIMAPClient, self).__init__('somehost')

    def _create_IMAP4(self):
        mock_IMAP4 = Mock()
        mock_IMAP4._quote = self._quote
        return mock_IMAP4

    def _quote(self, arg):
        """The real code from IMAP4._quote."""
        arg = arg.replace('\\', '\\\\')
        arg = arg.replace('"', '\\"')
        return '"%s"' % arg

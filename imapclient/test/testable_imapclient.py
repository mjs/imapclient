# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from imapclient.imapclient import IMAPClient
from imapclient.test.mock import Mock

class TestableIMAPClient(IMAPClient):

    def __init__(self):
        super(TestableIMAPClient, self).__init__('somehost')

    def _create_IMAP4(self):
        return Mock()

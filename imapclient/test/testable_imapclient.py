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
        return Mock()

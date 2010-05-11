# Copyright (c) 2010, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from imapclient.imapclient import IMAPClient
from imapclient.test.mock import Mock

class TestableIMAPClient(IMAPClient):

    def __init__(self):
        self._imap = Mock()
        self.use_uid = True
        self.folder_encode = True


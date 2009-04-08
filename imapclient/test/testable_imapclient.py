
from imapclient.imapclient import IMAPClient

class TestableIMAPClient(IMAPClient):

    def __init__(self):
        #XXX
        self._imap = Mock()


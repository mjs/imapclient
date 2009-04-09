import unittest
from imapclient.test.testable_imapclient import TestableIMAPClient
from imapclient.test.mock import sentinel

class IMAPClientTestBase(unittest.TestCase):

    def setUp(self):
        self.client = TestableIMAPClient()


class TestListFolders(IMAPClientTestBase):

    def test_simple(self):
        self.client._imap.list.return_value = ('OK', ['(\\HasNoChildren) "/" "A"',
                                                      '(\\HasNoChildren) "/" "Foo Bar"',
                                                      ])

        folders = self.client.list_folders(sentinel.dir, sentinel.pattern)

        self.assert_(self.client._imap.list.call_args == ((sentinel.dir, sentinel.pattern), {}))
        self.assert_(folders == ['A', 'Foo Bar'])


    def test_without_quotes(self):
        self.client._imap.list.return_value = ('OK', ['(\\HasNoChildren) "/" A',
                                                      '(\\HasNoChildren) "/" B',
                                                      '(\\HasNoChildren) "/" C',
                                                      ])

        folders = self.client.list_folders()
        self.assert_(folders == ['A', 'B', 'C'], 'got %r' % folders)


    def test_mixed(self):
        self.client._imap.list.return_value = ('OK', ['(\\HasNoChildren) "/" Alpha',
                                                      '(\\HasNoChildren) "/" "Foo Bar"',
                                                      '(\\HasNoChildren) "/" C',
                                                      ])

        folders = self.client.list_folders()
        self.assert_(folders == ['Alpha', 'Foo Bar', 'C'], 'got %r' % folders)


if __name__ == '__main__':
    unittest.main()

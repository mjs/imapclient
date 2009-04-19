import unittest
from imapclient.test.testable_imapclient import TestableIMAPClient as IMAPClient
from imapclient.test.mock import sentinel


class IMAPClientTestBase(unittest.TestCase):

    def setUp(self):
        self.client = IMAPClient()


class TestListFolders(IMAPClientTestBase):

    def test_simple(self):
        self.client._imap.list.return_value = ('OK', ['(\\HasNoChildren) "/" "A"',
                                                      '(\\HasNoChildren) "/" "Foo Bar"',
                                                      ])

        folders = self.client.list_folders(sentinel.dir, sentinel.pattern)

        self.assert_(self.client._imap.list.call_args == ((sentinel.dir, sentinel.pattern), {}))
        self.assert_(folders == ['A', 'Foo Bar'])


    def test_NO(self):
        self.client._imap.list.return_value = ('NO', ['badness'])
        self.assertRaises(IMAPClient.Error, self.client.list_folders)


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


    def test_funky_characters(self):
        self.client._imap.list.return_value = ('OK',
                                               [('(\\NoInferiors \\UnMarked) "/" {5}', 'bang\xff'),
                                                '',
                                                '(\\HasNoChildren \\UnMarked) "/" "INBOX"'])

        folders = self.client.list_folders()
        self.assert_(folders == ['bang\xff', 'INBOX'], 'got %r' % folders)



if __name__ == '__main__':
    unittest.main()

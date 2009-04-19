from datetime import datetime
from imapclient.fixed_offset import FixedOffset
from imapclient.imapclient import datetime_to_imap
from imapclient.test.mock import patch, sentinel
from imapclient.test.testable_imapclient import TestableIMAPClient as IMAPClient
import unittest


class IMAPClientTest(unittest.TestCase):

    def setUp(self):
        self.client = IMAPClient()


class TestListFolders(IMAPClientTest):

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


class TestAppend(IMAPClientTest):

    def test_without_msg_time(self):
        self.client._imap.append.return_value = ('OK', ['Good'])

        self.client.append('foobar', sentinel.msg, ['FLAG', 'WAVE'], None)
                           
        self.assert_(self.client._imap.method_calls ==
                     [('append', ('foobar',
                                  '(FLAG WAVE)',
                                  None,
                                  sentinel.msg),
                                 {})
                      ])

    @patch('imapclient.imapclient.datetime_to_imap')
    def test_with_msg_time(self, datetime_to_imap):
        datetime_to_imap.return_value = 'somedate'
        self.client._imap.append.return_value = ('OK', ['Good'])

        self.client.append('foobar', sentinel.msg, ['FLAG', 'WAVE'],
                           datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2*60)))

        self.assert_(datetime_to_imap.called)
        self.assert_(self.client._imap.method_calls ==
                     [('append', ('foobar',
                                  '(FLAG WAVE)',
                                  '"somedate"',
                                  sentinel.msg),
                                 {})
                      ])


class TestDateTimeToImap(unittest.TestCase):

    def test_with_timezone(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0, FixedOffset(2*60 + 30))
        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 +0230')

    @patch('imapclient.imapclient.time.daylight', False)
    @patch('imapclient.imapclient.time.timezone', -3600)
    def test_without_timezone_west(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        actual = datetime_to_imap(dt)
        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 +0100')

    @patch('imapclient.imapclient.time.daylight', False)
    @patch('imapclient.imapclient.time.timezone', 7200)
    def test_without_timezone_east(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 -0200')

    @patch('imapclient.imapclient.time.daylight', False)
    @patch('imapclient.imapclient.time.timezone', 0)
    def test_without_timezone_gmt(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 +0000')

    @patch('imapclient.imapclient.time.daylight', True)
    @patch('imapclient.imapclient.time.altzone', -7200)
    def test_without_timezone_with_dst(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 +0200')


if __name__ == '__main__':
    unittest.main()

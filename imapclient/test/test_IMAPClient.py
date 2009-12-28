# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from datetime import datetime
from imapclient.fixed_offset import FixedOffset
from imapclient.imapclient import datetime_to_imap
from imapclient.test.mock import patch, sentinel, Mock
from imapclient.test.testable_imapclient import TestableIMAPClient as IMAPClient
import unittest


class IMAPClientTest(unittest.TestCase):

    def setUp(self):
        self.client = IMAPClient()


class TestListFolders(IMAPClientTest):

    def test_list_folders(self):
        self.client._imap.list.return_value = ('OK', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_folders(sentinel.dir, sentinel.pattern)

        self.assert_(self.client._imap.list.call_args == ((sentinel.dir, sentinel.pattern), {}))
        self.assert_(self.client._proc_folder_list.call_args == ((sentinel.folder_data,), {}))
        self.assert_(folders is sentinel.folder_list)

        
    def test_list_sub_folders(self):
        self.client._imap.lsub.return_value = ('OK', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_sub_folders(sentinel.dir, sentinel.pattern)

        self.assert_(self.client._imap.lsub.call_args == ((sentinel.dir, sentinel.pattern), {}))
        self.assert_(self.client._proc_folder_list.call_args == ((sentinel.folder_data,), {}))
        self.assert_(folders is sentinel.folder_list)


    def test_list_folders_NO(self):
        self.client._imap.list.return_value = ('NO', ['badness'])
        self.assertRaises(IMAPClient.Error, self.client.list_folders)


    def test_list_sub_folders_NO(self):
        self.client._imap.list.return_value = ('NO', ['badness'])
        self.assertRaises(IMAPClient.Error, self.client.list_folders)


    def test_simple(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" "A"',
                                                 '(\\HasNoChildren) "/" "Foo Bar"',
                                                 ])
        self.assert_(folders == ['A', 'Foo Bar'])




    def test_without_quotes(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" A',
                                                 '(\\HasNoChildren) "/" B',
                                                 '(\\HasNoChildren) "/" C',
                                                 ])
        self.assert_(folders == ['A', 'B', 'C'], 'got %r' % folders)


    def test_mixed(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" Alpha',
                                                 '(\\HasNoChildren) "/" "Foo Bar"',
                                                 '(\\HasNoChildren) "/" C',
                                                 ])
        self.assert_(folders == ['Alpha', 'Foo Bar', 'C'], 'got %r' % folders)


    def test_funky_characters(self):
        folders = self.client._proc_folder_list([('(\\NoInferiors \\UnMarked) "/" {5}', 'bang\xff'),
                                                 '',
                                                 '(\\HasNoChildren \\UnMarked) "/" "INBOX"'])
        self.assert_(folders == ['bang\xff', 'INBOX'], 'got %r' % folders)


    def test_escaped_quotes(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" "Test \"Folder\""',
                                                 '(\\HasNoChildren) "/" "Left\"Right"',
                                                 ])
        self.assert_(folders == ['Test "Folder"', 'Left\"Right'], 'got %r' % folders)


    def test_other_escaping(self):
        self.fail("what other escapes are allowed?")


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

    @patch('imapclient.imapclient.FixedOffset.for_system')
    def test_without_timezone(self, for_system):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        for_system.return_value = FixedOffset(-5 * 60)

        self.assert_(datetime_to_imap(dt) == '02-Jan-2009 03:04:05 -0500')



if __name__ == '__main__':
    unittest.main()

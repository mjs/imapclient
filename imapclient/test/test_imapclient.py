# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import itertools
import socket
import sys
from datetime import datetime
from mock import patch, sentinel, Mock

from imapclient import six
from imapclient.fixed_offset import FixedOffset
from imapclient.imapclient import datetime_to_imap
from imapclient.test.testable_imapclient import TestableIMAPClient as IMAPClient
from imapclient.test.util import unittest

class IMAPClientTest(unittest.TestCase):

    def setUp(self):
        self.client = IMAPClient()


class TestListFolders(IMAPClientTest):

    def test_list_folders(self):
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = ('LIST', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with(
            'LIST', '"foo"', '"bar"')
        self.assertEqual(self.client._proc_folder_list.call_args, ((sentinel.folder_data,), {}))
        self.assertTrue(folders is sentinel.folder_list)

    def test_list_sub_folders(self):
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = ('LSUB', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_sub_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with(
            'LSUB', '"foo"', '"bar"')
        self.assertEqual(self.client._proc_folder_list.call_args, ((sentinel.folder_data,), {}))
        self.assertTrue(folders is sentinel.folder_list)


    def test_list_folders_NO(self):
        self.client._imap._simple_command.return_value = ('NO', [b'badness'])
        self.assertRaises(IMAPClient.Error, self.client.list_folders)


    def test_list_sub_folders_NO(self):
        self.client._imap._simple_command.return_value = ('NO', [b'badness'])
        self.assertRaises(IMAPClient.Error, self.client.list_folders)

    def test_utf7_decoding(self):
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = (
            b'LIST', [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ])

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with('LIST', '"foo"', '"bar"')
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'A'),
                                   (('\\HasNoChildren',), '/', 'Hello\xffworld')])

    def test_folder_encode_off(self):
        self.client.folder_encode = False
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = (
            b'LIST', [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ])

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with('LIST', '"foo"', '"bar"')
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'A'),
                                   (('\\HasNoChildren',), '/', 'Hello&AP8-world')])

    def test_simple(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" "A"',
                                                 '(\\HasNoChildren) "/" "Foo Bar"',
                                                 ])
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'A',),
                                   (('\\HasNoChildren',), '/', 'Foo Bar')])


    def test_without_quotes(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" A',
                                                 '(\\HasNoChildren) "/" B',
                                                 '(\\HasNoChildren) "/" C',
                                                 ])
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'A'),
                                   (('\\HasNoChildren',), '/', 'B'),
                                   (('\\HasNoChildren',), '/', 'C')])

    def test_unquoted_numeric_folder_name(self):
        # Some IMAP implementations do this
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" 123'])
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', '123')])

    def test_mixed(self):
        folders = self.client._proc_folder_list(['(\\HasNoChildren) "/" Alpha',
                                                 '(\\HasNoChildren) "/" "Foo Bar"',
                                                 '(\\HasNoChildren) "/" C',
                                                 ])
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'Alpha'),
                                   (('\\HasNoChildren',), '/', 'Foo Bar'),
                                   (('\\HasNoChildren',), '/', 'C')])


    def test_funky_characters(self):
        folders = self.client._proc_folder_list([('(\\NoInferiors \\UnMarked) "/" {5}', 'bang\xff'),
                                                 '',
                                                 '(\\HasNoChildren \\UnMarked) "/" "INBOX"'])
        self.assertEqual(folders, [(('\\NoInferiors', '\\UnMarked'), "/", 'bang\xff'),
                                   (('\\HasNoChildren', '\\UnMarked'), "/", 'INBOX')])


    def test_quoted_specials(self):
        folders = self.client._proc_folder_list([r'(\HasNoChildren) "/" "Test \"Folder\""',
                                                 r'(\HasNoChildren) "/" "Left\"Right"',
                                                 r'(\HasNoChildren) "/" "Left\\Right"',
                                                 r'(\HasNoChildren) "/" "\"Left Right\""',
                                                 r'(\HasNoChildren) "/" "\"Left\\Right\""',
                                                 ])
        self.assertEqual(folders, [(('\\HasNoChildren',), '/', 'Test "Folder"'),
                                   (('\\HasNoChildren',), '/', 'Left\"Right'),
                                   (('\\HasNoChildren',), '/', r'Left\Right'),
                                   (('\\HasNoChildren',), '/', r'"Left Right"'),
                                   (('\\HasNoChildren',), '/', r'"Left\Right"'),
                                   ])

    def test_empty_response(self):
        self.assertEqual(self.client._proc_folder_list([None]), [])


    def test_blanks(self):
        folders = self.client._proc_folder_list(['', None, r'(\HasNoChildren) "/" "last"'])
        self.assertEqual(folders, [((r'\HasNoChildren',), '/', 'last')])


class TestSelectFolder(IMAPClientTest):

    def test_normal(self):
        self.client._command_and_check = Mock()
        self.client._imap.untagged_responses = {
            b'exists': [b'3'],
            b'FLAGS': [br"(\Flagged \Deleted abc [foo]/bar def)"],
            b'HIGHESTMODSEQ': [b'127110'],
            b'OK': [br"[PERMANENTFLAGS (\Flagged \Deleted abc [foo]/bar def \*)] Flags permitted.",
                    b'[UIDVALIDITY 631062293] UIDs valid.',
                    b'[UIDNEXT 1281] Predicted next UID.',
                    b'[HIGHESTMODSEQ 127110]'],
            b'PERMANENTFLAGS': [br'(\Flagged \Deleted abc [foo'],
            b'READ-WRITE': [b''],
            b'RECENT': [b'0'],
            b'UIDNEXT': [b'1281'],
            b'UIDVALIDITY': [b'631062293'],
            b'OTHER': [b'blah']
        }

        result = self.client.select_folder(b'folder_name', sentinel.readonly)

        self.client._command_and_check.assert_called_once_with('select',
                                                               '"folder_name"',
                                                               sentinel.readonly)
        self.maxDiff = 99999
        self.assertEqual(result, {
            'EXISTS': 3,
            'RECENT': 0,
            'UIDNEXT': 1281,
            'UIDVALIDITY': 631062293,
            'HIGHESTMODSEQ': 127110,
            'FLAGS': (r'\Flagged', r'\Deleted', 'abc', '[foo]/bar', 'def'),
            'PERMANENTFLAGS': (r'\Flagged', r'\Deleted', 'abc', '[foo]/bar', 'def', r'\*'),
            'READ-WRITE': True,
            'OTHER': ['blah']
        })


class TestAppend(IMAPClientTest):

    def test_without_msg_time(self):
        self.client._imap.append.return_value = ('OK', [b'Good'])
        msg = 'hi'

        self.client.append('foobar', msg, ['FLAG', 'WAVE'], None)

        self.client._imap.append.assert_called_with(
            '"foobar"', '(FLAG WAVE)', None, b'hi')

    @patch('imapclient.imapclient.datetime_to_imap')
    def test_with_msg_time(self, datetime_to_imap):
        datetime_to_imap.return_value = 'somedate'
        self.client._imap.append.return_value = ('OK', [b'Good'])
        msg = b'bye'

        self.client.append('foobar', msg, ['FLAG', 'WAVE'],
                           datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2*60)))

        self.assertTrue(datetime_to_imap.called)
        self.client._imap.append.assert_called_with(
            '"foobar"', '(FLAG WAVE)', '"somedate"', msg)


class TestDateTimeToImap(unittest.TestCase):

    def test_with_timezone(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0, FixedOffset(2*60 + 30))
        self.assertEqual(datetime_to_imap(dt), '02-Jan-2009 03:04:05 +0230')

    @patch('imapclient.imapclient.FixedOffset.for_system')
    def test_without_timezone(self, for_system):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        for_system.return_value = FixedOffset(-5 * 60)

        self.assertEqual(datetime_to_imap(dt), '02-Jan-2009 03:04:05 -0500')


class TestAclMethods(IMAPClientTest):

    def test_getacl(self):
        self.client._imap.getacl.return_value = ('OK', [b'INBOX Fred rwipslda Sally rwip'])
        acl = self.client.getacl('INBOX')
        self.assertSequenceEqual(acl, [('Fred', 'rwipslda'), ('Sally', 'rwip')])

    def test_setacl(self):
        self.client._imap.setacl.return_value = ('OK', [b"SETACL done"])

        response = self.client.setacl('folder', sentinel.who, sentinel.what)

        self.client._imap.setacl.assert_called_with('"folder"',
                                                    sentinel.who,
                                                    sentinel.what)
        self.assertEqual(response, "SETACL done")


class TestIdleAndNoop(IMAPClientTest):

    def test_idle(self):
        self.client._imap._command.return_value = sentinel.tag
        self.client._imap._get_response.return_value = None

        self.client.idle()

        self.client._imap._command.assert_called_with('IDLE')
        self.assertEqual(self.client._idle_tag, sentinel.tag)

    @patch('imapclient.imapclient.select.select')
    def test_idle_check_blocking(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([True], [], [])
        counter = itertools.count()
        def fake_get_line():
            count = six.next(counter)
            if count == 0:
                return '* 1 EXISTS'
            elif count == 1:
                return '* 0 EXPUNGE'
            else:
                raise socket.timeout
        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        mock_select.assert_called_once_with([mock_sock], [], [], None)
        self.assertListEqual(mock_sock.method_calls,
                             [('setblocking', (0,), {}),
                              ('setblocking', (1,), {})])
        self.assertListEqual([(1, 'EXISTS'), (0, 'EXPUNGE')], responses)

    @patch('imapclient.imapclient.select.select')
    def test_idle_check_timeout(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([], [], [])

        responses = self.client.idle_check(timeout=0.5)

        mock_select.assert_called_once_with([mock_sock], [], [], 0.5)
        self.assertListEqual(mock_sock.method_calls,
                             [('setblocking', (0,), {}),
                              ('setblocking', (1,), {})])
        self.assertListEqual([], responses)

    @patch('imapclient.imapclient.select.select')
    def test_idle_check_with_data(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([True], [], [])
        counter = itertools.count()
        def fake_get_line():
            count = six.next(counter)
            if count == 0:
                return b'* 99 EXISTS'
            else:
                raise socket.timeout
        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        mock_select.assert_called_once_with([mock_sock], [], [], None)
        self.assertListEqual(mock_sock.method_calls,
                             [('setblocking', (0,), {}),
                              ('setblocking', (1,), {})])
        self.assertListEqual([(99, 'EXISTS')], responses)

    def test_idle_done(self):
        self.client._idle_tag = sentinel.tag

        mockSend = Mock()
        self.client._imap.send = mockSend
        mockConsume = Mock(return_value=sentinel.out)
        self.client._consume_until_tagged_response = mockConsume

        result = self.client.idle_done()

        mockSend.assert_called_with(b'DONE\r\n')
        mockConsume.assert_called_with(sentinel.tag, 'IDLE')
        self.assertEqual(result, sentinel.out)

    def test_noop(self):
        mockCommand = Mock(return_value=sentinel.tag)
        self.client._imap._command = mockCommand
        mockConsume = Mock(return_value=sentinel.out)
        self.client._consume_until_tagged_response = mockConsume

        result = self.client.noop()

        mockCommand.assert_called_with('NOOP')
        mockConsume.assert_called_with(sentinel.tag, 'NOOP')
        self.assertEqual(result, sentinel.out)

    def test_consume_until_tagged_response(self):
        client = self.client
        client._imap.tagged_commands = {sentinel.tag: None}

        counter = itertools.count()
        def fake_get_response():
            count = six.next(counter)
            if count == 0:
                return '* 99 EXISTS'
            client._imap.tagged_commands[sentinel.tag] = ('OK', ['Idle done'])
        client._imap._get_response = fake_get_response
            
        text, responses = client._consume_until_tagged_response(sentinel.tag,
                                                                'IDLE')
        self.assertEqual(client._imap.tagged_commands, {})
        self.assertEqual(text, 'Idle done')
        self.assertListEqual([(99, 'EXISTS')], responses)


                         
class TestDebugLogging(IMAPClientTest):

    def test_default_is_stderr(self):
        self.assertIs(self.client.log_file, sys.stderr)

    def test_IMAP_is_patched(self):
        log = six.StringIO()
        self.client.log_file = log

        self.client._log('one')
        self.client._imap._mesg('two')

        output = log.getvalue()
        self.assertIn('one', output)
        self.assertIn('two', output)

class TestTimeNormalisation(IMAPClientTest):

    def test_default(self):
        self.assertTrue(self.client.normalise_times)

    @patch('imapclient.imapclient.parse_fetch_response')
    def test_pass_through(self, parse_fetch_response):
        self.client._imap._command_complete.return_value = ('OK', sentinel.data)
        self.client._imap._untagged_response.return_value = ('OK', sentinel.fetch_data)
        self.client.use_uid = sentinel.use_uid

        def check(expected):
            self.client.fetch(22, ['SOMETHING'])
            parse_fetch_response.assert_called_with(sentinel.fetch_data,
                                                    expected,
                                                    sentinel.use_uid)

        self.client.normalise_times = True
        check(True)

        self.client.normalise_times = False
        check(False)


class TestGmailLabels(IMAPClientTest):

    def setUp(self):
        super(TestGmailLabels, self).setUp()
        patcher = patch.object(self.client, '_store', autospec=True, return_value=sentinel.label_set)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_get(self):
        with patch.object(self.client, 'fetch', autospec=True,
                          return_value={123: {'X-GM-LABELS': ['foo', 'bar']},
                                        444: {'X-GM-LABELS': ['foo']}}):
            out = self.client.get_gmail_labels(sentinel.messages)
            self.client.fetch.assert_called_with(sentinel.messages, ['X-GM-LABELS'])
            self.assertEqual(out, {123: ['foo', 'bar'],
                                   444: ['foo']})

    def test_add(self):
        self.client.add_gmail_labels(sentinel.messages, sentinel.labels)
        self.client._store.assert_called_with('+X-GM-LABELS', sentinel.messages, sentinel.labels, 'X-GM-LABELS')

    def test_remove(self):
        self.client.remove_gmail_labels(sentinel.messages, sentinel.labels)
        self.client._store.assert_called_with('-X-GM-LABELS', sentinel.messages, sentinel.labels, 'X-GM-LABELS')

    def test_set(self):
        self.client.set_gmail_labels(sentinel.messages, sentinel.labels)
        self.client._store.assert_called_with('X-GM-LABELS', sentinel.messages, sentinel.labels, 'X-GM-LABELS')


class TestNamespace(IMAPClientTest):

    def set_return(self, value):
        self.client._imap.namespace.return_value = ('OK', [value])

    def test_simple(self):
        self.set_return(b'(("FOO." "/")) NIL NIL')
        self.assertEqual(self.client.namespace(), ((('FOO.', '/'),), None, None))

    def test_other_only(self):
        self.set_return(b'NIL NIL (("" "."))')
        self.assertEqual(self.client.namespace(), (None, None, (("", "."),)))

    def test_complex(self):
        self.set_return(b'(("" "/")) '
                        b'(("~" "/")) '
                        b'(("#shared/" "/") ("#public/" "/")("#ftp/" "/")("#news." "."))')
        self.assertEqual(self.client.namespace(), (
            (("", "/"),),
            (("~", "/"),),
            (("#shared/", "/"), ("#public/", "/"), ("#ftp/", "/"), ("#news.", ".")),
            ))

class TestCapabilities(IMAPClientTest):

    def test_preauth(self):
        self.client._imap.capabilities = ('FOO', 'BAR')
        self.client._imap.untagged_responses = {}

        self.assertEqual(self.client.capabilities(), ('FOO', 'BAR'))

    def test_server_returned_capability_after_auth(self):
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {'CAPABILITY': ['FOO MORE']}

        self.assertEqual(self.client._cached_capabilities, None)
        self.assertEqual(self.client.capabilities(), ('FOO', 'MORE'))
        self.assertEqual(self.client._cached_capabilities, ('FOO', 'MORE'))

    def test_caching(self):
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {}
        self.client._cached_capabilities = ('FOO', 'MORE')

        self.assertEqual(self.client.capabilities(), ('FOO', 'MORE'))

    def test_post_auth_request(self):
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {}
        self.client._imap.state = 'SELECTED'
        self.client._imap.capability.return_value = ('OK', [b'FOO BAR'])

        self.assertEqual(self.client.capabilities(), ('FOO', 'BAR'))
        self.assertEqual(self.client._cached_capabilities, ('FOO', 'BAR'))


class TestThread(IMAPClientTest):

    def test_thread_without_uid(self):
        self.client._cached_capabilities = ('THREAD=REFERENCES',)
        self.client.use_uid = False
        self.client._imap.thread.return_value = ('OK', [b'(1 2)(3)(4 5 6)'])

        threads = self.client.thread()

        self.assertSequenceEqual(threads, ((1, 2), (3,), (4, 5, 6)))

    def test_thread_with_uid(self):
        self.client._cached_capabilities = ('THREAD=REFERENCES',)
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'(1 2)(3)(4 5 6)'])

        threads = self.client.thread()

        self.assertSequenceEqual(threads, ((1, 2), (3,), (4, 5, 6)))

    def test_no_support(self):
        self.client._cached_capabilities = ('NOT-THREAD',)
        self.assertRaises(ValueError, self.client.thread)

    def test_no_support2(self):
        self.client._cached_capabilities = ('THREAD=FOO',)
        self.assertRaises(ValueError, self.client.thread)

    def test_all_args_with_uid(self):
        self.client._cached_capabilities = ('THREAD=FOO',)
        self.client._imap.uid.return_value = ('OK', [])

        self.client.thread(algorithm='FOO', criteria='STUFF', charset='ASCII')

        self.client._imap.uid.assert_called_once_with('thread', 'FOO', 'ASCII', '(STUFF)')

    def test_all_args_without_uid(self):
        self.client.use_uid = False
        self.client._cached_capabilities = ('THREAD=FOO',)
        self.client._imap.thread.return_value = ('OK', [])

        self.client.thread(algorithm='FOO', criteria='STUFF', charset='ASCII')

        self.client._imap.thread.assert_called_once_with('FOO', 'ASCII','(STUFF)')

if __name__ == '__main__':
    unittest.main()

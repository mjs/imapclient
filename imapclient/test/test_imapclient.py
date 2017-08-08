# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import itertools
import socket
import sys
from datetime import datetime
import logging

import six

from imapclient.fixed_offset import FixedOffset
from .testable_imapclient import TestableIMAPClient as IMAPClient
from .imapclient_test import IMAPClientTest
from .util import patch, sentinel, Mock


class TestListFolders(IMAPClientTest):

    def test_list_folders(self):
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = ('LIST', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with(
            'LIST', b'"foo"', b'"bar"')
        self.assertEqual(self.client._proc_folder_list.call_args, ((sentinel.folder_data,), {}))
        self.assertTrue(folders is sentinel.folder_list)

    def test_list_sub_folders(self):
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = ('LSUB', sentinel.folder_data)
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_sub_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with(
            'LSUB', b'"foo"', b'"bar"')
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
            'LIST', [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ])

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with('LIST', b'"foo"', b'"bar"')
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', 'A'),
                                   ((b'\\HasNoChildren',), b'/', 'Hello\xffworld')])

    def test_folder_encode_off(self):
        self.client.folder_encode = False
        self.client._imap._simple_command.return_value = ('OK', [b'something'])
        self.client._imap._untagged_response.return_value = (
            'LIST', [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ])

        folders = self.client.list_folders('foo', 'bar')

        self.client._imap._simple_command.assert_called_once_with('LIST', '"foo"', '"bar"')
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', b'A'),
                                   ((b'\\HasNoChildren',), b'/', b'Hello&AP8-world')])

    def test_simple(self):
        folders = self.client._proc_folder_list([b'(\\HasNoChildren) "/" "A"',
                                                 b'(\\HasNoChildren) "/" "Foo Bar"',
                                                 ])
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', 'A',),
                                   ((b'\\HasNoChildren',), b'/', 'Foo Bar')])

    def test_without_quotes(self):
        folders = self.client._proc_folder_list([b'(\\HasNoChildren) "/" A',
                                                 b'(\\HasNoChildren) "/" B',
                                                 b'(\\HasNoChildren) "/" C',
                                                 ])
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', 'A'),
                                   ((b'\\HasNoChildren',), b'/', 'B'),
                                   ((b'\\HasNoChildren',), b'/', 'C')])

    def test_unquoted_numeric_folder_name(self):
        # Some IMAP implementations do this
        folders = self.client._proc_folder_list([b'(\\HasNoChildren) "/" 123'])
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', '123')])

    def test_unqouted_numeric_folder_name_parsed_as_long(self):
        # big enough numeric values might get parsed as longs
        folder_name = str(sys.maxsize + 1)
        folders = self.client._proc_folder_list(
            [b'(\\HasNoChildren) "/" ' + folder_name.encode('ascii')])
        self.assertEqual(folders, [((b'\\HasNoChildren', ), b'/', folder_name)])

    def test_mixed(self):
        folders = self.client._proc_folder_list([b'(\\HasNoChildren) "/" Alpha',
                                                 b'(\\HasNoChildren) "/" "Foo Bar"',
                                                 b'(\\HasNoChildren) "/" C',
                                                 ])
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', 'Alpha'),
                                   ((b'\\HasNoChildren',), b'/', 'Foo Bar'),
                                   ((b'\\HasNoChildren',), b'/', 'C')])

    def test_funky_characters(self):
        folders = self.client._proc_folder_list([(b'(\\NoInferiors \\UnMarked) "/" {5}', 'bang\xff'),
                                                 b'',
                                                 b'(\\HasNoChildren \\UnMarked) "/" "INBOX"'])
        self.assertEqual(folders, [((b'\\NoInferiors', b'\\UnMarked'), b"/", 'bang\xff'),
                                   ((b'\\HasNoChildren', b'\\UnMarked'), b"/", 'INBOX')])

    def test_quoted_specials(self):
        folders = self.client._proc_folder_list([br'(\HasNoChildren) "/" "Test \"Folder\""',
                                                 br'(\HasNoChildren) "/" "Left\"Right"',
                                                 br'(\HasNoChildren) "/" "Left\\Right"',
                                                 br'(\HasNoChildren) "/" "\"Left Right\""',
                                                 br'(\HasNoChildren) "/" "\"Left\\Right\""',
                                                 ])
        self.assertEqual(folders, [((b'\\HasNoChildren',), b'/', 'Test "Folder"'),
                                   ((b'\\HasNoChildren',), b'/', 'Left\"Right'),
                                   ((b'\\HasNoChildren',), b'/', r'Left\Right'),
                                   ((b'\\HasNoChildren',), b'/', r'"Left Right"'),
                                   ((b'\\HasNoChildren',), b'/', r'"Left\Right"'),
                                   ])

    def test_empty_response(self):
        self.assertEqual(self.client._proc_folder_list([None]), [])

    def test_blanks(self):
        folders = self.client._proc_folder_list(['', None, br'(\HasNoChildren) "/" "last"'])
        self.assertEqual(folders, [((br'\HasNoChildren',), b'/', 'last')])


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
                                                               b'"folder_name"',
                                                               sentinel.readonly)
        self.maxDiff = 99999
        self.assertEqual(result, {
            b'EXISTS': 3,
            b'RECENT': 0,
            b'UIDNEXT': 1281,
            b'UIDVALIDITY': 631062293,
            b'HIGHESTMODSEQ': 127110,
            b'FLAGS': (br'\Flagged', br'\Deleted', b'abc', b'[foo]/bar', b'def'),
            b'PERMANENTFLAGS': (br'\Flagged', br'\Deleted', b'abc', b'[foo]/bar', b'def', br'\*'),
            b'READ-WRITE': True,
            b'OTHER': [b'blah']
        })


class TestAppend(IMAPClientTest):

    def test_without_msg_time(self):
        self.client._imap.append.return_value = ('OK', [b'Good'])
        msg = 'hi'

        self.client.append('foobar', msg, ['FLAG', 'WAVE'], None)

        self.client._imap.append.assert_called_with(
            b'"foobar"', '(FLAG WAVE)', None, b'hi')

    @patch('imapclient.imapclient.datetime_to_INTERNALDATE')
    def test_with_msg_time(self, datetime_to_INTERNALDATE):
        datetime_to_INTERNALDATE.return_value = 'somedate'
        self.client._imap.append.return_value = ('OK', [b'Good'])
        msg = b'bye'

        self.client.append('foobar', msg, ['FLAG', 'WAVE'],
                           datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2 * 60)))

        self.assertTrue(datetime_to_INTERNALDATE.called)
        self.client._imap.append.assert_called_with(
            b'"foobar"', '(FLAG WAVE)', '"somedate"', msg)


class TestAclMethods(IMAPClientTest):

    def test_getacl(self):
        self.client._imap.getacl.return_value = ('OK', [b'INBOX Fred rwipslda Sally rwip'])
        acl = self.client.getacl('INBOX')
        self.assertSequenceEqual(acl, [(b'Fred', b'rwipslda'), (b'Sally', b'rwip')])

    def test_setacl(self):
        self.client._imap.setacl.return_value = ('OK', [b"SETACL done"])

        response = self.client.setacl('folder', sentinel.who, sentinel.what)

        self.client._imap.setacl.assert_called_with(b'"folder"',
                                                    sentinel.who,
                                                    sentinel.what)
        self.assertEqual(response, b"SETACL done")


class TestIdleAndNoop(IMAPClientTest):

    def assert_sock_calls(self, sock):
        self.assertListEqual(sock.method_calls, [
            ('settimeout', (None,), {}),
            ('setblocking', (0,), {}),
            ('setblocking', (1,), {}),
        ])

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
                return b'* 1 EXISTS'
            elif count == 1:
                return b'* 0 EXPUNGE'
            else:
                raise socket.timeout
        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        mock_select.assert_called_once_with([mock_sock], [], [], None)
        self.assert_sock_calls(mock_sock)
        self.assertListEqual([(1, b'EXISTS'), (0, b'EXPUNGE')], responses)

    @patch('imapclient.imapclient.select.select')
    def test_idle_check_timeout(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([], [], [])

        responses = self.client.idle_check(timeout=0.5)

        mock_select.assert_called_once_with([mock_sock], [], [], 0.5)
        self.assert_sock_calls(mock_sock)
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
        self.assert_sock_calls(mock_sock)
        self.assertListEqual([(99, b'EXISTS')], responses)

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
                return b'* 99 EXISTS'
            client._imap.tagged_commands[sentinel.tag] = ('OK', [b'Idle done'])
        client._imap._get_response = fake_get_response

        text, responses = client._consume_until_tagged_response(sentinel.tag, b'IDLE')
        self.assertEqual(client._imap.tagged_commands, {})
        self.assertEqual(text, b'Idle done')
        self.assertListEqual([(99, b'EXISTS')], responses)


class TestDebugLogging(IMAPClientTest):

    def test_IMAP_is_patched(self):
        log_stream = six.StringIO()
        logging.basicConfig(stream=log_stream, level=logging.DEBUG)
        self.client._imap._mesg('two')
        self.assertIn('DEBUG:imapclient.imaplib:two', log_stream.getvalue())


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


class TestNamespace(IMAPClientTest):

    def set_return(self, value):
        self.client._imap.namespace.return_value = ('OK', [value])

    def test_simple(self):
        self.set_return(b'(("FOO." "/")) NIL NIL')
        self.assertEqual(self.client.namespace(), ((('FOO.', '/'),), None, None))

    def test_folder_decoding(self):
        self.set_return(b'(("&AP8-." "/")) NIL NIL')
        self.assertEqual(self.client.namespace(), ((('\xff.', '/'),), None, None))

    def test_without_folder_decoding(self):
        self.set_return(b'(("&AP8-." "/")) NIL NIL')
        self.client.folder_encode = False
        self.assertEqual(self.client.namespace(), (((b'&AP8-.', '/'),), None, None))

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

        self.assertEqual(self.client.capabilities(), (b'FOO', b'BAR'))

    def test_server_returned_capability_after_auth(self):
        self.client._imap.capabilities = (b'FOO',)
        self.client._imap.untagged_responses = {'CAPABILITY': [b'FOO MORE']}

        self.assertEqual(self.client._cached_capabilities, None)
        self.assertEqual(self.client.capabilities(), (b'FOO', b'MORE'))
        self.assertEqual(self.client._cached_capabilities, (b'FOO', b'MORE'))
        self.assertEqual(self.client._imap.untagged_responses, {})

    def test_caching(self):
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {}
        self.client._cached_capabilities = (b'FOO', b'MORE')

        self.assertEqual(self.client.capabilities(), (b'FOO', b'MORE'))

    def test_post_auth_request(self):
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {}
        self.client._imap.state = 'SELECTED'
        self.client._imap.capability.return_value = ('OK', [b'FOO BAR'])

        self.assertEqual(self.client.capabilities(), (b'FOO', b'BAR'))
        self.assertEqual(self.client._cached_capabilities, (b'FOO', b'BAR'))

    def test_with_starttls(self):
        # Initial connection
        self.client._imap.capabilities = ('FOO',)
        self.client._imap.untagged_responses = {}
        self.client._imap.state = 'NONAUTH'
        self.assertEqual(self.client.capabilities(), (b'FOO',))

        # Now do STARTTLS; capabilities change and should be reported.
        self.client._starttls_done = True
        self.client._imap.capability.return_value = ('OK', [b'FOO BAR'])
        self.assertEqual(self.client.capabilities(), (b'FOO', b'BAR'))

        # Login done; capabilities change again.
        self.client._imap.state = 'AUTH'
        self.client._imap.capability.return_value = ('OK', [b'FOO BAR QUX'])
        self.assertEqual(self.client.capabilities(), (b'FOO', b'BAR', b'QUX'))

    def test_has_capability(self):
        self.client._cached_capabilities = (b'FOO', b'MORE')

        self.assertTrue(self.client.has_capability(b'FOO'))
        self.assertTrue(self.client.has_capability(b'foo'))
        self.assertFalse(self.client.has_capability(b'BAR'))

        self.assertTrue(self.client.has_capability('FOO'))
        self.assertTrue(self.client.has_capability('foo'))
        self.assertFalse(self.client.has_capability('BAR'))


class TestId(IMAPClientTest):

    def test_id(self):
        self.client._cached_capabilities = (b'ID',)
        self.client._imap._simple_command.return_value = ('OK', [b'Success'])
        self.client._imap._untagged_response.return_value = (
            b'OK', [b'("name" "GImap" "vendor" "Google, Inc.")'])

        id_response = self.client.id_({'name': 'IMAPClient'})
        self.client._imap._simple_command.assert_called_with(
            'ID', '("name" "IMAPClient")')

        self.assertSequenceEqual(
            id_response,
            ((b'name', b'GImap', b'vendor', b'Google, Inc.'),))

    def test_no_support(self):
        self.client._cached_capabilities = (b'IMAP4rev1',)
        self.assertRaises(ValueError, self.client.id_)

    def test_invalid_parameters(self):
        self.assertRaises(TypeError, self.client.id_, 'bananarama')


class TestRawCommand(IMAPClientTest):

    def setUp(self):
        super(TestRawCommand, self).setUp()
        self.client._imap._get_response.return_value = None
        self.client._imap._command_complete.return_value = ('OK', ['done'])

    def check(self, command, args, expected):
        typ, data = self.client._raw_command(command, args)
        self.assertEqual(typ, 'OK')
        self.assertEqual(data, ['done'])
        self.assertEqual(self.client._imap.sent, expected)

    def test_plain(self):
        self.check(b'search', [b'ALL'],
                   b'tag UID SEARCH ALL\r\n',
                   )

    def test_not_uid(self):
        self.client.use_uid = False
        self.check(b'search', [b'ALL'],
                   b'tag SEARCH ALL\r\n',
                   )

    def test_literal_at_end(self):
        self.check(b'search', [b'TEXT', b'\xfe\xff'],
                   b'tag UID SEARCH TEXT {2}\r\n'
                   b'\xfe\xff\r\n'
                   )

    def test_embedded_literal(self):
        self.check(b'search', [b'TEXT', b'\xfe\xff', b'DELETED'],
                   b'tag UID SEARCH TEXT {2}\r\n'
                   b'\xfe\xff DELETED\r\n'
                   )

    def test_multiple_literals(self):
        self.check(b'search', [b'TEXT', b'\xfe\xff', b'TEXT', b'\xcc'],
                   b'tag UID SEARCH TEXT {2}\r\n'
                   b'\xfe\xff TEXT {1}\r\n'
                   b'\xcc\r\n'
                   )

    def test_complex(self):
        self.check(b'search', [b'FLAGGED', b'TEXT', b'\xfe\xff', b'TEXT', b'\xcc', b'TEXT', b'foo'],
                   b'tag UID SEARCH FLAGGED TEXT {2}\r\n'
                   b'\xfe\xff TEXT {1}\r\n'
                   b'\xcc TEXT foo\r\n'
                   )

    def test_invalid_input_type(self):
        self.assertRaises(ValueError, self.client._raw_command, 'foo', [])
        self.assertRaises(ValueError, self.client._raw_command, u'foo', ['foo'])

    def test_failed_continuation_wait(self):
        self.client._imap._get_response.return_value = b'blah'
        self.client._imap.tagged_commands['tag'] = ('NO', ['go away'])

        expected_error = "unexpected response while waiting for continuation response: \(u?'NO', \[u?'go away'\]\)"
        with self.assertRaisesRegex(IMAPClient.AbortError, expected_error):
            self.client._raw_command(b'FOO', [b'\xff'])


class TestShutdown(IMAPClientTest):

    def test_shutdown(self):
        self.client.shutdown()
        self.client._imap.shutdown.assert_called_once_with()

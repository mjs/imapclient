# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import io
import itertools
import logging
import socket
import sys
import warnings
from datetime import datetime
from select import POLLIN
from unittest.mock import Mock, patch, sentinel

from imapclient.exceptions import CapabilityError, IMAPClientError, ProtocolError
from imapclient.fixed_offset import FixedOffset
from imapclient.imapclient import (
    _literal,
    _parse_quota,
    IMAPlibLoggerAdapter,
    MailboxQuotaRoots,
    Quota,
    require_capability,
)
from imapclient.testable_imapclient import TestableIMAPClient as IMAPClient

from .imapclient_test import IMAPClientTest


class TestListFolders(IMAPClientTest):
    def test_list_folders(self):
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            sentinel.folder_data,
        )
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_folders("foo", "bar")

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'"foo"', b'"bar"'
        )
        self.assertEqual(
            self.client._proc_folder_list.call_args, ((sentinel.folder_data,), {})
        )
        self.assertTrue(folders is sentinel.folder_list)

    def test_list_sub_folders(self):
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LSUB",
            sentinel.folder_data,
        )
        self.client._proc_folder_list = Mock(return_value=sentinel.folder_list)

        folders = self.client.list_sub_folders("foo", "bar")

        self.client._imap._simple_command.assert_called_once_with(
            "LSUB", b'"foo"', b'"bar"'
        )
        self.assertEqual(
            self.client._proc_folder_list.call_args, ((sentinel.folder_data,), {})
        )
        self.assertTrue(folders is sentinel.folder_list)

    def test_list_folders_NO(self):
        self.client._imap._simple_command.return_value = ("NO", [b"badness"])
        self.assertRaises(IMAPClientError, self.client.list_folders)

    def test_list_sub_folders_NO(self):
        self.client._imap._simple_command.return_value = ("NO", [b"badness"])
        self.assertRaises(IMAPClientError, self.client.list_folders)

    def test_utf7_decoding(self):
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ],
        )

        folders = self.client.list_folders("foo", "bar")

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'"foo"', b'"bar"'
        )
        self.assertEqual(
            folders,
            [
                ((b"\\HasNoChildren",), b"/", "A"),
                ((b"\\HasNoChildren",), b"/", "Hello\xffworld"),
            ],
        )

    def test_folder_encode_off(self):
        self.client.folder_encode = False
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Hello&AP8-world"',
            ],
        )

        folders = self.client.list_folders("foo", "bar")

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", '"foo"', '"bar"'
        )
        self.assertEqual(
            folders,
            [
                ((b"\\HasNoChildren",), b"/", b"A"),
                ((b"\\HasNoChildren",), b"/", b"Hello&AP8-world"),
            ],
        )

    def test_simple(self):
        folders = self.client._proc_folder_list(
            [
                b'(\\HasNoChildren) "/" "A"',
                b'(\\HasNoChildren) "/" "Foo Bar"',
            ]
        )
        self.assertEqual(
            folders,
            [
                (
                    (b"\\HasNoChildren",),
                    b"/",
                    "A",
                ),
                ((b"\\HasNoChildren",), b"/", "Foo Bar"),
            ],
        )

    def test_without_quotes(self):
        folders = self.client._proc_folder_list(
            [
                b'(\\HasNoChildren) "/" A',
                b'(\\HasNoChildren) "/" B',
                b'(\\HasNoChildren) "/" C',
            ]
        )
        self.assertEqual(
            folders,
            [
                ((b"\\HasNoChildren",), b"/", "A"),
                ((b"\\HasNoChildren",), b"/", "B"),
                ((b"\\HasNoChildren",), b"/", "C"),
            ],
        )

    def test_unquoted_numeric_folder_name(self):
        # Some IMAP implementations do this
        folders = self.client._proc_folder_list([b'(\\HasNoChildren) "/" 123'])
        self.assertEqual(folders, [((b"\\HasNoChildren",), b"/", "123")])

    def test_unquoted_numeric_folder_name_parsed_as_long(self):
        # big enough numeric values might get parsed as longs
        folder_name = str(sys.maxsize + 1)
        folders = self.client._proc_folder_list(
            [b'(\\HasNoChildren) "/" ' + folder_name.encode("ascii")]
        )
        self.assertEqual(folders, [((b"\\HasNoChildren",), b"/", folder_name)])

    def test_mixed(self):
        folders = self.client._proc_folder_list(
            [
                b'(\\HasNoChildren) "/" Alpha',
                b'(\\HasNoChildren) "/" "Foo Bar"',
                b'(\\HasNoChildren) "/" C',
            ]
        )
        self.assertEqual(
            folders,
            [
                ((b"\\HasNoChildren",), b"/", "Alpha"),
                ((b"\\HasNoChildren",), b"/", "Foo Bar"),
                ((b"\\HasNoChildren",), b"/", "C"),
            ],
        )

    def test_funky_characters(self):
        folders = self.client._proc_folder_list(
            [
                (b'(\\NoInferiors \\UnMarked) "/" {5}', "bang\xff"),
                b"",
                b'(\\HasNoChildren \\UnMarked) "/" "INBOX"',
            ]
        )
        self.assertEqual(
            folders,
            [
                ((b"\\NoInferiors", b"\\UnMarked"), b"/", "bang\xff"),
                ((b"\\HasNoChildren", b"\\UnMarked"), b"/", "INBOX"),
            ],
        )

    def test_quoted_specials(self):
        folders = self.client._proc_folder_list(
            [
                rb'(\HasNoChildren) "/" "Test \"Folder\""',
                rb'(\HasNoChildren) "/" "Left\"Right"',
                rb'(\HasNoChildren) "/" "Left\\Right"',
                rb'(\HasNoChildren) "/" "\"Left Right\""',
                rb'(\HasNoChildren) "/" "\"Left\\Right\""',
            ]
        )
        self.assertEqual(
            folders,
            [
                ((b"\\HasNoChildren",), b"/", 'Test "Folder"'),
                ((b"\\HasNoChildren",), b"/", 'Left"Right'),
                ((b"\\HasNoChildren",), b"/", r"Left\Right"),
                ((b"\\HasNoChildren",), b"/", r'"Left Right"'),
                ((b"\\HasNoChildren",), b"/", r'"Left\Right"'),
            ],
        )

    def test_empty_response(self):
        self.assertEqual(self.client._proc_folder_list([None]), [])

    def test_blanks(self):
        folders = self.client._proc_folder_list(
            ["", None, rb'(\HasNoChildren) "/" "last"']
        )
        self.assertEqual(folders, [((rb"\HasNoChildren",), b"/", "last")])


class TestFindSpecialFolder(IMAPClientTest):
    def test_find_special_folder_with_special_use(self):
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren) "/" "INBOX"',
                b'(\\HasNoChildren \\Sent) "/" "Sent"',
            ],
        )

        folder = self.client.find_special_folder(b"\\Sent")

        self.assertEqual(folder, "Sent")

    def test_find_special_folder_with_special_use_single_flag(self):
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren) "/" "INBOX"',
                b'(\\Sent) "/" "Sent"',
            ],
        )

        folder = self.client.find_special_folder(b"\\Sent")

        self.assertEqual(folder, "Sent")

    def test_find_special_folder_without_special_use_nor_namespace(self):
        self.client._cached_capabilities = (b"FOO",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren) "/" "Sent Items"',
            ],
        )

        folder = self.client.find_special_folder(b"\\Sent")

        self.assertEqual(folder, "Sent Items")


class TestSpecialUseFolders(IMAPClientTest):
    def test_list_special_folders_capability_required(self):
        """Test that SPECIAL-USE capability is required."""
        self.client._cached_capabilities = (b"IMAP4REV1",)
        self.assertRaises(CapabilityError, self.client.list_special_folders)

    def test_list_special_folders_basic(self):
        """Test basic special folder listing."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Drafts) "/" "INBOX.Drafts"',
                b'(\\HasNoChildren \\Sent) "/" "INBOX.Sent"',
                b'(\\HasNoChildren \\Archive) "/" "INBOX.Archive"',
            ],
        )

        folders = self.client.list_special_folders()

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'""', b'"*"', "RETURN", "(SPECIAL-USE)"
        )
        self.assertEqual(len(folders), 3)
        self.assertEqual(folders[0], ((b"\\HasNoChildren", b"\\Drafts"), b"/", "INBOX.Drafts"))
        self.assertEqual(folders[1], ((b"\\HasNoChildren", b"\\Sent"), b"/", "INBOX.Sent"))
        self.assertEqual(folders[2], ((b"\\HasNoChildren", b"\\Archive"), b"/", "INBOX.Archive"))

    def test_list_special_folders_with_params(self):
        """Test list_special_folders with directory and pattern parameters."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Trash) "/" "INBOX.Trash"',
            ],
        )

        folders = self.client.list_special_folders("INBOX", "T*")

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'"INBOX"', b'"T*"', "RETURN", "(SPECIAL-USE)"
        )
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0], ((b"\\HasNoChildren", b"\\Trash"), b"/", "INBOX.Trash"))

    def test_list_special_folders_server_response_empty(self):
        """Test list_special_folders with empty server response."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = ("LIST", [None])

        folders = self.client.list_special_folders()

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'""', b'"*"', "RETURN", "(SPECIAL-USE)"
        )
        self.assertEqual(folders, [])

    def test_list_special_folders_server_response_multiple_attributes(self):
        """Test parsing of server responses with multiple special-use attributes."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Sent \\Archive) "/" "Multi-Purpose"',
                b'(\\Trash) "/" "Trash"',
            ],
        )

        folders = self.client.list_special_folders()

        self.assertEqual(len(folders), 2)
        self.assertEqual(folders[0], ((b"\\HasNoChildren", b"\\Sent", b"\\Archive"), b"/", "Multi-Purpose"))
        self.assertEqual(folders[1], ((b"\\Trash",), b"/", "Trash"))

    def test_list_special_folders_imap_command_failed(self):
        """Test list_special_folders handles IMAP command failures."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("NO", [b"Command failed"])

        self.assertRaises(IMAPClientError, self.client.list_special_folders)

    def test_find_special_folder_uses_rfc6154_when_available(self):
        """Test that find_special_folder uses RFC 6154 when SPECIAL-USE capability exists."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Sent) "/" "Sent Messages"',
            ],
        )

        folder = self.client.find_special_folder(b"\\Sent")

        # Should call LIST with SPECIAL-USE extension, not regular LIST
        self.client._imap._simple_command.assert_called_once_with(
            "LIST", b'""', b'"*"', "RETURN", "(SPECIAL-USE)"
        )
        self.assertEqual(folder, "Sent Messages")

    def test_find_special_folder_fallback_without_capability(self):
        """Test find_special_folder falls back to list_folders when no SPECIAL-USE."""
        self.client._cached_capabilities = (b"IMAP4REV1",)  # No SPECIAL-USE
        
        # First call: list_folders() - looks for folders by attributes
        # Second call: list_folders(pattern="Sent") - looks for folders by name
        call_count = 0
        def mock_simple_command(cmd, *args):
            nonlocal call_count
            call_count += 1
            return ("OK", [b"something"])
        
        def mock_untagged_response(typ, dat, cmd):
            if call_count == 1:
                # First call returns no folders with \Sent attribute
                return ("LIST", [b'(\\HasNoChildren) "/" "INBOX"'])
            else:
                # Second call (by name pattern) returns "Sent Items"
                return ("LIST", [b'(\\HasNoChildren) "/" "Sent Items"'])
        
        self.client._imap._simple_command.side_effect = mock_simple_command
        self.client._imap._untagged_response.side_effect = mock_untagged_response

        folder = self.client.find_special_folder(b"\\Sent")

        # Should call regular LIST command without SPECIAL-USE (twice - by attributes then by name)
        self.assertEqual(self.client._imap._simple_command.call_count, 2)
        self.client._imap._simple_command.assert_any_call("LIST", b'""', b'"*"')
        self.client._imap._simple_command.assert_any_call("LIST", b'""', b'"Sent"')
        self.assertEqual(folder, "Sent Items")

    def test_list_special_folders_with_folder_encoding_disabled(self):
        """Test list_special_folders with folder_encode disabled."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client.folder_encode = False
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Sent) "/" "Hello&AP8-world"',
            ],
        )

        folders = self.client.list_special_folders()

        self.client._imap._simple_command.assert_called_once_with(
            "LIST", '""', '"*"', "RETURN", "(SPECIAL-USE)"
        )
        self.assertEqual(len(folders), 1)
        # Name should remain as bytes when folder_encode is False
        self.assertEqual(folders[0], ((b"\\HasNoChildren", b"\\Sent"), b"/", b"Hello&AP8-world"))

    def test_list_special_folders_with_utf7_decoding(self):
        """Test list_special_folders with UTF-7 folder name decoding."""
        self.client._cached_capabilities = (b"SPECIAL-USE",)
        self.client._imap._simple_command.return_value = ("OK", [b"something"])
        self.client._imap._untagged_response.return_value = (
            "LIST",
            [
                b'(\\HasNoChildren \\Sent) "/" "Hello&AP8-world"',
            ],
        )

        folders = self.client.list_special_folders()

        self.assertEqual(len(folders), 1)
        # Name should be decoded from UTF-7 when folder_encode is True (default)
        self.assertEqual(folders[0], ((b"\\HasNoChildren", b"\\Sent"), b"/", "Hello\xffworld"))


class TestSelectFolder(IMAPClientTest):
    def test_normal(self):
        self.client._command_and_check = Mock()
        self.client._imap.untagged_responses = {
            b"exists": [b"3"],
            b"FLAGS": [rb"(\Flagged \Deleted abc [foo]/bar def)"],
            b"HIGHESTMODSEQ": [b"127110"],
            b"OK": [
                rb"[PERMANENTFLAGS (\Flagged \Deleted abc [foo]/bar def \*)] Flags permitted.",
                b"[UIDVALIDITY 631062293] UIDs valid.",
                b"[UIDNEXT 1281] Predicted next UID.",
                b"[HIGHESTMODSEQ 127110]",
            ],
            b"PERMANENTFLAGS": [rb"(\Flagged \Deleted abc [foo"],
            b"READ-WRITE": [b""],
            b"RECENT": [b"0"],
            b"UIDNEXT": [b"1281"],
            b"UIDVALIDITY": [b"631062293"],
            b"OTHER": [b"blah"],
        }

        result = self.client.select_folder(b"folder_name", sentinel.readonly)

        self.client._command_and_check.assert_called_once_with(
            "select", b'"folder_name"', sentinel.readonly
        )
        self.maxDiff = 99999
        self.assertEqual(
            result,
            {
                b"EXISTS": 3,
                b"RECENT": 0,
                b"UIDNEXT": 1281,
                b"UIDVALIDITY": 631062293,
                b"HIGHESTMODSEQ": 127110,
                b"FLAGS": (rb"\Flagged", rb"\Deleted", b"abc", b"[foo]/bar", b"def"),
                b"PERMANENTFLAGS": (
                    rb"\Flagged",
                    rb"\Deleted",
                    b"abc",
                    b"[foo]/bar",
                    b"def",
                    rb"\*",
                ),
                b"READ-WRITE": True,
                b"OTHER": [b"blah"],
            },
        )

    def test_unselect(self):
        self.client._cached_capabilities = [b"UNSELECT"]
        self.client._imap._simple_command.return_value = ("OK", ["Unselect completed."])
        # self.client._imap._untagged_response.return_value = (
        #    b'OK', [b'("name" "GImap" "vendor" "Google, Inc.")'])

        result = self.client.unselect_folder()
        self.assertEqual(result, "Unselect completed.")
        self.client._imap._simple_command.assert_called_with("UNSELECT")


class TestAppend(IMAPClientTest):
    def test_without_msg_time(self):
        self.client._imap.append.return_value = ("OK", [b"Good"])
        msg = "hi"

        self.client.append("foobar", msg, ["FLAG", "WAVE"], None)

        self.client._imap.append.assert_called_with(
            b'"foobar"', "(FLAG WAVE)", None, b"hi"
        )

    @patch("imapclient.imapclient.datetime_to_INTERNALDATE")
    def test_with_msg_time(self, datetime_to_INTERNALDATE):
        datetime_to_INTERNALDATE.return_value = "somedate"
        self.client._imap.append.return_value = ("OK", [b"Good"])
        msg = b"bye"

        self.client.append(
            "foobar",
            msg,
            ["FLAG", "WAVE"],
            datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2 * 60)),
        )

        self.assertTrue(datetime_to_INTERNALDATE.called)
        self.client._imap.append.assert_called_with(
            b'"foobar"', "(FLAG WAVE)", '"somedate"', msg
        )

    def test_multiappend(self):
        self.client._cached_capabilities = (b"MULTIAPPEND",)
        self.client._raw_command = Mock()
        self.client.multiappend("foobar", ["msg1", "msg2"])

        self.client._raw_command.assert_called_once_with(
            b"APPEND", [b'"foobar"', b"msg1", b"msg2"], uid=False
        )

    def test_multiappend_with_flags_and_internaldate(self):
        self.client._cached_capabilities = (b"MULTIAPPEND",)
        self.client._raw_command = Mock()
        self.client.multiappend(
            "foobar",
            [
                {
                    "msg": "msg1",
                    "flags": ["FLAG", "WAVE"],
                    "date": datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2 * 60)),
                },
                {
                    "msg": "msg2",
                    "flags": ["FLAG", "WAVE"],
                },
                {
                    "msg": "msg3",
                    "date": datetime(2009, 4, 5, 11, 0, 5, 0, FixedOffset(2 * 60)),
                },
            ],
        )

        self.client._raw_command.assert_called_once_with(
            b"APPEND",
            [
                b'"foobar"',
                b"(FLAG WAVE)",
                b'"05-Apr-2009 11:00:05 +0200"',
                _literal(b"msg1"),
                b"(FLAG WAVE)",
                _literal(b"msg2"),
                b'"05-Apr-2009 11:00:05 +0200"',
                _literal(b"msg3"),
            ],
            uid=False,
        )


class TestAclMethods(IMAPClientTest):
    def setUp(self):
        super(TestAclMethods, self).setUp()
        self.client._cached_capabilities = [b"ACL"]

    def test_getacl(self):
        self.client._imap.getacl.return_value = (
            "OK",
            [b"INBOX Fred rwipslda Sally rwip"],
        )
        acl = self.client.getacl("INBOX")
        self.assertSequenceEqual(acl, [(b"Fred", b"rwipslda"), (b"Sally", b"rwip")])

    def test_setacl(self):
        self.client._imap.setacl.return_value = ("OK", [b"SETACL done"])

        response = self.client.setacl("folder", sentinel.who, sentinel.what)

        self.client._imap.setacl.assert_called_with(
            b'"folder"', sentinel.who, sentinel.what
        )
        self.assertEqual(response, b"SETACL done")


class TestQuota(IMAPClientTest):
    def setUp(self):
        super(TestQuota, self).setUp()
        self.client._cached_capabilities = [b"QUOTA"]

    def test_parse_quota(self):
        self.assertEqual(_parse_quota([]), [])
        self.assertEqual(
            _parse_quota([b'"User quota" (STORAGE 586720 4882812)']),
            [Quota("User quota", "STORAGE", 586720, 4882812)],
        )
        self.assertEqual(
            _parse_quota(
                [
                    b'"User quota" (STORAGE 586720 4882812)',
                    b'"Global quota" (MESSAGES 42 1000)',
                ]
            ),
            [
                Quota("User quota", "STORAGE", 586720, 4882812),
                Quota("Global quota", "MESSAGES", 42, 1000),
            ],
        )
        self.assertEqual(
            _parse_quota(
                [
                    b'"User quota" (STORAGE 586720 4882812 MESSAGES 42 1000)',
                ]
            ),
            [
                Quota("User quota", "STORAGE", 586720, 4882812),
                Quota("User quota", "MESSAGES", 42, 1000),
            ],
        )

    def test__get_quota(self):
        self.client._command_and_check = Mock()
        self.client._command_and_check.return_value = [
            b'"User quota" (MESSAGES 42 1000)'
        ]

        quotas = self.client._get_quota("foo")

        self.client._command_and_check.assert_called_once_with("getquota", '"foo"')
        self.assertEqual(quotas, [Quota("User quota", "MESSAGES", 42, 1000)])

    def test_set_quota(self):
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = [
            b'"User quota" (STORAGE 42 1000 MESSAGES 42 1000)'
        ]
        quotas = [
            Quota("User quota", "STORAGE", 42, 1000),
            Quota("User quota", "MESSAGES", 42, 1000),
        ]
        resp = self.client.set_quota(quotas)

        self.client._raw_command_untagged.assert_called_once_with(
            b"SETQUOTA",
            [b'"User quota"', b"(STORAGE 1000 MESSAGES 1000)"],
            uid=False,
            response_name="QUOTA",
        )
        self.assertListEqual(resp, quotas)

    def test_get_quota_root(self):
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = [b'"INBOX" "User quota"']
        self.client._imap.untagged_responses = dict()

        resp = self.client.get_quota_root("INBOX")

        self.client._raw_command_untagged.assert_called_once_with(
            b"GETQUOTAROOT", b"INBOX", uid=False, response_name="QUOTAROOT"
        )
        expected = (MailboxQuotaRoots("INBOX", ["User quota"]), list())
        self.assertTupleEqual(resp, expected)

        resp = self.client.get_quota("INBOX")
        self.assertEqual(resp, [])


class TestIdleAndNoop(IMAPClientTest):
    def setUp(self):
        super(TestIdleAndNoop, self).setUp()
        self.client._cached_capabilities = [b"IDLE"]

    def assert_sock_select_calls(self, sock):
        self.assertListEqual(
            sock.method_calls,
            [
                ("settimeout", (None,), {}),
                ("setblocking", (0,), {}),
                ("setblocking", (1,), {}),
                ("settimeout", (None,), {}),
            ],
        )

    def assert_sock_poll_calls(self, sock):
        self.assertListEqual(
            sock.method_calls,
            [
                ("settimeout", (None,), {}),
                ("setblocking", (0,), {}),
                ("fileno", (), {}),
                ("setblocking", (1,), {}),
                ("settimeout", (None,), {}),
            ],
        )

    def test_idle(self):
        self.client._imap._command.return_value = sentinel.tag
        self.client._imap._get_response.return_value = None

        self.client.idle()

        self.client._imap._command.assert_called_with("IDLE")
        self.assertEqual(self.client._idle_tag, sentinel.tag)

    @patch("imapclient.imapclient.POLL_SUPPORT", False)
    @patch("imapclient.imapclient.select.select")
    def test_idle_check_blocking(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([True], [], [])
        counter = itertools.count()

        def fake_get_line():
            count = next(counter)
            if count == 0:
                return b"* 1 EXISTS"
            elif count == 1:
                return b"* 0 EXPUNGE"
            else:
                raise socket.timeout

        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        mock_select.assert_called_once_with([mock_sock], [], [], None)
        self.assert_sock_select_calls(mock_sock)
        self.assertListEqual([(1, b"EXISTS"), (0, b"EXPUNGE")], responses)

    @patch("imapclient.imapclient.POLL_SUPPORT", False)
    @patch("imapclient.imapclient.select.select")
    def test_idle_check_timeout(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([], [], [])

        responses = self.client.idle_check(timeout=0.5)

        mock_select.assert_called_once_with([mock_sock], [], [], 0.5)
        self.assert_sock_select_calls(mock_sock)
        self.assertListEqual([], responses)

    @patch("imapclient.imapclient.POLL_SUPPORT", False)
    @patch("imapclient.imapclient.select.select")
    def test_idle_check_with_data(self, mock_select):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        mock_select.return_value = ([True], [], [])
        counter = itertools.count()

        def fake_get_line():
            count = next(counter)
            if count == 0:
                return b"* 99 EXISTS"
            else:
                raise socket.timeout

        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        mock_select.assert_called_once_with([mock_sock], [], [], None)
        self.assert_sock_select_calls(mock_sock)
        self.assertListEqual([(99, b"EXISTS")], responses)

    @patch("imapclient.imapclient.POLL_SUPPORT", True)
    @patch("imapclient.imapclient.select.poll")
    def test_idle_check_blocking_poll(self, mock_poll_module):
        mock_sock = Mock(fileno=Mock(return_value=1))
        self.client._imap.sock = self.client._imap.sslobj = mock_sock

        mock_poller = Mock(poll=Mock(return_value=[(1, POLLIN)]))
        mock_poll_module.return_value = mock_poller
        counter = itertools.count()

        def fake_get_line():
            count = next(counter)
            if count == 0:
                return b"* 1 EXISTS"
            elif count == 1:
                return b"* 0 EXPUNGE"
            else:
                raise socket.timeout

        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        assert mock_poll_module.call_count == 1
        mock_poller.register.assert_called_once_with(1, POLLIN)
        mock_poller.poll.assert_called_once_with(None)
        self.assert_sock_poll_calls(mock_sock)
        self.assertListEqual([(1, b"EXISTS"), (0, b"EXPUNGE")], responses)

    @patch("imapclient.imapclient.POLL_SUPPORT", True)
    @patch("imapclient.imapclient.select.poll")
    def test_idle_check_timeout_poll(self, mock_poll_module):
        mock_sock = Mock(fileno=Mock(return_value=1))
        self.client._imap.sock = self.client._imap.sslobj = mock_sock

        mock_poller = Mock(poll=Mock(return_value=[]))
        mock_poll_module.return_value = mock_poller

        responses = self.client.idle_check(timeout=0.5)

        assert mock_poll_module.call_count == 1
        mock_poller.register.assert_called_once_with(1, POLLIN)
        mock_poller.poll.assert_called_once_with(500)
        self.assert_sock_poll_calls(mock_sock)
        self.assertListEqual([], responses)

    @patch("imapclient.imapclient.POLL_SUPPORT", True)
    @patch("imapclient.imapclient.select.poll")
    def test_idle_check_with_data_poll(self, mock_poll_module):
        mock_sock = Mock(fileno=Mock(return_value=1))
        self.client._imap.sock = self.client._imap.sslobj = mock_sock

        mock_poller = Mock(poll=Mock(return_value=[(1, POLLIN)]))
        mock_poll_module.return_value = mock_poller
        counter = itertools.count()

        def fake_get_line():
            count = next(counter)
            if count == 0:
                return b"* 99 EXISTS"
            else:
                raise socket.timeout

        self.client._imap._get_line = fake_get_line

        responses = self.client.idle_check()

        assert mock_poll_module.call_count == 1
        mock_poller.register.assert_called_once_with(1, POLLIN)
        mock_poller.poll.assert_called_once_with(None)
        self.assert_sock_poll_calls(mock_sock)
        self.assertListEqual([(99, b"EXISTS")], responses)

    def test_idle_done(self):
        self.client._idle_tag = sentinel.tag

        mockSend = Mock()
        self.client._imap.send = mockSend
        mockConsume = Mock(return_value=sentinel.out)
        self.client._consume_until_tagged_response = mockConsume

        result = self.client.idle_done()

        mockSend.assert_called_with(b"DONE\r\n")
        mockConsume.assert_called_with(sentinel.tag, "IDLE")
        self.assertEqual(result, sentinel.out)

    def test_noop(self):
        mockCommand = Mock(return_value=sentinel.tag)
        self.client._imap._command = mockCommand
        mockConsume = Mock(return_value=sentinel.out)
        self.client._consume_until_tagged_response = mockConsume

        result = self.client.noop()

        mockCommand.assert_called_with("NOOP")
        mockConsume.assert_called_with(sentinel.tag, "NOOP")
        self.assertEqual(result, sentinel.out)

    def test_consume_until_tagged_response(self):
        client = self.client
        client._imap.tagged_commands = {sentinel.tag: None}

        counter = itertools.count()

        def fake_get_response():
            count = next(counter)
            if count == 0:
                return b"* 99 EXISTS"
            client._imap.tagged_commands[sentinel.tag] = ("OK", [b"Idle done"])

        client._imap._get_response = fake_get_response

        text, responses = client._consume_until_tagged_response(sentinel.tag, b"IDLE")
        self.assertEqual(client._imap.tagged_commands, {})
        self.assertEqual(text, b"Idle done")
        self.assertListEqual([(99, b"EXISTS")], responses)


class TestDebugLogging(IMAPClientTest):
    def test_IMAP_is_patched(self):
        # Remove all logging handlers so that the order of tests does not
        # prevent basicConfig from being executed
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        log_stream = io.StringIO()
        logging.basicConfig(stream=log_stream, level=logging.DEBUG)

        self.client._imap._mesg("two")
        self.assertIn("DEBUG:imapclient.imaplib:two", log_stream.getvalue())

    def test_redacted_password(self):
        logger_mock = Mock()
        logger_mock.manager.disable = logging.DEBUG
        logger_mock.getEffectiveLevel.return_value = logging.DEBUG

        adapter = IMAPlibLoggerAdapter(logger_mock, dict())
        adapter.info("""> b'ICHH1 LOGIN foo@bar.org "secret"'""")
        if sys.version_info >= (3, 6, 4):
            # LoggerAdapter in Python 3.6.4+ calls logger.log()
            logger_mock.log.assert_called_once_with(
                logging.INFO, "> b'ICHH1 LOGIN **REDACTED**", extra={}
            )
        else:
            # LoggerAdapter in Python 3.4 to 3.6 calls logger._log()
            logger_mock._log.assert_called_once_with(
                logging.INFO, "> b'ICHH1 LOGIN **REDACTED**", (), extra={}
            )


class TestTimeNormalisation(IMAPClientTest):
    def test_default(self):
        self.assertTrue(self.client.normalise_times)

    @patch("imapclient.imapclient.parse_fetch_response")
    def test_pass_through(self, parse_fetch_response):
        self.client._imap._command_complete.return_value = ("OK", sentinel.data)
        self.client._imap._untagged_response.return_value = ("OK", sentinel.fetch_data)
        self.client.use_uid = sentinel.use_uid

        def check(expected):
            self.client.fetch(22, ["SOMETHING"])
            parse_fetch_response.assert_called_with(
                sentinel.fetch_data, expected, sentinel.use_uid
            )

        self.client.normalise_times = True
        check(True)

        self.client.normalise_times = False
        check(False)


class TestNamespace(IMAPClientTest):
    def setUp(self):
        super(TestNamespace, self).setUp()
        self.client._cached_capabilities = [b"NAMESPACE"]

    def set_return(self, value):
        self.client._imap.namespace.return_value = ("OK", [value])

    def test_simple(self):
        self.set_return(b'(("FOO." "/")) NIL NIL')
        self.assertEqual(self.client.namespace(), ((("FOO.", "/"),), None, None))

    def test_folder_decoding(self):
        self.set_return(b'(("&AP8-." "/")) NIL NIL')
        self.assertEqual(self.client.namespace(), ((("\xff.", "/"),), None, None))

    def test_without_folder_decoding(self):
        self.set_return(b'(("&AP8-." "/")) NIL NIL')
        self.client.folder_encode = False
        self.assertEqual(self.client.namespace(), (((b"&AP8-.", "/"),), None, None))

    def test_other_only(self):
        self.set_return(b'NIL NIL (("" "."))')
        self.assertEqual(self.client.namespace(), (None, None, (("", "."),)))

    def test_complex(self):
        self.set_return(
            b'(("" "/")) '
            b'(("~" "/")) '
            b'(("#shared/" "/") ("#public/" "/")("#ftp/" "/")("#news." "."))'
        )
        self.assertEqual(
            self.client.namespace(),
            (
                (("", "/"),),
                (("~", "/"),),
                (("#shared/", "/"), ("#public/", "/"), ("#ftp/", "/"), ("#news.", ".")),
            ),
        )


class TestCapabilities(IMAPClientTest):
    def test_preauth(self):
        self.client._imap.capabilities = ("FOO", "BAR")
        self.client._imap.untagged_responses = {}

        self.assertEqual(self.client.capabilities(), (b"FOO", b"BAR"))

    def test_server_returned_capability_after_auth(self):
        self.client._imap.capabilities = (b"FOO",)
        self.client._imap.untagged_responses = {"CAPABILITY": [b"FOO MORE"]}

        self.assertEqual(self.client._cached_capabilities, None)
        self.assertEqual(self.client.capabilities(), (b"FOO", b"MORE"))
        self.assertEqual(self.client._cached_capabilities, (b"FOO", b"MORE"))
        self.assertEqual(self.client._imap.untagged_responses, {})

    def test_caching(self):
        self.client._imap.capabilities = ("FOO",)
        self.client._imap.untagged_responses = {}
        self.client._cached_capabilities = (b"FOO", b"MORE")

        self.assertEqual(self.client.capabilities(), (b"FOO", b"MORE"))

    def test_post_auth_request(self):
        self.client._imap.capabilities = ("FOO",)
        self.client._imap.untagged_responses = {}
        self.client._imap.state = "SELECTED"
        self.client._imap.capability.return_value = ("OK", [b"FOO BAR"])

        self.assertEqual(self.client.capabilities(), (b"FOO", b"BAR"))
        self.assertEqual(self.client._cached_capabilities, (b"FOO", b"BAR"))

    def test_with_starttls(self):
        # Initial connection
        self.client._imap.capabilities = ("FOO",)
        self.client._imap.untagged_responses = {}
        self.client._imap.state = "NONAUTH"
        self.assertEqual(self.client.capabilities(), (b"FOO",))

        # Now do STARTTLS; capabilities change and should be reported.
        self.client._starttls_done = True
        self.client._imap.capability.return_value = ("OK", [b"FOO BAR"])
        self.assertEqual(self.client.capabilities(), (b"FOO", b"BAR"))

        # Login done; capabilities change again.
        self.client._imap.state = "AUTH"
        self.client._imap.capability.return_value = ("OK", [b"FOO BAR QUX"])
        self.assertEqual(self.client.capabilities(), (b"FOO", b"BAR", b"QUX"))

    def test_has_capability(self):
        self.client._cached_capabilities = (b"FOO", b"MORE")

        self.assertTrue(self.client.has_capability(b"FOO"))
        self.assertTrue(self.client.has_capability(b"foo"))
        self.assertFalse(self.client.has_capability(b"BAR"))

        self.assertTrue(self.client.has_capability("FOO"))
        self.assertTrue(self.client.has_capability("foo"))
        self.assertFalse(self.client.has_capability("BAR"))

    def test_decorator(self):
        class Foo(object):
            def has_capability(self, capability):
                if capability == "TRUE":
                    return True
                return False

            @require_capability("TRUE")
            def yes(self):
                return True

            @require_capability("FALSE")
            def no(self):
                return False

        foo = Foo()
        self.assertTrue(foo.yes())
        self.assertRaises(CapabilityError, foo.no)


class TestId(IMAPClientTest):
    def setUp(self):
        super(TestId, self).setUp()
        self.client._cached_capabilities = [b"ID"]

    def test_id(self):
        self.client._imap._simple_command.return_value = ("OK", [b"Success"])
        self.client._imap._untagged_response.return_value = (
            b"OK",
            [b'("name" "GImap" "vendor" "Google, Inc.")'],
        )

        id_response = self.client.id_({"name": "IMAPClient"})
        self.client._imap._simple_command.assert_called_with(
            "ID", '("name" "IMAPClient")'
        )

        self.assertSequenceEqual(
            id_response, ((b"name", b"GImap", b"vendor", b"Google, Inc."),)
        )

    def test_no_support(self):
        self.client._cached_capabilities = (b"IMAP4rev1",)
        self.assertRaises(CapabilityError, self.client.id_)

    def test_invalid_parameters(self):
        self.assertRaises(TypeError, self.client.id_, "bananarama")


class TestRawCommand(IMAPClientTest):
    def setUp(self):
        super(TestRawCommand, self).setUp()
        self.client._imap._get_response.return_value = None
        self.client._imap._command_complete.return_value = ("OK", ["done"])
        self.client._cached_capabilities = ()

    def check(self, command, args, expected):
        typ, data = self.client._raw_command(command, args)
        self.assertEqual(typ, "OK")
        self.assertEqual(data, ["done"])
        self.assertEqual(self.client._imap.sent, expected)

    def test_plain(self):
        self.check(
            b"search",
            [b"ALL"],
            b"tag UID SEARCH ALL\r\n",
        )

    def test_not_uid(self):
        self.client.use_uid = False
        self.check(
            b"search",
            [b"ALL"],
            b"tag SEARCH ALL\r\n",
        )

    def test_literal_at_end(self):
        self.check(
            b"search",
            [b"TEXT", b"\xfe\xff"],
            b"tag UID SEARCH TEXT {2}\r\n" b"\xfe\xff\r\n",
        )

    def test_embedded_literal(self):
        self.check(
            b"search",
            [b"TEXT", b"\xfe\xff", b"DELETED"],
            b"tag UID SEARCH TEXT {2}\r\n" b"\xfe\xff DELETED\r\n",
        )

    def test_multiple_literals(self):
        self.check(
            b"search",
            [b"TEXT", b"\xfe\xff", b"TEXT", b"\xcc"],
            b"tag UID SEARCH TEXT {2}\r\n" b"\xfe\xff TEXT {1}\r\n" b"\xcc\r\n",
        )

    def test_literal_plus(self):
        self.client._cached_capabilities = (b"LITERAL+",)

        typ, data = self.client._raw_command(
            b"APPEND", [b"\xff", _literal(b"hello")], uid=False
        )
        self.assertEqual(typ, "OK")
        self.assertEqual(data, ["done"])
        self.assertEqual(
            self.client._imap.sent,
            b"tag APPEND {1+}\r\n" b"\xff  {5+}\r\n" b"hello\r\n",
        )

    def test_literal_plus_multiple_literals(self):
        self.client._cached_capabilities = (b"LITERAL+",)

        typ, data = self.client._raw_command(
            b"APPEND",
            [b"\xff", _literal(b"hello"), b"TEXT", _literal(b"test")],
            uid=False,
        )
        self.assertEqual(typ, "OK")
        self.assertEqual(data, ["done"])
        self.assertEqual(
            self.client._imap.sent,
            b"tag APPEND {1+}\r\n"
            b"\xff  {5+}\r\n"
            b"hello"
            b" TEXT {4+}\r\n"
            b"test\r\n",
        )

    def test_complex(self):
        self.check(
            b"search",
            [b"FLAGGED", b"TEXT", b"\xfe\xff", b"TEXT", b"\xcc", b"TEXT", b"foo"],
            b"tag UID SEARCH FLAGGED TEXT {2}\r\n"
            b"\xfe\xff TEXT {1}\r\n"
            b"\xcc TEXT foo\r\n",
        )

    def test_invalid_input_type(self):
        self.assertRaises(ValueError, self.client._raw_command, "foo", [])
        self.assertRaises(ValueError, self.client._raw_command, "foo", ["foo"])

    def test_failed_continuation_wait(self):
        self.client._imap._get_response.return_value = b"blah"
        self.client._imap.tagged_commands["tag"] = ("NO", ["go away"])

        expected_error = r"unexpected response while waiting for continuation response: \(u?'NO', \[u?'go away'\]\)"
        with self.assertRaisesRegex(IMAPClient.AbortError, expected_error):
            self.client._raw_command(b"FOO", [b"\xff"])


class TestExpunge(IMAPClientTest):
    def test_expunge(self):
        mockCommand = Mock(return_value=sentinel.tag)
        mockConsume = Mock(return_value=sentinel.out)
        self.client._imap._command = mockCommand
        self.client._consume_until_tagged_response = mockConsume
        result = self.client.expunge()
        mockCommand.assert_called_with("EXPUNGE")
        mockConsume.assert_called_with(sentinel.tag, "EXPUNGE")
        self.assertEqual(sentinel.out, result)

    def test_id_expunge(self):
        self.client._imap.uid.return_value = ("OK", [None])
        self.assertEqual([None], self.client.expunge(["4", "5", "6"]))


class TestShutdown(IMAPClientTest):
    def test_shutdown(self):
        self.client.shutdown()
        self.client._imap.shutdown.assert_called_once_with()


class TestContextManager(IMAPClientTest):
    def test_context_manager(self):
        with self.client as client:
            self.assertIsInstance(client, IMAPClient)

        self.client._imap.logout.assert_called_once_with()

    @patch("imapclient.imapclient.logger")
    def test_context_manager_fail_closing(self, mock_logger):
        self.client._imap.logout.side_effect = RuntimeError("Error logout")
        self.client._imap.shutdown.side_effect = RuntimeError("Error shutdown")

        with self.client as client:
            self.assertIsInstance(client, IMAPClient)

        self.client._imap.logout.assert_called_once_with()
        self.client._imap.shutdown.assert_called_once_with()
        mock_logger.info.assert_called_once_with(
            "Could not close the connection cleanly: %s",
            self.client._imap.shutdown.side_effect,
        )

    def test_exception_inside_context_manager(self):
        with self.assertRaises(ValueError):
            with self.client as _:
                raise ValueError("Error raised inside the context manager")


class TestProtocolError(IMAPClientTest):
    def test_tagged_response_with_parse_error(self):
        client = self.client
        client._imap.tagged_commands = {sentinel.tag: None}
        client._imap._get_response = lambda: b"NOT-A-STAR 99 EXISTS"

        with self.assertRaises(ProtocolError):
            client._consume_until_tagged_response(sentinel.tag, b"IDLE")


class TestCreateSpecialUseFolder(IMAPClientTest):
    def test_create_folder_backward_compatibility(self):
        """Test that create_folder() works unchanged without special_use parameter."""
        self.client._command_and_check = Mock()
        self.client._command_and_check.return_value = b"OK CREATE completed"
        
        result = self.client.create_folder("INBOX.TestFolder")
        
        self.client._command_and_check.assert_called_once_with(
            "create", b'"INBOX.TestFolder"', unpack=True
        )
        self.assertEqual(result, b"OK CREATE completed")

    def test_create_folder_with_special_use_capability_required(self):
        """Test CREATE-SPECIAL-USE capability requirement when special_use provided."""
        self.client._cached_capabilities = (b"IMAP4REV1",)
        
        self.assertRaises(
            CapabilityError, 
            self.client.create_folder, 
            "INBOX.TestSent", 
            special_use=b"\\Sent"
        )

    def test_create_folder_with_special_use_basic(self):
        """Test basic special-use folder creation with valid attributes."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        result = self.client.create_folder("INBOX.MySent", special_use=b"\\Sent")
        
        self.client._imap.create.assert_called_once_with(
            b'"INBOX.MySent"', b"(USE (\\Sent))"
        )
        self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_sent_constant(self):
        """Test creation with SENT RFC 6154 constant."""
        from imapclient import SENT
        
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        result = self.client.create_folder("INBOX.MySent", special_use=SENT)
        
        self.client._imap.create.assert_called_once_with(
            b'"INBOX.MySent"', b"(USE (\\Sent))"
        )
        self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_drafts_constant(self):
        """Test creation with DRAFTS RFC 6154 constant."""
        from imapclient import DRAFTS
        
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        result = self.client.create_folder("INBOX.MyDrafts", special_use=DRAFTS)
        
        self.client._imap.create.assert_called_once_with(
            b'"INBOX.MyDrafts"', b"(USE (\\Drafts))"
        )
        self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_all_rfc6154_constants(self):
        """Test creation with all RFC 6154 constants (SENT, DRAFTS, JUNK, etc.)."""
        from imapclient import ALL, ARCHIVE, DRAFTS, JUNK, SENT, TRASH
        
        test_cases = [
            (SENT, "INBOX.MySent", b"(USE (\\Sent))"),
            (DRAFTS, "INBOX.MyDrafts", b"(USE (\\Drafts))"),
            (JUNK, "INBOX.MyJunk", b"(USE (\\Junk))"),
            (ARCHIVE, "INBOX.MyArchive", b"(USE (\\Archive))"),
            (TRASH, "INBOX.MyTrash", b"(USE (\\Trash))"),
            (ALL, "INBOX.MyAll", b"(USE (\\All))"),
        ]
        
        for special_use, folder_name, expected_use_clause in test_cases:
            with self.subTest(special_use=special_use):
                self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
                self.client._imap.create = Mock()
                self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
                
                result = self.client.create_folder(folder_name, special_use=special_use)
                
                self.client._imap.create.assert_called_once_with(
                    b'"' + folder_name.encode("ascii") + b'"', expected_use_clause
                )
                self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_invalid_attribute(self):
        """Test error handling for invalid special_use attributes."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        
        with self.assertRaises(IMAPClientError) as cm:
            self.client.create_folder("INBOX.TestFolder", special_use=b"\\Invalid")
            
        self.assertIn("Invalid special_use attribute", str(cm.exception))
        self.assertIn("\\Invalid", str(cm.exception))
        self.assertIn("Must be one of", str(cm.exception))

    def test_create_folder_with_special_use_no_capability_error(self):
        """Test CapabilityError when CREATE-SPECIAL-USE not supported."""
        # Test with different capability sets that don't include CREATE-SPECIAL-USE
        capability_sets = [
            (b"IMAP4REV1",),
            (b"SPECIAL-USE",),  # Has SPECIAL-USE but not CREATE-SPECIAL-USE
            (b"IMAP4REV1", b"SPECIAL-USE"),
        ]
        
        for capabilities in capability_sets:
            with self.subTest(capabilities=capabilities):
                self.client._cached_capabilities = capabilities
                
                with self.assertRaises(CapabilityError) as cm:
                    self.client.create_folder("INBOX.TestFolder", special_use=b"\\Sent")
                
                self.assertIn("CREATE-SPECIAL-USE", str(cm.exception))

    def test_create_folder_with_special_use_imap_command_construction(self):
        """Test proper IMAP CREATE command construction with USE attribute."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        # Test with folder name that needs normalization
        result = self.client.create_folder("TestFolder", special_use=b"\\Archive")
        
        # Verify the folder name was normalized and USE clause formatted correctly
        self.client._imap.create.assert_called_once_with(
            b'"TestFolder"', b"(USE (\\Archive))"
        )
        self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_server_response_handling(self):
        """Test server response handling for successful CREATE command."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        
        # Test different server response formats
        test_responses = [
            [b"CREATE completed"],
            [b"CREATE completed successfully"],
            [b"OK Mailbox created"],
        ]
        
        for response in test_responses:
            with self.subTest(response=response):
                self.client._imap.create.return_value = ("OK", response)
                
                result = self.client.create_folder("INBOX.TestFolder", special_use=b"\\Sent")
                
                self.assertEqual(result, response[0].decode("ascii", "replace"))

    def test_create_folder_with_special_use_server_error_handling(self):
        """Test server error handling for failed CREATE command."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("NO", [b"CREATE failed - folder exists"])
        
        with self.assertRaises(IMAPClientError) as cm:
            self.client.create_folder("INBOX.TestFolder", special_use=b"\\Sent")
            
        self.assertIn("CREATE command failed", str(cm.exception))
        self.assertIn("CREATE failed - folder exists", str(cm.exception))

    def test_create_folder_with_special_use_unicode_folder_names(self):
        """Test special-use folder creation with Unicode folder names."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        # Test with Unicode folder name
        result = self.client.create_folder("INBOX.Боксы", special_use=b"\\Archive")
        
        self.client._imap.create.assert_called_once()
        # Verify folder name was properly encoded
        call_args = self.client._imap.create.call_args[0]
        self.assertIsInstance(call_args[0], bytes)
        self.assertEqual(call_args[1], b"(USE (\\Archive))")
        self.assertEqual(result, "CREATE completed")

    def test_create_folder_with_special_use_empty_folder_name(self):
        """Test behavior with empty folder name."""
        self.client._cached_capabilities = (b"CREATE-SPECIAL-USE",)
        self.client._imap.create = Mock()
        self.client._imap.create.return_value = ("OK", [b"CREATE completed"])
        
        result = self.client.create_folder("", special_use=b"\\Sent")
        
        self.client._imap.create.assert_called_once_with(
            b'""', b"(USE (\\Sent))"
        )
        self.assertEqual(result, "CREATE completed")


class TestSocket(IMAPClientTest):
    def test_issues_warning_for_deprecating_sock_property(self):
        mock_sock = Mock()
        self.client._imap.sock = self.client._imap.sslobj = mock_sock
        with warnings.catch_warnings(record=True) as warnings_caught:
            warnings.simplefilter("always", DeprecationWarning)
            assert self.client._sock == self.client.socket()
            assert len(warnings_caught) == 1

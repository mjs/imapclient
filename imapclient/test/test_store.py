# Copyright (c) 2016, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import six
from mock import patch, sentinel, Mock

from ..imapclient import DELETED, SEEN, ANSWERED, FLAGGED, DRAFT, RECENT
from .imapclient_test import IMAPClientTest


class TestFlagsConsts(IMAPClientTest):

    def test_flags_are_bytes(self):
        for flag in DELETED, SEEN, ANSWERED, FLAGGED, DRAFT, RECENT:
            if not isinstance(flag, six.binary_type):
                self.fail("%r flag is not bytes" % flag)


class TestFlags(IMAPClientTest):

    def setUp(self):
        super(TestFlags, self).setUp()
        self.client._command_and_check = Mock()

    def test_get(self):
        with patch.object(self.client, 'fetch', autospec=True,
                          return_value={123: {b'FLAGS': [b'foo', b'bar']},
                                        444: {b'FLAGS': [b'foo']}}):
            out = self.client.get_flags(sentinel.messages)
            self.client.fetch.assert_called_with(sentinel.messages, ['FLAGS'])
            self.assertEqual(out, {123: [b'foo', b'bar'],
                                   444: [b'foo']})

    def test_set(self):
        self.check(self.client.set_flags, b'FLAGS')

    def test_add(self):
        self.check(self.client.add_flags, b'+FLAGS')

    def test_remove(self):
        self.check(self.client.remove_flags, b'-FLAGS')

    def check(self, meth, expected_command):
        self._check(meth, expected_command)
        self._check(meth, expected_command, silent=True)

    def _check(self, meth, expected_command, silent=False):
        if silent:
            expected_command += b".SILENT"

        cc = self.client._command_and_check
        cc.return_value = [
            b'11 (FLAGS (blah foo) UID 1)',
            b'11 (UID 1 OTHER (dont))',
            b'22 (FLAGS (foo) UID 2)',
            b'22 (UID 2 OTHER (care))',
        ]
        resp = meth([1, 2], 'foo', silent=silent)
        cc.assert_called_once_with(
            'store', b"1,2",
            expected_command,
            '(foo)',
            uid=True)
        if silent:
            self.assertIsNone(resp)
        else:
            self.assertEqual(resp, {
                1: (b'blah', b'foo'),
                2: (b'foo',),
            })

        cc.reset_mock()

class TestGmailLabels(IMAPClientTest):

    def setUp(self):
        super(TestGmailLabels, self).setUp()
        self.client._command_and_check = Mock()

    def test_get(self):
        with patch.object(self.client, 'fetch', autospec=True,
                          return_value={123: {b'X-GM-LABELS': [b'foo', b'bar']},
                                        444: {b'X-GM-LABELS': [b'foo']}}):
            out = self.client.get_gmail_labels(sentinel.messages)
            self.client.fetch.assert_called_with(sentinel.messages, [b'X-GM-LABELS'])
            self.assertEqual(out, {123: [b'foo', b'bar'],
                                   444: [b'foo']})

    def test_set(self):
        self.check(self.client.set_gmail_labels, b'X-GM-LABELS')

    def test_add(self):
        self.check(self.client.add_gmail_labels, b'+X-GM-LABELS')

    def test_remove(self):
        self.check(self.client.remove_gmail_labels, b'-X-GM-LABELS')

    def check(self, meth, expected_command):
        self._check(meth, expected_command)
        self._check(meth, expected_command, silent=True)

    def _check(self, meth, expected_command, silent=False):
        if silent:
            expected_command += b".SILENT"

        cc = self.client._command_and_check
        cc.return_value = [
            b'11 (X-GM-LABELS (blah "f\\"o\\"o") UID 1)',
            b'22 (X-GM-LABELS ("f\\"o\\"o") UID 2)',
            b'11 (UID 1 FLAGS (dont))',
            b'22 (UID 2 FLAGS (care))',
        ]
        resp = meth([1, 2], 'f"o"o', silent=silent)
        cc.assert_called_once_with(
            'store', b"1,2",
            expected_command,
            '("f\\"o\\"o")',
            uid=True)
        if silent:
            self.assertIsNone(resp)
        else:
            self.assertEqual(resp, {
                1: (b'blah', b'f"o"o'),
                2: (b'f"o"o',),
            })

        cc.reset_mock()

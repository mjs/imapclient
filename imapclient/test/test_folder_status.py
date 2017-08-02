# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from mock import Mock

from .imapclient_test import IMAPClientTest


class TestFolderStatus(IMAPClientTest):

    def test_basic(self):
        self.client._imap.status.return_value = (
            'OK',
            [b'foo (MESSAGES 3 RECENT 0 UIDNEXT 4 UIDVALIDITY 1435636895 UNSEEN 0)']
        )

        out = self.client.folder_status('foo')

        self.client._imap.status.assert_called_once_with(
            b'"foo"',
            '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)'
        )
        self.assertDictEqual(out, {
            b'MESSAGES': 3,
            b'RECENT': 0,
            b'UIDNEXT': 4,
            b'UIDVALIDITY': 1435636895,
            b'UNSEEN': 0
        })

    def test_literal(self):
        self.client._imap.status.return_value = (
            'OK',
            [(b'{3}', b'foo'), b' (UIDNEXT 4)']
        )

        out = self.client.folder_status('foo', ['UIDNEXT'])

        self.client._imap.status.assert_called_once_with(b'"foo"', '(UIDNEXT)')
        self.assertDictEqual(out, {b'UIDNEXT': 4})

    def test_extra_response(self):
        # In production, we've seen folder names containing spaces come back
        # like this and be broken into two components in the tuple.
        server_response = [b"My files (UIDNEXT 24369)"]
        mock = Mock(return_value=server_response)
        self.client._command_and_check = mock

        resp = self.client.folder_status('My files', ['UIDNEXT'])
        self.assertEqual(resp, {b'UIDNEXT': 24369})

        # We've also seen the response contain mailboxes we didn't
        # ask for. In all known cases, the desired mailbox is last.
        server_response = [b"sent (UIDNEXT 123)\nINBOX (UIDNEXT 24369)"]
        mock = Mock(return_value=server_response)
        self.client._command_and_check = mock

        resp = self.client.folder_status('INBOX', ['UIDNEXT'])
        self.assertEqual(resp, {b'UIDNEXT': 24369})

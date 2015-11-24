# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

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

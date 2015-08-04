# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from six import PY3

from .imapclient_test import IMAPClientTest
from .testable_imapclient import TestableIMAPClient as IMAPClient


search_command = 'search' if PY3 else b'search'


class TestSearch(IMAPClientTest):

    def test_with_uid(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'1 2 44'])

        result = self.client.search('FOO')

        self.client._imap.uid.assert_called_once_with(search_command, b'(FOO)')
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_with_uid_none(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [None])

        result = self.client.search('FOO')

        self.client._imap.uid.assert_called_once_with(search_command, b'(FOO)')
        self.assertEqual(result, [])
        self.assertEqual(result.modseq, None)

    def test_without_uid(self):
        self.client.use_uid = False
        self.client._imap.search.return_value = ('OK', [b'1 2 44'])

        result = self.client.search('FOO')

        self.client._imap.search.assert_called_once_with(None, b'(FOO)')
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_with_uid_with_charset(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'1 2 44'])

        result = self.client.search(['UNDELETED', 'TEXT "\u2639"'], 'UTF-8')

        self.client._imap.uid.assert_called_once_with(
            search_command,
            b'CHARSET', b'UTF-8',
            b'(UNDELETED)',
            b'(TEXT "\xe2\x98\xb9")',
        )
        self.assertEqual(result, [1, 2, 44])

    def test_without_uid_with_charset(self):
        self.client.use_uid = False
        self.client._imap.search.return_value = ('OK', [b'1 2 44'])

        result = self.client.search(['UNDELETED', 'TEXT "\u2639"'], 'UTF-8')

        self.client._imap.search.assert_called_once_with(
            b'UTF-8',
            b'(UNDELETED)',
            b'(TEXT "\xe2\x98\xb9")',
        )
        self.assertEqual(result, [1, 2, 44])

    def test_modseq(self):
        self.client._imap.uid.return_value = ('OK', [b'1 2 (MODSEQ 51101)'])

        result = self.client.search(['MODSEQ 40000'])

        self.client._imap.uid.assert_called_once_with(search_command, b'(MODSEQ 40000)')
        self.assertEqual(result, [1, 2])
        self.assertEqual(result.modseq, 51101)

    def test_error_from_server(self):
        self.client._imap.uid.return_value = ('NO', [b'bad karma'])

        self.assertRaisesRegex(IMAPClient.Error,
                               'bad karma',
                               self.client.search, b'FOO')


class TestGmailSearch(IMAPClientTest):

    def test_with_uid(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'1 2 44'])

        result = self.client.gmail_search('FOO')

        self.client._imap.uid.assert_called_once_with(search_command, b'X-GM-RAW')
        self.assertEqual(self.client._imap.literal, b'FOO')
        self.assertEqual(result, [1, 2, 44])

    def test_without_uid(self):
        self.client.use_uid = False
        self.client._imap.search.return_value = ('OK', [b'1 2 44'])

        result = self.client.gmail_search('FOO')

        self.client._imap.search.assert_called_once_with(None, b'X-GM-RAW')
        self.assertEqual(self.client._imap.literal, b'FOO')
        self.assertEqual(result, [1, 2, 44])

    def test_with_uid_with_charset(self):
        self.client.use_uid = True
        self.client._imap.uid.return_value = ('OK', [b'1 2 44'])

        result = self.client.gmail_search('\u2620', 'UTF-8')

        self.client._imap.uid.assert_called_once_with(
            search_command,
            b'CHARSET', b'UTF-8',
            b'X-GM-RAW')
        self.assertEqual(self.client._imap.literal, b'\xe2\x98\xa0')
        self.assertEqual(result, [1, 2, 44])

    def test_without_uid_with_charset(self):
        self.client.use_uid = False
        self.client._imap.search.return_value = ('OK', [b'1 2 44'])

        result = self.client.gmail_search('\u2620', 'UTF-8')

        self.client._imap.search.assert_called_once_with(b'UTF-8', b'X-GM-RAW')
        self.assertEqual(self.client._imap.literal, b'\xe2\x98\xa0')
        self.assertEqual(result, [1, 2, 44])

    def test_error_from_server(self):
        self.client._imap.uid.return_value = ('NO', [b'bad karma'])

        self.assertRaisesRegex(IMAPClient.Error,
                               'bad karma',
                               self.client.gmail_search, b'FOO')

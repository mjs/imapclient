# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from datetime import date, datetime

from mock import Mock

from .imapclient_test import IMAPClientTest


class TestSearchBase(IMAPClientTest):

    def setUp(self):
        super(TestSearchBase, self).setUp()
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = [b'1 2 44']

    def check_call(self, expected_args):
        self.client._raw_command_untagged.assert_called_once_with(
            b'SEARCH', expected_args)


class TestSearch(TestSearchBase):

    def test_bytes_criteria(self):
        result = self.client.search([b'FOO', b'BAR'])

        self.check_call([b'FOO', b'BAR'])
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_bytes_criteria_with_charset(self):
        self.client.search([b'FOO', b'BAR'], 'utf-92')

        self.check_call([b'CHARSET', b'utf-92', b'FOO', b'BAR'])

    def test_unicode_criteria(self):
        result = self.client.search(['FOO', 'BAR'])

        # Default conversion using us-ascii.
        self.check_call([b'FOO', b'BAR'])
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_unicode_criteria_with_charset(self):
        self.client.search(['FOO', '\u2639'], 'utf-8')

        # Default conversion using us-ascii.
        self.check_call([b'CHARSET', b'utf-8', b'FOO', b'\xe2\x98\xb9'])

    def test_with_date(self):
        self.client.search(['SINCE', date(2005, 4, 3)])
        self.check_call([b'SINCE', b'03-Apr-2005'])

    def test_with_datetime(self):
        self.client.search(['SINCE', datetime(2005, 4, 3, 2, 1, 0)])
        self.check_call([b'SINCE', b'03-Apr-2005'])  # Time part is ignored

    def test_quoting(self):
        self.client.search(['TEXT', 'foo bar'])
        self.check_call([b'TEXT', b'"foo bar"'])

    def test_no_results(self):
        self.client._raw_command_untagged.return_value = [None]

        result = self.client.search(['FOO'])
        self.assertEqual(result, [])
        self.assertEqual(result.modseq, None)

    def test_modseq(self):
        self.client._raw_command_untagged.return_value = [b'1 2 (MODSEQ 51101)']

        result = self.client.search(['MODSEQ', '40000'])

        self.check_call([b'MODSEQ', b'40000'])
        self.assertEqual(result, [1, 2])
        self.assertEqual(result.modseq, 51101)

    def test_nested_empty(self):
        self.assertRaises(ValueError, self.client.search, [[]])

    def test_single(self):
        self.client.search([['FOO']])
        self.check_call([b'(FOO)'])

    def test_nested(self):
        self.client.search(['NOT', ['SUBJECT', 'topic',  'TO', 'some@email.com']])
        self.check_call([b'NOT', b'(SUBJECT', b'topic', b'TO', b'some@email.com)'])

    def test_nested_multiple(self):
        self.client.search(['NOT', ['OR', ['A', 'x', 'B', 'y'], ['C', 'z']]])
        self.check_call([b'NOT', b'(OR', b'(A', b'x', b'B', b'y)', b'(C', b'z))'])

    def test_nested_tuple(self):
        self.client.search(['NOT', ('SUBJECT', 'topic',  'TO', 'some@email.com')])
        self.check_call([b'NOT', b'(SUBJECT', b'topic', b'TO', b'some@email.com)'])


class TestGmailSearch(TestSearchBase):

    def test_bytes_query(self):
        result = self.client.gmail_search(b'foo bar')

        self.check_call([b'CHARSET', b'UTF-8', b'X-GM-RAW', b'"foo bar"'])
        self.assertEqual(result, [1, 2, 44])

    def test_bytes_query_with_charset(self):
        result = self.client.gmail_search(b'foo bar', 'utf-42')

        self.check_call([b'CHARSET', b'utf-42', b'X-GM-RAW', b'"foo bar"'])
        self.assertEqual(result, [1, 2, 44])

    def test_unicode_criteria_with_charset(self):
        self.client.gmail_search('foo \u2639', 'utf-8')

        self.check_call([b'CHARSET', b'utf-8', b'X-GM-RAW', b'"foo \xe2\x98\xb9"'])

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import imaplib
from datetime import date, datetime
from unittest.mock import Mock

from imapclient.exceptions import InvalidCriteriaError
from imapclient.imapclient import _quoted

from .imapclient_test import IMAPClientTest


class TestSearchBase(IMAPClientTest):
    def setUp(self):
        super(TestSearchBase, self).setUp()
        self.client._raw_command_untagged = Mock()
        self.client._raw_command_untagged.return_value = [b"1 2 44"]

    def check_call(self, expected_args):
        self.client._raw_command_untagged.assert_called_once_with(
            b"SEARCH", expected_args
        )


class TestSearch(TestSearchBase):
    def test_bytes_criteria(self):
        result = self.client.search([b"FOO", b"BAR"])

        self.check_call([b"FOO", b"BAR"])
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_bytes_criteria_with_charset(self):
        self.client.search([b"FOO", b"BAR"], "utf-92")

        self.check_call([b"CHARSET", b"utf-92", b"FOO", b"BAR"])

    def test_unicode_criteria(self):
        result = self.client.search(["FOO", "BAR"])

        # Default conversion using us-ascii.
        self.check_call([b"FOO", b"BAR"])
        self.assertEqual(result, [1, 2, 44])
        self.assertEqual(result.modseq, None)

    def test_unicode_criteria_with_charset(self):
        self.client.search(["FOO", "\u2639"], "utf-8")
        self.check_call([b"CHARSET", b"utf-8", b"FOO", _quoted(b"\xe2\x98\xb9")])

    def test_with_date(self):
        self.client.search(["SINCE", date(2005, 4, 3)])
        self.check_call([b"SINCE", b"03-Apr-2005"])

    def test_with_datetime(self):
        self.client.search(["SINCE", datetime(2005, 4, 3, 2, 1, 0)])
        self.check_call([b"SINCE", b"03-Apr-2005"])  # Time part is ignored

    def test_quoting(self):
        self.client.search(["TEXT", "foo bar"])
        self.check_call([b"TEXT", _quoted(b'"foo bar"')])

    def test_zero_length_quoting(self):
        # Zero-length strings should be quoted
        self.client.search(["HEADER", "List-Id", ""])
        self.check_call([b"HEADER", b"List-Id", b'""'])

    def test_no_results(self):
        self.client._raw_command_untagged.return_value = [None]

        result = self.client.search(["FOO"])
        self.assertEqual(result, [])
        self.assertEqual(result.modseq, None)

    def test_modseq(self):
        self.client._raw_command_untagged.return_value = [b"1 2 (MODSEQ 51101)"]

        result = self.client.search(["MODSEQ", "40000"])

        self.check_call([b"MODSEQ", b"40000"])
        self.assertEqual(result, [1, 2])
        self.assertEqual(result.modseq, 51101)

    def test_nested_empty(self):
        self.assertRaises(InvalidCriteriaError, self.client.search, [[]])

    def test_single(self):
        self.client.search([["FOO"]])
        self.check_call([b"(FOO)"])

    def test_nested(self):
        self.client.search(["NOT", ["SUBJECT", "topic", "TO", "some@email.com"]])
        self.check_call([b"NOT", b"(SUBJECT", b"topic", b"TO", b"some@email.com)"])

    def test_nested_multiple(self):
        self.client.search(["NOT", ["OR", ["A", "x", "B", "y"], ["C", "z"]]])
        self.check_call([b"NOT", b"(OR", b"(A", b"x", b"B", b"y)", b"(C", b"z))"])

    def test_nested_tuple(self):
        self.client.search(["NOT", ("SUBJECT", "topic", "TO", "some@email.com")])
        self.check_call([b"NOT", b"(SUBJECT", b"topic", b"TO", b"some@email.com)"])

    def test_search_custom_exception_with_invalid_list(self):
        def search_bad_command_exp(*args, **kwargs):
            raise imaplib.IMAP4.error(
                'SEARCH command error: BAD ["Unknown argument NOT DELETED"]'
            )

        self.client._raw_command_untagged.side_effect = search_bad_command_exp

        with self.assertRaises(imaplib.IMAP4.error) as cm:
            self.client.search(["NOT DELETED"])
        self.assertIn(
            # Python 2.x will add a `u` prefix in the list representation, so let it handle the
            # representation of the criteria there too...
            "may have been caused by a syntax error in the criteria: %s"
            % str(["NOT DELETED"]),
            str(cm.exception),
        )
        # Original exception message should be present too just in case...
        self.assertIn("Unknown argument NOT DELETED", str(cm.exception))

    def test_search_custom_exception_with_invalid_text(self):
        # Check the criteria is surrounding with quotes if the user is using a plain text criteria
        def search_bad_command_exp2(*args, **kwargs):
            raise imaplib.IMAP4.error(
                'SEARCH command error: BAD ["Unknown argument TOO"]'
            )

        self.client._raw_command_untagged.side_effect = search_bad_command_exp2

        with self.assertRaises(imaplib.IMAP4.error) as cm:
            self.client.search("TOO some@email.com")
        self.assertIn(
            'may have been caused by a syntax error in the criteria: "TOO some@email.com"',
            str(cm.exception),
        )
        self.assertIn("Unknown argument TOO", str(cm.exception))


class TestGmailSearch(TestSearchBase):
    def setUp(self):
        super(TestGmailSearch, self).setUp()
        self.client._cached_capabilities = [b"X-GM-EXT-1"]

    def test_bytes_query(self):
        result = self.client.gmail_search(b"foo bar")

        self.check_call([b"CHARSET", b"UTF-8", b"X-GM-RAW", b'"foo bar"'])
        self.assertEqual(result, [1, 2, 44])

    def test_bytes_query_with_charset(self):
        result = self.client.gmail_search(b"foo bar", "utf-42")

        self.check_call([b"CHARSET", b"utf-42", b"X-GM-RAW", b'"foo bar"'])
        self.assertEqual(result, [1, 2, 44])

    def test_unicode_criteria_with_charset(self):
        self.client.gmail_search("foo \u2639", "utf-8")

        self.check_call(
            [b"CHARSET", b"utf-8", b"X-GM-RAW", _quoted(b'"foo \xe2\x98\xb9"')]
        )

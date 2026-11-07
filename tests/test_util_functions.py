# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import unittest

from imapclient.exceptions import InvalidCriteriaError, ProtocolError
from imapclient.imapclient import (
    _normalise_search_criteria,
    _quoted,
    join_message_ids,
    literal,
    normalise_text_list,
    seq_to_parenstr,
    seq_to_parenstr_upper,
)
from imapclient.util import assert_imap_protocol, SequenceSet


class Test_normalise_text_list(unittest.TestCase):
    def check(self, items, expected):
        self.assertEqual(normalise_text_list(items), expected)

    def test_unicode(self):
        self.check("Foo", ["Foo"])

    def test_binary(self):
        self.check(b"FOO", ["FOO"])

    def test_tuple(self):
        self.check(("FOO", "BAR"), ["FOO", "BAR"])

    def test_list(self):
        self.check(["FOO", "BAR"], ["FOO", "BAR"])

    def test_iter(self):
        self.check(iter(["FOO", "BAR"]), ["FOO", "BAR"])

    def test_mixed_list(self):
        self.check(["FOO", b"Bar"], ["FOO", "Bar"])


class Test_seq_to_parenstr(unittest.TestCase):
    def check(self, items, expected):
        self.assertEqual(seq_to_parenstr(items), expected)

    def test_unicode(self):
        self.check("foO", "(foO)")

    def test_binary(self):
        self.check(b"Foo", "(Foo)")

    def test_tuple(self):
        self.check(("FOO", "BAR"), "(FOO BAR)")

    def test_list(self):
        self.check(["FOO", "BAR"], "(FOO BAR)")

    def test_iter(self):
        self.check(iter(["FOO", "BAR"]), "(FOO BAR)")

    def test_mixed_list(self):
        self.check(["foo", b"BAR"], "(foo BAR)")


class Test_seq_to_parenstr_upper(unittest.TestCase):
    def check(self, items, expected):
        self.assertEqual(seq_to_parenstr_upper(items), expected)

    def test_unicode(self):
        self.check("foO", "(FOO)")

    def test_binary(self):
        self.check(b"Foo", "(FOO)")

    def test_tuple(self):
        self.check(("foo", "BAR"), "(FOO BAR)")

    def test_list(self):
        self.check(["FOO", "bar"], "(FOO BAR)")

    def test_iter(self):
        self.check(iter(["FOO", "BaR"]), "(FOO BAR)")

    def test_mixed_list(self):
        self.check(["foo", b"BAR"], "(FOO BAR)")


class Test_join_message_ids(unittest.TestCase):
    def check(self, items, expected):
        self.assertEqual(join_message_ids(items), expected)

    def test_int(self):
        self.check(123, b"123")

    def test_unicode(self):
        self.check("123", b"123")

    def test_unicode_non_numeric(self):
        self.check("2:*", b"2:*")

    def test_binary(self):
        self.check(b"123", b"123")

    def test_binary_non_numeric(self):
        self.check(b"2:*", b"2:*")

    def test_tuple(self):
        self.check((123, 99), b"123,99")

    def test_mixed_list(self):
        self.check(["2:3", 123, b"44"], b"2:3,123,44")

    def test_iter(self):
        self.check(iter([123, 99]), b"123,99")


class Test_SequenceSet(unittest.TestCase):
    def check(self, items, expected, unexpected, highest_id=b"*"):
        sequence_set = SequenceSet(items, highest_id)
        for item in expected:
            self.assertIn(item, sequence_set)
        for item in unexpected:
            self.assertNotIn(item, sequence_set)

    def test_int(self):
        self.check(123, expected=[123], unexpected=[1, 124])

    def test_binary(self):
        self.check(b"123", expected=[123], unexpected=[1, 124])

    def test_unicode(self):
        self.check("123", expected=[123], unexpected=[1, 124])

    def test_int_list(self):
        self.check([1, 2, 3], expected=[1, 2, 3], unexpected=[0, 4])

    def test_mixed_type_list(self):
        self.check(["2:4", 7, b"9"], expected=[2, 3, 4, 7, 9], unexpected=[1, 5, 8])

    def test_mixed_list(self):
        self.check(b"2:4,123,44", expected=[2, 3, 4, 123, 44], unexpected=[1, 6])

    def test_reversed_mixed_list(self):
        self.check(b"123,44,4:2", expected=[2, 3, 4, 123, 44], unexpected=[1, 6])

    def test_unicode_mixed_list(self):
        self.check("2:4,123,44", expected=[2, 3, 4, 123, 44], unexpected=[1, 6])

    def test_infinite_list(self):
        self.check(b"2:*", expected=[2, 3], unexpected=[1, 4], highest_id=b"3")

    def test_reversed_infinite_list(self):
        self.check(b"*:2", expected=[2, 3], unexpected=[1, 4], highest_id=b"3")

    def test_unicode_infinite_list(self):
        self.check("2:*", expected=[2, 3], unexpected=[1, 4], highest_id=b"3")

    def test_infinite_list_without_highest(self):
        with self.assertRaises(ValueError):
            self.check(b"2:*", expected=[2, 3], unexpected=[1, 4])

    def test_highest_only(self):
        self.check("*", expected=[4], unexpected=[1, 2, 3, 5], highest_id=b"4")

    def test_highest_only_range(self):
        self.check("*:*", expected=[4], unexpected=[1, 2, 3, 5], highest_id=b"4")


class Test_normalise_search_criteria(unittest.TestCase):
    def check(self, criteria, charset, expected):
        actual = _normalise_search_criteria(criteria, charset)
        self.assertEqual(actual, expected)
        # Go further and check exact types
        for a, e in zip(actual, expected):
            self.assertEqual(
                type(a),
                type(e),
                "type mismatch: %s (%r) != %s (%r) in %r"
                % (type(a), a, type(e), e, actual),
            )

    def test_list(self):
        self.check(["FOO", "\u263a"], "utf-8", [b"FOO", b"\xe2\x98\xba"])

    def test_tuple(self):
        self.check(("FOO", "BAR"), None, [b"FOO", b"BAR"])

    def test_mixed_list(self):
        self.check(["FOO", b"BAR"], None, [b"FOO", b"BAR"])

    def test_quoting(self):
        self.check(["foo bar"], None, [_quoted(b'"foo bar"')])

    def test_literal_is_not_quoted(self):
        value = literal(b"line one\r\nline two")
        self.check(["TEXT", value], None, [b"TEXT", value])

    def test_ints(self):
        self.check(["modseq", 500], None, [b"modseq", b"500"])

    def test_unicode(self):
        self.check("Foo", None, [b"Foo"])

    def test_binary(self):
        self.check(b"FOO", None, [b"FOO"])

    def test_unicode_with_charset(self):
        self.check("\u263a", "UTF-8", [b"\xe2\x98\xba"])

    def test_binary_with_charset(self):
        # charset is unused when criteria is binary.
        self.check(b"FOO", "UTF-9", [b"FOO"])

    def test_no_quoting_when_criteria_given_as_string(self):
        self.check("foo bar", None, [b"foo bar"])

    def test_None(self):
        self.assertRaises(InvalidCriteriaError, _normalise_search_criteria, None, None)

    def test_empty(self):
        self.assertRaises(InvalidCriteriaError, _normalise_search_criteria, "", None)


class TestAssertIMAPProtocol(unittest.TestCase):
    def test_assert_imap_protocol(self):
        assert_imap_protocol(True)
        with self.assertRaises(ProtocolError):
            assert_imap_protocol(False)

    def test_assert_imap_protocol_with_message(self):
        assert_imap_protocol(True, b"foo")
        with self.assertRaises(ProtocolError):
            assert_imap_protocol(False, b"foo")

# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pytest

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
from imapclient.util import assert_imap_protocol


class Test_normalise_text_list:
    def _check(self, items, expected):
        assert normalise_text_list(items) == expected

    def test_unicode(self):
        self._check("Foo", ["Foo"])

    def test_binary(self):
        self._check(b"FOO", ["FOO"])

    def test_tuple(self):
        self._check(("FOO", "BAR"), ["FOO", "BAR"])

    def test_list(self):
        self._check(["FOO", "BAR"], ["FOO", "BAR"])

    def test_iter(self):
        self._check(iter(["FOO", "BAR"]), ["FOO", "BAR"])

    def test_mixed_list(self):
        self._check(["FOO", b"Bar"], ["FOO", "Bar"])


class Test_seq_to_parenstr:
    def _check(self, items, expected):
        assert seq_to_parenstr(items) == expected

    def test_unicode(self):
        self._check("foO", "(foO)")

    def test_binary(self):
        self._check(b"Foo", "(Foo)")

    def test_tuple(self):
        self._check(("FOO", "BAR"), "(FOO BAR)")

    def test_list(self):
        self._check(["FOO", "BAR"], "(FOO BAR)")

    def test_iter(self):
        self._check(iter(["FOO", "BAR"]), "(FOO BAR)")

    def test_mixed_list(self):
        self._check(["foo", b"BAR"], "(foo BAR)")


class Test_seq_to_parenstr_upper:
    def _check(self, items, expected):
        assert seq_to_parenstr_upper(items) == expected

    def test_unicode(self):
        self._check("foO", "(FOO)")

    def test_binary(self):
        self._check(b"Foo", "(FOO)")

    def test_tuple(self):
        self._check(("foo", "BAR"), "(FOO BAR)")

    def test_list(self):
        self._check(["FOO", "bar"], "(FOO BAR)")

    def test_iter(self):
        self._check(iter(["FOO", "BaR"]), "(FOO BAR)")

    def test_mixed_list(self):
        self._check(["foo", b"BAR"], "(FOO BAR)")


class Test_join_message_ids:
    def _check(self, items, expected):
        assert join_message_ids(items) == expected

    def test_int(self):
        self._check(123, b"123")

    def test_unicode(self):
        self._check("123", b"123")

    def test_unicode_non_numeric(self):
        self._check("2:*", b"2:*")

    def test_binary(self):
        self._check(b"123", b"123")

    def test_binary_non_numeric(self):
        self._check(b"2:*", b"2:*")

    def test_tuple(self):
        self._check((123, 99), b"123,99")

    def test_mixed_list(self):
        self._check(["2:3", 123, b"44"], b"2:3,123,44")

    def test_iter(self):
        self._check(iter([123, 99]), b"123,99")


class Test_normalise_search_criteria:
    def _check(self, criteria, charset, expected):
        actual = _normalise_search_criteria(criteria, charset)
        assert actual == expected
        # Go further and check exact types
        for a, e in zip(actual, expected):
            assert type(a) is type(e), "type mismatch: %s (%r) != %s (%r) in %r" % (
                type(a),
                a,
                type(e),
                e,
                actual,
            )

    def test_list(self):
        self._check(["FOO", "\u263a"], "utf-8", [b"FOO", b"\xe2\x98\xba"])

    def test_tuple(self):
        self._check(("FOO", "BAR"), None, [b"FOO", b"BAR"])

    def test_mixed_list(self):
        self._check(["FOO", b"BAR"], None, [b"FOO", b"BAR"])

    def test_quoting(self):
        self._check(["foo bar"], None, [_quoted(b'"foo bar"')])

    def test_literal_is_not_quoted(self):
        value = literal(b"line one\r\nline two")
        self._check(["TEXT", value], None, [b"TEXT", value])

    def test_ints(self):
        self._check(["modseq", 500], None, [b"modseq", b"500"])

    def test_unicode(self):
        self._check("Foo", None, [b"Foo"])

    def test_binary(self):
        self._check(b"FOO", None, [b"FOO"])

    def test_unicode_with_charset(self):
        self._check("\u263a", "UTF-8", [b"\xe2\x98\xba"])

    def test_binary_with_charset(self):
        # charset is unused when criteria is binary.
        self._check(b"FOO", "UTF-9", [b"FOO"])

    def test_no_quoting_when_criteria_given_as_string(self):
        self._check("foo bar", None, [b"foo bar"])

    def test_None(self):
        with pytest.raises(InvalidCriteriaError):
            _normalise_search_criteria(None, None)

    def test_empty(self):
        with pytest.raises(InvalidCriteriaError):
            _normalise_search_criteria("", None)


class TestAssertIMAPProtocol:
    def test_assert_imap_protocol(self):
        assert_imap_protocol(True)
        with pytest.raises(ProtocolError):
            assert_imap_protocol(False)

    def test_assert_imap_protocol_with_message(self):
        assert_imap_protocol(True, b"foo")
        with pytest.raises(ProtocolError):
            assert_imap_protocol(False, b"foo")

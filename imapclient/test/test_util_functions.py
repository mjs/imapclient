# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient.imapclient import (
    join_message_ids,
    _normalise_search_criteria,
    normalise_text_list,
    seq_to_parenstr,
    seq_to_parenstr_upper,
    _quoted
)
from imapclient.test.util import unittest


class Test_normalise_text_list(unittest.TestCase):

    def check(self, items, expected):
        self.assertEqual(normalise_text_list(items), expected)

    def test_unicode(self):
        self.check('Foo', ['Foo'])

    def test_binary(self):
        self.check(b'FOO', ['FOO'])

    def test_tuple(self):
        self.check(('FOO', 'BAR'), ['FOO', 'BAR'])

    def test_list(self):
        self.check(['FOO', 'BAR'], ['FOO', 'BAR'])

    def test_iter(self):
        self.check(iter(['FOO', 'BAR']), ['FOO', 'BAR'])

    def test_mixed_list(self):
        self.check(['FOO', b'Bar'], ['FOO', 'Bar'])


class Test_seq_to_parenstr(unittest.TestCase):

    def check(self, items, expected):
        self.assertEqual(seq_to_parenstr(items), expected)

    def test_unicode(self):
        self.check('foO', '(foO)')

    def test_binary(self):
        self.check(b'Foo', '(Foo)')

    def test_tuple(self):
        self.check(('FOO', 'BAR'), '(FOO BAR)')

    def test_list(self):
        self.check(['FOO', 'BAR'], '(FOO BAR)')

    def test_iter(self):
        self.check(iter(['FOO', 'BAR']), '(FOO BAR)')

    def test_mixed_list(self):
        self.check(['foo', b'BAR'], '(foo BAR)')


class Test_seq_to_parenstr_upper(unittest.TestCase):

    def check(self, items, expected):
        self.assertEqual(seq_to_parenstr_upper(items), expected)

    def test_unicode(self):
        self.check('foO', '(FOO)')

    def test_binary(self):
        self.check(b'Foo', '(FOO)')

    def test_tuple(self):
        self.check(('foo', 'BAR'), '(FOO BAR)')

    def test_list(self):
        self.check(['FOO', 'bar'], '(FOO BAR)')

    def test_iter(self):
        self.check(iter(['FOO', 'BaR']), '(FOO BAR)')

    def test_mixed_list(self):
        self.check(['foo', b'BAR'], '(FOO BAR)')


class Test_join_message_ids(unittest.TestCase):

    def check(self, items, expected):
        self.assertEqual(join_message_ids(items), expected)

    def test_int(self):
        self.check(123, b'123')

    def test_unicode(self):
        self.check('123', b'123')

    def test_unicode_non_numeric(self):
        self.check('2:*', b'2:*')

    def test_binary(self):
        self.check(b'123', b'123')

    def test_binary_non_numeric(self):
        self.check(b'2:*', b'2:*')

    def test_tuple(self):
        self.check((123, 99), b'123,99')

    def test_mixed_list(self):
        self.check(['2:3', 123, b'44'], b'2:3,123,44')

    def test_iter(self):
        self.check(iter([123, 99]), b'123,99')


class Test_normalise_search_criteria(unittest.TestCase):

    def check(self, criteria, charset, expected):
        actual = _normalise_search_criteria(criteria, charset)
        self.assertEqual(actual, expected)
        # Go further and check exact types
        for a, e in zip(actual, expected):
            self.assertEqual(
                type(a), type(e),
                "type mismatch: %s (%r) != %s (%r) in %r" % (type(a), a, type(e), e, actual),
            )

    def test_list(self):
        self.check(['FOO', '\u263a'], 'utf-8', [b'FOO', b'\xe2\x98\xba'])

    def test_tuple(self):
        self.check(('FOO', 'BAR'), None, [b'FOO', b'BAR'])

    def test_mixed_list(self):
        self.check(['FOO', b'BAR'], None, [b'FOO', b'BAR'])

    def test_quoting(self):
        self.check(['foo bar'], None, [_quoted(b'"foo bar"')])

    def test_ints(self):
        self.check(['modseq', 500], None, [b'modseq', b'500'])

    def test_unicode(self):
        self.check('Foo', None, [b'Foo'])

    def test_binary(self):
        self.check(b'FOO', None, [b'FOO'])

    def test_unicode_with_charset(self):
        self.check('\u263a', 'UTF-8', [b'\xe2\x98\xba'])

    def test_binary_with_charset(self):
        # charset is unused when criteria is binary.
        self.check(b'FOO', 'UTF-9', [b'FOO'])

    def test_no_quoting_when_criteria_given_as_string(self):
        self.check('foo bar', None, [b'foo bar'])

    def test_None(self):
        self.assertRaises(ValueError, _normalise_search_criteria, None, None)

    def test_empty(self):
        self.assertRaises(ValueError, _normalise_search_criteria, '', None)

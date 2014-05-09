# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from datetime import datetime

from mock import patch

from imapclient.imapclient import (
    datetime_to_imap,
    messages_to_str,
    normalise_search_criteria,
    normalise_text_list,
    seq_to_parenstr,
    seq_to_parenstr_upper,
)
from imapclient.fixed_offset import FixedOffset
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

class Test_messages_to_str(unittest.TestCase):

    def check(self, items, expected):
        self.assertEqual(messages_to_str(items), expected)

    def test_int(self):
        self.check(123, '123')

    def test_unicode(self):
        self.check('123', '123')

    def test_unicode_non_numeric(self):
        self.check('2:*', '2:*')

    def test_binary(self):
        self.check(b'123', '123')

    def test_binary_non_numeric(self):
        self.check(b'2:*', '2:*')

    def test_tuple(self):
        self.check((123, 99), '123,99')

    def test_mixed_list(self):
        self.check(['2:3', 123, b'44'], '2:3,123,44')

    def test_iter(self):
        self.check(iter([123, 99]), '123,99')

class Test_normalise_search_criteria(unittest.TestCase):

    def check(self, criteria, expected):
        self.assertEqual(normalise_search_criteria(criteria), expected)

    def test_unicode(self):
        self.check('Foo', ['(Foo)'])

    def test_binary(self):
        self.check(b'FOO', ['(FOO)'])

    def test_tuple(self):
        self.check(('FOO', 'BAR'), ['(FOO)', '(BAR)'])

    def test_list(self):
        self.check(['FOO', 'BAR'], ['(FOO)', '(BAR)'])

    def test_mixed_list(self):
        self.check(['FOO', b'BAR'], ['(FOO)', '(BAR)'])

    def test_None(self):
        self.assertRaises(ValueError, normalise_search_criteria, None)

    def test_empty(self):
        self.assertRaises(ValueError, normalise_search_criteria, '')

class TestDateTimeToImap(unittest.TestCase):

    def test_with_timezone(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0, FixedOffset(2*60 + 30))
        self.assertEqual(datetime_to_imap(dt), '02-Jan-2009 03:04:05 +0230')

    @patch('imapclient.imapclient.FixedOffset.for_system')
    def test_without_timezone(self, for_system):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        for_system.return_value = FixedOffset(-5 * 60)

        self.assertEqual(datetime_to_imap(dt), '02-Jan-2009 03:04:05 -0500')

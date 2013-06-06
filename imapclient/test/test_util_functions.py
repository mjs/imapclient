# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient.test.util import unittest
from imapclient.imapclient import normalise_search_criteria


class TestNormaliseSearchCriteria(unittest.TestCase):

    def check(self, criteria, expected):
        self.assertEqual(normalise_search_criteria(criteria), expected)

    def test_unicode(self):
        self.check('FOO', ['(FOO)'])

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

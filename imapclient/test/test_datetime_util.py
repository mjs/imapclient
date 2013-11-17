# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from datetime import datetime

from ..datetime_util import parse_to_datetime, datetime_to_native
from ..fixed_offset import FixedOffset
from .util import unittest


class TestParsing(unittest.TestCase):

    def check_normalised_and_not(self, in_string, expected_datetime):
        self.assertEqual(
            parse_to_datetime(in_string),
            datetime_to_native(expected_datetime)
        )
        self.assertEqual(
            parse_to_datetime(in_string, normalise=False),
            expected_datetime
        )

    def test_rfc822_style(self):
        self.check_normalised_and_not(
            'Sun, 24 Mar 2013 22:06:10 +0200',
            datetime(2013, 3, 24, 22, 6, 10, 0, FixedOffset(120))
        )

    def test_internaldate_style(self):
        self.check_normalised_and_not(
            ' 9-Feb-2007 17:08:08 -0430',
            datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4*60 - 30))
        )

    def test_invalid(self):
        self.assertRaises(ValueError, parse_to_datetime, 'ABC')

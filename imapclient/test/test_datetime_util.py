# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from datetime import datetime, date


from ..datetime_util import (
    datetime_to_INTERNALDATE,
    datetime_to_native,
    format_criteria_date,
    parse_to_datetime,
)
from ..fixed_offset import FixedOffset
from .util import unittest, patch


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
            b'Sun, 24 Mar 2013 22:06:10 +0200',
            datetime(2013, 3, 24, 22, 6, 10, 0, FixedOffset(120))
        )

    def test_internaldate_style(self):
        self.check_normalised_and_not(
            b' 9-Feb-2007 17:08:08 -0430',
            datetime(2007, 2, 9, 17, 8, 8, 0, FixedOffset(-4 * 60 - 30))
        )
        self.check_normalised_and_not(
            b'19-Feb-2007 17:08:08 0400',
            datetime(2007, 2, 19, 17, 8, 8, 0, FixedOffset(4 * 60))
        )

    def test_dots_for_time_separator(self):
        # As reported in issue #154.
        self.check_normalised_and_not(
            b'Sat, 8 May 2010 16.03.09 +0200',
            datetime(2010, 5, 8, 16, 3, 9, 0, FixedOffset(120))
        )
        self.check_normalised_and_not(
            b'Tue, 18 May 2010 16.03.09 -0200',
            datetime(2010, 5, 18, 16, 3, 9, 0, FixedOffset(-120))
        )
        self.check_normalised_and_not(
            b'Wednesday,18 August 2010 16.03.09 -0200',
            datetime(2010, 8, 18, 16, 3, 9, 0, FixedOffset(-120))
        )

    def test_invalid(self):
        self.assertRaises(ValueError, parse_to_datetime, b'ABC')


class TestDatetimeToINTERNALDATE(unittest.TestCase):

    def test_with_timezone(self):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0, FixedOffset(2 * 60 + 30))
        self.assertEqual(datetime_to_INTERNALDATE(dt), '02-Jan-2009 03:04:05 +0230')

    @patch('imapclient.datetime_util.FixedOffset.for_system')
    def test_without_timezone(self, for_system):
        dt = datetime(2009, 1, 2, 3, 4, 5, 0)
        for_system.return_value = FixedOffset(-5 * 60)

        self.assertEqual(datetime_to_INTERNALDATE(dt), '02-Jan-2009 03:04:05 -0500')


class TestCriteriaDateFormatting(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(format_criteria_date(date(1996, 2, 22)), b'22-Feb-1996')

    def test_single_digit_day(self):
        self.assertEqual(format_criteria_date(date(1996, 4, 4)), b'04-Apr-1996')

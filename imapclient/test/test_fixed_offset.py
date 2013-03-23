# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from datetime import timedelta
from imapclient.test.util import unittest
from imapclient.fixed_offset import FixedOffset
from imapclient.test.mock import patch

class TestFixedOffset(unittest.TestCase):

    def _check(self, offset, expected_delta, expected_name):
        self.assert_(offset.utcoffset(None) == expected_delta)
        self.assert_(offset.tzname(None) == expected_name)
        self.assert_(offset.dst(None) == timedelta(0))

    def test_GMT(self):
        self._check(FixedOffset(0),
                    timedelta(0), '+0000')

    def test_positive(self):
        self._check(FixedOffset(30),
                    timedelta(minutes=30), '+0030')
        self._check(FixedOffset(2 * 60),
                    timedelta(hours=2), '+0200')
        self._check(FixedOffset(11*60 + 30),
                    timedelta(hours=11, minutes=30), '+1130')

    def test_negative(self):
        self._check(FixedOffset(-30),
                    timedelta(minutes=-30), '-0030')
        self._check(FixedOffset(-2 * 60),
                    timedelta(hours=-2), '-0200')
        self._check(FixedOffset(-11*60 - 30),
                    timedelta(minutes=(-11*60) - 30), '-1130')

    @patch('imapclient.fixed_offset.time.daylight', True)
    @patch('imapclient.fixed_offset.time.altzone', 15*60*60)
    def test_for_system_DST(self):
        offset = FixedOffset.for_system()
        self.assert_(offset.tzname(None) == '-1500')

    @patch('imapclient.fixed_offset.time.daylight', False)
    @patch('imapclient.fixed_offset.time.timezone', -15*60*60)
    def test_for_system_no_DST(self):
        offset = FixedOffset.for_system()
        self.assert_(offset.tzname(None) == '+1500')

if __name__ == '__main__':
    unittest.main()

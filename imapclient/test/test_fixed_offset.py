import unittest
from datetime import timedelta
from imapclient.fixed_offset import FixedOffset

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

if __name__ == '__main__':
    unittest.main()

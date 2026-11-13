# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pickle
import unittest
from datetime import datetime, timedelta
from unittest.mock import DEFAULT, Mock, patch

from imapclient.fixed_offset import FixedOffset


class TestFixedOffset(unittest.TestCase):
    def _check(self, offset, expected_delta, expected_name):
        self.assertEqual(offset.utcoffset(None), expected_delta)
        self.assertEqual(offset.tzname(None), expected_name)
        self.assertEqual(offset.dst(None), timedelta(0))

    def test_GMT(self):
        self._check(FixedOffset(0), timedelta(0), "+0000")

    def test_positive(self):
        self._check(FixedOffset(30), timedelta(minutes=30), "+0030")
        self._check(FixedOffset(2 * 60), timedelta(hours=2), "+0200")
        self._check(FixedOffset(11 * 60 + 30), timedelta(hours=11, minutes=30), "+1130")

    def test_negative(self):
        self._check(FixedOffset(-30), timedelta(minutes=-30), "-0030")
        self._check(FixedOffset(-2 * 60), timedelta(hours=-2), "-0200")
        self._check(
            FixedOffset(-11 * 60 - 30), timedelta(minutes=(-11 * 60) - 30), "-1130"
        )

    def test_pickle(self):
        for minutes, name in [(0, "+0000"), (330, "+0530"), (-270, "-0430")]:
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(minutes=minutes, protocol=protocol):
                    offset = pickle.loads(
                        pickle.dumps(FixedOffset(minutes), protocol=protocol)
                    )
                    self.assertIsInstance(offset, FixedOffset)
                    self._check(offset, timedelta(minutes=minutes), name)

    def test_datetime_pickle(self):
        for minutes in [0, 330, -270]:
            expected = datetime(2007, 2, 9, 17, 8, 8, tzinfo=FixedOffset(minutes))
            for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
                with self.subTest(minutes=minutes, protocol=protocol):
                    restored = pickle.loads(pickle.dumps(expected, protocol=protocol))
                    self.assertEqual(restored, expected)
                    self.assertEqual(restored.utcoffset(), timedelta(minutes=minutes))
                    self.assertEqual(restored.tzname(), expected.tzname())

    @patch.multiple(
        "imapclient.fixed_offset.time",
        daylight=True,
        timezone=15 * 60 * 60,
        localtime=DEFAULT,
    )
    def test_for_system_DST_not_active(self, localtime):
        localtime_mock = Mock()
        localtime_mock.tm_isdst = False
        localtime.return_value = localtime_mock

        offset = FixedOffset.for_system()
        self.assertEqual(offset.tzname(None), "-1500")

    @patch.multiple(
        "imapclient.fixed_offset.time",
        daylight=True,
        altzone=15 * 60 * 60,
        localtime=DEFAULT,
    )
    def test_for_system_DST_active(self, localtime):
        localtime_mock = Mock()
        localtime_mock.tm_isdst = True
        localtime.return_value = localtime_mock

        offset = FixedOffset.for_system()
        self.assertEqual(offset.tzname(None), "-1500")

    @patch.multiple(
        "imapclient.fixed_offset.time", daylight=False, timezone=-15 * 60 * 60
    )
    def test_for_system_no_DST(self):
        offset = FixedOffset.for_system()
        self.assertEqual(offset.tzname(None), "+1500")


if __name__ == "__main__":
    unittest.main()

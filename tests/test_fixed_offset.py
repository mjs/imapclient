# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from imapclient.fixed_offset import FixedOffset


def _check(offset, expected_delta, expected_name):
    assert offset.utcoffset(None) == expected_delta
    assert offset.tzname(None) == expected_name
    assert offset.dst(None) == timedelta(0)


@pytest.mark.parametrize(
    "offset, expected_delta, expected_name",
    [
        (FixedOffset(0), timedelta(0), "+0000"),
        (FixedOffset(30), timedelta(minutes=30), "+0030"),
        (FixedOffset(2 * 60), timedelta(hours=2), "+0200"),
        (FixedOffset(11 * 60 + 30), timedelta(hours=11, minutes=30), "+1130"),
        (FixedOffset(-30), timedelta(minutes=-30), "-0030"),
        (FixedOffset(-2 * 60), timedelta(hours=-2), "-0200"),
        (
            FixedOffset(-11 * 60 - 30),
            timedelta(minutes=(-11 * 60) - 30),
            "-1130",
        ),
    ],
)
def test_offsets(offset, expected_delta, expected_name):
    _check(offset, expected_delta, expected_name)


@pytest.mark.parametrize(
    "minutes, name", [(0, "+0000"), (330, "+0530"), (-270, "-0430")]
)
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_pickle(minutes, name, protocol):
    offset = pickle.loads(pickle.dumps(FixedOffset(minutes), protocol=protocol))
    assert isinstance(offset, FixedOffset)
    _check(offset, timedelta(minutes=minutes), name)


@pytest.mark.parametrize("minutes", [0, 330, -270])
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_datetime_pickle(minutes, protocol):
    expected = datetime(2007, 2, 9, 17, 8, 8, tzinfo=FixedOffset(minutes))
    restored = pickle.loads(pickle.dumps(expected, protocol=protocol))
    assert restored == expected
    assert restored.utcoffset() == timedelta(minutes=minutes)
    assert restored.tzname() == expected.tzname()


@patch("imapclient.fixed_offset.time.localtime")
@patch.multiple(
    "imapclient.fixed_offset.time",
    daylight=True,
    timezone=15 * 60 * 60,
)
def test_for_system_DST_not_active(localtime):
    localtime.return_value = Mock(tm_isdst=False)

    offset = FixedOffset.for_system()
    assert offset.tzname(None) == "-1500"


@patch("imapclient.fixed_offset.time.localtime")
@patch.multiple(
    "imapclient.fixed_offset.time",
    daylight=True,
    altzone=15 * 60 * 60,
)
def test_for_system_DST_active(localtime):
    localtime.return_value = Mock(tm_isdst=True)

    offset = FixedOffset.for_system()
    assert offset.tzname(None) == "-1500"


@patch.multiple("imapclient.fixed_offset.time", daylight=False, timezone=-15 * 60 * 60)
def test_for_system_no_DST():
    offset = FixedOffset.for_system()
    assert offset.tzname(None) == "+1500"

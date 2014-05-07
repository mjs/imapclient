# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from datetime import datetime
from email.utils import parsedate_tz

from .fixed_offset import FixedOffset


def parse_to_datetime(timestamp, normalise=True):
    """Convert an IMAP datetime string to a datetime.

    If normalise is True (the default), then the returned datetime
    will be timezone-naive but adjusted to the local time.

    If normalise is False, then the returned datetime will be
    unadjusted but will contain timezone information as per the input.
    """
    time_tuple = parsedate_tz(timestamp)
    if time_tuple == None:
        raise ValueError("couldn't parse datetime %r" % timestamp)

    tz_offset_seconds = time_tuple[-1]
    tz = None
    if tz_offset_seconds is not None:
        tz = FixedOffset(tz_offset_seconds / 60)

    dt = datetime(*time_tuple[:6], tzinfo=tz)
    if normalise and tz:
       dt = datetime_to_native(dt)

    return dt

def datetime_to_native(dt):
    return dt.astimezone(FixedOffset.for_system()).replace(tzinfo=None)

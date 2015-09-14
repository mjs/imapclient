# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import re
from datetime import datetime
from email.utils import parsedate_tz

from .fixed_offset import FixedOffset

_SHORT_MONTHS = ' Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ')


def parse_to_datetime(timestamp, normalise=True):
    """Convert an IMAP datetime string to a datetime.

    If normalise is True (the default), then the returned datetime
    will be timezone-naive but adjusted to the local time.

    If normalise is False, then the returned datetime will be
    unadjusted but will contain timezone information as per the input.
    """
    time_tuple = parsedate_tz(_munge(timestamp))
    if time_tuple is None:
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


def datetime_to_INTERNALDATE(dt):
    """Convert a datetime instance to a IMAP INTERNALDATE string.

    If timezone information is missing the current system
    timezone is used.
    """
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=FixedOffset.for_system())
    return dt.strftime("%d-%b-%Y %H:%M:%S %z")


# Matches timestamp strings where the time separator is a dot (see
# issue #154). For example: 'Sat, 8 May 2010 16.03.09 +0200'
_rfc822_dotted_time = re.compile("\w+, ?\d{1,2} \w+ \d\d(\d\d)? \d\d?\.\d\d?\.\d\d?.*")


def _munge(s):
    s = s.decode('latin-1')  # parsedate_tz only works with strings
    if _rfc822_dotted_time.match(s):
        return s.replace(".", ":")
    return s


def format_criteria_date(dt):
    """Format a date or datetime instance for use in IMAP search criteria.
    """
    out = '%02d-%s-%d' % (dt.day, _SHORT_MONTHS[dt.month], dt.year)
    return out.encode('ascii')

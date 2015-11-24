# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import time
from datetime import tzinfo, timedelta

ZERO = timedelta(0)


class FixedOffset(tzinfo):
    """
    This class describes fixed timezone offsets in hours and minutes
    east from UTC
    """

    def __init__(self, minutes):
        self.__offset = timedelta(minutes=minutes)

        sign = '+'
        if minutes < 0:
            sign = '-'
        hours, remaining_mins = divmod(abs(minutes), 60)
        self.__name = '%s%02d%02d' % (sign, hours, remaining_mins)

    def utcoffset(self, _):
        return self.__offset

    def tzname(self, _):
        return self.__name

    def dst(self, _):
        return ZERO

    @classmethod
    def for_system(klass):
        """Return a FixedOffset instance for the current working timezone and
        DST conditions.
        """
        if time.localtime().tm_isdst and time.daylight:
            offset = time.altzone
        else:
            offset = time.timezone
        return klass(-offset // 60)

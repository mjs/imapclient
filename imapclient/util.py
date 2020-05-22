# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import re
import six
import logging
from six import binary_type, text_type
from datetime import datetime, timezone, timedelta
import binascii, time, calendar

from . import exceptions

logger = logging.getLogger(__name__)


def to_unicode(s):
    if isinstance(s, binary_type):
        try:
            return s.decode('ascii')
        except UnicodeDecodeError:
            logger.warning(
                "An error occurred while decoding %s in ASCII 'strict' mode. Fallback to "
                "'ignore' errors handling, some characters might have been stripped", s
            )
            return s.decode('ascii', 'ignore')
    return s


def to_bytes(s, charset='ascii'):
    if isinstance(s, text_type):
        return s.encode(charset)
    return s


def assert_imap_protocol(condition, message=None):
    if not condition:
        msg = "Server replied with a response that violates the IMAP protocol"
        if message:
            msg += "{}: {}".format(msg, message)
        raise exceptions.ProtocolError(msg)


def chunk(lst, size):
    for i in six.moves.range(0, len(lst), size):
        yield lst[i:i + size]

def redact_password(msg):
    """Preventing IMAP secrets from going to the logging facility."""
    for command in ("LOGIN", "AUTHENTICATE"):
        if command in msg:
            msg_start = msg.split(command)[0]
            return "{}{} **REDACTED**".format(msg_start, command)
    return msg

class _Authenticator:

    """Private class to provide en/decoding
            for base64-based authentication conversation.
    """

    def __init__(self, mechinst):
        self.mech = mechinst    # Callable object to provide/process data

    def process(self, data):
        ret = self.mech(self.decode(data))
        if ret is None:
            return b'*'     # Abort conversation
        return self.encode(ret)

    def encode(self, inp):
        #
        #  Invoke binascii.b2a_base64 iteratively with
        #  short even length buffers, strip the trailing
        #  line feed from the result and append.  "Even"
        #  means a number that factors to both 6 and 8,
        #  so when it gets to the end of the 8-bit input
        #  there's no partial 6-bit output.
        #
        oup = b''
        if isinstance(inp, str):
            inp = inp.encode('utf-8')
        while inp:
            if len(inp) > 48:
                t = inp[:48]
                inp = inp[48:]
            else:
                t = inp
                inp = b''
            e = binascii.b2a_base64(t)
            if e:
                oup = oup + e[:-1]
        return oup

    def decode(self, inp):
        if not inp:
            return b''
        return binascii.a2b_base64(inp)

Months = ' Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ')
Mon2num = {s.encode():n+1 for n, s in enumerate(Months[1:])}
InternalDate = re.compile(br'.*INTERNALDATE "'
                          br'(?P<day>[ 0123][0-9])-(?P<mon>[A-Z][a-z][a-z])-(?P<year>[0-9][0-9][0-9][0-9])'
                          br' (?P<hour>[0-9][0-9]):(?P<min>[0-9][0-9]):(?P<sec>[0-9][0-9])'
                          br' (?P<zonen>[-+])(?P<zoneh>[0-9][0-9])(?P<zonem>[0-9][0-9])'
                          br'"')

def Internaldate2tuple(resp):
    """Parse an IMAP4 INTERNALDATE string.

    Return corresponding local time.  The return value is a
    time.struct_time tuple or None if the string has wrong format.
    """

    mo = InternalDate.match(resp)
    if not mo:
        return None

    mon = Mon2num[mo.group('mon')]
    zonen = mo.group('zonen')

    day = int(mo.group('day'))
    year = int(mo.group('year'))
    hour = int(mo.group('hour'))
    min = int(mo.group('min'))
    sec = int(mo.group('sec'))
    zoneh = int(mo.group('zoneh'))
    zonem = int(mo.group('zonem'))

    # INTERNALDATE timezone must be subtracted to get UT

    zone = (zoneh*60 + zonem)*60
    if zonen == b'-':
        zone = -zone

    tt = (year, mon, day, hour, min, sec, -1, -1, -1)
    utc = calendar.timegm(tt) - zone

    return time.localtime(utc)

def Int2AP(num):
    """Convert integer to A-P string representation."""

    val = b''; AP = b'ABCDEFGHIJKLMNOP'
    num = int(abs(num))
    while num:
        num, mod = divmod(num, 16)
        val = AP[mod:mod+1] + val
    return val


def Time2Internaldate(date_time):

    """Convert date_time to IMAP4 INTERNALDATE representation.

    Return string in form: '"DD-Mmm-YYYY HH:MM:SS +HHMM"'.  The
    date_time argument can be a number (int or float) representing
    seconds since epoch (as returned by time.time()), a 9-tuple
    representing local time, an instance of time.struct_time (as
    returned by time.localtime()), an aware datetime instance or a
    double-quoted string.  In the last case, it is assumed to already
    be in the correct format.
    """
    if isinstance(date_time, (int, float)):
        dt = datetime.fromtimestamp(date_time,
                                    timezone.utc).astimezone()
    elif isinstance(date_time, tuple):
        try:
            gmtoff = date_time.tm_gmtoff
        except AttributeError:
            if time.daylight:
                dst = date_time[8]
                if dst == -1:
                    dst = time.localtime(time.mktime(date_time))[8]
                gmtoff = -(time.timezone, time.altzone)[dst]
            else:
                gmtoff = -time.timezone
        delta = timedelta(seconds=gmtoff)
        dt = datetime(*date_time[:6], tzinfo=timezone(delta))
    elif isinstance(date_time, datetime):
        if date_time.tzinfo is None:
            raise ValueError("date_time must be aware")
        dt = date_time
    elif isinstance(date_time, str) and (date_time[0],date_time[-1]) == ('"','"'):
        return date_time        # Assume in correct format
    else:
        raise ValueError("date_time not of a known type")
    fmt = '"%d-{}-%Y %H:%M:%S %z"'.format(Months[dt.month])
    return dt.strftime(fmt)


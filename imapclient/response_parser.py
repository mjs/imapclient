# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
Parsing for IMAP command responses with focus on FETCH responses as
returned by imaplib.

Initially inspired by http://effbot.org/zone/simple-iterator-parser.htm
"""

#TODO more exact error reporting

from __future__ import unicode_literals

import sys
from collections import defaultdict
from datetime import datetime

from . import six
xrange = six.moves.xrange

from .datetime_util import parse_to_datetime
from .fixed_offset import FixedOffset
from .response_lexer import TokenSource
from .response_types import Envelope, Address

try:
    import imaplib2 as imaplib
except ImportError:
    imaplib2 = None
    import imaplib

__all__ = ['parse_response', 'ParseError']


class ParseError(ValueError):
    pass


def parse_response(data):
    """Pull apart IMAP command responses.

    Returns nested tuples of appropriately typed objects.
    """
    return tuple(gen_parsed_response(data))


def gen_parsed_response(text):
    if not text:
        return
    src = TokenSource(text)

    token = None
    try:
        for token in src:
            yield atom(src, token)
    except ParseError:
        raise
    except ValueError:
        _, err, _ = sys.exc_info()
        raise ParseError("%s: %s" % (str(err), token))


def parse_fetch_response(text, normalise_times=True, uid_is_key=True):
    """Pull apart IMAP FETCH responses as returned by imaplib.

    Returns a dictionary, keyed by message ID. Each value a dictionary
    keyed by FETCH field type (eg."RFC822").
    """
    if text == [None]:
        return {}
    response = gen_parsed_response(text)

    parsed_response = defaultdict(dict)
    while True:
        try:
            msg_id = seq = _int_or_error(six.next(response),
                                         'invalid message ID')
        except StopIteration:
            break

        try:
            msg_response = six.next(response)
        except StopIteration:
            raise ParseError('unexpected EOF')

        if not isinstance(msg_response, tuple):
            raise ParseError('bad response type: %s' % repr(msg_response))
        if len(msg_response) % 2:
            raise ParseError('uneven number of response items: %s' % repr(msg_response))

        # always return the sequence of the message, so it is available
        # even if we return keyed by UID.
        msg_data = {'SEQ': seq}
        for i in xrange(0, len(msg_response), 2):
            word = msg_response[i].upper()
            value = msg_response[i+1]

            if word == 'UID':
                uid = _int_or_error(value, 'invalid UID')
                if uid_is_key:
                    msg_id = uid
                else:
                    msg_data[word] = uid
            elif word == 'INTERNALDATE':
                msg_data[word] = _convert_INTERNALDATE(value, normalise_times)
            elif word == 'ENVELOPE':
                msg_data[word] = _convert_ENVELOPE(value, normalise_times)
            elif word in ('BODY', 'BODYSTRUCTURE'):
                msg_data[word] = BodyData.create(value)
            else:
                msg_data[word] = value

        parsed_response[msg_id].update(msg_data)

    return parsed_response


def _int_or_error(value, error_text):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ParseError('%s: %s' % (error_text, repr(value)))


class BodyData(tuple):

    @classmethod
    def create(cls, response):
        # In case of multipart messages we will see at least 2 tuples
        # at the start. Nest these in to a list so that the returned
        # response tuple always has a consistent number of elements
        # regardless of whether the message is multipart or not.
        if isinstance(response[0], tuple):
            # Multipart, find where the message part tuples stop
            for i, part in enumerate(response):
                if isinstance(part, six.string_types):
                    break
            return cls(([cls.create(part) for part in response[:i]],) + response[i:])
        else:
            return cls(response)
            
    @property
    def is_multipart(self):
        return isinstance(self[0], list)
    

def _convert_INTERNALDATE(date_string, normalise_times=True):
    date_msg = 'INTERNALDATE "%s"' % date_string
    mo = imaplib.InternalDate.match(date_msg.encode('latin-1'))
    if not mo:
        raise ValueError("couldn't parse date %r" % date_string)

    zoneh = int(mo.group('zoneh'))
    zonem = (zoneh * 60) + int(mo.group('zonem'))
    if mo.group('zonen') == b'-':
        zonem = -zonem
    tz = FixedOffset(zonem)

    year = int(mo.group('year'))
    mon = imaplib.Mon2num[mo.group('mon')]
    day = int(mo.group('day'))
    hour = int(mo.group('hour'))
    min = int(mo.group('min'))
    sec = int(mo.group('sec'))

    dt = datetime(year, mon, day, hour, min, sec, 0, tz)

    if normalise_times:
        # Normalise to host system's timezone
        return dt.astimezone(FixedOffset.for_system()).replace(tzinfo=None)
    return dt

def _convert_ENVELOPE(envelope_response, normalise_times=True):
    dt = parse_to_datetime(envelope_response[0], normalise=normalise_times)
    subject = envelope_response[1]

    # addresses contains a tuple of addresses
    # from, sender, reply_to, to, cc, bcc headers
    addresses = []
    for addr_list in envelope_response[2:8]:
        addrs = []
        if addr_list:
            for addr_tuple in addr_list:
                 addrs.append(Address(*addr_tuple))
            addresses.append(tuple(addrs))
        else:
            addresses.append(None)

    return Envelope(
        dt, subject, *addresses,
        in_reply_to=envelope_response[8],
        message_id=envelope_response[9]
    )

def atom(src, token):
    if token == '(':
        return parse_tuple(src)
    elif token == 'NIL':
        return None
    elif token[:1] == '{':
        literal_len = int(token[1:-1])
        literal_text = src.current_literal
        if literal_text is None:
           raise ParseError('No literal corresponds to %r' % token)
        if len(literal_text) != literal_len:
            raise ParseError('Expecting literal of size %d, got %d' % (
                                literal_len, len(literal_text)))
        return literal_text
    elif len(token) >= 2 and (token[:1] == token[-1:] == '"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token

def parse_tuple(src):
    out = []
    for token in src:
        if token == ")":
            return tuple(out)
        out.append(atom(src, token))
    # no terminator
    raise ParseError('Tuple incomplete before "(%s"' % _fmt_tuple(out))

def _fmt_tuple(t):
    return ' '.join(str(item) for item in t)

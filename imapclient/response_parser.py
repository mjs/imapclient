# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
Parsing for IMAP command responses with focus on FETCH responses as
returned by imaplib.

Initially inspired by http://effbot.org/zone/simple-iterator-parser.htm
"""

# TODO more exact error reporting

from __future__ import unicode_literals

import re
import sys
from collections import defaultdict

import six

from .datetime_util import parse_to_datetime
from .response_lexer import TokenSource
from .response_types import BodyData, Envelope, Address, SearchIds
from .exceptions import ProtocolError

xrange = six.moves.xrange

__all__ = ['parse_response', 'parse_message_list']


def parse_response(data):
    """Pull apart IMAP command responses.

    Returns nested tuples of appropriately typed objects.
    """
    if data == [None]:
        return []
    return tuple(gen_parsed_response(data))


_msg_id_pattern = re.compile("(\d+(?: +\d+)*)")


def parse_message_list(data):
    """Parse a list of message ids and return them as a list.

    parse_response is also capable of doing this but this is
    faster. This also has special handling of the optional MODSEQ part
    of a SEARCH response.

    The returned list is a SearchIds instance which has a *modseq*
    attribute which contains the MODSEQ response (if returned by the
    server).
    """
    if len(data) != 1:
        raise ValueError("unexpected message list data")

    data = data[0]
    if not data:
        return SearchIds()

    if six.PY3 and isinstance(data, six.binary_type):
        data = data.decode('ascii')

    m = _msg_id_pattern.match(data)
    if not m:
        raise ValueError("unexpected message list format")

    ids = SearchIds(int(n) for n in m.group(1).split())

    # Parse any non-numeric part on the end using parse_response (this
    # is likely to be the MODSEQ section).
    extra = data[m.end(1):]
    if extra:
        for item in parse_response([extra.encode('ascii')]):
            if isinstance(item, tuple) and len(item) == 2 and item[0].lower() == b'modseq':
                ids.modseq = item[1]
            elif isinstance(item, int):
                ids.append(item)
    return ids


def gen_parsed_response(text):
    if not text:
        return
    src = TokenSource(text)

    token = None
    try:
        for token in src:
            yield atom(src, token)
    except ProtocolError:
        raise
    except ValueError:
        _, err, _ = sys.exc_info()
        raise ProtocolError("%s: %s" % (str(err), token))


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
            raise ProtocolError('unexpected EOF')

        if not isinstance(msg_response, tuple):
            raise ProtocolError('bad response type: %s' % repr(msg_response))
        if len(msg_response) % 2:
            raise ProtocolError('uneven number of response items: %s' % repr(msg_response))

        # always return the sequence of the message, so it is available
        # even if we return keyed by UID.
        msg_data = {b'SEQ': seq}
        for i in xrange(0, len(msg_response), 2):
            word = msg_response[i].upper()
            value = msg_response[i + 1]

            if word == b'UID':
                uid = _int_or_error(value, 'invalid UID')
                if uid_is_key:
                    msg_id = uid
                else:
                    msg_data[word] = uid
            elif word == b'INTERNALDATE':
                msg_data[word] = _convert_INTERNALDATE(value, normalise_times)
            elif word == b'ENVELOPE':
                msg_data[word] = _convert_ENVELOPE(value, normalise_times)
            elif word in (b'BODY', b'BODYSTRUCTURE'):
                msg_data[word] = BodyData.create(value)
            else:
                msg_data[word] = value

        parsed_response[msg_id].update(msg_data)

    return parsed_response


def _int_or_error(value, error_text):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ProtocolError('%s: %s' % (error_text, repr(value)))


def _convert_INTERNALDATE(date_string, normalise_times=True):
    if date_string is None:
        return None

    try:
        return parse_to_datetime(date_string, normalise=normalise_times)
    except ValueError:
        return None


def _convert_ENVELOPE(envelope_response, normalise_times=True):
    dt = None
    if envelope_response[0]:
        try:
            dt = parse_to_datetime(envelope_response[0], normalise=normalise_times)
        except ValueError:
            pass

    subject = envelope_response[1]

    # addresses contains a tuple of addresses
    # from, sender, reply_to, to, cc, bcc headers
    addresses = []
    for addr_list in envelope_response[2:8]:
        addrs = []
        if addr_list:
            for addr_tuple in addr_list:
                if addr_tuple:
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
    if token == b'(':
        return parse_tuple(src)
    elif token == b'NIL':
        return None
    elif token[:1] == b'{':
        literal_len = int(token[1:-1])
        literal_text = src.current_literal
        if literal_text is None:
            raise ProtocolError('No literal corresponds to %r' % token)
        if len(literal_text) != literal_len:
            raise ProtocolError('Expecting literal of size %d, got %d' % (
                literal_len, len(literal_text)))
        return literal_text
    elif len(token) >= 2 and (token[:1] == token[-1:] == b'"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token


def parse_tuple(src):
    out = []
    for token in src:
        if token == b")":
            return tuple(out)
        out.append(atom(src, token))
    # no terminator
    raise ProtocolError('Tuple incomplete before "(%s"' % _fmt_tuple(out))


def _fmt_tuple(t):
    return ' '.join(str(item) for item in t)

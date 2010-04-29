"""
Parsing for IMAP command responses with focus on FETCH responses as
returned by imaplib.

Intially inspired by http://effbot.org/zone/simple-iterator-parser.htm
"""

#TODO more exact error reporting

import imaplib
import shlex
from cStringIO import StringIO
from datetime import datetime
from fixed_offset import FixedOffset


__all__ = ['parse_response', 'ParseError']


class ParseError(ValueError):
    pass


def parse_response(text):
    """Pull apart IMAP command responses.

    Returns nested tuples of appropriately typed objects.
    """
    src = ResponseTokeniser(text)
    try:
        return tuple(atom(src, token) for token in src)
    except ParseError:
        raise
    except ValueError, err:
        raise ParseError("%s: %s" % (str(err), src.lex.token))


def parse_fetch_response(text):
    """Pull apart IMAP FETCH responses as returned by imaplib.

    Returns a dictionary, keyed by message ID. Each value a dictionary
    keyed by FETCH field type (eg."RFC822").
    """
    response = iter(parse_response(text))

    parsed_response = {}
    while True:
        try:
            msg_id = _int_or_error(response.next(), 'invalid message ID')
        except StopIteration:
            break

        try:
            msg_response = response.next()
        except StopIteration:
            raise ParseError('unexpected EOF')

        if not isinstance(msg_response, tuple):
            raise ParseError('bad response type: %s' % repr(msg_response))
        if len(msg_response) % 2:
            raise ParseError('uneven number of response items: %s' % repr(msg_response))

        # always return the 'sequence' of the message, so it is available
        # even if we return keyed by UID.
        msg_data = {'SEQ': msg_id}
        for i in xrange(0, len(msg_response), 2):
            word = msg_response[i].upper()
            value = msg_response[i+1]

            if word == 'UID':
                msg_id = _int_or_error(value, 'invalid UID')
            elif word == 'INTERNALDATE':
                msg_data[word] = _convert_INTERNALDATE(value)
            else:
                msg_data[word] = value

        parsed_response[msg_id] = msg_data

    return parsed_response


def _int_or_error(value, error_text):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ParseError('%s: %s' % (error_text, repr(value)))


def _convert_INTERNALDATE(date_string):
    mo = imaplib.InternalDate.match('INTERNALDATE "%s"' % date_string)
    if not mo:
        raise ValueError("couldn't parse date %r" % date_string)

    zoneh = int(mo.group('zoneh'))
    zonem = (zoneh * 60) + int(mo.group('zonem'))
    if mo.group('zonen') == '-':
        zonem = -zonem
    tz = FixedOffset(zonem)

    year = int(mo.group('year'))
    mon = imaplib.Mon2num[mo.group('mon')]
    day = int(mo.group('day'))
    hour = int(mo.group('hour'))
    min = int(mo.group('min'))
    sec = int(mo.group('sec'))

    dt = datetime(year, mon, day, hour, min, sec, 0, tz)

    # Normalise to host system's timezone
    return dt.astimezone(FixedOffset.for_system()).replace(tzinfo=None)


EOF = object()

# imaplib has poor handling of 'literals' - it both fails to remove the
# {size} marker, and fails to keep responses grouped into the same logical
# 'line'.  What we end up with is a list of response 'records', where each
# record is either a simple string, or tuple of (str_with_lit, literal) -
# where str_with_lit is a string with the {xxx} marker at its end.  Note
# that each elt of this list does *not* correspond 1:1 with the untagged
# responses.
# (http://bugs.python.org/issue5045 also has comments about this)
# So: we have a special file-like object for each of these records.  When
# a string literal is finally processed, we peek into this file-like object
# to grab the literal.
class LiteralHandlingReader:
    def __init__(self, lexer, resp_record):
        self.pushed = None
        self.lexer = lexer
        if isinstance(resp_record, tuple):
            # A 'record' with a string which includes a literal marker, and
            # the literal itself.
            src_text, self.literal = resp_record
            assert src_text.endswith("}"), src_text
            # add a token-sep after the text.
            self.src = StringIO(src_text + " ")
        else:
            # just a line with no literals.
            self.src = StringIO(resp_record)
            self.literal = None

    def read(self, n):
        # Two additional hacks:
        # 1. Hack into the lexer so we get special treatment for backslash
        #    chars - they are only special inside a quoted string.
        # 2. For quoted strings return the quotes around the string so
        #    that atom() can distinguish numbers from strings. Eg. "123" vs 123.
        #    These are stripped off before returning them to the user.
        assert n==1
        if self.pushed is not None:
            ret = self.pushed
            self.pushed = None
        else:
            ret = self.src.read(n)
            if ret == "\\" and self.lexer.state not in '"\\':
                self.pushed = "\\"
            elif ret == '"' and self.lexer.state != '\\':
                self.lexer.token += '"'
        return ret

    def close(self):
        self.src.close()
        self.src = None
        self.literal = None


class ResponseTokeniser(object):

    CTRL_CHARS = ''.join([chr(ch) for ch in range(32)])
    SPECIALS = r'()%"' + CTRL_CHARS
    ALL_CHARS = [chr(ch) for ch in range(256)]
    NON_SPECIALS = [ch for ch in ALL_CHARS if ch not in SPECIALS]

    def __init__(self, resp_chunks):
        # initialize the lexer with all the chunks we read.
        self.lex = shlex.shlex('', posix=True)
        for chunk in reversed(resp_chunks):
            self.lex.push_source(LiteralHandlingReader(self.lex, chunk))

        self.lex.quotes = '"'
        self.lex.commenters = ''
        self.lex.wordchars = self.NON_SPECIALS

    def __iter__(self):
        return iter(self.lex)

    def next(self):
        try:
            return self.lex.next()
        except StopIteration:
            return EOF


def atom(src, token):
    if token == "(":
        out = []
        while True:
            token = src.next()
            if token == ")":
                return tuple(out)
            if token == EOF:
                preceeding = ' '.join(str(val) for val in out)
                raise ParseError('Tuple incomplete before "(%s"' % preceeding)
            out.append(atom(src, token))
    elif token == 'NIL':
        return None
    elif token.startswith('{'):
        literal_len = int(token[1:-1])
        literal_text = src.lex.instream.literal
        if literal_text is None:
           raise ParseError('No literal corresponds to %r' % token)
        if len(literal_text) != literal_len:
            raise ParseError('Expecting literal of size %d, got %d' % (
                                literal_len, len(literal_text)))
        return literal_text
    elif len(token) >= 2 and (token[0] == token[-1] == '"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token

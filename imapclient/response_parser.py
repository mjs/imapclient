"""
XXX

Inspired by: http://effbot.org/zone/simple-iterator-parser.htm
"""

import shlex
from cStringIO import StringIO

#XXX higher level response type response type processing
#XXX plug-in this version
#XXX remove old FetchParser
#TODO more exact error reporting

__all__ = ['parse_response', 'ParseError']


class ParseError(ValueError):
    pass



def parse_response(text):
    #XXX doc
    src = ResponseTokeniser(text)
    try:
        return tuple(atom(src, token) for token in src)
    except ParseError:
        raise
    except ValueError, err:
        raise ParseError("%s: %s" % (str(err), src.lex.token))


def parse_fetch_response(text):
    response = iter(parse_response(text))

    def expect(expected_value):
        next_value = response.next()
        if next_value != expected_value:
            raise ParseError('expected %r, got %r' % (expected_value, next_value))

    msg_data = {}
    while True:
        try:
            expect('*')
        except StopIteration:
            break
        msgid = int(response.next())
        expect('FETCH')
        msg_data[msgid] = response.next()
    return msg_data


EOF = object()

class ResponseTokeniser(object):

    CTRL_CHARS = ''.join([chr(ch) for ch in range(32)])
    ATOM_SPECIALS = r'()%*\"]' + CTRL_CHARS
    ALL_CHARS = [chr(ch) for ch in range(256)]
    ATOM_NON_SPECIALS = [ch for ch in ALL_CHARS if ch not in ATOM_SPECIALS]

    def __init__(self, text):
        self.lex = shlex.shlex(text)
        self.lex.quotes = '"'
        self.lex.commenters = ''
        self.lex.wordchars = self.ATOM_NON_SPECIALS

    def __iter__(self):
        return iter(self.lex)

    def next(self):
        try:
            return self.lex.next()
        except StopIteration:
            return EOF

    def read(self, bytes):
        return self.lex.instream.read(bytes)


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
        if src.read(1) != '\n':
           raise ParseError('No CRLF after %s' % token)
        return src.read(literal_len)
    elif token.startswith('"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token




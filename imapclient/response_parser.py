# Inspired by: http://effbot.org/zone/simple-iterator-parser.htm

import shlex

#XXX error handling: needs to be friendly
#XXX higher level response type response type processing

__all__ = ['parse_response', 'ParseError']


class ParseError(ValueError):
    pass


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
        return self.lex.next()

    def read(self, bytes):
        return self.lex.instream.read(bytes)


def atom(src, token):
    if token == "(":
        out = []
        token = src.next()
        while token != ")":
            out.append(atom(src, token))
            token = src.next()
        return tuple(out)
    elif token == 'NIL':
        return None
    elif token.startswith('{'):
        literal_len = int(token[1:-1])
        assert src.read(1) == '\n' #XXX use ParseError
        return src.read(literal_len)
    elif token.startswith('"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token


def parse_response(text):
    src = ResponseTokeniser(text)
    return tuple([atom(src, token) for token in src])


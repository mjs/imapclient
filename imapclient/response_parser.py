# Inspired by: http://effbot.org/zone/simple-iterator-parser.htm

import shlex

CTRL_CHARS = ''.join([chr(ch) for ch in range(32)])
ATOM_SPECIALS = r'(){%*\"]' + CTRL_CHARS
ALL_CHARS = [chr(ch) for ch in range(256)]
ATOM_NON_SPECIALS = [ch for ch in ALL_CHARS if ch not in ATOM_SPECIALS]

#XXX literals
#XXX error handling: needs to be friendly
#XXX higher level response type response type processing

__all__ = ['parse_response', 'ParseError']

class ParseError(ValueError):
    pass


def generate_tokens(text):
    lex = shlex.shlex(text)
    lex.quotes = '"'
    lex.commenters = ''
    lex.wordchars = ATOM_NON_SPECIALS
    for token in lex:
        yield token


def atom(next, token):
    if token == "(":
        out = []
        token = next()
        while token != ")":
            out.append(atom(next, token))
            token = next()
        return tuple(out)
    elif token == 'NIL':
        return None
    elif token.startswith('"'):
        return token[1:-1]
    elif token.isdigit():
        return int(token)
    else:
        return token


def parse_response(text):
    src = generate_tokens(text)
    return tuple([atom(src.next, token) for token in src])


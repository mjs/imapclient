# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
A lexical analyzer class for IMAP responses.

Although Lexer does all the work, TokenSource is the class to use for
external callers.
"""

from __future__ import unicode_literals

from . import six

__all__ = ["TokenSource"]

if six.PY3:
    unichr = chr  # unichr doesn't exist in py3 where every string is unicode

CTRL_CHARS = frozenset(unichr(c) for c in range(32))
ALL_CHARS = frozenset(unichr(c) for c in range(256))
SPECIALS = frozenset(' ()%"[')
NON_SPECIALS = ALL_CHARS - SPECIALS - CTRL_CHARS
WHITESPACE = frozenset(' \t\r\n')


class TokenSource(object):
    """
    A simple iterator for the Lexer class that also provides access to
    the current IMAP literal.
    """

    def __init__(self, text):
        self.lex = Lexer(text)
        self.src = iter(self.lex)

    @property
    def current_literal(self):
        return self.lex.current_source.literal

    def __iter__(self):
        return self.src


class Lexer(object):
    """
    A lexical analyzer class for IMAP
    """

    def __init__(self, text):
        self.sources = (LiteralHandlingIter(self, chunk) for chunk in text)
        self.current_source = None

    def read_until(self, stream_i, end_char, escape=True):
        token = ''
        try:
            for nextchar in stream_i:
                if escape and nextchar == "\\":
                    escaper = nextchar
                    nextchar = six.next(stream_i)
                    if nextchar != escaper and nextchar != end_char:
                        nextchar = escaper + nextchar    # Don't touch invalid escaping
                elif nextchar == end_char:
                    break
                token += nextchar
            else:
                raise ValueError("No closing '%s'" % end_char)
        except StopIteration:
            raise ValueError("No closing '%s'" % end_char)
        return token + end_char

    def read_token_stream(self, stream_i):
        whitespace = WHITESPACE
        wordchars = NON_SPECIALS
        read_until = self.read_until

        while True:
            # whitespace
            for nextchar in stream_i:
                if nextchar not in whitespace:
                    stream_i.push(nextchar)
                    break    # done skipping over the whitespace

            # non whitespace
            token = ''
            for nextchar in stream_i:
                if nextchar in wordchars:
                    token += nextchar
                elif nextchar == '[':
                    token += nextchar + read_until(stream_i, ']', escape=False)
                else:
                    if nextchar in whitespace:
                        yield token
                    elif nextchar == '"':
                        assert not token
                        yield nextchar + read_until(stream_i, nextchar)
                    else:
                        # Other punctuation, eg. "(". This ends the current token.
                        if token:
                            yield token
                        yield nextchar
                    break
            else:
                if token:
                    yield token
                break

    def __iter__(self):
        for source in self.sources:
            self.current_source = source
            for tok in self.read_token_stream(iter(source)):
                yield tok


# imaplib has poor handling of 'literals' - it both fails to remove the
# {size} marker, and fails to keep responses grouped into the same logical
# 'line'.  What we end up with is a list of response 'records', where each
# record is either a simple string, or tuple of (str_with_lit, literal) -
# where str_with_lit is a string with the {xxx} marker at its end.  Note
# that each element of this list does *not* correspond 1:1 with the
# untagged responses.
# (http://bugs.python.org/issue5045 also has comments about this)
# So: we have a special object for each of these records.  When a
# string literal is processed, we peek into this object to grab the
# literal.
class LiteralHandlingIter:
    def __init__(self, lexer, resp_record):
        self.lexer = lexer
        if isinstance(resp_record, tuple):
            # A 'record' with a string which includes a literal marker, and
            # the literal itself.
            self.src_text = resp_record[0]
            assert self.src_text.endswith("}"), self.src_text
            self.literal = resp_record[1]
        else:
            # just a line with no literals.
            self.src_text = resp_record
            self.literal = None

    def __iter__(self):
        return PushableIterator(self.src_text)


class PushableIterator(object):

    NO_MORE = object()

    def __init__(self, it):
        self.it = iter(it)
        self.pushed = []

    def __iter__(self):
        return self

    def __next__(self):
        if self.pushed:
            return self.pushed.pop()
        return six.next(self.it)

    # For Python 2 compatibility
    next = __next__

    def push(self, item):
        self.pushed.append(item)

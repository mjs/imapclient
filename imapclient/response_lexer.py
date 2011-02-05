# Copyright (c) 2011, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
A lexical analyzer class for IMAP responses.

Although Lexer does all the work, TokenSource is probably the class to
use for external callers.
"""

# This was heavily inspired by (ie, ripped off from) python 2.6's shlex
# module with further inspiration from the patch in
# http://bugs.python.org/issue7594, but redone to be specific to IMAPs
# requirements while offering nice performance by using generators everywhere.

__all__ = ["Lexer"]


class TokenSource(object):
    """
    A simple iterator for the Lexer class that also provides access to
    the current IMAP literal.
    """

    def __init__(self, text):
        lex = Lexer()
        lex.sources = (LiteralHandlingIter(lex, chunk) for chunk in text)
        self.lex = lex
        self.src = iter(lex)

    @property
    def current_literal(self):
        return self.lex.current_source.literal

    def __iter__(self):
        return self.src
    

class Lexer(object):
    "A lexical analyzer class for IMAP"

    CTRL_CHARS = ''.join([chr(ch) for ch in range(32)])
    SPECIALS = r' ()%"[' + CTRL_CHARS
    ALL_CHARS = [chr(ch) for ch in range(256)]
    NON_SPECIALS = frozenset([ch for ch in ALL_CHARS if ch not in SPECIALS])
    WHITESPACE = frozenset(' \t\r\n')

    def __init__(self):
        self.sources = None
        self.current_source = None

    def read_until(self, stream_i, end_char, escape=True):
        token = ''
        try:
            for nextchar in stream_i:
                if escape and nextchar == "\\":
                    escaper = nextchar
                    nextchar = stream_i.next()
                    if nextchar != escaper and nextchar != end_char:
                        token += escaper
                elif nextchar == end_char:
                    break
                token += nextchar
            else:
                raise ValueError("No closing %r" % end_char)
        except StopIteration:
            raise ValueError("No closing %r" % end_char)
        return token + end_char

    def read_token_stream(self, stream_i):
        whitespace = self.WHITESPACE
        wordchars = self.NON_SPECIALS
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
                        # Other punctuation, eg. "("
                        if token:
                            yield token
                        if nextchar == ')' and stream_i.peek() == '(':
                            stream_i.next()     # Read the '('
                            yield ')('
                        else:
                            yield nextchar    # yield the punctuation
                    break
            else:
                if token:
                    yield token
                break

    def __iter__(self):
        "Generate tokens"
        for source in self.sources:
            self.current_source = source
            for tok in self.read_token_stream(iter(source)):
                yield tok


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
class LiteralHandlingIter:
    def __init__(self, lexer, resp_record):
        self.lexer = lexer
        if isinstance(resp_record, tuple):
            # A 'record' with a string which includes a literal marker, and
            # the literal itself.
            src_text, self.literal = resp_record
            assert src_text.endswith("}"), src_text
            self.src_text = src_text
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

    def next(self):
        if self.pushed:
            return self.pushed.pop()
        return self.it.next()

    def push(self, item):
        self.pushed.append(item)

    def peek(self, default=NO_MORE):
        if not self.pushed:
            try:
                self.pushed.append(self.it.next())
            except StopIteration:
                return default
        return self.pushed[-1]

        
        

"""A lexical analyzer class for IMAP responses."""

# This was heavily inspired by (ie, ripped off from) python 2.6's shlex
# module with further inspiration from the patch in
# http://bugs.python.org/issue7594, but redone to be specific to IMAPs
# requirements while offering nice performance by using generators everywhere.

__all__ = ["Lexer"]


class Lexer(object):
    "A lexical analyzer class for IMAP"

    CTRL_CHARS = ''.join([chr(ch) for ch in range(32)])
    SPECIALS = r' ()%"' + CTRL_CHARS
    ALL_CHARS = [chr(ch) for ch in range(256)]
    NON_SPECIALS = [ch for ch in ALL_CHARS if ch not in SPECIALS]

    def __init__(self, sources):
        self.wordchars = set(self.NON_SPECIALS)
        self.whitespace = set((' \t\r\n'))
        self.sources = (LiteralHandlingIter(self, chunk) for chunk in sources)
        self.current_source = None

    def parse_quote(self, stream_i, quoted, token):
        try:
            for nextchar in stream_i:
                if nextchar == "\\":
                    escaper = nextchar
                    nextchar = stream_i.next()
                    if nextchar != escaper and nextchar != quoted:
                        token += escaper
                elif nextchar == quoted:
                    break
                token += nextchar
            else:
                raise ValueError("No closing quotation")
        except StopIteration:
            # escaped char...
            raise ValueError("No closing quotation")

        return quoted + token + quoted

    def read_token_stream(self, stream_i):
        whitespace = self.whitespace
        wordchars = self.wordchars
        parse_quote = self.parse_quote

        while True:

            token = ''

            for nextchar in stream_i:
                if nextchar in whitespace:
                    continue

                # IMAP doesn't have escapes anywhere but strings.
                elif nextchar in wordchars:
                    token = nextchar

                elif nextchar == '"':
                    chunk = parse_quote(stream_i, nextchar, token)
                    token += chunk
                    yield token
                    token = ''
                    continue

                else:
                    # punctuation...
                    yield nextchar
                    continue
                # and... we're done processing the whitespace.
                break

            # non whitespace appending
            for nextchar in stream_i:
                if nextchar in wordchars:
                    token += nextchar
                    continue

                if nextchar in whitespace:
                    yield token
                    break

                elif nextchar == '"':
                    chunk = parse_quote(stream_i, nextchar, token)
                    token = chunk
                    yield token
                    break

                else:
                    assert token
                    yield token
                    yield nextchar # now yield the punctuation...
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

    @classmethod
    def create_token_source(cls, text):
        lex = cls(text)
        return TokenIterator(lex)


class TokenIterator(object):

    def __init__(self, lex):
        self.lex = lex
        self.src = iter(lex)

    @property
    def current_literal(self):
        return self.lex.current_source.literal

    def __iter__(self):
        return self.src
    

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
        self.pushed = None
        self.lexer = lexer
        if isinstance(resp_record, tuple):
            # A 'record' with a string which includes a literal marker, and
            # the literal itself.
            src_text, self.literal = resp_record
            assert src_text.endswith("}"), src_text
            self.src_text = self.literal
        else:
            # just a line with no literals.
            self.src_text = resp_record
            self.literal = None

    def __iter__(self):
        return iter(self.src_text)


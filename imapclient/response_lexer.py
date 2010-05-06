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
        self.sources = sources
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
        "Generate a token"
        for source in self.sources:
            self.current_source = source
            for tok in self.read_token_stream(iter(source)):
                yield tok

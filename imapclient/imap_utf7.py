# The contents of this file has been derived code from the Twisted project
# (http://twistedmatrix.com/). The original author is Jp Calderone.

# Twisted project license follows:

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from .six import b, u, text_type, PY3, int2byte
from .pycompat import iter_as_bytes

class FolderNameError(ValueError):
    pass

PRINTABLE = set(range(0x20, 0x26)) | set(range(0x27, 0x7f))

def encode(s):
    """Encode a folder name using IMAP modified UTF-7 encoding

    Input and output types:
      Python 2 - str/unicode to str
      Python 3 - str to bytes
    """
    # This is for Python 2 only. Under Python 3 the input will always be unicode.
    if (not PY3 and isinstance(s, str) and
          sum(n for n in (ord(c) for c in s) if n > 127)):
        raise FolderNameError("%r contains characters not valid in a str "
                              "folder name. Convert to unicode first?" % s)

    r = []
    _in = []

    def extend_result_if_chars_buffered():
        if _in:
            r.extend([b('&'), modified_base64(''.join(_in)), b('-')])
            del _in[:]

    for c in s:
        if ord(c) in PRINTABLE:
            extend_result_if_chars_buffered()
            r.append(int2byte(ord(c)))
        elif c == '&':
            extend_result_if_chars_buffered()
            r.append(b('&-'))
        else:
            _in.append(c)

    extend_result_if_chars_buffered()

    return b('').join(r[:])

def decode(s):
    """Decode a folder name from IMAP modified UTF-7 encoding to unicode

    Input and output types:
      Python 2 - str to unicode
      Python 3 - bytes to str
    """
    r = []
    _in = []
    for c in iter_as_bytes(s):
        if c == b('&') and not _in:
            _in.append(b('&'))
        elif c == b('-') and _in:
            if len(_in) == 1:
                r.append(u('&'))
            else:
                r.append(modified_unbase64(b('').join(_in[1:])))
            _in = []
        elif _in:
            _in.append(c)
        else:
            r.append(c)
    if _in:
        r.append(modified_unbase64(b('').join(_in[1:])))

    return u('').join(
        x.decode('latin-1') if not isinstance(x, text_type) else x
        for x in r[:])

def modified_base64(s):
    s_utf7 = s.encode('utf-7')
    return s_utf7[1:-1].replace(b('/'), b(','))

def modified_unbase64(s):
    s_utf7 = b('+') + s.replace(b(','), b('/')) + b('-')
    return s_utf7.decode('utf-7')

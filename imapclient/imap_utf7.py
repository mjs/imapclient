# This file contains two main methods used to encode and decode UTF-7
# string, described in the RFC 3501. There are some variations specific
# to IMAP4rev1, so the built-in Python UTF-7 codec can't be used instead.
#
# The main difference is the shift character (used to switch from ASCII to
# base64 encoding context), which is & in this modified UTF-7 convention,
# since + is considered as mainly used in mailbox names. 
# Other variations and examples can be found in the RFC 3501, section 5.1.3.
from __future__ import unicode_literals

import binascii
from six import binary_type, text_type, byte2int, iterbytes, unichr


def encode(s):
    """Encode a folder name using IMAP modified UTF-7 encoding.

    Input is unicode; output is bytes (Python 3) or str (Python 2). If
    non-unicode input is provided, the input is returned unchanged.
    """
    if not isinstance(s, text_type):
        return s

    res = []
    b64_buffer = []
    def consume_b64_buffer(buf):
        """
        Consume the buffer by encoding it into a modified base 64 representation
        and surround it with shift characters & and -
        """
        if b64_buffer:
            res.extend([b'&', base64_utf7_encode(buf), b'-'])
            del buf[:]

    for c in s:
        # printable ascii case should not be modified
        if 0x20 <= ord(c) <= 0x7e:
            consume_b64_buffer(b64_buffer)
            # Special case: & is used as shift character so we need to escape it in ASCII
            if c == '&':
                res.append(b'&-')
            else:
                res.append(c.encode('ascii'))

        # Bufferize characters that will be encoded in base64 and append them later 
        # in the result, when iterating over ASCII character or the end of string
        else:
            b64_buffer.append(c)

    # Consume the remaining buffer if the string finish with non-ASCII characters
    consume_b64_buffer(b64_buffer)

    return b''.join(res)


AMPERSAND_ORD = byte2int(b'&')
DASH_ORD = byte2int(b'-')


def decode(s):
    """Decode a folder name from IMAP modified UTF-7 encoding to unicode.

    Input is bytes (Python 3) or str (Python 2); output is always
    unicode. If non-bytes/str input is provided, the input is returned
    unchanged.
    """
    if not isinstance(s, binary_type):
        return s

    res = []
    # Store base64 substring that will be decoded once stepping on end shift character
    b64_buffer = bytearray()
    for c in iterbytes(s):
        # Shift character without anything in buffer -> starts storing base64 substring
        if c == AMPERSAND_ORD and not b64_buffer:
            b64_buffer.append(c)
        # End shift char. -> append the decoded buffer to the result and reset it
        elif c == DASH_ORD and b64_buffer:
            # Special case &-, representing "&" escaped
            if len(b64_buffer) == 1:
                res.append('&')
            else:
                res.append(base64_utf7_decode(b64_buffer[1:]))
            b64_buffer = bytearray()
        # Still buffering between the shift character and the shift back to ASCII
        elif b64_buffer:
            b64_buffer.append(c)
        # No buffer initialized yet, should be an ASCII printable char
        else:
            res.append(unichr(c))

    # Decode the remaining buffer if any
    if b64_buffer:
        res.append(base64_utf7_decode(b64_buffer[1:]))

    return ''.join(res)


def base64_utf7_encode(buffer):
    s = ''.join(buffer).encode('utf-16be')
    return binascii.b2a_base64(s).rstrip(b'\n=').replace(b'/', b',')


def base64_utf7_decode(s):
    s_utf7 = b'+' + s.replace(b',', b'/') + b'-'
    return s_utf7.decode('utf-7')

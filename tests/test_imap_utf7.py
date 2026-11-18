# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pytest

from imapclient.imap_utf7 import decode, encode

TESTS = [
    ["Foo", b"Foo"],
    ["Foo Bar", b"Foo Bar"],
    ["Stuff & Things", b"Stuff &- Things"],
    ["Hello world", b"Hello world"],
    ["Hello & world", b"Hello &- world"],
    ["Hello\xffworld", b"Hello&AP8-world"],
    ["\xff\xfe\xfd\xfc", b"&AP8A,gD9APw-"],
    [
        "~peter/mail/\u65e5\u672c\u8a9e/\u53f0\u5317",
        b"~peter/mail/&ZeVnLIqe-/&U,BTFw-",
    ],  # example from RFC 2060
    ["\x00foo", b"&AAA-foo"],
    ["foo\r\n\nbar\n", b"foo&AA0ACgAK-bar&AAo-"],  # see imapclient/#187 issue
]


@pytest.mark.parametrize("input, output", TESTS)
def test_encode(input, output):
    encoded = encode(input)
    assert isinstance(encoded, bytes)
    assert encoded == output


@pytest.mark.parametrize("input, output", TESTS)
def test_decode(input, output):
    decoded = decode(output)
    assert isinstance(decoded, str)
    assert input == decoded


@pytest.mark.parametrize("o", list(range(0x20, 0x26)) + list(range(0x27, 0x7F)))
def test_printable_singletons(o):
    """
    The IMAP4 modified UTF-7 implementation encodes all printable
    characters which are in ASCII using the corresponding ASCII byte.
    """
    # All printables represent themselves
    assert bytes((o,)) == encode(chr(o))
    assert chr(o) == decode(bytes((o,)))


def test_ampersand():
    assert encode("&") == b"&-"
    assert decode(b"&-") == "&"

# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import unittest

from imapclient.imap_utf7 import decode, encode


class IMAP4UTF7TestCase(unittest.TestCase):
    tests = [
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

    def test_encode(self):
        for input, output in self.tests:
            encoded = encode(input)
            self.assertIsInstance(encoded, bytes)
            self.assertEqual(encoded, output)

    def test_decode(self):
        for input, output in self.tests:
            decoded = decode(output)
            self.assertIsInstance(decoded, str)
            self.assertEqual(input, decoded)

    def test_printable_singletons(self):
        """
        The IMAP4 modified UTF-7 implementation encodes all printable
        characters which are in ASCII using the corresponding ASCII byte.
        """
        # All printables represent themselves
        for o in list(range(0x20, 0x26)) + list(range(0x27, 0x7F)):
            self.assertEqual(bytes((o,)), encode(chr(o)))
            self.assertEqual(chr(o), decode(bytes((o,))))
        self.assertEqual(encode("&"), b"&-")
        self.assertEqual(encode("&"), b"&-")
        self.assertEqual(decode(b"&-"), "&")

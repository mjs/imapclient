# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient.six import binary_type, text_type, PY3
from imapclient.imap_utf7 import decode, encode, FolderNameError
from imapclient.test.util import unittest

if PY3:
    unichr = chr  # unichr doesn't exist in py3 where every string is unicode

class IMAP4UTF7TestCase(unittest.TestCase):
    tests = [
        ['Foo', 'Foo'],
        ['Foo Bar', 'Foo Bar'],
        ['Stuff & Things', 'Stuff &- Things'],
        ['Hello world', 'Hello world'],
        ['Hello & world', 'Hello &- world'],
        ['Hello\xffworld', 'Hello&AP8-world'],
        ['\xff\xfe\xfd\xfc', '&AP8A,gD9APw-'],
        ['~peter/mail/\u65e5\u672c\u8a9e/\u53f0\u5317',
         '~peter/mail/&ZeVnLIqe-/&U,BTFw-'], # example from RFC 2060
        ['\x00foo', '&AAA-foo'],
    ]

    def test_encode(self):
        for (input, output) in self.tests:
            encoded = encode(input)
            self.assertIsInstance(encoded, text_type)
            self.assertEqual(encoded, output)


    def test_decode(self):
        for (input, output) in self.tests:
            decoded = decode(output)
            self.assertIsInstance(decoded, text_type)
            self.assertEqual(input, decoded)

    def test_printableSingletons(self):
        """
        The IMAP4 modified UTF-7 implementation encodes all printable
        characters which are in ASCII using the corresponding ASCII byte.
        """
        # All printables represent themselves
        for o in list(range(0x20, 0x26)) + list(range(0x27, 0x7f)):
            self.assertEqual(unichr(o), encode(chr(o)))
            self.assertEqual(unichr(o), decode(unichr(o)))
        self.assertEqual(encode('&'), '&-')
        self.assertEqual(encode('&'), '&-')
        self.assertEqual(decode(b'&-'), '&')

    def test_FolderNameError_super(self):
        self.assertTrue(issubclass(FolderNameError, ValueError))


if __name__ == '__main__':
    unittest.main()

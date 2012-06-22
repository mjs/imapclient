# Copyright (c) 2012, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from imapclient.six import b, u, binary_type, text_type, PY3
from imapclient.imap_utf7 import decode, encode, FolderNameError
from imapclient.test.util import unittest

class IMAP4UTF7TestCase(unittest.TestCase):
    tests = [
        ['Foo', b('Foo')],
        ['Foo Bar', b('Foo Bar')],
        ['Stuff & Things', b('Stuff &- Things')],
        [u('Hello world'), b('Hello world')],
        [u('Hello & world'), b('Hello &- world')],
        [u('Hello\xffworld'), b('Hello&AP8-world')],
        [u('\xff\xfe\xfd\xfc'), b('&AP8A,gD9APw-')],
        [u('~peter/mail/\u65e5\u672c\u8a9e/\u53f0\u5317'),
         b('~peter/mail/&ZeVnLIqe-/&U,BTFw-')], # example from RFC 2060
        ['\x00foo', b('&AAA-foo')],
    ]

    def test_encode(self):
        for (input, output) in self.tests:
            encoded = encode(input)
            self.assertIsInstance(encoded, binary_type)
            self.assertEqual(encoded, output)


    def test_decode(self):
        for (input, output) in self.tests:
            decoded = decode(output)
            self.assertIsInstance(decoded, text_type)
            self.assertEqual(input, decoded)


    @unittest.skipIf(PY3, "Only relevant for Python 2")
    def test_illegal_chars(self):
        not_valid_as_str = [
            'blah' + chr(0x80) + 'sne',
            chr(0xaa) + 'foo',
            'blah' + chr(0xff) + 'sne']

        for name in not_valid_as_str:
            self.assertRaises(FolderNameError, encode, name)

        unicode_names = [unicode(name, 'latin-1') for name in not_valid_as_str]
        for name in unicode_names:
            encoded = encode(name)
            self.assertIsInstance(encoded, str)

    def test_printableSingletons(self):
        """
        The IMAP4 modified UTF-7 implementation encodes all printable
        characters which are in ASCII using the corresponding ASCII byte.
        """
        # All printables represent themselves
        for o in list(range(0x20, 0x26)) + list(range(0x27, 0x7f)):
            self.assertEqual(b(chr(o)), encode(chr(o)))
            self.assertEqual(chr(o), decode(b(chr(o))))
        self.assertEqual(encode('&'), b('&-'))
        self.assertEqual(encode(u('&')), b('&-'))
        self.assertEqual(decode(b('&-')), u('&'))

    def test_FolderNameError_super(self):
        self.assertTrue(issubclass(FolderNameError, ValueError))


if __name__ == '__main__':
    unittest.main()

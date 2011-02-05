# Copyright (c) 2011, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from imapclient.imap_utf7 import decode, encode, FolderNameError
from imapclient.test.util import unittest

class IMAP4UTF7TestCase(unittest.TestCase):
    tests = [
        ['Foo', 'Foo'],
        ['Foo Bar', 'Foo Bar'],
        ['Stuff & Things', 'Stuff &- Things'],
        [u'Hello world', 'Hello world'],
        [u'Hello & world', 'Hello &- world'],
        [u'Hello\xffworld', 'Hello&AP8-world'],
        [u'\xff\xfe\xfd\xfc', '&AP8A,gD9APw-'],
        [u'~peter/mail/\u65e5\u672c\u8a9e/\u53f0\u5317',
         '~peter/mail/&ZeVnLIqe-/&U,BTFw-'], # example from RFC 2060
        ['\x00foo', '&AAA-foo'],
    ]

    def test_encode(self):
        for (input, output) in self.tests:
            self.assertEquals(encode(input), output)


    def test_decode(self):
        for (input, output) in self.tests:
            decoded = decode(output)
            self.assertEquals(input, decoded) 
            self.assert_(isinstance(decoded, unicode))


    def test_illegal_chars(self):
        not_valid_as_str = [
            'blah' + chr(0x80) + 'sne',
            chr(0xaa) + 'foo',
            'blah' + chr(0xff) + 'sne']

        for name in not_valid_as_str:
            self.assertRaises(FolderNameError, encode, name)

        unicode_names = [unicode(name, 'latin-1') for name in not_valid_as_str]
        for name in unicode_names:
            assert isinstance(encode(name), str)


    def test_printableSingletons(self):
        """
        The IMAP4 modified UTF-7 implementation encodes all printable
        characters which are in ASCII using the corresponding ASCII byte.
        """
        # All printables represent themselves
        for o in range(0x20, 0x26) + range(0x27, 0x7f):
            self.failUnlessEqual(chr(o), encode(chr(o)))
            self.failUnlessEqual(chr(o), decode(chr(o)))
        self.failUnlessEqual(encode('&'), '&-')
        self.failUnlessEqual(decode('&-'), '&')


    def test_FolderNameError_super(self):
        self.assert_(issubclass(FolderNameError, ValueError))


if __name__ == '__main__':
    unittest.main()

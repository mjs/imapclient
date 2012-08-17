# Copyright (c) 2012, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from imapclient.imapclient import IMAPClient
from imapclient.test.mock import patch, sentinel
from imapclient.test.util import unittest

class TestInit(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('imapclient.imapclient.imaplib')
        self.imaplib = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_plain(self):
        self.imaplib.IMAP4.return_value = sentinel.IMAP4

        imap = IMAPClient('1.2.3.4')

        self.assertEqual(imap._imap, sentinel.IMAP4)
        self.imaplib.IMAP4.assert_called_with('1.2.3.4', 143)
        self.assertEqual(imap.host, '1.2.3.4')
        self.assertEqual(imap.port, 143)
        self.assertEqual(imap.ssl, False)
        self.assertEqual(imap.stream, False)

    def test_SSL(self):
        self.imaplib.IMAP4_SSL.return_value = sentinel.IMAP4_SSL

        imap = IMAPClient('1.2.3.4', ssl=True)

        self.assertEqual(imap._imap, sentinel.IMAP4_SSL)
        self.imaplib.IMAP4_SSL.assert_called_with('1.2.3.4', 993)
        self.assertEqual(imap.host, '1.2.3.4')
        self.assertEqual(imap.port, 993)
        self.assertEqual(imap.ssl, True)
        self.assertEqual(imap.stream, False)

    def test_stream(self):
        self.imaplib.IMAP4_stream.return_value = sentinel.IMAP4_stream

        imap = IMAPClient('command', stream=True)

        self.assertEqual(imap._imap, sentinel.IMAP4_stream)
        self.imaplib.IMAP4_stream.assert_called_with('command')

        self.assertEqual(imap.host, 'command')
        self.assertEqual(imap.port, None)
        self.assertEqual(imap.ssl, False)
        self.assertEqual(imap.stream, True)

    def test_ssl_and_stream_is_error(self):
        self.assertRaises(ValueError, IMAPClient, 'command', ssl=True, stream=True)

    def test_stream_and_port_is_error(self):
        self.assertRaises(ValueError, IMAPClient, 'command', stream=True, port=123)

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from mock import patch, sentinel, Mock

from imapclient.imapclient import IMAPClient
from imapclient.test.util import unittest


class TestInit(unittest.TestCase):

    def setUp(self):
        patcher = patch('imapclient.imapclient.imap4')
        self.imap4 = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('imapclient.imapclient.tls')
        self.tls = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('imapclient.imapclient.imaplib')
        self.imaplib = patcher.start()
        self.addCleanup(patcher.stop)

    def test_plain(self):
        fakeIMAP4 = Mock()
        self.imap4.IMAP4WithTimeout.return_value = fakeIMAP4

        imap = IMAPClient('1.2.3.4', timeout=sentinel.timeout)

        self.assertEqual(imap._imap, fakeIMAP4)
        self.imap4.IMAP4WithTimeout.assert_called_with(
            '1.2.3.4', 143,
            sentinel.timeout
        )
        self.assertEqual(imap.host, '1.2.3.4')
        self.assertEqual(imap.port, 143)
        self.assertEqual(imap.ssl, False)
        self.assertEqual(imap.ssl_context, None)
        self.assertEqual(imap.stream, False)

    def test_SSL(self):
        fakeIMAP4_TLS = Mock()
        self.tls.IMAP4_TLS.return_value = fakeIMAP4_TLS

        imap = IMAPClient('1.2.3.4', ssl=True, ssl_context=sentinel.context,
                          timeout=sentinel.timeout)

        self.assertEqual(imap._imap, fakeIMAP4_TLS)
        self.tls.IMAP4_TLS.assert_called_with(
            '1.2.3.4', 993,
            sentinel.context, sentinel.timeout)
        self.assertEqual(imap.host, '1.2.3.4')
        self.assertEqual(imap.port, 993)
        self.assertEqual(imap.ssl, True)
        self.assertEqual(imap.ssl_context, sentinel.context)
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

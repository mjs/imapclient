# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient.imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from .imapclient_test import IMAPClientTest
from .util import Mock, patch, sentinel, ANY


class TestStarttls(IMAPClientTest):

    def setUp(self):
        super(TestStarttls, self).setUp()

        patcher = patch("imapclient.imapclient.tls")
        self.tls = patcher.start()
        self.addCleanup(patcher.stop)

        self.client.sock = sentinel.old_sock

        self.new_sock = Mock()
        self.new_sock.makefile.return_value = sentinel.file
        self.tls.wrap_socket.return_value = self.new_sock

        self.client.host = sentinel.host
        self.client.ssl = False
        self.client._starttls_done = False
        self.client._simple_command.return_value = "OK", [b'start TLS negotiation']
        self.client._cached_capabilities = [b'STARTTLS']
        self.client._do_capabilites = Mock(return_value=[b'STARTTLS'])

    def test_works(self):
        resp = self.client.starttls(sentinel.ssl_context)

        self.tls.wrap_socket.assert_called_once_with(
            ANY,
            sentinel.ssl_context,
            sentinel.host,
        )
        self.new_sock.makefile.assert_called_once_with('rb')
        self.assertEqual(self.client._conn.file, sentinel.file)
        self.assertEqual(resp, b'start TLS negotiation')

    def test_command_fails(self):
        self.client._simple_command.return_value = "NO", [b'sorry']

        with self.assertRaises(IMAPClientError) as raised:
            self.client.starttls(sentinel.ssl_context)
        self.assertEqual(str(raised.exception), "starttls failed: sorry")

    def test_fails_if_called_twice(self):
        self.client.starttls(sentinel.ssl_context)
        self.assert_tls_already_established()

    def test_fails_if_ssl_true(self):
        self.client.ssl = True
        self.assert_tls_already_established()

    def assert_tls_already_established(self):
        with self.assertRaises(IMAPClient.AbortError) as raised:
            self.client.starttls(sentinel.ssl_context)
        self.assertEqual(str(raised.exception), "TLS session already established")

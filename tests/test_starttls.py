# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from unittest.mock import patch, sentinel

from imapclient.exceptions import IMAPClientError
from imapclient.imapclient import IMAPClient

from .imapclient_test import IMAPClientTest


class TestStarttls(IMAPClientTest):
    def setUp(self):
        super(TestStarttls, self).setUp()

        patcher = patch("imapclient.imapclient.tls")
        self.tls = patcher.start()
        self.addCleanup(patcher.stop)

        self.client.ssl = False
        self.client._starttls_done = False
        self.client._imap.starttls.return_value = "OK", [b"start TLS negotiation"]
        self.client._cached_capabilities = [b"STARTTLS"]

    def test_works(self):
        resp = self.client.starttls(sentinel.ssl_context)

        self.client._imap.starttls.assert_called_once_with(
            ssl_context=sentinel.ssl_context
        )
        self.tls.create_default_context.assert_not_called()
        self.assertTrue(self.client._starttls_done)
        self.assertEqual(resp, b"start TLS negotiation")

    def test_default_context_is_used(self):
        resp = self.client.starttls()

        self.client._imap.starttls.assert_called_once_with(
            ssl_context=self.tls.create_default_context.return_value
        )
        self.assertEqual(resp, b"start TLS negotiation")

    def test_command_fails(self):
        self.client._imap.starttls.return_value = "NO", [b"sorry"]

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

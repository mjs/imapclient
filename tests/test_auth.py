# Copyright (c) 2016, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from imapclient import IMAPClient
from .imapclient_test import IMAPClientTest


class TestPlainLogin(IMAPClientTest):

    def assert_authenticate_call(self, expected_auth_string):
        authenticate = self.client._imap.authenticate
        self.assertEqual(authenticate.call_count, 1)
        auth_type, auth_func = authenticate.call_args[0]
        self.assertEqual(auth_type, "PLAIN")
        self.assertEqual(auth_func(None), expected_auth_string)

    def test_simple(self):
        self.client._imap.authenticate.return_value = ('OK', [b'Success'])
        result = self.client.plain_login("user", "secret")
        self.assertEqual(result, b'Success')
        self.assert_authenticate_call("\0user\0secret")

    def test_fail(self):
        self.client._imap.authenticate.return_value = ('NO', [b'Boom'])
        self.assertRaises(IMAPClient.Error, self.client.plain_login, "user", "secret")

    def test_with_authorization_identity(self):
        self.client._imap.authenticate.return_value = ('OK', [b'Success'])
        result = self.client.plain_login("user", "secret", "authid")
        self.assertEqual(result, b'Success')
        self.assert_authenticate_call("authid\0user\0secret")

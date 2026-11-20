# Copyright (c) 2016, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pytest

from imapclient.exceptions import LoginError


def _assert_authenticate_call(client, expected_auth_string):
    authenticate = client._imap.authenticate
    assert authenticate.call_count == 1
    auth_type, auth_func = authenticate.call_args[0]
    assert auth_type == "PLAIN"
    assert auth_func(None) == expected_auth_string


def test_simple(client):
    client._imap.authenticate.return_value = ("OK", [b"Success"])
    result = client.plain_login("user", "secret")
    assert result == b"Success"
    _assert_authenticate_call(client, "\0user\0secret")


def test_fail(client):
    client._imap.authenticate.return_value = ("NO", [b"Boom"])
    with pytest.raises(LoginError):
        client.plain_login("user", "secret")


def test_with_authorization_identity(client):
    client._imap.authenticate.return_value = ("OK", [b"Success"])
    result = client.plain_login("user", "secret", "authid")
    assert result == b"Success"
    _assert_authenticate_call(client, "authid\0user\0secret")

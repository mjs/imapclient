# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from unittest.mock import patch, sentinel

import pytest

from imapclient.exceptions import IMAPClientError
from imapclient.imapclient import IMAPClient
from imapclient.testable_imapclient import TestableIMAPClient


@pytest.fixture
def tls():
    with patch("imapclient.imapclient.tls") as mock:
        yield mock


@pytest.fixture
def client(tls):
    client = TestableIMAPClient()
    client.ssl = False
    client._starttls_done = False
    client._imap.starttls.return_value = ("OK", [b"start TLS negotiation"])
    client._cached_capabilities = [b"STARTTLS"]
    return client


def _assert_tls_already_established(client):
    with pytest.raises(IMAPClient.AbortError, match="TLS session already established"):
        client.starttls(sentinel.ssl_context)


def test_works(client, tls):
    resp = client.starttls(sentinel.ssl_context)

    client._imap.starttls.assert_called_once_with(ssl_context=sentinel.ssl_context)
    tls.create_default_context.assert_not_called()
    assert client._starttls_done
    assert resp == b"start TLS negotiation"


def test_default_context_is_used(client, tls):
    resp = client.starttls()

    client._imap.starttls.assert_called_once_with(
        ssl_context=tls.create_default_context.return_value
    )
    assert resp == b"start TLS negotiation"


def test_command_fails(client):
    client._imap.starttls.return_value = ("NO", [b"sorry"])

    with pytest.raises(IMAPClientError) as exc_info:
        client.starttls(sentinel.ssl_context)
    assert str(exc_info.value) == "starttls failed: sorry"


def test_fails_if_called_twice(client):
    client.starttls(sentinel.ssl_context)
    _assert_tls_already_established(client)


def test_fails_if_ssl_true(client):
    client.ssl = True
    _assert_tls_already_established(client)

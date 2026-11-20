# Copyright (c) 2017, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from unittest.mock import Mock

import pytest

from imapclient.exceptions import IllegalStateError


@pytest.fixture
def client(client):
    client._raw_command_untagged = Mock()
    client._imap.state = "AUTH"
    client._cached_capabilities = [b"ENABLE"]
    return client


def test_success(client):
    client._raw_command_untagged.return_value = b"CONDSTORE"

    resp = client.enable("CONDSTORE")

    client._raw_command_untagged.assert_called_once_with(
        b"ENABLE", [b"CONDSTORE"], uid=False, response_name="ENABLED", unpack=True
    )
    assert resp == [b"CONDSTORE"]


def test_failed1(client):
    # When server returns an empty ENABLED response
    client._raw_command_untagged.return_value = b""

    resp = client.enable("FOO")

    client._raw_command_untagged.assert_called_once_with(
        b"ENABLE", [b"FOO"], uid=False, response_name="ENABLED", unpack=True
    )
    assert resp == []


def test_failed2(client):
    # When server returns no ENABLED response
    client._raw_command_untagged.return_value = None

    resp = client.enable("FOO")

    client._raw_command_untagged.assert_called_once_with(
        b"ENABLE", [b"FOO"], uid=False, response_name="ENABLED", unpack=True
    )
    assert resp == []


def test_multiple(client):
    client._raw_command_untagged.return_value = b"FOO BAR"

    resp = client.enable("FOO", "BAR")

    client._raw_command_untagged.assert_called_once_with(
        b"ENABLE", [b"FOO", b"BAR"], uid=False, response_name="ENABLED", unpack=True
    )
    assert resp == [b"FOO", b"BAR"]


def test_wrong_state(client):
    client._imap.state = "SELECTED"

    with pytest.raises(IllegalStateError):
        client.enable("FOO")

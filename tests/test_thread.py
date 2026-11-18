# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from unittest.mock import Mock

import pytest

from imapclient.exceptions import CapabilityError


@pytest.fixture
def client(client):
    client._cached_capabilities = (b"THREAD=REFERENCES",)
    client._raw_command_untagged = Mock()
    client._raw_command_untagged.return_value = [b"(1 2)(3)(4 5 6)"]
    return client


def _check_call(client, expected_args):
    client._raw_command_untagged.assert_called_once_with(b"THREAD", expected_args)


def test_no_thread_support(client):
    client._cached_capabilities = (b"NOT-THREAD",)
    with pytest.raises(CapabilityError):
        client.thread()


def test_unsupported_algorithm(client):
    client._cached_capabilities = (b"THREAD=FOO",)
    with pytest.raises(CapabilityError):
        client.thread()


def test_defaults(client):
    threads = client.thread()

    _check_call(client, [b"REFERENCES", b"UTF-8", b"ALL"])
    assert threads == ((1, 2), (3,), (4, 5, 6))


def test_all_args(client):
    client._cached_capabilities = (b"THREAD=COTTON",)

    client.thread("COTTON", ["TEXT", "\u261e"], "UTF-7")

    _check_call(client, [b"COTTON", b"UTF-7", b"TEXT", b"+Jh4-"])

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from unittest.mock import Mock

import pytest

from imapclient.exceptions import CapabilityError


@pytest.fixture
def client(client):
    client._cached_capabilities = (b"SORT",)
    client._raw_command_untagged = Mock()
    client._raw_command_untagged.return_value = b"9 8 7"
    return client


def _check_call(client, expected_args):
    client._raw_command_untagged.assert_called_once_with(
        b"SORT", expected_args, unpack=True
    )


def test_no_support(client):
    client._cached_capabilities = (b"BLAH",)
    with pytest.raises(CapabilityError):
        client.sort("ARRIVAL")


def test_single_criteria(client):
    ids = client.sort("arrival")

    _check_call(client, [b"(ARRIVAL)", b"UTF-8", b"ALL"])
    assert list(ids) == [9, 8, 7]


def test_multiple_criteria(client):
    client.sort(["arrival", b"SUBJECT"])

    _check_call(client, [b"(ARRIVAL SUBJECT)", b"UTF-8", b"ALL"])


def test_all_args(client):
    client.sort("arrival", ["TEXT", "\u261e"], "UTF-7")

    _check_call(client, [b"(ARRIVAL)", b"UTF-7", b"TEXT", b"+Jh4-"])

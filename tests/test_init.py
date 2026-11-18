# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import sys
import types
from unittest.mock import Mock, patch, sentinel

import pytest

from imapclient.imapclient import IMAPClient, SocketTimeout


@pytest.fixture
def imap_mocks():
    with patch("imapclient.imapclient.imap4") as imap4, patch(
        "imapclient.imapclient.tls"
    ) as tls, patch("imapclient.imapclient.imaplib") as imaplib:
        yield types.SimpleNamespace(imap4=imap4, tls=tls, imaplib=imaplib)


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="connection timeouts require Python 3.9+"
)
def test_plain(imap_mocks):
    fakeIMAP4 = Mock()
    imap_mocks.imap4.IMAP4WithTimeout.return_value = fakeIMAP4

    imap = IMAPClient("1.2.3.4", ssl=False, timeout=sentinel.timeout)

    assert imap._imap is fakeIMAP4
    imap_mocks.imap4.IMAP4WithTimeout.assert_called_once_with(
        "1.2.3.4", 143, sentinel.timeout
    )
    assert imap.host == "1.2.3.4"
    assert imap.port == 143
    assert imap.ssl is False
    assert imap.ssl_context is None
    assert imap.stream is False


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="connection timeouts require Python 3.9+"
)
def test_plain_SocketTimeout(imap_mocks):
    fakeIMAP4 = Mock()
    imap_mocks.imap4.IMAP4WithTimeout.return_value = fakeIMAP4

    imap = IMAPClient(
        "1.2.3.4",
        ssl=False,
        timeout=SocketTimeout(sentinel.connect_timeout, sentinel.timeout),
    )

    assert imap._imap is fakeIMAP4
    imap_mocks.imap4.IMAP4WithTimeout.assert_called_once_with(
        "1.2.3.4", 143, sentinel.connect_timeout
    )


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="connection timeouts require Python 3.9+"
)
def test_SSL(imap_mocks):
    fakeIMAP4_TLS = Mock()
    imap_mocks.tls.IMAP4_TLS.return_value = fakeIMAP4_TLS

    imap = IMAPClient("1.2.3.4", ssl_context=sentinel.context, timeout=sentinel.timeout)

    assert imap._imap is fakeIMAP4_TLS
    imap_mocks.tls.IMAP4_TLS.assert_called_once_with(
        "1.2.3.4", 993, sentinel.context, sentinel.timeout
    )
    assert imap.host == "1.2.3.4"
    assert imap.port == 993
    assert imap.ssl is True
    assert imap.ssl_context is sentinel.context
    assert imap.stream is False


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason="connection timeouts require Python 3.9+"
)
def test_SSL_SocketTimeout(imap_mocks):
    fakeIMAP4_TLS = Mock()
    imap_mocks.tls.IMAP4_TLS.return_value = fakeIMAP4_TLS

    imap = IMAPClient(
        "1.2.3.4",
        ssl_context=sentinel.context,
        timeout=SocketTimeout(sentinel.connect_timeout, sentinel.timeout),
    )

    assert imap._imap is fakeIMAP4_TLS
    imap_mocks.tls.IMAP4_TLS.assert_called_once_with(
        "1.2.3.4", 993, sentinel.context, sentinel.connect_timeout
    )


def test_stream(imap_mocks):
    fakeIMAP4_stream = Mock()
    imap_mocks.imaplib.IMAP4_stream.return_value = fakeIMAP4_stream

    imap = IMAPClient("command", stream=True, ssl=False)

    assert imap._imap is fakeIMAP4_stream
    imap_mocks.imaplib.IMAP4_stream.assert_called_once_with("command")

    assert imap.host == "command"
    assert imap.port is None
    assert imap.ssl is False
    assert imap.stream is True


def test_ssl_and_stream_is_error():
    with pytest.raises(ValueError):
        IMAPClient("command", ssl=True, stream=True)


def test_stream_and_port_is_error():
    with pytest.raises(ValueError):
        IMAPClient("command", stream=True, port=123)

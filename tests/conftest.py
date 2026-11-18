# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import pytest

from imapclient.testable_imapclient import TestableIMAPClient as IMAPClient


@pytest.fixture
def client():
    """Return a fresh TestableIMAPClient instance for each test."""
    return IMAPClient()

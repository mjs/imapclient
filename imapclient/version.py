# Copyright (c) 2025, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from importlib import metadata

version = metadata.version("imapclient")


def _make_version_info():
    parts = version.split(".")
    assert len(parts) == 3
    return tuple(int(p) for p in parts) + ("final",)


# This is for backwards compatibility with older versions of IMAPClient only
version_info = _make_version_info()

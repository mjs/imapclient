# Copyright (c) 2025, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from importlib import metadata
from typing import Tuple

version = metadata.version("imapclient")


def _make_version_info() -> Tuple[int, int, int, str]:
    major, minor, micro = version.split(".")
    return (int(major), int(minor), int(micro), "final")


# This is for backwards compatibility with older versions of IMAPClient only
version_info = _make_version_info()

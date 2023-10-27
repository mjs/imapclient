#!/usr/bin/env python3

# Copyright (c) 2023, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from os import path
from typing import Dict

from setuptools import setup  # type: ignore[import-untyped]

# Read version info
here = path.dirname(__file__)
version_file = path.join(here, "imapclient", "version.py")
info: Dict[str, str] = {}
exec(open(version_file).read(), {}, info)

desc = """\
IMAPClient is an easy-to-use, Pythonic and complete IMAP client library.

Features:
    * Arguments and return values are natural Python types.
    * IMAP server responses are fully parsed and readily usable.
    * IMAP unique message IDs (UIDs) are handled transparently.
    * Internationalised mailbox names are transparently handled.
    * Time zones are correctly handled.
    * Convenience methods are provided for commonly used functionality.
    * Exceptions are raised when errors occur.

Python versions 3.7 through 3.11 are officially supported.

IMAPClient includes comprehensive units tests and automated
functional tests that can be run against a live IMAP server.
"""

doc_deps = ["sphinx"]

setup(
    name="IMAPClient",
    description="Easy-to-use, Pythonic and complete IMAP client library",
    keywords="imap client email mail",
    version=info["version"],
    maintainer=info["maintainer"],
    maintainer_email=info["maintainer_email"],
    author=info["author"],
    author_email=info["author_email"],
    license="3-Clause BSD License",
    url="https://github.com/mjs/imapclient/",
    packages=["imapclient"],
    package_data=dict(imapclient=["examples/*.py"]),
    extras_require={"doc": doc_deps},
    long_description=desc,
    python_requires=">=3.7.0",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Communications :: Email :: Post-Office :: IMAP",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
    ],
)

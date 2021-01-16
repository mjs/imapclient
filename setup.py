#!/usr/bin/env python

# Copyright (c) 2017, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import sys
from os import path

from setuptools import setup

MAJ_MIN_MIC = sys.version_info[:3]
IS_PY3 = MAJ_MIN_MIC >= (3, 0, 0)

# Read version info
here = path.dirname(__file__)
version_file = path.join(here, "imapclient", "version.py")
info = {}
if IS_PY3:
    exec(open(version_file).read(), {}, info)
else:
    execfile(version_file, {}, info)

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

Python versions 2.7 and 3.4 through 3.7 are officially supported.

IMAPClient includes comprehensive units tests and automated
functional tests that can be run against a live IMAP server.
"""

main_deps = ["six"]
test_deps = ['mock>=1.3.0; python_version < "3.4"']
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
    license="http://en.wikipedia.org/wiki/BSD_licenses",
    url="https://github.com/mjs/imapclient/",
    download_url="http://menno.io/projects/IMAPClient/IMAPClient-%s.zip"
    % info["version"],
    packages=["imapclient"],
    package_data=dict(imapclient=["examples/*.py"]),
    install_requires=main_deps,
    tests_require=test_deps,
    extras_require={"test": test_deps, "doc": doc_deps},
    long_description=desc,
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

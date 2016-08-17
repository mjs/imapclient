#!/usr/bin/env python

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import sys
from os import path

# bootstrap setuptools if necessary
from ez_setup import use_setuptools
use_setuptools(version="18.8.1")

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

MAJ_MIN = sys.version_info[:2]
IS_PY3 = MAJ_MIN >= (3, 0)
IS_PY_26_OR_OLDER = MAJ_MIN <= (2, 6)
IS_PY_34_OR_NEWER = MAJ_MIN >= (3, 4)

# Read version info
here = path.dirname(__file__)
version_file = path.join(here, 'imapclient', 'version.py')
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

Python versions 2.6, 2.7, 3.3 and 3.4 are officially supported.

IMAPClient includes comprehensive units tests and automated
functional tests that can be run against a live IMAP server.
"""


class TestDiscoverCommand(TestCommand):
    """
    Use unittest2 to discover and run tests
    """

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        from imapclient.test.util import unittest   # this will import unittest2
        module = "__main__"
        if IS_PY_26_OR_OLDER or IS_PY_34_OR_NEWER:
            module = None
        unittest.main(argv=['', 'discover'], module=module)

main_deps = [
    'backports.ssl>=0.0.9',
    'pyopenssl>=' + info["min_pyopenssl_version"],
    'six',
    'mock==1.3.0'
]

setup_deps = main_deps + ['sphinx']

test_deps = []
if IS_PY_26_OR_OLDER:
    test_deps.append('unittest2')

setup(name='IMAPClient',
      version=info['version'],
      author=info['author'],
      author_email=info['author_email'],
      license="http://en.wikipedia.org/wiki/BSD_licenses",
      url="http://imapclient.freshfoo.com/",
      download_url='http://freshfoo.com/projects/IMAPClient/IMAPClient-%s.zip' % info['version'],
      packages=find_packages(),
      package_data=dict(imapclient=['examples/*.py']),
      setup_requires=setup_deps,
      install_requires=main_deps,
      tests_require=test_deps,
      description="Easy-to-use, Pythonic and complete IMAP client library",
      long_description=desc,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Topic :: Communications :: Email :: Post-Office :: IMAP',
          'Topic :: Internet',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Networking'],
      cmdclass={'test': TestDiscoverCommand})

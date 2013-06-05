#!/usr/bin/env python

# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses


# bootstrap setuptools if necessary
import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

import imapclient
version = imapclient.__version__

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

Python versions 2.6, 2.7, 3.2 and 3.3 are officially supported.

IMAPClient includes fairly comprehensive units tests and automated functional tests that can be run against a live IMAP server.
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
        unittest.main(argv=['', 'discover'])


setup(name='IMAPClient',
      version=version,
      author="Menno Smits",
      author_email="menno@freshfoo.com",
      license="http://en.wikipedia.org/wiki/BSD_licenses",
      url="http://imapclient.freshfoo.com/",
      download_url='http://freshfoo.com/projects/IMAPClient/IMAPClient-%s.zip' % version,
      packages=find_packages(),
      package_data=dict(imapclient=['examples/*.py']),
      tests_require=['mock==0.8.0'],
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
      cmdclass={'test': TestDiscoverCommand},
)

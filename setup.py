#!/usr/bin/env python

# Copyright (c) 2010, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses


# bootstrap setuptools if necessary
import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages

import imapclient
version = imapclient.__version__

desc = """\
IMAPClient aims to be a easy-to-use, Pythonic and complete IMAP client library with no dependencies outside the Python standard library.

Features:
    * Arguments and return values are natural Python types.
    * IMAP server responses are fully parsed and readily usable.
    * IMAP unique message IDs (UIDs) are handled transparently.
    * Internationalised mailbox names are transparently handled.
    * Time zones are correctly handled.
    * Convenience methods are provided for commonly used functionality.
    * Exceptions are raised when errors occur.

IMAPClient includes units tests for more complex functionality and a automated functional test that can be run against a live IMAP server.
"""

#XXX put "test" command support back in
setup(name='IMAPClient',
      version=version,
      author="Menno Smits",
      author_email="menno@freshfoo.com",
      license="http://en.wikipedia.org/wiki/BSD_licenses",
      url="http://imapclient.freshfoo.com/",
      download_url='http://freshfoo.com/projects/IMAPClient/IMAPClient-%s.tar.gz' % version,
      packages=find_packages(),
      description="Easy-to-use, Pythonic and complete IMAP client library with "
          "no dependencies outside the Python standard library.",
      long_description=desc,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Natural Language :: English',
          'Programming Language :: Python',
          'Topic :: Communications :: Email :: Post-Office :: IMAP',
          'Topic :: Internet',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Networking'])

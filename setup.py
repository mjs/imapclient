#!/usr/bin/env python

# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses


# bootstrap setuptools if necessary
from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup
import imapclient
version = imapclient.__version__

desc = """\
IMAPClient aims to be a easy-to-use, Pythonic and complete IMAP client library with no dependencies outside the Python standard library.

Features:
    * Arguments and return values are natural Python types.
    * IMAP server responses are fully parsed and readily useable.
    * IMAP unique message IDs (UIDs) are handled transparently.
    * Internationalised mailbox names are transparently handled.
    * Time zones are correctly handled.
    * Convenience methods are provided for commonly used functionality.
    * Exceptions are raised when errors occur.

IMAPClient includes units tests for more complex functionality and a automated functional test that can be run against a live IMAP server.
"""

setup(
        name='IMAPClient',
        version=version,
        author="Menno Smits",
        author_email="menno@freshfoo.com",
        license="http://en.wikipedia.org/wiki/BSD_licenses",
        url="http://imapclient.freshfoo.com/",
        download_url='http://freshfoo.com/projects/IMAPClient/IMAPClient-%s.tar.gz' % version,
        packages=['imapclient', 'imapclient.test'],
        test_suite='imapclient.test.load_suite',
        py_modules=[],
        install_requires=[],
        description="Easy-to-use, Pythonic and complete IMAP client library with "
            "no dependencies outside the Python standard library.",
        long_description=desc,
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Natural Language :: English',
            'Programming Language :: Python',
            'Topic :: Communications :: Email :: Post-Office :: IMAP',
            'Topic :: Internet',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: System :: Networking'])

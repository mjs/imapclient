# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

try:
    from unittest.mock import Mock, patch, sentinel, DEFAULT
except ImportError:
    from mock import Mock, patch, sentinel, DEFAULT


def find_unittest2():
    import unittest
    if hasattr(unittest, 'skip') and hasattr(unittest, 'loader'):
        return unittest    # unittest from stdlib is unittest2, use that
    try:
        import unittest2   # try for a separately installed unittest2 package
    except ImportError:
        raise ImportError(
            'unittest2 not installed and unittest in standard library is not unittest2')
    else:
        return unittest2

unittest = find_unittest2()


def patch_TestCase():
    TestCase = unittest.TestCase
    # Older versions of unittest2 don't have
    # TestCase.assertRaisesRegex and newer version raises warnings
    # when you use assertRaisesRegexp. This helps deal with the
    # mismatch.
    if not hasattr(TestCase, 'assertRaisesRegex'):
        TestCase.assertRaisesRegex = TestCase.assertRaisesRegexp

patch_TestCase()

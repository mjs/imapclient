# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

from six import binary_type, text_type


def to_unicode(s):
    if isinstance(s, binary_type):
        return s.decode('ascii')
    return s


def to_bytes(s, charset='ascii'):
    if isinstance(s, text_type):
        return s.encode(charset)
    return s

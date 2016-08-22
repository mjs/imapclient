# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

version_info = (1, 0, 2, 'final')


def _imapclient_version_string(vinfo):
    major, minor, micro, releaselevel = vinfo
    v = '%d.%d.%d' % (major, minor, micro)
    if releaselevel != 'final':
        v += '-' + releaselevel
    return v

version = _imapclient_version_string(version_info)
author = 'Menno Smits'
author_email = 'menno@freshfoo.com'

min_pyopenssl_version = '0.15.1'

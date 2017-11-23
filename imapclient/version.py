# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

version_info = (1, 1, 0, 'final')


def _imapclient_version_string(vinfo):
    major, minor, micro, releaselevel = vinfo
    v = '%d.%d.%d' % (major, minor, micro)
    if releaselevel != 'final':
        v += '-' + releaselevel
    return v

version = _imapclient_version_string(version_info)

maintainer = 'IMAPClient Maintainers'
maintainer_email = 'imapclient@groups.io'

author = 'Menno Finlay-Smits'
author_email = 'inbox@menno.io'

min_pyopenssl_version = '0.15.1'

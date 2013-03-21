# Copyright (c) 2012, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

# version_info provides the version number in programmer friendly way.
# The 4th part will be either alpha, beta or final.

from __future__ import unicode_literals

version_info = (0, 9, 0, 'final')

def _imapclient_version_string(vinfo):
    major, minor, micro, releaselevel = vinfo
    v = '%d.%d' % (major, minor)
    if micro != 0:
        v += '.%d' % micro
    if releaselevel != 'final':
        v += '-' + releaselevel
    return v

__version__ = _imapclient_version_string(version_info)
__author__ = 'Menno Smits <menno@freshfoo.com>'

from .imapclient import *
from .response_parser import *

from .imaplib_ssl_fix import apply_patch
apply_patch()

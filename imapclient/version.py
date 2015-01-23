# -*- coding: utf-8 -*-

version_info = (1, 0, 0, 'alpha')

def _imapclient_version_string(vinfo):
    major, minor, micro, releaselevel = vinfo
    v = '%d.%d' % (major, minor)
    if micro != 0:
        v += '.%d' % micro
    if releaselevel != 'final':
        v += '-' + releaselevel
    return v

version = _imapclient_version_string(version_info)
author = 'Menno Smits'
author_email = 'menno@freshfoo.com'

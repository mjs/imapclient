# -*- coding: utf-8 -*-

version_info = (0, 11, 0, 'final')

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

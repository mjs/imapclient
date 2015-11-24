# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
Work-around for Python Issue 5943 (http://bugs.python.org/issue5949).

This will patch imaplib's IMAP4_SSL.readline method with the fixed
verion in Python versions that are known to have the problem.

The problem definitely exists in Python 2.5 and 2.6 up until but not
including 2.6.5. It was also fixed in Python 2.7 alpha 2 so no attempt
is made to patch 2.7 versions.

Please let me know if there's more Python versions that should be
patched.

Efforts are made to only perform the patch once.
"""

from __future__ import unicode_literals

import sys
import imaplib


def _is_affected_version(sys_version):
    sys_version = sys_version[:3]
    if sys_version < (2, 5, 0):
        # Not sure whether these old versions are affected so being
        # conservative and not patching.
        return False
    elif sys_version < (2, 6, 5):
        return True
    return False


def _fixed_readline(self):
    """Read line from remote."""
    line = []
    while True:
        char = self.sslobj.read(1)
        line.append(char)
        if char in ("\n", ""):
            return ''.join(line)

_fixed_readline.patched = True    # Marker to indicate patched version

ssl_class = imaplib.IMAP4_SSL


def apply_patch():
    if _is_affected_version(sys.version_info) and not hasattr(ssl_class.readline, 'patched'):
        ssl_class.readline = _fixed_readline

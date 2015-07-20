# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

# version_info provides the version number in programmer friendly way.
# The 4th part will be either alpha, beta or final.

from __future__ import unicode_literals

from .imapclient import *
from .response_parser import *
from .tls import *
from .version import author as __author__, version as __version__, version_info

from .imaplib_ssl_fix import apply_patch
apply_patch()

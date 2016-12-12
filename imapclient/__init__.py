# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

# version_info provides the version number in programmer friendly way.
# The 4th part will be either alpha, beta or final.

from __future__ import unicode_literals

from .version import author as __author__, version as __version__, version_info
from .imapclient import *
from .response_parser import *
# if backports.ssl is importable use it with our own ssl wrapper
# otherwise use the ssl module, that was shipped with python{2,3}
try:
    import backports.ssl
except ImportError:
    import ssl as tls
else:
    del backports.ssl
    from . import tls
    from .imaplib_ssl_fix import apply_patch
    apply_patch()

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import logging
from six import binary_type, text_type

from . import exceptions

logger = logging.getLogger(__name__)


def to_unicode(s):
    if isinstance(s, binary_type):
        try:
            return s.decode('ascii')
        except UnicodeDecodeError:
            logger.warning(
                "An error occurred while decoding %s in ASCII 'strict' mode. Fallback to "
                "'ignore' errors handling, some characters might have been stripped", s
            )
            return s.decode('ascii', 'ignore')
    return s


def to_bytes(s, charset='ascii'):
    if isinstance(s, text_type):
        return s.encode(charset)
    return s


def assert_imap_protocol(condition, message=None):
    if not condition:
        msg = "Server replied with a response that violates the IMAP protocol"
        if message:
            msg += "{}: {}".format(msg, message)
        raise exceptions.ProtocolError(msg)

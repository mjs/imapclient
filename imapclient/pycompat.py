"""
Further Python 2/3 compatibility helpers that aren't provided by six.
"""

from __future__ import unicode_literals

from .six import PY3, int2byte

if PY3:
    def iter_as_bytes(some_bytes):
        for c in some_bytes[:]:
            yield int2byte(c)

    # XXX consider alternative name
    def to_native_str(some_bytes):
        return some_bytes.decode('latin-1')

else:
    def iter_as_bytes(a_str):
        return iter(a_str)

    def to_native_str(some_bytes):
        return some_bytes

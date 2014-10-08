# -*- coding: utf-8 -*-
"""STARTTLS support for imaplib for Python 2.6+ and 3.3+ built on pyOpenSSL."""

__all__ = ('IMAP4', 'ssl_default_context')

import sys
import imaplib

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

if sys.platform == "win32":
    try:
        from ssl import enum_certificates, Purpose
    except ImportError:
        enum_certificates = lambda x: []

# third-party dependencies
from six import b, binary_type
from OpenSSL import SSL
from service_identity import VerificationError
from service_identity.pyopenssl import verify_hostname


# add STARTTLS command support in imaplib if necessary
if 'STARTTLS' not in imaplib.Commands:
    imaplib.Commands['STARTTLS'] = ('NONAUTH',)

# taken from Python 3.4 ssl module
_RESTRICTED_SERVER_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5:!DSS:!RC4'
)


def ssl_default_context(cafile=None, capath=None, check_hostname=True):
    """Create a SSL.Context object with reasonably secure default settings.

    This SSL context is configured only to be used for client connections, do
    not use it for a server connection.

    """
    # adapted from Python 3.4 ssl.create_default_context

    context = SSL.Context(SSL.SSLv23_METHOD)
    context.check_hostname = check_hostname

    # SSLv2 considered harmful.
    options = SSL.OP_NO_SSLv2

    # SSLv3 has problematic security and is only required for really old
    # clients such as IE6 on Windows XP
    options |= SSL.OP_NO_SSLv3

    # disable compression to prevent CRIME attacks (OpenSSL 1.0+)
    options |= getattr(SSL, "OP_NO_COMPRESSION", 0)

    options |= SSL.OP_CIPHER_SERVER_PREFERENCE

    # Use single use keys in order to improve forward secrecy
    options |= SSL.OP_SINGLE_DH_USE
    options |= getattr(SSL, "OP_SINGLE_ECDH_USE", 0)

    context.set_options(options)

    # disallow ciphers with known vulnerabilities
    context.set_cipher_list(_RESTRICTED_SERVER_CIPHERS)

    context.set_verify(SSL.VERIFY_PEER,
        lambda conn, cert, errnum, errdepth, ok: ok)

    if cafile or capath:
        context.load_verify_locations(cafile, capath)
    else:
        # no explicit cafile, capath. Let's try to load default system
        # root CA certificates for the given purpose. This may fail silently.

        if sys.platform == "win32":
            certs = bytearray()
            for storename in ("CA", "ROOT"):
                for cert, encoding, trust in enum_certificates(storename):
                    # CA certs are never PKCS#7 encoded
                    if encoding == "x509_asn":
                        if trust is True or Purpose.SERVER_AUTH in trust:
                            certs.extend(cert)

            if certs:
                context.load_verify_locations(cadata=certs)
        else:
            context.set_default_verify_paths()

    return context


class _SSLConnection(SSL.Connection):
    """Wrapper for OpenSSL.SSL.Connection for socket compatibility."""

    def shutdown(self, *args):
        # Fix method signature incompatibility bewteen pyOpenSSL.SSL.Connection
        # and socket.socket
        SSL.Connection.shutdown(self)

    def makefile(self, mode='rb', *args, **kwargs):
        # Support only arguments needed by imaplib
        return _socketfileobj(self, mode)


class IMAP4(imaplib.IMAP4):
    def starttls(self, ssl_context=None):
        """Send a STARTTLS command and wrap the socket with TLS."""
        name = 'STARTTLS'

        if (isinstance(self, imaplib.IMAP4_SSL) or
                getattr(self, '_tls_established', False)):
            raise self.abort('TLS session already established')

        if name not in self.capabilities:
            raise self.abort('STARTTLS not supported by server')

        if not ssl_context:
            ssl_context = ssl_default_context()

        type_, dat = self._simple_command(name)

        if type_ == 'OK':
            self.sock = _SSLConnection(ssl_context, self.sock)
            self.sock.set_connect_state()
            self.sock.do_handshake()

            if getattr(ssl_context, 'check_hostname', True):
                try:
                    verify_hostname(self.sock, self.host)
                except VerificationError:
                    self.sock.shutdown()
                    self.sock.close()
                    raise self.abort(
                        "Server certificate not valid for %s" % self.host)

            self.file = self.sock.makefile()
            self._tls_established = True
        else:
            raise self.Error("Couldn't establish TLS session")

        return self._untagged_response(type_, dat, name)


# lifted from backports.ssl
class _socketfileobj(object):
    """Custom file-like object to support socket.makefile for pyOpenSSL."""

    default_bufsize = 8192
    name = "<socket>"

    __slots__ = ["mode", "bufsize", "softspace", "_sock", "_rbufsize",
        "_wbufsize", "_rbuf", "_wbuf", "_wbuf_len", "_close"]
    # "closed" is a property, see below

    def __init__(self, sock, mode='rb', bufsize=-1, close=False):
        self._sock = sock
        # Not actually used in this version
        self.mode = mode
        if bufsize < 0:
            bufsize = self.default_bufsize
        self.bufsize = bufsize
        self.softspace = False
        # _rbufsize is the suggested recv buffer size.  It is *strictly*
        # obeyed within readline() for recv calls.  If it is larger than
        # default_bufsize it will be used for recv calls within read().
        if bufsize == 0:
            self._rbufsize = 1
        elif bufsize == 1:
            self._rbufsize = self.default_bufsize
        else:
            self._rbufsize = bufsize
        self._wbufsize = bufsize
        # We use BytesIO for the read buffer to avoid holding a list
        # of variously sized string objects which have been known to
        # fragment the heap due to how they are malloc()ed and often
        # realloc()ed down much smaller than their original allocation.
        self._rbuf = BytesIO()
        self._wbuf = []  # A list of strings
        self._wbuf_len = 0
        self._close = close

    def _getclosed(self):
        return self._sock is None
    closed = property(_getclosed, doc="True if the file is closed")

    def close(self):
        try:
            if self._sock:
                self.flush()
        finally:
            if self._close:
                self._sock.close()
            self._sock = None

    def __del__(self):
        try:
            self.close()
        except:
            # close() may fail if __init__ didn't complete
            pass

    def flush(self):
        if self._wbuf:
            data = b('').join(self._wbuf)
            self._wbuf = []
            self._wbuf_len = 0
            buffer_size = max(self._rbufsize, self.default_bufsize)
            data_size = len(data)
            write_offset = 0
            view = memoryview(data)
            try:
                while write_offset < data_size:
                    self._sock.sendall(
                        view[write_offset:write_offset + buffer_size])
                    write_offset += buffer_size
            finally:
                if write_offset < data_size:
                    remainder = data[write_offset:]
                    del view, data  # explicit free
                    self._wbuf.append(remainder)
                    self._wbuf_len = len(remainder)

    def fileno(self):
        return self._sock.fileno()

    def write(self, data):
        # XXX Should really reject non-string non-buffers
        data = binary_type(data)
        if not data:
            return
        self._wbuf.append(data)
        self._wbuf_len += len(data)
        if (self._wbufsize == 0 or (self._wbufsize == 1 and b('\n') in data) or
                (self._wbufsize > 1 and self._wbuf_len >= self._wbufsize)):
            self.flush()

    def writelines(self, list):
        # XXX We could do better here for very long lists
        # XXX Should really reject non-string non-buffers
        lines = filter(None, map(binary_type, list))
        self._wbuf_len += sum(map(len, lines))
        self._wbuf.extend(lines)
        if self._wbufsize <= 1 or self._wbuf_len >= self._wbufsize:
            self.flush()

    def read(self, size=-1):
        # Use max, disallow tiny reads in a loop as they are very inefficient.
        # We never leave read() with any leftover data from a new recv() call
        # in our internal buffer.
        rbufsize = max(self._rbufsize, self.default_bufsize)
        # Our use of BytesIO rather than lists of string objects returned by
        # recv() minimizes memory usage and fragmentation that occurs when
        # rbufsize is large compared to the typical return value of recv().
        buf = self._rbuf
        buf.seek(0, 2)  # seek end
        if size < 0:
            # Read until EOF
            self._rbuf = BytesIO()  # reset _rbuf.  we consume it via buf.
            data = self._sock.recv(rbufsize)
            buf.write(data)
            return buf.getvalue()
        else:
            # Read until size bytes or EOF seen, whichever comes first
            buf_len = buf.tell()
            if buf_len >= size:
                # Already have size bytes in our buffer?  Extract and return.
                buf.seek(0)
                rv = buf.read(size)
                self._rbuf = BytesIO()
                self._rbuf.write(buf.read())
                return rv

            self._rbuf = BytesIO()  # reset _rbuf.  we consume it via buf.
            while True:
                left = size - buf_len
                # recv() will malloc the amount of memory given as its
                # parameter even though it often returns much less data
                # than that.  The returned data string is short lived
                # as we copy it into a BytesIO and free it.  This avoids
                # fragmentation issues on many platforms.
                data = self._sock.recv(left)
                if not data:
                    break
                n = len(data)
                if n == size and not buf_len:
                    # Shortcut.  Avoid buffer data copies when:
                    # - We have no data in our buffer.
                    # AND
                    # - Our call to recv returned exactly the
                    #   number of bytes we were asked to read.
                    return data
                if n == left:
                    buf.write(data)
                    del data  # explicit free
                    break
                assert n <= left, "recv(%d) returned %d bytes" % (left, n)
                buf.write(data)
                buf_len += n
                del data  # explicit free
                #assert buf_len == buf.tell()
            return buf.getvalue()

    def readline(self, size=-1):
        buf = self._rbuf
        buf.seek(0, 2)  # seek end
        if buf.tell() > 0:
            # check if we already have it in our buffer
            buf.seek(0)
            bline = buf.readline(size)
            if bline.endswith(b('\n')) or len(bline) == size:
                self._rbuf = BytesIO()
                self._rbuf.write(buf.read())
                return bline
            del bline
        if size < 0:
            # Read until \n or EOF, whichever comes first
            if self._rbufsize <= 1:
                # Speed up unbuffered case
                buf.seek(0)
                buffers = [buf.read()]
                self._rbuf = BytesIO()  # reset _rbuf.  we consume it via buf.
                data = None
                while data != b('\n'):
                    data = self._sock.recv(1)
                    if not data:
                        break
                    buffers.append(data)
                return b('').join(buffers)

            buf.seek(0, 2)  # seek end
            self._rbuf = BytesIO()  # reset _rbuf.  we consume it via buf.
            while True:
                data = self._sock.recv(self._rbufsize)
                if not data:
                    break
                nl = data.find(b('\n'))
                if nl >= 0:
                    nl += 1
                    buf.write(data[:nl])
                    self._rbuf.write(data[nl:])
                    del data  # explicit free
                    break
                buf.write(data)
            return buf.getvalue()
        else:
            # Read until size bytes or \n or EOF seen, whichever comes first
            buf.seek(0, 2)  # seek end
            buf_len = buf.tell()
            if buf_len >= size:
                buf.seek(0)
                rv = buf.read(size)
                self._rbuf = BytesIO()
                self._rbuf.write(buf.read())
                return rv
            self._rbuf = BytesIO()  # reset _rbuf.  we consume it via buf.
            while True:
                data = self._sock.recv(self._rbufsize)
                if not data:
                    break
                left = size - buf_len
                # did we just receive a newline?
                nl = data.find(b('\n'), 0, left)
                if nl >= 0:
                    nl += 1
                    # save the excess data to _rbuf
                    self._rbuf.write(data[nl:])
                    if buf_len:
                        buf.write(data[:nl])
                        break
                    else:
                        # Shortcut.  Avoid data copy through buf when returning
                        # a substring of our first recv().
                        return data[:nl]
                n = len(data)
                if n == size and not buf_len:
                    # Shortcut.  Avoid data copy through buf when
                    # returning exactly all of our first recv().
                    return data
                if n >= left:
                    buf.write(data[:left])
                    self._rbuf.write(data[left:])
                    break
                buf.write(data)
                buf_len += n
                #assert buf_len == buf.tell()
            return buf.getvalue()

    def readlines(self, sizehint=0):
        total = 0
        list = []
        while True:
            line = self.readline()
            if not line:
                break
            list.append(line)
            total += len(line)
            if sizehint and total >= sizehint:
                break
        return list

    # Iterator protocols

    def __iter__(self):
        return self

    def next(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
This module contains IMAPClient's functionality related to Transport
Layer Security (TLS a.k.a. SSL).

It uses ``backports.ssl`` to provide consistent TLS functionality
across Python versions.
"""

import imaplib
import os
import socket
import sys

__all__ = ('create_default_context',)

# Explicitly check that the required pyOpenSSL is installed. On some
# systems (particularly OS X) the system installed version will be
# seen before any user installed version. Using a virtualenv is
# recommended to work around this.
def check_pyopenssl_version():
    from distutils.version import LooseVersion as V
    from OpenSSL import __version__ as installed_pyopenssl_version
    from .version import min_pyopenssl_version

    if V(installed_pyopenssl_version) < V(min_pyopenssl_version):
       raise ImportError(
           "pyOpenSSL version (%s) is too old. Need at least %s.\n"
           "See http://imapclient.rtfd.io/#old-pyopenssl-versions"
           % (installed_pyopenssl_version, min_pyopenssl_version))

if os.environ.get("READTHEDOCS") != "True":
    check_pyopenssl_version()

try:
    from backports import ssl
except ImportError:
    raise ImportError("backports.ssl is not installed")

_ossl = ssl.ossl

if sys.platform == "win32":
    try:
        from ssl import enum_certificates, Purpose
    except ImportError:
        enum_certificates = lambda x: []


# taken from Python 3.4 ssl module
_RESTRICTED_SERVER_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5:!DSS:!RC4'
)

# TODO: get this into backports.ssl


def create_default_context(cafile=None, capath=None, cadata=None):
    """Return a backports.ssl.SSLContext object configured with sensible
    default settings.

    The optional *cafile* argument is path to a file of concatenated
    CA certificates in PEM format.

    The optional *capath* argument is a path to a directory containing
    several CA certificates in PEM format, following an OpenSSL
    specific layout.

    The optional *cadata* argument is either an ASCII string of one or
    more PEM-encoded certificates or a bytes-like object of
    DER-encoded certificates.

    If *cafile*, *capath* and *cadata* are all None then
    system-installed CA certificates will be loaded (if available).

    """
    # adapted from Python 3.4's ssl.create_default_context

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    # require certificate that matches the host name.
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True

    # SSLv2 considered harmful.
    context.options |= _ossl.OP_NO_SSLv2

    # SSLv3 has problematic security and is only required for really old
    # clients such as IE6 on Windows XP
    context.options |= _ossl.OP_NO_SSLv3

    # disable compression to prevent CRIME attacks (OpenSSL 1.0+)
    context.options |= getattr(_ossl, "OP_NO_COMPRESSION", 0)

    # Prefer the server's ciphers by default so that we get stronger
    # encryption
    context.options |= getattr(_ossl, "OP_CIPHER_SERVER_PREFERENCE", 0)

    # Use single use keys in order to improve forward secrecy
    context.options |= getattr(_ossl, "OP_SINGLE_DH_USE", 0)
    context.options |= getattr(_ossl, "OP_SINGLE_ECDH_USE", 0)

    # disallow ciphers with known vulnerabilities
    # TODO: backports.ssl.SSLContext is missing set_ciphers
    context._ctx.set_cipher_list(_RESTRICTED_SERVER_CIPHERS)

    if cafile or capath or cadata:
        context.load_verify_locations(cafile, capath, cadata)
    elif context.verify_mode != ssl.CERT_NONE:
        # no explicit cafile, capath or cadata but the verify mode is
        # CERT_OPTIONAL or CERT_REQUIRED. Let's try to load default system
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


def wrap_socket(sock, ssl_context, hostname):
    """Wrap a socket and return an SSLSocket.

    If *ssl_context* is `None`, a default context as returned by
    `create_default_context` will be used.

    If certificate validation fails, the socket will be shut down and
    an Error raised.
    """
    if not ssl_context:
        ssl_context = create_default_context()

    def killsock():
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

    try:
        newsock = ssl_context.wrap_socket(sock, server_hostname=hostname)
    except ssl.CertificateError as err:
        killsock()
        raise imaplib.IMAP4.error("certificate error for %s: %s" % (hostname, str(err)))
    except ssl.SSLError as err:
        killsock()
        raise imaplib.IMAP4.error("SSL error for %s: %s" % (hostname, err.args[-1]))

    return _SSLSocketWithShutdown(newsock)


class IMAP4_TLS(imaplib.IMAP4):
    """IMAP4 client class for TLS/SSL connections.

    Adapted from imaplib.IMAP4_SSL.
    """

    def __init__(self, host, port, ssl_context, timeout):
        self.ssl_context = ssl_context
        self._timeout = timeout
        imaplib.IMAP4.__init__(self, host, port)

    def open(self, host, port):
        self.host = host
        self.port = port
        sock = socket.create_connection((host, port), self._timeout)
        self.sock = wrap_socket(sock, self.ssl_context, host)
        self.file = self.sock.makefile('rb')

    def read(self, size):
        return self.file.read(size)

    def readline(self):
        return self.file.readline()

    def send(self, data):
        remaining = len(data)
        while remaining > 0:
            sent = self.sock.send(data)
            if sent == remaining:
                break
            data = data[sent:]
            remaining -= sent

    def shutdown(self):
        self.file.close()
        self.sock._conn.shutdown()
        self.sock.close()


# TODO: get shutdown added in backports.ssl.SSLSocket
class _SSLSocketWithShutdown(object):

    def __init__(self, sslsock):
        self.sslsock = sslsock

    def shutdown(self, how):
        return self.sslsock._conn.sock_shutdown(how)

    def __getattr__(self, name):
        return getattr(self.sslsock, name)

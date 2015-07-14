# -*- coding: utf-8 -*-

"""
Solid TLS support for Python 2.6+ and 3.3+ built on backports.ssl/pyOpenSSL.
"""

__all__ = ('create_default_context', 'wrap_socket')


import sys
import imaplib

from backports import ssl
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
    """Create a SSLContext object with sensible default settings.
    """
    # adapted from Python 3.4's ssl.create_default_context

    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)

    # do certificate hostname checks.
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

    try:
        return ssl_context.wrap_socket(sock, server_hostname=hostname)
    except ssl.CertificateError:
        sock.shutdown()
        sock.close()
        raise imaplib.Error("server certificate not valid for %s" % hostname)

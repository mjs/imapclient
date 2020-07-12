"""
Low Level IMAP Connection
"""


import errno
import socket
import subprocess
import sys
from io import DEFAULT_BUFFER_SIZE
from logging import getLogger
from . import exceptions

try:
    import ssl
    HAVE_SSL = True
except ImportError:
    HAVE_SSL = False

# Maximal line length when calling readline(). This is to prevent
# reading arbitrary length lines. RFC 3501 and 2060 (IMAP 4rev1)
# don't specify a line length. RFC 2683 suggests limiting client
# command lines to 1000 octets and that servers should be prepared
# to accept command lines up to 8000 octets, so we used to use 10K here.
# In the modern world (eg: gmail) the response to, for example, a
# search command can be quite large, so we now use 1M.
_MAXLINE = 1000000

IMAP4_PORT = 143
IMAP4_SSL_PORT = 993

logger = getLogger(__name__)

class IMAP4:
    def __init__(self, host='', port=IMAP4_PORT):
        self.open(host, port)

    def _create_socket(self):
        # Default value of IMAP4.host is '', but socket.getaddrinfo()
        # (which is used by socket.create_connection()) expects None
        # as a default value for host.
        host = None if not self.host else self.host
        sys.audit("imaplib.open", self, self.host, self.port)
        return socket.create_connection((host, self.port))

    def open(self, host = '', port = IMAP4_PORT):
        """Setup connection to remote server on "host:port"
            (default: localhost:standard IMAP4 port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = host
        self.port = port
        self.sock = self._create_socket()
        self.file = self.sock.makefile('rb')

    def read(self, size):
        """Read 'size' bytes from remote."""
        return self.file.read(size)

    def readline(self):
        """Read line from remote."""
        line = self.file.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            raise exceptions.IMAPClientError("got more than %d bytes" % _MAXLINE)
        return line

    def get_line(self):

        line = self.readline()
        if not line:
            raise exceptions.IMAPClientAbortError('socket error: EOF')

        # Protocol mandates all lines terminated by CRLF
        if not line.endswith(b'\r\n'):
            raise exceptions.IMAPClientAbortError('socket error: unterminated line: %r' % line)

        line = line[:-2]
        if __debug__:
            logger.debug('< %r' % line)
        return line

    def send(self, data):
        """Send data to remote."""
        sys.audit("imaplib.send", self, data)
        self.sock.sendall(data)

    def shutdown(self):
        """Close I/O established in "open"."""
        self.file.close()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError as exc:
            # The server might already have closed the connection.
            # On Windows, this may result in WSAEINVAL (error 10022):
            # An invalid operation was attempted.
            if (exc.errno != errno.ENOTCONN
                    and getattr(exc, 'winerror', 0) != 10022):
                raise
        finally:
            self.sock.close()

    def socket(self):
        """Return socket instance used to connect to IMAP4 server.

        socket = <instance>.socket()
        """
        return self.sock


class IMAP4_SSL(IMAP4):

    """IMAP4 client class over SSL connection

    Instantiate with: IMAP4_SSL([host[, port[, keyfile[, certfile[, ssl_context]]]]])

            host - host's name (default: localhost);
            port - port number (default: standard IMAP4 SSL port);
            keyfile - PEM formatted file that contains your private key (default: None);
            certfile - PEM formatted certificate chain file (default: None);
            ssl_context - a SSLContext object that contains your certificate chain
                          and private key (default: None)
            Note: if ssl_context is provided, then parameters keyfile or
            certfile should not be set otherwise ValueError is raised.

    for more documentation see the docstring of the parent class IMAP4.
    """
    def __init__(self, host='', port=IMAP4_SSL_PORT, keyfile=None,
                 certfile=None, ssl_context=None):

        if not HAVE_SSL:
            raise ValueError('SSL support missing')

        if ssl_context is not None and keyfile is not None:
            raise ValueError("ssl_context and keyfile arguments are mutually "
                             "exclusive")
        if ssl_context is not None and certfile is not None:
            raise ValueError("ssl_context and certfile arguments are mutually "
                             "exclusive")
        if keyfile is not None or certfile is not None:
            import warnings
            warnings.warn("keyfile and certfile are deprecated, use a "
                          "custom ssl_context instead", DeprecationWarning, 2)
        self.keyfile = keyfile
        self.certfile = certfile
        if ssl_context is None:
            ssl_context = ssl._create_stdlib_context(certfile=certfile,
                                                     keyfile=keyfile)
        self.ssl_context = ssl_context
        IMAP4.__init__(self, host, port)

    def _create_socket(self):
        sock = IMAP4._create_socket(self)
        return self.ssl_context.wrap_socket(sock,
                                            server_hostname=self.host)

    def open(self, host='', port=IMAP4_SSL_PORT):
        """Setup connection to remote server on "host:port".
            (default: localhost:standard IMAP4 SSL port).
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        IMAP4.open(self, host, port)

class IMAP4_stream(IMAP4):

    """IMAP4 client class over a stream

    Instantiate with: IMAP4_stream(command)

            "command" - a string that can be passed to subprocess.Popen()

    for more documentation see the docstring of the parent class IMAP4.
    """
    def __init__(self, command):
        self.command = command
        IMAP4.__init__(self)

    def open(self, host = None, port = None):
        """Setup a stream connection.
        This connection will be used by the routines:
            read, readline, send, shutdown.
        """
        self.host = None        # For compatibility with parent class
        self.port = None
        self.sock = None
        self.file = None
        self.process = subprocess.Popen(self.command,
                                        bufsize=DEFAULT_BUFFER_SIZE,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        shell=True, close_fds=True)
        self.writefile = self.process.stdin
        self.readfile = self.process.stdout

    def read(self, size):
        """Read 'size' bytes from remote."""
        return self.readfile.read(size)

    def readline(self):
        """Read line from remote."""
        return self.readfile.readline()

    def send(self, data):
        """Send data to remote."""
        self.writefile.write(data)
        self.writefile.flush()

    def shutdown(self):
        """Close I/O established in "open"."""
        self.readfile.close()
        self.writefile.close()
        self.process.wait()


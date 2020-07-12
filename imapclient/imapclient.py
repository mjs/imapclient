# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

import functools
import itertools
import random
import re
import select
import socket
import sys
from collections import namedtuple
from datetime import datetime, date
from logging import getLogger
from operator import itemgetter

from six import moves, iteritems, text_type, integer_types, PY3, binary_type, iterbytes

from . import conn
from . import exceptions
from . import imap4
from . import response_lexer
from . import tls
from . import util
from .datetime_util import datetime_to_INTERNALDATE, format_criteria_date
from .imap_utf7 import encode as encode_utf7, decode as decode_utf7
from .response_parser import parse_response, parse_message_list, parse_fetch_response
from .util import to_bytes, to_unicode, assert_imap_protocol, chunk

xrange = moves.xrange

try:
    import ssl
except ImportError:
    ssl = None

try:
    from select import poll

    POLL_SUPPORT = True
except:
    # Fallback to select() on systems that don't support poll()
    POLL_SUPPORT = False

if PY3:
    long = int  # long is just int in python3

logger = getLogger(__name__)
imaplib_logger = getLogger(__name__ + '.imaplib')

__all__ = ['IMAPClient', 'SocketTimeout',
           'DELETED', 'SEEN', 'ANSWERED', 'FLAGGED', 'DRAFT', 'RECENT']

# System flags
DELETED = br'\Deleted'
SEEN = br'\Seen'
ANSWERED = br'\Answered'
FLAGGED = br'\Flagged'
DRAFT = br'\Draft'
RECENT = br'\Recent'  # This flag is read-only

# Special folders, see RFC6154
# \Flagged is omitted because it is the same as the flag defined above
ALL = br'\All'
ARCHIVE = br'\Archive'
DRAFTS = br'\Drafts'
JUNK = br'\Junk'
SENT = br'\Sent'
TRASH = br'\Trash'

# Personal namespaces that are common among providers
# used as a fallback when the server does not support the NAMESPACE capability
_POPULAR_PERSONAL_NAMESPACES = (("", ""), ("INBOX.", "."))

# Names of special folders that are common among providers
_POPULAR_SPECIAL_FOLDERS = {
    SENT: ("Sent", "Sent Items", "Sent items"),
    DRAFTS: ("Drafts",),
    ARCHIVE: ("Archive",),
    TRASH: ("Trash", "Deleted Items", "Deleted Messages"),
    JUNK: ("Junk", "Spam")
}

_RE_SELECT_RESPONSE = re.compile(br'\[(?P<key>[A-Z-]+)( \((?P<data>.*)\))?\]')


class Namespace(tuple):

    def __new__(cls, personal, other, shared):
        return tuple.__new__(cls, (personal, other, shared))

    personal = property(itemgetter(0))
    other = property(itemgetter(1))
    shared = property(itemgetter(2))


class SocketTimeout(namedtuple("SocketTimeout", "connect read")):
    """Represents timeout configuration for an IMAP connection.

    :ivar connect: maximum time to wait for a connection attempt to remote server
    :ivar read: maximum time to wait for performing a read/write operation

    As an example, ``SocketTimeout(connect=15, read=60)`` will make the socket
    timeout if the connection takes more than 15 seconds to establish but
    read/write operations can take up to 60 seconds once the connection is done.
    """


class MailboxQuotaRoots(namedtuple("MailboxQuotaRoots", "mailbox quota_roots")):
    """Quota roots associated with a mailbox.

    Represents the response of a GETQUOTAROOT command.

    :ivar mailbox: the mailbox
    :ivar quota_roots: list of quota roots associated with the mailbox
    """


class Quota(namedtuple("Quota", "quota_root resource usage limit")):
    """Resource quota.

    Represents the response of a GETQUOTA command.

    :ivar quota_roots: the quota roots for which the limit apply
    :ivar resource: the resource being limited (STORAGE, MESSAGES...)
    :ivar usage: the current usage of the resource
    :ivar limit: the maximum allowed usage of the resource
    """


def require_capability(capability):
    """Decorator raising CapabilityError when a capability is not available."""

    def actual_decorator(func):
        @functools.wraps(func)
        def wrapper(client, *args, **kwargs):
            if not client.has_capability(capability):
                raise exceptions.CapabilityError(
                    'Server does not support {} capability'.format(capability)
                )
            return func(client, *args, **kwargs)

        return wrapper

    return actual_decorator


#       Patterns to match server responses

CRLF = b'\r\n'
AllowedVersions = ('IMAP4REV1', 'IMAP4')  # Most recent first

Continuation = re.compile(br'\+( (?P<data>.*))?')

MapCRLF = re.compile(br'\r\n|\r|\n')
# We no longer exclude the ']' character from the data portion of the response
# code, even though it violates the RFC.  Popular IMAP servers such as Gmail
# allow flags with ']', and there are programs (including imaplib!) that can
# produce them.  The problem with this is if the 'text' portion of the response
# includes a ']' we'll parse the response wrong (which is the point of the RFC
# restriction).  However, that seems less likely to be a problem in practice
# than being unable to correctly parse flags that include ']' chars, which
# was reported as a real-world problem in issue #21815.
Response_code = re.compile(br'\[(?P<type>[A-Z-]+)( (?P<data>.*))?\]')
Untagged_response = re.compile(br'\* (?P<type>[A-Z-]+)( (?P<data>.*))?')
Literal = re.compile(br'.*{(?P<size>\d+)}$')
Untagged_status = re.compile(br'\* (?P<data>\d+) (?P<type>[A-Z-]+)( (?P<data2>.*))?')

def _check_resp(expected, command, typ, data):
    """Check command responses for errors.

    Raises IMAPClient.Error if the command fails.
    """
    if typ != expected:
        raise exceptions.IMAPClientError("%s failed: %s" % (command, to_unicode(data[0])))


class IMAPClient(object):
    """A connection to the IMAP server specified by *host* is made when
    this class is instantiated.

    *port* defaults to 993, or 143 if *ssl* is ``False``.

    If *use_uid* is ``True`` unique message UIDs be used for all calls
    that accept message ids (defaults to ``True``).

    If *ssl* is ``True`` (the default) a secure connection will be made.
    Otherwise an insecure connection over plain text will be
    established.

    If *ssl* is ``True`` the optional *ssl_context* argument can be
    used to provide an ``ssl.SSLContext`` instance used to
    control SSL/TLS connection parameters. If this is not provided a
    sensible default context will be used.

    If *stream* is ``True`` then *host* is used as the command to run
    to establish a connection to the IMAP server (defaults to
    ``False``). This is useful for exotic connection or authentication
    setups.

    Use *timeout* to specify a timeout for the socket connected to the
    IMAP server. The timeout can be either a float number, or an instance
    of :py:class:`imapclient.SocketTimeout`.

    * If a single float number is passed, the same timeout delay applies 
      during the  initial connection to the server and for all future socket 
      reads and writes.

    * In case of a ``SocketTimeout``, connection timeout and
      read/write operations can have distinct timeouts.

    * The default is ``None``, where no timeout is used.

    The *normalise_times* attribute specifies whether datetimes
    returned by ``fetch()`` are normalised to the local system time
    and include no timezone information (native), or are datetimes
    that include timezone information (aware). By default
    *normalise_times* is True (times are normalised to the local
    system time). This attribute can be changed between ``fetch()``
    calls if required.

    Can be used as a context manager to automatically close opened connections:

    >>> with IMAPClient(host="imap.foo.org") as client:
    ...     client.login("bar@foo.org", "passwd")

    """

    # Those exceptions are kept for backward-compatibility, since
    # previous versions included these attributes as references to
    # imaplib original exceptions
    Error = exceptions.IMAPClientError
    AbortError = exceptions.IMAPClientAbortError
    ReadOnlyError = exceptions.IMAPClientReadOnlyError

    def __init__(self, host, port=None, use_uid=True, ssl=True, stream=False,
                 ssl_context=None, timeout=None):
        if stream:
            if port is not None:
                raise ValueError("can't set 'port' when 'stream' True")
            if ssl:
                raise ValueError("can't use 'ssl' when 'stream' is True")
        elif port is None:
            port = ssl and 993 or 143

        if ssl and port == 143:
            logger.warning("Attempting to establish an encrypted connection "
                           "to a port (143) often used for unencrypted "
                           "connections")

        self.host = host
        self.port = port
        self.ssl = ssl
        self.ssl_context = ssl_context
        self.stream = stream
        self.use_uid = use_uid
        self.folder_encode = True
        self.normalise_times = True
        self.welcome = None  # the server greeting message

        # If the user gives a single timeout value, assume it is the same for
        # connection and read/write operations
        if not isinstance(timeout, SocketTimeout):
            timeout = SocketTimeout(timeout, timeout)

        self._timeout = timeout
        self._starttls_done = False
        self._cached_capabilities = None
        self._idle_tag = None

        self._conn = self._create_conn()
        logger.debug("Connected to host %s over %s", self.host,
                     "SSL/TLS" if ssl else "plain text")

        self._set_read_timeout()

        # from imaplib
        self.state = 'NONAUTH'
        self._literal = None  # A literal argument to a command
        self._tagged_commands = {}  # Tagged commands awaiting response
        self._untagged_responses = {}  # {typ: [data, ...], ...}
        self._continuation_response = ''  # Last continuation response
        self.is_readonly = False  # READ-ONLY desired state
        self._tagnum = 0
        self._encoding = 'ascii'

        try:
            self._connect()
        except Exception:
            try:
                self._conn.shutdown()
            except OSError:
                pass
            raise

    def _connect(self):
        # Create unique tag for this session,
        # and compile tagged response matcher.

        self.tagpre = util.Int2AP(random.randint(4096, 65535))
        self.tagre = re.compile(br'(?P<tag>'
                                + self.tagpre
                                + br'\d+) (?P<type>[A-Z]+) (?P<data>.*)', re.ASCII)

        # Get server welcome message,
        # request and store CAPABILITY response.

        if __debug__:
            self._cmd_log_len = 10
            self._cmd_log_idx = 0
            self._cmd_log = {}  # Last `_cmd_log_len' interactions
            imaplib_logger.debug('new IMAP4 connection, tag=%s' % self.tagpre)

        self.welcome = self._get_response()
        if 'PREAUTH' in self._untagged_responses:
            self.state = 'AUTH'
        elif 'OK' in self._untagged_responses:
            self.state = 'NONAUTH'
        else:
            raise exceptions.IMAPClientError(self.welcome)

        self._preauth_capabilities = self._get_preauth_capabilities()
        if __debug__:
            imaplib_logger.debug('CAPABILITIES: %r' % (self._preauth_capabilities,))

        for version in AllowedVersions:
            if version not in self._preauth_capabilities:
                continue
            self.PROTOCOL_VERSION = version
            return

        raise exceptions.IMAPClientError('server not IMAP4 compliant')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Logout and closes the connection when exiting the context manager.

        All exceptions during logout and connection shutdown are caught because
        an error here usually means the connection was already closed.
        """
        try:
            self.logout()
        except Exception:
            try:
                self.shutdown()
            except Exception as e:
                logger.info("Could not close the connection cleanly: %s", e)

    def _create_conn(self):
        if self.stream:
            return conn.IMAP4_stream(self.host)

        if self.ssl:
            return tls.IMAP4_TLS(self.host, self.port, self.ssl_context,
                                 self._timeout)

        return imap4.IMAP4WithTimeout(self.host, self.port, self._timeout)

    def _set_read_timeout(self):
        if self._timeout is not None:
            self._conn.sock.settimeout(self._timeout.read)

    @require_capability('STARTTLS')
    def starttls(self, ssl_context=None):
        """Switch to an SSL encrypted connection by sending a STARTTLS command.

        The *ssl_context* argument is optional and should be a
        :py:class:`ssl.SSLContext` object. If no SSL context is given, a SSL 
        context with reasonable default settings will be used.

        You can enable checking of the hostname in the certificate presented
        by the server  against the hostname which was used for connecting, by
        setting the *check_hostname* attribute of the SSL context to ``True``.
        The default SSL context has this setting enabled.

        Raises :py:exc:`Error` if the SSL connection could not be established.

        Raises :py:exc:`AbortError` if the server does not support STARTTLS
        or an SSL connection is already established.
        """
        self.check_state('NONAUTH')
        if self.ssl or self._starttls_done:
            raise exceptions.IMAPClientAbortError('TLS session already established')

        typ, data = self._simple_command("STARTTLS")
        self._checkok('starttls', typ, data)

        self._starttls_done = True

        self._conn.sock = tls.wrap_socket(self._conn.sock, ssl_context, self.host)
        self._conn.file = self._conn.sock.makefile('rb')
        return data[0]

    def login(self, username, password):
        """Login using *username* and *password*, returning the
        server response.
        """
        self.check_state('NONAUTH')
        try:
            rv = self._subcommand_and_check(
                self._cmd_login,
                to_unicode(username),
                to_unicode(password),
                unpack=True,
            )
        except exceptions.IMAPClientError as e:
            raise exceptions.LoginError(str(e))

        logger.info('Logged in as %s', username)
        return rv

    def _cmd_login(self, user, password):
        """Identify client using plaintext password.

        (typ, [data]) = <instance>.login(user, password)

        NB: 'password' will be quoted.
        """
        typ, dat = self._simple_command('LOGIN', user, _quote(password))
        if typ != 'OK':
            raise exceptions.IMAPClientError(dat[-1])
        self.state = 'AUTH'
        return typ, dat

    def oauth2_login(self, user, access_token, mech='XOAUTH2', vendor=None):
        """Authenticate using the OAUTH2 method.

        Gmail and Yahoo both support the 'XOAUTH2' mechanism, but Yahoo requires
        the 'vendor' portion in the payload.
        """
        auth_string = 'user=%s\1auth=Bearer %s\1' % (user, access_token)
        if vendor:
            auth_string += 'vendor=%s\1' % vendor
        auth_string += '\1'
        try:
            return self._subcommand_and_check(self._cmd_authenticate, mech, lambda x: auth_string)
        except exceptions.IMAPClientError as e:
            raise exceptions.LoginError(str(e))

    def _cmd_authenticate(self, mechanism, authobject):
        """Authenticate command - requires response processing.

        'mechanism' specifies which authentication mechanism is to
        be used - it must appear in <instance>.capabilities in the
        form AUTH=<mechanism>.

        'authobject' must be a callable object:

                data = authobject(response)

        It will be called to process server continuation responses; the
        response argument it is passed will be a bytes.  It should return bytes
        data that will be base64 encoded and sent to the server.  It should
        return None if the client abort response '*' should be sent instead.
        """
        self.check_state('NONAUTH')
        mech = mechanism.upper()
        self._literal = util._Authenticator(authobject).process
        typ, dat = self._simple_command('AUTHENTICATE', mech)
        if typ != 'OK':
            raise exceptions.IMAPClientError(dat[-1].decode('utf-8', 'replace'))
        self.state = 'AUTH'
        return typ, dat

    def plain_login(self, identity, password, authorization_identity=None):
        """Authenticate using the PLAIN method (requires server support).
        """
        if not authorization_identity:
            authorization_identity = ""
        auth_string = '%s\0%s\0%s' % (authorization_identity, identity, password)
        try:
            return self._subcommand_and_check(self._cmd_authenticate, 'PLAIN', lambda _: auth_string, unpack=True)
        except exceptions.IMAPClientError as e:
            raise exceptions.LoginError(str(e))

    def logout(self):
        """Logout, returning the server response.
        """
        typ, data = self._cmd_logout()
        _check_resp('BYE', 'logout', typ, data)
        logger.info('Logged out, connection closed')
        return data[0]

    def _cmd_logout(self):
        """Shutdown connection to server.

        (typ, [data]) = <instance>.logout()

        Returns server 'BYE' response.
        """
        self.check_state('NONAUTH','AUTH','SELECTED','LOGOUT')
        self.state = 'LOGOUT'
        typ, dat = self._simple_command('LOGOUT')
        self.shutdown()
        return typ, dat

    def shutdown(self):
        """Close the connection to the IMAP server (without logging out)

        In most cases, :py:meth:`.logout` should be used instead of
        this. The logout method also shutdown down the connection.
        """
        self._conn.shutdown()
        logger.info('Connection closed')

    @require_capability('ENABLE')
    def enable(self, *capabilities):
        """Activate one or more server side capability extensions.

        Most capabilities do not need to be enabled. This is only
        required for extensions which introduce backwards incompatible
        behaviour. Two capabilities which may require enable are
        ``CONDSTORE`` and ``UTF8=ACCEPT``.

        A list of the requested extensions that were successfully
        enabled on the server is returned.

        Once enabled each extension remains active until the IMAP
        connection is closed.

        See :rfc:`5161` for more details.
        """
        if self.state != 'AUTH':
            raise exceptions.IllegalStateError(
                'ENABLE command illegal in state %s' % self.state
            )

        resp = self._raw_command_untagged(
            b'ENABLE',
            [to_bytes(c) for c in capabilities],
            uid=False,
            response_name='ENABLED',
            unpack=True)
        if not resp:
            return []
        return resp.split()

    @require_capability('ID')
    def id_(self, parameters=None):
        """Issue the ID command, returning a dict of server implementation
        fields.

        *parameters* should be specified as a dictionary of field/value pairs,
        for example: ``{"name": "IMAPClient", "version": "0.12"}``
        """
        if parameters is None:
            args = 'NIL'
        else:
            if not isinstance(parameters, dict):
                raise TypeError("'parameters' should be a dictionary")
            args = seq_to_parenstr(
                _quote(v) for v in
                itertools.chain.from_iterable(parameters.items()))

        # RFC2971 says all states but workaround FastMail bug
        self.check_state('NONAUTH', 'AUTH', 'SELECTED')
        typ, data = self._simple_command('ID', args)
        self._checkok('id', typ, data)
        typ, data = self._untagged_response(typ, data, 'ID')
        return parse_response(data)

    def capabilities(self):
        """Returns the server capability list.

        If the session is authenticated and the server has returned an
        untagged CAPABILITY response at authentication time, this
        response will be returned. Otherwise, the CAPABILITY command
        will be issued to the server, with the results cached for
        future calls.

        If the session is not yet authenticated, the capabilities
        requested at connection time will be returned.
        """
        # Ensure cached capabilities aren't used post-STARTTLS. As per
        # https://tools.ietf.org/html/rfc2595#section-3.1
        if self._starttls_done and self.state == 'NONAUTH':
            self._cached_capabilities = None
            return self._do_capabilites()

        # If a capability response has been cached, use that.
        if self._cached_capabilities:
            return self._cached_capabilities

        # If the server returned an untagged CAPABILITY response
        # (during authentication), cache it and return that.
        untagged = _dict_bytes_normaliser(self._untagged_responses)
        response = untagged.pop('CAPABILITY', None)
        if response:
            self._cached_capabilities = self._normalise_capabilites(response[0])
            return self._cached_capabilities

        # If authenticated, but don't have a capability response, ask for one
        if self.state in ('SELECTED', 'AUTH'):
            self._cached_capabilities = self._do_capabilites()
            return self._cached_capabilities

        # Return capabilities fetched at connection time
        return tuple(to_bytes(c) for c in self._preauth_capabilities)

    def _do_capabilites(self):
        raw_response = self._subcommand_and_check(self._cmd_capability, unpack=True)
        return self._normalise_capabilites(raw_response)

    def _normalise_capabilites(self, raw_response):
        raw_response = to_bytes(raw_response)
        return tuple(raw_response.upper().split())

    def has_capability(self, capability):
        """Return ``True`` if the IMAP server has the given *capability*.
        """
        # FIXME: this will not detect capabilities that are backwards
        # compatible with the current level. For instance the SORT
        # capabilities may in the future be named SORT2 which is
        # still compatible with the current standard and will not
        # be detected by this method.
        return to_bytes(capability).upper() in self.capabilities()

    @require_capability('NAMESPACE')
    def namespace(self):
        """Return the namespace for the account as a (personal, other,
        shared) tuple.

        Each element may be None if no namespace of that type exists,
        or a sequence of (prefix, separator) pairs.

        For convenience the tuple elements may be accessed
        positionally or using attributes named *personal*, *other* and
        *shared*.

        See :rfc:`2342` for more details.
        """
        data = self._subcommand_and_check(self._cmd_namespace)
        parts = []
        for item in parse_response(data):
            if item is None:
                parts.append(item)
            else:
                converted = []
                for prefix, separator in item:
                    if self.folder_encode:
                        prefix = decode_utf7(prefix)
                    converted.append((prefix, to_unicode(separator)))
                parts.append(tuple(converted))
        return Namespace(*parts)

    def _cmd_namespace(self):
        """ Returns IMAP namespaces ala rfc2342

        (typ, [data, ...]) = <instance>.namespace()
        """
        self.check_state('AUTH','SELECTED')
        name = 'NAMESPACE'
        typ, dat = self._simple_command(name)
        return self._untagged_response(typ, dat, name)

    def list_folders(self, directory="", pattern="*"):
        """Get a listing of folders on the server as a list of
        ``(flags, delimiter, name)`` tuples.

        Specifying *directory* will limit returned folders to the
        given base directory. The directory and any child directories
        will returned.

        Specifying *pattern* will limit returned folders to those with
        matching names. The wildcards are supported in
        *pattern*. ``*`` matches zero or more of any character and
        ``%`` matches 0 or more characters except the folder
        delimiter.

        Calling list_folders with no arguments will recursively list
        all folders available for the logged in user.

        Folder names are always returned as unicode strings, and
        decoded from modified UTF-7, except if folder_decode is not
        set.
        """
        self.check_state('AUTH', 'SELECTED')
        return self._do_list('LIST', directory, pattern)

    @require_capability('XLIST')
    def xlist_folders(self, directory="", pattern="*"):
        """Execute the XLIST command, returning ``(flags, delimiter,
        name)`` tuples.

        This method returns special flags for each folder and a
        localized name for certain folders (e.g. the name of the
        inbox may be localized and the flags can be used to
        determine the actual inbox, even if the name has been
        localized.

        A ``XLIST`` response could look something like::

            [((b'\\HasNoChildren', b'\\Inbox'), b'/', u'Inbox'),
             ((b'\\Noselect', b'\\HasChildren'), b'/', u'[Gmail]'),
             ((b'\\HasNoChildren', b'\\AllMail'), b'/', u'[Gmail]/All Mail'),
             ((b'\\HasNoChildren', b'\\Drafts'), b'/', u'[Gmail]/Drafts'),
             ((b'\\HasNoChildren', b'\\Important'), b'/', u'[Gmail]/Important'),
             ((b'\\HasNoChildren', b'\\Sent'), b'/', u'[Gmail]/Sent Mail'),
             ((b'\\HasNoChildren', b'\\Spam'), b'/', u'[Gmail]/Spam'),
             ((b'\\HasNoChildren', b'\\Starred'), b'/', u'[Gmail]/Starred'),
             ((b'\\HasNoChildren', b'\\Trash'), b'/', u'[Gmail]/Trash')]

        This is a *deprecated* Gmail-specific IMAP extension (See
        https://developers.google.com/gmail/imap_extensions#xlist_is_deprecated
        for more information).

        The *directory* and *pattern* arguments are as per
        list_folders().
        """
        self.check_state('NONAUTH', 'AUTH', 'SELECTED')
        return self._do_list('XLIST', directory, pattern)

    def list_sub_folders(self, directory="", pattern="*"):
        """Return a list of subscribed folders on the server as
        ``(flags, delimiter, name)`` tuples.

        The default behaviour will list all subscribed folders. The
        *directory* and *pattern* arguments are as per list_folders().
        """
        self.check_state('AUTH','SELECTED')
        return self._do_list('LSUB', directory, pattern)

    def _do_list(self, cmd, directory, pattern):
        directory = self._normalise_folder(directory)
        pattern = self._normalise_folder(pattern)
        typ, dat = self._simple_command(cmd, directory, pattern)
        self._checkok(cmd, typ, dat)
        typ, dat = self._untagged_response(typ, dat, cmd)
        return self._proc_folder_list(dat)

    def _proc_folder_list(self, folder_data):
        # Filter out empty strings and None's.
        # This also deals with the special case of - no 'untagged'
        # responses (ie, no folders). This comes back as [None].
        folder_data = [item for item in folder_data if item not in (b'', None)]

        ret = []
        parsed = parse_response(folder_data)
        for flags, delim, name in chunk(parsed, size=3):
            if isinstance(name, (int, long)):
                # Some IMAP implementations return integer folder names
                # with quotes. These get parsed to ints so convert them
                # back to strings.
                name = text_type(name)
            elif self.folder_encode:
                name = decode_utf7(name)

            ret.append((flags, delim, name))
        return ret

    def find_special_folder(self, folder_flag):
        """Try to locate a special folder, like the Sent or Trash folder.

        >>> server.find_special_folder(imapclient.SENT)
        'INBOX.Sent'

        This function tries its best to find the correct folder (if any) but
        uses heuristics when the server is unable to precisely tell where
        special folders are located.

        Returns the name of the folder if found, or None otherwise.
        """
        # Detect folder by looking for known attributes
        # TODO: avoid listing all folders by using extended LIST (RFC6154)
        if self.has_capability('SPECIAL-USE'):
            for folder in self.list_folders():
                if folder and len(folder[0]) > 0 and folder_flag in folder[0]:
                    return folder[2]

        # Detect folder by looking for common names
        # We only look for folders in the "personal" namespace of the user
        if self.has_capability('NAMESPACE'):
            personal_namespaces = self.namespace().personal
        else:
            personal_namespaces = _POPULAR_PERSONAL_NAMESPACES

        for personal_namespace in personal_namespaces:
            for pattern in _POPULAR_SPECIAL_FOLDERS.get(folder_flag, tuple()):
                pattern = personal_namespace[0] + pattern
                sent_folders = self.list_folders(pattern=pattern)
                if sent_folders:
                    return sent_folders[0][2]

        return None

    def select_folder(self, folder, readonly=False):
        """Set the current folder on the server.

        Future calls to methods such as search and fetch will act on
        the selected folder.

        Returns a dictionary containing the ``SELECT`` response. At least
        the ``b'EXISTS'``, ``b'FLAGS'`` and ``b'RECENT'`` keys are guaranteed
        to exist. An example::

            {b'EXISTS': 3,
             b'FLAGS': (b'\\Answered', b'\\Flagged', b'\\Deleted', ... ),
             b'RECENT': 0,
             b'PERMANENTFLAGS': (b'\\Answered', b'\\Flagged', b'\\Deleted', ... ),
             b'READ-WRITE': True,
             b'UIDNEXT': 11,
             b'UIDVALIDITY': 1239278212}
        """
        self._subcommand_and_check(self._cmd_select, self._normalise_folder(folder), readonly)
        return self._process_select_response(self._untagged_responses)

    def _cmd_select(self, mailbox='INBOX', readonly=False):
        """Select a mailbox.

        Flush all untagged responses.

        (typ, [data]) = <instance>.select(mailbox='INBOX', readonly=False)

        'data' is count of messages in mailbox ('EXISTS' response).

        Mandated responses are ('FLAGS', 'EXISTS', 'RECENT', 'UIDVALIDITY'), so
        other responses should be obtained via <instance>.response('FLAGS') etc.
        """
        self.check_state('AUTH','SELECTED')
        self._untagged_responses = {}    # Flush old responses.
        self.is_readonly = readonly
        if readonly:
            name = 'EXAMINE'
        else:
            name = 'SELECT'
        typ, dat = self._simple_command(name, mailbox)
        if typ != 'OK':
            self.state = 'AUTH'     # Might have been 'SELECTED'
            return typ, dat
        self.state = 'SELECTED'
        if 'READ-ONLY' in self._untagged_responses \
                and not readonly:
            if __debug__:
                self._dump_ur(self._untagged_responses)
            raise exceptions.IMAPClientReadOnlyError('%s is not writable' % mailbox)
        return typ, self._untagged_responses.get('EXISTS', [None])

    @require_capability('UNSELECT')
    def unselect_folder(self):
        """Unselect the current folder and release associated resources.

        Unlike ``close_folder``, the ``UNSELECT`` command does not expunge
        the mailbox, keeping messages with \Deleted flag set for example.

        Returns the UNSELECT response string returned by the server.
        """
        logger.debug('< UNSELECT')
        self.check_state('AUTH', 'SELECTED')  # RFC3691 does not specify any state
        _typ, data = self._simple_command("UNSELECT")
        return data[0]

    def _process_select_response(self, resp):
        untagged = _dict_bytes_normaliser(resp)
        out = {}

        # imaplib doesn't parse these correctly (broken regex) so replace
        # with the raw values out of the OK section
        for line in untagged.get('OK', []):
            match = _RE_SELECT_RESPONSE.match(line)
            if match:
                key = match.group('key')
                if key == b'PERMANENTFLAGS':
                    out[key] = tuple(match.group('data').split())

        for key, value in iteritems(untagged):
            key = key.upper()
            if key in (b'OK', b'PERMANENTFLAGS'):
                continue  # already handled above
            elif key in (b'EXISTS', b'RECENT', b'UIDNEXT', b'UIDVALIDITY', b'HIGHESTMODSEQ'):
                value = int(value[0])
            elif key == b'READ-WRITE':
                value = True
            elif key == b'FLAGS':
                value = tuple(value[0][1:-1].split())
            out[key] = value
        return out

    def noop(self):
        """Execute the NOOP command.

        This command returns immediately, returning any server side
        status updates. It can also be used to reset any auto-logout
        timers.

        The return value is the server command response message
        followed by a list of status responses. For example::

            (b'NOOP completed.',
             [(4, b'EXISTS'),
              (3, b'FETCH', (b'FLAGS', (b'bar', b'sne'))),
              (6, b'FETCH', (b'FLAGS', (b'sne',)))])

        """
        tag = self._command('NOOP')
        return self._consume_until_tagged_response(tag, 'NOOP')

    @require_capability('IDLE')
    def idle(self):
        """Put the server into IDLE mode.

        In this mode the server will return unsolicited responses
        about changes to the selected mailbox. This method returns
        immediately. Use ``idle_check()`` to look for IDLE responses
        and ``idle_done()`` to stop IDLE mode.

        .. note::

            Any other commands issued while the server is in IDLE
            mode will fail.

        See :rfc:`2177` for more information about the IDLE extension.
        """
        self.check_state('NONAUTH', 'AUTH', 'SELECTED')
        self._idle_tag = self._command('IDLE')
        resp = self._get_response()
        if resp is not None:
            raise exceptions.IMAPClientError('Unexpected IDLE response: %s' % resp)

    def _poll_socket(self, sock, timeout=None):
        """
        Polls the socket for events telling us it's available to read.
        This implementation is more scalable because it ALLOWS your process
        to have more than 1024 file descriptors.
        """
        poller = select.poll()
        poller.register(sock.fileno(), select.POLLIN)
        timeout = timeout * 1000 if timeout is not None else None
        return poller.poll(timeout)

    def _select_poll_socket(self, sock, timeout=None):
        """
        Polls the socket for events telling us it's available to read.
        This implementation is a fallback because it FAILS if your process
        has more than 1024 file descriptors.
        We still need this for Windows and some other niche systems.
        """
        return select.select([sock], [], [], timeout)[0]

    @require_capability('IDLE')
    def idle_check(self, timeout=None):
        """Check for any IDLE responses sent by the server.

        This method should only be called if the server is in IDLE
        mode (see ``idle()``).

        By default, this method will block until an IDLE response is
        received. If *timeout* is provided, the call will block for at
        most this many seconds while waiting for an IDLE response.

        The return value is a list of received IDLE responses. These
        will be parsed with values converted to appropriate types. For
        example::

            [(b'OK', b'Still here'),
             (1, b'EXISTS'),
             (1, b'FETCH', (b'FLAGS', (b'\\NotJunk',)))]
        """
        sock = self._conn.sock

        # make the socket non-blocking so the timeout can be
        # implemented for this call
        sock.settimeout(None)
        sock.setblocking(0)

        if POLL_SUPPORT:
            poll_func = self._poll_socket
        else:
            poll_func = self._select_poll_socket

        try:
            resps = []
            events = poll_func(sock, timeout)
            if events:
                while True:
                    try:
                        line = self._conn.get_line()
                    except (socket.timeout, socket.error):
                        break
                    except IMAPClient.AbortError:
                        # An imaplib.IMAP4.abort with "EOF" is raised
                        # under Python 3
                        err = sys.exc_info()[1]
                        if 'EOF' in err.args[0]:
                            break
                        else:
                            raise
                    else:
                        resps.append(_parse_untagged_response(line))
            return resps
        finally:
            sock.setblocking(1)
            self._set_read_timeout()

    @require_capability('IDLE')
    def idle_done(self):
        """Take the server out of IDLE mode.

        This method should only be called if the server is already in
        IDLE mode.

        The return value is of the form ``(command_text,
        idle_responses)`` where *command_text* is the text sent by the
        server when the IDLE command finished (eg. ``b'Idle
        terminated'``) and *idle_responses* is a list of parsed idle
        responses received since the last call to ``idle_check()`` (if
        any). These are returned in parsed form as per
        ``idle_check()``.
        """
        logger.debug('< DONE')
        self._conn.send(b'DONE\r\n')
        return self._consume_until_tagged_response(self._idle_tag, 'IDLE')

    def folder_status(self, folder, what=None):
        """Return the status of *folder*.

        *what* should be a sequence of status items to query. This
        defaults to ``('MESSAGES', 'RECENT', 'UIDNEXT', 'UIDVALIDITY',
        'UNSEEN')``.

        Returns a dictionary of the status items for the folder with
        keys matching *what*.
        """
        if what is None:
            what = ('MESSAGES', 'RECENT', 'UIDNEXT', 'UIDVALIDITY', 'UNSEEN')
        else:
            what = normalise_text_list(what)
        what_ = '(%s)' % (' '.join(what))

        fname = self._normalise_folder(folder)
        data = self._subcommand_and_check(self._cmd_status, fname, what_)
        response = parse_response(data)
        status_items = response[-1]
        return dict(as_pairs(status_items))

    def _cmd_status(self, mailbox, names):
        """Request named status conditions for mailbox.

        (typ, [data]) = <instance>.status(mailbox, names)
        """
        self.check_state('AUTH', 'SELECTED')
        name = 'STATUS'
        # if self.PROTOCOL_VERSION == 'IMAP4':   # Let the server decide!
        #    raise exceptions.IMAPClientError('%s unimplemented in IMAP4 (obtain IMAP4rev1 server, or re-code)' % name)
        typ, dat = self._simple_command(name, mailbox, names)
        return self._untagged_response(typ, dat, name)

    def close_folder(self):
        """Close the currently selected folder, returning the server
        response string.
        """
        return self._subcommand_and_check(self._cmd_close, unpack=True)

    def _cmd_close(self):
        """Close currently selected mailbox.

        Deleted messages are removed from writable mailbox.
        This is the recommended command before 'LOGOUT'.

        (typ, [data]) = <instance>.close()
        """
        self.check_state('SELECTED')
        try:
            typ, dat = self._simple_command('CLOSE')
        finally:
            self.state = 'AUTH'
        return typ, dat

    def create_folder(self, folder):
        """Create *folder* on the server returning the server response string.
        """
        return self._subcommand_and_check(self._cmd_create, self._normalise_folder(folder), unpack=True)

    def _cmd_create(self, mailbox):
        """Create new mailbox.

        (typ, [data]) = <instance>.create(mailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('CREATE', mailbox)

    def rename_folder(self, old_name, new_name):
        """Change the name of a folder on the server.
        """
        return self._subcommand_and_check(self._cmd_rename,
                                       self._normalise_folder(old_name),
                                       self._normalise_folder(new_name),
                                       unpack=True)

    def _cmd_rename(self, oldmailbox, newmailbox):
        """Rename old mailbox name to new.

        (typ, [data]) = <instance>.rename(oldmailbox, newmailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('RENAME', oldmailbox, newmailbox)

    def delete_folder(self, folder):
        """Delete *folder* on the server returning the server response string.
        """
        return self._subcommand_and_check(self._cmd_delete, self._normalise_folder(folder), unpack=True)

    def _cmd_delete(self, mailbox):
        """Delete old mailbox.

        (typ, [data]) = <instance>.delete(mailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('DELETE', mailbox)

    def folder_exists(self, folder):
        """Return ``True`` if *folder* exists on the server.
        """
        return len(self.list_folders("", folder)) > 0

    def subscribe_folder(self, folder):
        """Subscribe to *folder*, returning the server response string.
        """
        return self._subcommand_and_check(self._cmd_subscribe, self._normalise_folder(folder))

    def _cmd_subscribe(self, mailbox):
        """Subscribe to new mailbox.

        (typ, [data]) = <instance>.subscribe(mailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('SUBSCRIBE', mailbox)

    def unsubscribe_folder(self, folder):
        """Unsubscribe to *folder*, returning the server response string.
        """
        return self._subcommand_and_check(self._cmd_unsubscribe, self._normalise_folder(folder))

    def _cmd_unsubscribe(self, mailbox):
        """Unsubscribe from old mailbox.

        (typ, [data]) = <instance>.unsubscribe(mailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('UNSUBSCRIBE', mailbox)

    def search(self, criteria='ALL', charset=None):
        """Return a list of messages ids from the currently selected
        folder matching *criteria*.

        *criteria* should be a sequence of one or more criteria
        items. Each criteria item may be either unicode or
        bytes. Example values::

            [u'UNSEEN']
            [u'SMALLER', 500]
            [b'NOT', b'DELETED']
            [u'TEXT', u'foo bar', u'FLAGGED', u'SUBJECT', u'baz']
            [u'SINCE', date(2005, 4, 3)]

        IMAPClient will perform conversion and quoting as
        required. The caller shouldn't do this.

        It is also possible (but not recommended) to pass the combined
        criteria as a single string. In this case IMAPClient won't
        perform quoting, allowing lower-level specification of
        criteria. Examples of this style::

            u'UNSEEN'
            u'SMALLER 500'
            b'NOT DELETED'
            u'TEXT "foo bar" FLAGGED SUBJECT "baz"'
            b'SINCE 03-Apr-2005'

        To support complex search expressions, criteria lists can be
        nested. IMAPClient will insert parentheses in the right
        places. The following will match messages that are both not
        flagged and do not have "foo" in the subject:

            ['NOT', ['SUBJECT', 'foo', 'FLAGGED']]

        *charset* specifies the character set of the criteria. It
        defaults to US-ASCII as this is the only charset that a server
        is required to support by the RFC. UTF-8 is commonly supported
        however.

        Any criteria specified using unicode will be encoded as per
        *charset*. Specifying a unicode criteria that can not be
        encoded using *charset* will result in an error.

        Any criteria specified using bytes will be sent as-is but
        should use an encoding that matches *charset* (the character
        set given is still passed on to the server).

        See :rfc:`3501#section-6.4.4` for more details.

        Note that criteria arguments that are 8-bit will be
        transparently sent by IMAPClient as IMAP literals to ensure
        adherence to IMAP standards.

        The returned list of message ids will have a special *modseq*
        attribute. This is set if the server included a MODSEQ value
        to the search response (i.e. if a MODSEQ criteria was included
        in the search).

        """
        return self._search(criteria, charset)

    @require_capability('X-GM-EXT-1')
    def gmail_search(self, query, charset='UTF-8'):
        """Search using Gmail's X-GM-RAW attribute.

        *query* should be a valid Gmail search query string. For
        example: ``has:attachment in:unread``. The search string may
        be unicode and will be encoded using the specified *charset*
        (defaulting to UTF-8).

        This method only works for IMAP servers that support X-GM-RAW,
        which is only likely to be Gmail.

        See https://developers.google.com/gmail/imap_extensions#extension_of_the_search_command_x-gm-raw
        for more info.
        """
        return self._search([b'X-GM-RAW', query], charset)

    def _search(self, criteria, charset):
        self.check_state('SELECTED')
        args = []
        if charset:
            args.extend([b'CHARSET', to_bytes(charset)])
        args.extend(_normalise_search_criteria(criteria, charset))

        try:
            data = self._raw_command_untagged(b'SEARCH', args)
        except exceptions.IMAPClientError as e:
            # Make BAD IMAP responses easier to understand to the user, with a link to the docs
            m = re.match(r'SEARCH command error: BAD \[(.+)\]', str(e))
            if m:
                raise exceptions.InvalidCriteriaError(
                    '{original_msg}\n\n'
                    'This error may have been caused by a syntax error in the criteria: '
                    '{criteria}\nPlease refer to the documentation for more information '
                    'about search criteria syntax..\n'
                    'https://imapclient.readthedocs.io/en/master/#imapclient.IMAPClient.search'
                        .format(
                        original_msg=m.group(1),
                        criteria='"%s"' % criteria if not isinstance(criteria, list) else criteria
                    )
                )

            # If the exception is not from a BAD IMAP response, re-raise as-is
            raise

        return parse_message_list(data)

    @require_capability('SORT')
    def sort(self, sort_criteria, criteria='ALL', charset='UTF-8'):
        """Return a list of message ids from the currently selected
        folder, sorted by *sort_criteria* and optionally filtered by
        *criteria*.

        *sort_criteria* may be specified as a sequence of strings or a
        single string. IMAPClient will take care any required
        conversions. Valid *sort_criteria* values::

            ['ARRIVAL']
            ['SUBJECT', 'ARRIVAL']
            'ARRIVAL'
            'REVERSE SIZE'

        The *criteria* and *charset* arguments are as per
        :py:meth:`.search`.

        See :rfc:`5256` for full details.

        Note that SORT is an extension to the IMAP4 standard so it may
        not be supported by all IMAP servers.
        """
        self.check_state('SELECTED')
        args = [
            _normalise_sort_criteria(sort_criteria),
            to_bytes(charset),
        ]
        args.extend(_normalise_search_criteria(criteria, charset))
        ids = self._raw_command_untagged(b'SORT', args, unpack=True)
        return [long(i) for i in ids.split()]

    def thread(self, algorithm='REFERENCES', criteria='ALL', charset='UTF-8'):
        """Return a list of messages threads from the currently
        selected folder which match *criteria*.

        Each returned thread is a list of messages ids. An example
        return value containing three message threads::

            ((1, 2), (3,), (4, 5, 6))

        The optional *algorithm* argument specifies the threading
        algorithm to use.

        The *criteria* and *charset* arguments are as per
        :py:meth:`.search`.

        See :rfc:`5256` for more details.
        """
        self.check_state('SELECTED')
        algorithm = to_bytes(algorithm)
        if not self.has_capability(b'THREAD=' + algorithm):
            raise exceptions.CapabilityError(
                'The server does not support %s threading algorithm' % algorithm
            )

        args = [algorithm, to_bytes(charset)] + \
               _normalise_search_criteria(criteria, charset)
        data = self._raw_command_untagged(b'THREAD', args)
        return parse_response(data)

    def get_flags(self, messages):
        """Return the flags set for each message in *messages* from
        the currently selected folder.

        The return value is a dictionary structured like this: ``{
        msgid1: (flag1, flag2, ... ), }``.
        """
        response = self.fetch(messages, ['FLAGS'])
        return self._filter_fetch_dict(response, b'FLAGS')

    def add_flags(self, messages, flags, silent=False):
        """Add *flags* to *messages* in the currently selected folder.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*), or None if *silent* is true.
        """
        return self._store(b'+FLAGS', messages, flags, b'FLAGS', silent=silent)

    def remove_flags(self, messages, flags, silent=False):
        """Remove one or more *flags* from *messages* in the currently
        selected folder.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*), or None if *silent* is true.
        """
        return self._store(b'-FLAGS', messages, flags, b'FLAGS', silent=silent)

    def set_flags(self, messages, flags, silent=False):
        """Set the *flags* for *messages* in the currently selected
        folder.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*), or None if *silent* is true.
        """
        return self._store(b'FLAGS', messages, flags, b'FLAGS', silent=silent)

    def get_gmail_labels(self, messages):
        """Return the label set for each message in *messages* in the
        currently selected folder.

        The return value is a dictionary structured like this: ``{
        msgid1: (label1, label2, ... ), }``.

        This only works with IMAP servers that support the X-GM-LABELS
        attribute (eg. Gmail).
        """
        response = self.fetch(messages, [b'X-GM-LABELS'])
        response = self._filter_fetch_dict(response, b'X-GM-LABELS')
        return {msg: utf7_decode_sequence(labels)
                for msg, labels in iteritems(response)}

    def add_gmail_labels(self, messages, labels, silent=False):
        """Add *labels* to *messages* in the currently selected folder.

        *labels* should be a sequence of strings.

        Returns the label set for each modified message (see
        *get_gmail_labels*), or None if *silent* is true.

        This only works with IMAP servers that support the X-GM-LABELS
        attribute (eg. Gmail).
        """
        return self._gm_label_store(b'+X-GM-LABELS', messages, labels,
                                    silent=silent)

    def remove_gmail_labels(self, messages, labels, silent=False):
        """Remove one or more *labels* from *messages* in the
        currently selected folder, or None if *silent* is true.

        *labels* should be a sequence of strings.

        Returns the label set for each modified message (see
        *get_gmail_labels*).

        This only works with IMAP servers that support the X-GM-LABELS
        attribute (eg. Gmail).
        """
        return self._gm_label_store(b'-X-GM-LABELS', messages, labels,
                                    silent=silent)

    def set_gmail_labels(self, messages, labels, silent=False):
        """Set the *labels* for *messages* in the currently selected
        folder.

        *labels* should be a sequence of strings.

        Returns the label set for each modified message (see
        *get_gmail_labels*), or None if *silent* is true.

        This only works with IMAP servers that support the X-GM-LABELS
        attribute (eg. Gmail).
        """
        return self._gm_label_store(b'X-GM-LABELS', messages, labels,
                                    silent=silent)

    def delete_messages(self, messages, silent=False):
        """Delete one or more *messages* from the currently selected
        folder.

        Returns the flags set for each modified message (see
        *get_flags*).
        """
        return self.add_flags(messages, DELETED, silent=silent)

    def fetch(self, messages, data, modifiers=None):
        """Retrieve selected *data* associated with one or more
        *messages* in the currently selected folder.

        *data* should be specified as a sequence of strings, one item
        per data selector, for example ``['INTERNALDATE',
        'RFC822']``.

        *modifiers* are required for some extensions to the IMAP
        protocol (eg. :rfc:`4551`). These should be a sequence of strings
        if specified, for example ``['CHANGEDSINCE 123']``.

        A dictionary is returned, indexed by message number. Each item
        in this dictionary is also a dictionary, with an entry
        corresponding to each item in *data*. Returned values will be
        appropriately typed. For example, integer values will be returned as
        Python integers, timestamps will be returned as datetime
        instances and ENVELOPE responses will be returned as
        :py:class:`Envelope <imapclient.response_types.Envelope>` instances.

        String data will generally be returned as bytes (Python 3) or
        str (Python 2).

        In addition to an element for each *data* item, the dict
        returned for each message also contains a *SEQ* key containing
        the sequence number for the message. This allows for mapping
        between the UID and sequence number (when the *use_uid*
        property is ``True``).

        Example::

            >> c.fetch([3293, 3230], ['INTERNALDATE', 'FLAGS'])
            {3230: {b'FLAGS': (b'\\Seen',),
                    b'INTERNALDATE': datetime.datetime(2011, 1, 30, 13, 32, 9),
                    b'SEQ': 84},
             3293: {b'FLAGS': (),
                    b'INTERNALDATE': datetime.datetime(2011, 2, 24, 19, 30, 36),
                    b'SEQ': 110}}

        """
        self.check_state('SELECTED')
        if not messages:
            return {}

        args = [
            'FETCH',
            join_message_ids(messages),
            seq_to_parenstr_upper(data),
            seq_to_parenstr_upper(modifiers) if modifiers else None
        ]
        if self.use_uid:
            args.insert(0, 'UID')
        tag = self._command(*args)
        typ, data = self._command_complete('FETCH', tag)
        self._checkok('fetch', typ, data)
        typ, data = self._untagged_response(typ, data, 'FETCH')
        return parse_fetch_response(data, self.normalise_times, self.use_uid)

    def append(self, folder, msg, flags=(), msg_time=None):
        """Append a message to *folder*.

        *msg* should be a string contains the full message including
        headers.

        *flags* should be a sequence of message flags to set. If not
        specified no flags will be set.

        *msg_time* is an optional datetime instance specifying the
        date and time to set on the message. The server will set a
        time if it isn't specified. If *msg_time* contains timezone
        information (tzinfo), this will be honoured. Otherwise the
        local machine's time zone sent to the server.

        Returns the APPEND response as returned by the server.
        """
        if msg_time:
            time_val = '"%s"' % datetime_to_INTERNALDATE(msg_time)
            if PY3:
                time_val = to_unicode(time_val)
            else:
                time_val = to_bytes(time_val)
        else:
            time_val = None
        return self._subcommand_and_check(self._cmd_append,
                                       self._normalise_folder(folder),
                                       seq_to_parenstr(flags),
                                       time_val,
                                       to_bytes(msg),
                                       unpack=True)

    def _cmd_append(self, mailbox, flags, date_time, message):
        """Append message to named mailbox.

        (typ, [data]) = <instance>.append(mailbox, flags, date_time, message)

                All args except `message' can be None.
        """
        self.check_state('AUTH', 'SELECTED')
        name = 'APPEND'
        if not mailbox:
            mailbox = 'INBOX'
        if flags:
            if (flags[0], flags[-1]) != ('(', ')'):
                flags = '(%s)' % flags
        else:
            flags = None
        if date_time:
            date_time = util.Time2Internaldate(date_time)
        else:
            date_time = None
        literal = MapCRLF.sub(CRLF, message)
        self._literal = literal
        return self._simple_command(name, mailbox, flags, date_time)

    @require_capability('MULTIAPPEND')
    def multiappend(self, folder, msgs):
        """Append messages to *folder* using the MULTIAPPEND feature from :rfc:`3502`.

        *msgs* should be a list of strings containing the full message including
        headers.

        Returns the APPEND response from the server.
        """
        msgs = [_literal(to_bytes(m)) for m in msgs]

        return self._raw_command(
            b'APPEND',
            [self._normalise_folder(folder)] + msgs,
            uid=False,
        )

    def copy(self, messages, folder):
        """Copy one or more messages from the current folder to
        *folder*. Returns the COPY response string returned by the
        server.
        """
        self.check_state('SELECTED')
        return self._uid_command_and_check('COPY',
                                              join_message_ids(messages),
                                              self._normalise_folder(folder),
                                              unpack=True)

    @require_capability('MOVE')
    def move(self, messages, folder):
        """Atomically move messages to another folder.

        Requires the MOVE capability, see :rfc:`6851`.

        :param messages: List of message UIDs to move.
        :param folder: The destination folder name.
        """
        self.check_state('AUTH','SELECTED')  # RFC6851
        return self._uid_command_and_check('MOVE',
                                              join_message_ids(messages),
                                              self._normalise_folder(folder),
                                              unpack=True)

    def expunge(self, messages=None):
        """When, no *messages* are specified, remove all messages
        from the currently selected folder that have the
        ``\\Deleted`` flag set.

        The return value is the server response message
        followed by a list of expunge responses. For example::

            ('Expunge completed.',
             [(2, 'EXPUNGE'),
              (1, 'EXPUNGE'),
              (0, 'RECENT')])

        In this case, the responses indicate that the message with
        sequence numbers 2 and 1 where deleted, leaving no recent
        messages in the folder.

        See :rfc:`3501#section-6.4.3` section 6.4.3 and
        :rfc:`3501#section-7.4.1` section 7.4.1 for more details.

        When *messages* are specified, remove the specified messages
        from the selected folder, provided those messages also have
        the ``\\Deleted`` flag set. The return value is ``None`` in
        this case.

        Expunging messages by id(s) requires that *use_uid* is
        ``True`` for the client.

        See :rfc:`4315#section-2.1` section 2.1 for more details.
        """
        self.check_state('SELECTED')
        if messages:
            if not self.use_uid:
                raise ValueError('cannot EXPUNGE by ID when not using uids')
            return self._uid_command_and_check('EXPUNGE', join_message_ids(messages))
        tag = self._command('EXPUNGE')
        return self._consume_until_tagged_response(tag, 'EXPUNGE')

    @require_capability('ACL')
    def getacl(self, folder):
        """Returns a list of ``(who, acl)`` tuples describing the
        access controls for *folder*.
        """
        data = self._subcommand_and_check(self._cmd_getacl, self._normalise_folder(folder))
        parts = list(response_lexer.TokenSource(data))
        parts = parts[1:]  # First item is folder name
        return [(parts[i], parts[i + 1]) for i in xrange(0, len(parts), 2)]

    def _cmd_getacl(self, mailbox):
        """Get the ACLs for a mailbox.

        (typ, [data]) = <instance>.getacl(mailbox)
        """
        self.check_state('AUTH', 'SELECTED')
        typ, dat = self._simple_command('GETACL', mailbox)
        return self._untagged_response(typ, dat, 'ACL')

    @require_capability('ACL')
    def setacl(self, folder, who, what):
        """Set an ACL (*what*) for user (*who*) for a folder.

        Set *what* to an empty string to remove an ACL. Returns the
        server response string.
        """
        return self._subcommand_and_check(self._cmd_setacl,
                                       self._normalise_folder(folder),
                                       who, what,
                                       unpack=True)

    def _cmd_setacl(self, mailbox, who, what):
        """Set a mailbox acl.

        (typ, [data]) = <instance>.setacl(mailbox, who, what)
        """
        self.check_state('AUTH', 'SELECTED')
        return self._simple_command('SETACL', mailbox, who, what)

    @require_capability('QUOTA')
    def get_quota(self, mailbox="INBOX"):
        """Get the quotas associated with a mailbox.

        Returns a list of Quota objects.
        """
        return self.get_quota_root(mailbox)[1]

    @require_capability('QUOTA')
    def _get_quota(self, quota_root=""):
        """Get the quotas associated with a quota root.

        This method is not private but put behind an underscore to show that
        it is a low-level function. Users probably want to use `get_quota`
        instead.

        Returns a list of Quota objects.
        """
        return _parse_quota(
            self._subcommand_and_check(self._cmd_getquota, _quote(quota_root))
        )

    def _cmd_getquota(self, root):
        """Get the quota root's resource usage and limits.

        Part of the IMAP4 QUOTA extension defined in rfc2087.

        (typ, [data]) = <instance>.getquota(root)
        """
        self.check_state('AUTH', 'SELECTED')
        typ, dat = self._simple_command('GETQUOTA', root)
        return self._untagged_response(typ, dat, 'QUOTA')

    @require_capability('QUOTA')
    def get_quota_root(self, mailbox):
        """Get the quota roots for a mailbox.

        The IMAP server responds with the quota root and the quotas associated
        so there is usually no need to call `get_quota` after.

        See :rfc:`2087` for more details.

        Return a tuple of MailboxQuotaRoots and list of Quota associated
        """
        self.check_state('AUTH','SELECTED')
        quota_root_rep = self._raw_command_untagged(
            b'GETQUOTAROOT', to_bytes(mailbox), uid=False,
            response_name='QUOTAROOT'
        )
        quota_rep = pop_with_default(self._untagged_responses, 'QUOTA', [])
        quota_root_rep = parse_response(quota_root_rep)
        quota_root = MailboxQuotaRoots(
            to_unicode(quota_root_rep[0]),
            [to_unicode(q) for q in quota_root_rep[1:]]
        )
        return quota_root, _parse_quota(quota_rep)

    @require_capability('QUOTA')
    def set_quota(self, quotas):
        """Set one or more quotas on resources.

        :param quotas: list of Quota objects
        """
        self.check_state('AUTH','SELECTED')
        if not quotas:
            return

        quota_root = None
        set_quota_args = list()

        for quota in quotas:
            if quota_root is None:
                quota_root = quota.quota_root
            elif quota_root != quota.quota_root:
                raise ValueError("set_quota only accepts a single quota root")

            set_quota_args.append(
                "{} {}".format(quota.resource, quota.limit)
            )

        set_quota_args = " ".join(set_quota_args)
        args = [
            to_bytes(_quote(quota_root)),
            to_bytes("({})".format(set_quota_args))
        ]

        response = self._raw_command_untagged(
            b'SETQUOTA', args, uid=False, response_name='QUOTA'
        )
        return _parse_quota(response)

    #       Internal methods

    def _append_untagged(self, typ, dat):
        if dat is None:
            dat = b''
        ur = self._untagged_responses
        if __debug__:
            imaplib_logger.debug('untagged_responses[%s] %s += ["%r"]' %
                                 (typ, len(ur.get(typ, '')), dat))
        if typ in ur:
            ur[typ].append(dat)
        else:
            ur[typ] = [dat]

    def _check_bye(self):
        bye = self._untagged_responses.get('BYE')
        if bye:
            raise exceptions.IMAPClientAbortError(bye[-1].decode(self._encoding, 'replace'))

    def check_state(self, *states):
        if self.state in states:
            return

        self._literal = None
        raise exceptions.IMAPClientError("command illegal in state %s, "
                         "only allowed in states %s" %
                         (self.state, ', '.join(states)))

    def _command(self, name, *args):
        for typ in ('OK', 'NO', 'BAD'):
            if typ in self._untagged_responses:
                del self._untagged_responses[typ]

        if 'READ-ONLY' in self._untagged_responses \
                and not self.is_readonly:
            raise exceptions.IMAPClientReadOnlyError('mailbox status changed to READ-ONLY')

        tag = self._new_tag()
        name = bytes(name, self._encoding)
        data = tag + b' ' + name
        for arg in args:
            if arg is None: continue
            if isinstance(arg, str):
                arg = bytes(arg, self._encoding)
            data = data + b' ' + arg

        literal = self._literal
        if literal is not None:
            self._literal = None
            if type(literal) is type(self._command):
                literator = literal
            else:
                literator = None
                data = data + bytes(' {%s}' % len(literal), self._encoding)

        if __debug__:
            msg = util.redact_password('> %r' % data)
            imaplib_logger.debug(msg)

        try:
            self._conn.send(data + CRLF)
        except OSError as val:
            raise exceptions.IMAPClientAbortError('socket error: %s' % val)

        if literal is None:
            return tag

        while 1:
            # Wait for continuation response

            while self._get_response():
                if self._tagged_commands[tag]:  # BAD/NO?
                    return tag

            # Send literal

            if literator:
                literal = literator(self._continuation_response)

            if __debug__:
                imaplib_logger.debug('write literal size %s' % len(literal))

            try:
                self._conn.send(literal)
                self._conn.send(CRLF)
            except OSError as val:
                raise exceptions.IMAPClientAbortError('socket error: %s' % val)

            if not literator:
                break

        return tag

    def _command_complete(self, name, tag):
        logout = (name == 'LOGOUT')
        # BYE is expected after LOGOUT
        if not logout:
            self._check_bye()
        try:
            typ, data = self._get_tagged_response(tag, expect_bye=logout)
        except exceptions.IMAPClientAbortError as val:
            raise exceptions.IMAPClientAbortError('command: %s => %s' % (name, val))
        except exceptions.IMAPClientError as val:
            raise exceptions.IMAPClientError('command: %s => %s' % (name, val))
        if not logout:
            self._check_bye()
        if typ == 'BAD':
            raise exceptions.IMAPClientError('%s command error: %s %s' % (name, typ, data))
        return typ, data

    def _get_preauth_capabilities(self):
        typ, dat = self._cmd_capability()
        if dat == [None]:
            raise exceptions.IMAPClientError('no CAPABILITY response from server')
        dat = str(dat[-1], self._encoding)
        dat = dat.upper()
        return tuple(dat.split())

    def _cmd_capability(self):
        """(typ, [data]) = <instance>.capability()
        Fetch capabilities list from server."""
        name = 'CAPABILITY'
        typ, dat = self._simple_command(name)
        return self._untagged_response(typ, dat, name)

    def _get_response(self):
        # Read response and store.
        #
        # Returns None for continuation responses,
        # otherwise first response line received.

        resp = self._conn.get_line()

        # Command completion response?

        if self._match(self.tagre, resp):
            tag = self.mo.group('tag')
            if not tag in self._tagged_commands:
                raise exceptions.IMAPClientAbortError('unexpected tagged response: %r' % resp)

            typ = self.mo.group('type')
            typ = str(typ, self._encoding)
            dat = self.mo.group('data')
            self._tagged_commands[tag] = (typ, [dat])
        else:
            dat2 = None

            # '*' (untagged) responses?

            if not self._match(Untagged_response, resp):
                if self._match(Untagged_status, resp):
                    dat2 = self.mo.group('data2')

            if self.mo is None:
                # Only other possibility is '+' (continuation) response...

                if self._match(Continuation, resp):
                    self._continuation_response = self.mo.group('data')
                    return None  # NB: indicates continuation

                raise exceptions.IMAPClientAbortError("unexpected response: %r" % resp)

            typ = self.mo.group('type')
            typ = str(typ, self._encoding)
            dat = self.mo.group('data')
            if dat is None: dat = b''  # Null untagged response
            if dat2: dat = dat + b' ' + dat2

            # Is there a literal to come?

            while self._match(Literal, dat):

                # Read literal direct from connection.

                size = int(self.mo.group('size'))
                if __debug__:
                    imaplib_logger.debug('read literal size %s' % size)
                data = self._conn.read(size)

                # Store response with literal as tuple

                self._append_untagged(typ, (dat, data))

                # Read trailer - possibly containing another literal

                dat = self._conn.get_line()

            self._append_untagged(typ, dat)

        # Bracketed response information?

        if typ in ('OK', 'NO', 'BAD') and self._match(Response_code, dat):
            typ = self.mo.group('type')
            typ = str(typ, self._encoding)
            self._append_untagged(typ, self.mo.group('data'))

        if __debug__:
            if typ in ('NO', 'BAD', 'BYE'):
                imaplib_logger.debug('%s response: %r' % (typ, dat))

        return resp

    def _get_tagged_response(self, tag, expect_bye=False):

        while 1:
            result = self._tagged_commands[tag]
            if result is not None:
                del self._tagged_commands[tag]
                return result

            if expect_bye:
                typ = 'BYE'
                bye = self._untagged_responses.pop(typ, None)
                if bye is not None:
                    # Server replies to the "LOGOUT" command with "BYE"
                    return (typ, bye)

            # If we've seen a BYE at this point, the socket will be
            # closed, so report the BYE now.
            self._check_bye()

            # Some have reported "unexpected response" exceptions.
            # Note that ignoring them here causes loops.
            # Instead, send me details of the unexpected response and
            # I'll update the code in `_get_response()'.
            self._get_response()

    def _match(self, cre, s):
        # Run compiled regular expression match method on 's'.
        # Save result, return success.

        self.mo = cre.match(s)
        if __debug__:
            if self.mo is not None:
                imaplib_logger.debug("\tmatched %r => %r" % (cre.pattern, self.mo.groups()))
        return self.mo is not None

    def _new_tag(self):
        tag = self.tagpre + bytes(str(self._tagnum), self._encoding)
        self._tagnum = self._tagnum + 1
        self._tagged_commands[tag] = None
        return tag

    def _simple_command(self, name, *args):
        return self._command_complete(name, self._command(name, *args))

    def _untagged_response(self, typ, dat, name):
        if typ == 'NO':
            return typ, dat
        if not name in self._untagged_responses:
            return typ, [None]
        data = self._untagged_responses.pop(name)
        if __debug__:
            imaplib_logger.debug('untagged_responses[%s] => %s' % (name, data))
        return typ, data

    def _dump_ur(self, dict):
        # Dump untagged responses (in `dict').
        l = dict.items()
        if not l: return
        t = '\n\t\t'
        l = map(lambda x: '%s: "%s"' % (x[0], x[1][0] and '" "'.join(x[1]) or ''), l)
        imaplib_logger.debug('untagged responses dump:%s%s' % (t, t.join(l)))

    def _consume_until_tagged_response(self, tag, command):
        tagged_commands = self._tagged_commands
        resps = []
        while True:
            line = self._get_response()
            if tagged_commands[tag]:
                break
            resps.append(_parse_untagged_response(line))
        typ, data = tagged_commands.pop(tag)
        self._checkok(command, typ, data)
        return data[0], resps

    def _raw_command_untagged(self, command, args, response_name=None, unpack=False, uid=True):
        # TODO: eventually this should replace _subcommand_and_check (call it _command)
        typ, data = self._raw_command(command, args, uid=uid)
        if response_name is None:
            response_name = command
        typ, data = self._untagged_response(typ, data, to_unicode(response_name))
        self._checkok(to_unicode(command), typ, data)
        if unpack:
            return data[0]
        return data

    def _raw_command(self, command, args, uid=True):
        """Run the specific command with the arguments given. 8-bit arguments
        are sent as literals. The return value is (typ, data).

        This sidesteps much of imaplib's command sending
        infrastructure because imaplib can't send more than one
        literal.

        *command* should be specified as bytes.
        *args* should be specified as a list of bytes.
        """
        command = command.upper()

        if isinstance(args, tuple):
            args = list(args)
        if not isinstance(args, list):
            args = [args]

        tag = self._new_tag()
        prefix = [to_bytes(tag)]
        if uid and self.use_uid:
            prefix.append(b'UID')
        prefix.append(command)

        line = []
        for item, is_last in _iter_with_last(prefix + args):
            if not isinstance(item, bytes):
                raise ValueError("command args must be passed as bytes")

            if _is8bit(item):
                # If a line was already started send it
                if line:
                    out = b' '.join(line)
                    logger.debug('> %s', out)
                    self._conn.send(out)
                    line = []

                # Now send the (unquoted) literal
                if isinstance(item, _quoted):
                    item = item.original
                self._send_literal(tag, item)
                if not is_last:
                    self._conn.send(b' ')
            else:
                line.append(item)

        if line:
            out = b' '.join(line)
            logger.debug('> %s', out)
            self._conn.send(out)

        self._conn.send(b'\r\n')

        return self._command_complete(to_unicode(command), tag)

    def _send_literal(self, tag, item):
        """Send a single literal for the command with *tag*.
        """
        if b'LITERAL+' in self._cached_capabilities:
            out = b' {' + str(len(item)).encode('ascii') + b'+}\r\n' + item
            logger.debug('> %s', debug_trunc(out, 64))
            self._conn.send(out)
            return

        out = b' {' + str(len(item)).encode('ascii') + b'}\r\n'
        logger.debug('> %s', out)
        self._conn.send(out)

        # Wait for continuation response
        while self._get_response():
            tagged_resp = self._tagged_commands.get(tag)
            if tagged_resp:
                raise exceptions.IMAPClientAbortError(
                    "unexpected response while waiting for continuation response: " +
                    repr(tagged_resp))

        logger.debug("   (literal) > %s", debug_trunc(item, 256))
        self._conn.send(item)

    def _uid_command_and_check(self, command, *args, **kwargs):
        """Execute a simple command "command arg ...".

        If self.use_uid is True, identify messages by UID rather than message number.

        Returns response appropriate to 'command'.
        """
        unpack = pop_with_default(kwargs, 'unpack', False)
        assert not kwargs, "unexpected keyword args: " + ', '.join(kwargs)

        if self.use_uid:
            typ, data = self._simple_command('UID', command, *args)
        else:
            typ, data = self._simple_command(command, *args)

        # I don't know why this is always fetch
        typ, data = self._untagged_response(typ, data, 'FETCH')
        self._checkok(command, typ, data)
        if unpack:
            return data[0]
        return data

    def _subcommand_and_check(self, meth, *args, **kwargs):
        """Call another method and check the result code.

        Return the data from the command. If unpack=True, return data[0].
        """
        unpack = pop_with_default(kwargs, 'unpack', False)
        assert not kwargs, "unexpected keyword args: " + ', '.join(kwargs)

        typ, data = meth(*args)
        self._checkok(meth.__func__.__name__.upper(), typ, data)
        if unpack:
            return data[0]
        return data

    def _checkok(self, command, typ, data):
        _check_resp('OK', command, typ, data)

    def _gm_label_store(self, cmd, messages, labels, silent):
        response = self._store(cmd, messages, self._normalise_labels(labels),
                               b'X-GM-LABELS', silent=silent)
        return {msg: utf7_decode_sequence(labels)
                for msg, labels in iteritems(response)} if response else None

    def _store(self, cmd, messages, flags, fetch_key, silent):
        """Worker function for the various flag manipulation methods.

        *cmd* is the STORE command to use (eg. '+FLAGS').
        """
        if not messages:
            return {}
        if silent:
            cmd += b".SILENT"

        self.check_state('SELECTED')
        data = self._uid_command_and_check('STORE',
                                              join_message_ids(messages),
                                              cmd,
                                              seq_to_parenstr(flags))
        if silent:
            return None
        return self._filter_fetch_dict(parse_fetch_response(data),
                                       fetch_key)

    def _filter_fetch_dict(self, fetch_dict, key):
        return dict((msgid, data[key])
                    for msgid, data in iteritems(fetch_dict))

    def _normalise_folder(self, folder_name):
        if isinstance(folder_name, binary_type):
            folder_name = folder_name.decode('ascii')
        if self.folder_encode:
            folder_name = encode_utf7(folder_name)
        return _quote(folder_name)

    def _normalise_labels(self, labels):
        if isinstance(labels, (text_type, binary_type)):
            labels = (labels,)
        return [_quote(encode_utf7(l)) for l in labels]

    # More stuff from imaplib

    def _cmd_recent(self):
        """Return most recent 'RECENT' responses if any exist,
        else prompt server for an update using the 'NOOP' command.

        (typ, [data]) = <instance>.recent()

        'data' is None if no new messages,
        else list of RECENT responses, most recent last.
        """
        name = 'RECENT'
        typ, dat = self._untagged_response('OK', [None], name)
        if dat[-1]:
            return typ, dat
        typ, dat = self.noop()  # Prod server for response
        return self._untagged_response(typ, dat, name)

    def _cmd_partial(self, message_num, message_part, start, length):
        """Fetch truncated part of a message.

        (typ, [data, ...]) = <instance>.partial(message_num, message_part, start, length)

        'data' is tuple of message part envelope and data.
        """
        self.check_state('SELECTED')  # NB: obsolete
        name = 'PARTIAL'
        typ, dat = self._simple_command(name, message_num, message_part, start, length)
        return self._untagged_response(typ, dat, 'FETCH')

    def _cmd_proxyauth(self, user):
        """Assume authentication as "user".

        Allows an authorised administrator to proxy into any user's
        mailbox.

        (typ, [data]) = <instance>.proxyauth(user)
        """
        self.check_state('AUTH')

        name = 'PROXYAUTH'
        return self._simple_command('PROXYAUTH', user)

    def _cmd_setannotation(self, *args):
        """(typ, [data]) = <instance>.setannotation(mailbox[, entry, attribute]+)
        Set ANNOTATIONs."""

        typ, dat = self._simple_command('SETANNOTATION', *args)
        return self._untagged_response(typ, dat, 'ANNOTATION')

    def _cmd_xatom(self, name, *args):
        """Allow simple extension commands
                notified by server in CAPABILITY response.

        Assumes command is legal in current state.

        (typ, [data]) = <instance>.xatom(name, arg, ...)

        Returns response appropriate to extension command `name'.
        """
        name = name.upper()
        if not name in self._capabilities:
            raise exceptions.IMAPClientError('unknown extension command: %s' % name)
        return self._simple_command(name, *args)

    def _cmd_myrights(self, mailbox):
        """Show my ACLs for a mailbox (i.e. the rights that I have on mailbox).

        (typ, [data]) = <instance>.myrights(mailbox)
        """
        self.check_state('AUTH','SELECTED')
        typ,dat = self._simple_command('MYRIGHTS', mailbox)
        return self._untagged_response(typ, dat, 'MYRIGHTS')

    def _cmd_login_cram_md5(self, user, password):
        """ Force use of CRAM-MD5 authentication.

        (typ, [data]) = <instance>.login_cram_md5(user, password)
        """
        self.user, self.password = user, password
        return self.authenticate('CRAM-MD5', self._CRAM_MD5_AUTH)

    def _CRAM_MD5_AUTH(self, challenge):
        """ Authobject to use with CRAM-MD5 authentication. """
        import hmac
        pwd = (self.password.encode('utf-8') if isinstance(self.password, str)
               else self.password)
        return self.user + " " + hmac.HMAC(pwd, challenge, 'md5').hexdigest()


    def _cmd_check(self):
        """Checkpoint mailbox on server.

        (typ, [data]) = <instance>.check()
        """
        self.check_state('SELECTED')
        return self._simple_command('CHECK')

    def _cmd_deleteacl(self, mailbox, who):
        """Delete the ACLs (remove any rights) set for who on mailbox.

        (typ, [data]) = <instance>.deleteacl(mailbox, who)
        """
        self.check_state('AUTH','SELECTED')
        return self._simple_command('DELETEACL', mailbox, who)

    def _cmd_getannotation(self, mailbox, entry, attribute):
        """(typ, [data]) = <instance>.getannotation(mailbox, entry, attribute)
        Retrieve ANNOTATIONs."""

        typ, dat = self._simple_command('GETANNOTATION', mailbox, entry, attribute)
        return self._untagged_response(typ, dat, 'ANNOTATION')

def _quote(arg):
    if isinstance(arg, text_type):
        arg = arg.replace('\\', '\\\\')
        arg = arg.replace('"', '\\"')
        q = '"'
    else:
        arg = arg.replace(b'\\', b'\\\\')
        arg = arg.replace(b'"', b'\\"')
        q = b'"'
    return q + arg + q


def _normalise_search_criteria(criteria, charset=None):
    if not criteria:
        raise exceptions.InvalidCriteriaError('no criteria specified')
    if not charset:
        charset = 'us-ascii'

    if isinstance(criteria, (text_type, binary_type)):
        return [to_bytes(criteria, charset)]

    out = []
    for item in criteria:
        if isinstance(item, int):
            out.append(str(item).encode('ascii'))
        elif isinstance(item, (datetime, date)):
            out.append(format_criteria_date(item))
        elif isinstance(item, (list, tuple)):
            # Process nested criteria list and wrap in parens.
            inner = _normalise_search_criteria(item)
            inner[0] = b'(' + inner[0]
            inner[-1] = inner[-1] + b')'
            out.extend(inner)  # flatten
        else:
            out.append(_quoted.maybe(to_bytes(item, charset)))
    return out


def _normalise_sort_criteria(criteria, charset=None):
    if isinstance(criteria, (text_type, binary_type)):
        criteria = [criteria]
    return b'(' + b' '.join(to_bytes(item).upper() for item in criteria) + b')'


class _literal(bytes):
    """Hold message data that should always be sent as a literal."""
    pass


class _quoted(binary_type):
    """
    This class holds a quoted bytes value which provides access to the
    unquoted value via the *original* attribute.

    They should be created via the *maybe* classmethod.
    """

    @classmethod
    def maybe(cls, original):
        """Maybe quote a bytes value.

        If the input requires no quoting it is returned unchanged.

        If quoting is required a *_quoted* instance is returned. This
        holds the quoted version of the input while also providing
        access to the original unquoted source.
        """
        quoted = original.replace(b'\\', b'\\\\')
        quoted = quoted.replace(b'"', b'\\"')
        if quoted != original or b' ' in quoted or not quoted:
            out = cls(b'"' + quoted + b'"')
            out.original = original
            return out
        return original


# normalise_text_list, seq_to_parentstr etc have to return unicode
# because imaplib handles flags and sort criteria assuming these are
# passed as unicode
def normalise_text_list(items):
    return list(_normalise_text_list(items))


def seq_to_parenstr(items):
    return _join_and_paren(_normalise_text_list(items))


def seq_to_parenstr_upper(items):
    return _join_and_paren(item.upper() for item in _normalise_text_list(items))


def _join_and_paren(items):
    return '(' + ' '.join(items) + ')'


def _normalise_text_list(items):
    if isinstance(items, (text_type, binary_type)):
        items = (items,)
    return (to_unicode(c) for c in items)


def join_message_ids(messages):
    """Convert a sequence of messages ids or a single integer message id
    into an id byte string for use with IMAP commands
    """
    if isinstance(messages, (text_type, binary_type, integer_types)):
        messages = (to_bytes(messages),)
    return b','.join(_maybe_int_to_bytes(m) for m in messages)


def _maybe_int_to_bytes(val):
    if isinstance(val, integer_types):
        return str(val).encode('us-ascii') if PY3 else str(val)
    return to_bytes(val)


def _parse_untagged_response(text):
    assert_imap_protocol(text.startswith(b'* '))
    text = text[2:]
    if text.startswith((b'OK ', b'NO ')):
        return tuple(text.split(b' ', 1))
    return parse_response([text])


def pop_with_default(dct, key, default):
    if key in dct:
        return dct.pop(key)
    return default


def as_pairs(items):
    i = 0
    last_item = None
    for item in items:
        if i % 2:
            yield last_item, item
        else:
            last_item = item
        i += 1


def as_triplets(items):
    a = iter(items)
    return zip(a, a, a)


def _is8bit(data):
    return isinstance(data, _literal) or any(b > 127 for b in iterbytes(data))


def _iter_with_last(items):
    last_i = len(items) - 1
    for i, item in enumerate(items):
        yield item, i == last_i


_not_present = object()


class _dict_bytes_normaliser(object):
    """Wrap a dict with unicode/bytes keys and normalise the keys to
    bytes.
    """

    def __init__(self, d):
        self._d = d

    def iteritems(self):
        for key, value in iteritems(self._d):
            yield to_bytes(key), value

    # For Python 3 compatibility.
    items = iteritems

    def __contains__(self, ink):
        for k in self._gen_keys(ink):
            if k in self._d:
                return True
        return False

    def get(self, ink, default=_not_present):
        for k in self._gen_keys(ink):
            try:
                return self._d[k]
            except KeyError:
                pass
        if default == _not_present:
            raise KeyError(ink)
        return default

    def pop(self, ink, default=_not_present):
        for k in self._gen_keys(ink):
            try:
                return self._d.pop(k)
            except KeyError:
                pass
        if default == _not_present:
            raise KeyError(ink)
        return default

    def _gen_keys(self, k):
        yield k
        if isinstance(k, binary_type):
            yield to_unicode(k)
        else:
            yield to_bytes(k)


def debug_trunc(v, maxlen):
    if len(v) < maxlen:
        return repr(v)
    hl = maxlen // 2
    return repr(v[:hl]) + "..." + repr(v[-hl:])


def utf7_decode_sequence(seq):
    return [decode_utf7(s) for s in seq]


def _parse_quota(quota_rep):
    quota_rep = parse_response(quota_rep)
    rv = list()
    for quota_root, quota_resource_infos in as_pairs(quota_rep):
        for quota_resource_info in as_triplets(quota_resource_infos):
            rv.append(Quota(
                quota_root=to_unicode(quota_root),
                resource=to_unicode(quota_resource_info[0]),
                usage=quota_resource_info[1],
                limit=quota_resource_info[2]
            ))
    return rv

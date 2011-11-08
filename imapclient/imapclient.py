# Copyright (c) 2011, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import re
import select
import socket
import sys
import warnings
from datetime import datetime
from operator import itemgetter

import imaplib
import response_lexer

    
try:
    import oauth2
except ImportError:
    oauth2 = None

import imap_utf7
from fixed_offset import FixedOffset


__all__ = ['IMAPClient', 'DELETED', 'SEEN', 'ANSWERED', 'FLAGGED', 'DRAFT', 'RECENT']

from response_parser import parse_response, parse_fetch_response

# We also offer the gmail-specific XLIST command...
if 'XLIST' not in imaplib.Commands:
  imaplib.Commands['XLIST'] = imaplib.Commands['LIST']

# ...and IDLE
if 'IDLE' not in imaplib.Commands:
  imaplib.Commands['IDLE'] = imaplib.Commands['APPEND']


# System flags
DELETED = r'\Deleted'
SEEN = r'\Seen'
ANSWERED = r'\Answered'
FLAGGED = r'\Flagged'
DRAFT = r'\Draft'
RECENT = r'\Recent'         # This flag is read-only

class Namespace(tuple):
    def __new__(cls, personal, other, shared):
        return tuple.__new__(cls, (personal, other, shared)) 

    personal = property(itemgetter(0))
    other = property(itemgetter(1))
    shared = property(itemgetter(2))


class IMAPClient(object):
    """
    A connection to the IMAP server specified by *host* is made when
    the class is instantiated.

    *port* defaults to 143, or 993 if *ssl* is ``True``.

    If *use_uid* is ``True`` unique message UIDs be used for all calls
    that accept message ids (defaults to ``True``).

    If *ssl* is ``True`` an SSL connection will be made (defaults to
    ``False``).

    The *normalise_times* attribute specifies whether datetimes
    returned by ``fetch()`` are normalised to the local system time
    and include no timezone information (native), or are datetimes
    that include timezone information (aware). By default
    *normalise_times* is True (times are normalised to the local
    system time). This attribute can be changed between ``fetch()``
    calls if required.

    The *debug* property can be used to enable debug logging. It can
    be set to an integer from 0 to 5 where 0 disables debug output and
    5 enables full output with wire logging and parsing logs. ``True``
    and ``False`` can also be assigned where ``True`` sets debug level
    4.

    By default, debug output goes to stderr. The *log_file* attribute
    can be assigned to an alternate file handle for writing debug
    output to.
    """

    Error = imaplib.IMAP4.error
    AbortError = imaplib.IMAP4.abort
    ReadOnlyError = imaplib.IMAP4.readonly

    re_status = re.compile(r'^\s*"?(?P<folder>[^"]+)"?\s+'
                           r'\((?P<status_items>.*)\)$')

    def __init__(self, host, port=None, use_uid=True, ssl=False):
        if port is None:
            port = ssl and 993 or 143

        self.host = host
        self.port = port
        self.ssl = ssl
        self.use_uid = use_uid
        self.folder_encode = True
        self.log_file = sys.stderr
        self.normalise_times = True

        self._imap = self._create_IMAP4()
        self._imap._mesg = self._log    # patch in custom debug log method
        self._idle_tag = None

    def _create_IMAP4(self):
        # Create the IMAP instance in a separate method to make unit tests easier
        ImapClass = self.ssl and imaplib.IMAP4_SSL or imaplib.IMAP4
        return ImapClass(self.host, self.port)

    def login(self, username, password):
        """Login using *username* and *password*, returning the
        server response.
        """
        typ, data = self._imap.login(username, password)
        self._checkok('login', typ, data)
        return data[0]

    def oauth_login(self, url, oauth_token, oauth_token_secret,
                    consumer_key='anonymous', consumer_secret='anonymous'):
        """Authenticate using the OAUTH method.

        This only works with IMAP servers that support OAUTH (eg. Gmail).
        """
        if oauth2:
            token = oauth2.Token(oauth_token, oauth_token_secret)
            consumer = oauth2.Consumer(consumer_key, consumer_secret)
            xoauth_callable = lambda x: oauth2.build_xoauth_string(url, consumer, token)
            
            typ, data = self._imap.authenticate('XOAUTH', xoauth_callable)
            self._checkok('authenticate', typ, data)
            return data[0]
        else:
            raise self.Error('The optional oauth2 dependency is needed for oauth authentication')

    def logout(self):
        """Logout, returning the server response.
        """
        typ, data = self._imap.logout()
        self._checkbye('logout', typ, data)
        return data[0]


    def capabilities(self):
        """Returns the server capability list.
        """
        return self._imap.capabilities


    def has_capability(self, capability):
        """Return ``True`` if the IMAP server has the given *capability*.
        """
        # FIXME: this will not detect capabilities that are backwards
        # compatible with the current level. For instance the SORT
        # capabilities may in the future be named SORT2 which is
        # still compatible with the current standard and will not
        # be detected by this method.
        if capability.upper() in self._imap.capabilities:
            return True
        else:
            return False

    def namespace(self):
        """Return the namespace for the account as a (personal, other,
        shared) tuple.

        Each element may be None if no namespace of that type exists,
        or a sequence of (prefix, separator) pairs.

        For convenience the tuple elements may be accessed
        positionally or using attributes named *personal*, *other* and
        *shared*.

        See `RFC 2342 <http://tools.ietf.org/html/rfc2342>`_ for more details.
        """
        typ, data = self._imap.namespace()
        self._checkok('namespace', typ, data)
        return Namespace(*parse_response(data))

    def get_folder_delimiter(self):
        """Return the folder separator used by the IMAP server.

        .. warning::

            The implementation just picks the first folder separator
            from the first namespace returned. This is not
            particularly sensible. Use namespace instead().
        """
        warnings.warn(DeprecationWarning('get_folder_delimiter is going away. Use namespace() instead.'))
        for part in self.namespace():
            for ns in part:
                return ns[1]
        raise self.Error('could not determine folder separator')

    def list_folders(self, directory="", pattern="*"):
        """Get a listing of folders on the server as a list of
        ``(flags, delimiter, name)`` tuples.

        Calling list_folders with no arguments will list all
        folders.

        Specifying *directory* will limit returned folders to that
        base directory. Specifying *pattern* will limit returned
        folders to those with matching names. The wildcards are
        supported in *pattern*. ``*`` matches zero or more of any
        character and ``%`` matches 0 or more characters except the
        folder delimiter.

        Folder names are always returned as unicode strings except if
        folder_decode is not set.
        """
        return self._do_list('LIST', directory, pattern)

    def xlist_folders(self, directory="", pattern="*"):
        """Execute the XLIST command, returning ``(flags, delimiter,
        name)`` tuples.

        This method returns special flags for each folder and a
        localized name for certain folders (e.g. the name of the
        inbox may be localized and the flags can be used to
        determine the actual inbox, even if the name has been
        localized.

        A ``XLIST`` response could look something like::

            [([u'\\HasNoChildren', u'\\Inbox'], '/', u'Inbox'),
             ([u'\\Noselect', u'\\HasChildren'], '/', u'[Gmail]'),
             ([u'\\HasNoChildren', u'\\AllMail'], '/', u'[Gmail]/All Mail'),
             ([u'\\HasNoChildren', u'\\Drafts'], '/', u'[Gmail]/Drafts'),
             ([u'\\HasNoChildren', u'\\Important'], '/', u'[Gmail]/Important'),
             ([u'\\HasNoChildren', u'\\Sent'], '/', u'[Gmail]/Sent Mail'),
             ([u'\\HasNoChildren', u'\\Spam'], '/', u'[Gmail]/Spam'),
             ([u'\\HasNoChildren', u'\\Starred'], '/', u'[Gmail]/Starred'),
             ([u'\\HasNoChildren', u'\\Trash'], '/', u'[Gmail]/Trash')]

        This is a Gmail-specific IMAP extension. It is the
        responsibility of the caller to either check for ``XLIST`` in
        the server capabilites, or to handle the error if the server
        doesn't support this extension.

        The *directory* and *pattern* arguments are as per
        list_folders().
        """
        return self._do_list('XLIST', directory, pattern)

    def list_sub_folders(self, directory="", pattern="*"):
        """Return a list of subscribed folders on the server as
        ``(flags, delimiter, name)`` tuples.

        The default behaviour will list all subscribed folders. The
        *directory* and *pattern* arguments are as per list_folders().
        """
        return self._do_list('LSUB', directory, pattern)

    def _do_list(self, cmd, directory, pattern):
        typ, dat = self._imap._simple_command(cmd, directory, pattern)
        self._checkok(cmd, typ, dat)
        typ, dat = self._imap._untagged_response(typ, dat, cmd)
        return self._proc_folder_list(dat)

    def _proc_folder_list(self, folder_data):
        # Filter out empty strings and None's.
        # This also deals with the special case of - no 'untagged'
        # responses (ie, no folders). This comes back as [None].
        folder_data = [item for item in folder_data if item not in ('', None)]

        ret = []
        parsed = parse_response(folder_data)
        while parsed:
            raw_flags, delim, raw_name = parsed[:3]
            parsed = parsed[3:]
            flags = [imap_utf7.decode(flag) for flag in raw_flags]
            ret.append((flags, delim, self._decode_folder_name(raw_name)))
        return ret

    def select_folder(self, folder, readonly=False):
        """Set the current folder on the server.

        Future calls to methods such as search and fetch will act on
        the selected folder.

        Returns a dictionary containing the ``SELECT`` response. At least
        the ``EXISTS``, ``FLAGS`` and ``RECENT`` keys are guaranteed
        to exist. An example::

            {'EXISTS': 3,
             'FLAGS': ('\\Answered', '\\Flagged', '\\Deleted', ... ),
             'RECENT': 0,
             'PERMANENTFLAGS': ('\\Answered', '\\Flagged', '\\Deleted', ... ),
             'READ-WRITE': True,
             'UIDNEXT': 11,
             'UIDVALIDITY': 1239278212}
        """
        typ, data = self._imap.select(self._encode_folder_name(folder), readonly)
        self._checkok('select', typ, data)
        return self._process_select_response(self._imap.untagged_responses)

    def _process_select_response(self, resp):
        out = {}
        for key, value in resp.iteritems():
            key = key.upper()
            if key == 'OK':
                continue
            elif key in ('EXISTS', 'RECENT', 'UIDNEXT', 'UIDVALIDITY'):
                value = int(value[0])
            elif key in ('FLAGS', 'PERMANENTFLAGS'):
                value = parse_response(value)[0]
            elif key == 'READ-WRITE':
                value = True
                                 
            out[key] = value
        return out

    def noop(self):
        """Execute the NOOP command.

        This command returns immediately, returning any server side
        status updates. It can also be used to reset any auto-logout
        timers.

        The return value is the server command response message
        followed by a list of status responses. For example::

            ('NOOP completed.',
             [(4, 'EXISTS'),
              (3, 'FETCH', ('FLAGS', ('bar', 'sne'))),
              (6, 'FETCH', ('FLAGS', ('sne',)))])

        """
        tag = self._imap._command('NOOP')
        return self._consume_until_tagged_response(tag, 'NOOP')

    def idle(self):
        """Put the server into IDLE mode.

        In this mode the server will return unsolicited responses
        about changes to the selected mailbox. This method returns
        immediately. Use ``idle_check()`` to look for IDLE responses
        and ``idle_done()`` to stop IDLE mode.

        .. note::

            Any other commmands issued while the server is in IDLE
            mode will fail.

        See `RFC 2177 <http://tools.ietf.org/html/rfc2177>`_ for more
        information about the IDLE extension.
        """
        self._idle_tag = self._imap._command('IDLE')
        resp = self._imap._get_response()
        if resp is not None:
            raise self.Error('Unexpected IDLE response: %s' % resp)

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

            [('OK', 'Still here'),
             (1, 'EXISTS'),
             (1, 'FETCH', ('FLAGS', ('\\NotJunk',)))]
        """
        # make the socket non-blocking so the timeout can be
        # implemented for this call
        if self.ssl:
            sock = self._imap.sslobj
        else:
            sock = self._imap.sock
        sock.setblocking(0)
        try:
            resps = []
            rs, _, _ = select.select([sock], [], [], timeout)
            if rs:
                while True:
                    try:
                        line = self._imap._get_line()
                    except (socket.timeout, socket.error):
                        break
                    else:
                        resps.append(_parse_untagged_response(line))
            return resps
        finally:
            sock.setblocking(1)

    def idle_done(self):
        """Take the server out of IDLE mode.

        This method should only be called if the server is already in
        IDLE mode.

        The return value is of the form ``(command_text,
        idle_responses)`` where *command_text* is the text sent by the
        server when the IDLE command finished (eg. ``'Idle
        terminated'``) and *idle_responses* is a list of parsed idle
        responses received since the last call to ``idle_check()`` (if
        any). These are returned in parsed form as per
        ``idle_check()``.
        """
        self._imap.send('DONE\r\n')
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
        elif isinstance(what, basestring):
            what = (what,)
        what_ = '(%s)' % (' '.join(what))

        typ, data = self._imap.status(self._encode_folder_name(folder), what_)
        self._checkok('status', typ, data)

        match = self.re_status.match(data[0])
        if not match:
            raise self.Error('Could not get the folder status')

        out = {}
        status_items = match.group('status_items').strip().split()
        while status_items:
            key = status_items.pop(0)
            value = long(status_items.pop(0))
            out[key] = value
        return out

    def close_folder(self):
        """Close the currently selected folder, returning the server
        response string.
        """
        typ, data = self._imap.close()
        self._checkok('close', typ, data)
        return data[0]

    def create_folder(self, folder):
        """Create *folder* on the server returning the server response string.
        """
        typ, data = self._imap.create(self._encode_folder_name(folder))
        self._checkok('create', typ, data)
        return data[0]

    def rename_folder(self, old_name, new_name):
        """Change the name of a folder on the server.
        """
        typ, data = self._imap.rename(self._encode_folder_name(old_name),
                                      self._encode_folder_name(new_name))
        self._checkok('rename', typ, data)
        return data[0]
        
    def delete_folder(self, folder):
        """Delete *folder* on the server returning the server response string.
        """
        typ, data = self._imap.delete(self._encode_folder_name(folder))
        self._checkok('delete', typ, data)
        return data[0]

    def folder_exists(self, folder):
        """Return ``True`` if *folder* exists on the server.
        """
        typ, data = self._imap.list('', self._encode_folder_name(folder))
        self._checkok('list', typ, data)
        data = [x for x in data if x]
        return len(data) == 1 and data[0] != None

    def subscribe_folder(self, folder):
        """Subscribe to *folder*, returning the server response string.
        """
        typ, data = self._imap.subscribe(self._encode_folder_name(folder))
        self._checkok('subscribe', typ, data)
        return data

    def unsubscribe_folder(self, folder):
        """Unsubscribe to *folder*, returning the server response string.
        """
        typ, data = self._imap.unsubscribe(self._encode_folder_name(folder))
        self._checkok('unsubscribe', typ, data)
        return data

    def search(self, criteria='ALL', charset=None):
        """Return a list of messages ids matching *criteria*.

        *criteria* should be a list of of one or more criteria
        specifications or a single critera string. Example values
        include::

             'NOT DELETED'
             'UNSEEN'
             'SINCE 1-Feb-2011'

        *charset* specifies the character set of the strings in the
        criteria. It defaults to US-ASCII.

        See `RFC 3501 section 6.4.4 <http://tools.ietf.org/html/rfc3501#section-6.4.4>`_
        for more details.
        """
        if not criteria:
            raise ValueError('no criteria specified')

        if isinstance(criteria, basestring):
            criteria = (criteria,)
        crit_list = ['(%s)' % c for c in criteria]

        if self.use_uid:
            if charset is None:
                typ, data = self._imap.uid('SEARCH', *crit_list)
            else:
                typ, data = self._imap.uid('SEARCH', 'CHARSET', charset,
                    *crit_list)
        else:
            typ, data = self._imap.search(charset, *crit_list)

        self._checkok('search', typ, data)
        if data == [None]: # no untagged responses...
            return []

        return [ long(i) for i in data[0].split() ]


    def sort(self, sort_criteria, criteria='ALL', charset='UTF-8'):
        """Return a list of message ids sorted by *sort_criteria* and
        optionally filtered by *criteria*.

        Example values for *sort_criteria* include::

            ARRIVAL
            REVERSE SIZE
            SUBJECT

        The *criteria* argument is as per search(). 
        See `RFC 5256 <http://tools.ietf.org/html/rfc5256>`_ for full details.

        Note that SORT is an extension to the IMAP4 standard so it may
        not be supported by all IMAP servers.
        """
        if not criteria:
            raise ValueError('no criteria specified')

        if not self.has_capability('SORT'):
            raise self.Error('The server does not support the SORT extension')

        if isinstance(criteria, basestring):
            criteria = (criteria,)
        crit_list = ['(%s)' % c for c in criteria]

        sort_criteria = seq_to_parenlist([ s.upper() for s in sort_criteria])

        if self.use_uid:
            typ, data = self._imap.uid('SORT', sort_criteria, charset,
                *crit_list)
        else:
            typ, data = self._imap.sort(sort_criteria, charset, *crit_list)

        self._checkok('sort', typ, data)

        return [long(i) for i in data[0].split()]


    def get_flags(self, messages):
        """Return the flags set for each message in *messages*.

        The return value is a dictionary structured like this: ``{
        msgid1: [flag1, flag2, ... ], }``.
        """
        response = self.fetch(messages, ['FLAGS'])
        return self._flatten_dict(response)


    def add_flags(self, messages, flags):
        """Add *flags* to *messages*.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*).
        """
        return self._store('+FLAGS', messages, flags)


    def remove_flags(self, messages, flags):
        """Remove one or more *flags* from *messages*.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*).
        """
        return self._store('-FLAGS', messages, flags)


    def set_flags(self, messages, flags):
        """Set the *flags* for *messages*.

        *flags* should be a sequence of strings.

        Returns the flags set for each modified message (see
        *get_flags*).
        """
        return self._store('FLAGS', messages, flags)


    def delete_messages(self, messages):
        """Delete one or more *messages* from the currently selected
        folder.

        Returns the flags set for each modified message (see
        *get_flags*).
        """
        return self.add_flags(messages, DELETED)


    def fetch(self, messages, data, modifiers=None):
        """Retrieve selected *data* associated with one or more *messages*.

        *data* should be specified as a sequnce of strings, one item
        per data selector, for example ``['INTERNALDATE',
        'RFC822']``.

        *modifiers* are required for some extensions to the IMAP
        protocol (eg. RFC 4551). These should be a sequnce of strings
        if specified, for example ``['CHANGEDSINCE 123']``.

        A dictionary is returned, indexed by message number. Each item
        in this dictionary is also a dictionary, with an entry
        corresponding to each item in *data*.

        In addition to an element for each *data* item, the dict
        returned for each message also contains a *SEQ* key containing
        the sequence number for the message. This allows for mapping
        between the UID and sequence number (when the *use_uid*
        property is ``True``).

        Example::

            >> c.fetch([3293, 3230], ['INTERNALDATE', 'FLAGS'])
            {3230: {'FLAGS': ('\\Seen',),
                    'INTERNALDATE': datetime.datetime(2011, 1, 30, 13, 32, 9),
                    'SEQ': 84},
             3293: {'FLAGS': (),
                    'INTERNALDATE': datetime.datetime(2011, 2, 24, 19, 30, 36),
                    'SEQ': 110}}

        """
        if not messages:
            return {}

        msg_list = messages_to_str(messages)
        data_list = seq_to_parenlist([p.upper() for p in data])
        modifiers_list = None
        if modifiers is not None:
          modifiers_list = seq_to_parenlist([m.upper() for m in modifiers])

        if self.use_uid:
            tag = self._imap._command('UID', 'FETCH', msg_list, data_list, modifiers_list)
        else:
            tag = self._imap._command('FETCH', msg_list, data_list, modifiers_list)
        typ, data = self._imap._command_complete('FETCH', tag)
        self._checkok('fetch', typ, data)
        typ, data = self._imap._untagged_response(typ, data, 'FETCH')
        return parse_fetch_response(data, self.normalise_times)

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
            time_val = '"%s"' % datetime_to_imap(msg_time)
        else:
            time_val = None

        flags_list = seq_to_parenlist(flags)

        typ, data = self._imap.append(self._encode_folder_name(folder),
                                      flags_list, time_val, msg)
        self._checkok('append', typ, data)

        return data[0]

    def copy(self, messages, folder):
        """Copy one or more messages from the current folder to
        *folder*. Returns the COPY response string returned by the
        server.
        """
        msg_list = messages_to_str(messages)
        folder = self._encode_folder_name(folder)

        if self.use_uid:
            typ, data = self._imap.uid('COPY', msg_list, folder)
        else:
            typ, data = self._imap.copy(msg_list, folder)
        self._checkok('copy', typ, data)
        return data[0]

    def expunge(self):
        """Remove any messages from the currently selected folder that
        have the ``\\Deleted`` flag set.
        """
        typ, data = self._imap.expunge()
        self._checkok('expunge', typ, data)
        #TODO: expunge response

    def getacl(self, folder):
        """Returns a list of ``(who, acl)`` tuples describing the
        access controls for *folder*.
        """
        typ, data = self._imap.getacl(folder)
        self._checkok('getacl', typ, data)

        parts = list(response_lexer.TokenSource(data))
        parts = parts[1:]       # First item is folder name
        return [(parts[i], parts[i+1]) for i in xrange(0, len(parts), 2)]

    def setacl(self, folder, who, what):
        """Set an ACL (*what*) for user (*who*) for a folder.

        Set *what* to an empty string to remove an ACL. Returns the
        server response string.
        """
        typ, data = self._imap.setacl(folder, who, what)
        self._checkok('setacl', typ, data)
        return data[0]

    def _check_resp(self, expected, command, typ, data):
        """Check command responses for errors.

        Raises IMAPClient.Error if the command fails.
        """
        if typ != expected:
            raise self.Error('%s failed: %r' % (command, data[0]))

    def _consume_until_tagged_response(self, tag, command):
        tagged_commands = self._imap.tagged_commands
        resps = []
        while True:
            line = self._imap._get_response()
            if tagged_commands[tag]:
                break
            resps.append(_parse_untagged_response(line))
        typ, data = tagged_commands.pop(tag)
        self._checkok(command, typ, data)
        return data[0], resps

    def _checkok(self, command, typ, data):
        self._check_resp('OK', command, typ, data)

    def _checkbye(self, command, typ, data):
        self._check_resp('BYE', command, typ, data)

    def _store(self, cmd, messages, flags):
        """Worker function for the various flag manipulation methods.

        *cmd* is the STORE command to use (eg. '+FLAGS').
        """
        if not messages:
            return {}

        msg_list = messages_to_str(messages)
        flag_list = seq_to_parenlist(flags)

        if self.use_uid:
            typ, data = self._imap.uid('STORE', msg_list, cmd, flag_list)
        else:
            typ, data = self._imap.store(msg_list, cmd, flag_list)
        self._checkok('store', typ, data)
        return self._flatten_dict(parse_fetch_response((data)))

    def _flatten_dict(self, fetch_dict):
        return dict([
            (msgid, data.values()[0])
            for msgid, data in fetch_dict.iteritems()
            ])

    def _decode_folder_name(self, name):
        if self.folder_encode:
            return imap_utf7.decode(name)
        return name

    def _encode_folder_name(self, name):
        if self.folder_encode:
            name = imap_utf7.encode(name)
        # imaplib assumes that if a command argument (in this case a
        # folder name) has double quotes around it, then it doesn't
        # need quoting. This "feature" prevents creation of folders
        # with names that start and end with double quotes.
        #
        # To work around this IMAPClient performs the quoting
        # itself. This adds start and end double quotes which also
        # serves to fool IMAP4._checkquote into not attempting further
        # quoting. A hack but it works.
        return _quote_arg(name)

    def __debug_get(self):
        return self._imap.debug

    def __debug_set(self, level):
        if level is True:
            level = 4
        elif level is False:
            level = 0
        self._imap.debug = level

    debug = property(__debug_get, __debug_set)

    def _log(self, text):
        self.log_file.write('%s %s\n' % (datetime.now().strftime('%M:%S.%f'), text))
        self.log_file.flush()
        

def messages_to_str(messages):
    """Convert a sequence of messages ids or a single integer message id
    into an id list string for use with IMAP commands
    """
    if isinstance(messages, (str, int, long)):
        messages = (messages,)
    elif not isinstance(messages, (tuple, list)):
        raise ValueError('invalid message list: %r' % messages)
    return ','.join([str(m) for m in messages])


def seq_to_parenlist(flags):
    """Convert a sequence of strings into parenthised list string for
    use with IMAP commands.
    """
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)


def datetime_to_imap(dt):
    """Convert a datetime instance to a IMAP datetime string.

    If timezone information is missing the current system
    timezone is used.
    """
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=FixedOffset.for_system())
    return dt.strftime("%d-%b-%Y %H:%M:%S %z")


def _quote_arg(arg):
  arg = arg.replace('\\', '\\\\')
  arg = arg.replace('"', '\\"')
  return '"%s"' % arg


def _parse_untagged_response(text):
    assert text.startswith('* ')
    text = text[2:]
    if text.startswith(('OK ', 'NO ')):
        return tuple(text.split(' ', 1))
    return parse_response([text]) 
                

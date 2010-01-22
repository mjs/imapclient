# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

import re
import imaplib
import shlex
import datetime
#imaplib.Debug = 5

import imap_utf7
from fixed_offset import FixedOffset


__all__ = ['IMAPClient', 'DELETED', 'SEEN', 'ANSWERED', 'FLAGGED', 'DRAFT',
    'RECENT']

# System flags
DELETED = r'\Deleted'
SEEN = r'\Seen'
ANSWERED = r'\Answered'
FLAGGED = r'\Flagged'
DRAFT = r'\Draft'
RECENT = r'\Recent'         # This flag is read-only


class IMAPClient(object):
    """
    A Pythonic, easy-to-use IMAP client class.

    Unlike imaplib, arguments and returns values are Pythonic and readily
    usable. Exceptions are raised when problems occur (no error checking of
    return values is required).

    Message unique identifiers (UID) can be used with any call. The use_uid
    argument to the constructor and the use_uid attribute control whether UIDs
    are used.

    Any method that accepts message id's takes either a sequence containing
    message IDs (eg. [1,2,3]) or a single message ID as an integer.

    Any method that accepts message flags takes either a sequence containing
    message flags (eg. [DELETED, 'foo', 'Bar']) or a single message flag (eg.
    'Foo'). See the constants at the top of this file for commonly used flags.

    Any method that takes a folder name will accept a standard string or a
    unicode string. Unicode strings will be transparently encoded using
    modified UTF-7 as specified by RFC-2060. Such folder names will be returned
    as unicode strings by methods that return folder names.

    Transparent folder name encoding can be enabled or disabled with the
    folder_encode attribute. It defaults to True.

    The IMAP related exceptions that will be raised by this class are:
        IMAPClient.Error
        IMAPClient.AbortError
        IMAPClient.ReadOnlyError
    These are aliases for the imaplib.IMAP4 exceptions of the same name. Socket
    errors may also be raised in the case of network errors.
    """

    Error = imaplib.IMAP4.error
    AbortError = imaplib.IMAP4.abort
    ReadOnlyError = imaplib.IMAP4.readonly

    re_sep = re.compile('^\(\("[^"]*" "([^"]+)"\)\)')
#     re_folder = re.compile('\([^)]*\) "[^"]+" "?([^"]+)"?')
    re_folder = re.compile(r'\([^)]*\) "[^"]+" (?P<qqq>"?)(?P<folder>.+)(?P=qqq)')
    re_status = re.compile(r'^\s*"?(?P<folder>[^"]+)"?\s+'
                           r'\((?P<status_items>.*)\)$')

    def __init__(self, host, port=None, use_uid=True, ssl=False):
        """Initialise object instance and connect to the remote IMAP server.

        @param host: The IMAP server address/hostname to connect to.
        @param port: The port number to use (default is 143, 993 for SSL).
        @param use_uid: Should message UIDs be used (default is True).
        @param ssl: Make an SSL connection (default is False)
        """
        if ssl:
            ImapClass = imaplib.IMAP4_SSL
            default_port = 993
        else:
            ImapClass = imaplib.IMAP4
            default_port = 143

        if port is None:
            port = default_port

        self._imap = ImapClass(host, port)
        self.use_uid = use_uid
        self.folder_encode = True

   
    def login(self, username, password):
        """Perform a simple login
        """
        typ, data = self._imap.login(username, password)
        self._checkok('login', typ, data)
        return data[0]


    def logout(self):
        """Perform a logout
        """
        typ, data = self._imap.logout()
        self._checkbye('logout', typ, data)
        return data[0]


    def capabilities(self):
        """Returns the server capability list
        """
        return self._imap.capabilities


    def has_capability(self, capability):
        """Checks if the server has the given capability.

        @param capability: capability to test (eg 'SORT')
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

    def get_folder_delimiter(self):
        """Determine the folder separator used by the IMAP server.

        @return: The folder separator.
        @rtype: string
        """
        typ, data = self._imap.namespace()
        self._checkok('namespace', typ, data)

        match = self.re_sep.match(data[0])
        if match:
            return match.group(1)
        else:
            raise self.Error('could not determine folder separator')


    def list_folders(self, directory="", pattern="*"):
        """Get a listing of folders on the server.

        The default behaviour (no args) will list all folders for the logged in
        user.

        @param directory: The base directory to look for folders from.
        @param pattern: A pattern to match against folder names. Only folder
            names matching this pattern will be returned. Wildcards accepted.
        @return: A list of folder names. Each folder name will be either a
            string or a unicode string (if the folder on the server required
            decoding). If the folder_encode attribute is False, no decoding
            will be performed and only ordinary strings will be returned.
        """
        typ, data = self._imap.list(directory, pattern)
        self._checkok('list', typ, data)
        return self._proc_folder_list(data)


    def list_sub_folders(self, directory="", pattern="*"):
        """Get a listing of subscribed folders on the server.

        The default behaviour (no args) will list all subscribed folders for the
        logged in user.

        @param directory: The base directory to look for folders from.
        @param pattern: A pattern to match against folder names. Only folder
            names matching this pattern will be returned. Wildcards accepted.
        @return: A list of folder names. As per the return of list_folders().
        """
        typ, data = self._imap.lsub(directory, pattern)
        self._checkok('lsub', typ, data)
        return self._proc_folder_list(data)


    def _proc_folder_list(self, folder_data):
        folders = []
        for line in folder_data:
            #TODO can the FetchParser code be adapted for use here?
            folder_text = None
            if isinstance(line, tuple):
                folder_text = line[-1]
            elif line:
                match = self.re_folder.match(line)
                if match:
                    folder_text = match.group('folder')
                    folder_text = folder_text.replace(r'\"', '"')
                    folder_text = folder_text.replace(r'\\', '\\')
            if folder_text is not None:
                folders.append(self._decode_folder_name(folder_text))
        return folders
        

    def select_folder(self, folder):
        """Select the current folder on the server. Future calls to methods
        such as search and fetch will act on the selected folder.

        @param folder: The folder name.
        @return: Number of messages in the folder.
        @rtype: long int
        """
        typ, data = self._imap.select(self._encode_folder_name(folder))
        self._checkok('select', typ, data)
        return long(data[0])


    def folder_status(self, folder, what=None):
        """Requests the status from folder.

        @param folder: The folder name.
        @param what: A sequence of status items to query. Defaults to
            ('MESSAGES', 'RECENT', 'UIDNEXT', 'UIDVALIDITY', 'UNSEEN').
        @return: Dictionary of the status items for the folder. The keys match
            the items specified in the what parameter.
        @rtype: dict
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
        """Close the currently selected folder.

        @return: Server response.
        """
        typ, data = self._imap.close()
        self._checkok('close', typ, data)
        return data[0]


    def create_folder(self, folder):
        """Create a new folder on the server.

        @param folder: The folder name.
        @return: Server response.
        """
        typ, data = self._imap.create(self._encode_folder_name(folder))
        self._checkok('create', typ, data)
        return data[0]


    def delete_folder(self, folder):
        """Delete a new folder on the server.

        @param folder: Folder name to delete.
        @return: Server response.
        """
        typ, data = self._imap.delete(self._encode_folder_name(folder))
        self._checkok('delete', typ, data)
        return data[0]


    def folder_exists(self, folder):
        """Determine if a folder exists on the server.

        @param folder: Full folder name to look for.
        @return: True if the folder exists. False otherwise.
        """
        typ, data = self._imap.list('', self._encode_folder_name(folder))
        self._checkok('list', typ, data)
        return len(data) == 1 and data[0] != None


    def subscribe_folder(self, folder):
        """Subscribe to a folder.

        @param folder: Folder name to subscribe to.
        @return: Server response message.
        """
        typ, data = self._imap.subscribe(self._encode_folder_name(folder))
        self._checkok('subscribe', typ, data)
        return data


    def unsubscribe_folder(self, folder):
        """Unsubscribe a folder.

        @param folder: Folder name to unsubscribe.
        @return: Server response message.
        """
        typ, data = self._imap.unsubscribe(self._encode_folder_name(folder))
        self._checkok('unsubscribe', typ, data)
        return data


    def search(self, criteria='ALL', charset=None):
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

        return [ long(i) for i in data[0].split() ]


    def sort(self, sort_criteria, criteria='ALL', charset='UTF-8' ):
        """Returns a list of messages sorted by sort_criteria.

        Note that this is an extension to the IMAP4:
        http://www.ietf.org/internet-drafts/draft-ietf-imapext-sort-19.txt
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

        return [ long(i) for i in data[0].split() ]


    def get_flags(self, messages):
        """Return the flags set for messages

        @param messages: Message IDs to check flags for
        @return: As for add_f
            { msgid1: [flag1, flag2, ... ], }
        """
        response = self.fetch(messages, ['FLAGS'])
        return self._flatten_dict(response)


    def add_flags(self, messages, flags):
        """Add one or more flags to messages

        @param messages: Message IDs to add flags to
        @param flags: Sequence of flags to add
        @return: The flags set for each message ID as a dictionary
            { msgid1: [flag1, flag2, ... ], }
        """
        return self._store('+FLAGS', messages, flags)


    def remove_flags(self, messages, flags):
        """Remove one or more flags from messages

        @param messages: Message IDs to remove flags from
        @param flags: Sequence of flags to remove
        @return: As for get_flags.
        """
        return self._store('-FLAGS', messages, flags)


    def set_flags(self, messages, flags):
        """Set the flags for messages

        @param messages: Message IDs to set flags for
        @param flags: Sequence of flags to set
        @return: As for get_flags.
        """
        return self._store('FLAGS', messages, flags)


    def delete_messages(self, messages):
        """Short-hand method for deleting one or more messages

        @param messages: Message IDs to mark for deletion.
        @return: Same as for get_flags.
        """
        return self.add_flags(messages, DELETED)


    def fetch(self, messages, parts):
        """Retrieve selected data items for one or more messages.

        @param messages: Message IDs to fetch.
        @param parts: A sequence of data items to retrieve.
        @return: A dictionary indexed by message number. Each item is itself a
            dictionary containing the requested message parts.
            INTERNALDATE parts will be returned as datetime objects converted
            to the local machine's time zone.
        """
        if not messages:
            return {}

        msg_list = messages_to_str(messages)
        parts_list = seq_to_parenlist([p.upper() for p in parts])

        if self.use_uid:
            typ, data = self._imap.uid('FETCH', msg_list, parts_list)
        else:
            typ, data = self._imap.fetch(msg_list, parts_list)
        self._checkok('fetch', typ, data)

        parser = FetchParser()
        return parser(data)


    def append(self, folder, msg, flags=(), msg_time=None):
        """Append a message to a folder

        @param folder: Folder name to append to.
        @param msg: Message body as a string.
        @param flags: Sequnce of message flags to set. If not specified no
            flags will be set.
        @param msg_time: Optional date and time to set for the message. The
            server will set a time if it isn't specified. If msg_time contains
            timezone information (tzinfo), this will be honoured. Otherwise the
            local machine's time zone sent to the server.
        @type msg_time: datetime.datetime
        @return: The append response returned by the server.
        @rtype: str
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
        """XXX
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
        typ, data = self._imap.expunge()
        self._checkok('expunge', typ, data)
        #TODO: expunge response


    def getacl(self, folder):
        """Get the ACL for a folder

        @param folder: Folder name to get the ACL for.
        @return: A list of (who, acl) tuples
        """
        typ, data = self._imap.getacl(folder)
        self._checkok('getacl', typ, data)

        parts = shlex.split(data[0])
        parts = parts[1:]       # First item is folder name

        out = []
        for i in xrange(0, len(parts), 2):
            out.append((parts[i], parts[i+1]))
        return out


    def setacl(self, folder, who, what):
        """Set an ACL for a folder

        @param folder: Folder name to set an ACL for.
        @param who: User or group ID for the ACL.
        @param what: A string describing the ACL. Set to '' to remove an ACL.
        @return: Server response string.
        """
        typ, data = self._imap.setacl(folder, who, what)
        self._checkok('setacl', typ, data)
        return data[0]


    def _check_resp(self, expected, command, typ, data):
        """Check command responses for errors.

        @raise: Error if a command failed.
        """
        if typ != expected:
            raise self.Error('%s failed: %r' % (command, data[0]))


    def _checkok(self, command, typ, data):
        self._check_resp('OK', command, typ, data)


    def _checkbye(self, command, typ, data):
        self._check_resp('BYE', command, typ, data)


    def _store(self, cmd, messages, flags):
        """Worker function for flag manipulation functions

        @param cmd: STORE command to use (eg. '+FLAGS')
        @param messages: Sequence of message IDs
        @param flags: Sequence of flags to set.
        @return: The flags set for each message ID as a dictionary
            { msgid1: [flag1, flag2, ... ], }
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

        return self._flatten_dict(FetchParser()(data))


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
            return imap_utf7.encode(name)
        return name


class FetchParser(object):
    """
    Parse an IMAP FETCH response and convert the return values to useful Python
    values.
    """

    def parse(self, response):
        out = {}
        for response_item in response:
            msgid, data = self.parse_data(response_item)

            if msgid != None:
                # Response for a new message
                current_msg_data = {}
                out[msgid] = current_msg_data

            current_msg_data.update(data)

        return out

    __call__ = parse

    def parse_data(self, data):
        out = {}

        if isinstance(data, str):
            if data == ')':
                # End of response for current message
                return None, {}

        elif isinstance(data, tuple):
            data, literal_data = data

        else:
            raise ValueError("don't know how to handle %r" % data)

        data = data.lstrip()
        msgid = None
        if data[0].isdigit():
            # Get message ID
            msgid, data = data.split(None, 1)
            msgid = long(msgid)

            assert data.startswith('('), data
            data = data[1:]

        if data.endswith(')'):
            data = data[:-1]

        for name, item in FetchTokeniser().process_pairs(data):
            name = name.upper()

            if name == 'UID':
                # Using UID's, override the message ID
                msgid = long(item)

            else:
                if isinstance(item, Literal):
                    #assert len(data) == item.length
                    arg = literal_data
                else:
                    arg = item

                # Call handler function based on the response type
                methname = 'do_'+name.upper().replace('.', '_')
                meth = getattr(self, methname, self.do_default)
                out[name] = meth(arg)

        return msgid, out

    def do_INTERNALDATE(self, arg):
        """Process an INTERNALDATE response

        @param arg: A quoted IMAP INTERNALDATE string
            (eg. " 9-Feb-2007 17:08:08 +0000")
        @return: datetime.datetime instance for the given time (in UTC)
        """
        arg = 'INTERNALDATE "%s"' % arg
        mo = imaplib.InternalDate.match(arg)
        if not mo:
            raise ValueError("couldn't parse date %r" % arg)

        zoneh = int(mo.group('zoneh'))
        zonem = (zoneh * 60) + int(mo.group('zonem'))
        if mo.group('zonen') == '-':
            zonem = -zonem
        tz = FixedOffset(zonem)

        year = int(mo.group('year'))
        mon = imaplib.Mon2num[mo.group('mon')]
        day = int(mo.group('day'))
        hour = int(mo.group('hour'))
        min = int(mo.group('min'))
        sec = int(mo.group('sec'))

        dt = datetime.datetime(year, mon, day, hour, min, sec, 0, tz)

        # Normalise to host system's timezone
        return dt.astimezone(FixedOffset.for_system()).replace(tzinfo=None)


    def do_default(self, arg):
        return arg


class FetchTokeniser(object):
    """
    General response tokenizer and converter
    """

    QUOTED_STRING = '(?:".*?")'
    PAREN_LIST = '(?:\(.*?\))'

    PAIR_RE = re.compile((
        '([\w\.]+(?:\[[^\]]+\]+)?)\s+' +    # name (matches "FOO", "FOO.BAR" & "BODY[SECTION STUFF]")
        '((?:\d+)' +                        # bare integer
        '|(?:{\d+?})' +                     # IMAP literal
        '|' + QUOTED_STRING +
        '|' + PAREN_LIST +
        ')\s*'))

    DATA_RE = re.compile((
        '(' + QUOTED_STRING +
        '|' + PAREN_LIST +
        '|(?:\S+)' +            # word
        ')\s*'))

    def process_pairs(self, s):
        """Break up and convert a string of FETCH response pairs

        @param s: FETCH response string eg. "FOO 12 BAH (1 abc def "foo bar")"
        @return: Tokenised and converted input return as (name, data) pairs.
        """
        out = []
        for m in strict_finditer(self.PAIR_RE, s):
            name, data = m.groups()
            out.append((name, self.nativefy(data)))
        return out

    def process_list(self, s):
        """Break up and convert a string of data items

        @param s: FETCH response string eg. "(1 abc def "foo bar")"
        @return: A list of converted items.
        """
        if s == '':
            return []
        out = []
        for m in strict_finditer(self.DATA_RE, s):
            out.append(self.nativefy(m.group(1)))
        return out

    def nativefy(self, s):
        if s.startswith('"'):
            return s[1:-1]      # Debracket
        elif s.startswith('{'):
            return Literal(long(s[1:-1]))
        elif s.startswith('('):
            return self.process_list(s[1:-1])
        elif s.isdigit():
            return long(s)
        elif s.upper() == 'NIL':
            return None
        else:
            return s


class Literal(object):
    """
    Simple class to represent a literal token in the fetch response
    (eg. "{21}")
    """

    def __init__(self, length):
        self.length = length

    def __eq__(self, other):
        return self.length == other.length

    def __str__(self):
        return '{%d}' % self.length


def strict_finditer(regex, s):
    """Like re.finditer except the regex must match from exactly where the
    previous match ended and all the entire input must be matched.
    """
    i = 0
    matched = False
    while 1:
        match = regex.match(s[i:])
        if match:
            matched = True
            i += match.end()
            yield match
        else:
            if (len(s) > 0 and not matched) or i < len(s):
                raise ValueError("failed to match all of input. "
                        "%r remains" % s[i:])
            else:
                return


def messages_to_str(messages):
    """Convert a sequence of messages ids or a single message id into an
    message ID list for use with IMAP commands.

    @param messages: A sequence of messages IDs or a single message ID.
        (eg. [1,4,5,7,8])
    @return: Message list string (eg. "1,4,5,6,8")
    """
    if isinstance(messages, (str, int, long)):
        messages = (messages,)
    elif not isinstance(messages, (tuple, list)):
        raise ValueError('invalid message list: %r' % messages)
    return ','.join([str(m) for m in messages])


def seq_to_parenlist(flags):
    """Convert a sequence into parenthised list for use with IMAP commands

    @param flags: Sequence to process (eg. ['abc', 'def'])
    @return: IMAP parenthenised list (eg. '(abc def)')
    """
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)


def datetime_to_imap(dt):
    """Convert a datetime instance to a IMAP datetime string

    If timezone information is missing the current system timezone is used.
    """
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=FixedOffset.for_system())

    return dt.strftime("%d-%b-%Y %H:%M:%S %z")
    


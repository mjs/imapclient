# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import re
import imaplib
import shlex
import datetime

#XXX: fix fetch bug

#TODO: finish up livetest.py for stable-ish functionality
#   folder exists
#   select
#   basic search
#   fetch
#   flags stuff

#XXX's

#TODO: flags and message parts constants
#TODO: simple README: 
#   - quick intro
#   - compare imaplib and imapclient
#   - install and test instructions
#   - defer to example, doctstrings etc
# example.py
#TODO: add COPYING
#TODO: copyright 
#----- initial release -----

# Common flags
F_DELETED = r'\Deleted'

class IMAPClient:
    '''
    A high level, friendly IMAP client interface.

    Unlike imaplib, arguments and returns values are Pythonic and readily
    usable. Exceptions are raised when problems occur (no error checking of
    return values is required).

    Message unique identifiers (UID) can be used with any call. The use_uid
    argument to the constructor and the use_uid attribute control whether or
    not UIDs are used.

    '''
    #XXX: document how messages and flags are accepted

    # Map error classes across from imaplib
    error = imaplib.IMAP4.error
    abort = imaplib.IMAP4.abort
    readonly = imaplib.IMAP4.readonly

    re_sep = re.compile('^\(\("[^"]*" "([^"]+)"\)\)')
    re_folder = re.compile('\([^)]*\) "[^"]+" "([^"]+)"')

    def __init__(self, host, port=143, use_uid=True):
        '''Initialise object instance and connect to the remote IMAP server.

        @param host: The IMAP server address/hostname to connect to.
        @param port: The port number to use (default is 143).
        @param use_uid: Should message UIDs be used (default is True).
        '''
        self._imap = imaplib.IMAP4(host, port)
        self.use_uid = use_uid

    def login(self, username, password):
        '''Perform a simple login
        '''
        typ, data = self._imap.login(username, password)
        self._checkok('login', typ, data)
        return data[0]

    def get_folder_delimiter(self):
        '''Determine the folder separator used by the IMAP server.

        @return: The folder separator.
        @rtype: string
        '''
        typ, data = self._imap.namespace()
        self._checkok('namespace', typ, data)

        match = self.re_sep.match(data[0])
        if match:
            return match.group(1)
        else:
            raise self.error('could not determine folder separator')

    def list_folders(self, directory="", pattern="*"):
        '''Get a listing of folders on the server.

        The default behaviour (no args) will list all folders for the logged in
        user.

        @param directory: The base directory to look for folders from.
        @param pattern: A pattern to match against folder names. Only folder
            names matching this pattern will be returned. Wildcards accepted.
        @return: A list of folder names.
        '''
        typ, data = self._imap.list(directory, pattern)
        self._checkok('list', typ, data)

        folders = []
        for line in data:
            m = self.re_folder.match(line)
            if m:
                folders.append(m.group(1))

        return folders

    def select_folder(self, folder):
        #XXX: readonly option
        '''Select the current folder on the server. Future calls to methods
        such as search and fetch will act on the selected folder.

        @param folder: The folder name.
        @return: Number of messages in the folder.
        @rtype: long int
        '''
        typ, data = self._imap.select(folder)
        self._checkok('select', typ, data)
        return long(data[0])

    def close_folder(self):
        '''Close the currently selected folder.

        @return: Server response.
        '''
        typ, data = self._imap.close()
        self._checkok('close', typ, data)
        return data[0]

    def create_folder(self, folder):
        '''Create a new folder on the server.

        @param folder: The folder name.
        @return: Server response.
        '''
        typ, data = self._imap.create(folder)
        self._checkok('create', typ, data)
        return data[0]

    def folder_exists(self, folder):
        '''Determine if a folder exists on the server.

        @param folder: Full folder name to look for.
        @return: True if the folder exists. False otherwise.
        '''
        typ, data = self._imap.list('', folder)
        self._checkok('list', typ, data)
        return len(data) == 1 and data[0] != None

    def search(self, criteria='ALL', charset=None):
        #XXX: Pythonic criteria specification
        if isinstance(criteria, basestring):
            criteria = (criteria,)

        if self.use_uid:
            if charset is None:
                typ, data = self._imap.uid('SEARCH', *criteria)
            else:
                typ, data = self._imap.uid('SEARCH', 'CHARSET', charset,
                    *criteria)
        else:
            typ, data = self._imap.search(charset, *criteria)

        self._checkok('search', typ, data)

        return [ long(i) for i in data[0].split() ]

    def delete_messages(self, messages):
        '''Short-hand method for deleting one or more messages

        @param messages: Message IDs to mark for deletion.
        @return: Same as for set_flags.
        '''
        return self.add_flags(messages, F_DELETED)

    def add_flags(self, messages, flags):
        #XXX: doc
        return self._store('+FLAGS', messages, flags)

    def remove_flags(self, messages, flags):
        #XXX: doc
        return self._store('-FLAGS', messages, flags)

    def set_flags(self, messages, flags):
        #XXX: doc
        return self._store('FLAGS', messages, flags)

    def fetch(self, messages, parts):
        '''Retrieve selected data items for one or more messages.

        @param messages: Message IDs to fetch.
        @param parts: A sequence of data items to retrieve.
        @return: A dictionary indexed by message number. Each item is itself a
            dictionary, one item per field.
        '''
        msg_list = messages_to_str(messages)

        #XXX: parts handling is broken, needs to be turned into a parenthenised list first
        parts = [ p.upper() for p in parts ]

        #XXX: abstract out UID handling if possible
        if self.use_uid:
            typ, data = self._imap.uid('FETCH', msg_list, *parts)
        else:
            typ, data = self._imap.fetch(msg_list, *parts)
        self._checkok('fetch', typ, data)

        parser = FetchParser()
        return parser(data)

    def append(self, folder, msg, flags=(), msg_time=None):
        '''Append a message to a folder

        @param folder: Folder name to append to.
        @param msg: Message body as a string.
        @param flags: Sequnce of message flags to set. If not specified no
            flags will be set.
        @param msg_time: Optional date and time to set for the message. The
            server will set a time if it isn't specified.
        @type msg_time: datetime.datetime
        @return: The append response returned by the server.
        @rtype: str
        '''
        if msg_time:
            time_val = msg_time.timetuple()
        else:
            time_val = None

        flags_list = flags_to_str(flags)

        typ, data = self._imap.append(folder, flags_list, time_val, msg)
        self._checkok('append', typ, data)

        return data[0]

    def expunge(self):
        typ, data = self._imap.expunge()
        self._checkok('expunge', typ, data)
        #TODO: expunge response

    def getacl(self, folder):
        typ, data = self._imap.getacl(folder)
        self._checkok('getacl', typ, data)

        parts = shlex.split(data[0])
        parts = parts[1:]       # First item is folder name

        out = []
        for i in xrange(0, len(parts), 2):
            out.append((parts[i], parts[i+1]))
        return out

    def setacl(self, folder, who, what):
        '''Set an ACL for a folder

        @param folder: Folder name to set an ACL for.
        @param who: User or group ID for the ACL.
        @param what: A string describing the ACL. Set to '' to remove an ACL.
        @return: Server response string.
        '''
        typ, data = self._imap.setacl(folder, who, what)
        self._checkok('setacl', typ, data)
        return data[0]

    def _checkok(self, command, typ, data):
        '''Check command responses for errors.

        Will raise IMAPClient.error if a command failed.
        '''
        if typ != 'OK':
            raise self.error('%s failed: %r' % (command, data[0]))

    def _store(self, cmd, messages, flags):
        '''Worker functions for flag manipulation functions

        @param cmd: STORE command to use (eg. '+FLAGS')
        @param messages: Sequence of message IDs
        @param flags: Sequence of flags to set.
        @return: Parsed fetch response (dictionary)
        '''
        if not messages:
            return {}

        msg_list = messages_to_str(messages)
        flag_list = flags_to_str(flags)

        if self.use_uid:
            typ, data = self._imap.uid('STORE', msg_list, '+FLAGS', flag_list)
        else:
            typ, data = self.store(msg_list, cmd, flag_list)
        self._checkok('store', typ, data)

        return FetchParser()(data)

class FetchParser(object):
    #XXX: quick doc

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
        if data[0].isdigit():
            # Get message ID
            msgid, data = data.split(None, 1)
            msgid = long(msgid)

            assert data.startswith('('), data
            data = data[1:]
            if data.endswith(')'):
                data = data[:-1]

        else:
            msgid = None

        for name, item in FetchTokeniser().process_pairs(data):
            name = name.upper()

            if name == 'UID':
                # Using UID's, override the message ID
                msgid = long(item)

            else:
                if isinstance(item, Literal):
                    #assert len(data) == item.length    #XXX
                    arg = literal_data
                else:
                    arg = item

                # Call handler function based on the response type
                methname = 'do_'+name.upper().replace('.', '_')
                meth = getattr(self, methname, self.do_default)
                out[name] = meth(arg)

        return msgid, out

    def do_INTERNALDATE(self, arg):
        '''Process an INTERNALDATE response

        @param arg: A quoted IMAP INTERNALDATE string
            (eg. " 9-Feb-2007 17:08:08 +0000")
        @return: datetime.datetime instance for the given time (in UTC)
        '''
        t = imaplib.Internaldate2tuple('INTERNALDATE "%s"' % arg)
        if t is None:
            return None
        else:
            return datetime.datetime(*t[:6])

    def do_default(self, arg):
        return arg

class FetchTokeniser(object):
    '''
    General response tokenizer and converter
    '''

    #XXX reuse expressions
    PAIR_RE = re.compile(
        '([\w\.]+)\s+'          # name
        '((?:\d+)'              # bare integer
        '|(?:".*?")'            # quoted string 
        '|(?:\(.*?\))'          # parenthensized list
        '|(?:{\d+?})'           # IMAP literal
        ')\s*')

    DATA_RE = re.compile(
        '((?:".*?")'            # quoted string 
        '|(?:\(.*?\))'          # parenthensized list
        '|(?:\S+)'              # word 
        ')\s*')

    def process_pairs(self, s):
        '''Break up and convert a string of FETCH response pairs

        @param s: FETCH response string eg. "FOO 12 BAH (1 abc def "foo bar")"
        @return: Tokenised and converted input return as (name, data) pairs.
        '''
        out = []
        for m in strict_finditer(self.PAIR_RE, s):
            name, data = m.groups()
            out.append((name, self._convert(data)))
        return out

    def process_list(self, s):
        '''Break up and convert a string of data items

        @param s: FETCH response string eg. "(1 abc def "foo bar")"
        @return: A list of converted items.
        '''
        if s == '':
            return []
        out = []
        for m in strict_finditer(self.DATA_RE, s):
            out.append(self._convert(m.group(1)))
        return out

    def _convert(self, s):
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
    '''
    Simple class to represent a literal token in the fetch response
    (eg. "{21}")
    '''

    def __init__(self, length):
        self.length = length

    def __eq__(self, other):
        return self.length == other.length

    def __str__(self):
        return '{%d}' % self.length

def strict_finditer(regex, s):
    '''Like re.finditer except the regex must match from exactly where the
    previous match ended and all the entire input must be matched.
    '''
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
    '''Convert a sequence of messages ids or a single message id into an
    message ID list for use with IMAP commands.

    @param messages: A sequence of messages IDs or a single message ID.
        (eg. [1,4,5,7,8])
    @return: Message list string (eg. "1,4,5,6,8")
    '''
    if isinstance(messages, (str, int, long)):
        messages = (messages,)
    elif not isinstance(messages, (tuple, list)):
        raise ValueError('invalid message list: %r' % messages)
    return ','.join([str(m) for m in messages])

def flags_to_str(flags):
    '''Convert a sequence of flags or a single flag into a flag list for use
    with IMAP commands.

    @param flags: Flag sequence to process (eg. [F_DELETED])
    @return: Flags list string (eg. r'(\Deleted))
    '''
    if isinstance(flags, str):
        flags = (flags,)
    elif not isinstance(flags, (tuple, list)):
        raise ValueError('invalid flags list: %r' % flags)
    return '(%s)' % ' '.join(flags)



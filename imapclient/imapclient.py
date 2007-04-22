
import re
import imaplib
import shlex

#TODO: more docs
#TODO: transparent "&" escaping
#TODO: support for streaming messages in and out (generators or file-like
# objects)
#TODO: SSL support
#TODO: full message fetch support
#TODO: more complex authentication methods
#TODO: store
#TODO: better namespace support

class HighIMAP4:
    '''
    A higher level, friendlier wrapper around imaplib.IMAP4.

    Unlike imaplib, arguments and returns values are Pythonic and readily
    usable. Exceptions are raised when problems occur (no error checking of
    return values is required).

    Message unique identifiers (UID) can be used with any call. The use_uid
    argument to the constructor and the use_uid attribute control whether or
    not UIDs are used.

    Pronounced "hi-map-four"
    '''

    # Map error classes across from imaplib
    error = imaplib.IMAP4.error
    abort = imaplib.IMAP4.abort
    readonly = imaplib.IMAP4.readonly

    re_sep = re.compile('^\(\("[^"]*" "([^"]+)"\)\)')
    re_folder = re.compile('\([^)]*\) "[^"]+" "([^"]+)"')
    re_append = re.compile('\[APPENDUID (\d+) (\d+)\]')

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
    
    def get_separator(self):
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

    def list(self, directory="", pattern="*"):
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

    def select(self, folder):
        '''Select a folder on the server to access

        @param folder: The folder name.
        @return: Number of messages in the folder.
        @rtype: long int
        '''
        typ, data = self._imap.select(folder)
        self._checkok('select', typ, data)
        return long(data[0])
  
    def close(self):
        '''Close the currently selected folder.

        @return: Server response.
        '''
        typ, data = self._imap.close()
        self._checkok('close', typ, data)
        return data[0]
        
    def create(self, folder):
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

    def search(self, criteria, charset=None):
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

        return [ int(i) for i in data[0].split() ]

    def fetch(self, msgids, parts):
        #XXX need some proper parsing here, shlex might be enough
        raise NotImplementedError

        ids = ','.join([str(i) for i in msgids])

        if self.use_uid:
            typ, data = self._imap.uid('FETCH', ids, parts) 
        else:
            typ, data = self._imap.fetch(ids, parts) 
        self._checkok('fetch', typ, data)

        out = {}
        last_msgid = None

        for resp in data:
            if isinstance(resp, tuple):
                header, literal = resp
            else:
                header = resp

            msgid = header.split(' ', 1)
            if not msgid:
                if last_msgid is None:
                    raise self.error('unparsable FETCH response')
                else:
                    msgid = last_msgid
            else:
                msgid = int(msgid)
                out[msgid] = {}

    def simplefetch(self, msgids):
        '''Will be superceeded by fetch() once complete
        '''
        out = {}
        ids = ','.join([str(i) for i in msgids])

        parts = '(FLAGS RFC822)'
        if self.use_uid:
            typ, data = self._imap.uid('FETCH', ids, parts) 
        else:
            typ, data = self._imap.fetch(ids, parts) 
        self._checkok('fetch', typ, data)

        if self.use_uid:
            header_regex = '\d+ \(FLAGS \((?P<flags>[^)]+)\) UID (?P<id>\d+)'
        else:
            header_regex = '(?P<id>\d+) \(FLAGS \((?P<flags>[^)]+)\)'
        re_header = re.compile(header_regex)

        for item in data:
            if item == ')':
                continue

            header, body = item
            match = re_header.match(header)
            if not match:
                raise self.error("couldn't match %r" % header)
    
            msgid = int(match.group('id'))
            flags = match.group('flags').split()
            out[msgid] = (flags, body)
       
        return out

    def append(self, folder, msg, flags=None, msg_time=None):
        '''Append a message to a mailbox

        @param folder: Folder name to append to.
        @param msg: Message body as a string.
        @param flags: Message flags as a seq of strings. Default is to set no
            flags.
        @param msg_time: Epoch time to use for the message (defaults to now)
        @return: (Append epoch time, message UID)
        '''
        if flags is None:
            flags = '()'
        else:
            flags = "(%s)" % (" ".join(flags))

        typ, data = self._imap.append(folder, flags, msg_time, msg)
        self._checkok('append', typ, data)
    
        # Process response
        m = self.re_append.match(data[0])
        if m:
            return long(m.group(1)), long(m.group(2))
        else:
            raise self.error("couldn't process APPEND response: %r" % data[0])

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

        Will raise HighIMAP4.error if a command failed.
        '''
        if typ != 'OK':
            raise self.error('%s failed: %r' % (command, data[0]))


class ResponseParser:

    def __init__(self, data):
        self._data = data

    def parse(self):

        out = {}

        while self._data:
            item = self._data.pop(0)

            if isinstance(item, tuple):


    

            msgid, remainder = 


def test():
    data = ['1 (ENVELOPE (NIL "test" NIL NIL NIL NIL NIL NIL NIL NIL))']

    p = ResponseParser(









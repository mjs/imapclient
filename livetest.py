#!/usr/bin/python

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

# Copyright 2009 Menno Smits

import sys
from datetime import datetime
from optparse import OptionParser
import imapclient

#TODO: more fetch() testing

def test_capabilities(server):
    caps = server.capabilities()
    assert isinstance(caps, tuple)
    assert len(caps) > 1
    for cap in caps:
        assert server.has_capability(cap)
    assert not server.has_capability('WONT EXIST')

def test_list_folders(server):
    folders = server.list_folders()
    assert len(folders) > 0, 'No folders visible on server'
    assert 'INBOX' in [f.upper() for f in folders], 'INBOX not returned'
    #TODO: test wildcards
    #TODO: test other folders...


def test_select_and_close(server):
    num_msgs = server.select_folder('INBOX')
    assert isinstance(num_msgs, long)
    assert num_msgs >= 0
    server.close_folder()


def test_subscriptions(server):
    # Start with a clean slate
    clear_folders(server)

    for folder in server.list_sub_folders():
        server.unsubscribe_folder(folder)

    test_folders = ['foobar',
                    'stuff & things',
                    u'test & \u2622']

    for folder in test_folders:
        server.create_folder(folder)

    all_folders = sorted(server.list_folders())

    for folder in all_folders:
        server.subscribe_folder(folder)

    assert all_folders == sorted(server.list_sub_folders())

    for folder in all_folders:
        server.unsubscribe_folder(folder)
    assert server.list_sub_folders() == []

    assert_raises(imapclient.IMAPClient.Error,
                  server.subscribe_folder,
                  'this folder is not likely to exist')


def test_folders(server):
    '''Test folder manipulation
    '''
    clear_folders(server)

    assert server.folder_exists('INBOX')
    assert not server.folder_exists('this is very unlikely to exist')

    test_folders = ['foobar',
                    'stuff & things',
                    u'test & \u2622']

    for folder in test_folders:
        assert not server.folder_exists(folder)

        server.create_folder(folder)

        assert server.folder_exists(folder)
        assert folder in server.list_folders()

        server.select_folder(folder)
        server.close_folder()

        server.delete_folder(folder)
        assert not server.folder_exists(folder)


def test_status(server):
    clear_folders(server)

    # Default behaviour should return 5 keys
    assert len(server.folder_status('INBOX')) == 5

    new_folder = u'test \u2622'
    server.create_folder(new_folder)
    try:
        status = server.folder_status(new_folder)
        assert status['MESSAGES'] == 0
        assert status['RECENT'] == 0
        assert status['UNSEEN'] == 0

        # Add a message to the folder, it should show up now.
        body = 'Subject: something\r\n\r\nFoo'
        server.append(new_folder, body)

        status = server.folder_status(new_folder)
        assert status['MESSAGES'] == 1
        assert status['RECENT'] == 1
        assert status['UNSEEN'] == 1

    finally:
        server.delete_folder(new_folder)

def test_append(server):
    '''Test that appending a message works correctly
    '''
    clear_folder(server, 'INBOX')

    # Message time microseconds are set to 0 because the server will return
    # time with only seconds precision.
    msg_time = datetime.now().replace(microsecond=0)

    # Append message
    body = 'Subject: something\r\n\r\nFoo\r\n'
    resp = server.append('INBOX', body, ('abc', 'def'), msg_time)
    assert isinstance(resp, str)

    # Retrieve the just added message and check that all looks well
    num_msgs = server.select_folder('INBOX')
    assert num_msgs == 1

    resp = server.fetch(
            server.search()[0],
            ('RFC822', 'FLAGS', 'INTERNALDATE')
            )

    assert len(resp) == 1
    msginfo = resp.values()[0]

    # Time should match the time we specified
    returned_msg_time = msginfo['INTERNALDATE']
    assert returned_msg_time.tzinfo is None
    assert returned_msg_time == msg_time

    # Flags should be the same
    assert 'abc' in msginfo['FLAGS']
    assert 'def' in msginfo['FLAGS']

    # Message body should match
    assert msginfo['RFC822'] == body


def test_flags(server):
    '''Test flag manipulations
    '''
    server.select_folder('INBOX')
    msgid = server.search()[0]

    def _flagtest(func, args, expected_flags):
        answer = func(msgid, *args)

        assert answer.has_key(msgid)
        answer_flags = answer[msgid]

        # This is required because the order of the returned flags isn't
        # guaranteed
        answer_flags.sort()
        expected_flags.sort()

        assert answer_flags == expected_flags

    base_flags = ['abc', 'def']
    _flagtest(server.set_flags, [base_flags], base_flags)
    _flagtest(server.get_flags, [], base_flags)
    _flagtest(server.add_flags, ['boo'], base_flags + ['boo'])
    _flagtest(server.remove_flags, ['boo'], base_flags)

def test_search(server):
    clear_folder(server, 'INBOX')

    # Add some test messages
    msg_tmpl = 'Subject: %s\r\n\r\nBody'
    subjects = ('a', 'b', 'c')
    for subject in subjects:
        msg = msg_tmpl % subject
        if subject == 'c':
            flags = (imapclient.DELETED,)
        else:
            flags = ()
        server.append('INBOX', msg, flags)

    messages_all = server.search('ALL')
    assert len(messages_all) == len(subjects)   # Check we see all messages
    assert server.search() == messages_all      # Check default

    # Single criteria
    assert len(server.search('DELETED')) == 1
    assert len(server.search('NOT DELETED')) == len(subjects) - 1
    assert server.search('NOT DELETED') == server.search(['NOT DELETED'])

    # Multiple criteria
    assert len(server.search(['NOT DELETED', 'SMALLER 100'])) == \
            len(subjects) - 1
    assert len(server.search(['NOT DELETED', 'SUBJECT "a"'])) == 1
    assert len(server.search(['NOT DELETED', 'SUBJECT "c"'])) == 0


def assert_raises(exception_class, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception_class:
        return
    except Exception, e:
        raise AssertionError('expected %r but got %s instead' % (exception_class, type(e)))
    raise AssertionError('no exception raised, expected %r' % exception_class)


def runtests(server):
    '''Run a sequence of tests against the IMAP server
    '''
    # The ordering of these tests is important
    test_capabilities(server)
    test_list_folders(server)
    test_select_and_close(server)
    test_subscriptions(server)
    test_folders(server)
    test_status(server)
    test_append(server)
    test_flags(server)
    test_search(server)

def clear_folder(server, folder):
    server.select_folder(folder)
    server.delete_messages(server.search())
    server.expunge()


def clear_folders(server):
    server.folder_encode = False
    for folder in server.list_folders():
        if folder.upper() != 'INBOX':
            server.delete_folder(folder)
    server.folder_encode = True

def command_line():
    p = OptionParser()
    p.add_option('-H', '--host', dest='host', action='store',
                 help='IMAP host connect to')
    p.add_option('-P', '--port', dest='port', action='store',
                 default=143, help='IMAP port to use (default is 143)')
    p.add_option('-s', '--ssl', dest='ssl', action='store_true', default=False,
                 help='Use SSL connection')
    p.add_option('-u', '--username', dest='username', action='store',
                 help='Username to login with')
    p.add_option('-p', '--password', dest='password', action='store',
                 help='Password to login with')
    p.add_option('', '--clobber', dest='clobber', action='store_true',
                 default=False, help='These tests are destructive. Use this '
                 'option to bypass the confirmation prompt.')
    p.add_option('', '--debug', dest='debug', action='store_true',
                 default=False,
                 help='Instead of running tests, set up the connection & drop into pdb')
    p.add_option('', '--interact', dest='interact', action='store_true',
                 default=False,
                 help='Instead of running tests, set up the connection & drop into a shell')

    options, args = p.parse_args()

    if args:
        p.error('unexpected arguments %s' % ' '.join(args))

    for opt_name in ('host', 'username', 'password'):
        if not getattr(options, opt_name):
            p.error('%s must be specified' % opt_name)

    return options


def user_confirm():
    print """\
WARNING: These tests are destructive.
Email in the specified account will be lost!
"""
    r = raw_input('Enter "yes" to confirm this is ok: ')
    if r.lower() != 'yes':
        print "Aborting tests."
        sys.exit()


def main():
    options = command_line()

    if not options.clobber:
        user_confirm()

    # Test with use_uid on and off
    for use_uid in (True, False):
        print '-'*60
        print "Testing with use_uid=%r, ssl=%r..." % (use_uid, options.ssl)
        print '-'*60
        server = imapclient.IMAPClient(options.host, use_uid=use_uid, ssl=options.ssl)
        server.login(options.username, options.password)
        if options.debug:
            import pdb
            pdb.set_trace()
        elif options.interact:
            import code
            code.interact(local=locals())
        else:
            runtests(server)
            print 'SUCCESS'

if __name__ == '__main__':
    main()


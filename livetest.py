#!/usr/bin/python

# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses


import sys
from datetime import datetime
from optparse import OptionParser
import imapclient


SIMPLE_MESSAGE = 'Subject: something\r\n\r\nFoo\r\n'

MULTIPART_MESSAGE = """\
From: Bob Smith <bob@smith.com>
To: Some One <some@one.com>
Date: Tue, 16 Mar 2010 16:45:32 +0000
Message-ID: <1A472770E042064698CB5ADC83A12ACD39455AAB@ABC>
MIME-Version: 1.0
Subject: A multipart message
Content-Type: multipart/mixed; boundary="===============1534046211=="

--===============1534046211==
Content-Type: text/html; charset="us-ascii"
Content-Transfer-Encoding: quoted-printable

<html><body>
Here is the first part.
</body></html>

--===============1534046211==
Content-Type: text/plain; charset="us-ascii"
Content-Transfer-Encoding: 7bit

Here is the second part.

--===============1534046211==--
""".replace('\n', '\r\n')

def is_gmail(client):
    return client._imap.host == 'imap.gmail.com'

def extract_folder_names(dat):
    ret = []
    for _, _, folder_name in dat:
        # gmail's "special" folders start with '['
        if not folder_name.startswith('['):
            ret.append(folder_name)
    return ret

def test_capabilities(client):
    caps = client.capabilities()
    assert isinstance(caps, tuple)
    assert len(caps) > 1
    for cap in caps:
        assert client.has_capability(cap)
    assert not client.has_capability('WONT EXIST')

def test_list_folders(client):
    clear_folders(client)
    some_folders = ['simple', r'foo\bar', r'test"folder"']
    for name in some_folders:
        client.create_folder(name)

    folders = extract_folder_names(client.list_folders())
    assert len(folders) > 0, 'No folders visible on server'
    assert 'INBOX' in [f.upper() for f in folders], 'INBOX not returned'

    for name in some_folders:
        assert name in folders
    #TODO: test wildcards

    caps = client.capabilities()
    if is_gmail(client):
        assert "XLIST" in caps, caps
    if 'XLIST' in caps:
        info = client.xlist_folders()
        folders = extract_folder_names(info)
        assert len(folders) > 0, 'No folders visible on server'
        for flags, _, _  in info:
            if '\\INBOX' in [flag.upper() for flag in flags]:
                break
        else:
            raise AssertionError('INBOX not returned', info)

    for name in some_folders:
        assert name in folders
        

def test_select_and_close(client):
    resp = client.select_folder('INBOX')
    assert isinstance(resp['EXISTS'], int)
    assert resp['EXISTS'] > 0
    assert isinstance(resp['RECENT'], int)
    assert isinstance(resp['FLAGS'], tuple)
    assert len(resp['FLAGS']) > 1
    client.close_folder()


def test_subscriptions(client):
    # Start with a clean slate
    clear_folders(client)

    for folder in extract_folder_names(client.list_sub_folders()):
        client.unsubscribe_folder(folder)

    test_folders = ['foobar',
                    'stuff & things',
                    u'test & \u2622']

    for folder in test_folders:
        client.create_folder(folder)

    all_folders = sorted(extract_folder_names(client.list_folders()))

    for folder in all_folders:
        client.subscribe_folder(folder)

    assert all_folders == sorted(extract_folder_names(client.list_sub_folders()))

    for folder in all_folders:
        client.unsubscribe_folder(folder)
    assert extract_folder_names(client.list_sub_folders()) == []

    assert_raises(imapclient.IMAPClient.Error,
                  client.subscribe_folder,
                  'this folder is not likely to exist')


def test_folders(client):
    '''Test folder manipulation
    '''
    clear_folders(client)

    assert client.folder_exists('INBOX')
    assert not client.folder_exists('this is very unlikely to exist')

    test_folders = ['foobar',
                    'stuff & things',
                    u'test & \u2622']

    for folder in test_folders:
        assert not client.folder_exists(folder)

        client.create_folder(folder)

        assert client.folder_exists(folder)
        assert folder in extract_folder_names(client.list_folders())

        client.select_folder(folder)
        client.close_folder()

        client.delete_folder(folder)
        assert not client.folder_exists(folder)


def test_status(client):
    clear_folders(client)

    # Default behaviour should return 5 keys
    assert len(client.folder_status('INBOX')) == 5

    new_folder = u'test \u2622'
    client.create_folder(new_folder)
    try:
        status = client.folder_status(new_folder)
        assert status['MESSAGES'] == 0, status
        assert status['RECENT'] == 0, status
        assert status['UNSEEN'] == 0, status

        # Add a message to the folder, it should show up now.
        client.append(new_folder, SIMPLE_MESSAGE)

        status = client.folder_status(new_folder)
        assert status['MESSAGES'] == 1, status
        if not is_gmail(client):
            assert status['RECENT'] == 1, status
        assert status['UNSEEN'] == 1, status

    finally:
        client.delete_folder(new_folder)

def test_append(client):
    '''Test that appending a message works correctly
    '''
    clear_folder(client, 'INBOX')

    # Message time microseconds are set to 0 because the server will return
    # time with only seconds precision.
    msg_time = datetime.now().replace(microsecond=0)

    # Append message
    resp = client.append('INBOX', SIMPLE_MESSAGE, ('abc', 'def'), msg_time)
    assert isinstance(resp, str)

    # Retrieve the just added message and check that all looks well
    assert client.select_folder('INBOX')['EXISTS'] == 1

    resp = client.fetch(
            client.search()[0],
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
    assert msginfo['RFC822'] == SIMPLE_MESSAGE


def test_flags(client):
    '''Test flag manipulations
    '''
    client.select_folder('INBOX')
    msgid = client.search()[0]

    def _flagtest(func, args, expected_flags):
        answer = func(msgid, *args)

        assert answer.has_key(msgid)
        answer_flags = list(answer[msgid])

        # This is required because the order of the returned flags isn't
        # guaranteed
        answer_flags.sort()
        expected_flags.sort()

        assert answer_flags == expected_flags

    base_flags = ['abc', 'def']
    _flagtest(client.set_flags, [base_flags], base_flags)
    _flagtest(client.get_flags, [], base_flags)
    _flagtest(client.add_flags, ['boo'], base_flags + ['boo'])
    _flagtest(client.remove_flags, ['boo'], base_flags)

def test_search(client):
    clear_folder(client, 'INBOX')

    # Add some test messages
    msg_tmpl = 'Subject: %s\r\n\r\nBody'
    subjects = ('a', 'b', 'c')
    for subject in subjects:
        msg = msg_tmpl % subject
        if subject == 'c':
            flags = (imapclient.DELETED,)
        else:
            flags = ()
        client.append('INBOX', msg, flags)

    messages_all = client.search('ALL')
    if is_gmail(client):
        # gmail seems to never return deleted items.
        assert len(messages_all) == len(subjects)-1   # Check we see all messages
    else:
        assert len(messages_all) == len(subjects)   # Check we see all messages
    assert client.search() == messages_all      # Check default

    # Single criteria
    if not is_gmail(client):
        assert len(client.search('DELETED')) == 1
        assert len(client.search('NOT DELETED')) == len(subjects) - 1
    assert client.search('NOT DELETED') == client.search(['NOT DELETED'])

    # Multiple criteria
    assert len(client.search(['NOT DELETED', 'SMALLER 100'])) == \
            len(subjects) - 1
    assert len(client.search(['NOT DELETED', 'SUBJECT "a"'])) == 1
    assert len(client.search(['NOT DELETED', 'SUBJECT "c"'])) == 0


def test_copy(client):
    clear_folders(client)
    clear_folder(client, 'INBOX')

    client.select_folder('INBOX')
    client.append('INBOX', SIMPLE_MESSAGE)
    client.create_folder('target')
    msg_id = client.search()[0]
    
    client.copy(msg_id, 'target')

    client.select_folder('target')
    msgs = client.search()
    assert len(msgs) == 1
    msg_id = msgs[0]
    assert 'something' in client.fetch(msg_id, ['RFC822'])[msg_id]['RFC822']


def test_fetch(client):
    clear_folder(client, 'INBOX')

    client.select_folder('INBOX')
    client.append('INBOX', MULTIPART_MESSAGE)

    fields = ['RFC822', 'FLAGS', 'INTERNALDATE', 'ENVELOPE']
    msg_id = client.search()[0]
    resp = client.fetch(msg_id, fields)

    assert len(resp) == 1
    msginfo = resp[msg_id]

    assert set(msginfo.keys()) == set(fields + ['SEQ'])
    assert msginfo['SEQ'] == 1
    assert msginfo['RFC822'] == MULTIPART_MESSAGE
    assert isinstance(msginfo['INTERNALDATE'], datetime)
    assert isinstance(msginfo['FLAGS'], tuple)
    assert msginfo['ENVELOPE'] == ('Tue, 16 Mar 2010 16:45:32 +0000',
                                   'A multipart message',
                                   (('Bob Smith', None, 'bob', 'smith.com'),),
                                   (('Bob Smith', None, 'bob', 'smith.com'),),
                                   (('Bob Smith', None, 'bob', 'smith.com'),),
                                   (('Some One', None, 'some', 'one.com'),),
                                   None, None, None,
                                   '<1A472770E042064698CB5ADC83A12ACD39455AAB@ABC>')
    

def assert_raises(exception_class, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exception_class:
        return
    except Exception, e:
        raise AssertionError('expected %r but got %s instead' % (exception_class, type(e)))
    raise AssertionError('no exception raised, expected %r' % exception_class)


def runtests(client):
    '''Run a sequence of tests against the IMAP server
    '''
    # The ordering of these tests is important (but shouldn't be!)
    test_capabilities(client)
    test_list_folders(client)
    test_select_and_close(client)
    test_subscriptions(client)
    test_folders(client)
    test_status(client)
    test_append(client)
    test_flags(client)
    test_search(client)
    test_fetch(client)
    test_copy(client)


def clear_folder(client, folder):
    client.select_folder(folder)
    client.delete_messages(client.search())
    client.expunge()


def clear_folders(client):
    client.folder_encode = False
    for folder in extract_folder_names(client.list_folders()):
        if folder.upper() != 'INBOX':
            client.delete_folder(folder)
    client.folder_encode = True

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
        client = imapclient.IMAPClient(options.host, use_uid=use_uid, ssl=options.ssl)
        client.login(options.username, options.password)
        if options.interact:
            import code
            code.interact('HAI! IMAPClient instance is "c"', local=dict(c=client))
            break
        else:
            runtests(client)
            print 'SUCCESS'

if __name__ == '__main__':
    main()


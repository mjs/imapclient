import highimap
import imaplib
from datetime import datetime

'''
Docs:

Must be used with an account that has an INBOX folder

Each test function (test_...) is standalone but may use assume other methods or
functions are working correctly.
'''

#XXX: test flags setting and checking
#XXX: test with and without UID
#XXX: integrate this into the main script?
#XXX: decorators to pretty up test output

def test_acls(server):
    '''Test 
    '''
    print server.getacl('INBOX')
    #XXX: test folder with spaces

def setup_environment(server):
    init_folder(server, 'some folder')
    init_folder(server, 'INBOX')

def init_folder(server, folder):
    if not server.folder_exists(folder):
        server.create_folder(folder)
    clear_folder(server, folder)

def clear_folder(server, folder):
    server.select_folder(folder)
    server.delete_messages(server.search())
    server.expunge()

def test_list_folders(server):
    folders = server.list_folders()
    assert len(folders) > 0, 'No folders visible on server'
    assert 'INBOX' in [f.upper() for f in folders], 'INBOX not returned'
    #XXX: test wildcards
    #XXX: test other folders...

def test_select_and_close(server):
    num_msgs = server.select_folder('INBOX')
    assert isinstance(num_msgs, long)
    assert num_msgs >= 0
    server.close_folder()

def test_folder_exists(server):
    assert server.folder_exists('INBOX')
    assert not server.folder_exists('this is very unlikely to exist')

def test_append(server):
    clear_folder(server, 'INBOX')

    # Append message
    msg_time = datetime.now()
    resp = server.append(
            'INBOX',
            'Subject: something\n\nFoo',
            ('abc',),
            msg_time,
            )
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

    #XXX: not setting INTERNALDATE response when using Dovecot
    assert msginfo['INTERNALDATE'] == msg_time
    assert msginfo['FLAGS'] == ('abc',)
    print msginfo['RFC822']

def runtest(server):
    #XXX: run all and report failures (decorator)
    test_list_folders(server)
    test_select_and_close(server)
    test_folder_exists(server)
    test_append(server)


def main():
    server = highimap.HighIMAP4('127.0.0.1')
    server.login('mailtest', 'foo')

    runtest(server)

    #setup_environment(server)

    #server.select_folder('INBOX')
    #id = server.search()[0]

    #print server.set_flags([id], ['boo', 'hoo'])
    #print server.fetch([id], ['FLAGS'])

if __name__ == '__main__':
    main()


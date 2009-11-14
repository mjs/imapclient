from pprint import pprint
from imapclient import IMAPClient

def main():
    i = IMAPClient('localhost')
    i.login('mailtest', 'foobar')
    i.select_folder('INBOX')
    msgs = i.search()
    print msgs
    i._imap.debug = 5
    pprint(i.altfetch(msgs[0], 'RFC822'))

if __name__ == '__main__':
    main()

from pprint import pprint
from imapclient import IMAPClient

def main():
    i = IMAPClient('localhost')
    i.login('mailtest', 'foobar')
    i.select_folder('INBOX')
    msgs = i.search()
    i._imap.debug = 5
    lines = i.altfetch(msgs[0], ['RFC822'])

    print lines[0]
    body = '\r\n'.join(lines[1:-1])
    body += '\r\n'
    print body
    print len(body)


if __name__ == '__main__':
    main()

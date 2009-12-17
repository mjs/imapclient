from pprint import pprint
from imapclient import IMAPClient
from imapclient.response_parser import parse_response

def main():
    i = IMAPClient('localhost')
    i.login('mailtest', 'foobar')
    i.select_folder('INBOX')
    msgs = i.search()
    i._imap.debug = 5
    lines = i.altfetch(msgs, ['ENVELOPE', 'BODYSTRUCTURE'])

    body = '\r\n'.join(lines)
    #body += '\r\n'

    for x in parse_response(body):
        print x

if __name__ == '__main__':
    main()

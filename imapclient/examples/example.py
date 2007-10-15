from imapclient import IMAPClient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'secret'

server = IMAPClient(HOST, use_uid=True)
server.login(USERNAME, PASSWORD)

number_msgs = server.select_folder('INBOX')
print '%d messages in INBOX' % number_msgs

messages = server.search(['NOT DELETED'])
print "%d messages that aren't deleted" % len(messages)

print
print "Messages:"
response = server.fetch(messages, ['FLAGS', 'RFC822.SIZE'])
for msgid, data in response.iteritems():
    print '   ID %d: %d bytes, flags=%s' % (
            msgid,
            data['RFC822.SIZE'],
            ','.join(data['FLAGS']))

# This example is a lot more interesting if you have an active client
# connected to the same IMAP account!

from __future__ import unicode_literals

from imapclient import IMAPClient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'password'
ssl = True

server = IMAPClient(HOST, use_uid=True, ssl=ssl)
server.login(USERNAME, PASSWORD)
server.select_folder('INBOX')

# Start IDLE mode
server.idle()

# Wait for up to 30 seconds for an IDLE response
responses = server.idle_check(timeout=30)
print(responses)

# Come out of IDLE mode
text, responses = server.idle_done()
print('IDLE done. Server said %r' % text)
print('Final responses: ', responses)

print(server.logout())

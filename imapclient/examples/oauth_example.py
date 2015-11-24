from __future__ import unicode_literals

from imapclient import IMAPClient

# Populate these with actual values
CONSUMER_KEY = '...'
CONSUMER_SECRET = '...'
OAUTH_TOKEN = '...'
OAUTH_TOKEN_SECRET = '...'

HOST = 'imap.host.com'
URL = "https://somedomain.com/someuser/imap/"
ssl = True

server = IMAPClient(HOST, use_uid=True, ssl=ssl)

resp = server.oauth_login(URL, OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                          CONSUMER_KEY, CONSUMER_SECRET)
print(resp)

select_info = server.select_folder('INBOX')
print(select_info)

server.logout()

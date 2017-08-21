from __future__ import unicode_literals

from imapclient import IMAPClient

# Populate these with actual values
OAUTH2_USER = '...'
OAUTH2_ACCESS_TOKEN = '...'

HOST = 'imap.host.com'
URL = "https://somedomain.com/someuser/imap/"
ssl = True

server = IMAPClient(HOST, use_uid=True, ssl=ssl)

resp = server.oauth2_login(URL, OAUTH2_USER, OAUTH2_ACCESS_TOKEN)
print(resp)

select_info = server.select_folder('INBOX')
print(select_info)

server.logout()

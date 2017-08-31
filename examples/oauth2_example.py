# Login using OAUTH2

from imapclient import IMAPClient

# Populate these with actual values
OAUTH2_USER = '...'
OAUTH2_ACCESS_TOKEN = '...'

HOST = 'imap.host.com'
URL = "https://somedomain.com/someuser/imap/"

with IMAPClient(HOST) as server:
    server.oauth2_login(URL, OAUTH2_USER, OAUTH2_ACCESS_TOKEN)
    # ...do something...

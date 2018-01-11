# Establish an encrypted connection to a server without checking its
# certificate. This setup is insecure, DO NOT USE to connect to servers
# over the Internet.

import ssl

from imapclient import IMAPClient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'secret'

ssl_context = ssl.create_default_context()

# don't check if certificate hostname doesn't match target hostname
ssl_context.check_hostname = False

# don't check if the certificate is trusted by a certificate authority
ssl_context.verify_mode = ssl.CERT_NONE

with IMAPClient(HOST, ssl_context=ssl_context) as server:
    server.login(USERNAME, PASSWORD)
    # ...do something...

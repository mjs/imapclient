# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses
#
# Establish a secure connection to a server that does not have a certificate
# signed by a trusted authority.

import ssl

from imapclient import IMAPClient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'secret'

ssl_context = ssl.create_default_context(cafile="/path/to/cacert.pem")

with IMAPClient(HOST, ssl_context=ssl_context) as server:
    server.login(USERNAME, PASSWORD)
    # ...do something...

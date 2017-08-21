# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals
import imapclient
from backports import ssl

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'secret'

context = imapclient.create_default_context()

# don't check if certificate hostname doesn't match target hostname
context.check_hostname = False

# don't check if the certificate is trusted by a certificate authority
context.verify_mode = ssl.CERT_NONE

server = imapclient.IMAPClient(HOST, use_uid=True, ssl=True, ssl_context=context)
server.login(USERNAME, PASSWORD)
# ...

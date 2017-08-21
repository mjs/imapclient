# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals
import imapclient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'secret'

context = imapclient.create_default_context(cafile="/path/to/cacert.pem")

server = imapclient.IMAPClient(HOST, use_uid=True, ssl=True, ssl_context=context)
server.login(USERNAME, PASSWORD)
# ...

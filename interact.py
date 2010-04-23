#!/usr/bin/python

# Copyright (c) 2009, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses


import code
from optparse import OptionParser
import imapclient
from getpass import getpass


def command_line():
    p = OptionParser()
    p.add_option('-H', '--host', dest='host', action='store',
                 help='IMAP host connect to')
    p.add_option('-u', '--username', dest='username', action='store',
                 help='Username to login with')
    p.add_option('-p', '--password', dest='password', action='store',
                 help='Password to login with')
    p.add_option('-P', '--port', dest='port', action='store',
                 default=143, help='IMAP port to use (default is 143)')
    p.add_option('-s', '--ssl', dest='ssl', action='store_true', default=False,
                 help='Use SSL connection')

    options, args = p.parse_args()
    if args:
        p.error('unexpected arguments %s' % ' '.join(args))

    # Get compulsory options if not given on the command line
    for opt_name in ('host', 'username', 'password'):
        if not getattr(options, opt_name):
            setattr(options, opt_name, getpass(opt_name + ': '))

    return options


def setup_client():
    options = command_line()
    client = imapclient.IMAPClient(options.host, ssl=options.ssl)
    client.login(options.username, options.password)
    return client


if __name__ == '__main__':
    client = setup_client()
    banner = '\nIMAPClient instance is "c"'
    try:
        from IPython.Shell import IPShellEmbed
        c = client
        IPShellEmbed('', banner=banner)()
    except ImportError:
        code.interact(banner, local=dict(c=client))

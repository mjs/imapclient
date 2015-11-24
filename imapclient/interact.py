#!/usr/bin/python

# Copyright (c) 2014, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals


from getpass import getpass
from optparse import OptionParser

from six import iteritems

from .config import parse_config_file, create_client_from_config, get_config_defaults


def command_line():
    p = OptionParser()
    p.add_option('-H', '--host', dest='host', action='store',
                 help='IMAP host connect to')
    p.add_option('-u', '--username', dest='username', action='store',
                 help='Username to login with')
    p.add_option('-p', '--password', dest='password', action='store',
                 help='Password to login with')
    p.add_option('-P', '--port', dest='port', action='store', type=int,
                 default=None,
                 help='IMAP port to use (default is 143, or 993 for SSL)')
    p.add_option('-s', '--ssl', dest='ssl', action='store_true', default=False,
                 help='Use SSL connection')
    p.add_option('-f', '--file', dest='file', action='store', default=None,
                 help='Config file (same as livetest)')

    opts, args = p.parse_args()
    if args:
        p.error('unexpected arguments %s' % ' '.join(args))

    if opts.file:
        if opts.host or opts.username or opts.password or opts.port or opts.ssl:
            p.error('If -f/--file is given no other options can be used')
        # Use the options in the config file
        opts = parse_config_file(opts.file)
    else:
        # Scan through options, filling in defaults and prompting when
        # a compulsory option wasn't provided.
        compulsory_opts = ('host', 'username', 'password')
        for name, default_value in iteritems(get_config_defaults()):
            value = getattr(opts, name, default_value)
            if name in compulsory_opts and value is None:
                value = getpass(name + ': ')
            setattr(opts, name, value)

    return opts


def main():
    opts = command_line()
    print('Connecting...')
    client = create_client_from_config(opts)
    print('Connected.')
    banner = '\nIMAPClient instance is "c"'

    def ipython_400(c):
        from IPython.terminal.embed import InteractiveShellEmbed
        ipshell = InteractiveShellEmbed(banner1=banner)
        ipshell('')

    def ipython_011(c):
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
        ipshell = InteractiveShellEmbed(banner1=banner)
        ipshell('')

    def ipython_010(c):
        from IPython.Shell import IPShellEmbed
        IPShellEmbed('', banner=banner)()

    def builtin(c):
        import code
        code.interact(banner, local=dict(c=c))

    shell_attempts = (
        ipython_400,
        ipython_011,
        ipython_010,
        builtin,
    )
    for shell in shell_attempts:
        try:
            shell(client)
        except ImportError:
            pass
        else:
            break

if __name__ == '__main__':
    main()

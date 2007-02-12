#!/usr/bin/env python

# Warning: this script makes assumptions about the location of data files
# because distutils doesn't make it easy to substitute the correct installation
# directories into your files. If you use a custom --prefix to setup.py things
# may break. Yes, this sucks.

from distutils.core import setup
from distutils.sysconfig import get_config_var
import glob
import os

VERSION = '0.1'

LIB_DIR = get_config_var('LIBDIR')
BIN_DIR = get_config_var('BINDIR')
DATA_DIR = os.path.join(LIB_DIR, 'ssh-agent-applet')
BONOBO_SERVER_DIR = os.path.join(LIB_DIR, 'bonobo/servers')
GNOME_SCHEMA_DIR = '/etc/gconf/schemas'

# Subsitution file locations into various files that need it
def _subst(src, token, text):
    '''Perform substitution for defs.py
    '''
    return src.replace('<<'+token+'>>', text)

def munge(src, dst):
    defs = file(src).read()
    defs = _subst(defs, 'VERSION', VERSION)
    defs = _subst(defs, 'DATA_DIR', DATA_DIR)
    defs = _subst(defs, 'BIN_DIR', BIN_DIR)
    file(dst, 'w').write(defs)

munge('ssh-agent-applet.server.in', 'ssh-agent-applet.server')
munge('sshagentapplet/defs.py.in', 'sshagentapplet/defs.py')

# Run installation etc
setup(
    name='ssh-agent-applet',
    version=VERSION,
    description='Gnome applet to load keys into ssh-agent',
    author='Menno Smits',
    author_email='menno@freshfoo.com',
    license='GPL',
    packages=['sshagentapplet'],
    scripts=['ssh-agent-applet'],
    data_files=[
        (DATA_DIR, glob.glob('data/*')),
        (BONOBO_SERVER_DIR, ['ssh-agent-applet.server']),
        (GNOME_SCHEMA_DIR, ['ssh-agent-applet.schema']),
        ],
     )

#!/usr/bin/python

'''
Release script for IMAPClient
'''

import os
import sys
import imapclient

DIST_DIR = '../dist'

def fatal(msg):
    sys.stderr.write(msg+'\n')
    sys.exit(1)

os.system('find -name "*.pyc" | xargs rm -f')

# Check for stale commits
if os.popen('svn status').readlines():
    fatal("Stale commits, please fix")

# Tag in svn
exitcode = os.system('svn cp '
    '-m "tagging IMAPClient %(version)s" '
    'file:///home/msmits/svnroot/trunk/IMAPClient '
    'file:///home/msmits/svnroot/tags/IMAPClient/%(version)s' % {
        'version': imapclient.__version__ })
if exitcode:
    sys.exit(2)

# Create distribution archives
os.system('python setup.py sdist -d %s --formats=gztar,zip' % DIST_DIR)
os.system('rm -rf IMAPClient.egg-info')

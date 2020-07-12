#!/bin/bash

podman run --name=dovecot --rm -d -p 14301:143 dovecot/dovecot

cat >/tmp/livetest.ini <<EOF
[DEFAULT]
host = localhost
username = user
password = pass
port = 14301
ssl = false
EOF

python livetest.py /tmp/livetest.ini

podman rm -f dovecot

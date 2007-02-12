#!/bin/sh

# Install the gconf schema for the applet
gconftool-2 --install-schema-file=/etc/gconf/schemas/ssh-agent-applet.schema

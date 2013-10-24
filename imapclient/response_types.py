# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from collections import namedtuple

Address = namedtuple("Address", "Name Route Mailbox Host")

# note lowercase "from" is a keyword
Envelope = namedtuple("Envelope", "Date Subject From Sender Reply_To To " + \
                                  "Cc Bcc In_Reply_To Message_Id")

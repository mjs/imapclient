# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
Structured representation for IMAP response.
Inspired by Ruby Net::IMAP::Envelope and Net::IMAP::Address
(see http://www.ruby-doc.org/stdlib-2.0.0/libdoc/net/imap/rdoc/Net/IMAP.html).
"""

from collections import namedtuple

# the following hacks to add docstrings to namedtuples is courtesy of:
# http://stackoverflow.com/questions/1606436/adding-docstrings-to-namedtuples-in-python

class Address(namedtuple("Address", "Name Route Mailbox Host")):
    """
    Represents electronic mail addresses.

    Fields (in-order):

        Name -- Returns the phrase from [RFC-822] mailbox.

        Route -- Returns the route from [RFC-822] route-addr.

        Mailbox -- None indicates end of [RFC-822] group. If not None and host is None,
                   returns [RFC-822] group name. Otherwise, returns [RFC-822] local-part.

        Host -- None indicates [RFC-822] group syntax. Otherwise, returns [RFC-822] domain name.


    """

# note lowercase "from" is a keyword
class Envelope(namedtuple("Envelope", "Date Subject From Sender Reply_To To " + \
                          "Cc Bcc In_Reply_To Message_Id")):
    """

    Represents envelope structures of messages.

    Fields (in-order):

        Date -- Returns a string that represents the "Date:" header.

        Subject -- Returns a string that represents the "Subject:" header.

        From -- Returns a tuple sequence of Address structure that represents "From:" header,
                or None if header does not exist.

        Sender -- Returns a tuple sequence of Address structure that represents "Sender:" header,
                  or None if header does not exist.

        Reply_To -- Returns a tuple sequence of Address structure that represents "Reply_To:" header,
                    or None if header does not exist.

        To -- Returns a tuple sequence of Address structure that represents "To:" header,
              or None if header does not exist.

        Cc -- Returns a tuple sequence of Address structure that represents "Cc:" header,
              or None if header does not exist.

        Bcc -- Returns a tuple sequence of Address structure that represents "Bcc:" header,
               or None if header does not exist.

        In_Reply_To -- Returns a string that represents the "In-Reply-To:" header.

        Message_Id -- Returns a string that represents the "Message-Id:" header.


    """

# Copyright (c) 2013, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

"""
Structured representation for IMAP response.
Inspired by Ruby Net::IMAP::Envelope and Net::IMAP::Address
(see http://www.ruby-doc.org/stdlib-2.0.0/libdoc/net/imap/rdoc/Net/IMAP.html).
"""

from collections import namedtuple
from email.utils import formataddr

# the following hack to add docstrings to namedtuples is courtesy of:
# http://stackoverflow.com/questions/1606436/adding-docstrings-to-namedtuples-in-python

class Address(namedtuple("Address", "name route mailbox host")):
    """
    Represents electronic mail addresses.

    Fields (in-order):

        name -- Returns the phrase from [RFC-822] mailbox.

        route -- Returns the route from [RFC-822] route-addr.

        mailbox -- None indicates end of [RFC-822] group. If not None and host is None,
                   returns [RFC-822] group name. Otherwise, returns [RFC-822] local-part.

        host -- None indicates [RFC-822] group syntax. Otherwise, returns [RFC-822] domain name.

    """

    def __str__(self):
        return formataddr((self.name, self.mailbox + '@' + self.host))

class Envelope(namedtuple("Envelope", "date subject from_ sender reply_to to " +
                          "cc bcc in_reply_to message_id")):
    """

    Represents envelope structures of messages.

    Fields (in-order):

        date -- Returns a string that represents the "Date:" header.

        subject -- Returns a string that represents the "Subject:" header.

        from_ -- Returns a tuple sequence of Address structure that represents "From:" header,
                 or None if header does not exist.

        sender -- Returns a tuple sequence of Address structure that represents "Sender:" header,
                  or None if header does not exist.

        reply_to -- Returns a tuple sequence of Address structure that represents "Reply_To:" header,
                    or None if header does not exist.

        to -- Returns a tuple sequence of Address structure that represents "To:" header,
              or None if header does not exist.

        cc -- Returns a tuple sequence of Address structure that represents "Cc:" header,
              or None if header does not exist.

        bcc -- Returns a tuple sequence of Address structure that represents "Bcc:" header,
               or None if header does not exist.

        in_reply_to -- Returns a string that represents the "In-Reply-To:" header.

        message_id -- Returns a string that represents the "Message-Id:" header.

    """

IMAPClient
==========

.. toctree::
   :maxdepth: 1

Introduction
------------
A Pythonic, easy-to-use IMAP client package.

Although IMAPClient actually uses the imaplib module from the Python
standard library under the hood, it provides a different API. Instead
of requiring that the caller performs extra parsing work, return
values are full parsed, readily usable and use sensible Python
types. Exceptions are raised when problems occur (no error checking of
return values is required).

IMAPClient is straight forward it use, but it can be useful to have at
least a general understanding of the IMAP protocol. `RFC3501
<http://www.faqs.org/rfcs/rfc3501.html>`_ explains IMAP in
detail. Other RFCs also apply to various extensions to the base
protocol. These are referred to in the documentation below where
relevant.

A Simple Example
----------------
The core of the IMAPClient API is the IMAPClient class. Instantiating
this class, creates a connection to an IMAP account. Calling methods
on the IMAPClient instance interacts with the server.

The following example shows a simple interaction with an IMAP
server. It displays the message ID, size and IMAP flags of all
non-deleted messages in the INBOX folder.

.. literalinclude:: ../imapclient/examples/example.py

The output from this example could look something like this

::

    96 messages in INBOX
    75 messages that aren't deleted

    Messages:
       ID 38273: 1775 bytes, flags=('NonJunk',)
       ID 36459: 2833 bytes, flags=('\\Flagged', '\\Seen')
       ID 34693: 2874 bytes, flags=('\\Flagged', '\\Seen')
       ID 38066: 5368 bytes, flags=('\\Flagged', '\\Seen')
       ID 38154: 9079 bytes, flags=('\\Seen', 'NonJunk')
       ID 14099: 3322 bytes, flags=('\\Flagged', '\\Seen', '$Label1')
       ID 34196: 9163 bytes, flags=('\\Answered', '\\Seen')
       ID 35349: 4266 bytes, flags=('\\Flagged', '\\Seen')
       ID 29335: 5617 bytes, flags=('\\Flagged', '\\Seen', 'NonJunk')
       ID 38041: 7649 bytes, flags=('\\Seen', 'NonJunk')
       ID 22310: 976108 bytes, flags=('\\Flagged', '\\Seen', '$Label1')
       ID 6439: 3792 bytes, flags=('\\Flagged', '\\Seen', '$Label1', 'Junk')


Concepts
--------

Message Identifiers
~~~~~~~~~~~~~~~~~~~
There are two ways to refer to messages using the IMAP protocol. 

One way is by message sequence number where the messages in a mailbox
are numbered from 1 to N where N is the number of messages. These
numbers don't persist between sessions and may be reassigned after
some operations such as a folder expunge.

XXX explain UIDs

XXX rework below
Message unique identifiers (UID) can be used with any call. The use_uid
argument to the constructor and the use_uid attribute control whether UIDs
are used.

Any method that accepts message id's takes either a sequence containing
message IDs (eg. [1,2,3]) or a single message ID as an integer.

Message Flags
~~~~~~~~~~~~~
Any method that accepts message flags takes either a sequence containing
message flags (eg. [DELETED, 'foo', 'Bar']) or a single message flag (eg.
'Foo'). See the constants at the top of this file for commonly used flags.

Folder Name Encoding
~~~~~~~~~~~~~~~~~~~~
XXX 
Any method that takes a folder name will accept a standard string or a
unicode string. Unicode strings will be transparently encoded using
modified UTF-7 as specified by RFC-2060. Such folder names will be returned
as unicode strings by methods that return folder names.

Transparent folder name encoding can be enabled or disabled with the
folder_encode attribute. It defaults to True.

XXX check FPNP for more ideas on what should go in here

Exceptions
~~~~~~~~~~
The IMAP related exceptions that will be raised by this class are:

* IMAPClient.Error
* IMAPClient.AbortError
* IMAPClient.ReadOnlyError

These are aliases for the imaplib.IMAP4 exceptions of the same name. Socket
errors may also be raised in the case of network errors.

IMAPClient Class Reference
--------------------------
The primary class used by the imapclient package is the IMAPClient
class. All interaction with a remote IMAP server is performed via an
IMAPClient instance.

.. autoclass:: imapclient.IMAPClient
   :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


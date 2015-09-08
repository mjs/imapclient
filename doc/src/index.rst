============
 IMAPClient
============

:Author: `Menno Smits <http://freshfoo.com>`_
:Version: |release|
:Date: |today|
:Homepage: http://imapclient.freshfoo.com
:Download: http://pypi.python.org/pypi/IMAPClient/
:Documentation: http://imapclient.readthedocs.org/
:License: `New BSD License <http://en.wikipedia.org/wiki/BSD_licenses>`_
:Support: `Mailing List <http://librelist.com/browser/imapclient/>`_

Introduction
------------
IMAPClient is an easy-to-use, Pythonic and complete IMAP client
library.

Although IMAPClient actually uses the imaplib module from the Python
standard library under the hood, it provides a different API. Instead
of requiring that the caller performs extra parsing work, return
values are full parsed, readily usable and use sensible Python
types. Exceptions are raised when problems occur (no error checking of
return values is required).

IMAPClient is straight forward it use, but it can be useful to have at
least a general understanding of the IMAP protocol. :rfc:`3501`
explains IMAP in detail. Other RFCs also apply to various extensions
to the base protocol. These are referred to in the documentation below
where relevant.

Python versions 2.6, 2.7, 3.3 and 3.4 are officially supported.

A Simple Example
----------------
The core of the IMAPClient API is the IMAPClient class. Instantiating
this class, creates a connection to an IMAP account. Calling methods
on the IMAPClient instance interacts with the server.

The following example shows a simple interaction with an IMAP
server. It displays the message ID, size and IMAP flags of all
non-deleted messages in the INBOX folder.

.. literalinclude:: ../../imapclient/examples/example.py

The output from this example could look something like this

::

    96 messages in INBOX
    75 messages that aren't deleted

    Messages:
       ID 38273: 1775 bytes, flags=(b'NonJunk',)
       ID 36459: 2833 bytes, flags=(b'\\Flagged', v'\\Seen')
       ID 34693: 2874 bytes, flags=(b'\\Flagged', v'\\Seen')
       ID 38066: 5368 bytes, flags=(b'\\Flagged', v'\\Seen')
       ID 38154: 9079 bytes, flags=(b'\\Seen', b'NonJunk')
       ID 14099: 3322 bytes, flags=(b'\\Flagged', b'\\Seen', b'$Label1')
       ID 34196: 9163 bytes, flags=(b'\\Answered', b'\\Seen')
       ID 35349: 4266 bytes, flags=(b'\\Flagged', b'\\Seen')
       ID 29335: 5617 bytes, flags=(b'\\Flagged', b'\\Seen', b'NonJunk')
       ID 38041: 7649 bytes, flags=(b'\\Seen', b'NonJunk')
       ID 22310: 976108 bytes, flags=(b'\\Flagged', b'\\Seen', b'$Label1')
       ID 6439: 3792 bytes, flags=(b'\\Flagged', b'\\Seen', b'$Label1', b'Junk')


Concepts
--------

Message Identifiers
~~~~~~~~~~~~~~~~~~~
There are two ways to refer to messages using the IMAP protocol.

One way is by message sequence number where the messages in a mailbox
are numbered from 1 to N where N is the number of messages. These
numbers don't persist between sessions and may be reassigned after
some operations such as a folder expunge.

A more convenient approach is Unique Identifiers (UIDs). Unique
Identifiers are integers assigned to each message by the IMAP server
that will persist across sessions. They do not change when folders are
expunged.

Each call to the IMAP server can use either message sequence numbers
or UIDs in the command arguments and return values. The client
specifies to the server which type of identifier should be
used. IMAPClient uses UIDs by default.

Any method that accepts message ids takes either a sequence containing
message ids (eg. ``[1,2,3]``), or a single message id integer, or a
string representing sets and ranges of messages as supported by the
IMAP protocol (e.g. ``'50-65'``, ``'2:*'`` or
``'2,4:7,9,12:*'``). Whether these are interpreted as message sequence
numbers or UIDs depends on the *use_uid* argument passed when an
IMAPClient instance is created and the *use_uid* attribute. The
*use_uid* attribute can be used to change the message id type between
calls to the server.

Message Flags
~~~~~~~~~~~~~
An IMAP server keeps zero or more flags for each message. These
indicate certain properties of the message or can be used by IMAP
clients to keep track of data related to a message.

The IMAPClient package has constants for a number of commmonly used flags::

    DELETED = br'\Deleted'
    SEEN = br'\Seen'
    ANSWERED = br'\Answered'
    FLAGGED = br'\Flagged'
    DRAFT = br'\Draft'
    RECENT = br'\Recent'         # This flag is read-only

Any method that accepts message flags takes either a sequence
containing message flags (eg. ``[DELETED, 'foo', 'Bar']``) or a single
message flag (eg.  ``'Foo'``).

Folder Name Encoding
~~~~~~~~~~~~~~~~~~~~
Any method that takes a folder name will accept a standard string or a
unicode string. Unicode strings will be transparently encoded using
modified UTF-7 as specified by :rfc:`3501#section-5.1.3`.  This allows
for arbitrary unicode characters (eg. non-English characters) to be
used in folder names.

The ampersand character ("&") has special meaning in IMAP folder
names. IMAPClient automatically escapes and unescapes this character
so that the caller doesn't have to.

Automatic folder name encoding and decoding can be enabled or disabled
with the *folder_encode* attribute. It defaults to True.

If *folder_encode* is True, all folder names returned by IMAPClient
are always returned as unicode strings. If *folder_encode* is False,
folder names are returned as str (Python 2) or bytes (Python 3).

Exceptions
~~~~~~~~~~
The IMAP related exceptions that will be raised by this class are:

* IMAPClient.Error
* IMAPClient.AbortError
* IMAPClient.ReadOnlyError

These are aliases for the imaplib.IMAP4 exceptions of the same name. Socket
errors may also be raised in the case of network errors.

TLS/SSL
~~~~~~~
IMAPClient uses sensible TLS parameter defaults for encrypted
connections and also allows for a high level of control of TLS
parameters if required. To provide a consistent API and capabilities
across Python versions the `backports.ssl <https://github.com/alekstorm/backports.ssl>`_
library is used instead of the standard library ssl
package. backports.ssl provides an API that aims to mimic the Python
3.4 ssl package so it should be familiar to developers that have used
the ssl package in recent versions of Python.

TLS parameters are controlled by passing a ``backports.ssl.SSLContext``
when creating an IMAPClient instance. When ``ssl=True`` is used
without passing a SSLContext, a default context is used. The default
context avoids the use of known insecure ciphers and SSL protocol
versions, with certificate verification and hostname verification
turned on. The default context will use system installed certificate
authority trust chains, if available.

:py:func:`IMAPClient.tls.create_default_context` returns IMAPClient's
default context. When constructing a custom context it is usually best
to start with the default context and modify it to suit your needs.

The following example shows how to to disable certification
verification and certificate host name checks if required.

.. literalinclude:: ../../imapclient/examples/tls_no_checks.py

The next example shows how to create a context that will use custom CA
certificate. This is required to perform verification of a self-signed
certificate used by the IMAP server.

.. literalinclude:: ../../imapclient/examples/tls_cacert.py

The above examples show some of the most common TLS parameter
customisations but there are many other tweaks are possible. Consult
the Python 3 :py:mod:`ssl` package documentation for further options.

Using gevent with IMAPClient
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Some extra monkey patching is required to let gevent_ work with
pyOpenSSL (used by IMAPClient for TLS support). The `gevent_openssl`_
package performs this patching and can be used with IMAPClient like
this::

  from gevent import monkey; monkey.patch_all()
  import gevent_openssl; gevent_openssl.monkey_patch()

  import imapclient

  client = imapclient.IMAPClient(...)
  ...

.. _gevent: http://www.gevent.org/
.. _`gevent_openssl`: https://pypi.python.org/pypi/gevent_openssl/

API Reference
-------------

IMAPClient Class
~~~~~~~~~~~~~~~~
The primary class used by the imapclient package is the IMAPClient
class. All interaction with a remote IMAP server is performed via an
IMAPClient instance.

.. autoclass:: imapclient.IMAPClient
   :members:

Fetch Response Types
~~~~~~~~~~~~~~~~~~~~
Various types may be used in the data structures returned by
:py:meth:`.IMAPClient.fetch` when certain response types
are encountered during parsing.

.. automodule:: imapclient.response_types
   :members:

TLS Support
~~~~~~~~~~~

.. automodule:: imapclient.tls
   :members:

Interactive Sessions
--------------------
When developing program using IMAPClient is it sometimes useful to
have an interactive shell to play with. IMAPClient ships with a module
that lets you fire up an interactive shell with an IMAPClient instance
connected to an IMAP server.

Start a session like this::

   python -m imapclient.interact -H <host> -u <user> ...

Various options are available to specify the IMAP server details. See
the help (--help) for more details. You'll be prompted for a username
and password if one isn't provided on the command line.

The connected IMAPClient instance is available as the variable "c".

If installed, IPython will be used as the embedded shell. Otherwise
the basic built-in Python shell will be used.

Here's an example session::

    $ python -m imapclient.interact -H <host> -u <user> ...
    Connecting...
    Connected.

    IMAPClient instance is "c"
    In [1]: c.select_folder('inbox')
    Out[1]: 
    {b'EXISTS': 2,
     b'FLAGS': (b'\\Answered',
         b'\\Flagged',
         b'\\Deleted',
         b'\\Seen',
         b'\\Draft'),
     b'PERMANENTFLAGS': (b'\\Answered',
         b'\\Flagged',
         b'\\Deleted',
         b'\\Seen',
         b'\\Draft'),
     b'READ-WRITE': True,
     b'RECENT': 0,
     b'UIDNEXT': 1339,
     b'UIDVALIDITY': 1239278212}

    In [2]: c.search()
    Out[2]: [1123, 1233]

    In [3]: c.logout()
    Out[3]: b'Logging out'

External Documentation
----------------------
The `Unofficial IMAP Protocol Wiki <http://www.imapwiki.org/>`_ is
very useful when writing IMAP related software and is highly
recommended.

Release History
---------------
.. toctree::
   :maxdepth: 1

   releases

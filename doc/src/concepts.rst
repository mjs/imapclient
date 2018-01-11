IMAPClient Concepts
-------------------

Message Identifiers
~~~~~~~~~~~~~~~~~~~
In the IMAP protocol, messages are identified using an integer. These
message ids are specific to a given folder.

There are two types of message identifiers in the IMAP protocol.

One type is the message sequence number where the messages in a folder
are numbered from 1 to N where N is the number of messages in the
folder. These numbers don't persist between sessions and may be
reassigned after some operations such as an expunge.

A more convenient approach is Unique Identifiers (UIDs). Unique
Identifiers are integers assigned to each message by the IMAP server
that will persist across sessions. They do not change when folders are
expunged. Almost all IMAP servers support UIDs.

Each call to the IMAP server can use either message sequence numbers
or UIDs in the command arguments and return values. The client
specifies to the server which type of identifier should be used. You
can set whether IMAPClient should use UIDs or message sequence number
via the *use_uid* argument passed when an IMAPClient instance is
created and the *use_uid* attribute. The *use_uid* attribute can be
used to change the message id type between calls to the
server. IMAPClient uses UIDs by default.

Any method that accepts message ids takes either a sequence containing
message ids (eg. ``[1,2,3]``), or a single message id integer, or a
string representing sets and ranges of messages as supported by the
IMAP protocol (e.g. ``'50-65'``, ``'2:*'`` or ``'2,4:7,9,12:*'``).

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

TLS/SSL
~~~~~~~
IMAPClient uses sensible TLS parameter defaults for encrypted
connections and also allows for a high level of control of TLS
parameters if required. It uses the built-in `ssl` package, 
provided since Python 2.7.9 and 3.4.

TLS parameters are controlled by passing a ``ssl.SSLContext`` when
creating an IMAPClient instance (or to the `starttls` method when the
STARTTLS is used). When ``ssl=True`` is used without passing a
SSLContext, a default context is used. The default context avoids the
use of known insecure ciphers and SSL protocol versions, with
certificate verification and hostname verification turned on. The
default context will use system installed certificate authority trust
chains, if available.

When constructing a custom context it is usually best to start with
the default context, created by the ``ssl`` module, and modify it to
suit your needs.

.. warning::

  Users of Python 2.7.0 - 2.7.8 can use TLS but cannot configure
  the settings via an ``ssl.SSLContext``. These Python versions are
  also not capable of proper certification verification. It is highly
  encouraged to upgrade to a more recent version of Python.

The following example shows how to to disable certification
verification and certificate host name checks if required.

.. literalinclude:: ../../examples/tls_no_checks.py

The next example shows how to create a context that will use custom CA
certificate. This is required to perform verification of a self-signed
certificate used by the IMAP server.

.. literalinclude:: ../../examples/tls_cacert.py

If your operating system comes with an outdated list of CA certificates you can
use the `certifi <https://pypi.python.org/pypi/certifi>`_ package that provides
an up-to-date set of trusted CAs::

  import certifi

  ssl_context = ssl.create_default_context(cafile=certifi.where())

The above examples show some of the most common TLS parameter
customisations but there are many other tweaks are possible. Consult
the Python 3 :py:mod:`ssl` package documentation for further options.

Logging
~~~~~~~
IMAPClient logs debug lines using the standard Python :py:mod:`logging`
module. Its logger prefix is ``imapclient.``.

One way to see debug messages from IMAPClient is to set up logging
like this::

  import logging

  logging.basicConfig(
      format='%(asctime)s - %(levelname)s: %(message)s',
      level=logging.DEBUG
  )

For advanced usage, please refer to the documentation ``logging``
module.

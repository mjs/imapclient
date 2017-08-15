Advanced Usage
--------------
This document covers some more advanced features and tips for handling
specific usages.

Watching a mailbox asynchronously using idle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TODO

Handling large mailboxes
~~~~~~~~~~~~~~~~~~~~~~~~
TODO

Interactive Sessions
~~~~~~~~~~~~~~~~~~~~
When developing program using IMAPClient is it sometimes useful to
have an interactive shell to play with. IMAPClient ships with a module
that lets you fire up an interactive shell with an IMAPClient instance
connected to an IMAP server.

Start a session like this::

   python -m imapclient.interact -H <host> -u <user> ...

Various options are available to specify the IMAP server details. See
the help (--help) for more details. You'll be prompted for a username
and password if one isn't provided on the command line.

It is also possible to pass connection details as a configuration file
like this::

   python -m imapclient.interact -f <config file>

See below for details of the :ref:`configuration file format<conf-files>`.

If installed, IPython will be used as the embedded shell. Otherwise
the basic built-in Python shell will be used.

The connected IMAPClient instance is available as the variable
"c". Here's an example session::

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


.. _conf-files:

Configuration File Format
+++++++++++++++++++++++++
Both the IMAPClient interactive shell and the live tests take
configuration files which specify how to to connect to an IMAP
server. The configuration file format is the same for both.

Configuration files use the INI format and must always have a section
called ``DEFAULT``. Here's a simple example::

    [DEFAULT]
    host = imap.mailserver.com
    username = bob
    password = sekret
    ssl = True

The supported options are:

==================== ======= =========================================================================================
Name                 Type    Description
==================== ======= =========================================================================================
host                 string  IMAP hostname to connect to.
username             string  The username to authenticate as.
password             string  The password to use with ``username``.
port                 int     Server port to connect to. Defaults to 143 unless ``ssl`` is True.
ssl                  bool    Use SSL/TLS to connect.
starttls             bool    Use STARTTLS to connect.
ssl_check_hostname   bool    If true and SSL is in use, check that certificate matches the hostname (defaults to true)
ssl_verify_cert      bool    If true and SSL is in use, check that the certifcate is valid (defaults to true).
ssl_ca_file          string  If SSL is true, use this to specify certificate authority certs to validate with.
timeout              int     Time out I/O operations after this many seconds.
oauth2               bool    If true, use OAUTH2 to authenticate (``username`` and ``password`` are ignored).
oauth2_client_id     string  OAUTH2 client id.
oauth2_client_secret string  OAUTH2 client secret.
oauth2_refresh_token string  OAUTH2 token for refreshing the secret.
==================== ======= =========================================================================================

Acceptable boolean values are "1", "yes", "true", and "on", for true;
and "0", "no", "false", and "off", for false.

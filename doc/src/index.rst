============
 IMAPClient
============

:Author: `Menno Finlay-Smits <http://menno.io/>`_
:Version: |release|
:Date: |today|
:Homepage: http://imapclient.freshfoo.com
:Download: http://pypi.python.org/pypi/IMAPClient/
:Source code: https://github.com/mjs/imapclient
:Documentation: http://imapclient.readthedocs.io/
:License: `New BSD License <http://en.wikipedia.org/wiki/BSD_licenses>`_
:Support: `Mailing List <https://groups.io/g/imapclient>`_

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

Python versions 2.7 and 3.4 through 3.9 are officially supported.

Getting Started
---------------

Install IMAPClient::

    $ pip install imapclient

See :ref:`Installation <installation>` for more details.

The core of the IMAPClient API is the IMAPClient class. Instantiating
this class, creates a connection to an IMAP account. Calling methods
on the IMAPClient instance interacts with the server.

The following example shows a simple interaction with an IMAP server.
It displays the message ID, subject and date of the message for all
messages in the INBOX folder.

::

    >>> from imapclient import IMAPClient
    >>> server = IMAPClient('imap.mailserver.com', use_uid=True)
    >>> server.login('someuser', 'somepassword')
    b'[CAPABILITY IMAP4rev1 LITERAL+ SASL-IR [...] LIST-STATUS QUOTA] Logged in'

    >>> select_info = server.select_folder('INBOX')
    >>> print('%d messages in INBOX' % select_info[b'EXISTS'])
    34 messages in INBOX

    >>> messages = server.search(['FROM', 'best-friend@domain.com'])
    >>> print("%d messages from our best friend" % len(messages))
    5 messages from our best friend

    >>> for msgid, data in server.fetch(messages, ['ENVELOPE']).items():
    >>>     envelope = data[b'ENVELOPE']
    >>>     print('ID #%d: "%s" received %s' % (msgid, envelope.subject.decode(), envelope.date))
    ID #62: "Our holidays photos" received 2017-07-20 21:47:42
    ID #55: "Re: did you book the hotel?" received 2017-06-26 10:38:09
    ID #53: "Re: did you book the hotel?" received 2017-06-25 22:02:58
    ID #44: "See that fun article about lobsters in Pacific ocean!" received 2017-06-09 09:49:47
    ID #46: "Planning for our next vacations" received 2017-05-12 10:29:30

    >>> server.logout()
    b'Logging out'

User Guide
----------
This section describes how IMAPClient works and gives some examples to
help you start.

.. toctree::
    :maxdepth: 2

    installation
    concepts
    advanced


API Reference
-------------
This section describes public functions and classes of IMAPClient
library.

.. toctree::
    :maxdepth: 2

    api


Contributor Guide
-----------------
.. toctree::
    :maxdepth: 2

    contributing


External Documentation
----------------------
The `Unofficial IMAP Protocol Wiki <http://www.imapwiki.org/>`_ is
very useful when writing IMAP related software and is highly
recommended.


Authors
-------

.. include:: ../../AUTHORS.rst


Release History
---------------
.. toctree::
   :maxdepth: 1

   releases

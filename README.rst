Essentials
----------
IMAPClient is an easy-to-use, Pythonic and complete IMAP client
library.

=========================  ========================================
Current version            2.2.0
Supported Python versions  2.7, 3.4 - 3.9
License                    New BSD
Project home               https://github.com/mjs/imapclient/
PyPI                       https://pypi.python.org/pypi/IMAPClient
Documentation              https://imapclient.readthedocs.io/
Mailing list               https://groups.io/g/imapclient
=========================  ========================================

Test Status
~~~~~~~~~~~

===================== ==============
``1.x`` unit tests    |build 1.x|
``master`` unit tests |build master|
===================== ==============

.. |build 1.x| image:: https://travis-ci.org/mjs/imapclient.svg?branch=1.x
    :target: https://travis-ci.org/mjs/imapclient/branches
    :alt: 1.x branch

.. |build master| image:: https://travis-ci.org/mjs/imapclient.svg?branch=master
   :target: https://travis-ci.org/mjs/imapclient/branches
   :alt: master branch


Features
--------
- Arguments and return values are natural Python types.
- IMAP server responses are fully parsed and readily usable.
- IMAP unique message IDs (UIDs) are handled transparently. There is
  no need to call different methods to use UIDs.
- Escaping for internationalised mailbox names is transparently
  handled.  Unicode mailbox names may be passed as input wherever a
  folder name is accepted.
- Time zones are transparently handled including when the server and
  client are in different zones.
- Convenience methods are provided for commonly used functionality.
- Exceptions are raised when errors occur.

Example
-------

.. code-block:: python

    from imapclient import IMAPClient

    # context manager ensures the session is cleaned up
    with IMAPClient(host="imap.host.org") as client:
        client.login('someone', 'secret')
        client.select_folder('INBOX')

        # search criteria are passed in a straightforward way
        # (nesting is supported)
        messages = client.search(['NOT', 'DELETED'])

        # fetch selectors are passed as a simple list of strings.
        response = client.fetch(messages, ['FLAGS', 'RFC822.SIZE'])

        # `response` is keyed by message id and contains parsed,
        # converted response items.
        for message_id, data in response.items():
            print('{id}: {size} bytes, flags={flags}'.format(
                id=message_id,
                size=data[b'RFC822.SIZE'],
                flags=data[b'FLAGS']))

Why IMAPClient?
---------------
You may ask: "why create another IMAP client library for Python?
Doesn't the Python standard library already have imaplib?".

The problem with imaplib is that it's very low-level. It expects
string values where lists or tuples would be more appropriate and
returns server responses almost unparsed. As IMAP server responses can
be quite complex this means everyone using imaplib ends up writing
their own fragile parsing routines.

Also, imaplib doesn't make good use of exceptions. This means you need
to check the return value of each call to imaplib to see if what you
just did was successful.

IMAPClient actually uses imaplib internally. This may change at some
point in the future.

Installing IMAPClient
---------------------
IMAPClient is listed on PyPI and can be installed with pip::

    pip install imapclient

More installation methods are described in the documentation.

Documentation
-------------
IMAPClient's manual is available at http://imapclient.readthedocs.io/.
Release notes can be found at
http://imapclient.readthedocs.io/#release-history.

See the `examples` directory in the root of project source for
examples of how to use IMAPClient.

Current Status
--------------
You should feel confident using IMAPClient for production
purposes. Any problems found will be fixed quickly once reported.

In order to clearly communicate version compatibility, IMAPClient
will strictly adhere to the `Semantic Versioning <http://semver.org>`_
scheme from version 1.0 onwards.

The project's home page is https://github.com/mjs/imapclient/ (this
currently redirects to the IMAPClient Github site). Details about
upcoming versions and planned features/fixes can be found in the issue
tracker on Github. The maintainers also blog about IMAPClient
news. Those articles can be found `here
<http://menno.io/tags/imapclient>`_.

Mailing List
------------
The IMAPClient mailing list can be used to ask IMAPClient related
questions and report bugs. Details of new releases and project changes
will also be announced there.

The mailing list is hosted at `Groups.io
<http://groups.io>`_. Interaction via both email and the web is
supported. To join the list, see the list archives or just find out
more, visit https://groups.io/g/imapclient. The key details of the
list are:

* Post: imapclient@groups.io
* Subscribe: imapclient+subscribe@groups.io
* Unsubscribe: imapclient+unsubscribe@groups.io
* Web: https://groups.io/g/imapclient
* Web archives: https://groups.io/g/imapclient/messages

If you're having trouble using the mailing list, please email
inbox@menno.io.

Working on IMAPClient
---------------------
The `contributing documentation
<http://imapclient.rtfd.io/en/master/contributing.html>`_ contains
information for those interested in improving IMAPClient.

IMAP Servers
------------
IMAPClient is heavily tested against Dovecot, Gmail, Fastmail.fm
(who use a modified Cyrus implementation), Office365 and Yahoo. Access
to accounts on other IMAP servers/services for testing would be
greatly appreciated.

Interactive Console
-------------------
This script connects an IMAPClient instance using the command line
args given and starts an interactive session. This is useful for
exploring the IMAPClient API and testing things out, avoiding the
steps required to set up an IMAPClient instance.

The IPython shell is used if it is installed. Otherwise the
code.interact() function from the standard library is used.

The interactive console functionality can be accessed running the
interact.py script in the root of the source tree or by invoking the
interact module like this::

    python -m imapclient.interact ...

"Live" Tests
------------
IMAPClient includes a series of live, functional tests which exercise
it against a live IMAP account. These are useful for ensuring
compatibility with a given IMAP server implementation.

The livetest functionality are run from the root of the project source
like this::

    python livetest.py <livetest.ini> [ optional unittest arguments ]

The configuration file format is
`described in the main documentation <http://imapclient.rtfd.io/#configuration-file-format>`_.

**WARNING**: The operations used by livetest are destructive and could
cause unintended loss of data. That said, as of version 0.9, livetest
limits its activity to a folder it creates and subfolders of that
folder. It *should* be safe to use with any IMAP account but please
don't run livetest against a truly important IMAP account.

Please send the output of livetest.py to the mailing list if it fails
to run successfully against a particular IMAP server. Reports of
successful runs are also welcome.  Please include the type and version
of the IMAP server, if known.

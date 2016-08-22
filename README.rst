Essentials
----------
IMAPClient is an easy-to-use, Pythonic and complete IMAP client
library.

=========================  ========================================
Current version            1.0.2
Supported Python versions  2.6, 2.7, 3.3, 3.4 and 3.5
License                    New BSD
Project home               http://imapclient.freshfoo.com/
PyPI                       https://pypi.python.org/pypi/IMAPClient
Documentation              http://imapclient.readthedocs.io/
Mailing list               https://groups.io/g/imapclient
=========================  ========================================

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

Why IMAPClient?
---------------
You may ask: "why create another IMAP client library for Python?
Doesn't the Python standard library already have imaplib?".

The problem with imaplib is that it's very low-level. It expects
string values where lists or tuples would be more appropriate and
returns server responses almost unparsed. As IMAP server responses can
be quite complex this means everyone using imaplib ends up writing
their own flimsy parsing routines which break easily.

Also, imaplib doesn't make good use of exceptions. This means you need
to check the return value of each call to imaplib to see if what you
just did was successful.

IMAPClient actually uses imaplib internally. This may change at some
point in the future.

Installing IMAPClient
---------------------
IMAPClient is listed on the PyPI (Python Package Index). To install
via PyPI use the pip or easy_install tools::

    pip install imapclient

    easy_install IMAPClient

The source distributions of all IMAPClient versions are available at
http://freshfoo.com/projects/IMAPClient/. Alternatively you can also
use the PyPI page at https://pypi.python.org/pypi/IMAPClient/.

To install from source run::

    python setup.py install

The project is packaged using Distribute (mostly compatible with
setuptools) and all the usual setup.py installation options are
available. See http://packages.python.org/distribute/ for more info.

Documentation
-------------
IMAPClient's manual is available at http://imapclient.readthedocs.io/. Release notes can be found at http://imapclient.readthedocs.io/#release-history.

The Sphinx source for the documentation can be found under doc/src. If
Sphinx is installed, the documentation can be rebuilt using::

    python setup.py build_sphinx

See the imapclient/examples directory for examples of how to use
IMAPClient. If the IMAPClient was installed from PyPI, the examples
subdirectory can be found under the imapclient package in the
installation directory.

Current Status
--------------
IMAPClient is currently under development but it is unlikely that
the existing API will change in backwards-incompatible ways. Changes
planned for the near future will only add extra functionality to the
API.

You should feel confident using IMAPClient for production
purposes. Any problems found will be fixed quickly once reported.

The project's home page is http://imapclient.freshfoo.com/ (this
currently redirects to the IMAPClient Bitbucket site). Details about
upcoming versions and planned features/fixes can be found in the issue
tracker on Bitbucket. The maintainer also blogs about IMAPClient
news. Those articles can be found `here
<http://freshfoo.com/tags/imapclient>`_.

Versions
--------
In order to clearly communicate version compatibility, IMAPClient
will strictly adhere to the `Semantic Versioning <http://semver.org>`_
scheme from version 1.0 onwards.

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
menno@freshfoo.com.

Working on IMAPClient
---------------------
The HACKING.rst document contains information for those interested in
improving IMAPClient and contributing back to the project.

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
IMAPClient includes a series of functional tests which exercise
it against a live IMAP account. It is useful for ensuring
compatibility with a given IMAP server implementation.

The livetest functionality can also be accessed like this::

    python -m imapclient.livetest <livetest.ini> [ optional unittest arguments ]

Alternatively you can run the ``livetest.py`` script included with the
source distribution. Use ``livetest.py --help`` to see usage.

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

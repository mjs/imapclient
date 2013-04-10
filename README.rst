Introduction
------------
IMAPClient aims to be a easy-to-use, Pythonic and complete IMAP client
library.

Features:

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


Current Status
--------------
IMAPClient is currently under development but it is unlikely that
the existing API will change in backwards-incompatible ways. Changes
planned for the near future will only add extra functionality to the
API.

You should feel confident using IMAPClient for production
purposes. Any problems found will be fixed quickly once reported.

The project's home page is a Trac instance at: http://imapclient.freshfoo.com/

Details about upcoming versions and planned features/fixes can be
found there.


Using IMAPClient
----------------
IMAPClient is listed on the PyPI (Python Package Index). To install
via PyPI use the pip or easy_install tools::

    pip install imapclient

    easy_install IMAPClient

To install from the source distribution::

    python setup.py install

The project is packaged using Distribute (mostly compatible with
setuptools) and all the usual setup.py installation options are
available. See http://packages.python.org/distribute/ for more info.


Documentation
-------------
HTML documentation can be found at doc/html in the source
distribution. The documentation is also available online at:
http://imapclient.readthedocs.org/

The Sphinx source is at doc/src. If Sphinx is installed, the
documentation can be rebuilt using::

    python setup.py build_sphinx

See imapclient/examples/example.py for a sample of how to use
IMAPClient. If the IMAPClient was installed from PyPI the examples
subdirectory can be found under the imapclient package installation
directory.


Working on IMAPClient
---------------------
The HACKING.rst document contains information for those interested in
improving IMAPClient and contributing back to the project.


Mailing List
------------
The IMAPClient mailing list can be used to ask IMAPClient related
questions and report bugs.

- To send to the list and subscribe send an email to imapclient@librelist.com
- Archives of the list are available at http://librelist.com/browser/imapclient/
- See http://librelist.com/help.html for more information about the mailing list


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

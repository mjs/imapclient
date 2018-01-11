============================
 Contributing to IMAPClient
============================

The best way to contribute changes to IMAPClient is to fork the
official repository on Github, make changes in a branch in your
personal fork and then submit a pull request.

Discussion on the mailing list before undertaking development is
highly encouraged for potentially major changes.

Although not essential, it will make the project maintainers much
happier if change submissions include appropriate updates to unit
tests, live tests and documentation. Please ask if you're unsure how
of how the tests work.

Please read on if you plan on submitting changes to IMAPClient.

Source Code
===========
The official source code repository for IMAPClient can be found on
Github at: https://github.com/mjs/imapclient

Any major feature work will also be found as branches of this
repository.

Branches
--------
Development for the next major release happens on the ``master`` branch.

There is also a branch for each major release series (for example:
``1.x``). When appropriate and when there will be future releases for
a series, changes may be selectively merged between ``master`` and a
stable release branch.

Release Tags
------------
Each released version is available in the IMAPClient repository
as a Git tag (e.g. "0.9.1").

Unit Tests
==========

Running Unit Tests
------------------
To run the tests, from the root of the package source run::

     python setup.py test

Testing Against Multiple Python Versions
----------------------------------------
When submitting a Pull Request to IMAPClient, tests are automatically ran
against all the supported Python versions.

It is possible to locally run these tests using `tox`_. Once
installed, the ``tox`` command will use the tox.ini file in the root
of the project source and run the unit tests against the Python
versions officially supported by IMAPClient (provided these versions
of Python are installed!).

.. _`tox`: http://testrun.org/tox/

Writing Unit Tests
------------------
Protocol level unit tests should not act against a real IMAP server
but should use canned data instead. The IMAPClientTest base class
should typically be used as the base class for any tests - it provides
a mock IMAPClient instance at `self.client`. See the tests in
`tests/test_imapclient.py` for examples of how to write unit tests using
this approach.

Documentation
=============
The source for the project's documentation can be found under doc/src
in the source distribution.

In order to build the documentation you'll need install
Sphinx. Running ``pip install '.[doc]'`` from the root of the project
source will do this.

Once Sphinx is installed, the documentation can be rebuilt using::

    python setup.py build_sphinx

:tocdepth: 1

===============
 Version 1.0.2
===============

New
---
- Documented the livetest/interact INI file format.
- Documented handling of RFC2822 group syntax.

Changed
-------
- Explicitly check that the required pyOpenSSL version is installed
- Start testing against Python 3.5
- Update doc links from readthedocs.org to readthedocs.io
- Rearranged README so that project essentials are right at the top.

Fixed
-----
- Allow installation from alternate directories

===============
 Version 1.0.1
===============

Changed
-------
- Minimum backports.ssl dependency is now 0.0.9 (an important
  performance issue was addressed)
- setuptools 18.8.1 now used due to strange zip file error for 17.1

Fixed
-----
- Unit test for version strings were updated to now always include the
  patch version.
- Fresh capabilities now retrieved between STARTTLS and authentication
  (#195).

===============
 Version 1.0.0
===============

Enhanced TLS support [API]
--------------------------
The way that IMAPClient establishes TLS/SSL connections has been
completely reworked. By default IMAPClient will attempt certificate
verification, certificate hostname checking, and will not use
known-insecure TLS settings and protocols. In addition, TLS parameters
are now highly configurable.

By leveraging pyOpenSSL and backports.ssl, all Python versions
supported by IMAPClient enjoy the same TLS functionality and
API.

These packages mean that IMAPClient now has a number of new
dependencies. These should be installed automatically as required but
there will no doubt be complications.

Compatibility breaks:

1. Due to lack of support in some of the dependent libraries,
   IMAPClient no longer supports Python 3.2.
2. The passthrough keyword arguments that the IMAPClient constructor
   took in past versions are no longer accepted. These were in place
   to provide access to imaplib's SSL arguments which are no longer
   relevant. Please pass a SSL context object instead.
3. When using the default SSL context that IMAPClient creates
   (recommended), certificate verification is enabled. This means that
   IMAPClient connections to servers that used to work before,
   may fail now (especially if a self-signed certificate is used by
   the server). Refer to the documentation for details of how to
   supply alternate CA certificates or disable verification.
4. There are some new exceptions that might be raised in response to
   network issues or TLS protocol failures. Refer to the
   Exceptions_ section of the manual for more details.

Please refer to the "TLS/SSL" section of the manual for more details
on all of the above.

Many thanks to Chris Arndt and Marc-Antoine Parent for their input
into these TLS improvements.

.. _Exceptions: http://imapclient.readthedocs.io/en/latest/#exceptions

STARTTLS support [NEW]
----------------------
When the server supports it, IMAPClient can now establish an encrypted
connection after initially starting with an unencrypted connection
using the STARTTLS command. The starttls method takes an SSL context
object for controlling the parameters of the TLS negotiation.

Many thanks to Chris Arndt for his extensive initial work on this.

More robust criteria handling for search, sort and thread [API]
---------------------------------------------------------------
IMAPClient's methods that accept search criteria (search, sort,
thread, gmail_search) have been changed to provide take criteria in
a more straightforward and robust way. In addition, the way the
*charset* argument interacts with search criteria has been
improved. These changes make it easier to pass search criteria and
have them handled correctly but unfortunately also mean that small
changes may be required to existing code that uses IMAPClient.

Search criteria
~~~~~~~~~~~~~~~
The preferred way to specify criteria now is as a list of strings,
ints and dates (where relevant). The list should be flat with all the
criteria parts run together. Where a criteria takes an argument, just
provide it as the next element in the list.

Some valid examples::

  c.search(['DELETED'])
  c.search(['NOT', 'DELETED'])
  c.search(['FLAGGED', 'SUBJECT', 'foo', 'BODY', 'hello world'])
  c.search(['NOT', 'DELETED', 'SMALLER', 1000])
  c.search(['SINCE', date(2006, 5, 3)])

IMAPClient will perform all required conversion, quoting and
encoding. Callers do not need to and should not attempt to do this
themselves. IMAPClient will automatically send criteria parts as IMAP
literals when required (i.e. when the encoded part is 8-bit).

Some previously accepted ways of passing search criteria will not work
as they did in previous versions of IMAPClient. Small changes will be
required in these cases.  Here are some examples of how to update code
written against older versions of IMAPClient::

  c.search(['NOT DELETED'])    # Before
  c.search(['NOT', 'DELETED']) # After

  c.search(['TEXT "foo"'])     # Before
  c.search(['TEXT', 'foo'])    # After (IMAPClient will add the quotes)

  c.search(['DELETED', 'TEXT "foo"'])    # Before
  c.search(['DELETED', 'TEXT', 'foo'])   # After

  c.search(['SMALLER 1000'])    # Before
  c.search(['SMALLER', 1000])   # After

It is also possible to pass a single string as the search
criteria. IMAPClient will not attempt quoting in this case, allowing
the caller to specify search criteria at a lower level. Specifying
criteria using a sequence of strings is preferable however. The
following examples (equivalent to those further above) are valid::

  c.search('DELETED')
  c.search('NOT DELETED')
  c.search('FLAGGED SUBJECT "foo" BODY "hello world"')
  c.search('NOT DELETED SMALLER 1000')
  c.search('SINCE 03-May-2006')

Search charset
~~~~~~~~~~~~~~
The way that the search *charset* argument is handled has also
changed.

Any unicode criteria arguments will now be encoded by IMAPClient using
the supplied charset. The charset must refer to an encoding that is
capable of handling the criteria's characters or an error will
occur. The charset must obviously also be one that the server
supports! (UTF-8 is common)

Any criteria given as bytes will not be changed by IMAPClient, but the
provided charset will still be passed to the IMAP server. This allows
already encoding criteria to be passed through as-is. The encoding
referred to by *charset* should match the actual encoding used for the
criteria.

The following are valid examples::

  c.search(['TEXT', u'\u263a'], 'utf-8')         # IMAPClient will apply UTF-8 encoding
  c.search([b'TEXT', b'\xe2\x98\xba'], 'utf-8')  # Caller has already applied UTF-8 encoding

The documentation and tests for search, gmail_search, sort and thread
has updated to account for these changes and have also been generally
improved.

Socket timeout support [NEW]
----------------------------
IMAPClient now accepts a timeout at creation time. The timeout applies
while establishing the connection and for all operations on the socket
connected to the IMAP server.

Semantic versioning
-------------------
In order to better indicate version compatibility to users, IMAPClient
will now strictly adhere to the `Semantic Versioning
<http://semver.org>`_ scheme.

Performance optimisation for parsing message id lists
-----------------------------------------------------
A short circuit is now used when parsing a list of message ids which
greatly speeds up parsing time.

Other
-----
  * Perform quoting of Gmail labels. Thanks to Pawel Sz for the fix.
  * The type of the various flag constants was fixed. Thanks to Thomi
    Richards for pointing this out.
  * Now using mock 1.3.0. Thanks to Thomi Richards for the patch.
  * Fixed handling of very long numeric only folder names. Thanks to
    Paweł Gorzelany for the patch.
  * The default charset for gmail_search is now UTF-8. This makes it
    easier to use any unicode string as a search string and is safe
    because Gmail supports UTF-8 search criteria.
  * PEP8 compliance fixed (except for some occasional long lines)
  * Added a "shutdown" method.
  * The embedded six package has been removed in favour of using an
    externally installed instance.
  * Fixed handling of literals in STATUS responses.
  * Only use the untagged post-login CAPABILITY response once (if sent
    by server).
  * Release history made part of the main documentation.
  * Clarified how message ids work in the docs.
  * Livetest infrastructure now works with Yahoo's OAUTH2
  * Fixed bytes handling in Address.__str__

==============
 Version 0.13
==============

Added support for the ID command [NEW]
--------------------------------------
As per RFC2971. Thanks to Eben Freeman from Nylas.

Fix exception with NIL address in envelope address list
-------------------------------------------------------
Thanks to Thomas Steinacher for this fix.

Fixed handling of NIL in SEARCH response
----------------------------------------
Fixed a regression in the handling of NIL/None SEARCH
responses. Thanks again to Thomas Steinacher.

Date parsing fixes
------------------
Don't traceback when an unparsable date is seen in ENVELOPE
responses. None is returned instead.

Support quirky timestamp strings which use dots for the time
separator.

Removed horrible INTERNALDATE parsing code (use parse_to_datetime
instead).

datetime_to_imap has been moved to the datetime_util module and is now
called datetime_to_INTERNALDATE. This will only affect you in the
unlikely case that you were importing this function out of the
IMAPClient package.

Other
-----
  * The docs for various IMAPClient methods, and the HACKING.rst file
    have been updated.
  * CONDSTORE live test is now more reliable (especially when running
    against Gmail)

==============
 Version 0.12
==============

Fixed unicode handling [API CHANGE]
-----------------------------------
During the work to support Python 3, IMAPClient was changed to do
return unicode for most responses. This was a bad decision, especially
because it effectively breaks content that uses multiple encodings
(e.g. RFC822 responses). This release includes major changes so that
most responses are returned as bytes (Python 3) or str (Python
2). This means that correct handling of response data is now possible
by code using IMAPClient.

Folder name handling has also been cleaned up as part of this work. If
the ``folder_encode`` attribute is ``True`` (the default) then folder
names will **always** be returned as unicode. If ``folder_encode`` is
False then folder names will always be returned as bytes/strs.

Code using IMAPClient will most likely need to be updated to account
these unicode handling changes.

Many thanks to Inbox (now Nilas, https://nilas.com/) for sponsoring this
work.

Extra __init__ keyword args are passed through [NEW]
----------------------------------------------------
Any unused keyword arguments passed to the IMAPClient initialiser will
now be passed through to the underlying imaplib IMAP4, IMAP4_SSL or
IMAP4_stream class. This is specifically to allow the use of imaplib
features that control certificate validation (if available with the
version of Python being used).

Thanks to Chris Arndt for this change.

MODSEQ parts in SEARCH responses are now handled
------------------------------------------------
If the CONDSTORE extension is supported by a server and a MODSEQ
criteria was used with search(), a TypeError could occur. This has now
been fixed and the MODSEQ value returned by the server is now
available via an attribute on the returned list of ids.

Minor Changes
-------------
* Small tweaks to support Python 3.4.
* The deprecated get_folder_delimiter() method has been removed.
* More control over OAUTH2 parameters. Thanks to Phil Peterson for
  this.
* Fixed livetest/interact OAUTH handling under Python 3.

================
 Version 0.11.1
================

* Close folders during livetest cleanup so that livetests work with
  newer Dovecot servers (#131)

==============
 Version 0.11
==============

Support for raw Gmail searching [NEW]
-------------------------------------
The new gmail_search methods allows direct Gmail queries using the
X-GM-RAW search extension. Thanks to John Louis del Rosario for the
patch.

ENVELOPE FETCH response parsing [NEW, API CHANGE]
-------------------------------------------------
ENVELOPE FETCH responses are now returned as Envelope instances. These
objects are namedtuples providing convenient attribute and positional
based access to envelope fields. The Date field is also now converted
to a datetime instance.

As part of this change various date and time related utilities were
moved to a new module at imapclient.datetime_util.

Thanks to Naveen Nathan for the work on this feature.

Correct nested BODYSTRUCTURE handling [API CHANGE]
--------------------------------------------------
BODY and BODYSTRUCTURE responses are now processed recusively so
multipart sections within other multipart sections are returned
correctly. This also means that each the part of the response now has
a is_multipart property available.

NOTE: code that expects the old (broken) behaviour will need to be
updated.

Thanks to Brandon Rhodes for the bug report.

SELECT response bug fix
-----------------------
Handle square brackets in flags returned in SELECT response.
Previously these would cause parsing errors. Thanks to Benjamin
Morrise for the bug report.

Minor Changes
-------------
Copyright date update for 2014.


================
 Version 0.10.2
================

Switch back to setuptools now that distribute and setuptools have
merged back. Some users were reporting problems with distribute and
the newer versions of setuptools.

================
 Version 0.10.1
================

Fixed regressions in several cases when binary data (i.e. normal
strings under Python 2) are used as arguments to some methods. Also
refactored input normalisation functions somewhat.

Fixed buggy method for extracting flags and Gmail labels from STORE
responses.

==============
 Version 0.10
==============

Python 3 support (#22) [API CHANGE]
-----------------------------------
Python 3.2 and 3.3 are now officially supported. This release also
means that Python versions older than 2.6 are no longer supported.

A single source approach has been used, with no conversion step required.

A big thank you to Mathieu Agopian for his massive contribution to
getting the Python 3 port finished. His changes and ideas feature
heavily in this release.

**IMPORTANT**: Under Python 2, all strings returned by IMAPClient are now
returned as unicode objects. With the exception of folder names, these
unicode objects will only contain characters in the ASCII range so
this shouldn't break existing code, however there is always a chance
that there will be a problem. Please test your existing applications
thoroughly with this verison of IMAPClient before deploying to
production situations.

Minor Changes
-------------
* "python setup.py test" now runs the unit tests
* Mock library is now longer included (listed as external test dependency)
* live tests that aren't UID related are now only run once
* live tests now perform far less logins to the server under test
* Unit tests can now be run for all supported Python versions using ``tox``.
* Improved documentation regarding working on the project.
* Many documentation fixes and improvements.

Minor Bug Fixes
---------------
* HIGHESTMODSEQ in SELECT response is now parsed correctly
* Fixed daylight saving handling in FixedOffset class
* Fixed --port command line bug in imapclient.interact when SSL
  connections are made.

===============
 Version 0.9.2
===============

THREAD support [NEW]
--------------------
The IMAP THREAD command is now supported. Thanks to Lukasz Mierzwa for
the patches.

Enhanced capability querying [NEW]
----------------------------------
Previously only the pre-authentication server capabilities were
returned by the capabilities() method. Now, if the connection is
authenticated, the post-authentication capabilities will be returned.
If the server sent an untagged CAPABILITY response after authentication,
that will be used, avoiding an unnecessary CAPABILITY command call.

All this ensures that the client sees all available server
capabilities.

Minor Features
--------------
* Better documentation for contributers (see HACKING file)
* Copyright date update for 2013.

===============
 Version 0.9.1
===============

Stream support [NEW]
--------------------
It is now possible to have IMAPClient run an external command to
establish a connection to the IMAP server via a new *stream* keyword
argument to the initialiser. This is useful for exotic connection or
authentication setups. The *host* argument is used as the command to
run.

Thanks to Dave Eckhardt for the original patch.

OAUTH2 Support [NEW]
--------------------
OAUTH2 authentication (as supported by Gmail's IMAP) is now available
via the new oauth2_login method. Thanks to Zac Witte for the original
patch.

livetest now handles Gmail's new message handling
-------------------------------------------------
Gmail's IMAP implementation recently started requiring a NOOP command
before new messages become visible after delivery or an APPEND. The
livetest suite has been updated to deal with this.

=============
 Version 0.9
=============

Gmail Label Support
-------------------
New methods have been added for interacting with Gmail's label API:
get_gmail_labels, add_gmail_labels, set_gmail_labels,
remove_gmail_labels. Thanks to Brian Neal for the patches.

Removed Code Duplication (#9)
-----------------------------
A signficant amount of duplicated code has been removed by abstracting
out common command handling code. This will make the Python 3 port and
future maintenance easier.

livetest can now be run against non-dummy accounts (#108)
---------------------------------------------------------
Up until this release the tests in imapclient.livetest could only be
run against a dummy IMAP account (all data in the account would be
lost during testing). The tests are now limited to a sub-folder
created by the tests so it is ok to run them against an account that
contains real messages. These messages will be left alone.

Minor Features
--------------
* Don't traceback when an IMAP server returns a all-digit folder name
  without quotes. Thanks to Rhett Garber for the bug report. (#107)
* More tests for ACL related methods (#89)
* More tests for namespace()
* Added test for read-only select_folder()

Minor Bug Fixes
---------------
* Fixed rename live test so that it uses folder namespaces (#100).
* Parse STATUS responses robustly - fixes folder_status() with MS
  Exchange.
* Numerous livetest fixes to work around oddities with the MS
  Exchange IMAP implementation.

===============
 Version 0.8.1
===============

* IMAPClient wasn't installing on Windows due to an extra trailing
  slash in MANIFEST.in (#102). This is a bug in distutils.
* MANIFEST.in was fixed so that the main documentation index file
  is included the source distribution.
* distribute_setup.py was updated to the 0.6.24 version.
* This release also contains some small documentation fixes.

=============
 Version 0.8
=============

OAUTH Support (#54) [NEW]
-------------------------
OAUTH authentication is now supported using the oauth_login
method. This requires the 3rd party oauth2 package is
installed. Thanks to Johannes Heckel for contributing the patch to
this.

IDLE Support (#50) [NEW]
------------------------
The IDLE extension is now supported through the new idle(),
idle_check() and idle_done() methods. See the example in
imapclient/examples/idle_example.py.

NOOP Support (#74) [NEW]
------------------------
The NOOP command is now supported. It returns parsed untagged server
responses in the same format as idle_check() and idle_done().

Sphinx Based Docs (#5) [NEW]
----------------------------
Full documentation is now available under doc/html in the source
distribution and at http://imapclient.readthedocs.io/ online.

Added rename_folder (#77) [NEW] 
--------------------------------
Renaming of folders was an obvious omission!

Minor Features
--------------
* interact.py can now read livetest.py INI files (#66)
* interact.py can now embed shells from ipython 0.10 and 0.11 (#98)
* interact.py and livetest.py are now inside the imapclient package so
  they can be used even when IMAClient has been installed from PyPI
  (#82)
* Added "debug" propety and setting of a log file (#90)
* "normalise_times" attribute allows caller to select whether
  datetimes returned by fetch() are native or not (#96) (Thanks Andrew
  Scheller)
* Added imapclient.version_info - a tuple that contains the IMAPClient
  version number broken down into it's parts.

Minor Bug Fixes
---------------
* getacl() was using wrong lexing class (#85) (Thanks josephhh)
* Removed special handling for response tuples without whitespace
  between them.  Post-process BODY/BODYSTRUCTURE responses
  instead. This should not affect the external API. (#91) (Thanks
  daishi)
* Fix incorrect msg_id for UID fetch when use_uid is False (#99)

=============
 Version 0.7
=============

BODY and BODYSTRUCTURE parsing fixes (#58) [API CHANGE]
-------------------------------------------------------
The response values for BODY and BODYSTRUCTURE responses may include a
sequence of tuples which are not separated by whitespace. These should
be treated as a single item (a list of multiple arbitrarily nested
tuples) but IMAPClient was treating them as separate items. IMAPClient
now returns these tuples in a list to allow for consistent parsing.

A BODYSTRUCTURE response for a multipart email with 2 parts would have
previously looked something like this::

  (('text', 'html', ('charset', 'us-ascii'), None, None, 'quoted-printable', 55, 3),
   ('text', 'plain', ('charset', 'us-ascii'), None, None, '7bit', 26, 1), 
   'mixed', ('boundary', '===============1534046211=='))

The response is now returned like this::

  ([
     ('text', 'html', ('charset', 'us-ascii'), None, None, 'quoted-printable', 55, 3),
     ('text', 'plain', ('charset', 'us-ascii'), None, None, '7bit', 26, 1) 
   ], 
   'mixed', ('boundary', '===============1534046211=='))

The behaviour for single part messages is unchanged. In this case the
first element of the tuple is a string specifying the major content
type of the message (eg "text"). 

An is_multipart boolean property now exists on BODY and BODYSTRUCTURE
responses to allow the caller to easily determine whether the response
is for a multipart message.

Code that expects the previous response handling behaviour needs to be
updated.

Live tests converted to use unittest2 (#4)
------------------------------------------
livetest.py now uses the unittest2 package to run the tests. This
provides much more flexibility that the custom approach that was used
before. Dependencies between tests are gone - each test uses a fresh
IMAP connection and is preceeded by the same setup.

unittest2.main() is used to provide a number of useful command line
options and the ability to run a subset of tests.

IMAP account parameters are now read using a configuration file
instead of command line arguments. See livetest-sample.ini for an
example.

Added NAMESPACE support (#63) [API CHANGE]
------------------------------------------
namespace() method added and get_folder_delimiter() has been
deprecated.

Added support for FETCH modifiers (#62) [NEW]
---------------------------------------------
The fetch method now takes optional modifiers as the last
argument. These are required for extensions such as RFC 4551
(conditional store). Thanks to Thomas Jost for the patch.

===============
 Version 0.6.2
===============

Square brackets in responses now parsed correctly (#55)
-------------------------------------------------------
This fixes response handling for FETCH items such as 
``BODY[HEADER.FIELDS (from subject)]``.

Example moved (#56)
-------------------
The example has been moved to imapclient/examples directory and is
included when the IMAPClient is installed from PyPI.

Distribute (#57)
----------------
The project is now packaged using Distribute instead of
setuptools. There should be no real functional change.

===============
 Version 0.6.1
===============

Python SSL bug patch
--------------------
Automatically patch a bug in imaplib which can cause hangs when using
SSL (Python Issue 5949). The patch is only applied when the running
Python version is known to be affected by the problem.

Doc update
----------
Updated the README to better reflect the current state of the project.

=============
 Version 0.6
=============

New response parser (#1, #45)
-----------------------------
Command response lexing and parsing code rewritten from stratch to
deal with various bugs that surfaced when dealing with more complex
responses (eg. BODYSTRUCTURE and ENVELOPE). This change also fixes
various problems when interacting with Gmail and MS Exchange. 

XLIST extension support (#25) [NEW]
-----------------------------------
Where the server supports it, xlist_folders() will return a mapping of
various common folder names to the actual server folder names. Gmail's
IMAP server supports this.

Added COPY command support (#36) [NEW]
--------------------------------------
New copy() method.
 
Added interact.py [NEW]
-----------------------
A script for interactive IMAPClient sessions. Useful for debugging and
exploration. Uses IPython if installed.

Full SELECT response (#24) [API CHANGE]
---------------------------------------
select_folder() now returns a dictionary with the full (parsed) SELECT
command response instead of just the message count.

Full list responses (#24) [API CHANGE]
--------------------------------------
The return value from list_folders(), list_sub_folders() and
xlist_folders() now include the IMAP folder flags and delimiter.

Folder name character encoding (#21) [API CHANGE]
-------------------------------------------------
Bytes that are greater than 0x7f in folder names are will cause an
exception when passed to methods that accept folder name arguments
because there is no unambigous way to handle these. Callers should
encode such folder names to unicode objects first.

Folder names are now always returned as unicode objects.

Message sequence number now always returned in FETCH responses
--------------------------------------------------------------
Fetch responses now include a "SEQ" element which gives the message
(non-UID) sequence number. This allows for easy mapping between UIDs
and standard sequence IDs.

Folder name handling fixes (#28, #42)
-------------------------------------
Various folder name handling bugs fixed.


===============
 Version 0.5.2
===============

Folder name quoting and escaping fixes (#28)
--------------------------------------------
Correctly handle double quotes and backslashes in folder names when
parsing LIST and LSUB responses.

Fixed fetch literal handling (#33)
----------------------------------
Fixed problem with parsing responses where a literal followed another
literal.


===============
 Version 0.5.1
===============

License change
--------------
Changed license from GPL to new BSD.

=============
 Version 0.5
=============

SSL support
-----------
Support for SSL based connections by passing ssl=True when
constructing an IMAPClient instance.

Transparent folder encoding
---------------------------
Folder names are now encoded and decoded transparently if required
(using modified UTF-7). This means that any methods that return folder
names may return unicode objects as well as normal strings [API
CHANGE]. Additionally, any method that takes a folder name now accepts
unicode object too. Use the folder_encode attribute to control whether
encode/decoding is performed.

Unquoted folder name handling fix
---------------------------------
Unquoted folder names in server responses are now handled
correctly. Thanks to Neil Martinsen-Burrell for reporting this bug.

Fixed handling of unusual characters in folder names
----------------------------------------------------
Fixed a bug with handling of unusual characters in folder names.

Timezone handling [API CHANGE]
------------------------------
Timezones are now handled correctly for datetimes passed as input and for
server responses. This fixes a number of bugs with timezones. Returned
datetimes are always in the client's local timezone.

More unit tests
---------------
Many more unit tests added, some using Michael Foord's excellent
mock.py.  (http://www.voidspace.org.uk/python/mock/)



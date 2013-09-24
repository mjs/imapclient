======
 0.11
======

Support for raw Gmail searching [NEW]
-------------------------------------
The new gmail_search methods allows direct Gmail queries using the
X-GM-RAW search extension. Thanks to John Louis del Rosario for the
patch.

SELECT response bug fix
-----------------------
Handle square brackets in flags returned in SELECT
response. Previously these would cause parsing errors. Thanks to
Benjamin Morrise for the bug report.

========
 0.10.2
========

Switch back to setuptools now that distribute and setuptools have
merged back. Some users were reporting problems with distribute and
the newer versions of setuptools.

========
 0.10.1
========

Fixed regressions in several cases when binary data (i.e. normal
strings under Python 2) are used as arguments to some methods. Also
refactored input normalisation functions somewhat.

Fixed buggy method for extracting flags and Gmail labels from STORE
responses.

======
 0.10
======

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

=======
 0.9.2
=======

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

=======
 0.9.1
=======

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

=====
 0.9
=====

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

=======
 0.8.1
=======

* IMAPClient wasn't installing on Windows due to an extra trailing
  slash in MANIFEST.in (#102). This is a bug in distutils.
* MANIFEST.in was fixed so that the main documentation index file
  is included the source distribution.
* distribute_setup.py was updated to the 0.6.24 version.
* This release also contains some small documentation fixes.

=====
 0.8
=====

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
distribution and at http://imapclient.readthedocs.org/ online.

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



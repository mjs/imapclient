IMAPClient Class
~~~~~~~~~~~~~~~~
The primary class used by the imapclient package is the IMAPClient
class. All interaction with a remote IMAP server is performed via an
IMAPClient instance.

.. autoclass:: imapclient.IMAPClient
   :members:

.. autoclass:: imapclient.SocketTimeout
   :members:

Fetch Response Types
~~~~~~~~~~~~~~~~~~~~
Various types may be used in the data structures returned by
:py:meth:`.IMAPClient.fetch` when certain response types
are encountered during parsing.

.. automodule:: imapclient.response_types
   :members:

Exceptions
~~~~~~~~~~
IMAPClient wraps exceptions raised by imaplib to ease the error handling.
All the exceptions related to IMAP errors are defined in the module
`imapclient.exceptions`. The following general exceptions may be raised:

* IMAPClientError: the base class for IMAPClient's exceptions and the
  most commonly used error.
* IMAPClientAbortError: raised if a serious error has occurred that
  means the IMAP connection is no longer usable. The connection should
  be dropped without logout if this occurs.
* IMAPClientReadOnlyError: raised if a modifying operation was
  attempted on a read-only folder.


More specific exceptions existed for common known errors:

.. automodule:: imapclient.exceptions
    :members:


Exceptions from lower layers are possible, such as networks error or unicode
malformed exception. In particular:

* socket.error
* socket.timeout: raised if a timeout was specified when creating the
  IMAPClient instance and a network operation takes too long.
* ssl.SSLError: the base class for network or SSL protocol errors when 
  ``ssl=True`` or ``starttls()`` is used.
* ssl.CertificateError: raised when TLS certification
  verification fails. This is *not* a subclass of SSLError.

Utilities
~~~~~~~~~
.. automodule:: imapclient.testable_imapclient
   :members:

TLS Support
~~~~~~~~~~~

.. automodule:: imapclient.tls
   :members:

Thread Safety
~~~~~~~~~~~~~
Instances of IMAPClient are NOT thread safe. They should not be shared and
accessed concurrently from multiple threads.

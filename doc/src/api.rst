IMAPClient Class
~~~~~~~~~~~~~~~~
The primary class used by the imapclient package is the IMAPClient
class. All interaction with a remote IMAP server is performed via an
IMAPClient instance.

.. autoclass:: imapclient.IMAPClient
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
The following exceptions may be raised by IMAPClient directly. They
are attached to the IMAPClient class.

* IMAPClient.Error: the base class for IMAPClient's exceptions and the
  most commonly used error.
* IMAPClient.AbortError: raised if a serious error has occurred that
  means the IMAP connection is no longer usable. The connection should
  be dropped without logout if this occurs.
* IMAPClient.ReadOnlyError: raised if a modifying operation was
  attempted on a read-only folder.

Exceptions from lower network layers are also possible, in particular:

* socket.error
* socket.timeout: raised if a timeout was specified when creating the
  IMAPClient instance and a network operation takes too long.
* backports.ssl.SSLError: the base class for network or SSL protocol
  errors when ssl=True or starttls() is used.
* backports.ssl.CertificateError: raised when TLS certification
  verification fails. This is *not* a subclass of SSLError.


TLS Support
~~~~~~~~~~~

.. automodule:: imapclient.tls
   :members:
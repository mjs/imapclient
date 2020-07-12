
# Base class allowing to catch any IMAPClient related exceptions
class IMAPClientError(RuntimeError):
    pass


class IMAPClientAbortError(IMAPClientError):
    # Service errors - close and retry
    pass


class IMAPClientReadOnlyError(IMAPClientError):
    # Mailbox status changed to READ-ONLY
    pass


class CapabilityError(IMAPClientError):
    """ 
    The command tried by the user needs a capability not installed 
    on the IMAP server
    """


class LoginError(IMAPClientError):
    """
    A connection has been established with the server but an error 
    occurred during the authentication.
    """


class IllegalStateError(IMAPClientError):
    """
    The command tried needs a different state to be executed. This
    means the user is not logged in or the command needs a folder to
    be selected.
    """


class InvalidCriteriaError(IMAPClientError):
    """ 
    A command using a search criteria failed, probably due to a syntax 
    error in the criteria string.
    """


class ProtocolError(IMAPClientError):
    """The server replied with a response that violates the IMAP protocol."""

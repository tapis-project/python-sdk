class BaseTapyException(Exception):
    """
    Base Tapy error class. All Error types should descend from this class.
    """
    def __init__(self, msg=None, response=None):
        """
        Create a new TapisError object.
        :param msg: (str) A helpful string
        :param response: (requests.Response) The HTTP response object from the request.
        """
        self.msg = msg
        self.response = response


class TapyClientNotImplementedError(BaseTapyException):
    """The Tapy client has not implemented the requested functionality yet."""
    pass


class TapyClientConfigurationError(BaseTapyException):
    """The Tapy client was improperly configured."""
    pass


class TokenInvalidError(BaseTapyException):
    """Error indicating the token on the request was invalid."""
    pass


class NotAuthorizedError(BaseTapyException):
    """Error indicating the user is not authorized for the request."""
    pass


class InvalidInputError(BaseTapyException):
    """The input provided to the function was not valid."""
    pass


class ServerDownError(BaseTapyException):
    """Tapy got an error trying to communication with the Tapis server."""
    pass


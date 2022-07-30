class EntryNotFoundError(ValueError):
    """Exception class to raise if error returned from request points to entry not being found.
    """
    pass

class ForbiddenError(BaseException):
    """Exception class to raise when an invalid API key is provided for a request.
    """
    pass

class LimitExceededError(BaseException):
    """Exception class to raise when request limit has been reached for the API key.
    """
    pass

class RequestValueError(ValueError):
    """Exception class to raise when an invalid value is provided for a request parameter.
    """
    pass

class RequestError(BaseException):
    """Exception class to raise when the response code is not 200.
    """
    pass

class WaitInterruptedError(BaseException):
    """Exception class to raise when a segmented wait is interrupted.
    """
    pass

class TooManyRequestsError(BaseException):
    """Exception class to raise when too many requests are performed.
    """
    pass
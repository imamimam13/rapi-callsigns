class RapiCallsignError(Exception):
    """Base error for package."""
    pass


class InvalidCallsignError(RapiCallsignError):
    pass


class FetchError(RapiCallsignError):
    pass
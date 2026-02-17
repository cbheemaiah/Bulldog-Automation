class MauticError(Exception):
    pass

class MauticAuthError(MauticError):
    pass

class MauticConnectionError(MauticError):
    pass

class MauticAPIError(MauticError):
    def __init__(self, message: str, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
class APIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_type: str,
        error_code: str,
        error_message: str,
    ):
        super().__init__(error_message)
        self.status_code = status_code
        self.error_type = error_type
        self.error_code = error_code
        self.error_message = error_message


class BadRequestError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=400,
            error_type="INVALID_REQUEST",
            error_code=error_code,
            error_message=error_message,
        )


class AuthenticationError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=401,
            error_type="AUTHENTICATION_ERROR",
            error_code=error_code,
            error_message=error_message,
        )


class PermissionError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=403,
            error_type="PERMISSION_ERROR",
            error_code=error_code,
            error_message=error_message,
        )


class NotFoundAPIError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=404,
            error_type="INVALID_REQUEST",
            error_code=error_code,
            error_message=error_message,
        )


class ConflictAPIError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=409,
            error_type="INVALID_REQUEST",
            error_code=error_code,
            error_message=error_message,
        )


class ProviderAPIError(APIError):
    def __init__(self, *, error_code: str, error_message: str):
        super().__init__(
            status_code=502,
            error_type="API_ERROR",
            error_code=error_code,
            error_message=error_message,
        )

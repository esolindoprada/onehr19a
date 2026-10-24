class ApiError(Exception):
    """Controlled REST transport error with stable machine-readable code."""

    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status = int(status)
        self.code = code
        self.message = message
        self.details = details or {}


class AuthenticationError(ApiError):
    def __init__(self, message="Invalid or inactive API credential."):
        super().__init__(401, "authentication_failed", message)


class AuthorizationError(ApiError):
    def __init__(self, message="The API credential does not grant this operation."):
        super().__init__(403, "scope_forbidden", message)


class RateLimitError(ApiError):
    def __init__(self, retry_after=60):
        super().__init__(429, "rate_limited", "API rate limit exceeded.", {"retry_after": retry_after})


class CapabilityUnavailable(ApiError):
    def __init__(self, capability):
        super().__init__(501, "capability_unavailable", f"OneHR capability is not installed or not available: {capability}")


class PayloadError(ApiError):
    def __init__(self, message, details=None):
        super().__init__(400, "invalid_payload", message, details)


class ReplayError(ApiError):
    def __init__(self, message="The request ID has already been used for this integration identity."):
        super().__init__(409, "replay_detected", message)

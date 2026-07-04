from typing import Any


class AppServiceError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Internal error."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details


class ServiceError(AppServiceError):
    pass


class UnauthorizedError(ServiceError):
    status_code = 401
    code = "unauthorized"
    message = "Unauthorized."


class MissingAuthorizationError(UnauthorizedError):
    code = "missing_authorization"
    message = "Missing Authorization header."


class InvalidAccessTokenError(UnauthorizedError):
    code = "invalid_access_token"
    message = "Invalid access token."


class ExpiredAccessTokenError(UnauthorizedError):
    code = "expired_access_token"
    message = "Access token has expired."


class MissingRefreshTokenError(UnauthorizedError):
    code = "missing_refresh_token"
    message = "Missing refresh token."


class InvalidRefreshTokenError(UnauthorizedError):
    code = "invalid_refresh_token"
    message = "Invalid refresh token."


class ExpiredRefreshTokenError(UnauthorizedError):
    code = "expired_refresh_token"
    message = "Refresh token has expired."


class RevokedRefreshTokenError(UnauthorizedError):
    code = "revoked_refresh_token"
    message = "Refresh token has been revoked."


class UserNotFoundError(ServiceError):
    status_code = 404
    code = "user_not_found"
    message = "User was not found."


class ForbiddenError(ServiceError):
    status_code = 403
    code = "forbidden"
    message = "Forbidden."


class ServiceNotReadyError(ServiceError):
    status_code = 503
    code = "service_not_ready"
    message = "Service is not ready."


# app/business/errors.py


class BusinessError(AppServiceError):
    pass


class InvalidInitDataError(BusinessError):
    status_code = 400
    code = "invalid_init_data"
    message = "Invalid Telegram init data."


class InvalidTelegramSignatureError(BusinessError):
    status_code = 403
    code = "invalid_telegram_signature"
    message = "Invalid Telegram init data signature."


class ExpiredInitDataError(BusinessError):
    status_code = 403
    code = "expired_init_data"
    message = "Telegram init data has expired."


class InitDataReplayError(BusinessError):
    status_code = 403
    code = "init_data_replay_detected"
    message = "Telegram init data was already used."


class RefreshReuseDetectedError(BusinessError):
    status_code = 403
    code = "refresh_reuse_detected"
    message = "Refresh token reuse detected."

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
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


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


class ItemNotFoundError(ServiceError):
    status_code = 404
    code = "item_not_found"
    message = "Item was not found."


class SecretNotFoundError(ServiceError):
    status_code = 404
    code = "secret_not_found"
    message = "Item secret was not found."


class ScanNotFoundError(ServiceError):
    status_code = 404
    code = "scan_not_found"
    message = "Scan was not found."


class ForbiddenError(ServiceError):
    status_code = 403
    code = "forbidden"
    message = "Forbidden."


class ItemNotCollectedError(ForbiddenError):
    code = "item_not_collected"
    message = "Item was not collected."


class ServiceNotReadyError(ServiceError):
    status_code = 503
    code = "service_not_ready"
    message = "Service is not ready."


class MapApiKeyNotConfiguredError(ServiceError):
    status_code = 503
    code = "map_api_key_not_configured"
    message = "Map API key is not configured."


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


class InvalidSecretTokenError(BusinessError):
    status_code = 400
    code = "invalid_secret_token"
    message = "Invalid secret token."


class MissingSecretError(BusinessError):
    status_code = 400
    code = "missing_secret"
    message = "Secret claim is missing."


class InvalidSecretTypeError(BusinessError):
    status_code = 400
    code = "invalid_secret_type"
    message = "Invalid secret token type."


class ValidationConflictError(BusinessError):
    status_code = 409
    code = "validation_conflict"
    message = "Validation conflict."


class RewardAlreadyClaimedError(BusinessError):
    status_code = 409
    code = "reward_already_claimed"
    message = "Reward was already claimed."


class ScanRateLimitedError(BusinessError):
    status_code = 429
    code = "scan_rate_limited"
    message = "Слишком частые запросы на сканирование. Подождите 5 секунд."


class ScanCooldownError(BusinessError):
    status_code = 400
    code = "scan_on_cooldown"
    message = "QR_ON_COOLDOWN"


class OwnStickerScanError(BusinessError):
    status_code = 400
    code = "own_sticker_scan"
    message = "Нельзя сканировать свой собственный стикер"


class StickerNotFoundError(BusinessError):
    status_code = 404
    code = "sticker_not_found"
    message = "Стикер не найден"


class StickerAlreadyExistsError(BusinessError):
    status_code = 400
    code = "sticker_already_exists"
    message = "Стикер уже сгенерирован"


class ShopOperationError(BusinessError):
    status_code = 400
    code = "invalid_shop_operation"


class ShopItemNotFoundError(ShopOperationError):
    status_code = 404
    code = "shop_item_not_found"
    message = "Товар не найден"


class ShopItemAlreadyOwnedError(ShopOperationError):
    code = "shop_item_already_owned"
    message = "Товар уже куплен"


class InsufficientCoinsError(ShopOperationError):
    code = "insufficient_coins"
    message = "Недостаточно монет"


class ItemNotCraftableError(ShopOperationError):
    code = "item_not_craftable"
    message = "Этот товар нельзя скрафтить"


class InvalidFragmentRarityError(ShopOperationError):
    code = "invalid_fragment_rarity"
    message = "Неверная редкость осколков"


class InsufficientFragmentsError(ShopOperationError):
    code = "insufficient_fragments"
    message = "Недостаточно осколков"


class ShopItemNotOwnedError(ShopOperationError):
    code = "shop_item_not_owned"
    message = "Товар не куплен"

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import jwt

from app.core.config import Settings


class TelegramInitDataError(ValueError):
    pass


def validate_telegram_init_data(init_data: str, settings: Settings, now: int | None = None) -> dict[str, object]:
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("Missing Telegram signature")
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise TelegramInitDataError("Invalid Telegram signature")
    auth_date = int(values.get("auth_date", 0))
    current_time = int(time.time()) if now is None else now
    if auth_date <= 0 or current_time - auth_date > 86400:
        raise TelegramInitDataError("Expired Telegram authentication data")
    user = json.loads(values.get("user", "{}"))
    if not isinstance(user, dict) or "id" not in user:
        raise TelegramInitDataError("Telegram user is missing")
    return {"user": user, "auth_date": auth_date}


def create_access_token(telegram_user_id: int, settings: Settings, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    return jwt.encode(
        {"sub": str(telegram_user_id), "iat": issued_at, "exp": issued_at + settings.access_token_minutes * 60},
        settings.jwt_secret,
        algorithm="HS256",
    )

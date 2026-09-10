import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.core.config import Settings
from app.core.security import TelegramInitDataError, validate_telegram_init_data


def make_init_data(settings: Settings, auth_date: int) -> str:
    values = {"auth_date": str(auth_date), "user": json.dumps({"id": 42, "first_name": "Ali"}, separators=(",", ":"))}
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_telegram_init_data_is_validated() -> None:
    settings = Settings(bot_token="test-token", jwt_secret="1234567890123456")
    result = validate_telegram_init_data(make_init_data(settings, 1_700_000_000), settings, now=1_700_000_100)
    assert result["user"] == {"id": 42, "first_name": "Ali"}


def test_telegram_init_data_rejects_bad_signature() -> None:
    settings = Settings(bot_token="test-token", jwt_secret="1234567890123456")
    with pytest.raises(TelegramInitDataError, match="Invalid"):
        validate_telegram_init_data(make_init_data(settings, 1_700_000_000) + "x", settings, now=1_700_000_100)


def test_telegram_init_data_rejects_stale_data() -> None:
    settings = Settings(bot_token="test-token", jwt_secret="1234567890123456")
    with pytest.raises(TelegramInitDataError, match="Expired"):
        validate_telegram_init_data(make_init_data(settings, 1_700_000_000), settings, now=1_700_100_000)

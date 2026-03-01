"""Environment-based configuration loader for StorePay SDK."""

import os

from .types import StorePayConfig


def load_config_from_env() -> StorePayConfig:
    """Load StorePay configuration from environment variables.

    Required environment variables:
        STOREPAY_APP_USERNAME  - OAuth app username.
        STOREPAY_APP_PASSWORD  - OAuth app password.
        STOREPAY_USERNAME      - Basic Auth username.
        STOREPAY_PASSWORD      - Basic Auth password.
        STOREPAY_AUTH_URL      - Auth server URL.
        STOREPAY_BASE_URL      - API base URL.
        STOREPAY_STORE_ID      - Merchant store ID.
        STOREPAY_CALLBACK_URL  - Callback URL for loan notifications.

    Returns:
        A populated StorePayConfig instance.

    Raises:
        ValueError: If any required variable is missing.
    """
    required = [
        ("app_username", "STOREPAY_APP_USERNAME"),
        ("app_password", "STOREPAY_APP_PASSWORD"),
        ("username", "STOREPAY_USERNAME"),
        ("password", "STOREPAY_PASSWORD"),
        ("auth_url", "STOREPAY_AUTH_URL"),
        ("base_url", "STOREPAY_BASE_URL"),
        ("store_id", "STOREPAY_STORE_ID"),
        ("callback_url", "STOREPAY_CALLBACK_URL"),
    ]

    values = {}
    for key, env_var in required:
        value = os.environ.get(env_var)
        if not value:
            raise ValueError(f"Missing environment variable: {env_var}")
        values[key] = value

    return StorePayConfig(**values)

"""Tests for the StorePay payment SDK."""

import os
import time
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio

from mongolian_payment_storepay import (
    AsyncStorePayClient,
    StorePayClient,
    StorePayConfig,
    StorePayError,
    StorePayLoanInput,
    load_config_from_env,
)

# ── Fixtures ──

AUTH_RESPONSE = {
    "access_token": "test-token-abc123",
    "expires_in": 3600,
    "token_type": "bearer",
    "refresh_token": "refresh-abc",
    "scope": "read write",
}


@pytest.fixture
def config() -> StorePayConfig:
    return StorePayConfig(
        app_username="app_user",
        app_password="app_pass",
        username="basic_user",
        password="basic_pass",
        auth_url="https://auth.storepay.test/",
        base_url="https://api.storepay.test/",
        store_id="store-123",
        callback_url="https://example.com/callback",
    )


@pytest.fixture
def loan_input() -> StorePayLoanInput:
    return StorePayLoanInput(
        description="Test order",
        mobile_number="99112233",
        amount=50000.0,
    )


def _mock_auth_response() -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json=AUTH_RESPONSE,
        request=httpx.Request("POST", "https://auth.storepay.test/oauth/token"),
    )


# ============================================================================
# Sync Client Tests
# ============================================================================


class TestStorePayClient:
    """Tests for the synchronous StorePayClient."""

    def test_constructor_strips_trailing_slash(self, config: StorePayConfig) -> None:
        client = StorePayClient(config)
        assert client._auth_url == "https://auth.storepay.test"
        assert client._base_url == "https://api.storepay.test"

    def test_constructor_strips_multiple_trailing_slashes(self) -> None:
        config = StorePayConfig(
            app_username="au",
            app_password="ap",
            username="u",
            password="p",
            auth_url="https://auth.storepay.test///",
            base_url="https://api.storepay.test///",
            store_id="s",
            callback_url="https://example.com/cb",
        )
        client = StorePayClient(config)
        assert client._auth_url == "https://auth.storepay.test"
        assert client._base_url == "https://api.storepay.test"

    def test_constructor_requires_app_username(self) -> None:
        with pytest.raises(ValueError, match="app_username is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="",
                    app_password="ap",
                    username="u",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_app_password(self) -> None:
        with pytest.raises(ValueError, match="app_password is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="",
                    username="u",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_username(self) -> None:
        with pytest.raises(ValueError, match="username is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_password(self) -> None:
        with pytest.raises(ValueError, match="password is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="u",
                    password="",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_auth_url(self) -> None:
        with pytest.raises(ValueError, match="auth_url is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="u",
                    password="p",
                    auth_url="",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_base_url(self) -> None:
        with pytest.raises(ValueError, match="base_url is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="u",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="",
                    store_id="s",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_store_id(self) -> None:
        with pytest.raises(ValueError, match="store_id is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="u",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="",
                    callback_url="https://example.com/cb",
                )
            )

    def test_constructor_requires_callback_url(self) -> None:
        with pytest.raises(ValueError, match="callback_url is required"):
            StorePayClient(
                StorePayConfig(
                    app_username="au",
                    app_password="ap",
                    username="u",
                    password="p",
                    auth_url="https://auth.test",
                    base_url="https://api.test",
                    store_id="s",
                    callback_url="",
                )
            )

    def test_loan_success(
        self, config: StorePayConfig, loan_input: StorePayLoanInput
    ) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={
                "value": 12345,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res]
        ) as mock:
            result = client.loan(loan_input)

            assert mock.call_count == 2

            # Check loan request body
            loan_call = mock.call_args_list[1]
            body = loan_call.kwargs["json"]
            assert body["storeId"] == "store-123"
            assert body["mobileNumber"] == "99112233"
            assert body["description"] == "Test order"
            assert body["amount"] == "50000.00"
            assert body["callbackUrl"] == "https://example.com/callback"

        assert result == 12345

    def test_loan_formats_amount_two_decimals(
        self, config: StorePayConfig
    ) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={"value": 1, "msgList": [], "attrs": None, "status": "Success"},
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res]
        ) as mock:
            client.loan(
                StorePayLoanInput(
                    description="Test",
                    mobile_number="99001122",
                    amount=1000,
                )
            )

            body = mock.call_args_list[1].kwargs["json"]
            assert body["amount"] == "1000.00"

    def test_loan_failure_raises_error(
        self, config: StorePayConfig, loan_input: StorePayLoanInput
    ) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={
                "value": 0,
                "msgList": [{"code": "ERR", "text": "Insufficient funds", "params": ""}],
                "attrs": None,
                "status": "Failed",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res]
        ):
            with pytest.raises(StorePayError, match="Insufficient funds"):
                client.loan(loan_input)

    def test_loan_check_success(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        check_res = httpx.Response(
            status_code=200,
            json={
                "value": True,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "GET", "https://api.storepay.test/merchant/loan/check/12345"
            ),
        )

        client = StorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with patch.object(client._client, "get", return_value=check_res):
                result = client.loan_check("12345")

        assert result is True

    def test_loan_check_failure_raises_error(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        check_res = httpx.Response(
            status_code=200,
            json={
                "value": False,
                "msgList": [{"code": "ERR", "text": "Loan not found", "params": ""}],
                "attrs": None,
                "status": "Failed",
            },
            request=httpx.Request(
                "GET", "https://api.storepay.test/merchant/loan/check/99999"
            ),
        )

        client = StorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with patch.object(client._client, "get", return_value=check_res):
                with pytest.raises(StorePayError, match="Loan not found"):
                    client.loan_check("99999")

    def test_user_possible_amount_success(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        amount_res = httpx.Response(
            status_code=200,
            json={
                "value": 500000.0,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/user/possibleAmount"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, amount_res]
        ) as mock:
            result = client.user_possible_amount("99112233")

            # Check request body
            body = mock.call_args_list[1].kwargs["json"]
            assert body["mobileNumber"] == "99112233"

        assert result == 500000.0

    def test_user_possible_amount_failure(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        amount_res = httpx.Response(
            status_code=200,
            json={
                "value": 0,
                "msgList": [{"code": "ERR", "text": "User not found", "params": ""}],
                "attrs": None,
                "status": "Failed",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/user/possibleAmount"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, amount_res]
        ):
            with pytest.raises(StorePayError, match="User not found"):
                client.user_possible_amount("00000000")

    def test_auth_caches_token(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={"value": 1, "msgList": [], "attrs": None, "status": "Success"},
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        # First call: auth + loan = 2 POSTs
        # Second call: loan only = 1 POST (token cached)
        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res, loan_res]
        ) as mock:
            client.loan(
                StorePayLoanInput(
                    description="first", mobile_number="99001122", amount=100
                )
            )
            client.loan(
                StorePayLoanInput(
                    description="second", mobile_number="99001122", amount=200
                )
            )

            # auth called once + two loan calls = 3 total
            assert mock.call_count == 3

    def test_auth_refreshes_expired_token(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={"value": 1, "msgList": [], "attrs": None, "status": "Success"},
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client,
            "post",
            side_effect=[auth_res, loan_res, auth_res, loan_res],
        ) as mock:
            client.loan(
                StorePayLoanInput(
                    description="first", mobile_number="99001122", amount=100
                )
            )

            # Expire the token
            client._token_expires_at = 0

            client.loan(
                StorePayLoanInput(
                    description="second", mobile_number="99001122", amount=200
                )
            )

            # auth called twice + two loan calls = 4 total
            assert mock.call_count == 4

    def test_auth_http_error(self, config: StorePayConfig) -> None:
        auth_res = httpx.Response(
            status_code=401,
            json={"error": "invalid_credentials"},
            request=httpx.Request("POST", "https://auth.storepay.test/oauth/token"),
        )

        client = StorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with pytest.raises(StorePayError, match="HTTP 401"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

    def test_auth_no_access_token(self, config: StorePayConfig) -> None:
        auth_res = httpx.Response(
            status_code=200,
            json={"expires_in": 3600},
            request=httpx.Request("POST", "https://auth.storepay.test/oauth/token"),
        )

        client = StorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with pytest.raises(StorePayError, match="no access_token"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

    def test_auth_network_error(self, config: StorePayConfig) -> None:
        client = StorePayClient(config)

        with patch.object(
            client._client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(StorePayError, match="Network error"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

    def test_api_http_error(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        error_res = httpx.Response(
            status_code=500,
            json={"error": "Internal Server Error"},
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, error_res]
        ):
            with pytest.raises(StorePayError, match="HTTP 500") as exc_info:
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )
            assert exc_info.value.status_code == 500
            assert exc_info.value.response == {"error": "Internal Server Error"}

    def test_api_network_error(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()

        client = StorePayClient(config)

        with patch.object(
            client._client,
            "post",
            side_effect=[auth_res, httpx.ConnectError("Connection refused")],
        ):
            with pytest.raises(StorePayError, match="Network error"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

    def test_invalid_json_response(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        bad_res = httpx.Response(
            status_code=200,
            content=b"not json",
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, bad_res]
        ):
            with pytest.raises(StorePayError, match="Invalid JSON"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

    def test_close_clears_token(self, config: StorePayConfig) -> None:
        client = StorePayClient(config)
        client._access_token = "some-token"
        client._token_expires_at = time.time() + 3600

        client.close()

        assert client._access_token is None
        assert client._token_expires_at == 0

    def test_context_manager(self, config: StorePayConfig) -> None:
        with StorePayClient(config) as client:
            assert client._base_url == "https://api.storepay.test"

    def test_loan_failure_falls_back_to_status(
        self, config: StorePayConfig
    ) -> None:
        """When msgList is empty, error message falls back to status."""
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={
                "value": 0,
                "msgList": [],
                "attrs": None,
                "status": "Failed",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = StorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res]
        ):
            with pytest.raises(StorePayError, match="Failed"):
                client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )


# ============================================================================
# Async Client Tests
# ============================================================================


class TestAsyncStorePayClient:
    """Tests for the asynchronous AsyncStorePayClient."""

    @pytest.mark.asyncio
    async def test_loan_success(
        self, config: StorePayConfig, loan_input: StorePayLoanInput
    ) -> None:
        auth_res = _mock_auth_response()
        loan_res = httpx.Response(
            status_code=200,
            json={
                "value": 67890,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = AsyncStorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, loan_res]
        ) as mock:
            result = await client.loan(loan_input)

            body = mock.call_args_list[1].kwargs["json"]
            assert body["amount"] == "50000.00"

        assert result == 67890

        await client.close()

    @pytest.mark.asyncio
    async def test_loan_check_success(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        check_res = httpx.Response(
            status_code=200,
            json={
                "value": True,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "GET", "https://api.storepay.test/merchant/loan/check/67890"
            ),
        )

        client = AsyncStorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with patch.object(client._client, "get", return_value=check_res):
                result = await client.loan_check("67890")

        assert result is True

        await client.close()

    @pytest.mark.asyncio
    async def test_loan_check_failure(self, config: StorePayConfig) -> None:
        auth_res = _mock_auth_response()
        check_res = httpx.Response(
            status_code=200,
            json={
                "value": False,
                "msgList": [{"code": "ERR", "text": "Not found", "params": ""}],
                "attrs": None,
                "status": "Failed",
            },
            request=httpx.Request(
                "GET", "https://api.storepay.test/merchant/loan/check/00000"
            ),
        )

        client = AsyncStorePayClient(config)

        with patch.object(client._client, "post", return_value=auth_res):
            with patch.object(client._client, "get", return_value=check_res):
                with pytest.raises(StorePayError, match="Not found"):
                    await client.loan_check("00000")

        await client.close()

    @pytest.mark.asyncio
    async def test_user_possible_amount_success(
        self, config: StorePayConfig
    ) -> None:
        auth_res = _mock_auth_response()
        amount_res = httpx.Response(
            status_code=200,
            json={
                "value": 250000.0,
                "msgList": [],
                "attrs": None,
                "status": "Success",
            },
            request=httpx.Request(
                "POST", "https://api.storepay.test/user/possibleAmount"
            ),
        )

        client = AsyncStorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, amount_res]
        ):
            result = await client.user_possible_amount("99112233")

        assert result == 250000.0

        await client.close()

    @pytest.mark.asyncio
    async def test_http_error_raises_storepay_error(
        self, config: StorePayConfig
    ) -> None:
        auth_res = _mock_auth_response()
        error_res = httpx.Response(
            status_code=403,
            json={"error": "Forbidden"},
            request=httpx.Request(
                "POST", "https://api.storepay.test/merchant/loan"
            ),
        )

        client = AsyncStorePayClient(config)

        with patch.object(
            client._client, "post", side_effect=[auth_res, error_res]
        ):
            with pytest.raises(StorePayError, match="HTTP 403"):
                await client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

        await client.close()

    @pytest.mark.asyncio
    async def test_network_error_raises_storepay_error(
        self, config: StorePayConfig
    ) -> None:
        client = AsyncStorePayClient(config)

        with patch.object(
            client._client,
            "post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(StorePayError, match="Network error"):
                await client.loan(
                    StorePayLoanInput(
                        description="test", mobile_number="99001122", amount=100
                    )
                )

        await client.close()

    @pytest.mark.asyncio
    async def test_async_context_manager(self, config: StorePayConfig) -> None:
        async with AsyncStorePayClient(config) as client:
            assert client._base_url == "https://api.storepay.test"

    @pytest.mark.asyncio
    async def test_close_clears_token(self, config: StorePayConfig) -> None:
        client = AsyncStorePayClient(config)
        client._access_token = "some-token"
        client._token_expires_at = time.time() + 3600

        await client.close()

        assert client._access_token is None
        assert client._token_expires_at == 0


# ============================================================================
# Config Tests
# ============================================================================


class TestLoadConfigFromEnv:
    """Tests for load_config_from_env."""

    def test_loads_all_env_vars(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "app_user",
            "STOREPAY_APP_PASSWORD": "app_pass",
            "STOREPAY_USERNAME": "user",
            "STOREPAY_PASSWORD": "pass",
            "STOREPAY_AUTH_URL": "https://auth.storepay.test",
            "STOREPAY_BASE_URL": "https://api.storepay.test",
            "STOREPAY_STORE_ID": "store-123",
            "STOREPAY_CALLBACK_URL": "https://example.com/callback",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = load_config_from_env()

        assert cfg.app_username == "app_user"
        assert cfg.app_password == "app_pass"
        assert cfg.username == "user"
        assert cfg.password == "pass"
        assert cfg.auth_url == "https://auth.storepay.test"
        assert cfg.base_url == "https://api.storepay.test"
        assert cfg.store_id == "store-123"
        assert cfg.callback_url == "https://example.com/callback"

    def test_missing_app_username_raises(self) -> None:
        env = {
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_APP_USERNAME", None)
            with pytest.raises(ValueError, match="STOREPAY_APP_USERNAME"):
                load_config_from_env()

    def test_missing_app_password_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_APP_PASSWORD", None)
            with pytest.raises(ValueError, match="STOREPAY_APP_PASSWORD"):
                load_config_from_env()

    def test_missing_username_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_USERNAME", None)
            with pytest.raises(ValueError, match="STOREPAY_USERNAME"):
                load_config_from_env()

    def test_missing_password_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_PASSWORD", None)
            with pytest.raises(ValueError, match="STOREPAY_PASSWORD"):
                load_config_from_env()

    def test_missing_auth_url_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_AUTH_URL", None)
            with pytest.raises(ValueError, match="STOREPAY_AUTH_URL"):
                load_config_from_env()

    def test_missing_base_url_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_STORE_ID": "s",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_BASE_URL", None)
            with pytest.raises(ValueError, match="STOREPAY_BASE_URL"):
                load_config_from_env()

    def test_missing_store_id_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_CALLBACK_URL": "https://example.com/cb",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_STORE_ID", None)
            with pytest.raises(ValueError, match="STOREPAY_STORE_ID"):
                load_config_from_env()

    def test_missing_callback_url_raises(self) -> None:
        env = {
            "STOREPAY_APP_USERNAME": "au",
            "STOREPAY_APP_PASSWORD": "ap",
            "STOREPAY_USERNAME": "u",
            "STOREPAY_PASSWORD": "p",
            "STOREPAY_AUTH_URL": "https://auth.test",
            "STOREPAY_BASE_URL": "https://api.test",
            "STOREPAY_STORE_ID": "s",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("STOREPAY_CALLBACK_URL", None)
            with pytest.raises(ValueError, match="STOREPAY_CALLBACK_URL"):
                load_config_from_env()


# ============================================================================
# Error Tests
# ============================================================================


class TestStorePayError:
    """Tests for StorePayError."""

    def test_basic_error(self) -> None:
        err = StorePayError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.status_code is None
        assert err.response is None

    def test_error_with_status_code(self) -> None:
        err = StorePayError("bad request", status_code=400)
        assert err.status_code == 400

    def test_error_with_response(self) -> None:
        body = {"error": "details"}
        err = StorePayError("api error", status_code=500, response=body)
        assert err.status_code == 500
        assert err.response == body

    def test_is_exception(self) -> None:
        err = StorePayError("test")
        assert isinstance(err, Exception)

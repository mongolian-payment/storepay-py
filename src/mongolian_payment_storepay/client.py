"""StorePay payment client implementations (sync and async)."""

import base64
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from .errors import StorePayError
from .types import (
    MsgStruct,
    StorePayConfig,
    StorePayLoanInput,
)


def _parse_msg_list(raw_list: Optional[List[Dict[str, Any]]]) -> List[MsgStruct]:
    """Parse a raw msgList from the API into MsgStruct objects."""
    if not raw_list:
        return []
    return [
        MsgStruct(
            code=m.get("code", ""),
            text=m.get("text", ""),
            params=m.get("params", ""),
        )
        for m in raw_list
    ]


def _extract_error_message(data: Dict[str, Any]) -> str:
    """Extract the first message text from msgList, falling back to status."""
    msg_list = data.get("msgList")
    if msg_list and len(msg_list) > 0:
        text = msg_list[0].get("text")
        if text:
            return text
    return data.get("status", "Unknown error")


class StorePayClient:
    """StorePay payment client (synchronous).

    Handles OAuth2 password-grant authentication (with Basic Auth) and
    provides methods for creating loans, checking loan status, and
    querying user possible amounts.
    """

    def __init__(self, config: StorePayConfig) -> None:
        if not config.app_username:
            raise ValueError("StorePayClient: app_username is required")
        if not config.app_password:
            raise ValueError("StorePayClient: app_password is required")
        if not config.username:
            raise ValueError("StorePayClient: username is required")
        if not config.password:
            raise ValueError("StorePayClient: password is required")
        if not config.auth_url:
            raise ValueError("StorePayClient: auth_url is required")
        if not config.base_url:
            raise ValueError("StorePayClient: base_url is required")
        if not config.store_id:
            raise ValueError("StorePayClient: store_id is required")
        if not config.callback_url:
            raise ValueError("StorePayClient: callback_url is required")

        # Strip trailing slashes for consistent URL building
        self._app_username = config.app_username
        self._app_password = config.app_password
        self._username = config.username
        self._password = config.password
        self._auth_url = re.sub(r"/+$", "", config.auth_url)
        self._base_url = re.sub(r"/+$", "", config.base_url)
        self._store_id = config.store_id
        self._callback_url = config.callback_url

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

        self._client = httpx.Client()

    # -- Public API --

    def loan(self, input: StorePayLoanInput) -> int:
        """Create a loan request.

        Args:
            input: Loan request details (description, mobile_number, amount).

        Returns:
            The loan ID on success.

        Raises:
            StorePayError: If the API returns an error or non-Success status.
        """
        self._auth()

        body = {
            "storeId": self._store_id,
            "mobileNumber": input.mobile_number,
            "description": input.description,
            "amount": f"{input.amount:.2f}",
            "callbackUrl": self._callback_url,
        }

        data = self._post(f"{self._base_url}/merchant/loan", body)

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay loan failed: {msg}",
                response=data,
            )

        return data["value"]

    def loan_check(self, id: str) -> bool:
        """Check the status of a loan.

        Args:
            id: The loan ID to check.

        Returns:
            True if the loan is confirmed, False otherwise.

        Raises:
            StorePayError: On network or API errors.
        """
        self._auth()

        data = self._get(
            f"{self._base_url}/merchant/loan/check/{quote(str(id), safe='')}"
        )

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay loanCheck failed: {msg}",
                response=data,
            )

        return data["value"]

    def user_possible_amount(self, mobile_number: str) -> float:
        """Get the possible loan amount for a user.

        Args:
            mobile_number: The user's mobile number.

        Returns:
            The possible loan amount.

        Raises:
            StorePayError: On network or API errors.
        """
        self._auth()

        body = {"mobileNumber": mobile_number}

        data = self._post(f"{self._base_url}/user/possibleAmount", body)

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay userPossibleAmount failed: {msg}",
                response=data,
            )

        return data["value"]

    def close(self) -> None:
        """Clear cached authentication tokens and close the HTTP client."""
        self._access_token = None
        self._token_expires_at = 0
        self._client.close()

    def __enter__(self) -> "StorePayClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- Private helpers --

    def _auth(self) -> None:
        """Authenticate via OAuth2 password grant with Basic Auth.

        Caches the token until it expires (with a 30-second safety margin).
        """
        if self._access_token and time.time() < self._token_expires_at:
            return

        params = {
            "grant_type": "password",
            "username": self._app_username,
            "password": self._app_password,
        }

        url = f"{self._auth_url}/oauth/token"
        basic_credentials = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()

        try:
            res = self._client.post(
                url,
                params=params,
                headers={
                    "Authorization": f"Basic {basic_credentials}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error during authentication: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                "Invalid JSON response during authentication",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay authentication failed: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        if not json_data.get("access_token"):
            raise StorePayError(
                "StorePay authentication failed: no access_token in response",
                status_code=res.status_code,
                response=json_data,
            )

        self._access_token = json_data["access_token"]
        # Cache until 30 seconds before expiry
        self._token_expires_at = time.time() + (json_data["expires_in"] - 30)

    def _post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to the StorePay API with Bearer auth."""
        try:
            res = self._client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error calling {url}: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                f"Invalid JSON response from {url}",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay API error: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        return json_data

    def _get(self, url: str) -> Dict[str, Any]:
        """Send a GET request to the StorePay API with Bearer auth."""
        try:
            res = self._client.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error calling {url}: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                f"Invalid JSON response from {url}",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay API error: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        return json_data


class AsyncStorePayClient:
    """StorePay payment client (asynchronous).

    Handles OAuth2 password-grant authentication (with Basic Auth) and
    provides methods for creating loans, checking loan status, and
    querying user possible amounts.
    """

    def __init__(self, config: StorePayConfig) -> None:
        if not config.app_username:
            raise ValueError("AsyncStorePayClient: app_username is required")
        if not config.app_password:
            raise ValueError("AsyncStorePayClient: app_password is required")
        if not config.username:
            raise ValueError("AsyncStorePayClient: username is required")
        if not config.password:
            raise ValueError("AsyncStorePayClient: password is required")
        if not config.auth_url:
            raise ValueError("AsyncStorePayClient: auth_url is required")
        if not config.base_url:
            raise ValueError("AsyncStorePayClient: base_url is required")
        if not config.store_id:
            raise ValueError("AsyncStorePayClient: store_id is required")
        if not config.callback_url:
            raise ValueError("AsyncStorePayClient: callback_url is required")

        # Strip trailing slashes for consistent URL building
        self._app_username = config.app_username
        self._app_password = config.app_password
        self._username = config.username
        self._password = config.password
        self._auth_url = re.sub(r"/+$", "", config.auth_url)
        self._base_url = re.sub(r"/+$", "", config.base_url)
        self._store_id = config.store_id
        self._callback_url = config.callback_url

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

        self._client = httpx.AsyncClient()

    # -- Public API --

    async def loan(self, input: StorePayLoanInput) -> int:
        """Create a loan request.

        Args:
            input: Loan request details (description, mobile_number, amount).

        Returns:
            The loan ID on success.

        Raises:
            StorePayError: If the API returns an error or non-Success status.
        """
        await self._auth()

        body = {
            "storeId": self._store_id,
            "mobileNumber": input.mobile_number,
            "description": input.description,
            "amount": f"{input.amount:.2f}",
            "callbackUrl": self._callback_url,
        }

        data = await self._post(f"{self._base_url}/merchant/loan", body)

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay loan failed: {msg}",
                response=data,
            )

        return data["value"]

    async def loan_check(self, id: str) -> bool:
        """Check the status of a loan.

        Args:
            id: The loan ID to check.

        Returns:
            True if the loan is confirmed, False otherwise.

        Raises:
            StorePayError: On network or API errors.
        """
        await self._auth()

        data = await self._get(
            f"{self._base_url}/merchant/loan/check/{quote(str(id), safe='')}"
        )

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay loanCheck failed: {msg}",
                response=data,
            )

        return data["value"]

    async def user_possible_amount(self, mobile_number: str) -> float:
        """Get the possible loan amount for a user.

        Args:
            mobile_number: The user's mobile number.

        Returns:
            The possible loan amount.

        Raises:
            StorePayError: On network or API errors.
        """
        await self._auth()

        body = {"mobileNumber": mobile_number}

        data = await self._post(f"{self._base_url}/user/possibleAmount", body)

        if data.get("status") != "Success":
            msg = _extract_error_message(data)
            raise StorePayError(
                f"StorePay userPossibleAmount failed: {msg}",
                response=data,
            )

        return data["value"]

    async def close(self) -> None:
        """Clear cached authentication tokens and close the HTTP client."""
        self._access_token = None
        self._token_expires_at = 0
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncStorePayClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # -- Private helpers --

    async def _auth(self) -> None:
        """Authenticate via OAuth2 password grant with Basic Auth.

        Caches the token until it expires (with a 30-second safety margin).
        """
        if self._access_token and time.time() < self._token_expires_at:
            return

        params = {
            "grant_type": "password",
            "username": self._app_username,
            "password": self._app_password,
        }

        url = f"{self._auth_url}/oauth/token"
        basic_credentials = base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()

        try:
            res = await self._client.post(
                url,
                params=params,
                headers={
                    "Authorization": f"Basic {basic_credentials}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error during authentication: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                "Invalid JSON response during authentication",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay authentication failed: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        if not json_data.get("access_token"):
            raise StorePayError(
                "StorePay authentication failed: no access_token in response",
                status_code=res.status_code,
                response=json_data,
            )

        self._access_token = json_data["access_token"]
        # Cache until 30 seconds before expiry
        self._token_expires_at = time.time() + (json_data["expires_in"] - 30)

    async def _post(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to the StorePay API with Bearer auth."""
        try:
            res = await self._client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error calling {url}: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                f"Invalid JSON response from {url}",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay API error: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        return json_data

    async def _get(self, url: str) -> Dict[str, Any]:
        """Send a GET request to the StorePay API with Bearer auth."""
        try:
            res = await self._client.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                },
            )
        except httpx.HTTPError as exc:
            raise StorePayError(
                f"Network error calling {url}: {exc}"
            ) from exc

        try:
            json_data: Dict[str, Any] = res.json()
        except Exception:
            raise StorePayError(
                f"Invalid JSON response from {url}",
                status_code=res.status_code,
            )

        if res.status_code < 200 or res.status_code >= 300:
            raise StorePayError(
                f"StorePay API error: HTTP {res.status_code}",
                status_code=res.status_code,
                response=json_data,
            )

        return json_data

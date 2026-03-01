"""Type definitions for the StorePay payment SDK."""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class StorePayConfig:
    """Configuration for the StorePayClient.

    Attributes:
        app_username: OAuth app username (used in password grant body).
        app_password: OAuth app password (used in password grant body).
        username: Basic Auth username (used in Authorization header).
        password: Basic Auth password (used in Authorization header).
        auth_url: Auth server URL (e.g. "https://auth.storepay.mn").
        base_url: API base URL (e.g. "https://api.storepay.mn").
        store_id: Merchant store ID.
        callback_url: Callback URL for loan notifications.
    """

    app_username: str
    app_password: str
    username: str
    password: str
    auth_url: str
    base_url: str
    store_id: str
    callback_url: str


# ============================================================================
# SDK Input Types (user-facing)
# ============================================================================


@dataclass
class StorePayLoanInput:
    """Input for creating a loan request.

    Attributes:
        description: Description of the loan.
        mobile_number: Customer mobile number.
        amount: Loan amount.
    """

    description: str
    mobile_number: str
    amount: float


# ============================================================================
# API Response Types
# ============================================================================


@dataclass
class MsgStruct:
    """A message entry from the StorePay API response.

    Attributes:
        code: Message code.
        text: Message text.
        params: Message params.
    """

    code: str
    text: str
    params: str


@dataclass
class StorePayLoanResponse:
    """Response from creating a loan.

    Attributes:
        value: Loan ID.
        msg_list: List of messages.
        attrs: Additional attributes.
        status: Response status ("Success" indicates success).
    """

    value: int
    msg_list: List[MsgStruct]
    attrs: Any
    status: str


@dataclass
class StorePayCheckResponse:
    """Response from checking a loan.

    Attributes:
        value: Whether the loan is confirmed.
        msg_list: List of messages.
        attrs: Additional attributes.
        status: Response status ("Success" indicates success).
    """

    value: bool
    msg_list: List[MsgStruct]
    attrs: Any
    status: str


@dataclass
class StorePayUserCheckResponse:
    """Response from checking a user's possible loan amount.

    Attributes:
        value: Possible loan amount for the user.
        msg_list: List of messages.
        attrs: Additional attributes.
        status: Response status ("Success" indicates success).
    """

    value: float
    msg_list: List[MsgStruct]
    attrs: Any
    status: str


@dataclass
class StorePayLoginResponse:
    """OAuth2 login response (internal).

    Attributes:
        access_token: The access token.
        expires_in: Token lifetime in seconds.
        token_type: Token type (e.g. "bearer").
        refresh_token: Refresh token.
        scope: Token scope.
    """

    access_token: str
    expires_in: int
    token_type: str = ""
    refresh_token: str = ""
    scope: str = ""

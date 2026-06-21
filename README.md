# mongolian-payment-storepay

StorePay payment gateway SDK for Python (sync + async) — create loans, check loan status, query user possible amounts.

[![PyPI version](https://img.shields.io/pypi/v/mongolian-payment-storepay.svg)](https://pypi.org/project/mongolian-payment-storepay/)
[![Python versions](https://img.shields.io/pypi/pyversions/mongolian-payment-storepay.svg)](https://pypi.org/project/mongolian-payment-storepay/)
[![license](https://img.shields.io/pypi/l/mongolian-payment-storepay.svg)](./LICENSE)

> Part of the **[mongolian-payment](https://github.com/mongolian-payment)** SDK suite.
> Also available for Node.js: **[@mongolian-payment/storepay](https://www.npmjs.com/package/@mongolian-payment/storepay)** ([source](https://github.com/mongolian-payment/storepay-js)).

## Requirements

- Python >= 3.8 (depends on `httpx`)

## Installation

```bash
pip install mongolian-payment-storepay
```

## Quick Start

```python
from mongolian_payment_storepay import StorePayClient, StorePayConfig, StorePayLoanInput

client = StorePayClient(StorePayConfig(
    app_username="MY_APP_USERNAME",
    app_password="MY_APP_PASSWORD",
    username="MY_USERNAME",
    password="MY_PASSWORD",
    auth_url="https://auth.storepay.mn",
    base_url="https://api.storepay.mn",
    store_id="MY_STORE_ID",
    callback_url="https://example.com/callback",
))

# Create a loan
loan_id = client.loan(StorePayLoanInput(
    description="Order #001",
    mobile_number="99112233",
    amount=50000,
))
print(loan_id)  # Loan ID

# Check loan status
confirmed = client.loan_check(str(loan_id))
print(confirmed)  # True if confirmed

# Query a user's possible loan amount
amount = client.user_possible_amount("99112233")
print(amount)

# Clean up
client.close()
```

### Async

```python
import asyncio
from mongolian_payment_storepay import AsyncStorePayClient, StorePayConfig, StorePayLoanInput

async def main():
    async with AsyncStorePayClient(StorePayConfig(
        app_username="MY_APP_USERNAME",
        app_password="MY_APP_PASSWORD",
        username="MY_USERNAME",
        password="MY_PASSWORD",
        auth_url="https://auth.storepay.mn",
        base_url="https://api.storepay.mn",
        store_id="MY_STORE_ID",
        callback_url="https://example.com/callback",
    )) as client:
        loan_id = await client.loan(StorePayLoanInput(
            description="Order #001",
            mobile_number="99112233",
            amount=50000,
        ))
        confirmed = await client.loan_check(str(loan_id))
        print(confirmed)

asyncio.run(main())
```

## Configuration from Environment Variables

```python
from mongolian_payment_storepay import StorePayClient, load_config_from_env

client = StorePayClient(load_config_from_env())
```

| Variable                | Description                         |
| ----------------------- | ----------------------------------- |
| `STOREPAY_APP_USERNAME` | OAuth app username                  |
| `STOREPAY_APP_PASSWORD` | OAuth app password                  |
| `STOREPAY_USERNAME`     | Basic Auth username                 |
| `STOREPAY_PASSWORD`     | Basic Auth password                 |
| `STOREPAY_AUTH_URL`     | Auth server URL                     |
| `STOREPAY_BASE_URL`     | API base URL                        |
| `STOREPAY_STORE_ID`     | Merchant store ID                   |
| `STOREPAY_CALLBACK_URL` | Callback URL for loan notifications |

> Never hard-code credentials — load them from the environment or a secrets vault.

## API Reference

`StorePayClient` and `AsyncStorePayClient` share identical method signatures (the async
client uses `async`/`await`). Authentication is automatic — an OAuth2 password-grant
login is performed on the first request and refreshed when the token expires.

| Method | Description |
|--------|-------------|
| `loan(input)` | Create a loan request → returns the loan ID (`int`) |
| `loan_check(id)` | Check loan status → `True` if confirmed |
| `user_possible_amount(mobile_number)` | Get the user's maximum possible loan amount |
| `close()` | Clear cached tokens and close the HTTP client |

## Error Handling

All API errors raise `StorePayError`, which includes the HTTP status code and response body:

```python
from mongolian_payment_storepay import StorePayError

try:
    client.loan_check("invalid_id")
except StorePayError as err:
    print(err)              # Human-readable message
    print(err.status_code)  # HTTP status code (if available)
    print(err.response)     # Raw response body (if available)
```

## License

MIT

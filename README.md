# mongolian-payment-storepay

StorePay payment gateway SDK for Python. Supports both synchronous and asynchronous usage.

## Installation

```bash
pip install mongolian-payment-storepay
```

## Usage

### Synchronous

```python
from mongolian_payment_storepay import StorePayClient, StorePayConfig, StorePayLoanInput

client = StorePayClient(StorePayConfig(
    app_username="your_app_username",
    app_password="your_app_password",
    username="your_username",
    password="your_password",
    auth_url="https://auth.storepay.mn",
    base_url="https://api.storepay.mn",
    store_id="your_store_id",
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

# Check user possible amount
amount = client.user_possible_amount("99112233")
print(amount)

# Clean up
client.close()
```

### Asynchronous

```python
import asyncio
from mongolian_payment_storepay import AsyncStorePayClient, StorePayConfig, StorePayLoanInput

async def main():
    async with AsyncStorePayClient(StorePayConfig(
        app_username="your_app_username",
        app_password="your_app_password",
        username="your_username",
        password="your_password",
        auth_url="https://auth.storepay.mn",
        base_url="https://api.storepay.mn",
        store_id="your_store_id",
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

### Configuration from Environment Variables

```python
from mongolian_payment_storepay import StorePayClient, load_config_from_env

client = StorePayClient(load_config_from_env())
```

Required environment variables:

| Variable                 | Description                          |
|--------------------------|--------------------------------------|
| `STOREPAY_APP_USERNAME`  | OAuth app username                   |
| `STOREPAY_APP_PASSWORD`  | OAuth app password                   |
| `STOREPAY_USERNAME`      | Basic Auth username                  |
| `STOREPAY_PASSWORD`      | Basic Auth password                  |
| `STOREPAY_AUTH_URL`      | Auth server URL                      |
| `STOREPAY_BASE_URL`      | API base URL                         |
| `STOREPAY_STORE_ID`      | Merchant store ID                    |
| `STOREPAY_CALLBACK_URL`  | Callback URL for loan notifications  |

## License

MIT

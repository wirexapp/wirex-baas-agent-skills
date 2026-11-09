# Webhooks & Activity History Reference

Complete webhook payload reference for all Wirex BaaS webhook endpoints. This is the canonical location for webhook payloads — other skills cross-reference this file.

For delivery semantics (POST, 10s timeout, up to 5 retries with exponential backoff) and the activity history feed API, see [SKILL.md](../SKILL.md). All paths are appended to your webhook base URL: `POST {your_webhook_base_url}/v2/webhooks/...`.

---

## V2 Webhook Endpoints

### Wallet Webhook -- `/v2/webhooks/wallets`

Fires when a wallet is created or its status changes.

**Payload:**

```json
{
  "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
  "wallet_name": "Main Wallet",
  "wallet_status": "Confirmed",
  "wallet_type": "Primary",
  "balances": []
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `wallet_address` | string | The Smart Wallet address |
| `wallet_name` | string | Human-readable wallet label |
| `wallet_status` | string | Current wallet status |
| `wallet_type` | string | Wallet classification |
| `balances` | array | Token balances (empty in the wallet creation webhook; the Webhooks guide payload omits it) |

**`wallet_status` Values:**

| Status | Meaning |
|--------|---------|
| `Confirmed` | Wallet is properly configured as a Smart Wallet with required modules |
| `Rejected` | Wallet configuration is invalid or incomplete |
| `Unknown` | Status could not be determined |

**`wallet_type` Values:**

| Type | Meaning |
|------|---------|
| `Primary` | Main user wallet |
| `Secondary` | Additional user wallet |
| `Global` | Global wallet |
| `Card` | Card wallet |

---

### Balance Webhook -- `/v2/webhooks/balances`

Fires when a token balance changes on a wallet.

**Payload:**

```json
{
  "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
  "token_symbol": "WUSD",
  "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
  "balance": 2,
  "reference_balance": 1.68,
  "reference_currency": "EUR"
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `wallet_address` | string | The wallet whose balance changed |
| `token_symbol` | string | Token symbol (e.g. `WUSD`, `WEUR`; the guide's field table says e.g. USDT, USDC) |
| `token_address` | string | On-chain token contract address |
| `balance` | float | Available token balance |
| `reference_balance` | float | Balance converted to reference currency |
| `reference_currency` | string | ISO 4217 currency code (default: `EUR`) |

---

### Card Webhook -- `/v2/webhooks/cards`

Fires when card state changes (issuance, activation, blocking, status updates).

**Payload:**

```json
{
  "id": "64120850-73a1-4df5-a074-d463258c9deb",
  "card_wallet_address": "0xAAFF0821A09A1Aac28B72dD3Ff410A7ea5FEb874",
  "status": "Closed",
  "status_reason": "User",
  "generation": "Gen2",
  "provider": "Wirex",
  "card_data": {
    "name_on_card": "ALEX GREY",
    "payment_system": "Visa",
    "card_number_last_4": "0333",
    "expiry_date": "02/27",
    "format": "Plastic",
    "card_name": "Main Card"
  }
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique card identifier |
| `card_wallet_address` | string | Linked wallet address |
| `status` | enum | `Requested`, `NotActivated`, `Active`, `Closed`, `Blocked` |
| `status_reason` | string | Reason for the current status |
| `previous_status` | enum | Status before the current state |
| `generation` | enum | `Gen1`, `Gen2` |
| `provider` | enum | `Wirex`, `Bridge` |
| `card_data` | object | Card display information (see sub-fields below) |
| `delivery_address` | object (optional) | Physical card delivery address |

**`card_data` Sub-Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name_on_card` | string | Cardholder name as printed on card |
| `payment_system` | string | Payment network (e.g., Visa) |
| `card_number_last_4` | string | Last 4 digits of the card number |
| `expiry_date` | string | Card expiry date (the Webhooks guide example shows `MM/YY`; card activation uses `MM/YYYY`) |
| `format` | string | Card format (e.g., `Plastic`) |
| `card_name` | string | User-assigned card name |

---

### Card Limits Webhook -- `/v2/webhooks/card-limits`

Fires when card spending limits or usage change.

**Payload:**

```json
{
  "card_id": "64120850-73a1-4df5-a074-d463258c9deb",
  "transaction_limit": -1,
  "daily_limit": 1000.00,
  "daily_usage": 45.99,
  "monthly_limit": -1,
  "monthly_usage": 45.99,
  "lifetime_limit": -1,
  "lifetime_usage": 45.99
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `card_id` | string (UUID) | Card identifier |
| `transaction_limit` | number | Per-transaction limit (-1 = unlimited) |
| `daily_limit` | number | Daily spending limit (-1 = unlimited) |
| `daily_usage` | number | Amount spent today |
| `monthly_limit` | number | Monthly spending limit (-1 = unlimited) |
| `monthly_usage` | number | Amount spent this month |
| `lifetime_limit` | number | Lifetime spending limit (-1 = unlimited) |
| `lifetime_usage` | number | Total amount spent lifetime |

**Note:** Limit semantics (Managing Card Limits guide): a positive number is a hard cap, `-1` means no limit, `0` blocks all spending. The payload has no `owner` field.

---

### 3DS Webhook -- `/v2/webhooks/3ds`

Fires when a 3D Secure confirmation is required for a card transaction.

**Payload:**

```json
{
  "card_id": "64120850-73a1-4df5-a074-d463258c9deb",
  "user_address": "0xAAFF0821A09A1Aac28B72dD3Ff410A7ea5FEb874",
  "transaction_id": "1b0b99c8-566c-45e5-8c82-4151edd078f5",
  "merchant_name": "Amazon UK",
  "amount": "127.15",
  "currency": "USD",
  "card_last_4": "0333"
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `card_id` | string (UUID) | Card being charged |
| `user_address` | string | EOA address of the user who owns the card |
| `owner` | string | **Deprecated.** Mirrors `user_address` |
| `transaction_id` | string | Issuer transaction identifier |
| `merchant_name` | string | Merchant name |
| `amount` | string | Transaction amount |
| `currency` | string | ISO 4217 currency code |
| `card_last_4` | string | Last 4 digits of the card |

---

### Activity Webhook -- `/v2/webhooks/activities`

Fires when a transaction or activity state changes. The payload carries the same fields as `GET /api/v2/activity/single/{id}` (including `chain_id`, the `amount_precise`/`decimals` amount fields and `operations[].resulting_balance`). You may receive several webhooks per transaction as it progresses.

**Payload (SEPA deposit):**

```json
{
  "id": "ea6fbc2c-b8da-4a7b-99d1-6a2220352d02",
  "user_address": "0x1d595bFAc81F231Ebc30950B8B08F2beEb97934B",
  "type": "Sepa",
  "status": "Completed",
  "direction": "Inbound",
  "source": {
    "type": "SepaBankAccount",
    "bank_account": {
      "iban": "GB82WEST12345698765432",
      "bic": "WESTGB2L",
      "owner_name": "Alex Grey",
      "is_business": false
    }
  },
  "destination": {
    "type": "Wallet",
    "wallet": { "address": "0x6fb0fCA78F4b717fbAaB89c96754200355554832" }
  },
  "source_amount": { "amount": 55.93, "currency": "EUR" },
  "destination_amount": {
    "amount": 55.93,
    "token_symbol": "WEUR",
    "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2"
  },
  "reference": "Payment reference",
  "operations": [
    {
      "operation_amount": { "amount": 55.93, "token_symbol": "WEUR", "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2" },
      "transaction_amount": { "amount": 55.93, "currency": "EUR" },
      "rate": { "ticker": "EUR/WEUR", "rate": 1 }
    }
  ],
  "activity_steps": [
    { "type": "Initiated", "status": "Completed", "created_at": "2024-01-01T10:15:30.000Z", "completed_at": "2024-01-01T10:15:30.000Z" },
    { "type": "BankIn", "status": "Completed", "created_at": "2024-01-01T10:15:30.000Z", "completed_at": "2024-01-01T10:15:45.000Z" },
    { "type": "CryptoIn", "status": "Completed", "created_at": "2024-01-01T10:15:45.000Z", "completed_at": "2024-01-01T10:15:50.000Z" }
  ]
}
```

The Webhooks guide also shows examples for a crypto deposit/transfer (`Crypto`, `ExternalWallet` <-> `Wallet`, steps `CryptoIn`/`CryptoOut`), SEPA outbound (steps `Initiated`, `CryptoOut`, `Review`, `BankOut`), ACH (`AchPush`, `AchBankAccount` with `account_number`/`routing_number`), a card transaction (`CardTransaction`, `sub_type: "POS"`, `Cards` source with `card.id`/`pan_last`/`payment_system`, `Merchant` destination with `merchant.id`/`name`/`logo_url`/`full_address`, top-level `rate`, steps `Initiated`, `CardOut`) and a card transfer (`CardTransfer`, `Wallet` -> `Cards`). Card top-up completion is reported as a `CardTopup` activity (`direction: Inbound`, `ExternalCard` -> `Wallet`).

**Top-Level Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Activity identifier (the transaction id) |
| `user_address` | string | User's EOA address |
| `chain_id` | integer | EIP-155 chain the entry was recorded on |
| `type` | enum | See Activity Type Values in [SKILL.md](../SKILL.md) |
| `sub_type` | string | Finer classification (optional, e.g. `POS`) |
| `status` | enum | `Pending`, `Completed`, `Failed` |
| `status_reason` | string | Machine-readable reason for the status (optional) |
| `direction` | enum | `Inbound`, `Outbound`, `Internal` |
| `source` | object | Source subject (wallet, card, bank account) |
| `destination` | object | Destination subject (wallet, merchant, bank account) |
| `source_amount` | object | Amount debited from source |
| `destination_amount` | object | Amount credited to destination |
| `rate` | object | Average exchange rate applied (optional): `ticker`, `rate` |
| `reference` | string | Reference/memo (optional) |
| `operations` | array | On-chain operations with transaction hashes |
| `activity_steps` | array | Ordered processing steps |
| `created_at` | string (ISO 8601) | Activity creation timestamp |

**Source/Destination Object:** `type` plus a nested sub-object named after the subject -- `wallet.address` (`Wallet`, `ExternalWallet`), `card.id` / `card.pan_last` / `card.payment_system` (`Cards`, `ExternalCard`), `merchant.*` (`Merchant`), `bank_account.*` (`SepaBankAccount`: `iban`, `bic`; `AchBankAccount`: `account_number`, `routing_number`; all: `owner_name`, `is_business`).

**Amount Object:**

| Field | Type | Description |
|-------|------|-------------|
| `amount` | number | Amount as a number (not a string) |
| `amount_precise` | string | Exact base-unit value (absent for aggregates) |
| `decimals` | integer | Fractional digits `amount_precise` is scaled by |
| `currency` | string | ISO 4217 code -- present only for fiat amounts |
| `token_symbol` / `token_address` | string | Present only for crypto amounts |

**Operations Object:**

| Field | Type | Description |
|-------|------|-------------|
| `operation_id` | string (UUID) | Operation identifier |
| `hash` | string | On-chain transaction hash |
| `operation_amount` | amount object | Crypto amount (negative when debited) |
| `transaction_amount` | amount object | Fiat amount (negative when debited) |
| `resulting_balance` | amount object | Balance after the operation |
| `rate` | object | Rate effective for this operation (`ticker`, `rate`) |
| `status` / `status_reason` | string | Operation status (v2+) |

**Activity Steps Object:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Step type (Initiated, CryptoIn, CryptoOut, BankIn, BankOut, Review, CardIn, CardOut, Reversal, SyntheticWrap, SyntheticUnwrap, Completed) |
| `status` | string | `Pending`, `Completed`, `Failed` |
| `created_at` | string (ISO 8601) | Step creation timestamp |
| `completed_at` | string (ISO 8601) | Step completion timestamp |

For card transactions, the `source_amount`/`destination_amount` always use positive values; until the crypto step (`CryptoOut`/`CryptoIn`) executes, the crypto amount may be `0` or missing.

---

### ERC Withdrawal Webhook -- `/v2/webhooks/erc-withdrawals`

Fires when an ERC20 withdrawal is requested and pending user signature. Includes the validity window for execution.

**Payload:**

```json
{
  "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  "destination_address": "0xF4D2A0E30C7983EF65DC0DD938BED82C7E3745DB",
  "amount": 100.0,
  "valid_after": "2024-01-01T12:05:00.000Z",
  "valid_before": "2024-01-02T12:05:00.000Z",
  "hash": "0x8A7B6C5D4E3F2A1B0C9D8E7F6A5B4C3D2E1F0A9B8C7D6E5F4A3B2C1D0E9F8171",
  "call_data": "3F7D9E1C5A2B804D6E93F7C1A0B5D8E29F4A3B7C6D5E0F1A2B3C4D5E6F7A8B9..."
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `wallet_address` | string | Account Abstraction wallet address (formerly `account_address`) |
| `token_address` | string | ERC20 token contract address |
| `destination_address` | string | Destination address for the withdrawal (formerly `to_address`) |
| `amount` | float | Withdrawal amount |
| `valid_after` | string (ISO 8601) | Request validity start time |
| `valid_before` | string (ISO 8601) | Request expiry time |
| `hash` | string | Calldata and nonce hash |
| `call_data` | string | Encoded contract call data |

**Note:** Pending requests can also be read with `GET /api/v1/withdrawal/requests` (`{ "data": [...] }`). The old names `account_address` and `to_address` are still populated alongside the new ones. Use this webhook to update the UI showing pending withdrawals.

---

### Recipients Webhook -- `/v2/webhooks/recipients`

Fires when a recipient is created or updated.

**Payload:**

```json
{
  "id": "77fc49bd-1d7d-41d9-beea-a0aee0dc8c35",
  "personal_info": {
    "first_name": "Alex",
    "last_name": "Grey",
    "is_business": false
  },
  "payment_details": [
    {
      "id": "c56428d0-e1ce-4c4e-a9ca-63bb0f668d00",
      "type": "Sepa",
      "currencies": ["EUR"],
      "sepa": { "iban": "MT08CFTE28004000000000006388232", "bic": "CFTEMTM1XXX" }
    },
    {
      "id": "5d69a2f6-fd1d-4b23-bf41-94057a4ba768",
      "type": "Crypto",
      "currencies": ["USDT"],
      "crypto": { "recipient_address": "0xb7830E9DEab7dd10aC5E8F05aadec1b5b29Abc0B", "network": "Base" }
    }
  ]
}
```

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique recipient identifier |
| `personal_info` | object | Recipient name and type (person/business): `first_name`, `last_name`, `is_business` |
| `payment_details` | array | Payment methods for this recipient |

**`payment_details` Item Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Payment detail identifier |
| `type` | string | Payment type (see below) |
| `currencies` | array | Supported currency codes |

**Supported `payment_details` Types:**

Crypto, Sepa, FasterPayment, Ach, Swift, Spei, Card, Pix, Imps, Instapay, BiFast, Nip, FpsHk

Each type includes a type-specific sub-object (e.g., `sepa.iban`, `sepa.bic`; `crypto.recipient_address`, `crypto.network`; `ach.routing_number`, `ach.account_number`, `ach.bank_name`, `ach.legal_address` with `country`, `city`, `zip_code`, `line1`, `state`). The crypto address field was formerly `address`; it is now `recipient_address`.

---

### User Webhook -- `/v2/webhooks/user`

Fires when user profile or verification status changes. The payload is the `GET /api/v2/user` object **without `capabilities`** (`profile`, `residence_address`, `verification`, `external_providers` sub-objects). After a verification change, call `GET /api/v2/user` to read capabilities.

**Payload:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "owner": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "user_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "chain_id": 8453,
  "last_login_ip": "203.0.113.7",
  "profile": {
    "first_name": "Alex",
    "last_name": "Grey",
    "email": "alex.grey@wirexapp.com",
    "status": "Active",
    "registration_date": "2024-01-01T10:00:00Z"
  },
  "residence_address": { "line1": "10 Downing Street", "city": "London", "post_code": "SW1A 2AA", "country": "GB" },
  "verification": { "status": "Approved", "levels": [{ "status": "Approved", "type": "SDD", "name": "SDD" }] }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string (UUID) | User account identifier |
| `user_address` | string | EOA address that owns the account |
| `chain_id` | integer | Chain the account was registered on |
| `id` | string (UUID) | **Deprecated.** Mirrors `user_id` |
| `owner` | string | **Deprecated.** Mirrors `user_address` |
| `last_login_ip` | string | IP of the last non-S2S login. Omitted until one is recorded |
| `tags` | array of string | Platform tags on the account. Omitted when none |
| `profile` | object | Personal details, profile status, `registration_date` |
| `residence_address`, `verification`, `external_providers` | object / array | As in `GET /api/v2/user` |

This is the v2 replacement for the legacy `/webhook/users`. Both are delivered; treat the legacy one as superseded for new integrations.

---

### Debt Case Webhook -- `/v2/webhooks/debt-cases`

Fires when operations leave a user account in debt -- a card transaction or withdrawal that settled against the platform but could not be recovered from the user's balance.

**Payload:**

```json
{
  "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "operations": [
    {
      "transaction_id": "927476c4-7c72-458a-abff-9ab5db0d9f1a",
      "operation_id": "1b0b99c8-566c-45e5-8c82-4151edd078f5",
      "operation_subject_address": "0xAAFF0821A09A1Aac28B72dD3Ff410A7ea5FEb874",
      "operation_amount": "64240000",
      "operation_token_address": "0x0774164DC20524Bb239b39D1DC42573C3E4C6976",
      "operation_hash": "0x28da8dec81198cd43329c92ac5b7bcb048a48495bdbc69fc1c921da72fe42939",
      "operation_type": "CardTransaction",
      "status": "Failed",
      "type": "Debit",
      "status_reason": "InsufficientFunds"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `wallet_address` | string | Wallet address of the user the debt case belongs to |
| `operations[].transaction_id` | string (UUID) | Transaction the operation belongs to |
| `operations[].operation_id` | string (UUID) | Operation identifier |
| `operations[].operation_subject_address` | string | Address the operation was executed against |
| `operations[].operation_amount` | string | **Raw integer string in the token's smallest unit**, not a decimal (other webhooks deliver `amount` as a float) |
| `operations[].operation_token_address` | string | Token contract address |
| `operations[].operation_hash` | string | Hash of the underlying on-chain operation |
| `operations[].operation_type` | string | Operation type, e.g. `CardTransaction` |
| `operations[].status` | string | Operation status, e.g. `Failed` |
| `operations[].type` | string | `Debit` or `Credit` |
| `operations[].status_reason` | string | Reason for the status; omitted when not set |

---

### Corporation Webhook -- `/v2/webhooks/corporations`

Fires when a corporate profile or its verification status changes. Only relevant if your integration onboards corporate accounts.

**Payload:**

```json
{
  "corporation_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
  "owner_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "corporation_id": "550e8400-e29b-41d4-a716-446655440000",
  "corporation_name": "Acme Inc",
  "corporation_type": "LimitedLiability",
  "verification_status": "Approved",
  "status": "Active",
  "registration_number": "12345678",
  "corporation_registration_address": {
    "line1": "10 Downing Street", "line2": "Suite 200", "city": "London",
    "state": "", "country": "GB", "postal_code": "SW1A 2AA"
  },
  "corporation_contact_details": {
    "name": "Alex Grey", "email": "alex.grey@wirexapp.com", "phone_number": "+447700900123"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `corporation_address` | string | On-chain address of the corporate account |
| `owner_address` | string | EOA address of the account owner |
| `corporation_id` | string (UUID) | Corporation identifier |
| `corporation_name` | string | Registered company name |
| `corporation_type` | enum | `LimitedLiability`, `SoleTrader`, `Partnership`, `PublicLimitedCompany`, `JointStockCompany`, `Charity` |
| `verification_status` | enum | `Pending`, `Applied`, `InReview`, `Approved`, `Rejected`, `Canceled` |
| `status` | enum | `Pending`, `Active`, `Blocked`, `Deleted` |
| `registration_number` | string | Company registration number |
| `corporation_registration_address` | object | Registered address (uses `postal_code`, unlike a user's `post_code`) |
| `corporation_contact_details` | object | Primary contact name, email and phone number |
| `freshdesk_id` | string | Freshdesk identifier; omitted when not set |

---

## V1 Legacy Webhook Endpoints

> These endpoints use a legacy format that will be replaced with a v2 model in a future release.

### Users Webhook -- `/webhook/users`

Fires when user status or verification status changes. Superseded by `/v2/webhooks/user`.

**Payload:**

```json
{
  "id": "f409ac484633456192de3a2a1d689475",
  "external_id": "0x6072FF6fF23Ae51aB705414A7c58C2b0E4b6192a",
  "status": "Active",
  "verification_status": "Approved",
  "personal_details": {
    "email": "alex.grey@wirexapp.com",
    "phone_number": "+447700900123",
    "first_name": "Alex",
    "last_name": "Grey",
    "date_of_birth": "1990-01-15",
    "residence_address": {
      "line1": "10 Downing Street",
      "city": "London",
      "country": "GB",
      "postal_code": "SW1A 2AA"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | User ID (same as the registration response) |
| `external_id` | string | User's EOA address |
| `status` | enum | `Pending`, `Active`, `Blocked`, `Deleted` |
| `verification_status` | enum | See below |
| `personal_details` | object | `email`, `phone_number`, `first_name`, `last_name`, `date_of_birth`, `residence_address` (note: `postal_code` here) |

**`verification_status` Values:**

| Status | Meaning |
|--------|---------|
| `None` | No verification submitted |
| `Applied` | User has unfinished steps in the SumSub SDK, or incomplete data was provided during Shared / KYC Sharing via API flows |
| `Pending` | Verification checks are being executed on Wirex side |
| `InReview` | Verification checks are being executed on Wirex side |
| `Approved` | Verification approved -- user is ready to use all features |
| `Canceled` | Verification was rejected -- contact Wirex support |
| `Rejected` | Verification was rejected -- contact Wirex support |

---

### Fiat Accounts Webhook -- `/webhook/accounts/fiat`

Fires when a bank account is created or its details are updated.

**Payload (`DetailsChanged`):**

```json
{
  "change_type": "DetailsChanged",
  "id": "1334726cbd7641c09b4124e3e52f53fe",
  "account_type": "Fiat",
  "currency": "EUR",
  "status": "Active",
  "balance": { "amount": 0, "available_amount": 0 },
  "details": [
    {
      "id": "8d5a65eb59d94afea64374d45591fe9f",
      "type": "Sepa",
      "status": "Pending",
      "transport_currency": "EUR"
    }
  ],
  "owner_type": "Personal"
}
```

A `Created` event has the same shape with `change_type: "Created"`, empty `details` and a `created_at` timestamp.

**Field Reference:**

| Field | Type | Description |
|-------|------|-------------|
| `change_type` | enum | `Created`, `DetailsChanged`, `StatusChanged` |
| `id` | string (UUID) | Account identifier |
| `account_type` | string | Always `Fiat` |
| `currency` | string | Account currency (`EUR`, `USD`, `GBP`) |
| `status` | enum | `Active`, `Pending`, `Blocked`, `Closed` |
| `balance` | object | `amount`, `available_amount` |
| `details` | array | Bank account details (SEPA, ACH, etc.) |
| `details[].id` | string (UUID) | Details identifier |
| `details[].type` | enum | `Sepa`, `Ach`, `FasterPayment` |
| `details[].status` | enum | `Pending`, `Active`, `Blocked`, `Closed` |
| `owner_type` | enum | `Personal`, `Business` |

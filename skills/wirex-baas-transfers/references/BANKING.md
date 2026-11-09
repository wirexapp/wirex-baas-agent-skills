# Wirex BaaS Transfers — SEPA & ACH Banking Reference

Detailed endpoint reference for SEPA (EUR) and ACH (USD) bank transfers, including bank detail activation, transfer estimation, execution, capabilities, and webhooks.

## Table of Contents

- [SEPA Bank Details](#sepa-bank-details)
- [SEPA Transfer Estimate](#sepa-transfer-estimate)
- [SEPA Transfer Execute](#sepa-transfer-execute)
- [ACH Bank Details](#ach-bank-details)
- [ACH Transfer Estimate](#ach-transfer-estimate)
- [ACH Transfer Execute](#ach-transfer-execute)
- [Capability Requirements](#capability-requirements)
- [Activity Webhook](#activity-webhook)
- [Error Codes](#error-codes)

---

## SEPA Bank Details

SEPA accounts **require activation**: verification alone does not provision an IBAN (this changed; SEPA now follows the same model as ACH). Check the `SepaAccount` capability via `GET /api/v2/user` and follow the path for its status. Available to residents of: AT, BE, BG, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IS, IE, IT, LV, LT, LU, MT, NL, NO, PL, PT, RO, SK, SI, ES, SE, GB.

### SepaAccount Capability Status

| Status                                 | Meaning / what to do                                                  |
|----------------------------------------|-----------------------------------------------------------------------|
| `ActivationNotStarted`                 | Standard activation: `POST /api/v1/bank/accounts`                     |
| `ExternalProviderVerificationRequired` | Wallet-linking activation (`init` -> sign -> `complete`)              |
| `ExternalProviderRegistrationPending`  | Wait, then re-check                                                   |
| `InProgress`                           | Activation requested; wait for the bank account webhook               |
| `Active`                               | Provisioned; retrieve details                                         |
| `NotFulfilled`                         | Complete the required verification level first                        |
| `NotRequired`                          | Capability does not apply to this user                                |
| `NotAvailable`                         | Not available for the user's country of residence                     |

> The API reference `CapabilityStatus` enum now also lists `ExternalProviderRegistrationPending` and `ExternalProviderVerificationRequired`, and `/api/v1/bank/accounts/init` and `/complete` have reference pages (their examples show `"chain": "polygon"`; this skill sends the numeric chain ID as a string, as the SEPA bank details guide says).

### Activate SEPA Account (standard)

**POST /api/v1/bank/accounts**

```json
{ "account_type": "Sepa" }
```

`account_type` accepts `Sepa`, `Ach`, `FasterPayment`, `Spei` (the API reference enum also lists `Swift`). Response: `{ "details_id": "..." }`; the capability becomes `InProgress`. When the capability does not need activation the call returns `400` ("Account capability does not need activation or is not available").

### Activate SEPA Account (with wallet linking)

Used only when the capability is `ExternalProviderVerificationRequired`; the Primary Smart Wallet must prove ownership to an external provider.

1. **POST /api/v1/bank/accounts/init** with `{ "chain": "8453" }`. `chain` must be a numeric chain ID sent as a string (not a name like `"base"`). Response: `{ "challenge": "...", "wallet_address": "0x...", "chain": "8453" }`. The wallet is resolved server-side as the user's Primary wallet (none -> `400 Wallet not found`).
2. Sign `challenge` with the wallet at `wallet_address`.
3. **POST /api/v1/bank/accounts/complete** with `{ "chain": "8453", "signed_challenge": "0x..." }`. Response: `{ "details_id": "..." }`.

Both calls return `400` ("External provider wallet verification is not required for this account") when the capability is in any other status.

### Get Bank Accounts

**GET /api/v1/bank/accounts**

Retrieves all bank accounts for the user, including SEPA details (IBAN and BIC).

**Request Headers:**

| Header         | Required | Description                        |
|---------------|----------|------------------------------------|
| Authorization  | Yes      | Bearer `{access_token}`           |
| Content-Type   | Yes      | `application/json`                 |
| X-User-Wallet  | Yes      | The user's EOA wallet address      |
| X-Chain-Id     | Yes      | The blockchain chain ID            |

**Query Parameters:**

| Parameter   | Type    | Default | Description              |
|------------|---------|---------|--------------------------|
| page_number | integer | 0       | Page number; `0` and `1` both return the first page, `2` the second |
| page_size   | integer | 25      | Items per page, capped at 50; `0` = no limit |
| sort        | string  | name    | `name` (ascending) or `usage` (descending usage count) |

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "{account_id}:{details_id}",
      "account_type": "Sepa",
      "status": "Active",
      "account_holder": "John Doe",
      "currency": "EUR",
      "details": {
        "iban": "GB29NWBK60161331926819",
        "bic": "TRWIGB2L"
      }
    }
  ]
}
```

The list is under `data`, as in the API reference schema and now in the SEPA and ACH guides too (live sandbox returned `data`, 2026-10-25). Paging behaviour above was observed live in sandbox: without paging parameters the whole list is returned. `account_type` values: `Sepa`, `Swift`, `FasterPayment`, `Ach`, `Spei`. `details` may also carry `mandatory_reference` (if present it MUST be set as the incoming transfer comment so the funds are credited to the right account), `sort_code`, `clabe`. Extra query parameter: `sort` (`name` default, or `usage`).

The `id` field uses a composite `{account_id}:{details_id}` format. Use this composite ID as the `account_id` in transfer estimate and execute requests.

**Account Statuses:** `Pending` (provisioning), `Active` (ready), `Blocked` (suspended), `Closed` (terminated), `Failed` (provisioning failed at the bank provider; the account cannot be used). Each entry also carries `created_at`.

### Bank Account Webhook

**Endpoint:** `POST {webhook_url}/webhook/accounts/fiat`

Triggered when a bank account is created or details change. The account is usable once the webhook reports the SEPA details.

**`change_type` values:** `Created`, `DetailsChanged` (`details[]` entries carry `id` = `details_id`, `type` e.g. `Sepa`/`Ach`, `status`, `transport_currency`).

Incoming transfers arrive as `/v2/webhooks/activities` events (`type: Sepa` or `AchPush`, `direction: Inbound`, steps Initiated → BankIn → CryptoIn) and are credited as WEUR/WUSD. Typical settlement: SEPA 1-2 business days, ACH 1-3 business days.

---

## SEPA Transfer Estimate

### POST /api/v2/bank/transfer/estimate

Estimate the cost and exchange rate for a SEPA transfer before executing it.

**Request Headers:**

| Header         | Required | Description                        |
|---------------|----------|------------------------------------|
| Authorization  | Yes      | Bearer `{access_token}`           |
| Content-Type   | Yes      | `application/json`                 |
| X-User-Wallet  | Yes      | The user's EOA wallet address      |
| X-Chain-Id     | Yes      | The blockchain chain ID            |

**Request Body:**

```json
{
  "account_id": "{account_id}:{details_id}",
  "amount": 100.00,
  "tokens": ["0x5c55F314624718019A326F16a62A05D6C6d8C8A2"],
  "recipient": {
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "recipient_account": {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX"
  },
  "reference": "Invoice 12345"
}
```

For company recipients, use `company_name` instead of `first_name`/`last_name`:

```json
{
  "account_id": "{account_id}:{details_id}",
  "amount": 500.00,
  "tokens": ["0x5c55F314624718019A326F16a62A05D6C6d8C8A2"],
  "recipient": {
    "company_name": "Acme GmbH"
  },
  "recipient_account": {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX"
  }
}
```

**Request Fields:**

| Field                     | Type     | Required | Description                                              |
|---------------------------|----------|----------|----------------------------------------------------------|
| account_id                | string   | Yes      | Composite ID in `{account_id}:{details_id}` format      |
| amount                    | number   | Yes      | Transfer amount in EUR                                   |
| tokens                    | string[] | No       | Token contract addresses; omit for all available tokens  |
| recipient.first_name      | string   | No*      | Recipient first name (individual); recipient is required for ACH |
| recipient.last_name       | string   | No*      | Recipient last name (individual)                         |
| recipient.company_name    | string   | No*      | Recipient company name (business)                        |
| recipient_account.iban    | string   | Yes      | Recipient IBAN                                           |
| recipient_account.bic     | string   | Yes      | Recipient BIC/SWIFT code                                 |
| reference                 | string   | No       | Payment memo/reference (max 140 chars)                   |

*Either (`first_name` + `last_name`) or `company_name` is required.

**Response (200 OK):**

```json
{
  "id": "uuid-estimation-id",
  "expires_at": 1704110400,
  "amount": 100.00,
  "currency": "EUR",
  "estimated_amounts": [
    {
      "amount": 109.41,
      "precise_amount": "109410000000000000000",
      "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2",
      "token_symbol": "WEUR",
      "rate": 1.0
    }
  ]
}
```

**Response Fields:**

| Field                                    | Type   | Description                                          |
|------------------------------------------|--------|------------------------------------------------------|
| id                                       | string | Estimation ID (use in execute step)                  |
| expires_at                               | number | Unix timestamp when estimate expires                 |
| amount                                   | number | Fiat amount the recipient receives                   |
| amount_precise / decimals                | string / integer | `amount` as an integer string, and its decimal places (`18`) |
| currency                                 | string | Transfer currency (EUR)                              |
| estimated_amounts                        | array  | Array of per-token quote objects                     |
| estimated_amounts[].amount               | number | Human-readable token amount to debit, fee included   |
| estimated_amounts[].precise_amount       | string | Amount in the token's smallest unit (exponent is the token's `decimals`, not always 18) |
| estimated_amounts[].token_address        | string | Token contract address                               |
| estimated_amounts[].token_symbol         | string | Token symbol (e.g., WEUR)                            |
| estimated_amounts[].rate                 | number | EUR per 1 token                                      |
| estimated_amounts[].fee_amount           | number | Per-token fee included in the debited amount (token precision); absent when no per-token fee is reported |
| estimated_amounts[].fee_precise_amount   | string | Same fee in the token's smallest unit; absent under the same condition |

---

## SEPA Transfer Execute

### POST /api/v1/bank/transfer

Execute a SEPA transfer using the estimation ID (the guide now requires it; the API reference also lists a direct amount).

**Request Headers:**

| Header         | Required | Description                        |
|---------------|----------|------------------------------------|
| Authorization  | Yes      | Bearer `{access_token}`           |
| Content-Type   | Yes      | `application/json`                 |
| X-User-Wallet  | Yes      | The user's EOA wallet address      |
| X-Chain-Id     | Yes      | The blockchain chain ID            |

**Request Body (with estimation):**

```json
{
  "account_id": "{account_id}:{details_id}",
  "token_address": "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606",
  "estimation_id": "uuid-estimation-id",
  "recipient": {
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "recipient_account": {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX"
  }
}
```

**Request Body (with direct amount, API reference only):**

```json
{
  "account_id": "{account_id}:{details_id}",
  "token_address": "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606",
  "amount": 100.00,
  "recipient": {
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "recipient_account": {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX"
  }
}
```

**Request Fields:**

| Field          | Type   | Required | Description                                          |
|----------------|--------|----------|------------------------------------------------------|
| account_id     | string | Yes      | The SEPA bank account ID (`{account_id}:{details_id}`) |
| token_address  | string | Yes      | Token to charge from the user's balance |
| estimation_id  | string | Yes (guide) / No* (API reference) | Estimation ID from the estimate step. Single use |
| amount         | number | No*      | API reference only: fiat amount (if not using estimation); dropped from the guides |
| reference      | string | No       | Payment reference                                    |
| transaction_authorization | object | Conditional | Required in `Signature` mode, see [Transaction Authorization](https://docs.wirexapp.com/docs/retail-transaction-authorization) |
| recipient      | object | Yes      | Recipient name details (same as estimate)            |
| recipient_account | object | Yes   | Recipient bank details (same as estimate)            |

*API reference: provide either `estimation_id` or `amount`, not both; the guide requires `estimation_id`. The execute is not idempotent: a retry with the same `estimation_id` is refused with `ErrorExpired`, request a new estimate. Recipient fields: `first_name` + `last_name` for a person, `company_name` for a business. This endpoint always checks `SepaOut3rdParty`, even for the user's own account; `SepaOut1stParty` applies only to the corridor flow.

**Response (200 OK):**

```json
{
  "id": "uuid-activity-id"
}
```

The `id` is the activity ID for tracking the transfer progress via webhooks.

---

## ACH Bank Details

ACH accounts are available to users residing in these 48 countries (plus all US states and territories except Texas (TX) and New York (NY), where users cannot open a USD account; the USD account supports both ACH and Fedwire): AD, AR, AU, AT, BE, BR, BG, CL, CO, CY, CZ, DK, EE, FI, FR, DE, GI, GR, HK, HU, IS, ID, IE, IT, LV, LT, LU, MY, MT, MX, MC, ME, NL, NO, PE, PL, PT, RO, SG, SK, ES, SE, CH, TW, TH, GB, US, VN. Check the `AchAccount` capability (`NotAvailable`, `NotFulfilled`, `ExternalProviderRegistrationPending`, `ActivationNotStarted`, `InProgress`, `Active`) in `GET /api/v2/user`.

### AchAccount activation (Bridge, `XDDBridgeBase`)

ACH accounts are issued through an external provider, Bridge: on top of `SDD` the user must complete the level `XDDBridgeBase`, and Wirex registers the user with Bridge before activation. The capability lists the levels in `verification_requirements` (`SDD` order 1, `XDDBridgeBase` order 2).

| Status | Meaning | Next step |
|--------|---------|-----------|
| `NotAvailable` | Country is not supported | none |
| `NotFulfilled` | A level in `verification_requirements` is missing | `POST /api/v1/user/verification-token` or `/verification-link` with `{"verification_level": "XDDBridgeBase"}`; the user completes SumSub |
| `ExternalProviderRegistrationPending` | Not yet registered and verified with Bridge | Poll `GET /api/v2/user`; do not call activation yet |
| `ActivationNotStarted` | Ready | `POST /api/v1/bank/accounts` |
| `InProgress` | Account being provisioned | Wait for the bank account webhook |
| `Active` | Provisioned | `GET /api/v1/bank/accounts` |

An omitted or unrecognised `verification_level` silently falls back to `SDD`, so a user who holds `SDD` never reaches `XDDBridgeBase` and `AchAccount` stays `NotFulfilled`. `sdk.api.baas.user.getVerificationToken()` / `getVerificationLink()` send an empty body and cannot pass the level: call REST. The user must hold `SDD` before starting `XDDBridgeBase`.

### Activate ACH Bank Account

**POST /api/v1/bank/accounts**

Creates ACH bank account credentials (account number and routing number) for the user.

**Request Body:**

```json
{
  "account_type": "Ach"
}
```

**Response (200 OK):**

```json
{
  "details_id": "uuid-details-id"
}
```

After activation the capability becomes `InProgress` and a bank account webhook is sent when the account is ready. Then use `GET /api/v1/bank/accounts` to retrieve the full account details (account number, routing number). The response follows the same structure as SEPA (`data[]`), with `details.account_number` and `details.routing_number`.

---

## ACH Transfer Estimate

### POST /api/v2/bank/transfer/estimate

Estimate the cost and exchange rate for an ACH transfer.

**Request Body:**

```json
{
  "account_id": "{account_id}:{details_id}",
  "amount": 250.00,
  "tokens": ["0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2"],
  "recipient": {
    "first_name": "Bob",
    "last_name": "Johnson"
  },
  "recipient_account": {
    "account_number": "1234567890",
    "routing_number": "021000021",
    "bank_name": "Chase Bank",
    "legal_address": {
      "line1": "123 Main Street",
      "line2": "Suite 100",
      "city": "New York",
      "state": "NY",
      "zip_code": "10001",
      "country": "US"
    }
  }
}
```

**ACH-Specific Request Fields:**

| Field                                    | Type   | Required | Description                      |
|------------------------------------------|--------|----------|----------------------------------|
| recipient_account.account_number         | string | Yes      | Recipient bank account number    |
| recipient_account.routing_number         | string | Yes      | ABA routing number               |
| recipient_account.bank_name              | string | No (API reference) / Yes (ACH guide) | Name of the recipient's bank |
| recipient_account.legal_address          | object | Yes      | Recipient's legal address        |
| recipient_account.legal_address.line1    | string | Yes      | Street address                   |
| recipient_account.legal_address.line2    | string | No       | Additional address info          |
| recipient_account.legal_address.city     | string | Yes      | City                             |
| recipient_account.legal_address.state    | string | No (API reference) / Yes for US (ACH guide) | State/province code |
| recipient_account.legal_address.zip_code | string | Yes      | Postal/ZIP code                  |
| recipient_account.legal_address.country  | string | Yes      | ISO 3166-1 alpha-2 country code  |

**Response (200 OK):**

Uses the same response format as SEPA estimates (`amount` is what the recipient receives; `estimated_amounts[].amount` is the debit, fee included; `rate` is USD per 1 token):

```json
{
  "id": "uuid-estimation-id",
  "expires_at": 1704110400,
  "amount": 250.00,
  "currency": "USD",
  "estimated_amounts": [
    {
      "amount": 250.00,
      "precise_amount": "250000000000000000000",
      "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
      "token_symbol": "WUSD",
      "rate": 1.0
    }
  ]
}
```

`legal_address` is mandatory for ACH recipients (`recipient` and `recipient_account` are required on ACH estimates). The API reference schema marks `recipient_account.legal_address` as required in general, while the SEPA guide examples omit it.

---

## ACH Transfer Execute

### POST /api/v1/bank/transfer

Execute an ACH transfer.

**Request Body:**

```json
{
  "account_id": "{account_id}:{details_id}",
  "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
  "estimation_id": "uuid-estimation-id",
  "recipient": {
    "first_name": "Bob",
    "last_name": "Johnson"
  },
  "recipient_account": {
    "account_number": "1234567890",
    "routing_number": "021000021",
    "bank_name": "Chase Bank",
    "legal_address": {
      "line1": "123 Main Street",
      "city": "New York",
      "state": "NY",
      "zip_code": "10001",
      "country": "US"
    }
  }
}
```

**Response (200 OK):**

```json
{
  "id": "uuid-activity-id"
}
```

The `id` is the activity ID for tracking the transfer progress via webhooks.

---

## Activity Webhook

**Endpoint:** `/v2/webhooks/activities`

SEPA and ACH transfers emit activity events as the transfer progresses through each step.

**Steps:** Initiated → CryptoOut → Review → BankOut → Completed

Activity `status` is `Pending`, `Completed` or `Failed` (there is no `Cancelled` status: a cancelled movement reads `Failed`). SEPA activities have `type: Sepa`, ACH `type: AchPush`.

See [wirex-baas-webhooks reference](../wirex-baas-webhooks/references/REFERENCE.md) for complete activity webhook payloads (activity types `Sepa` / `AchPush`).

---

## Error Codes

All errors follow the standard Wirex BaaS error format with nested `error_category`:

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Recipient IBAN is invalid",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "field", "details": "iban" }
  ]
}
```

### SEPA Error Codes

| Error Reason | Field / Description |
|-------------|-------------|
| `ErrorMissingField` / `ErrorInvalidField` / `ErrorNotFound` | `account_id`: required / invalid format / not found or not owned by user |
| `ErrorMissingField` | `recipient`, `recipient_account.iban`, `recipient_account.bic`, `amount` (amount or `estimation_id` required) |
| `ErrorInvalidField` | `recipient_account.iban` / `.bic` invalid format; `token_address` invalid |
| `ErrorGeneral` | `Capability is not active`: `SepaOut3rdParty` is not `Active` (the endpoint always checks it) |
| `ErrorGeneral` (400) | Activation: "Account capability does not need activation or is not available"; wallet linking: "External provider wallet verification is not required for this account" |
| `ErrorInvalidField` (400) | `chain` not numeric or unsupported (error reports the field as `chain_id`) |

These endpoints never return `404`: a missing or ineligible resource is a `400`.

### ACH Error Codes

| Error Reason | Description |
|-------------|-------------|
| `ErrorNotFound` | User not found or not verified |
| `ErrorInvalidStatus` | `AchAccount` is not `ActivationNotStarted` on activation: verification missing, Bridge registration pending, or already activated |
| `ErrorInvalidField` | Invalid account type |
| `ErrorGeneral` | Transfer: `Capability is not active`, `AchOut3rdParty` is not `Active` (the endpoint always checks it) |
| `ErrorMissingField` | `legal_address` and other required recipient fields |

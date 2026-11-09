---
name: wirex-baas-webhooks
description: "Wirex BaaS webhooks and activity history — receive real-time event notifications and query transaction history. Covers all v2 webhook endpoints (wallets, balances, cards, card-limits, 3ds, activities, recipients, erc-withdrawals, user, debt-cases, corporations), v1 legacy webhooks (users, accounts/fiat), delivery specs (POST JSON, 10s timeout, up to 5 retries with exponential backoff), and the activity history feed (GET /api/v2/activity/feed, plus v1/v3, single, search, with pagination and filters)."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Webhooks & Activity History

Wirex BaaS uses webhooks to notify partners of state changes in real time. This skill covers all webhook endpoints (v2 and v1 legacy), delivery semantics, payload structures, and the activity history feed API.

## Webhook Delivery Semantics

| Property | Value |
|----------|-------|
| **Method** | HTTP POST |
| **Content-Type** | `application/json` |
| **Timeout** | 10 seconds |
| **Retries** | A failed delivery is retried up to 5 times with exponential backoff, then dropped. Retries can arrive out of order and more than once |
| **Authentication** | None -- no auth headers are added to webhook requests |

Webhooks are delivered to your **webhook base URL** (HTTPS), which Wirex configures for your company during onboarding; the paths below are appended to it (`POST {your_webhook_base_url}/v2/webhooks/wallets`).

> **Security:** Since no authentication headers are included, you are responsible for validating webhook origin through network-level controls such as **IP allowlisting** (contact Wirex for the list of webhook source IPs) or **payload verification**.

Your webhook receiver must:

1. Return a **2xx HTTP status** within **10 seconds**.
2. Implement **idempotent handlers** -- duplicate events must be processed safely.
3. Offload heavy processing to an **async queue** -- do not block the response while processing business logic.

If the receiver does not respond with 2xx within the timeout window, the delivery is retried up to 5 times with exponential backoff, then dropped; retries can arrive out of order and more than once, so treat each payload as the latest state of the entity. Monitor your webhook logs and implement a polling fallback using the activity history feed for critical flows.

---

## V2 Webhook Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/v2/webhooks/wallets` | Wallet creation and status changes (Confirmed, Rejected, Unknown) |
| `/v2/webhooks/balances` | Token balance updates |
| `/v2/webhooks/cards` | Card status and data changes |
| `/v2/webhooks/card-limits` | Spending limit and usage updates |
| `/v2/webhooks/3ds` | 3D Secure transaction confirmations |
| `/v2/webhooks/activities` | Transaction and activity feed updates |
| `/v2/webhooks/recipients` | Recipient creation and update notifications |
| `/v2/webhooks/erc-withdrawals` | Pending ERC20 withdrawal requests with validity windows |
| `/v2/webhooks/user` | User profile and verification changes (v2 replacement for `/webhook/users`) |
| `/v2/webhooks/debt-cases` | Operations that left a user account in debt |
| `/v2/webhooks/corporations` | Corporate profile and verification changes (only for corporate integrations) |

---

## V1 Legacy Webhook Endpoints

> These use a legacy format that will be replaced in a future release. `/webhook/users` is superseded by `/v2/webhooks/user` (both are delivered); treat it as legacy for new integrations.

| Endpoint | Purpose |
|----------|---------|
| `/webhook/users` | User status and verification status changes |
| `/webhook/accounts/fiat` | Bank account creation and details updates |

---

## Activity Types

The activity system categorizes all financial operations. Each activity has a `type`, `status`, `direction`, and a sequence of `activity_steps`.

### Activity Type Values

| Type | Description |
|------|-------------|
| `Crypto` | On-chain crypto transfer (both directions) |
| `Deposit` | Deposit into the user's wallet (inbound) |
| `Withdrawal` | Withdrawal from the user's wallet (outbound) |
| `Exchange` | Token exchange within wallet (internal) |
| `Sepa` | SEPA bank transfer |
| `AchPull` | ACH pull transfer |
| `AchPush` | ACH push transfer |
| `FasterPayment` | UK Faster Payments transfer |
| `Swift` | SWIFT international transfer |
| `Spei` | Mexican SPEI transfer |
| `CardTransaction` | Card transaction (purchase or refund); payload may carry a `sub_type` such as `POS` |
| `ExternalCardTransaction` | Transaction on an external card |
| `CardTransfer` | Push to card transfer |
| `CardFeesPayment` | Card-related fee payment |
| `CardTopup` | Card top-up (inbound, `ExternalCard` source to `Wallet` destination) |
| `YieldClaim` | Yield or reward claim |

The API reference enum additionally lists `Pix`, `FpsHk`, `Imps`, `Instapay`, `BiFast`, `Nip`, `Ipp`, `Pse`, `Fedwire`, `Chats`, `Cips`, `SavingsTransaction`, `LoanTransaction`, `Cryptoback` (the Activity History guide's type table omits `Spei` and `CardTopup`, which are in the API reference enum; the webhooks guide lists `Spei`).

### Activity Status Values

| Status | Meaning |
|--------|---------|
| `Pending` | Transaction in progress |
| `Completed` | Transaction successfully finished |
| `Failed` | Transaction failed or was cancelled (see `status_reason`) |

There is no `Cancelled` status: a cancelled movement reads `Failed`. A card purchase refunded or reversed in full reads `Failed`; a partial refund leaves it `Completed`. A card purchase stays `Pending` until its debit settles.

### Activity Direction Values

| Direction | Meaning |
|-----------|---------|
| `Inbound` | Funds received into the user's wallet |
| `Outbound` | Funds sent from the user's wallet |
| `Internal` | Movement within the user's accounts (e.g., exchange) |

### Activity Step Types

Each activity progresses through a sequence of steps. The `activity_steps` array tracks each step's type, status and timestamps (`created_at`, `completed_at`).

| Step Type | Description |
|-----------|-------------|
| `Initiated` | Transaction started |
| `CryptoIn` | Tokens credited to user wallet |
| `CryptoOut` | Tokens debited from user wallet |
| `BankIn` | Fiat received from bank |
| `BankOut` | Fiat sent to bank |
| `Review` | Manual or compliance review |
| `CardOut` | Fiat sent to card network / merchant |
| `CardIn` | Fiat received from card network / merchant (refund) |
| `Reversal` | Transaction reversed |
| `SyntheticWrap` | Tokens wrapped to synthetic tokens |
| `SyntheticUnwrap` | Tokens unwrapped from synthetic tokens |
| `Completed` | Transaction finalized |

The API reference enum also has `Trade`, `IntentClaim`, `IntentFill`, `IntentResolve`.

### Operations

Each activity carries an `operations[]` array -- the on-chain operations of that one transaction (e.g. an authorization, its refund and a reversal). Fields: `operation_id`, `hash`, `operation_amount` (crypto; negative when debited), `transaction_amount` (fiat; negative when debited), `resulting_balance` (balance after the operation), `rate`, `status`, `status_reason`. In **v2/v3** every related operation is returned with its `status`; in **v1** only `Completed` operations are returned and each `status` is `null`.

Every amount in the feed carries `amount_precise` (exact base-unit string) and `decimals` next to the float `amount`.

---

## Implementation Best Practices

> **WARNING:** A failed delivery is retried up to 5 times with exponential backoff, then **dropped**. Retries can arrive out of order and more than once. Implement polling fallback for critical flows.

**Webhook handling flow:**

1. Receive POST → validate payload → return `2xx` immediately (within 10 seconds)
2. Enqueue payload for async processing (SQS, RabbitMQ, Redis Streams)
3. Process idempotently — use the activity `id` or another unique identifier to deduplicate
4. Log every received webhook (timestamp, endpoint, payload hash) for debugging
5. Poll the activity history feed (`GET /api/v2/activity/feed`) as fallback for missed webhooks

You may receive several webhooks for one transaction as it progresses (e.g. `status=Pending` with only `Initiated`, later `Completed` with more steps).

---

## Activity History Feed

The activity history endpoints provide a paginated, filterable feed of user activities. Use them as a fallback for missed webhooks or for building transaction history UIs.

| Endpoint | Notes |
|----------|-------|
| `GET /api/v2/activity/feed` | **Recommended** for a single-chain integration; every operation with its status |
| `GET /api/v3/activity/feed` | Same shape as v2, read across **every chain** the user holds activity on (e.g. Bridge-rail cards); read each entry's `chain_id` |
| `GET /api/v1/activity/feed` | Earlier version; operations differ as described above |
| `GET /api/v{1,2,3}/activity/single/{id}` | One transaction by its activity `id` (the transaction id); response is the activity object directly, not wrapped in `data` |
| `GET /api/v2/activity/search`, `GET /api/v3/activity/search` | Full-text search over the owner's activities |

`GET /api/v1/transactions/card` is deprecated; use the v2 feed with `?types=CardTransaction`.

### GET /api/v2/activity/feed

**Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <access_token>` |
| `X-Chain-Id` | Chain id — `84532` (sandbox) or `8453` (production) |
| `X-User-Wallet` | The user's EOA address (with an S2S token; a Wirex user token carries identity) |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page_number` | integer | No | Page number, **0-based** (default: `0`) |
| `page_size` | integer | No | Items per page (default: `25`, **max: `50`**) |
| `sort` | string | No | `name` (default) or `usage` |
| `types` | string[] | No | Activity type(s); **repeat the parameter** for several (`types=CardTransaction&types=Sepa`). Case-insensitive. A comma-separated value is **not** supported and returns `400` |
| `subject` | string | No | Filter by a card ID (UUID), wallet address, or account reference |

**Important:** `types` and `subject` are **mutually exclusive** — send one or the other, not both. The feed cannot be filtered by transaction ID; use the single-activity endpoint.

### Search

`GET /api/v2/activity/search?predicate=...` -- `predicate` is required, 1-128 characters matching `^[A-Za-z0-9 \-_.@:/+]{1,128}$` (quotes, backslashes, backticks, semicolons, brackets, pipes and control characters are refused with `400`); `page_number`, `page_size` (default 25, max 50). Same response shape as the feed; scoped to the authenticated owner. `GET /api/v3/activity/search` accepts up to five `predicate` parameters (`?predicate=amazon&predicate=4821`); an activity must match all of them.

### Subject Types

`source` and `destination` carry a `type` plus a sub-object with the fields below.

| Subject Type | Description | Fields |
|-------------|-------------|--------|
| `Wallet` | User wallet | `wallet.address` |
| `ExternalWallet` | External crypto address | `wallet.address` |
| `Cards` | User's card | `card.id`, `card.pan_last`, `card.payment_system` |
| `ExternalCard` | External card (push to card) | `card.id`, `card.pan_last`, `card.payment_system` |
| `Merchant` | Card merchant | `merchant.id`, `name`, `category`, `full_address` (and `logo_url`, `mcc`, ...) |
| `SepaBankAccount` | SEPA bank account | `bank_account.iban`, `bic`, `owner_name`, `is_business` |
| `AchBankAccount` | ACH bank account | `bank_account.account_number`, `routing_number`, `owner_name` |
| `FasterPaymentBankAccount` | UK bank account | `bank_account.account_number`, `sort_code`, `owner_name` |
| `SwiftBankAccount` | SWIFT bank account | `bank_account.iban`, `bic`, `owner_name` |

The API reference lists further subject types (other local rails, `SpeiBankAccount`, `CrossChainWallet`, `SavingsAccount`, `LoanPosition`, ...).

### Response Structure

The feed response is a `data` array (there is no pagination envelope):

```json
{
  "data": [
    {
      "id": "beedaf4f-d0de-48ee-8bdf-c6c624af90ef",
      "user_address": "0x465Da298F22977628d5F85471db9648C54D88C62",
      "chain_id": 8453,
      "type": "Sepa",
      "status": "Completed",
      "status_reason": "credit_done",
      "direction": "Inbound",
      "source": {
        "type": "SepaBankAccount",
        "bank_account": { "iban": "MT22CFTE19870000000090010248742", "bic": "CFTEMTM1", "owner_name": "Alex Grey", "is_business": false }
      },
      "destination": {
        "type": "Wallet",
        "wallet": { "address": "0x6fb0fCA78F4b717fbAaB89c96754200355554832" }
      },
      "source_amount": { "amount": 50, "amount_precise": "50000000000000000000", "decimals": 18, "currency": "EUR" },
      "destination_amount": {
        "amount": 50, "amount_precise": "50000000000000000000", "decimals": 18,
        "token_symbol": "WEUR", "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2"
      },
      "rate": { "ticker": "EUR/WEUR", "rate": 1 },
      "reference": "NJOZWZXIUGWVETREJUJO",
      "operations": [
        {
          "operation_id": "beedaf4f-d0de-48ee-8bdf-c6c624af90ef",
          "operation_amount": { "amount": 50, "token_symbol": "WEUR", "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2" },
          "transaction_amount": { "amount": 50, "currency": "EUR" },
          "resulting_balance": { "amount": 1631.07, "token_symbol": "WEUR", "token_address": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2" },
          "rate": { "ticker": "EUR/WEUR", "rate": 1 },
          "status": "Completed"
        }
      ],
      "activity_steps": [
        { "type": "Initiated", "status": "Completed", "created_at": "2024-01-01T10:15:30.000Z", "completed_at": "2024-01-01T10:15:30.000Z" },
        { "type": "BankIn", "status": "Completed", "created_at": "2024-01-01T10:15:30.000Z", "completed_at": "2024-01-01T10:15:45.000Z" },
        { "type": "CryptoIn", "status": "Completed", "created_at": "2024-01-01T10:15:45.000Z", "completed_at": "2024-01-01T10:15:50.000Z" }
      ],
      "created_at": "2024-01-01T10:15:30.000Z"
    }
  ]
}
```

Fiat amounts carry `currency`; crypto amounts carry `token_symbol` and `token_address`. Optional fields include `fee_amount` (card fees are reported here, not folded into `rate`), `recipient`, `reward`, `rrn` (card transactions) and `sub_type`.

### Filter Examples

Card and SEPA activities (repeat `types`):

```
GET /api/v2/activity/feed?types=CardTransaction&types=Sepa&page_number=0&page_size=50
```

Activities for a specific card (UUID) or wallet address:

```
GET /api/v2/activity/feed?subject=00000000-0000-0000-0000-000000000001
GET /api/v2/activity/feed?subject=0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE
```

### Error Responses

| Error Reason | Issue | Description |
|-------------|-------|-------------|
| `ErrorInvalidField` | `invalid_format` | Invalid format of `subject` |
| `ErrorInvalidField` | `mutually_exclusive` | Both `types` and `subject` were provided |
| `ErrorInvalidField` | `max_exceeded` | `page_size` greater than `50` |

Error response body (`400`):

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Fields are mutually exclusive",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "fields", "details": "types,subject" },
    { "key": "issue", "details": "mutually_exclusive" }
  ]
}
```

---

See [references/REFERENCE.md](references/REFERENCE.md) for complete webhook payload examples for every endpoint.

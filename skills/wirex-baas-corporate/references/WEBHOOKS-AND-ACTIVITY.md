# Wirex BaaS Corporate — Webhooks, Activity, Statements, Errors and Validation

Guides: [Webhooks](https://docs.wirexapp.com/docs/corporate-webhooks), [Activities](https://docs.wirexapp.com/docs/corporate-activities), [Activity History](https://docs.wirexapp.com/docs/corporate-activity-history), [Statements](https://docs.wirexapp.com/docs/corporate-statements), [Error Reference](https://docs.wirexapp.com/docs/corporate-error-reference), [Field Validation Rules](https://docs.wirexapp.com/docs/corporate-validation-rules), [Feature Parity](https://docs.wirexapp.com/docs/corporate-feature-parity).

## Table of Contents

- [Webhook Delivery](#webhook-delivery)
- [Webhook Endpoints](#webhook-endpoints)
- [Corporation Webhook Payload](#corporation-webhook-payload)
- [What Is Not Delivered](#what-is-not-delivered)
- [Activity Feed](#activity-feed)
- [Withdrawal Requests](#withdrawal-requests)
- [Statements](#statements)
- [Error Format](#error-format)
- [Error Reasons and Categories](#error-reasons-and-categories)
- [Validation Rules](#validation-rules)
- [Retail vs Corporate Parity](#retail-vs-corporate-parity)

---

## Webhook Delivery

The same dispatcher serves retail and corporate companies, so delivery and payload shapes are shared.

- HTTP POST with a JSON body, `Content-Type: application/json`.
- Timeout 10 seconds per request. Failed deliveries are logged and **not retried**. Deliveries can repeat: make handlers idempotent.
- No authentication headers are added. Validate origin at network level (IP allowlisting).
- One webhook base URL per company (configured at onboarding); there is no per-corporation URL. Route on `corporation_address` in the payload. Wallet and balance events are addressed by wallet address, not corporation id: match `wallet_address` against `GET /api/v1/wallets`.

## Webhook Endpoints

Delivered to `{your_webhook_base_url}` plus the path.

| Path | Entity | Delivered when |
|---|---|---|
| `/v2/webhooks/corporations` | Corporation | Profile, status or KYB verification status changes |
| `/v2/webhooks/wallets` | Wallet | A corporation wallet is created or its confirmation status changes |
| `/v2/webhooks/balances` | Balance | A token balance changes on a corporation wallet |
| `/v2/webhooks/cards` | Card | A card is issued or its status or data changes |
| `/v2/webhooks/card-limits` | Card limit | A limit or its usage changes |
| `/v2/webhooks/3ds` | 3DS request | A 3DS challenge is raised |
| `/v2/webhooks/activities` | Activity | A transaction or feed item is created or updated |
| `/v2/webhooks/recipients` | Recipient | A recipient is created or updated |
| `/v2/webhooks/erc-withdrawals` | ERC withdrawal | A withdrawal request awaits on-chain execution |

`/v2/webhooks/user` and `/v2/webhooks/debt-cases` carry retail entities and are not delivered for corporations. The wallet, balance, card, card-limit, 3DS, activity, recipient and ERC-withdrawal payloads are the shared retail shapes (see the retail [Webhooks](https://docs.wirexapp.com/docs/retail-webhooks) guide). The card webhook carries retail-only extras (`generation`, `balances`, `lifetime_limit`, `lifetime_usage`) that the Corporate card list does not.

## Corporation Webhook Payload

Fields: `corporation_address`, `owner_address`, `corporation_id`, `corporation_name`, `corporation_type`, `verification_status` (`Pending`, `Applied`, `InReview`, `Approved`, `Rejected`, `Canceled`), `status` (`Pending`, `Active`, `Blocked`, `Deleted`), `registration_number`, `corporation_registration_address` and `corporation_contact_details` (omitted until KYB supplies them), `freshdesk_id`.

It is narrower than `GET /api/v1/corporations`: no `capabilities`, `actions` or `verification_levels`. Treat it as a signal to re-read the corporation.

## What Is Not Delivered

No webhook for employees, roles, bank account activation, FX swaps or bulk transfer approval. Poll after the triggering call:

| Change | How to observe |
|---|---|
| Employee invited, updated, deleted | `GET /api/v1/employees` |
| Role created, updated, deleted | `GET /api/v1/roles` |
| Bank account details activated | `GET /api/v1/bank/accounts` (details appear when `Active`) |
| Capability became active | `GET /api/v1/corporations`, read `capabilities[].status` |
| FX swap settled, bulk transfer executed | `GET /api/v1/activity/feed` |

## Activity Feed

`GET /api/v1/activity/feed` (no permission). It is where every asynchronous outcome lands (FX, bulk and corridor transfers have no status endpoint).

Query: `page_number` (starts at `0`; `1` is the second page), `page_size` (default 25, **maximum 50**), `sort` (`name` or `usage`; neither orders by time), and one of `types[]` or `subject` (**mutually exclusive**, else `400 ErrorInvalidField` / `Fields are mutually exclusive`). `subject` is a wallet address, card id or account reference and must parse as an address or UUID; a bank account's composite `<accountId>:<detailsId>` is not a valid subject. No date filter, no free-text search, no single-item read: read the feed and filter on `id` (use statements for a period).

Item fields: `id` (matches the `id` returned by the transfer that created it), `corporation_address`, `type`, `sub_type`, `status` (`Pending`, `Completed`, `Failed`; a fully refunded card payment reads `Failed`, a partial refund stays `Completed`; see the Activity Status table in the guide), `status_reason`, `direction` (`Inbound`, `Outbound`, `Internal`), `created_at`, `reference`, `rrn` (card transactions), `source`, `destination`, `source_amount`, `destination_amount`, `fee_amount`, `rate`, `recipient`, `reward` (`Cashback`, `Bonus`), `operations[]` (`hash`, `operation_amount`, `transaction_amount`, `rate`), `activity_steps[]`.

Activity types: `Deposit`, `Withdrawal`, `Exchange`, `Crypto`, `Sepa`, `FasterPayment`, `AchPull`, `AchPush`, `Swift`, `Spei`, `CardTransaction`, `ExternalCardTransaction`, `CardTransfer`, `CardFeesPayment`, `YieldClaim`, `Fedwire` (outbound `fedwire` payout or inbound deposit; `direction` tells them apart), `FedNow` (incoming only); the `types` filter also accepts the corridor types `Pix`, `FpsHk`, `Imps`, `Instapay`, `BiFast`, `Nip`, `Ipp`, `Pse` (case-insensitive; unknown values give `Invalid value for types`).

Step types: `Initiated`, `CryptoIn`, `CryptoOut`, `BankIn`, `BankOut`, `CardIn`, `CardOut`, `SyntheticWrap`, `SyntheticUnwrap`, `Trade`, `Review`, `Reversal`, `Completed`. Each step has its own `status`, so a `Pending` activity shows where it is. A `Review` step means a compliance hold (not a failure, will not clear on retry); `Reversal` means funds are being returned.

Subject types for `source` / `destination`: `Wallet`, `Card`, `Merchant`, `ExternalCard`, `ExternalWallet`, `SepaBankAccount`, `FasterPaymentBankAccount`, `AchBankAccount`, `FedwireBankAccount`, `FedNowBankAccount`, `SwiftBankAccount`, `SpeiBankAccount`, `CardFeesPayment`.

The activity webhook payload matches a feed item. Poll the feed for anything you must not miss.

## Withdrawal Requests

`GET /api/v1/withdrawal/requests` (no permission) lists ERC-20 withdrawals awaiting on-chain execution: `account_address`, `to_address`, `token_address`, `amount`, `hash`, `call_data`, `valid_after`, `valid_before`. They are prepared calls, not completed movements. `valid_after` reflects the `ExecutionDelayCorporatePolicy` time-lock; execution is possible only between `valid_after` and `valid_before`, outside which the request must be re-requested. Also delivered to `/v2/webhooks/erc-withdrawals`.

## Statements

`POST /api/v1/activity/statement/full` (no permission):

```json
{
  "start": 1,
  "end": 2
}
```

Replace the placeholders with Unix timestamps in seconds. `start` rounds down and `end` rounds up to day boundaries; both positive, `start` strictly before `end`, window **at most 6 months** (`End time must be within 6 months from start time`).

Response: `owner` (wallet address), `chain_id`, `created_at`, `period`, `company_data`, `company_bank_accounts`, `balances[]` (`currency`, `opening`, `closing`, `debit`, `credit`), `transactions[]` (`id`, `type`, `direction`, `amount`, `currency`, `created_at`, `updated_at`, `source`, `destination`, `operations[]` with `account_address`, `token_address`, `token_symbol`, `amount`, `resulting_balance`, `hash`, `created_at`). Exact values come as `*_precise` integer strings (`opening_precise`, `closing_precise`, `debit_precise`, `credit_precise`, `amount_precise`, `resulting_balance_precise`) with a sibling `decimals` that is always `18` here, not the token's decimals: a token whose decimals differ from 18 is rescaled, so its value no longer matches `balance_precise` on `GET /api/v1/wallets`.

Statement timestamps are Unix seconds, not ISO 8601 as in the feed. The statement covers the one chain fixed into the corporation token; log in against each chain for more. JSON only (no PDF/CSV), not paginated, no statement history; consecutive windows must not overlap on the join date.

## Error Format

Every failing call returns one envelope:

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Human-readable message",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "field", "details": "email" },
    { "key": "issue", "details": "invalid_format" }
  ]
}
```

Branch on `error_reason`, never parse `error_description`. Validation errors come in two shapes: **structured** (`error_details` key `field` carries the field name, often with `issue` and `pattern`; corporations, bank, recipient and v1 card endpoints) and **keyed** (the field is the `key`, description is `Request failed validation`; employee, role, FX and v2 card endpoints). Handle both.

Note: docs differ. The API reference schema types `error_reason` as an object (`reason`); the guides and every example show `error_reason` as a plain string. Read it defensively. `error_category.grpc_status_code` (informational) is now shown in the guides too.

The rate limiter on `POST /api/v1/token` returns `ErrorTooManyRequests` under `CategoryInternalFailure`, HTTP `500` not `429`; it applies to repeated failed attempts (successful exchanges are not counted). Branch on `error_reason` and back off.

## Error Reasons and Categories

| Category | HTTP | Meaning |
|---|---|---|
| `CategoryValidationFailure` | 400 | Request rejected |
| `CategoryUnauthorized` | 401 | Authentication failed |
| `CategoryForbidden` | 403 | Role lacks the permission |
| `CategoryTransientFailure` | 429 | Transient rejection |
| `CategoryInternalFailure` | 500 | Server-side failure |
| `CategoryTransportFailure` | 503 | Downstream service unreachable |

`error_reason` values: `ErrorMissingField`, `ErrorInvalidField`, `ErrorInvalidStatus`, `ErrorNotFound`, `ErrorAlreadyExists`, `ErrorPermissionDenied`, `ErrorNotSupported`, `ErrorExpired`, `ErrorTooManyRequests`, `ErrorInsufficientFunds`, `ErrorLimitExceeded`, `ErrorConfigurationInvalid`, `ErrorGeneral`, `ErrorUnknown`, `ErrorResponseInvalid`, `ErrorInvalidMethod`, `ErrorTimeout`, `ErrorInitFailed`, `ErrorNotImplemented`, `ErrorDeadlinesExceeded`, `ErrorCanceled`, `ErrorReverted`, `ErrorNotYetValid` (a time-locked withdrawal before `valid_after`).

Auth errors: partner-token requests to non-partner endpoints get `401 ErrorNotSupported` (`No authorization provider found for requested method`); `401 ErrorExpired` / `Token is expired`; `403 ErrorPermissionDenied` / `User does not have any permissions` or `User does not have required permissions`; a corporation token missing a claim returns `401 ErrorMissingField` (e.g. `Employee address claim is missing`, meaning no wallet bound: log in with `X-User-Wallet`).

## Validation Rules

`GET /api/v1/validation/rules` (anonymous) publishes regexes at runtime; four differ from what is enforced, and the enforced pattern decides.

Note: docs differ. Published `firstName` / `lastName` `^[a-zA-Z][a-zA-Z\-']{1,50}$` rejects names with a space and single-character names, which the API accepts, and accepts 51 characters, which the API rejects; enforced is `^[a-zA-Z][a-zA-Z\-' ]{0,49}$`. Published `state` is `^[A-Za-z\s\-']{2,100}$`, enforced `^[A-Za-z][A-Za-z\s\-']{1,99}$`. Published `department` / `job` patterns are not enforced (any string is accepted). Published `cardNumber` is not used (the API never accepts a full card number).

Enforced patterns:

| Field | Pattern |
|---|---|
| `first_name`, `last_name` (employees) | `^[a-zA-Z][a-zA-Z\-' ]{0,49}$` |
| `email` | `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` |
| `phone` | `^\+\d{1,15}$` |
| `corporation_name`, `company_name` | `^[A-Za-z0-9&.,'’\-/() :+#]{2,100}$` |
| `corporation_registration_number` | `^[A-Z0-9\-]{6,15}$` (uppercase only) |
| `corporation_registration_country`, `country` | `^[A-Z]{2}$` |
| `line1`, `line2` | `^[A-Za-z0-9&.,'’\-/() :+#]{2,100}$` |
| `city` | `^[A-Za-z\s\-'.]{2,100}$` (no digits) |
| `state` | `^[A-Za-z][A-Za-z\s\-']{1,99}$` |
| `postal_code`, `zip_code` | `^[A-Za-z0-9\s\-]{3,12}$` |
| Blockchain address (`corporation_address`, token, wallet) | `^(0x[a-fA-F0-9]{40}\|C[A-Za-z2-7]{55}\|G[A-Za-z2-7]{55}\|T[1-9A-HJ-NP-Za-km-z]{33})$` (EVM, Stellar or Tron form) |
| `manager_address` | `^0x[a-fA-F0-9]{40}$` (EVM only) |
| `name_on_card` | `^[A-Za-z][A-Za-z .'-]{1,25}$` |
| `card_name` | `^[a-zA-Z0-9]+[a-zA-Z0-9\-':+#& ]{1,50}$` |
| Employee search `term` | `^[A-Za-z0-9@._%+' -]{2,100}$` |
| `currency` | `^[A-Za-z0-9]{3,10}$` |

Rail field patterns (IBAN, BIC, sort code, routing number, CLABE, PIX, FPS, IMPS, InstaPay, BI-FAST, NIP, PSE) are in [RECIPIENTS.md](RECIPIENTS.md); card patterns in [CARDS.md](CARDS.md). Employee names accept only unaccented Latin letters (`José` fails); recipient names accept any Unicode letter or digit.

## Retail vs Corporate Parity

Not implemented in the Corporate API: card top-up; XRPL accounts and withdrawals; `GET /api/v1/cards/{cardId}` (use `GET /api/v3/cards/{cardId}`); metal cards; the activity v2 feed, search and single-item read (only `GET /api/v1/activity/feed` exists). Global deposit addresses work as on retail (Rhino.fi, keyed from `GET /api/v1/config`). Everything else in the corporate tree works, including parts that share retail infrastructure (webhook dispatcher, Rhino.fi).

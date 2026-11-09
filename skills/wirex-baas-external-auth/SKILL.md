---
name: wirex-baas-external-auth
description: "Wirex BaaS External Authorization model — partner-managed user balances with Master Account settlement. Covers what the partner must implement (POST .../external/authorize and .../external/settle endpoints, request/response bodies, 300ms target / 500ms max timeout, mandatory vs non-mandatory decision rules, idempotency by unique_operation_id), Master Account setup and funding, simplified user registration without Smart Wallet (POST /api/v2/user with user_address and initial_data), card issuance and card transaction settlement with activity webhooks and reconciliation, and mandatory crypto transaction screening (POST /api/v1/transactions/risk-assessment). Use when a partner holds balances in its own ledger instead of on-chain Wirex wallets."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS External Authorization

## Overview

External Authorization is an alternative integration model for **retail** partners:

- The partner manages user balances in its own system (its ledger is the source of truth).
- Wirex calls the partner's authorization API before processing card transactions.
- All transactions settle against a partner-prefunded **Master Account** (a Wirex Business account).
- No per-user Smart Wallet deployment or on-chain registration.
- The partner submits users' crypto transactions to Wirex for risk screening (regulatory requirement).

Docs entry: https://docs.wirexapp.com/docs/retail-external-authorization (changelog: "External Authorization Support"). Pages: [Overview](https://docs.wirexapp.com/docs/retail-extauth-overview), [Registering Users](https://docs.wirexapp.com/docs/retail-extauth-creating-user-2), [Authorization API](https://docs.wirexapp.com/docs/retail-extauth-api), [Card Transactions](https://docs.wirexapp.com/docs/retail-extauth-cards), [Transaction Screening](https://docs.wirexapp.com/docs/retail-extauth-risk-assessment). The docs cache has no dedicated API reference pages for these endpoints (only the generic `POST /api/v2/user` reference).

Use it when you keep your own balance ledger, need real-time per-transaction authorization logic, and want to avoid per-user on-chain wallet deployment. Use the standard flow when users hold their own on-chain balances and Wirex manages balances.

## Standard vs External Authorization

| Aspect | Standard Flow | External Authorization |
|--------|---------------|------------------------|
| Smart Wallet deployment | Required per user | Not required |
| On-chain registration | Required | Not required |
| User identifier | EOA address | EOA address |
| Balance management | Wirex (on-chain per user) | Partner (external system) |
| Transaction settlement | User's AA wallet | Partner's Master Account |
| Authorization | Internal (Wirex) | External (Partner API) |
| Crypto transaction screening | Automatic | **Partner submits them** |

## Setup: Master Account and enabling

1. Register a Wirex Business account in your organization's name: production https://business.wirexapp.com, sandbox https://business.wirexapp.tech.
2. Complete KYB.
3. Tell your Wirex account manager this account is the Master Account.
4. Ask your account manager to: enable External Authorization for your partner account, link the Master Account, configure your authorization API endpoint URL, and set up webhook endpoints.
5. Fund the Master Account, then implement the endpoints below.

Master Account requirements:
- Minimum balance for the external authorization model: $50,000 or EUR 50,000, or both, as applicable. Declines due to insufficient funds are monitored by card schemes.
- Recommended: 3-5 days of typical transaction volume; monitor and top up proactively.
- Mandatory transactions process even if the balance is insufficient (the Master Account may go negative).
- Non-mandatory transactions are declined when the Master Account balance is insufficient, even if you approve.

## User registration (differs from standard)

Standard onboarding (deploy Smart Wallet, install executor + policy, register in Accounts contract, wait for wallet webhook, register user, KYC) collapses to: 1. register user via API, 2. complete KYC. No blockchain interaction, no wallet webhook; the EOA in `user_address` is only an identifier (not a Smart Wallet address) and no balance exists in Wirex.

```
POST /api/v2/user
Authorization: Bearer <access_token>
X-User-Wallet: <user EOA>
X-Chain-Id: <chain id>
Content-Type: application/json
```

```json
{
  "user_address": "0x1234567890abcdef1234567890abcdef12345678",
  "initial_data": {
    "profile": { "email": "user@example.com" },
    "residence_address": { "country": "GB" }
  }
}
```

Response: `{ "id": "64120850-73a1-4df5-a074-d463258c9deb" }` (the user id).

- `user_address` (required): EOA, 0x-prefixed 40 hex; replaces the former `wallet_address` (both accepted; if both are sent they must match).
- `initial_data.profile.email` (required, unique) and `initial_data.residence_address.country` (required, ISO 3166-1 alpha-2) are **nested under `initial_data`**. A flat body returns `200 OK` but top-level `email`/`country` are ignored, leaving the user without KYC data.
- KYC is identical to the standard integration (see `wirex-baas-onboarding`).

> Note: docs differ. The External Authorization page shows only `email` and `country` under `initial_data`; the API reference for `POST /api/v2/user` marks `initial_data.is_pep`, `profile` (`date_of_birth`, `email`, `first_name`, `last_name`, `nationality`, `phone_number`) and `residence_address` (`city`, `country`, `line1`, `post_code`) as required, and says `initial_data` and `sharing_data` are mutually exclusive. Follow the API reference when the API rejects the short body.

## What the partner must implement

Two HTTPS endpoints that Wirex calls (your base URL is configured by your account manager):

```
POST /external-authorization/on-chain/card-transaction/external/authorize
POST /external-authorization/on-chain/card-transaction/external/settle
```

Flow per card transaction: card network -> Wirex -> `authorize` (you answer `is_allowed`) -> Wirex holds on the Master Account -> later network settlement -> Wirex calls `settle` (you answer `is_processed`) -> Wirex debits the Master Account.

### Performance

| Metric | Requirement |
|--------|-------------|
| Target response time | < 300 ms |
| Maximum round trip | 500 ms |
| Timeout behavior | Declined (non-mandatory transactions) |

Deploy in the same region as Wirex (AWS eu-central-1 / Azure west-europe).

### Authorize request (Wirex -> you)

```json
{
  "transaction_type": "POS",
  "user_id": "5f7e3f7b-8e0c-48b8-9f2c-3e0c9d7a2a11",
  "transaction_id": "a7b2a4b3-2f61-41a7-9f5a-3f3f0b1a3d22",
  "operation_type": "Debit",
  "card_id": "c0b2c7b1-1d2e-4d7a-9a5d-2b7e3c4d5f66",
  "currency": "USD",
  "amount": 123.45,
  "unique_operation_id": "3e1f6a98-6b0a-4c8c-93e5-0b9c6d2a7f31",
  "correlation_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "rates_by_assets": [
    { "ticker": "WUSD/EUR", "buy": 0.88, "sell": 0.85 }
  ],
  "is_mandatory": false,
  "related_external_operation_status": "None",
  "transaction_reason": "Authorization",
  "mcc": "5411"
}
```

Key fields: `transaction_type` (`POS`, `ATM`, `ePOS`, `MoneyTransfer`), `operation_type` (`Debit` purchase/withdrawal, `Credit` refund), `is_mandatory`, `unique_operation_id` (idempotency key), `correlation_id` (optional; never require it), `preferred_payment_currency` (ISO 4217, empty string when no preference), `related_external_operation_status` (`None`, `Rejected`, `Approved`), `transaction_reason` (`Authorization`, `Clearing`, `Refund`, `Reversal`, `OriginalCredit`, `Representment`, `MoneySend`, `DelayAuthorization`), `mcc` (optional). Full field table in [reference](references/REFERENCE.md#authorize-request-fields).

### Authorize response (you -> Wirex)

```json
{
  "transaction_id": "a7b2a4b3-2f61-41a7-9f5a-3f3f0b1a3d22",
  "is_allowed": true,
  "decline_reason": null
}
```

`transaction_id` echoes the request; `is_allowed` true approves, false declines; `decline_reason` optional: `InsufficientFunds` or `GeneralError`.

### Settle request (Wirex -> you)

Same identifying fields as authorize (`transaction_type`, `user_id`, `transaction_id`, `operation_type`, `card_id`, `currency`, `amount`, `unique_operation_id`, `correlation_id`) plus:

```json
{
  "settlement_currency": "USD",
  "settlement_amount": 123.45,
  "settlement_decision": 0,
  "reject_reason": null
}
```

`settlement_decision`: `0` = Approve, `1` = Reject. `reject_reason` optional.

### Settle response

```json
{
  "is_processed": true,
  "error_reason": null,
  "transaction_id": "a7b2a4b3-2f61-41a7-9f5a-3f3f0b1a3d22"
}
```

`error_reason` optional: `InsufficientFunds` or `GeneralError`. Return `is_processed: false` with `GeneralError` when the operation is unknown.

> Note: docs differ. The settle field table says `settlement_decision` 0 = Approve, 1 = Reject, but the code examples treat `settlement_decision === 1` as "finalize debit" and 0 as "release hold" (inverted). Follow the field table and verify against sandbox. The Python/Go authorize examples (not the settle ones) also return an `external_transactions` array (`account_currency`, `account_id`, `amount`, `rate`, `transaction_identifier`) that is not in the authorize response field table.

### Decision rules

| Scenario | Non-mandatory | Mandatory |
|----------|---------------|-----------|
| `is_allowed: true` | Processed | Processed |
| `is_allowed: false` | Declined | Processed |
| Timeout (> 500 ms) | Declined | Processed |
| 5xx error | Declined | Processed |

`is_mandatory: true` covers refunds, chargebacks and network corrections: you are notified but cannot decline them. Your API unavailable: non-mandatory declined, mandatory processed anyway.

### Implementation checklist

1. Idempotency: look up `unique_operation_id` first and return the stored decision on repeats.
2. Mandatory: record the operation and answer `is_allowed: true`.
3. Otherwise compare the user's ledger balance with `amount` in `currency`; if allowed, place a hold; answer with `decline_reason: "InsufficientFunds"` when not.
4. On settle: look up the operation by `unique_operation_id`; finalize the debit or release the hold per `settlement_decision`; respond `is_processed`.
5. Keep responses under 300 ms (the docs' target response time); test timeouts (> 500 ms = decline) and mandatory handling in sandbox.

Code examples (JavaScript, Python, Go) are in the Authorization API docs page.

## Card issuance and transactions

- Issuance works as in the standard flow with the same cards: **v1 (external fee)** you pay the invoice and pass `payment_transaction_hash`; **v2 (direct fee)** Wirex debits the fee automatically, from your **Master Account** (cardholders have no on-chain balance). v3 issuance is not available under External Authorization (see `wirex-baas-cards`).
- Block, unblock, close and set limits work identically to standard integration.
- Settlement source is the Master Account; balance check is your authorization API; balance updates happen in your system.
- After completion Wirex sends `POST {your_webhook_base_url}/v2/webhooks/activities`; use it to update your ledger. The payload is the v2 activity (see Activity History) and the same activity is delivered again each time it changes:

```json
{
  "id": "a7b2a4b3-2f61-41a7-9f5a-3f3f0b1a3d22",
  "user_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "chain_id": 8453,
  "type": "CardTransaction",
  "sub_type": "Pos",
  "direction": "Outbound",
  "status": "Completed",
  "source": { "type": "Cards", "card": { "id": "64120850-73a1-4df5-a074-d463258c9deb", "pan_last": "4821", "payment_system": "Visa" } },
  "operations": [
    {
      "operation_id": "3b0c5f7e-2a1d-4e8f-9c6b-7d5e4f3a2b1c",
      "operation_reason": "Authorization",
      "transaction_amount": { "amount": -123.45, "amount_precise": "-123450000000000000000", "decimals": 18, "currency": "USD" },
      "status": "Completed"
    }
  ],
  "created_at": "2024-01-01T10:00:00Z"
}
```

Handle only `type == CardTransaction`. Book each `Completed` operation once, keyed by `operations[].operation_id` (the `unique_operation_id` of the authorization request); a refund or reversal arrives as a new operation on the activity you already processed. `operations[].transaction_amount` is negative when it debits the user and positive when it credits them. `status` is `Pending`, `Completed` or `Failed`; a purchase refunded or reversed in full reads `Failed`. Refunds are mandatory Credit transactions: the Master Account is credited and you receive the webhook. Transaction history: standard Activity History endpoints (see `wirex-baas-webhooks`); transactions are attributed to users by EOA identifier (`user_address`).
- Reconciliation: you hold the truth for user balances; Wirex tracks only the Master Account. Match approved authorizations to webhooks; the Master Account balance should equal the sum of processed transactions. Discrepancies: mandatory transactions processed without your approval, network timeouts where the transaction succeeded, chargebacks or reversals. Key on `unique_operation_id` for authorization handling and on `operations[].operation_id` for booking settled movements from the activity webhook.

## Transaction screening (mandatory)

Under the standard model Wirex screens crypto deposits and transfers automatically. Under External Authorization nothing is screened unless you submit it. Submitting is a regulatory requirement, part of your pipeline, not an optional report.

```
POST /api/v1/transactions/risk-assessment
Authorization: Bearer <access_token>
X-User-Wallet: <user EOA>
X-Chain-Id: <chain id>
Content-Type: application/json
```

```json
{
  "direction": "Outbound",
  "user_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "amount": 99.99,
  "asset_symbol": "USDC",
  "chain_name": "Base",
  "transaction_hash": "0x0000000000000000000000000000000000000000000000000000000000000001",
  "sender_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "recipient_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

Response `200` with `{}`: accepted into the screening pipeline, **not a risk verdict**; do not gate user actions on it.

Rules:
1. Submit every crypto deposit (`Inbound`) and transfer (`Outbound`) of users onboarded through Wirex, **after on-chain confirmation** (not on broadcast).
2. Do not submit fiat/card activity (already visible to Wirex) or internal ledger movements without an on-chain hash.
3. `user_address` is the address of your user, not the counterparty; it is not inferred from sender/recipient.
4. `chain_name` values are case-sensitive (`Base`, not `BASE`) and use their own vocabulary; list in [reference](references/REFERENCE.md#supported-networks-chain_name).
5. Addresses must match the multi-chain pattern (EVM `0x`, Stellar `C`/`G`, Tron `T`, XRPL `r`); Bitcoin, Cosmos, Solana and Waves addresses do not match it.
6. `amount` must be greater than 0. One call per transaction (no batch). No deduplication: the same `transaction_hash` twice creates two reports, so track what you sent.
7. On `500`, retry with backoff and keep the transaction in an outbox; a dropped report is a compliance gap.

## Error handling

Screening validation errors are `400` with `ErrorInvalidField` or `ErrorMissingField` and a nested `error_category` object, for example:

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "chain_name must be a supported network",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "field", "details": "chain_name" },
    { "key": "issue", "details": "invalid_value" },
    { "key": "chain_name", "details": "BASE" }
  ]
}
```

Per-field messages and `issue` values: [reference](references/REFERENCE.md#screening-validation-errors). See the Error Reference docs page for all reasons.

## Environments

Master Account business portal: production https://business.wirexapp.com, sandbox https://business.wirexapp.tech. API hosts, headers and sandbox credentials: see `wirex-baas-overview` and `wirex-baas-auth`.

## Go-live checklist

- Master Account created, KYB done, linked by Wirex, funded (>= $50,000 / EUR 50,000)
- `/authorize` and `/settle` live in the same region as Wirex, response < 300 ms, idempotent
- Mandatory transactions always accepted
- Webhook handler for `/v2/webhooks/activities` updates internal balances
- Screening submissions after confirmation with retry and dedup tracking
- Sandbox tests: authorization flow, timeout (> 500 ms = decline), mandatory handling, reconciliation

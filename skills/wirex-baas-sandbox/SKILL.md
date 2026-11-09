---
name: wirex-baas-sandbox
description: "Wirex BaaS sandbox testing — simulate real-world scenarios in the development environment. Helper API (ramc.wirexapp.tech) for minting test tokens, creating registered smart wallets, simulating SEPA deposits and transfers (complete/cancel/revert), ACH customer activation and transfers, and card transaction flows (auth + clearing, e-commerce, ATM, refunds, reversals, original credit, adjustments), and 3DS in-app confirmation challenges. Includes sandbox test credentials and token addresses. Interactive docs at ramc.wirexapp.tech/api-docs/."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Sandbox Testing

The Wirex BaaS sandbox environment provides a **Helper API** for simulating real-world financial scenarios without touching production systems. This includes minting test tokens, simulating bank transfers, and triggering card transactions.

## Helper API

| Property | Value |
|----------|-------|
| **Base URL** | `https://ramc.wirexapp.tech` |
| **Interactive Docs** | `https://ramc.wirexapp.tech/api-docs/` |
| **Identification** | User's `email` (all endpoints identify accounts by email); ACH transfer complete/revert use `externalId` instead |
| **Availability** | Sandbox only -- not available in production |

The Helper API is separate from the main BaaS API (sandbox: `https://api-baas.wirexapp.tech`, production: `https://api-baas.wirexapp.com`). It simulates external events that cannot be triggered through the standard API (bank deposits, transfer completions, card transactions) and triggers the same webhooks and state changes as production.

---

## Sandbox Test Credentials

Shared credentials for initial integration testing with the **main BaaS API** (not the Helper API). Contact Wirex for dedicated credentials for your company.

| Credential | Value |
|------------|-------|
| `client_id` | `3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB` |
| `client_secret` | `6FIY2GEQvdlgUEFHw4Dbii22_wCAqZ37lWV3TEMfTlkxrn8F5IbdgX9TiAvQUEsC` |
| `partner_id` | `0x00000000000000000000000000000044` |

### Sandbox Chains

| Chain | Chain ID |
|-------|----------|
| Base Sepolia | `84532` |
| Stellar Testnet | `9223372036854775806` |

### Sandbox Token Addresses (Base Sepolia, Chain ID: 84532)

| Token | Address | Decimals |
|-------|---------|----------|
| WUSD | `0x0774164DC20524Bb239b39D1DC42573C3E4C6976` | 18 |
| WEUR | `0x5c55F314624718019A326F16a62A05D6C6d8C8A2` | 18 |
| USDC | `0x7Af7cDbd557eD302F7538Db1e3d094C8BBcA665c` | 6 |
| USDT | `0x2C6c7c00ACa9B9D8446d107367485079b0471706` | 18 |
| EURC | `0xF70461ffb413981852683657A310892227e3989e` | 6 |

> Docs advise reading token addresses and `decimals` from `GET /api/v1/config/tokens` (per company and per chain) rather than hardcoding them. The sandbox ContractRegistry on Base Sepolia is `0xC801a0f38E20500B5840c4927553b3409890bc3c`.

---

## Mint Test Tokens

```
POST /account/retail/mint
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chainId` | string | Yes | `84532` (Base Sepolia) |
| `token` | string | Yes | Token contract address |
| `to` | string | Yes | The user's smart wallet address |
| `amount` | string | Yes | Amount in the token's **smallest unit** (decimal amount x `10^decimals`). Mint the base token: USDC and EURC have 6 decimals, so 250 USDC = `"250000000"` |

Response: `{ "ok": "Hell yeah!" }`. On a registered smart wallet USDC arrives 1:1 as WUSD and EURC as WEUR; the balance can take more than a minute to appear.

### Wallet Helpers

Helpers for creating sandbox wallets and moving test tokens. Transfer helpers take the owner's private key in the request body -- use them only with keys generated for the sandbox.

| Endpoint | Description |
|----------|-------------|
| `GET /account/generate?chainId=84532` | Returns a fresh key pair: `{ "address", "privateKey" }`. Nothing is deployed |
| `POST /account/retail` | Deploys a smart wallet for a fresh owner key and registers it under your company. Body: `{ "chainId": "84532", "companyId": "0x…" }`. Returns `wallet` (owner EOA), `privateKey` and `account` (smart wallet) |
| `GET /account/retail/balance?chainId=84532&account={address}&token={token}&decimals={decimals}` | Reads a token balance. Send the token's own `decimals` -- the default is `18` on EVM and Tron, `7` on Stellar |
| `POST /account/retail/transfer/request` | Requests a token transfer from a smart wallet. Body: `chainId`, `account`, `privateKey`, `token`, `to`, `amount` (smallest unit). Returns `{ "hash", "call" }` |
| `POST /account/retail/transfer/execute` | Executes the requested transfer. Body: `chainId`, `account`, `privateKey` and the `call` from the request |
| `POST /account/retail/unwrap/transfer/request` | As `transfer/request`, but debits the synthetic token (`unwrapToken`, `unwrapAmount`) and sends the base token (`token`, `amount`). Execute with `transfer/execute` |

Mint to and transfer from `account`, the smart wallet. Register the user with the owner (`wallet`) as described in [Onboarding](https://docs.wirexapp.com/docs/retail-onboarding).

---

## SEPA Simulation

| Action | Endpoint | Method |
|--------|----------|--------|
| Deposit | `/bank/sepa/deposit` | POST |
| Get pending | `/bank/sepa/transfers/pending?region={r}&email={e}` | GET |
| Complete | `/bank/sepa/transfer/complete` | POST |
| Cancel | `/bank/sepa/transfer/cancel` | POST |
| Revert | `/bank/sepa/transfer/revert` | POST |

- Deposit takes `email` (required), `amount` (EUR, required) and `region` (optional, `GB` or `EEA`; docs say "always use `GB` for now").
- Get pending takes `email` (required) and optional `region`. Pass the `id` value of an entry (not its own `transactionId` field) as `transactionId` to complete/cancel/revert. A payout is listed only once the user's SEPA account has received at least one deposit.
- Complete/cancel/revert take `email`, `transactionId` and optional `region`. Cancel ends the payout `Failed` and refunds the debit.
- **Sandbox behavior:** all outbound SEPA transfers remain in pending state indefinitely. Use `complete` or `revert` to simulate the external banking system processing the transfer.
- **Revert constraint:** can only be called after a transfer has been completed; it creates an inbound reversal transaction that credits the funds back.
- **Triggers:** `/v2/webhooks/activities` with `type=Sepa` (deposit: `Inbound`; complete: `status=Completed`; revert: `Sepa` `Inbound` reversal credit)

---

## ACH Simulation

| Action | Endpoint | Method |
|--------|----------|--------|
| Activate customer | `/bank/ach/customer/activate` | POST |
| Deposit | `/bank/ach/deposit` | POST |
| Complete transfer | `/bank/ach/transfer/complete` | POST |
| Revert transfer | `/bank/ach/transfer/revert` | POST |

- Activate requires `email`. Must be called before ACH deposits.
- **ACH account behavior:** ACH accounts remain in pending state indefinitely after creation. Call activate to simulate the external ACH provider activating the account.
- Deposit requires `email` and `amount` (USD).
- **ACH transfer behavior:** `ach` corridor payouts end `Failed` by themselves within minutes and the debit is refunded; they never reach the bank simulator, so `complete` and `revert` answer `No transfer found`.
- Complete/revert require `externalId` (activity ID from the Wirex BaaS transfer response). Revert can only be called after the transfer has been completed and creates an inbound reversal that credits the funds back.
- **Triggers:** deposit -> `/v2/webhooks/activities` with `type=AchPush`, `direction=Inbound`

---

## Card Transaction Simulation

Each endpoint runs a complete ISO-8583 message flow (authorization, clearing, reversal, refund, ...) against a card and triggers `/v2/webhooks/activities` with `type=CardTransaction`.

Common request: `cardId` (UUID), `amount`, `currency` (ISO 4217), `settlementAmount`, `settlementCurrency` (all required); optional `merchantCountry` (ISO 3166 alpha-3, e.g. `GBR`) and `paymentProvider` (`Visa`, `MasterCard`, `VisaEFunds`). For a same-currency purchase use equal amount/settlement values; use different values to simulate FX.

| Purpose | Endpoint |
|---------|----------|
| In-store purchase (auth + clearing) | `POST /card/auth-and-clearing` |
| E-commerce / card-not-present purchase | `POST /card/epos-auth-and-clearing` |
| ATM cash withdrawal | `POST /card/atm-auth-and-clearing` |
| Standalone refund | `POST /card/standalone-refund` |
| Push funds to card (Original Credit) | `POST /card/original-credit` |
| Balance inquiry | `POST /card/balance-inquiry` |

Single-message simulators: `POST /card/transaction/pos`, `/epos`, `/atm` and `/credit` (Original Credit) take only `{ "cardId", "amount" }`, with the amount in **GBP**. The response carries `success` and the ISO 8583 `responseCode`; a decline is still `200` (an amount the wallet cannot cover answers `"success": false`, `"responseCode": "51"`).

Reversals, multi-auth/multi-clearing, refunds with representment, chargeback and adjustment flows (25 endpoints in total) are listed in the [reference](references/REFERENCE.md#all-flow-endpoints). `POST /card/auth-and-multi-clearing` also requires `clearingAmounts` (array of numbers summing to the auth amount). Other flows that need an extra amount (`reversalAmount`, `refundAmount`, `clearingAmount`, `secondAuthAmount`, `adjustmentAmount`) answer `400 {"error": "<field> is required"}` without it. Every flow answers `200`; the decision is in the body, and a declined authorization carries `auth.response.responseCode: "51"` and the flow stops.

---

## 3DS Challenge Simulation

Card transaction simulations **never** raise a 3DS challenge. Raise one explicitly, then decide it through the Wirex BaaS API as in production:

1. `POST /card/3ds/initiate` (Helper API) with `cardId` (UUID from card issuance) and optional `transactionCurrency` (ISO 4217 alphabetic, default `USD`). Returns `{ "bin", "transactionId", "currency" }` with the alphabetic code (`"USD"`); the amount and merchant are generated by the simulator and are not in this response.
2. `GET /api/v1/cards/3ds/requests` (BaaS, user token): the challenge appears within seconds with `transaction_id` = `transactionId`, plus `merchant_name`, `amount` (string) and `card_last_4` -- read amount and merchant here, match by ID.
3. `POST /api/v1/cards/3ds/requests/{transactionId}/approve` or `/decline` (empty body) -> `200 {}`; a second decision -> `400 ErrorNotFound`. An undecided challenge expires after 5 minutes.

Errors: `400 {"error": "cardId is required"}`; `500 {"error": "3DS initiation failed: ..."}` when the ID is not a Wirex BaaS sandbox card. See [reference](references/REFERENCE.md#3ds-challenge-simulation).

---

## Webhook Trigger Summary

| Simulation | Webhooks Triggered |
|------------|-------------------|
| SEPA deposit | `/v2/webhooks/activities` (Sepa, Inbound) |
| SEPA complete | `/v2/webhooks/activities` (Completed) |
| SEPA revert | `/v2/webhooks/activities` (Sepa, Inbound reversal) |
| ACH deposit | `/v2/webhooks/activities` (AchPush, Inbound) |
| Card flows | `/v2/webhooks/activities` (CardTransaction) |
| 3DS initiate | The docs do not state whether `/v2/webhooks/3ds` fires; poll `GET /api/v1/cards/3ds/requests` |

The docs do not list webhooks for token minting or ACH complete/revert.

---

## Quick Start: Testing Workflow

1. **Obtain S2S token** from the main BaaS API using sandbox credentials (`POST /api/v1/token`).
2. **Register a user** via `POST /api/v2/user` on the main BaaS API.
3. **Mint tokens** via the Helper API to fund the user's wallet.
4. **Simulate deposits** (SEPA or ACH) to test bank transfer flows.
5. **Issue a card** via the main BaaS API (e.g. `POST /api/v2/cards/virtual`).
6. **Simulate card transactions** via the Helper API; raise a 3DS challenge with `POST /card/3ds/initiate` if you test approve/decline.
7. **Monitor webhooks** on your registered endpoints.
8. **Query activity history** via `GET /api/v2/activity/feed` to verify.

---

## References

- [Sandbox Helper API Reference](references/REFERENCE.md) -- Endpoint specifications with request/response fields, the full list of card flow endpoints, 3DS challenge simulation, error codes, and JavaScript examples

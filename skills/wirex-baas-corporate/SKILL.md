---
name: wirex-baas-corporate
description: "Wirex BaaS Corporate API (business accounts with employees, roles and KYB). Covers the corporate model vs retail, sandbox and production hosts, partner and corporation tokens, on-chain corporation registration, KYB onboarding, employees and role permissions, wallets, cards (issuance, limits, details, 3DS), bank, bulk, corridor and push-to-card transfers, recipients, FX, webhooks, activity feed, statements, error format, validation rules. Use when integrating or debugging api-business.wirexapp endpoints."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Corporate API

The Corporate API serves **businesses**: one corporation owns wallets, cards and bank accounts, and many employees act on it with role-based permissions. It is a separate API from the retail (consumer) BaaS API. Docs: [Corporate guides](https://docs.wirexapp.com/docs/corporate-getting-started). Authentication fundamentals shared with retail are in the wirex-baas-auth skill; this skill covers only what differs for corporations.

## Reference Files

| File | Content |
|---|---|
| [ENDPOINTS.md](references/ENDPOINTS.md) | Every endpoint: method, path, auth, permission, key fields |
| [ONBOARDING.md](references/ONBOARDING.md) | On-chain wallet deployment, register, login, KYB, capabilities, wallets |
| [TEAM-AND-PERMISSIONS.md](references/TEAM-AND-PERMISSIONS.md) | Employees, default and custom roles, permission codes |
| [CARDS.md](references/CARDS.md) | Card issuance, fees, management, limits, details, 3DS |
| [TRANSFERS.md](references/TRANSFERS.md) | Bank accounts, v1/v2 bank, v3 corridors, bulk, push-to-card, FX |
| [RECIPIENTS.md](references/RECIPIENTS.md) | Recipient model, per-rail fields and regexes |
| [WEBHOOKS-AND-ACTIVITY.md](references/WEBHOOKS-AND-ACTIVITY.md) | Webhooks, activity feed, statements, errors, validation rules, parity |

## Corporate vs Retail

| Aspect | Retail | Corporate |
|---|---|---|
| Entity | User | Corporation with employees |
| Token identity | User | Corporation + employee + permissions |
| Access control | None | Role-based, checked per endpoint |
| Verification | KYC | KYB (business verification) |
| Smart contract | `Accounts` | `CorporateAccounts` |
| Hosts | `api-baas.wirexapp.*` | `api-business.wirexapp.*` |

- The two APIs do not share credentials: a corporate `client_id` is rejected by retail and vice versa. Retail hosts do not route corporate endpoints.
- Terminology mapping: the retail S2S token is the corporate **partner token**; the retail user token is the corporate **corporation token**.
- Routes are served under `/api/v1`, `/api/v2` and `/api/v3`. A v2 or v3 route does not deprecate its v1 sibling; use the version shown in the flow.

## Environments

| | Sandbox | Production |
|---|---|---|
| Base URL | `https://api-business.wirexapp.tech` | `https://api-business.wirexapp.com` |
| Default chain | Base Sepolia, id `84532` | Base, id `8453` |
| Stellar chain id | `9223372036854775806` | `9223372036854775806` |
| PCI card manager (push-to-card) | `https://wx-acquiring-card-manager-uat.wirexapp.com` | `https://wx-acquiring-card-manager.wirexapp.com` |

- `GET /api/v1/config` (anonymous) returns live chain config: RPC, bundler, paymaster, ContractRegistry, and the Rhino.fi key at `auth.rhinoApiKey`. Read it at startup instead of hard-coding.
- `GET /api/v1/config/tokens` (partner or corporation token) returns the token catalogue for your company.
- Anonymous endpoints: `GET /api/v1/config`, `GET /api/v1/global/capabilities`, `GET /api/v1/validation/rules`.

## Authentication

Three token levels. Full flows: [ONBOARDING.md](references/ONBOARDING.md).

| Token | Obtained by | Lifetime | Used for |
|---|---|---|---|
| Partner token | `POST /api/v1/token` | 48 h (172800 s) | Register, login, list the employee's corporations, config tokens |
| Corporation token | `POST /api/v1/corporations/login` | See `exp` claim | Everything else |
| Action token | `POST /api/v1/confirmation/signature/verify` | 5 min | Card details, CVV, PIN, 3DS-challenge actions |

### Partner token

```http
POST /api/v1/token
Content-Type: application/json

{
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "grant_type": "client_credentials"
}
```

Response: `access_token`, `token_type`, `expires_at`. HS256, scope `partner:full`; optional `audience` in the body. Cache for 48 h.

The partner token reaches **only four endpoints**; any other returns `401 ErrorNotSupported`:

1. `GET /api/v1/config/tokens`
2. `GET /api/v1/employees/corporations`
3. `POST /api/v1/corporations/register`
4. `POST /api/v1/corporations/login`

### Identity headers

| Header | Meaning |
|---|---|
| `X-User-Wallet` | Employee wallet address |
| `X-User-Email` | Employee email |
| `X-User-Id` | Employee identity id |
| `X-Chain-Id` | Chain for the corporation token (omitted = environment default) |

- `register` and `login` need **both** `X-User-Wallet` and `X-User-Email`; otherwise `500` with `Failed to get user from context`.
- The chain is fixed into the corporation token at login from `X-Chain-Id`. Sending `X-Chain-Id` on later requests has no effect. To switch chains, log in again. Stellar uses its own chain id (above).
- Permissions are frozen into the token at login. A role change takes effect only after the employee logs in again.

### Corporation token

`POST /api/v1/corporations/login` with partner token, `X-User-Wallet`, `X-User-Email`, `X-Chain-Id` headers and body `{"corporation_address": "0x..."}` (use a real address). The response holds only `access_token`; read `exp` from the JWT. A token missing a wallet claim yields `401 ErrorMissingField` (`Employee address claim is missing`): log in with `X-User-Wallet`.

### Action token

For sensitive card actions the employee signs a message with their wallet:

1. Pick `action_type`: `GetCardDetails` or `3dsChallenge`, and a fresh `nonce` (valid 120 s).
2. Sign `By signing this I confirm that I am executing action {action_type} at {nonce}`.
3. `POST /api/v1/confirmation/signature/verify` with the corporation token and body `action_type`, `message_signature`, `nonce`. Requires `CardSu` or `CardViewDetails`.
4. Send the returned token as `action_token` in the card-details body. It lives 5 minutes.

`POST /api/v1/confirmation/signature` is the obsolete form of the same call. Read PAN, CVV and PIN (also during a 3DS challenge) with a `GetCardDetails` token: a `3dsChallenge` token is refused by every card-data endpoint with `invalid_purpose`. Details: [CARDS.md](references/CARDS.md).

## Registration and Onboarding (KYB)

A corporation exists on-chain first, then in Wirex. Detail and contract addresses: [ONBOARDING.md](references/ONBOARDING.md), [guide](https://docs.wirexapp.com/docs/corporate-onboarding).

1. **Deploy the corporate wallet on-chain.** Install `CorporateValidator` with `ExecutionDelayCorporatePolicy` and `FundsManagement` on the wallet, then any address calls `createCorporationForCorporateWallet` on `CorporateAccounts` (permissionless; the owner is the `creator` recorded in the `CorporateValidator` install data, not `msg.sender`). The older `createCorporation` is obsolete. The code is TypeScript/ABI work done by the partner, described in ONBOARDING.md.
2. `GET /api/v1/config` for the ContractRegistry, then `POST /api/v1/token` for the partner token.
3. `POST /api/v1/corporations/register` (partner token; `X-User-Wallet` and `X-User-Email` both required) links the on-chain corporation to Wirex.
4. `POST /api/v1/corporations/login` returns the corporation token.
5. `GET /api/v1/corporations` returns status, `verification_status`, capabilities, allowed actions.
6. `POST /api/v1/corporations/level-token` (`Su` only; body `verification_level`) returns an SDK token to launch the KYB verification widget; `POST /api/v1/corporations/verification-token` is the shorthand for level `SDD`.
7. Wait for `verification_status` to become `Approved`: webhook `/v2/webhooks/corporations` or poll `GET /api/v1/corporations`.
8. Read `capabilities[]`; each capability has a status and, when not active, reasons. Activate bank details where needed (see Transfers).

Corporation `status`: `Pending`, `Active`, `Blocked`, `Deleted`. KYB `verification_status`: `Pending`, `Applied`, `InReview`, `Approved`, `Rejected`, `Canceled`. `PUT /api/v1/corporations/freshdesk-id` stores a support identifier (body `freshdesk_id`).

Levels: `SDD`, `EDD`, `XDDBridgeBase`, `XDDOpenPaydBase`. An unrecognised level silently yields an `SDD` token, so validate it yourself. `XDDBridgeBase` is required, after `SDD`, for ACH and Fedwire. Requesting its token puts the whole corporation back into review: `verification_status` reads `Applied`, `verification_levels` is emptied and every capability gated on `SDD` (card issuance included) reads `NotFulfilled` until the level is approved.

### Wallets and balances

- `GET /api/v1/wallets` (no permission): `data[]` with `wallet_address`, `wallet_status` and balances per token, with a USD reference currency. `balance` is rounded to 2 decimal places: compute and check funds with `balance_precise` (scaled by `decimals`). Note: docs differ: the schema says the reference currency follows the corporation country; the endpoint always returns USD.
- `POST /api/v1/wallets/global` (`AccountSu`, `AccountCreate`, `AccountManage` or `Su`; owner-only before October 2026) registers an extra address to receive cross-chain deposits (global deposit addresses via Rhino.fi, same as retail).

## Employees, Roles and Permissions

Detail: [TEAM-AND-PERMISSIONS.md](references/TEAM-AND-PERMISSIONS.md), [guide](https://docs.wirexapp.com/docs/corporate-employees).

Employee lifecycle: invite creates an `Invited` employee; when the invitee logs in with the invited wallet and email, they become active.

1. `GET /api/v1/roles` lists default roles and custom roles (needs `EmployeeSu`, `EmployeeManage` or `EmployeeView`).
2. `POST /api/v1/employees/invite` (`EmployeeSu` or `EmployeeManage`) with `first_name`, `last_name`, `email`, `role_id` required; `phone`, `department`, `job_title`, `manager_address`, `residence_address` optional.
3. `PUT /api/v1/employees/{employeeId}/role` changes the role (effective at next login).
4. `PUT /api/v1/employees/{employeeId}` updates personal data (email ignored).
5. `DELETE /api/v1/employees/{employeeId}` is refused for the Owner, for self, and in other protected cases.

| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/employees` | List |
| GET | `/api/v1/employees/search` | `term` (2+ chars) and/or `manager_address` |
| GET | `/api/v1/employees/{employeeId}` | Own record always; others need an employee permission |
| GET | `/api/v1/roles/{roleId}` | One role |
| POST | `/api/v1/roles` | `EmployeeSu`; `name` max 64 bytes, `permissions[]` (no `Su`) |
| PUT | `/api/v1/roles/{roleId}` | Replaces name and the full permission set |
| DELETE | `/api/v1/roles/{roleId}` | Custom roles only |

Permission code families (numeric codes 101-118 and the default role table are in TEAM-AND-PERMISSIONS.md): `Su` (owner-level, only the owner), `EmployeeSu/Manage/View`, `CardSu/Create/Manage/View/ViewDetails/LimitManage`, `TransactionSu/Create/Manage`, `AccountSu/Create/Manage/View`. Missing permission returns `403 ErrorPermissionDenied`. Custom roles cannot include `Su`.

Note: docs differ. The Employees reference lists `phone` as optional on invite; the Employees guide says it is required, and card embossing depends on it. Send it (format `+` followed by 1-15 digits).

## Cards

Detail: [CARDS.md](references/CARDS.md), [guide](https://docs.wirexapp.com/docs/corporate-cards).

Cards are **virtual** or **plastic**; ceilings 30 virtual and 15 plastic cards per corporation (a closed card frees a slot). Issuance may carry an order fee, only when fees are enforced for your company; otherwise `GET /api/v1/cards/{type}/fees/{country}` returns `400 You have no card order/delivery fees to pay` and the card is issued directly. There is no `GET /api/v1/cards/{cardId}`: use `GET /api/v3/cards/{cardId}` (`CardSu` or `CardView`; `GET /api/v3/cards` lists across every chain) or list and filter.

### Issue a card (v2 fee flow, when fees are enforced)

1. `GET /api/v1/cards/{type}/fees/{country}` (`type` = `Plastic` or `Virtual`) returns the fee. For plastic: `GET /api/v1/cards/delivery/countries` and `GET /api/v1/cards/delivery/methods/{country}`.
2. `POST /api/v2/cards/{type}/fees/{country}/payment` (body `token_address`, plus `delivery_provider` for non-Virtual) returns a fee invoice with `delivery_id`. Wirex debits the fee at issuance; no on-chain payment.
3. `POST /api/v2/cards/virtual` or `POST /api/v2/cards/plastic` with `card_name`, `name_on_card`, employee link and `delivery_id`; plastic also `delivery_provider`, `delivery_address`.
   v3 (`POST /api/v3/cards/virtual`, `/plastic`) uses the same v2 fee invoice and `delivery_id`, takes optional `design`, `card_program`, `payment_system` read from `GET /api/v3/cards/config` (`CardSu`, `CardCreate` or `CardView`), and requires a fee only when the order is priced above zero. No version issues metal cards.
4. v1 alternative (you pay the fee on-chain yourself): `/api/v1/cards/{type}/fees/{country}/payment` returns `recipient_address`; transfer the fee, then `/api/v1/cards/virtual` or `/api/v1/cards/plastic` take `payment_transaction_hash` instead of `delivery_id`. Do not mix v1 and v2 calls.
5. Observe `/v2/webhooks/cards` or poll `GET /api/v1/cards` (`CardSu` or `CardView`; admins may pass `employee_id`).

Plastic cards start `NotActivated`: `PUT /api/v1/cards/{cardId}/activate` with `card_number_last4` and `expiry_date` (`MM/YYYY`).

### Manage

| Method | Path | Permission |
|---|---|---|
| PUT | `/api/v1/cards/{cardId}/activate` | `CardSu`, `CardManage` |
| PUT | `/api/v1/cards/{cardId}/block` | same; card must be `Active` |
| PUT | `/api/v1/cards/{cardId}/unblock` | same; card must be `Blocked` |
| PUT | `/api/v1/cards/{cardId}/close` | same; permanent |
| PUT | `/api/v1/cards/{cardId}/name` | same; body `name` |
| PUT | `/api/v1/cards/{cardId}/limit` | `CardSu`, `CardLimitManage` |

Limits: body `daily_limit`, `limit`, `monthly_limit`, `transaction_limit`. The call **replaces the whole set**; an omitted field becomes `-1` (disabled). Note: docs differ: the reference schema marks all four required.

### Details and 3DS

- `POST /api/v1/cards/{cardId}/details` (PAN, expiry), `/cvv`, `/pin`: body `action_token` (from the signature flow above); permission `CardSu` or `CardViewDetails`.
- `GET /api/v1/cards/3ds/requests` returns a bare array of pending challenges (`CardSu` or `CardViewDetails`).
- `POST /api/v1/cards/3ds/requests/{transactionId}/approve` and `/decline`: corporation token, no body, permission `CardSu` or `CardManage`.
- Webhook: `/v2/webhooks/3ds`.

Approve/decline take the corporation token only (the Auth Tokens guide no longer lists them as needing a `3dsChallenge` action token). The earlier fallback to an action token is unverified. The `3dsChallenge` token scope is no longer disputed: every card-data endpoint refuses it.

## Transfers

Detail: [TRANSFERS.md](references/TRANSFERS.md), [guide](https://docs.wirexapp.com/docs/corporate-bank-transfers). Money-moving calls follow **estimate, then execute with the `estimation_id`**. The returned `id` equals the activity feed id; status is read from `GET /api/v1/activity/feed`.

| Goal | Path |
|---|---|
| Crypto batch to many wallets | `POST /api/v1/bulk/transfer` |
| SEPA / ACH / Faster Payments (v1/v2) | `POST /api/v1/bank/transfer/estimate` or `/api/v2/...`, then `POST /api/v1/bank/transfer` with the `estimation_id` (an `amount`-only execute is refused) |
| Local corridor (PIX, FPS HK, IMPS, InstaPay, BI-FAST, NIP, IPP, PSE and more) | `POST /api/v3/bank/estimate/{corridor}`, `POST /api/v3/bank/initiate/{corridor}`, `POST /api/v3/bank/confirm/{corridor}` |
| Push to external card | `POST /api/v1/cards/transfer/estimate`, `POST /api/v1/cards/transfer` |
| Token swap | `POST /api/v1/fx/estimate`, `POST /api/v1/fx` |

Permissions: bank, corridor and bulk need `TransactionSu` or `TransactionCreate`; push-to-card needs `CardSu`; FX needs `TransactionSu` (and the capability `Active`: `CardTransfer`, `StableExchange`).

### Bank accounts

1. `GET /api/v1/bank/accounts` (`TransactionSu`, `TransactionCreate` or `AccountView`) lists accounts and details; each entry has an `id` and, when `Active`, bank details. Activating `Ach` also adds `Fedwire` and `FedNow` entries to the same USD account (same routing and account numbers); `FedNow` is deposits only and is not accepted as `account_type`. ACH needs `XDDBridgeBase` on top of `SDD` (see Onboarding).
2. `POST /api/v1/bank/accounts` (`TransactionSu`, `AccountSu`, `AccountCreate`) with `account_type` activates details. Poll the list: no webhook.

Note: docs differ. The reference accepts `Sepa` as `account_type`; the Account Activation guide says SEPA is auto-provisioned on verification and rejects `Sepa`, and refuses `Swift`. Follow the capability status (`SepaAccount`): the Account Activation guide now says to read the capability, not `actions[]` (no action exists for Faster Payments, yet its activation is accepted at `ActivationNotStarted`).

### Bank transfer (v1/v2)

1. Estimate: v1 `POST /api/v1/bank/transfer/estimate` (account, amount, no beneficiary) or v2 `POST /api/v2/bank/transfer/estimate` (`recipient` and `recipient_account` required on every rail); both return the same quote.
2. Execute: `POST /api/v1/bank/transfer` with `account_id`, `token_address`, recipient data and the estimate.
3. Follow the activity feed (types `Sepa`, `FasterPayment`, `AchPush`, `AchPull`).

### Corridors (v3)

1. Create or pick a recipient with matching payment details ([RECIPIENTS.md](references/RECIPIENTS.md)).
2. `POST /api/v3/bank/estimate/{corridor}` with `recipient_id`, `recipient_payment_details_id`, amounts.
3. `POST /api/v3/bank/initiate/{corridor}` with `estimation_id`, `source_token_address`, `reference`.
4. For CPN corridors the response contains a `FundTransfer` to confirm: `POST /api/v3/bank/confirm/{corridor}` with `transfer_id` and `actions[]`.

The 16-row corridor table (currencies, rails, capabilities, providers) is in TRANSFERS.md. `fedwire` is a bank corridor (`account_id` required, no confirm step) paying from the same USD account as `ach`; only `pix`, `spei`, `swift`, `cips`, `chats` and `fps_hk` are CPN. In `Signature` mode bank transfer, corridor `initiate` and card transfer carry `transaction_authorization` (see TRANSFERS.md).

### Bulk transfer

`POST /api/v1/bulk/transfer` with `recipients[]` (1 to 50, `currency` `WUSD` or `WEUR`). It approves a crypto batch and **reserves** the balance for 24 hours; amounts are truncated to 2 decimals. The batch is then executed on-chain by the partner (TypeScript/ABI details in TRANSFERS.md). No webhook for approval; read the feed.

### Push to card

1. `POST /api/v1/cards/transfer/estimate` with the external-card reference and amount.
2. Card data is tokenized at the PCI host (table above), never sent to the corporate host.
3. `POST /api/v1/cards/transfer` with `estimation_id`, `token_address`; response `id` is the activity feed id.

### FX

1. `POST /api/v1/fx/estimate` returns a quote and a deposit address.
2. Pay the deposit address on-chain.
3. `POST /api/v1/fx` with `estimation_id` and `payment_transaction_hash`; response `trade_id`. No webhook; poll the feed.

### Recipients

Recipient = identity plus one or more payment details (rails). Use v2 to create both at once.

| Method | Path | Permission |
|---|---|---|
| GET | `/api/v1/recipients`, `/api/v1/recipients/{recipientId}` | none |
| GET | `/api/v1/recipients/filter/{name,catalog,currency,type}` | none |
| POST / PUT | `/api/v2/recipients`, `/api/v2/recipients/{recipientId}` | `TransactionSu`, `TransactionManage` |
| POST / PUT | `/api/v1/recipients`, `/api/v1/recipients/{recipientId}` | same; identity only |
| DELETE | `/api/v1/recipients/{recipientId}` | same |
| POST / PUT / DELETE | `/api/v1/recipients/{recipientId}/payment_details[/{paymentDetailsId}]` | same |
| POST | `/api/v1/recipients/{recipientId}/usage` | Transaction* |

Webhook: `/v2/webhooks/recipients`. IBAN and card checksums are not validated by the API.

## Webhooks and Activity

Detail: [WEBHOOKS-AND-ACTIVITY.md](references/WEBHOOKS-AND-ACTIVITY.md), [guide](https://docs.wirexapp.com/docs/corporate-webhooks).

- One webhook base URL per partner; route by `corporation_address`. HTTP POST JSON, 10 s timeout, **no retries**, no auth headers (allowlist IPs, make handlers idempotent).
- Paths: `/v2/webhooks/corporations`, `/wallets`, `/balances`, `/cards`, `/card-limits`, `/3ds`, `/activities`, `/recipients`, `/erc-withdrawals`. `/v2/webhooks/user` and `/debt-cases` are retail only.
- Not delivered (poll): employees, roles, bank account activation, FX swaps, bulk approval, capability changes.
- `GET /api/v1/activity/feed`: `page_number` starts at `0`, `page_size` default 25, max 50; `types` and `subject` are mutually exclusive. Status `Pending`/`Completed`/`Failed`, direction `Inbound`/`Outbound`/`Internal`. No single-item read, no date filter.
- `GET /api/v1/withdrawal/requests` lists ERC-20 withdrawals awaiting on-chain execution (time-locked by `ExecutionDelayCorporatePolicy`).

## Statements

`POST /api/v1/activity/statement/full` with body `start` and `end` (Unix seconds, rounded to day boundaries, `start` before `end`, at most 6 months, else `End time must be within 6 months from start time`). Returns `balances[]` and `transactions[]` as JSON for the one chain in the token; not paginated. Timestamps are Unix seconds (the feed uses ISO 8601).

## Error Format

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Human-readable message",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "field", "details": "email" }
  ]
}
```

- Branch on `error_reason`; never parse `error_description`.
- Categories: `CategoryValidationFailure` 400, `CategoryUnauthorized` 401, `CategoryForbidden` 403, `CategoryTransientFailure` 429, `CategoryInternalFailure` 500, `CategoryTransportFailure` 503.
- The token endpoint rate limit (repeated failed attempts; successful exchanges are not counted) returns `ErrorTooManyRequests` with **HTTP 500**, not 429.
- Validation errors have two shapes (structured `key: field` with `issue` and `pattern`, or keyed where the field is the key); handle both.
- Note: docs differ. The reference types `error_reason` as an object; guides show a string. Read defensively.

Full reason list: [WEBHOOKS-AND-ACTIVITY.md](references/WEBHOOKS-AND-ACTIVITY.md).

## Validation Rules

`GET /api/v1/validation/rules` (anonymous) publishes patterns, but four differ from what is enforced: `firstName` / `lastName` (enforced `^[a-zA-Z][a-zA-Z\-' ]{0,49}$`), `state` (enforced `^[A-Za-z][A-Za-z\s\-']{1,99}$`), `department` / `job` (published, not enforced), `cardNumber` (published, never used). Enforced examples: registration number `^[A-Z0-9\-]{6,15}$`, country `^[A-Z]{2}$`, currency `^[A-Za-z0-9]{3,10}$`. Pagination `page_size` maximum is 50 (employee search 100): `page size exceeds maximum allowed`. Amount fields: `amount` is a decimal, `precise_amount` is a string in smallest units. All patterns: WEBHOOKS-AND-ACTIVITY.md and RECIPIENTS.md.

## Retail vs Corporate Feature Parity

Not implemented for corporations: card top-up; XRPL accounts and withdrawals; metal cards; `GET /api/v1/cards/{cardId}` (use `GET /api/v3/cards/{cardId}`); activity v2 feed, search and single-item read (only `GET /api/v1/activity/feed`). Global deposit addresses behave as on retail.

## Common Pitfalls

1. Using a retail `client_id` or host: both are rejected.
2. Calling anything except the four partner endpoints with the partner token (`401 ErrorNotSupported`).
3. Sending only one of `X-User-Wallet` / `X-User-Email` on register or login (`500 Failed to get user from context`).
4. Changing a role and expecting immediate effect: re-login.
5. Expecting `X-Chain-Id` to switch chains on a corporation token: it is fixed at login.
6. Expecting retries on webhooks: none; poll the feed.
7. Reusing nonces or old action tokens: nonce 120 s, action token 5 min.
8. Not checking the capability status before estimates; inactive capabilities fail with a reason.

## Links

- [Corporate overview](https://docs.wirexapp.com/docs/corporate-getting-started)
- [Authentication](https://docs.wirexapp.com/docs/corporate-authentication)
- [Onboarding](https://docs.wirexapp.com/docs/corporate-onboarding)
- [Employees](https://docs.wirexapp.com/docs/corporate-employees)
- [Cards](https://docs.wirexapp.com/docs/corporate-cards)
- [Transfers](https://docs.wirexapp.com/docs/corporate-bank-transfers)
- [Webhooks](https://docs.wirexapp.com/docs/corporate-webhooks)
- [Statements](https://docs.wirexapp.com/docs/corporate-statements)
- [Error Reference](https://docs.wirexapp.com/docs/corporate-error-reference)

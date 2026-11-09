# Wirex BaaS Corporate API — Endpoint Reference

Every Corporate API endpoint with method, path, purpose, required permission and key fields. Source: the Corporate API reference and the [Endpoint Surface](https://docs.wirexapp.com/docs/corporate-endpoint-surface) and [Permissions](https://docs.wirexapp.com/docs/corporate-permissions) guides.

## Table of Contents

- [Conventions](#conventions)
- [Authorization and Configuration](#authorization-and-configuration)
- [Corporations and KYB](#corporations-and-kyb)
- [Employees and Roles](#employees-and-roles)
- [Wallets and FX](#wallets-and-fx)
- [Cards](#cards)
- [Confirmation and 3DS](#confirmation-and-3ds)
- [Push-to-Card](#push-to-card)
- [Bank Accounts and Transfers](#bank-accounts-and-transfers)
- [Recipients](#recipients)
- [Activity](#activity)

---

## Conventions

- Base URL: `https://api-business.wirexapp.tech` (sandbox) or `https://api-business.wirexapp.com` (production). The retail hosts `api-baas.wirexapp.*` do not route corporate endpoints.
- Auth column: **anon** = no `Authorization` header; **partner** = partner token + identity headers; **corp** = corporation token (`Authorization: Bearer <corporation_token>`).
- Permission column: the endpoint admits a caller holding **any one** of the listed permissions. `Su` always passes. `none` = any valid corporation token.
- List endpoints take `page_number` (starts at `0`; `page_number=1` is the second page, so paging from `1` skips the first page; exception: `GET /api/v1/bank/accounts` pages from `1` and `0` also returns the first page), `page_size` (default 25, maximum 50) and `sort` (`name` default, or `usage`). `GET /api/v1/employees/search` allows `page_size` up to 100.
- `precise_amount` is a string with the integer amount in the token's smallest unit; `amount` is a decimal number. Other responses use a `_precise` suffix with a `decimals` field beside it (`amount_precise`, `balance_precise`, `order_fee_precise`, `source_asset_amount_precise`, `opening_precise`): the float is rounded for display, often to 2 decimals, so compute and reconcile on the `_precise` value and read its `decimals` every time (token amounts scale by the token's decimals, fiat amounts and every statement amount by `18`).
- Full permission names and codes: [TEAM-AND-PERMISSIONS.md](TEAM-AND-PERMISSIONS.md).

## Authorization and Configuration

| Method | Path | Auth | Purpose | Key fields |
|---|---|---|---|---|
| POST | `/api/v1/token` | anon | Exchange client credentials for a partner token (48h) | body `client_id`, `client_secret`, `grant_type` = `client_credentials`; response `access_token`, `token_type`, `expires_at` |
| GET | `/api/v1/config` | anon | Live chain and client config: RPC, bundler, paymaster, ContractRegistry, Rhino.fi key | `chains.<id>.contractRegistry`, `bundlerUrl`, `paymasterUrl`, `auth.rhinoApiKey`, `defaultChain` |
| GET | `/api/v1/config/tokens` | partner or corp | Token catalogue for your company | `address`, `base_token_address`, `symbol`, `decimals`, `token_type` (`Synthetic`/`Regular`), `is_active`, `supported_chain_ids` |
| GET | `/api/v1/validation/rules` | anon | Published validation regexes (differ from enforced — see WEBHOOKS-AND-ACTIVITY.md) | `rules` map |
| GET | `/api/v1/global/capabilities` | anon | Capability matrix per country (not corporation-specific) | `capabilities` map keyed by ISO country |

## Corporations and KYB

| Method | Path | Auth / permission | Purpose | Key fields |
|---|---|---|---|---|
| POST | `/api/v1/corporations/register` | partner (`X-User-Wallet` and `X-User-Email` both required) | Link the on-chain corporation to a Wirex record; owner only | body `corporation_address` (required), `corporation_name`, `corporation_registration_number`, `corporation_registration_country`; response `{}` |
| POST | `/api/v1/corporations/login` | partner (`X-User-Wallet`, `X-User-Email`, `X-Chain-Id`) | Get a corporation token; invited employee claims their record | body `corporation_address`; response `access_token` |
| GET | `/api/v1/employees/corporations` | partner (any one identity header) | Corporations the employee belongs to | `corporation_descriptors[].corporation_address`, `corporation_name` |
| GET | `/api/v1/corporations` | corp, none | Corporation record, statuses, capabilities, allowed actions | `status`, `verification_status`, `verification_levels[]`, `capabilities[]`, `actions[]`, `owner_address` |
| PUT | `/api/v1/corporations/freshdesk-id` | corp, none | Store support identifier | body `freshdesk_id` |
| POST | `/api/v1/corporations/level-token` | corp, `Su` only | SumSub SDK token for a KYB level | body `verification_level`: `SDD`, `EDD`, `XDDBridgeBase`, `XDDOpenPaydBase`; response `token` |
| POST | `/api/v1/corporations/verification-token` | corp, `Su` only | SDK token for `SDD` (shorthand) | empty body; response `token` |

## Employees and Roles

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| GET | `/api/v1/employees` | `EmployeeSu`, `EmployeeManage`, `EmployeeView` | List employees | response `employees[]`: `id`, `email`, `role_id`, `status`, `owner_address` |
| GET | `/api/v1/employees/search` | same | Search by `term` (2+ chars) and/or `manager_address` | query `term`, `manager_address`, `page_size` max 100 |
| POST | `/api/v1/employees/invite` | `EmployeeSu`, `EmployeeManage` | Create an `Invited` employee | `first_name`, `last_name`, `email`, `role_id` required; `phone`, `department`, `job_title`, `manager_address`, `residence_address` optional per reference |
| GET | `/api/v1/employees/{employeeId}` | none at route; handler: own record always, others need `Su`/`EmployeeSu`/`EmployeeManage`/`EmployeeView` | Read one employee | same shape as list item |
| PUT | `/api/v1/employees/{employeeId}` | `EmployeeSu`, `EmployeeManage` | Update personal data (email ignored) | `first_name`, `last_name`, `phone`, `department`, `job_title`, `manager_address`, `residence_address` |
| PUT | `/api/v1/employees/{employeeId}/role` | `EmployeeSu`, `EmployeeManage` | Change role (effective at next login) | body `role_id` |
| DELETE | `/api/v1/employees/{employeeId}` | `EmployeeSu`, `EmployeeManage` | Delete; refused for Owner, for self, for other corporations | — |
| GET | `/api/v1/roles` | `EmployeeSu`, `EmployeeManage`, `EmployeeView` | Default plus custom roles | `roles[]`: `id`, `name`, `permissions[]`, `is_global` |
| GET | `/api/v1/roles/{roleId}` | none | One role | — |
| POST | `/api/v1/roles` | `EmployeeSu` | Create custom role | `name` (max 64 bytes), `permissions[]` (no `Su`) |
| PUT | `/api/v1/roles/{roleId}` | `EmployeeSu` | Replace name and the full permission set | same body |
| DELETE | `/api/v1/roles/{roleId}` | `EmployeeSu` | Delete custom role (defaults refused) | — |

## Wallets and FX

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| GET | `/api/v1/wallets` | none | Wallets with balances | `data[]`: `wallet_address`, `wallet_status` (`Unknown`/`Confirmed`/`Rejected`), `wallet_type` (`Primary`/`Secondary`/`Global`), `balances[]` |
| POST | `/api/v1/wallets/global` | `AccountSu`, `AccountCreate`, `AccountManage` | Register an extra address to receive cross-chain deposits | `wallet_address`, `wallet_name` |
| POST | `/api/v1/fx/estimate` | `TransactionSu`; `StableExchange` capability `Active` | Quote a swap, get a deposit address | `source_asset_address`, `destination_asset_address`, exactly one of `source_asset_amount` / `destination_asset_amount` (decimal strings), optional `correlation_id`; response `estimation_id`, `deposit_address`, `trade_rate`, `expiration_time`, plus `source_asset_amount_precise` / `source_asset_decimals` (the exact amount to deposit) |
| POST | `/api/v1/fx` | same | Execute after paying the deposit address on-chain | `estimation_id`, `payment_transaction_hash`; response `trade_id` |

## Cards

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| GET | `/api/v1/cards` | `CardSu`, `CardView` | List cards (get by id: `GET /api/v3/cards/{cardId}`) | query `employee_id` (admins only), pagination; `data[]` with `status`, `card_data`, `limit`, `allowed_actions` |
| GET | `/api/v1/cards/{type}/fees/{country}` | `CardSu`, `CardCreate`, `CardView` | Order fee; `type` = `Plastic`, `Virtual`, `Metal` | `order_fee`, `estimated_payment_amounts[]` |
| GET | `/api/v1/cards/delivery/countries` | same | Plastic delivery countries | array of ISO codes |
| GET | `/api/v1/cards/delivery/methods/{country}` | same | Couriers and delivery fee | `provider`, `fee` |
| POST | `/api/v1/cards/{type}/fees/{country}/payment` | `CardSu`, `CardCreate` | v1 fee invoice | body `token_address`, `delivery_provider` (non-Virtual); response `recipient_address`, `payment_amount` |
| POST | `/api/v2/cards/{type}/fees/{country}/payment` | same | v2 fee invoice | adds `delivery_id` (integer, single-use) |
| GET | `/api/v3/cards`, `/api/v3/cards/{cardId}` | `CardSu`, `CardView` | List / read cards across every chain | same card objects as v1 |
| GET | `/api/v3/cards/config` | `CardSu`, `CardCreate`, `CardView` | Orderable formats, payment systems, designs, card programs, countries | `formats[].offerings[]` |
| POST | `/api/v3/cards/virtual`, `/api/v3/cards/plastic` | `CardSu`, `CardCreate` | Issue with optional `design`, `card_program`, `payment_system` (v2 fee invoice; `delivery_id` only when the order is priced above zero) | as v2 |
| POST | `/api/v1/cards/virtual` | `CardSu`, `CardCreate` | Issue virtual card (v1 fee flow) | `card_name`, `name_on_card`, `employee_id`, `payment_transaction_hash`; response `id` |
| POST | `/api/v1/cards/plastic` | same | Issue plastic card (v1) | adds `delivery_address` (required) and `delivery_provider` (required when fees are enforced) |
| POST | `/api/v2/cards/virtual` | same | Issue virtual card (v2 fee flow) | `delivery_id` instead of `payment_transaction_hash` |
| POST | `/api/v2/cards/plastic` | same | Issue plastic card (v2) | adds `delivery_address` (required) and `delivery_provider` (required when fees are enforced) |
| PUT | `/api/v1/cards/{cardId}/activate` | `CardSu`, `CardManage` | Activate a plastic card (`NotActivated`) | `card_number_last4`, `expiry_date` (`MM/YYYY`) |
| PUT | `/api/v1/cards/{cardId}/block` | `CardSu`, `CardManage` | Block an `Active` card | — |
| PUT | `/api/v1/cards/{cardId}/unblock` | `CardSu`, `CardManage` | Unblock a `Blocked` card | — |
| PUT | `/api/v1/cards/{cardId}/close` | `CardSu`, `CardManage` | Close permanently | — |
| PUT | `/api/v1/cards/{cardId}/name` | `CardSu`, `CardManage` | Rename display name | `name` |
| PUT | `/api/v1/cards/{cardId}/limit` | `CardSu`, `CardLimitManage` | Replace limits (omitted = `-1`) | `daily_limit`, `monthly_limit`, `transaction_limit`, obsolete `limit` |
| POST | `/api/v1/cards/{cardId}/details` | `CardSu`, `CardViewDetails` | PAN and expiry | body `action_token`; response `card_number`, `expiry_date` |
| POST | `/api/v1/cards/{cardId}/cvv` | same | CVV | response `cvv` |
| POST | `/api/v1/cards/{cardId}/pin` | same | PIN | response `pin` |

## Confirmation and 3DS

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| POST | `/api/v1/confirmation/signature/verify` | `CardSu`, `CardViewDetails` | Exchange a wallet signature for an action token | `action_type` (`GetCardDetails`, `3dsChallenge`), `message_signature`, `nonce`; response `token` |
| POST | `/api/v1/confirmation/signature` | same | Obsolete form of the above | same |
| GET | `/api/v1/cards/3ds/requests` | `CardSu`, `CardViewDetails` | Pending 3DS challenges (bare array) | `transaction_id`, `card_id`, `card_last_4`, `amount`, `currency`, `merchant_name` |
| POST | `/api/v1/cards/3ds/requests/{transactionId}/approve` | `CardSu`, `CardManage` | Approve; no body | — |
| POST | `/api/v1/cards/3ds/requests/{transactionId}/decline` | `CardSu`, `CardManage` | Decline; no body | — |

## Push-to-Card

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| POST | `/api/v1/cards/transfer/estimate` | `CardSu`; `CardTransfer` capability `Active` | Quote an OCT push | `external_card_id`, `amount` (> 0), `tokens[]`, optional `currency` (defaults `EUR`); response `estimation_id`, `expires_at`, `estimated_amounts[]` |
| POST | `/api/v1/cards/transfer` | same | Execute | `estimation_id`, `token_address`; response `id` (activity feed id) |

## Bank Accounts and Transfers

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| GET | `/api/v1/bank/accounts` | `TransactionSu`, `TransactionCreate`, `AccountView` | Bank accounts and details | `id` is composite `<accountId>:<detailsId>`; `details.iban`/`bic`/`account_number`/`sort_code`/`routing_number`/`clabe`/`mandatory_reference`; `account_type` includes `Fedwire`; v1 transfer takes the whole `id`, v3 takes only `<accountId>` |
| POST | `/api/v1/bank/accounts` | `TransactionSu`, `AccountSu`, `AccountCreate` | Activate account details | body `account_type`; response `details_id` |
| POST | `/api/v1/bank/transfer/estimate` | `TransactionSu`, `TransactionCreate` | v1 estimate (no beneficiary) | `account_id` (composite), `amount`, `tokens[]`; response `id`, `expires_at`, `estimated_amounts[]` |
| POST | `/api/v2/bank/transfer/estimate` | same | v2 estimate; `recipient` and `recipient_account` required on every rail | as v1 plus beneficiary (`reference` is ignored by the estimate) |
| POST | `/api/v1/bank/transfer` | same | Execute SEPA/ACH/Faster Payments transfer | `account_id`, `token_address`, `recipient`, `recipient_account`, `estimation_id` (an `amount`-only request is refused with `ErrorNotFound`), `reference`, `transaction_authorization` (`Signature` mode); response `id` |
| POST | `/api/v3/bank/estimate/{corridor}` | same | Corridor estimate | `recipient_id`, `recipient_payment_details_id`, `destination_amount`, `destination_currency`, `account_id` (plain UUID, bank corridors `sepa`, `ach`, `faster-payments`, `fedwire`), `source_tokens[]` |
| POST | `/api/v3/bank/initiate/{corridor}` | same | Corridor initiate | `estimation_id`, `source_token_address`, `reference`, `transaction_authorization` (`Signature` mode); response `transfer_id`, `status`, `required_actions[]` (omitted when none) |
| POST | `/api/v3/bank/confirm/{corridor}` | same | Confirm a `FundTransfer` (CPN corridors) | `transfer_id`, `actions[]` with `data.tx_hash`; response `status`, `tx_hash` |
| POST | `/api/v1/bulk/transfer` | same | Approve a crypto batch (1-50), reserves balance | `recipients[]`; response `transaction_id`, `operation_id`, `crypto_transfers[]` |

## Recipients

| Method | Path | Permission | Purpose |
|---|---|---|---|
| GET | `/api/v1/recipients` | none | List recipients |
| GET | `/api/v1/recipients/{recipientId}` | none | One recipient |
| GET | `/api/v1/recipients/filter/name` | none | Query `name` substring |
| GET | `/api/v1/recipients/filter/catalog` | none | Query `catalog_index` (single letter) |
| GET | `/api/v1/recipients/filter/currency` | none | Query `currency` |
| GET | `/api/v1/recipients/filter/type` | none | Query `type` (details type) |
| POST | `/api/v2/recipients` | `TransactionSu`, `TransactionManage` | Create identity plus first payment details, with name check |
| PUT | `/api/v2/recipients/{recipientId}` | same | Update identity and details in one call |
| POST | `/api/v1/recipients` | same | v1: create identity only (`is_business`, names) |
| PUT | `/api/v1/recipients/{recipientId}` | same | v1: update identity only |
| DELETE | `/api/v1/recipients/{recipientId}` | same | Delete recipient |
| POST | `/api/v1/recipients/{recipientId}/payment_details` | same | Add a rail |
| PUT | `/api/v1/recipients/{recipientId}/payment_details/{paymentDetailsId}` | same | Replace details |
| DELETE | `/api/v1/recipients/{recipientId}/payment_details/{paymentDetailsId}` | same | Remove one rail |
| POST | `/api/v1/recipients/{recipientId}/usage` | `TransactionSu`, `TransactionCreate`, `TransactionManage` | Increment usage counter (not automatic) |

Field details per rail: [RECIPIENTS.md](RECIPIENTS.md).

## Activity

| Method | Path | Permission | Purpose | Key fields |
|---|---|---|---|---|
| GET | `/api/v1/activity/feed` | none | Transaction feed | query `types[]` XOR `subject` (address or UUID), pagination; items `id`, `type`, `status`, `direction`, `activity_steps[]` |
| POST | `/api/v1/activity/statement/full` | none | Period statement | body `start`, `end` (Unix seconds, max 6 months); response `balances[]`, `transactions[]` |
| GET | `/api/v1/withdrawal/requests` | none | ERC-20 withdrawals awaiting on-chain execution | `to_address`, `call_data`, `valid_after`, `valid_before` |

The reference also lists `GET /api/v1/test/{type}`, an internal request-parsing test endpoint; do not use it.

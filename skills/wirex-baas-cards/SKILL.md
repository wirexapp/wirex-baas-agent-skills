---
name: wirex-baas-cards
description: "Wirex BaaS card management — issue Visa cards, retrieve card details, manage card lifecycle. Covers virtual, plastic, and metal card issuance (v1 external fee, v2 direct fee, v3 configurable / Bridge rail) and order fees, card activation, block/unblock/close, card reissue, card name change, sensitive card details (PAN/CVV/PIN via action token from wallet signature or SMS OTP), spending limits (daily/monthly/per-transaction settable, lifetime read-only), card transaction lifecycle (on-chain debit/credit via activity webhooks), card top-up from an external card, and 3DS authentication (OTP via SMS and webhook in-app confirmation approve/decline)."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Card Management

## Overview

The Wirex BaaS card system provides Visa virtual, plastic, and metal card issuance, lifecycle management, secure details retrieval, configurable limits, an on-chain transaction flow reported through activity webhooks, card top-up from external cards, and 3DS authentication handling (OTP via SMS and in-app confirmation via webhook). Cards are linked to user wallets and spend the user's unified balance (WUSD/WEUR). Cards are multi-currency: there is no fixed card currency.

> This skill covers the **retail** API. Corporate cards use separate corporate endpoints. For External Authorization (partner-held balances) see the External Authorization guide: issuance works the same, but settlement is against your Master Account and v3 issuance is not available.

### Required Headers

| Header | Description |
|--------|-------------|
| `Authorization` | Bearer token (S2S token, or user-scoped token from `POST /api/v1/user/authorize`) |
| `X-Chain-Id` | Blockchain chain ID |
| `X-User-Wallet` | User's EOA (not the Smart Wallet address). Needed with an S2S token to name the user (exactly one of `X-User-Wallet`, `X-User-Email`, `X-User-Id`); not needed with a user-scoped token, where identity is in the token |

### Card Types and Capabilities

| Type | Capability Required | Delivery | Activation |
|------|-------------------|----------|------------|
| **Virtual** | `VisaVirtualCard` | Instant (digital), no `delivery_address` | Not required (activation is for physical cards only) |
| **Plastic** | `VisaPlasticCard` | Shipped to address | Required (`NotActivated` until activated) |
| **Metal** | `VisaMetalCard` | Shipped to address | Required |

On v3, `BridgeVirtualCard` / `BridgePlasticCard` capabilities let an order resolve to the Bridge rail (Visa is tried first). Metal has no Bridge counterpart.

Check eligibility with `GET /api/v2/user` -> `capabilities[]`. Capability `status`: `Active` (can issue), `NotFulfilled` (see `status_reason`, e.g. missing verification level), `NotAvailable`; the API reference enum also has `ActivationNotStarted`, `InProgress`, `NotRequired` (the guide lists only the first three).

---

## Card Issuance

Issuing a card always carries an issuance fee paid in crypto, **if fees are enforced for your company** (`GET .../fees/...` returns `400 ErrorNotSupported` "You have no card order/delivery fees to pay" otherwise; skip the fee steps and issue directly). Fee endpoints apply only if your account manager advised fee handling. Every issue call returns `{ "id": "<card id>" }`; the card starts `Requested`, then becomes `NotActivated` once processed, and a card webhook follows.

| | v1 -- External Fee | v2 -- Direct Fee | v3 -- Bridge Rail, Configurable |
|---|---|---|---|
| Fee collection | You pay on-chain to the invoice `recipient_address` | Auto-debited by Wirex at issuance | Auto-debited by Wirex at issuance |
| Fee invoice | `POST /api/v1/cards/{type}/fees/{country}/payment` | `POST /api/v2/cards/{type}/fees/{country}/payment` | same v2 invoice call (no v3 invoice) |
| Passed at issuance | `payment_transaction_hash` | `delivery_id` | `delivery_id` (only when the order is priced above zero) + optional product selection (`product` / `product_type` / `payment_system` / `design` / `card_program`) / `card_wallet_address` |
| `name_on_card` | Ignored: the card carries the KYC name | Ignored: the card carries the KYC name | Printed, uppercased |
| Issue endpoints | `POST /api/v1/cards/virtual\|plastic\|metal` | `POST /api/v2/cards/virtual\|plastic\|metal` | `POST /api/v3/cards/virtual\|plastic\|metal` |
| Works in | On-chain and External Authorization | On-chain and External Authorization | On-chain only |

Common steps: `GET /api/v1/cards/{type}/fees/{country}` (type `virtual`/`plastic`/`metal`, case-insensitive) -> create fee invoice (body `token_address`, `delivery_provider` for physical) -> issue card. Physical cards also use `GET /api/v1/cards/delivery/countries` (array of country codes) and `GET /api/v1/cards/delivery/methods/{country}` (array with `provider`, `fee`, `currency`). Physical cards need `delivery_address` (`line1`, `city`, `zip_code`, `country` required; `zip_code` always required, send a placeholder like `"00000"` where no postal code exists). The API reference documents `POST /api/v2/cards/plastic` twice with different names for this field: `zip_code` ("direct invoice" page) and `postal_code` ("Issue plastic card (v2)" page, newer) — confirm with Wirex which one your flow expects. `card_name` 1-50 chars. `name_on_card` is used only by v3 and has no pattern check (the card processor may reject with `400 "Request failed due to external validation failure"`).

v3 extras: `GET /api/v3/cards/config` lists orderable `products[]` per format (`product`, `product_type` `Debit`/`Credit`, `provider`, `payment_system`, `designs`, `card_programs`, `countries`); filter by the user's residence country, one product name can appear more than once. **Product selection is all or none**: send all five of `product`, `product_type`, `payment_system`, `design`, `card_program` from one product entry, or none for the issuer's defaults (some -> `400 ErrorMissingField`; a combination the issuer does not offer -> `400 "Request failed due to external validation failure"`). `payment_system` is `Visa` or `MasterCard`. A v3 order that is priced above zero without `delivery_id` fails (`ErrorGeneral`); create the v2 fee invoice first. `card_wallet_address` is required only when the order resolves to Bridge (a confirmed wallet of type `Card`), rejected on Visa and always rejected for metal. The rail is never chosen in the request.

See [reference](references/REFERENCE.md) for request/response shapes and errors.

---

## Card Lifecycle

### Status Flow

`Requested -> NotActivated -> Active <-> Blocked -> Closed` (physical cards need activation; virtual cards need none).

> **WARNING:** Closing a card is **irreversible**.

| Status | Description |
|--------|-------------|
| `Requested` | Order submitted, processing |
| `NotActivated` | Issued, awaiting activation |
| `Active` | Usable |
| `Blocked` | Temporarily blocked; can be unblocked |
| `Closed` | Permanently closed, by you or by Wirex after a reissue |

Each card carries `allowed_actions[]` (types `Activate`, `Block`, `Unblock`, `Close`, `SetLimit`, `GetDetails`, `GetCvv`, `GetPin`, `Reissue`, `SetActiveBalance`, with `relative_path`); it reflects status only, not token scope. Action gates: Activate only in `NotActivated`; Block only `Active`; Unblock only `Blocked`; Close in `Active`/`Blocked`; limits and details/CVV/PIN only `Active`; Reissue in `NotActivated`/`Active`/`Blocked` (by the user) once the card is old enough; rename works in any status. Refusals are `ErrorInvalidStatus`.

### Management Endpoints

| Action | Endpoint | Method | Body |
|--------|----------|--------|------|
| Activate | `/api/v1/cards/{cardId}/activate` | PUT | `card_number_last4`, `expiry_date` (`MM/YYYY`) |
| Block | `/api/v1/cards/{cardId}/block` | PUT | none |
| Unblock | `/api/v1/cards/{cardId}/unblock` | PUT | none |
| Close | `/api/v1/cards/{cardId}/close` | PUT | none |
| Change name | `/api/v1/cards/{cardId}/name` | PUT | `name` (`^[a-zA-Z0-9\-':+# @]{1,50}$`) |

List: `GET /api/v1/cards` (`page_number`, `page_size` default 25, `sort`=`name`\|`usage`); `GET /api/v3/cards` and `GET /api/v3/cards/{cardId}` read across every chain the user holds a card on and add `product`, `product_type` and `region` to each card.

### Reissue (lost, stolen, damaged or expiring card)

> The guide marks reissue as **in active testing**: the endpoint will change before it is final.

`POST /api/v3/cards/{cardId}/reissue` (v3 only, any card whose `allowed_actions` lists `Reissue`, whichever version issued it) creates a replacement with its own `id` on the same format, rail, funding wallet, chain and payment system. Body: `reason` (required: `Expiration`, `Damaged`, `LostOrStolen`, `UpdateProduct`), `delivery_address` (required for plastic/metal, refused for virtual), `delivery_provider` (plastic/metal; required when fees are enforced, else `DHL`), optional `delivery_id` (from the v2 fee invoice when the reissue is priced), optional `card_program`. Response `{ "id": "<replacement card id>" }`.

Rules: card status `NotActivated`, `Active` or `Blocked` by the user (a card blocked by Wirex cannot be reissued: contact support); card age at least 6 months, 6 minutes in sandbox, else `ErrorNotYetValid` with `reissuable_from` in `error_details`. A virtual replacement is `Active` at once; plastic/metal is `NotActivated` and ships. The old card closes when the virtual replacement is issued, or (plastic/metal `Damaged`) when the user activates the replacement; for plastic/metal `LostOrStolen` it is **not** closed automatically, so block it first with `PUT .../block`. Card status webhooks arrive for the replacement and the closed old card, with nothing linking them: keep the mapping from the reissue response.

---

## Card Details Retrieval (PAN, CVV, PIN)

> **WARNING:** `action_token` expires in **5 minutes**; the same token works for PAN, CVV and PIN. Mint a fresh one each time the user opens the card details view.

Requires an `action_token` from one of two confirmations:

1. **Wallet signature** (recommended): sign `By signing this I confirm that I am executing action {ActionType} at {Nonce}`, then `POST /api/v1/confirmation/signature/verify` with `action_type` (`GetCardDetails`, `3dsChallenge`, `VerifyPhone`), `message_signature`, `nonce` (Unix timestamp, valid 5 minutes). Response: `{ "action_token": "..." }`. On XRPL also send `public_key`.
2. **SMS OTP**: `POST /api/v1/confirmation/sms` (`action_type`) -> `{ session_id, attempts_left, code_length, expires_at, resend_at }`, then `POST /api/v1/confirmation/sms/verify` (`session_id`, `code`) -> `{ "token": "..." }` (use as `action_token`).

| Detail | Endpoint | Method | Response |
|--------|----------|--------|----------|
| PAN + Expiry | `/api/v1/cards/{cardId}/details` | POST | `card_number`, `expiry_date` |
| CVV | `/api/v1/cards/{cardId}/cvv` | POST | `cvv` |
| PIN | `/api/v1/cards/{cardId}/pin` | POST | `pin` (physical cards only) |

Body for all three: `{ "action_token": "..." }`. The card must be `Active`.

> These endpoints return cardholder data: call them directly from the client app; proxying through your backend is only allowed if it is PCI DSS compliant. Recommended: the PCI Compliant SDK (skill `wirex-baas-pci-sdk`) reveals PAN/expiry/CVV/PIN inside Wirex-controlled views so the values never reach your app or servers; you still mint the `action_token` and pass it to the SDK. Reveal surfaces: Web `@wirexapp/card-reveal-web` (docs `retail-pci-sdk-web-reveal`), React Native `@wirexapp/mobile-sdk`, Flutter `wirex_mobile_sdk`, iOS `WirexMobileSDK`, Android `com.wirexapp.baas:mobile-sdk`.

---

## Card Limits

Daily, monthly and per-transaction limits are settable; the **lifetime limit is read-only**. Value semantics: positive = hard cap, `-1` = no limit, `0` = blocks all spending. A new card starts with all limits at `-1` (limits cannot be set at issuance). Usage resets at 00:00 UTC (daily), 00:00 UTC on the 1st (monthly); lifetime never resets.

```
GET /api/v1/cards/{cardId}
```

Returns `limit`: `daily_limit`, `daily_usage`, `monthly_limit`, `monthly_usage`, `lifetime_limit`, `lifetime_usage`, `currency` (`transaction_limit` is only delivered in the `card-limits` webhook).

```
PUT /api/v1/cards/{cardId}/limit
{ "daily_limit": 1000.00, "monthly_limit": 20000.00, "transaction_limit": 500.00 }
```

Send only fields to change; `-1` disables. `limit` is an obsolete alias of `daily_limit`. `lifetime_limit` is accepted but ignored. Response: empty `200`. Higher customer limits (standard per-transaction and monthly cap is 30,000 EUR) are requested via a Support Portal ticket with PoI/PoA and SoW/SoF documentation.

---

## Card Transaction Flow

Card transactions execute through the **FundsManagement** contract (ERC-7579 executor on the user's Smart Wallet), tokens WUSD/WEUR (Base, 18 decimals). Each transaction settles from a **single** token: the one with the highest ratio of available balance to required (converted) amount; if no single token covers it, it is declined with `InsufficientFunds`.

Debit stages: `Initiated` -> `CryptoOut` (on-chain debit to FundsBuffer) -> `CardOut` -> `Completed`; `Reversal` returns tokens on failure or refund. Credit (refund/original credit): `Initiated` -> `CardIn` -> `CryptoIn` -> `Completed`.

Webhook `POST /v2/webhooks/activities` (`type: CardTransaction`, `direction: Outbound|Inbound`, `status: Pending|Completed|Failed`) arrives at each stage. `status_reason` examples: `InsufficientFunds`, `DailySpendAmountIsExceeded` (card spending limit exceeded), `ChainRejected`, `BroadcastFailed`, `GeneralError`. Refunds are not separate transactions: the original activity is re-sent with a `Reversal` step and a positive operation. Every webhook carries the full current state with all `operations[]`, each with `operation_id`, `status` (`Pending`/`Completed`/`Failed`, moves only forward) and `operation_reason` (`Authorization`, `Clearing`, `Reversal`, `Refund`, ...); a clearing or refund arrives as a new operation. A full refund/reversal turns the activity `Failed`; a partial refund keeps it `Completed`; a purchase stays `Pending` until its debit settles. Card fees come in `fee_amount`, the card network reference in `rrn`. Deduplicate on each operation's `operation_id` + `status`. A `Pending` operation's `hash` is an interim value, not an on-chain hash; use `amount_precise` for accounting.

`GET /api/v1/transactions/card` is **deprecated**; use `GET /api/v2/activity/feed?types=CardTransaction`. The card `withdraw/estimate|execute` endpoints (`/api/v1/cards/{cardId}/withdraw/...`) were deprecated and their reference pages and SDK methods are gone from the current docs. Sending funds to an external card (push to card) uses `POST /api/v1/cards/transfer/estimate` + `POST /api/v1/cards/transfer` (see the transfers skill).

---

## Card Top-Up (from an external card)

Funds a user wallet from an external Visa/Mastercard via AFT rails. Requires the `CardTopup` capability (`WalletTopup` for `apple_pay` / `google_pay`).

1. Register the source card in the PCI environment: `POST {pci_base_url}/b2b/cards/topup?user_id={user_id}` (user-scoped token) -> `card_id`. Also `GET` (list) and `DELETE .../{card_id}`.
2. `POST /api/v1/cards/topup/estimate` with `external_card_id`, `destination_amount` (integer string in token base units), `destination_token_address`, optional `payment_method` (`external_card` default, `apple_pay`, `google_pay`) -> `estimation_id`, source/destination amounts, fee, `expires_at`.
3. `POST /api/v1/cards/topup/execute` with `estimation_id`, optional `device_id` -> `id`, `status`, optional `three_ds_state` (`flow` is `Unknown` at execute; whenever `url` is present, load it on the cardholder's device: the page runs the issuer device check, then completes frictionless or shows the challenge; a top-up whose page is never loaded stays `Pending`; no `three_ds_state` = no 3DS step).
4. Completion arrives as an activity webhook (`type: CardTopup`, `direction: Inbound`).

Restricted top-up token: `POST /api/v1/cards/topup/token` (user token, no body) -> `{ access_token, expires_at }`; accepted only by top-up estimate and execute (any other endpoint returns `401 Token is not allowed for this endpoint`), valid 15 minutes, one per armed quote, never hand the user's session token to a checkout. The mobile SDKs' wallet checkout passes it as `checkoutToken`.

> Recommended: the PCI Compliant SDK (skill `wirex-baas-pci-sdk`) collects the source card and returns the same `card_id`, runs the 3DS step (pass it `three_ds_state.url`) and, on mobile, hosts the Apple Pay / Google Pay checkout. Web `@wirexapp/card-topup-web` (docs `retail-pci-sdk-web-topup-collect`, `retail-pci-sdk-web-3ds`); React Native `@wirexapp/mobile-sdk`; Flutter `wirex_mobile_sdk`; iOS `WirexMobileSDK`; Android `com.wirexapp.baas:mobile-sdk`. Call the PCI environment directly only from a PCI DSS compliant environment.

---

## 3DS Authentication

This section covers purchases made with a Wirex-issued card. The 3DS surfaces of the PCI Compliant SDK cover card top-up only.

Two methods, shown to the user in the 3DS window:

### Method 1: OTP via SMS

An OTP is sent to the phone number given at registration and entered in the 3DS form. **No backend involvement** from the partner.

### Method 2: In-App Confirmation via Webhook

1. Wirex sends `POST /v2/webhooks/3ds`: `card_id`, `user_address` (`owner` is a deprecated mirror), `transaction_id`, `merchant_name`, `amount`, `currency`, `card_last_4`
2. Partner shows an approval UI (merchant, amount, last 4 digits)
3. Partner calls approve or decline
4. A request expires **5 minutes after creation** (the expiry timestamp is not in the payload; start your countdown on receipt)

| Action | Endpoint | Method |
|--------|----------|--------|
| Get pending | `/api/v1/cards/3ds/requests` | GET (JSON array, undecided and unexpired only) |
| Approve | `/api/v1/cards/3ds/requests/{transactionId}/approve` | POST |
| Decline | `/api/v1/cards/3ds/requests/{transactionId}/decline` | POST |

Approve/decline take **no body and no `action_token`**; success is `200 {}`. Unknown, already decided, expired, or foreign transactions all return the same `400 ErrorNotFound` (no `401`); treat it as terminal. A decision cannot be replayed.

**Sandbox:** card transaction simulations do not raise 3DS challenges. Raise one with the Helper API `POST /card/3ds/initiate` (see the wirex-baas-sandbox skill).

---

## Webhooks

| Webhook | Endpoint | Trigger |
|---------|----------|---------|
| Card status | `/v2/webhooks/cards` | Card status changes (payload = `GET /api/v1/cards` item) |
| Card limits | `/v2/webhooks/card-limits` | Limit or usage updates |
| Activities | `/v2/webhooks/activities` | Card transactions, top-ups |
| 3DS | `/v2/webhooks/3ds` | 3DS authentication requests |

---

## Quick Reference

| Action | Endpoint | Method |
|--------|----------|--------|
| List cards | `/api/v1/cards` (v3: `/api/v3/cards`) | GET |
| Get card | `/api/v1/cards/{cardId}` | GET |
| Order fees | `/api/v1/cards/{type}/fees/{country}` | GET |
| Fee invoice (v1 / v2) | `/api/v1\|v2/cards/{type}/fees/{country}/payment` | POST |
| Issue virtual / plastic / metal | `/api/v1\|v2\|v3/cards/virtual\|plastic\|metal` | POST |
| Order config (v3) | `/api/v3/cards/config` | GET |
| Activate / Block / Unblock / Close | `/api/v1/cards/{cardId}/activate\|block\|unblock\|close` | PUT |
| Change card name | `/api/v1/cards/{cardId}/name` | PUT |
| Reissue card (v3) | `/api/v3/cards/{cardId}/reissue` | POST |
| Get PAN / CVV / PIN | `/api/v1/cards/{cardId}/details\|cvv\|pin` | POST |
| Update limits | `/api/v1/cards/{cardId}/limit` | PUT |
| Top-up estimate / execute | `/api/v1/cards/topup/estimate\|execute` | POST |
| Restricted top-up token | `/api/v1/cards/topup/token` | POST |
| 3DS requests | `/api/v1/cards/3ds/requests` | GET |
| Approve / Decline 3DS | `/api/v1/cards/3ds/requests/{transactionId}/approve\|decline` | POST |

---

## References

- [Card API Reference](references/REFERENCE.md) -- Request/response schemas, error codes, field validation patterns, and JavaScript examples
- See [webhook payloads](../wirex-baas-webhooks/references/REFERENCE.md) for complete webhook payload examples

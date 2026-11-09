# Wirex BaaS Corporate — Cards

Guides: [Cards](https://docs.wirexapp.com/docs/corporate-cards), [Issuing a Card](https://docs.wirexapp.com/docs/corporate-card-issuance), [Card Details](https://docs.wirexapp.com/docs/corporate-card-details), [Managing a Card](https://docs.wirexapp.com/docs/corporate-card-management), [3DS Authentication](https://docs.wirexapp.com/docs/corporate-3ds-authentication), [Auth Tokens](https://docs.wirexapp.com/docs/corporate-auth-tokens).

## Table of Contents

- [Model](#model)
- [Issuance and Fee Flows](#issuance-and-fee-flows)
- [Linking a Card to an Employee](#linking-a-card-to-an-employee)
- [Card Validation Rules](#card-validation-rules)
- [Listing Cards](#listing-cards)
- [Sensitive Data: Action Tokens](#sensitive-data-action-tokens)
- [Managing a Card](#managing-a-card)
- [Spending Limits](#spending-limits)
- [3DS Challenges](#3ds-challenges)
- [Card Webhooks](#card-webhooks)
- [Errors](#errors)

---

## Model

Corporate cards are issued against the corporation wallet and spend from its token balances. Formats: `Virtual` (instant) and `Plastic` (shipped, activated on arrival). Metal cards are **not** issued by the Corporate API. Ceilings: 30 virtual and 15 plastic cards per corporation; at the ceiling the capability turns `NotAvailable` until a card is closed. Issuance needs `VisaVirtualCard` / `VisaPlasticCard` `Active` and the profile `Active`.

Status lifecycle: `Requested` -> `NotActivated` -> `Active`; `Active` <-> `Blocked`; `Closed` is terminal. A virtual card goes `Requested` -> `Active`; a plastic card stops at `NotActivated` until `PUT /api/v1/cards/{cardId}/activate`.

| Action | Allowed in | Refusal text |
|---|---|---|
| Activate | `NotActivated` | `Card is not issued yet` (Requested), `Card is already activated` |
| Block | `Active` | `Card status does not allow blocking`, `Card is already blocked` |
| Unblock | `Blocked` | `Card is not blocked` |
| Close | `Active`, `Blocked` | `Card status does not allow closing`, `Card is already closed` |
| SetLimit | `Active` | `Card status does not allow limit changes` |
| Details, CVV, PIN | `Active` | `Card status does not allow details retrieval` (and CVV / PIN variants) |
| Rename | any status | none |

## Issuance and Fee Flows

1. `GET /api/v1/corporations` — confirm the format's capability is `Active`.
2. `GET /api/v1/cards/{type}/fees/{country}` (`type` = `Plastic`, `Virtual`, `Metal`, case-insensitive; `country` uppercase ISO 3166-1 alpha-2). The answer decides the flow:
   - `400 ErrorNotSupported` / `You have no card order/delivery fees to pay` — fees not enforced: skip every fee step and issue directly.
   - `400 ErrorNotSupported` / `Card issuance is not supported for this company` — no card configuration; contact Wirex.
   - `200` with `order_fee` — fees enforced: pick the v1, v2 or v3 flow and follow it end to end. v3 (`POST /api/v3/cards/virtual`, `/plastic`) uses the v2 invoice (`delivery_id`; v3 has no invoice endpoint of its own), takes optional `design`, `card_program`, `payment_system` from `GET /api/v3/cards/config`, and needs the fee only when the order is priced above zero (v1 likewise needs `payment_transaction_hash` only then). `order_fee` excludes delivery; the invoice returns the combined total.
3. Plastic only: `GET /api/v1/cards/delivery/countries` (array of ISO codes) and `GET /api/v1/cards/delivery/methods/{country}` (`provider`, `fee`, `currency`, `estimated_payment_amounts[]`). `provider` is the value passed as `delivery_provider`.

Fee endpoints are applicable only if your account manager advised you to handle card fees.

| | v1 external fee | v2 direct fee |
|---|---|---|
| Fee invoice | `POST /api/v1/cards/{type}/fees/{country}/payment` returns `recipient_address`, `payment_amount` | `POST /api/v2/cards/{type}/fees/{country}/payment` returns `delivery_id` (integer), `recipient_address`, `payment_amount` |
| Settlement | You transfer `payment_amount.precise_amount` of `payment_amount.token_address` to `recipient_address` on-chain and keep the tx hash | Wirex debits at issuance |
| Issue | `POST /api/v1/cards/virtual` or `/plastic` with `payment_transaction_hash` | `POST /api/v2/cards/virtual` or `/plastic` with `delivery_id` |

Do not mix: `delivery_id` is ignored by v1 endpoints and `payment_transaction_hash` by v2. `delivery_id` is single use and consumed by the issuance call; do not retry a failed v2 issuance with the same id, create a new invoice.

Invoice body (both versions): `{"token_address": "<token_address>", "delivery_provider": "<provider>"}`; `delivery_provider` is required unless the type is `Virtual`.

Issue bodies (response `{"id": "<card_id>"}`):

```json
{
  "card_name": "<card_name>",
  "name_on_card": "<name_on_card>",
  "employee_id": "<employee_uuid>",
  "delivery_id": 1
}
```

Plastic adds `delivery_provider` and `delivery_address` (`line1`, `city`, `postal_code`, `country` required; `line2`, `state` optional). v1 replaces `delivery_id` with `payment_transaction_hash`. `payment_transaction_hash` (v1) and `delivery_id` (v2) are required only when fees are enforced; `delivery_provider` defaults to `DHL` when fees are not enforced.

Processor-side address rejection returns a synchronous `400`; no card is created and no webhook is sent.

## Linking a Card to an Employee

`employee_id` is optional, must belong to this corporation, and cannot be added or changed afterwards (there is no link endpoint). It decides three things at issuance:

1. **Visibility.** Without `Su` / `CardSu` a caller sees only cards linked to them; an unlinked card is invisible to everyone but a card administrator.
2. **Embossed name.** With a linked employee that has `first_name`, `last_name`, `email` and `phone`, the card carries `"<first_name> <last_name>"` truncated to 25 characters and `name_on_card` is **ignored**. To emboss a corporate name, issue without `employee_id`.
3. **Billing address.** The corporation's legal address is sent to the processor; with none on record issuance fails `400 ErrorMissingField` / `Failed to determine billing address for the card`.

The employee is validated before the fee is charged. A foreign `employee_id` gives `401` / `Employee does not belong to corporation`.

`Failed to link card to employee` (500) means the card **exists** but is not linked; retrying issuance creates a second card.

## Card Validation Rules

| Field | Pattern |
|---|---|
| `card_name`, rename `name` | `^[a-zA-Z0-9]+[a-zA-Z0-9\-':+#& ]{1,50}$` |
| `name_on_card` | `^[A-Za-z][A-Za-z .'-]{1,25}$` |
| `delivery_address.line1` / `line2` | `^[A-Za-z0-9&.,'’\-/() :+#]{2,100}$` |
| `delivery_address.city` | `^[A-Za-z\s\-'.]{2,100}$` (no digits) |
| `delivery_address.state` | `^[A-Za-z][A-Za-z\s\-']{1,99}$` |
| `delivery_address.postal_code` | `^[A-Za-z0-9\s\-]{3,12}$`; always required, send a placeholder matching the pattern where a country has no postal code |
| `delivery_address.country` | `^[A-Z]{2}$` |
| `card_number_last4` (activate) | `^\d{4}$` |
| `expiry_date` (activate) | `^(0[1-9]\|1[012])/\d{4}$` (four-digit year) |

The address field is `postal_code` on input and `zip_code` on the card record returned by `GET /api/v1/cards`. Activation uses `card_number_last4` (no underscore before the 4) while the card record reports `card_data.card_number_last_4`.

## Listing Cards

`GET /api/v1/cards` (`CardSu` or `CardView`); query `employee_id`, `page_number`, `page_size`. Get one card with `GET /api/v3/cards/{cardId}` (`CardSu` or `CardView`; `GET /api/v3/cards` lists across every chain), or read the v1 list and filter on `id`. `CardView` alone sees only its own linked cards and a sent `employee_id` filter is dropped without error.

Card item: `id`, `card_wallet_address`, `status` (`Requested`, `NotActivated`, `Active`, `Blocked`, `Closed`), `status_reason`, `previous_status`, `card_data` (`name_on_card`, `payment_system` `Visa`/`MasterCard`, `card_number_first_4` only while `Requested`/`NotActivated`, `card_number_last_4` and `expiry_date` `MM/YY` on the list (the details call returns `MM/YYYY`; do not compare the strings directly) afterwards, `format`, `card_name`, and when set `design`, `card_program`, `region`), `limit`, `delivery_address`, `allowed_actions[]` (`type`, `relative_path`; reflects card status only, not caller permissions), `created_at`, `updated_at`.

## Sensitive Data: Action Tokens

PAN, expiry, CVV and PIN each need an **action token** on top of the corporation token.

1. Form the message exactly: `By signing this I confirm that I am executing action GetCardDetails at <nonce>` where `<nonce>` is the current Unix time in seconds.
2. Sign it with the employee's wallet key (the `employee_address` claim). EVM: personal-sign (EIP-191), `0x` hex signature. Stellar: sign the SHA-256 hash, base64 signature.
3. `POST /api/v1/confirmation/signature/verify` (`CardSu` or `CardViewDetails`):

```json
{
  "action_type": "GetCardDetails",
  "message_signature": "<signature>",
  "nonce": 1
}
```

Response `{"token": "<action_token>"}`. The nonce expires after 120 seconds (`Invalid nonce`); the action token lives 5 minutes. Sign, exchange and read in one interaction.

4. `POST /api/v1/cards/{cardId}/details`, `/cvv` or `/pin` with `{"action_token": "<action_token>"}` (`CardSu` or `CardViewDetails`; card must be `Active`). Responses: `card_number` + `expiry_date`; `cvv`; `pin`. One `GetCardDetails` token unlocks all three.

`action_type` values: `GetCardDetails`, `3dsChallenge` (case-insensitive match, send exactly). A token for a different purpose fails `400 ErrorInvalidField` with `action_token: invalid_purpose` (not an expiry; retrying does not help). Other token errors: `ErrorExpired` (`action_token: expired`), `invalid_token`, `invalid_claims`. `POST /api/v1/confirmation/signature` is the obsolete form. There is no SMS confirmation route.

Never log or persist PAN, CVV, PIN or action tokens. Mint tokens on demand, not speculatively.

A `3dsChallenge` token is refused by every card-data endpoint (`invalid_purpose`, PIN included): the 3DS guide now says the same and tells you to read PIN, PAN or CVV during a challenge with a `GetCardDetails` token. Details of the sentence and errors: [Action Confirmation Signatures](https://docs.wirexapp.com/docs/corporate-action-confirmation-signatures).

## Managing a Card

All status changes need `CardSu` or `CardManage`; responses are `{}`.

| Action | Call |
|---|---|
| Activate (plastic only) | `PUT /api/v1/cards/{cardId}/activate` body `card_number_last4`, `expiry_date` |
| Block / Unblock | `PUT /api/v1/cards/{cardId}/block`, `/unblock` (no body); block is reversible |
| Close | `PUT /api/v1/cards/{cardId}/close` (no body); permanent, frees a slot against the 30/15 ceiling |
| Rename | `PUT /api/v1/cards/{cardId}/name` body `{"name": "<card_name>"}`; changes the display label only, never `name_on_card` |

Read `allowed_actions` before acting. A `cardId` that does not belong to the corporation fails as a card lookup `500`.

## Spending Limits

`PUT /api/v1/cards/{cardId}/limit` (`CardSu` or `CardLimitManage`; card `Active`). Body fields `daily_limit`, `monthly_limit`, `transaction_limit` (numbers; `-1` disables) and obsolete `limit` (alias for `daily_limit`, wins when both sent).

```json
{
  "daily_limit": 1000,
  "monthly_limit": 10000,
  "transaction_limit": 500
}
```

**The call replaces the whole limit set.** Any limit you omit becomes `-1` (disabled). Read current limits from `GET /api/v1/cards` and send all three back. The lifetime limit is set to `-1` on every call and cannot be configured. The current state is in `limit`: `daily_limit`, `daily_usage`, `monthly_limit`, `monthly_usage`, `transaction_limit`, `currency`.

Note: docs differ. The reference schema marks `daily_limit`, `limit`, `monthly_limit` and `transaction_limit` as required, while its description and the Managing a Card guide say omitted fields are disabled. Send all three limits explicitly.

## 3DS Challenges

A merchant's 3D Secure request holds the transaction until the corporation decides. Challenges arrive at `/v2/webhooks/3ds` and can be polled.

1. `GET /api/v1/cards/3ds/requests` (`CardSu` or `CardViewDetails`) returns a bare JSON array of active challenges: `transaction_id`, `card_id`, `card_last_4`, `amount` (string), `currency`, `merchant_name`. The list is corporation-wide, not per employee; decided challenges disappear.
2. `POST /api/v1/cards/3ds/requests/{transactionId}/approve` or `/decline` (`CardSu` or `CardManage`; no body; response `{}`). `{transactionId}` matches case-insensitively.
3. Decisions are final. A second call returns `400 ErrorNotFound` / `No active 3DS request for this transaction` (already decided, or not yours, indistinguishable). Treat it as success for idempotency and never follow it with the opposite decision.
4. Webhook delivery is best-effort (10 s timeout, no retries): also poll the list on a schedule, since an undecided challenge blocks a real transaction.

Approve and decline take the corporation token and no body; the Auth Tokens guide no longer lists them as needing a `3dsChallenge` action token.

## Card Webhooks

- `POST {your_webhook_base_url}/v2/webhooks/cards` on issuance, activation, block, unblock, close. The payload is the shared retail card shape and carries `generation`, `balances` and `lifetime_limit` / `lifetime_usage` inside `limit`, which the Corporate card list does not; ignore them. `card_number_first_4` is present while `Requested` or `NotActivated`; `card_number_last_4` and `expiry_date` appear later.
- `POST {your_webhook_base_url}/v2/webhooks/card-limits` when a limit or its usage changes.
- `POST {your_webhook_base_url}/v2/webhooks/3ds` when a challenge is raised.

## Errors

| HTTP | Reason | Message / detail | Fix |
|---|---|---|---|
| 400 | `ErrorNotFound` | `No fees found for specified country and method` | Format not offered there |
| 400 | `ErrorMissingField` | `delivery provider is required for physical cards` | Use `provider` from delivery methods |
| 400 | `ErrorInvalidField` | `Invalid value for type` / `Invalid format for country` | `Plastic`, `Virtual`, `Metal` (the fee endpoint accepts `Metal`, but no version issues metal cards); uppercase two letters |
| 400 | `ErrorGeneral` | `Delivery ID is required and must be positive` | Create a v2 invoice |
| 400 | `ErrorGeneral` | `Cards name is invalid` / `Name on card is invalid` | Match the patterns |
| 400 | `ErrorGeneral` | `Capability is not active` | Card capability not `Active` |
| 400 | `ErrorInvalidStatus` | `Action is not allowed` (`action_type`, `value` = current status) | Check `allowed_actions` |
| 400 | `ErrorInvalidField` | `Invalid nonce` / `Invalid signature` | Re-sign within 120 s |
| 401 | `ErrorGeneral` | `Employee does not belong to corporation` | Wrong `employee_id` |
| 403 | `ErrorPermissionDenied` | `User does not have required permissions` | See permission matrix |
| 500 | `ErrorGeneral` | `Failed to process delivery payment` | `delivery_id` expired, used or unfunded; new invoice |
| 500 | `ErrorGeneral` | `Failed to issue virtual card` / `Failed to issue plastic card` | Processor rejected; nothing created |
| 500 | `ErrorGeneral` | `This signature does not belong to you` | Signature recovers to a different address than `employee_address` |
| 500 | `ErrorConfigurationInvalid` | `Card configuration is missing` | Contact Wirex |

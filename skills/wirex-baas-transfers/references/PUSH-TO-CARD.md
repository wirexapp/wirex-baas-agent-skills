# Wirex BaaS Transfers — Push-to-Card Reference

Detailed reference for Push-to-Card transfers via Visa/Mastercard OCT (Original Credit Transaction) rails, including PCI tokenization, recipient creation, estimation, and execution.

## Table of Contents

- [PCI Environment URLs](#pci-environment-urls)
- [Step 1: Card Tokenization](#step-1-card-tokenization)
- [Step 2: Create Card Recipient](#step-2-create-card-recipient)
- [Step 3: Estimate Transfer](#step-3-estimate-transfer)
- [Step 4: Execute Transfer](#step-4-execute-transfer)
- [Activity Steps](#activity-steps)
- [Capability Requirements](#capability-requirements)
- [Error Codes](#error-codes)

---

## PCI Environment URLs

Card tokenization must be performed against the PCI-compliant card manager service. Use the appropriate URL for your environment:

| Environment | URL                                                                |
|-------------|--------------------------------------------------------------------|
| Sandbox     | `https://wx-acquiring-card-manager-uat.wirexapp.com`               |
| Production  | `https://wx-acquiring-card-manager.wirexapp.com`                   |

All card data (card number, cardholder name) is sent only to the PCI endpoint and never to the main API. The main API only receives tokenized references.

Recommended: the PCI Compliant SDK collects the card inside Wirex-controlled views and returns the same card token, so the PAN never reaches your app or servers (browser `@wirexapp/card-oct-web` returns `externalCardId`, `brand`, `bin`, `last4`; also React Native `@wirexapp/mobile-sdk` profile `oct-destination`, Flutter `wirex_mobile_sdk`, iOS `WirexMobileSDK`, Android `com.wirexapp.baas:mobile-sdk`). Call the PCI environment directly only from a PCI DSS compliant environment.

---

## Step 1: Card Tokenization

### POST {pci_url}/b2b/cards/oct?user_id={user_id}

Tokenize a card for use in Push-to-Card transfers. The card number is validated and a secure token is returned.

> **Authentication:** This endpoint requires a **user-scoped token** obtained via [User Token Issuance](../../wirex-baas-auth/SKILL.md#method-2-user-token-issuance). S2S tokens are not supported for this endpoint.

**Query Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `user_id` | Yes      | User UUID from `GET /api/v2/user` response (`id` field) |

**Request Headers:**

| Header         | Required | Description                        |
|---------------|----------|------------------------------------|
| Authorization  | Yes      | Bearer `{user_token}` (user-scoped, not S2S) |
| Content-Type   | Yes      | `application/json`                 |

> Identity headers (`X-User-Wallet`, `X-Chain-Id`) are not documented for this endpoint; the user-scoped token carries the user identity.

**Request Body:**

```json
{
  "card_number": "4111111111111111",
  "cardholder_name": "JANE SMITH",
  "card_label": "Jane's Visa",
  "is_saved": true,
  "is_third_party": false
}
```

**Request Fields:**

| Field           | Type    | Required | Description                                        |
|-----------------|---------|----------|----------------------------------------------------|
| card_number     | string  | Yes      | Full card number (PAN). Visa or Mastercard only.   |
| cardholder_name | string  | Yes      | Name as printed on the card (uppercase recommended)|
| card_label      | string  | No       | Display label for the card                         |
| is_saved        | boolean | Yes      | Whether to save the card for future use            |
| is_third_party  | boolean | No       | `true` if the card belongs to someone else         |

**Validations Performed:**

| Validation          | Description                                          |
|--------------------|------------------------------------------------------|
| Luhn check          | Not checked: the card number's Luhn digit is not verified; validate it in your form or use the PCI Compliant SDK |
| Network check       | Only Visa and Mastercard are supported               |
| Expiration check    | Card must not be expired (if expiry provided)        |

**Response (200 OK):**

```json
{
  "value": "63c4dd27-1f95-42b1-9a09-35cdda05f4c6"
}
```

**Response Fields:**

| Field | Type   | Description                                         |
|-------|--------|-----------------------------------------------------|
| value | string (UUID) | Card token. Pass it as `card.card_id` when creating the recipient and as `external_card_id` on the transfer |

`is_third_party` is `false` for the user's own card and `true` for a card belonging to another person; third-party transfers may have additional compliance requirements and limits. Use the last 4 digits of the PAN for `card_pan_last` in step 2.

---

## Step 2: Create Card Recipient

### POST /api/v2/recipients

Register the tokenized card as a recipient for transfers.

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
  "first_name": "Jane",
  "last_name": "Smith",
  "is_business": false,
  "type": "Card",
  "currencies": ["USD", "EUR"],
  "card": {
    "card_id": "63c4dd27-1f95-42b1-9a09-35cdda05f4c6",
    "card_pan_last": "1111"
  }
}
```

**Request Fields:**

| Field             | Type     | Required | Description                          |
|-------------------|----------|----------|--------------------------------------|
| first_name        | string   | Yes*     | Recipient first name (personal)      |
| last_name         | string   | Yes*     | Recipient last name (personal)       |
| company_name      | string   | Yes*     | Company name (business recipients)   |
| is_business       | boolean  | Yes      | `false` for personal, `true` for business |
| type              | string   | Yes      | Must be `"Card"`                     |
| currencies        | string[] | Yes      | Supported currencies (e.g., `["USD", "EUR"]`) |
| card.card_id      | string   | Yes      | Token value from step 1              |
| card.card_pan_last| string   | Yes      | Last 4 digits of the card            |

*Either (`first_name` + `last_name`) or `company_name` is required.

**Response (200 OK):**

```json
{
  "id": "uuid-recipient-id",
  "personal_info": {
    "first_name": "Jane",
    "last_name": "Smith",
    "is_business": false
  },
  "payment_details": [
    {
      "id": "uuid-payment-details-id",
      "type": "Card",
      "currencies": ["USD", "EUR"],
      "card": {
        "card_id": "63c4dd27-1f95-42b1-9a09-35cdda05f4c6",
        "card_pan_last": "1111"
      }
    }
  ]
}
```

Use `payment_details[].card.card_id` (the card token) as the `external_card_id` in the estimate step, not `payment_details[].id` (the card-transfer, recipients and tokenization guides now agree; `payment_details[].id` is the `recipient_payment_details_id` of a bank payout). Not confirmed live in sandbox. `card_pan_last` must be exactly 4 digits.

---

## Step 3: Estimate Transfer

### POST /api/v1/cards/transfer/estimate

Estimate the cost and fees for a Push-to-Card transfer.

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
  "external_card_id": "uuid-card-token",
  "currency": "USD",
  "amount": 50.00,
  "tokens": ["0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2"]
}
```

**Request Fields:**

| Field            | Type     | Required | Description                              |
|------------------|----------|----------|------------------------------------------|
| external_card_id | string   | Yes      | Card token (`payment_details[].card.card_id` on the recipient), not `payment_details[].id` |
| currency         | string   | No       | Transfer currency (default: EUR per guide) |
| amount           | number   | Yes      | Amount to send to the card               |
| tokens           | string[] | Yes      | Token address(es) to quote against       |

**Response (200 OK):**

```json
{
  "estimation_id": "uuid-estimation-id",
  "expires_at": 1704110400,
  "currency": "USD",
  "amount": 50.00,
  "amount_precise": "50000000000000000000",
  "decimals": 18,
  "fee_amount": 0,
  "estimated_amounts": [
    {
      "amount": 51.50,
      "precise_amount": "51500000000000000000",
      "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
      "token_symbol": "WUSD",
      "rate": 1.0,
      "fee_amount": 1.5,
      "fee_precise_amount": "1500000000000000000"
    }
  ]
}
```

**Response Fields:**

| Field                              | Type   | Description                              |
|------------------------------------|--------|------------------------------------------|
| estimation_id                      | string | Estimation ID (use in execute step)      |
| expires_at                         | number | Unix timestamp when estimate expires     |
| currency                           | string | Transfer currency                        |
| amount                             | number | Amount credited to the card              |
| amount_precise / decimals          | string / integer | `amount` in base units, scaled by `decimals` |
| fee_amount                         | number | **Deprecated, always `0`.** Read the fee per token from `estimated_amounts[].fee_amount` |
| estimated_amounts                  | array  | Per-token debit amounts                  |
| estimated_amounts[].amount         | number | Human-readable token amount to debit     |
| estimated_amounts[].precise_amount | string | Amount in the token's smallest unit (exponent is the token's `decimals`, not always 18) |
| estimated_amounts[].token_address  | string | Token contract address                   |
| estimated_amounts[].token_symbol   | string | Token symbol (WUSD, WEUR)               |
| estimated_amounts[].rate           | number | Exchange rate applied                    |
| estimated_amounts[].fee_amount / fee_precise_amount | number / string | Per-token fee, included in `amount`; `fee_precise_amount` is always scaled by 18 decimals whatever the token's `decimals` |

---

## Step 4: Execute Transfer

### POST /api/v1/cards/transfer

Execute the Push-to-Card transfer using the estimation ID.

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
  "estimation_id": "uuid-estimation-id",
  "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2"
}
```

**Request Fields:**

| Field          | Type   | Required | Description                          |
|----------------|--------|----------|--------------------------------------|
| estimation_id  | string | Yes      | Estimation ID from step 3            |
| token_address  | string | Yes      | Token to debit (must be one of the `estimated_amounts` entries, e.g. WUSD or WEUR) |
| transaction_authorization | object | Conditional | Required when your company's `transactionAuthorizationMode` is `Signature`, see [Transaction Authorization](https://docs.wirexapp.com/docs/retail-transaction-authorization) |

**Response (200 OK):**

```json
{
  "id": "uuid-activity-id"
}
```

The `id` is the activity ID for tracking the transfer progress via webhooks.

---

## Activity Steps

Push-to-Card transfers progress through the following steps:

**Steps:** Initiated → CryptoOut → Review → CardOut → Completed

Activity `status` is `Pending`, `Completed` or `Failed` (there is no `Cancelled` status: a cancelled movement reads `Failed`; the card-transfer guide also lists `Processing`, which is not in the API reference enum). The final `Completed` step type exists for push-to-card. Webhook `type` is `CardTransfer`, `direction` is always `Outbound`; `destination.type` is `ExternalCard` and `destination.card` carries `id` and `pan_last` (the guide no longer lists `payment_system`).

See [wirex-baas-webhooks reference](../wirex-baas-webhooks/references/REFERENCE.md) for complete activity webhook payloads (transfer type: `CardTransfer`).

> The earlier card-withdrawal endpoints `POST /api/v1/cards/{cardId}/withdraw/estimate` and `/withdraw/execute` were removed (they return `404`); use this flow instead.

---

## Error Codes

| Error Reason | Field | Description |
|-------------|-------|-------------|
| `ErrorMissingField` | `external_card_id` | Card token (`card.card_id`) is required |
| `ErrorInvalidField` | `amount` | Amount must be greater than zero |
| `ErrorMissingField` | `tokens` | At least one token address required |
| `ErrorNotSupported` | | CardTransfer capability not active |
| `ErrorInvalidField` | `estimation_id` / `token_address` | Must be a valid UUID / valid address |
| `ErrorNotFound` | `estimation_id` | Estimation not found or expired |
| `ErrorInsufficientFunds` | | User lacks sufficient token balance |

Tokenization (PCI environment) errors, all HTTP 400: unsupported card type (only Visa and Mastercard), card expired, missing required field. Recipient creation: `ErrorMissingField` for `first_name` / `last_name` / `company_name` / `type` / `card` / `card.card_id` / `card.card_pan_last`; `ErrorInvalidField` for `card.card_pan_last` (must be exactly 4 digits).

### Common Troubleshooting

| Issue                          | Cause                                     | Resolution                                |
|--------------------------------|-------------------------------------------|-------------------------------------------|
| Tokenization fails             | Invalid card number or unsupported network| Verify card is Visa/Mastercard and not expired (Luhn is not checked) |

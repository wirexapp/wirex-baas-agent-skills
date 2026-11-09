# Wirex BaaS Transfers — Recipients CRUD Reference

Complete reference for recipient management: listing, filtering, creating, updating, and deleting recipients. The `type` enum has 16 payment-detail types: Crypto, Sepa, FasterPayment, Ach, Swift, Spei, Card, Pix, FpsHk, Imps, Instapay, BiFast, Nip, Ipp, Pse, CrossChainCrypto.

## Table of Contents

- [List Recipients](#list-recipients)
- [Get Recipient by ID](#get-recipient-by-id)
- [Filter Recipients](#filter-recipients)
- [Create Recipient](#create-recipient)
- [Add Payment Details](#add-payment-details)
- [Update Personal Info](#update-personal-info)
- [Update Payment Details](#update-payment-details)
- [Delete Payment Details](#delete-payment-details)
- [Delete Recipient](#delete-recipient)
- [Payment Type Fields](#payment-type-fields)
- [Recipient Webhook](#recipient-webhook)

---

## Common Headers

All recipient endpoints require the following headers:

| Header         | Required | Description                        |
|---------------|----------|------------------------------------|
| Authorization  | Yes      | Bearer `{access_token}`           |
| Content-Type   | Yes      | `application/json`                 |
| X-User-Wallet  | Yes      | The user's EOA wallet address      |
| X-Chain-Id     | Yes      | The blockchain chain ID            |

---

## List Recipients

### GET /api/v1/recipients

Retrieve a paginated list of all recipients.

**Query Parameters:**

| Parameter   | Type    | Required | Default | Description              |
|------------|---------|----------|---------|--------------------------|
| page_number | integer | No       | 0       | Page number; the guides disagree (0-indexed default vs 1-indexed). `0` and `1` both return the first page (observed live, see BANKING.md) |
| page_size   | integer | No       | 25      | Items per page (maximum 50) |
| sort        | string  | No       | name    | `name` (ascending) or `usage` (descending usage count) |

**Response (200 OK):**

> The list is under `data`, as in the API reference schema (`RecipientsResponse`); live sandbox returned `data` for `GET /api/v1/recipients` (2026-10-25). The guides now also show `data`, with no `items` / `total_count` / `page_number` / `page_size`: the list carries no total count, page until a page returns fewer than `page_size` items.

```json
{
  "data": [
    {
      "id": "uuid-recipient-1",
      "personal_info": {
        "first_name": "Jane",
        "last_name": "Smith",
        "is_business": false,
        "nick_name": null
      },
      "payment_details": [
        {
          "id": "uuid-pd-1",
          "type": "Sepa",
          "currencies": ["EUR"],
          "sepa": {
            "iban": "DE89370400440532013000",
            "bic": "COBADEFFXXX"
          }
        }
      ]
    },
    {
      "id": "uuid-recipient-2",
      "personal_info": {
        "first_name": "Bob",
        "last_name": "Johnson",
        "is_business": false,
        "nick_name": null
      },
      "payment_details": [
        {
          "id": "uuid-pd-2",
          "type": "Card",
          "currencies": ["USD"],
          "card": {
            "card_id": "b7e2c1a4-3f5d-4e6a-9c8b-1d2e3f4a5b6c",
            "card_pan_last": "4242"
          }
        }
      ]
    }
  ]
}
```

---

## Get Recipient by ID

### GET /api/v1/recipients/{recipient_id}

Retrieve a single recipient by their unique ID.

**Path Parameters:**

| Parameter    | Type   | Description              |
|-------------|--------|--------------------------|
| recipient_id | string | The recipient's UUID     |

**Response (200 OK):**

```json
{
  "id": "uuid-recipient-1",
  "personal_info": {
    "first_name": "Jane",
    "last_name": "Smith",
    "is_business": false,
    "nick_name": null
  },
  "payment_details": [
    {
      "id": "uuid-pd-1",
      "type": "Sepa",
      "currencies": ["EUR"],
      "sepa": {
        "iban": "DE89370400440532013000",
        "bic": "COBADEFFXXX"
      }
    }
  ]
}
```

---

## Filter Recipients

### Filter by Type

**GET /api/v1/recipients/filter/type**

| Query Parameter | Type   | Required | Description                                           |
|----------------|--------|----------|-------------------------------------------------------|
| type           | string | Yes      | A payment-detail type from the 16-value enum above (e.g. Card, Sepa, Ach, Crypto, FasterPayment, Swift) |

All filter endpoints also accept `page_number`, `page_size` and `sort` (`name` | `usage`).

**Observed live in sandbox (2026-10-25):** all four filters return `{ "data": [...] }`. `type` is case-sensitive (`Sepa` works, `SEPA` -> `400 ErrorGeneral` "Details type was not provided or invalid"); omitting it -> `400 ErrorMissingField` "type is required". `filter/type` lags behind writes: a recipient created a moment earlier was missing from `filter/type` but already present in `filter/currency`, `filter/name` and `filter/catalog`; it appeared in `filter/type` within 15 s.

**Example:**

```
GET /api/v1/recipients/filter/type?type=Card
```

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "uuid-recipient-2",
      "personal_info": {
        "first_name": "Bob",
        "last_name": "Johnson",
        "is_business": false,
        "nick_name": null
      },
      "payment_details": [
        {
          "id": "uuid-pd-2",
          "type": "Card",
          "currencies": ["USD"],
          "card": {
            "card_id": "b7e2c1a4-3f5d-4e6a-9c8b-1d2e3f4a5b6c",
            "card_pan_last": "4242"
          }
        }
      ]
    }
  ]
}
```

### Filter by Currency

**GET /api/v1/recipients/filter/currency**

| Query Parameter | Type   | Required | Description                 |
|----------------|--------|----------|-----------------------------|
| currency       | string | Yes      | ISO 4217 currency code (EUR, USD, GBP) |

**Example:**

```
GET /api/v1/recipients/filter/currency?currency=EUR
```

### Filter by Name

**GET /api/v1/recipients/filter/name**

| Query Parameter | Type   | Required | Description                          |
|----------------|--------|----------|--------------------------------------|
| name           | string | Yes      | Partial name match (case-insensitive)|

**Example:**

```
GET /api/v1/recipients/filter/name?name=Alex
```

Returns all recipients whose first name, last name, company name, or nick name contains "Alex". Live sandbox check: `name=bo` found "Bob Johnson" (case-insensitive).

### Browse by Catalog Index

**GET /api/v1/recipients/filter/catalog?catalog_index=A** returns recipients whose full name begins with the given letter (page_size default 25, max 50; `sort` = `name` | `usage`).

### Record Usage

**POST /api/v1/recipients/{recipient_id}/usage** increments the usage counter that drives `sort=usage`. No body. It is **not** incremented automatically when a transfer is sent; call it when the user selects a recipient.

---

## Create Recipient

### POST /api/v2/recipients

Create a new recipient with personal information and payment details.

**Request Body — Card Recipient:**

```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "is_business": false,
  "type": "Card",
  "currencies": ["USD", "EUR"],
  "card": {
    "card_id": "b7e2c1a4-3f5d-4e6a-9c8b-1d2e3f4a5b6c",
    "card_pan_last": "1111"
  }
}
```

**Request Body — SEPA Recipient:**

```json
{
  "first_name": "Hans",
  "last_name": "Mueller",
  "is_business": false,
  "type": "Sepa",
  "currencies": ["EUR"],
  "sepa": {
    "iban": "DE89370400440532013000",
    "bic": "COBADEFFXXX"
  }
}
```

**Request Body — ACH Recipient:**

```json
{
  "first_name": "Bob",
  "last_name": "Johnson",
  "is_business": false,
  "type": "Ach",
  "currencies": ["USD"],
  "ach": {
    "routing_number": "021000021",
    "account_number": "1234567890",
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

**Request Body — Crypto Recipient:**

```json
{
  "first_name": "Alice",
  "last_name": "Nakamoto",
  "is_business": false,
  "type": "Crypto",
  "currencies": ["USD"],
  "crypto": {
    "recipient_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f7BABA",
    "network": "Base"
  }
}
```

**Request Body — Faster Payment Recipient:**

```json
{
  "first_name": "Charlie",
  "last_name": "Brown",
  "is_business": false,
  "type": "FasterPayment",
  "currencies": ["GBP"],
  "faster_payments": {
    "account_number": "12345678",
    "sort_code": "200000"
  }
}
```

**Request Body — SWIFT Recipient:**

```json
{
  "first_name": "Yuki",
  "last_name": "Tanaka",
  "is_business": false,
  "type": "Swift",
  "currencies": ["JPY"],
  "swift": {
    "iban": "JP1234567890123456789012",
    "bic": "BOTKJPJT",
    "bank_name": "Bank of Tokyo",
    "bank_country": "JP",
    "legal_address": {
      "line1": "1-2-3 Shibuya",
      "city": "Tokyo",
      "zip_code": "150-0002",
      "country": "JP"
    }
  }
}
```

**Common Request Fields:**

| Field        | Type     | Required | Description                                      |
|-------------|----------|----------|--------------------------------------------------|
| first_name   | string   | Yes*     | Recipient first name (personal)                  |
| last_name    | string   | Yes*     | Recipient last name (personal)                   |
| company_name | string   | Yes*     | Recipient company name (business)                |
| is_business  | boolean  | Yes      | `false` for personal, `true` for business        |
| nick_name    | string   | No       | Display name (max 127 chars); can replace personal info for Crypto type |
| type         | string   | Yes      | Payment type (one of the 16 enum values) |
| currencies   | string[] | Yes      | At least one currency code (e.g., `["EUR"]`)     |

*Either (`first_name` + `last_name`) or `company_name` is required.

Request object key matches the type: `card`, `sepa`, `ach`, `crypto`, `faster_payments` (request) / `faster_payment` (response), `swift`, `spei`, `pix`, `fps_hk`, `imps`, `instapay`, `bi_fast`, `nip`, `ipp`, `pse`, `cross_chain_crypto`. Exactly the object matching `type` must be present.

**Response (200 OK):**

```json
{
  "id": "uuid-new-recipient",
  "personal_info": {
    "first_name": "Jane",
    "last_name": "Smith",
    "is_business": false,
    "nick_name": null
  },
  "payment_details": [
    {
      "id": "uuid-pd-new",
      "type": "Card",
      "currencies": ["USD", "EUR"],
      "card": {
        "card_id": "b7e2c1a4-3f5d-4e6a-9c8b-1d2e3f4a5b6c",
        "card_pan_last": "1111"
      }
    }
  ]
}
```

---

## Add Payment Details

### POST /api/v1/recipients/{recipient_id}/payment_details

Add additional payment details to an existing recipient. A single recipient can have multiple payment methods.

**Path Parameters:**

| Parameter    | Type   | Description          |
|-------------|--------|----------------------|
| recipient_id | string | The recipient's UUID |

**Request Body:**

```json
{
  "type": "Sepa",
  "currencies": ["EUR"],
  "sepa": {
    "iban": "FR7630006000011234567890189",
    "bic": "BNPAFRPP"
  }
}
```

The body structure depends on the payment type. Include `type`, `currencies`, and the type-specific nested object (see [Payment Type Fields](#payment-type-fields) below).

**Response:** the new payment detail: `id`, `type`, `currencies`, type object (the guides previously showed only `{ "id": ... }`).

---

## Update Personal Info

### PUT /api/v1/recipients/{recipient_id}

Update the recipient's personal information (name, company name).

**Path Parameters:**

| Parameter    | Type   | Description          |
|-------------|--------|----------------------|
| recipient_id | string | The recipient's UUID |

**Request Body:**

```json
{
  "first_name": "Janet",
  "last_name": "Smith-Jones",
  "is_business": false,
  "nick_name": "Janet S"
}
```

**Request Fields:**

| Field        | Type    | Required | Description                          |
|-------------|---------|----------|--------------------------------------|
| first_name   | string  | Yes*     | Recipient first name (personal)      |
| last_name    | string  | Yes*     | Recipient last name (personal)       |
| company_name | string  | Yes*     | Company name (business)              |
| is_business  | boolean | Yes      | `false` for personal, `true` for business |
| nick_name    | string  | No       | Display name (max 127 chars)         |

*Either (`first_name` + `last_name`) or `company_name` is required.

**Response (200 OK):**

Returns the full recipient object with `id`, `personal_info`, and `payment_details` array.

---

## Update Recipient and Payment Details (v2)

### PUT /api/v2/recipients/{recipient_id}

Replaces personal info and one payment detail in one call. Body: same shape as `POST /api/v2/recipients` (`first_name`/`last_name` or `company_name`, `is_business`, `nick_name`, `type`, `currencies`, and exactly the matching type object; omitting it fails with `missing_for_type`). Returns the full recipient.

## Update Payment Details

### PUT /api/v1/recipients/{recipient_id}/payment_details/{payment_details_id}

Update specific payment details for a recipient.

**Path Parameters:**

| Parameter          | Type   | Description                    |
|-------------------|--------|--------------------------------|
| recipient_id       | string | The recipient's UUID           |
| payment_details_id | string | The payment details UUID       |

**Request Body (SEPA example):**

```json
{
  "type": "Sepa",
  "currencies": ["EUR"],
  "sepa": {
    "iban": "DE12345678901234567890",
    "bic": "DEUTDEDB"
  }
}
```

Include `type`, `currencies`, and the type-specific nested object.

**Response (200 OK):**

```json
{
  "id": "uuid-pd-1"
}
```

---

## Delete Payment Details

### DELETE /api/v1/recipients/{recipient_id}/payment_details/{payment_details_id}

Remove specific payment details from a recipient.

**Path Parameters:**

| Parameter          | Type   | Description                    |
|-------------------|--------|--------------------------------|
| recipient_id       | string | The recipient's UUID           |
| payment_details_id | string | The payment details UUID       |

**Response (204 No Content):**

No body returned (the API reference lists `200` with an empty object).

---

## Delete Recipient

### DELETE /api/v1/recipients/{recipient_id}

Delete a recipient and all associated payment details.

**Path Parameters:**

| Parameter    | Type   | Description          |
|-------------|--------|----------------------|
| recipient_id | string | The recipient's UUID |

**Response (204 No Content):**

No body returned (the API reference lists `200` with an empty object).

---

## Agent Companies

For a company whose users' accounts are operated by AI agents, recipients cannot be edited: every `PUT` and every `POST`/`PUT`/`DELETE` on `.../payment_details` returns `403 ErrorPermissionDenied`. Delete the recipient and create a new one. Your Wirex account manager sets this mode. `POST /api/v2/recipients` also accepts an optional `transaction_authorization`, verified only for agent companies in `Signature` mode.

---

## Payment Type Fields

Each payment type requires different fields when creating or updating payment details.

### Card

| Field         | Type   | Required | Description                              |
|--------------|--------|----------|------------------------------------------|
| card_id       | string | Yes      | Card token (UUID) from PCI tokenization; pass the same value as `external_card_id` on the card transfer |
| card_pan_last | string | Yes      | Last 4 digits of the card number         |

### Sepa

| Field | Type   | Required | Description                              |
|-------|--------|----------|------------------------------------------|
| iban  | string | Yes      | International Bank Account Number        |
| bic   | string | Yes      | Bank Identifier Code (SWIFT/BIC)         |

### Ach

| Field                        | Type   | Required | Description                      |
|------------------------------|--------|----------|----------------------------------|
| routing_number               | string | Yes      | ABA routing number (9 digits)    |
| account_number               | string | Yes      | Bank account number              |
| bank_name                    | string | No       | Name of the recipient's bank     |
| legal_address                | object | Yes      | Recipient's legal address        |
| legal_address.line1          | string | Yes      | Street address                   |
| legal_address.line2          | string | No       | Additional address info          |
| legal_address.city           | string | Yes      | City                             |
| legal_address.state          | string | No       | State/province code (required for US) |
| legal_address.zip_code       | string | Yes      | Postal/ZIP code                  |
| legal_address.country        | string | Yes      | ISO 3166-1 alpha-2 country code  |

### Crypto

| Field   | Type   | Required | Description                                        |
|---------|--------|----------|----------------------------------------------------|
| recipient_address | string | Yes | Blockchain address. Replaces the former `address`; both accepted and returned, must match if both supplied |
| network | string | Yes      | Network name (e.g. Base, Ethereum)                 |

`nick_name` can replace first/last/company name for Crypto recipients. `CrossChainCrypto` takes `address`, `network`, optional `tag` (destination tag/memo, e.g. XRP, Stellar); non-EVM address formats (Solana, Tron, Bitcoin) are supported.

### FasterPayment

| Field          | Type   | Required | Description                    |
|---------------|--------|----------|--------------------------------|
| account_number | string | Yes      | UK bank account number (8-18 digits) |
| sort_code      | string | Yes      | UK sort code (6 digits)        |

### Swift

| Field                        | Type   | Required | Description                      |
|------------------------------|--------|----------|----------------------------------|
| iban                         | string | Yes      | International Bank Account Number|
| bic                          | string | Yes      | SWIFT/BIC code                   |
| bank_name                    | string | Yes      | Recipient's bank name            |
| bank_country                 | string | Yes      | Bank country (ISO 3166-1 alpha-2)|
| legal_address                | object | Yes      | Recipient's legal address        |
| legal_address.line1          | string | Yes      | Street address                   |
| legal_address.line2          | string | No       | Additional address info          |
| legal_address.city           | string | Yes      | City                             |
| legal_address.zip_code       | string | Yes      | Postal/ZIP code                  |
| legal_address.country        | string | Yes      | ISO 3166-1 alpha-2 country code  |

### Other types (from the API reference, `POST /api/v2/recipients`)

| Type | Required fields |
|------|-----------------|
| Spei | `clabe`, `legal_address`, `national_id_number` (CURP or RFC) |
| Pix | `pix_key`, `pix_key_type` (CPF, CNPJ, EMAIL, PHONE, EVP), `national_id_number`, `recipient_name`, `legal_address` |
| FpsHk | `bank_code`, `fps_id`, `fps_id_type` (MOBILE, EMAIL, FPS_ID), `recipient_name`, `legal_address` |
| Imps | `account_number`, `ifsc_code`, `destination_country`, `recipient_name` (`bank_name` optional) |
| Instapay / Nip / BiFast | `account_number`, `bank_code`, `destination_country`, `recipient_name` (`bank_name` optional) |
| Ipp | `iban`, `destination_country`, `recipient_name` (`bank_name` optional) |
| Pse | `account_number`, `account_type` (SAVINGS, CHECKING), `bank_code`, `destination_country`, `document_number`, `document_type` (CC, NIT, CE, PASSPORT), `recipient_name` |

---

## Payment Type Summary Table

| Type           | Key Identifier           | Currency | Region         |
|----------------|--------------------------|----------|----------------|
| Card           | card_id (token)          | Any      | Global (Visa/MC)|
| Sepa           | iban + bic               | EUR      | SEPA zone      |
| Ach            | routing_number + account | USD      | US ACH         |
| Crypto         | recipient_address + network | Crypto | Global        |
| FasterPayment  | account_number + sort_code| GBP     | UK             |
| Swift          | iban + bic               | Various  | Global         |

---

## Recipient Webhook

**Endpoint:** `/v2/webhooks/recipients`

**POST {your_webhook_base_url}/v2/webhooks/recipients** is delivered when a recipient is created, updated, or deleted; the payload has the recipient shape (`id`, `personal_info`, `payment_details[]`).

See [wirex-baas-webhooks reference](../wirex-baas-webhooks/references/REFERENCE.md) for complete recipient webhook payloads.

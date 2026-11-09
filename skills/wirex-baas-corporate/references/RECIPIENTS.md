# Wirex BaaS Corporate — Recipients

Guides: [Recipients](https://docs.wirexapp.com/docs/corporate-recipients), [Creating a Recipient](https://docs.wirexapp.com/docs/corporate-recipients-create), [Managing Recipients](https://docs.wirexapp.com/docs/corporate-recipients-manage).

## Table of Contents

- [Model](#model)
- [Create a Recipient (v2)](#create-a-recipient-v2)
- [Payment Details by Type](#payment-details-by-type)
- [Field Formats](#field-formats)
- [Manage Recipients](#manage-recipients)
- [Errors](#errors)

---

## Model

A recipient is a stored payee: one identity (person or business) plus one or more payment details, one per rail. Recipients belong to the corporation, not to the employee who created them. Corridor and card transfers pay a recipient by id (`recipient_id` plus `recipient_payment_details_id`). Supported details types: `Crypto`, `Sepa`, `Swift`, `FasterPayment`, `Ach`, `Fedwire`, `Spei`, `Card`, `Pix`, `FpsHk`, `Imps`, `Instapay`, `BiFast`, `Nip`, `Ipp`, `Pse`.

Reads need no permission. Writes need `TransactionSu` or `TransactionManage`.

## Create a Recipient (v2)

Use `POST /api/v2/recipients`: it writes the identity and its first payment details in one call and performs a name check. The v1 pair (`POST /api/v1/recipients` for identity only, then `POST /api/v1/recipients/{recipientId}/payment_details`) is for adding a further rail to an existing recipient.

```json
{
  "first_name": "<first_name>",
  "last_name": "<last_name>",
  "is_business": false,
  "type": "Sepa",
  "currencies": ["EUR"],
  "sepa": {
    "iban": "<iban>",
    "bic": "<bic>"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `is_business` | Yes | `true` for a company |
| `first_name`, `last_name` | When `is_business` is `false` | |
| `company_name` | When `is_business` is `true` | `^[A-Za-z0-9&.,'’\-/() :+#]{2,100}$` |
| `nick_name` | No | At most 127 characters. For `type` `Crypto` a nickname replaces the name requirement entirely |
| `type` | Yes | One of the types above |
| `currencies` | Yes | Currencies the recipient accepts, e.g. `["EUR"]` |
| `<type object>` | Yes | The details object matching `type` |

Response: `id` (the `recipient_id`), `personal_info` (`first_name`, `last_name`, `is_business`, `nick_name`), `payment_details[]` (`id` is the `recipient_payment_details_id`, `type`, `currencies`, type object) and `name_check` (`name_matched`, `resolved_name` populated only on a partial match).

`name_check` is a warning, not a rejection: a recipient with `name_matched: false` is created and payable, and a rail rejects the mismatch later, after the debit. Surface it before the first payout. A duplicate set of details for the corporation fails with a `500`.

## Payment Details by Type

| `type` | Object | Required fields |
|---|---|---|
| `Crypto` | `crypto` | `address`, `network` |
| `Sepa` | `sepa` | `iban`, `bic` |
| `Swift` | `swift` | `iban`, `bic`, `bank_name`, `bank_country`, `legal_address` |
| `FasterPayment` | `faster_payments` | `account_number`, `sort_code` |
| `Ach` | `ach` | `routing_number`, `account_number`, `legal_address`; optional `bank_name` |
| `Fedwire` | `fedwire` | `routing_number`, `account_number`, `bank_name`, `legal_address` |
| `Spei` | `spei` | `clabe`, `recipient_id_number`, `legal_address` |
| `Card` | `card` | `card_id`, `card_pan_last` |
| `Pix` | `pix` | `pix_key`, `pix_key_type`, `recipient_name`, `recipient_id_number`, `legal_address` |
| `FpsHk` | `fps_hk` | `fps_id`, `fps_id_type`, `bank_code`, `recipient_name`, `legal_address` |
| `Imps` | `imps` | `account_number`, `ifsc_code`, `recipient_name`, `destination_country` |
| `Instapay` | `instapay` | `account_number`, `bank_code`, `recipient_name`, `destination_country` |
| `BiFast` | `bi_fast` | `account_number`, `bank_code`, `recipient_name`, `destination_country` |
| `Nip` | `nip` | `account_number`, `bank_code`, `recipient_name`, `destination_country` |
| `Ipp` | `ipp` | `iban`, `recipient_name`, `destination_country` |
| `Pse` | `pse` | `account_number`, `account_type`, `bank_code`, `recipient_name`, `document_type`, `document_number` |

> Note: docs differ. The recipients-create guide lists `bank_name`, `bank_country`, `legal_address` (Swift/Ach/FpsHk) and `recipient_id_number`, `legal_address` (Spei/Pix) as optional; the request schemas in the API reference mark them required, so send them. `legal_address` requires `line1`, `city`, `country`, `zip_code`.

The `FasterPayment` object is `faster_payments` on the way in and `faster_payment` on the way out. `card.card_id` is the tokenized card identifier that push-to-card takes as `external_card_id`.

`Fedwire` and `Ach` are separate details types and each corridor pays only its own type: an `Ach`-only recipient cannot be paid over `fedwire` (rejected at `initiate` with `Invalid recipient details`); add `Fedwire` details with `POST /api/v1/recipients/{recipientId}/payment_details`. `legal_address.line2` is not sent with a Fedwire payout. `first_name` / `last_name` must match `^[a-zA-Z][a-zA-Z\-' ]{0,49}$` (unaccented Latin; `José` is rejected). Send `legal_address.state` for a US address: without it the `ach` payout is refused after the debit and the debit is returned. `POST /api/v2/recipients` accepts an optional `transaction_authorization`, checked only for an agent company in `Signature` mode.

## Field Formats

| Field | Pattern | Applies to |
|---|---|---|
| `iban` | `^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$` | `sepa`, `swift` |
| `iban` (UAE) | `^AE\d{21}$` | `ipp` |
| `bic` | `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` | `sepa`, `swift` |
| `account_number` | `^\d{8,18}$` | `faster_payments`, `ach` |
| `account_number` | `^\d{9,18}$` | `imps` |
| `account_number` | `^\d{10}$` | `nip` |
| `sort_code` | `^\d{6}$` | `faster_payments` |
| `routing_number` | `^\d{9}$` | `ach` |
| `clabe` | `^\d{18}$` | `spei` |
| `recipient_name` | `^[\p{L}\p{N}\s.'\-]{1,100}$` | every corridor type; accepts Unicode (unlike employee names) |
| `pix_key_type` | `^(CPF\|CNPJ\|EMAIL\|PHONE\|EVP)$` | `pix` |
| `pix_key` CPF / CNPJ / PHONE | `^\d{11}$` / `^\d{14}$` / `^\+55\d{10,11}$`; EVP is UUID form | `pix` |
| `fps_id_type` | `^(FPS_ID\|MOBILE\|EMAIL)$` | `fps_hk` |
| `bank_code` | `^\d{3}$` | `fps_hk`, `nip`, `pse` |
| `bank_code` | `^([A-Z]{3,4}\|[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?)$` | `instapay` |
| `bank_code` | `^(\d{3}\|[A-Z]{4}ID[A-Z]{2})$` | `bi_fast` |
| `ifsc_code` | `^[A-Z]{4}0[A-Z0-9]{6}$` | `imps` |
| `account_type` | `^(SAVINGS\|CHECKING)$` | `pse` |
| `document_type` | `^(CC\|NIT\|CE\|PP)$` | `pse` |
| `document_number` | `^[A-Z0-9]{5,20}$` | `pse` |

Note: the PSE `document_type` regex accepts `PP`, while the field's own documentation names `PASSPORT`; send `PP`. IBAN and card-number checksums are not validated (format only): a bad check digit passes here and is rejected by the rail after acceptance.

## Manage Recipients

| Call | Notes |
|---|---|
| `GET /api/v1/recipients` | `page_number` (starts at `0`; `0` also returns the first page on bank accounts only), `page_size` (default 25), `sort` (`name` or `usage`); response `data[]` |
| `GET /api/v1/recipients/{recipientId}` | One recipient |
| `GET /api/v1/recipients/filter/name` | Required `name` substring |
| `GET /api/v1/recipients/filter/catalog` | Required `catalog_index`, a single letter `^[a-zA-Z]$` (first letter of the full name) |
| `GET /api/v1/recipients/filter/currency` | Required `currency` |
| `GET /api/v1/recipients/filter/type` | Required `type` |
| `PUT /api/v2/recipients/{recipientId}` | Same body as v2 create: identity plus `type` and details in one call |
| `PUT /api/v1/recipients/{recipientId}` | Identity only: `is_business`, `first_name`, `last_name`, `company_name`, `nick_name` |
| `POST /api/v1/recipients/{recipientId}/payment_details` | Add a rail: `type`, `currencies`, type object; returns the details with `id` |
| `PUT /api/v1/recipients/{recipientId}/payment_details/{paymentDetailsId}` | Replaces the details |
| `DELETE /api/v1/recipients/{recipientId}/payment_details/{paymentDetailsId}` | Removes one rail |
| `DELETE /api/v1/recipients/{recipientId}` | Invalidates every reference to it |
| `POST /api/v1/recipients/{recipientId}/usage` | Increments the usage counter that `sort=usage` orders by; never automatic |

The four filters take exactly one criterion each and cannot be combined; filter on the more selective one and narrow client-side. List responses omit `name_check` (it is on create and update responses). A webhook `POST {your_webhook_base_url}/v2/webhooks/recipients` fires on create or update.

## Errors

| HTTP | Reason | Detail | Fix |
|---|---|---|---|
| 400 | `ErrorMissingField` | `first_name`, `last_name` (person), `company_name` (business), `type`, `<type object>`, `catalog_index`, `currency`, `name` | Send the missing field |
| 400 | `ErrorInvalidField` | `company_name`, `nick_name` (max 127), `type`, `<type>.<field>`, `catalog_index`, `recipient_id` | Match the format tables |
| 403 | `ErrorPermissionDenied` | `User does not have required permissions` | Writes need `TransactionManage` or `TransactionSu` |
| 500 | `ErrorGeneral` | Lookup or details failure | Recipient or details id not found for this corporation, or duplicate details |

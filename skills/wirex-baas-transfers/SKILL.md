---
name: wirex-baas-transfers
description: "Wirex BaaS money transfers — send money to bank accounts and cards. Covers SEPA transfers (EUR, accounts for residents of 29 countries, explicit activation required), ACH transfers (USD, accounts for residents of 48 countries), v3 corridor transfers (16 payout rails), Push-to-Card payouts (PCI tokenization, OCT rails), and recipient management (16 payment-detail types, e.g. Card, Sepa, Ach, Crypto, FasterPayment, Swift). All transfers follow the estimate-then-execute pattern."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Money Transfers

This skill covers all money transfer capabilities in the Wirex Banking-as-a-Service platform: SEPA transfers (EUR), ACH transfers (USD), Push-to-Card via Visa/Mastercard OCT rails, and recipient management.

## Core Pattern: Estimate then Execute

All transfer types in Wirex BaaS follow the **estimate-then-execute** pattern:

1. **Estimate**: Submit transfer details to get a cost estimate. The response includes an `id` (estimation ID; `estimation_id` for card transfers) and an `expires_at` Unix timestamp, plus `estimated_amounts[]` (one entry per token, with `amount` (token amount debited, fee included), `precise_amount` in the token's smallest unit, `rate` and, where reported, `fee_amount` / `fee_precise_amount`).
2. **Execute**: Submit the transfer using the `estimation_id` from step 1 and the `token_address` to charge. Executing with an `estimation_id` uses the quoted amounts until `expires_at`. The SEPA and ACH guides now list `estimation_id` as required and single use (a retry with the same id is refused with `ErrorExpired`: estimate again); the API reference for `POST /api/v1/bank/transfer` still lists `amount` as an alternative, which is unverified live. If your company runs in `Signature` mode, the bank, corridor (`initiate`) and card transfer executes also carry `transaction_authorization` (see [Transaction Authorization](https://docs.wirexapp.com/docs/retail-transaction-authorization)); read the mode from `GET /api/v1/config` (`transactionAuthorizationMode`).

This two-step process ensures the user sees exact costs before committing to the transfer.

## SEPA Transfers (EUR)

SEPA (Single Euro Payments Area) enables EUR bank transfers. SEPA accounts are available to users residing in 29 countries: AT, BE, BG, CY, CZ, DK, EE, FI, FR, DE, GR, HU, IS, IE, IT, LV, LT, LU, MT, NL, NO, PL, PT, RO, SK, SI, ES, SE, GB (the `SepaAccount` capability is `NotAvailable` elsewhere).

### Prerequisites

- Account must have the **SepaAccount** capability enabled.
- `POST /api/v1/bank/transfer` always requires **SepaOut3rdParty**, even when the beneficiary is the user's own account.
- **SepaOut1stParty** applies only to the corridor flow, when the saved recipient's name matches the user's verified name.

### Flow

1. **Check capability**: Read the `SepaAccount` capability from `GET /api/v2/user` and branch on its status. SEPA accounts are **not** auto-provisioned: verification alone does not create an IBAN, activation is required.
2. **Activate the account**:
   - `ActivationNotStarted`: `POST /api/v1/bank/accounts` with `{ "account_type": "Sepa" }` (returns `{ "details_id": ... }`).
   - `ExternalProviderVerificationRequired`: wallet-linking path: `POST /api/v1/bank/accounts/init` (`{ "chain": "8453" }`, numeric chain ID as a string, returns `challenge` + `wallet_address`) → sign the challenge with the user's Primary wallet → `POST /api/v1/bank/accounts/complete` (`{ "chain", "signed_challenge" }`).
   - `ExternalProviderRegistrationPending`: wait, then re-check the capability.
   - `InProgress`: wait for the `/webhook/accounts/fiat` bank account webhook. `Active`: already provisioned.
   - The API reference now includes `ExternalProviderVerificationRequired` / `ExternalProviderRegistrationPending` in the `CapabilityStatus` enum and has reference pages for the `init` / `complete` endpoints.
   - The two paths are mutually exclusive; calling the wrong one returns `400`.
3. **Retrieve bank details**: Get the IBAN and BIC for the account.
   ```
   GET /api/v1/bank/accounts
   ```
4. **Estimate transfer**: Calculate fees and exchange rates.
   ```
   POST /api/v2/bank/transfer/estimate
   ```
5. **Execute transfer**: Send the payment.
   ```
   POST /api/v1/bank/transfer
   ```

See [references/BANKING.md](references/BANKING.md) for full request/response formats.

## ACH Transfers (USD)

> **WARNING:** ACH recipients require a `legal_address` field; SEPA does not.

ACH (Automated Clearing House) enables USD bank transfers. ACH accounts are available to users residing in 48 countries (see [references/BANKING.md](references/BANKING.md) for the list) and all US states and territories except Texas (TX) and New York (NY): users resident there cannot open a USD account. The USD account supports both ACH and Fedwire.

### Prerequisites

- Account must have the **AchAccount** capability enabled.
- `POST /api/v1/bank/transfer` always requires **AchOut3rdParty**, even when the beneficiary is the user's own account.
- **AchOut1stParty** applies only to the corridor flow, when the saved recipient's name matches the user's verified name.

### Flow

1. **Check capability**: Verify `AchAccount` in `GET /api/v2/user`. ACH is issued through Bridge and needs the extra verification level `XDDBridgeBase` on top of `SDD`: while the status is `NotFulfilled`, request it with `POST /api/v1/user/verification-token` (or `/verification-link`) and `"verification_level": "XDDBridgeBase"` (an omitted or unrecognised level silently falls back to `SDD`; the SDK helpers cannot pass it, call REST), then poll `GET /api/v2/user` while the status is `ExternalProviderRegistrationPending`. Activate only when it is `ActivationNotStarted`; otherwise the call fails with `ErrorInvalidStatus`.
2. **Activate ACH bank details** (status then becomes `InProgress` until the bank account webhook reports details): Create ACH bank account credentials for the user.
   ```
   POST /api/v1/bank/accounts
   Body: { "account_type": "Ach" }
   ```
3. **Retrieve bank details**: Get the account number and routing number.
   ```
   GET /api/v1/bank/accounts
   ```
4. **Estimate transfer**: Calculate fees and exchange rates.
   ```
   POST /api/v2/bank/transfer/estimate
   ```
5. **Execute transfer**: Send the payment.
   ```
   POST /api/v1/bank/transfer
   ```

See [references/BANKING.md](references/BANKING.md) for full request/response formats.

## Push-to-Card Transfers

Push-to-Card allows sending funds directly to a Visa or Mastercard debit card via OCT (Original Credit Transaction) rails.

### Prerequisites

- Account must have the **CardTransfer** capability enabled.

### Flow

1. **Tokenize card**: Submit the card details to the PCI-compliant endpoint to receive a token. **Requires user-scoped token** (not S2S).
   ```
   POST {pci_url}/b2b/cards/oct?user_id={user_id}
   Body: { card_number, cardholder_name, card_label, is_saved, is_third_party }
   ```
   The `user_id` is obtained from `GET /api/v2/user` response.
2. **Create recipient**: Register the card as a recipient.
   ```
   POST /api/v2/recipients
   Body: { type: "Card", card: { card_id: token, card_pan_last } }
   ```
3. **Estimate transfer**: Calculate fees and amounts.
   ```
   POST /api/v1/cards/transfer/estimate
   ```
4. **Execute transfer**: Send the payment.
   ```
   POST /api/v1/cards/transfer
   ```

**Card validations**: Visa/Mastercard only, not expired; the card number's Luhn digit is not checked (validate it in your form or use the PCI Compliant SDK). The tokenization response is `{ "value": "<uuid>" }` (card token, UUID); pass it as `card.card_id` on the recipient and as `external_card_id` in the estimate (`payment_details[].card.card_id`, not `payment_details[].id`; the docs no longer disagree). The PCI Compliant SDK (browser `@wirexapp/card-oct-web`, React Native, Flutter, iOS, Android) is the recommended way to tokenize; call the PCI endpoint directly only from a PCI DSS compliant environment.

See [references/PUSH-TO-CARD.md](references/PUSH-TO-CARD.md) for full details including PCI environment URLs.

## Corridor Transfers (v3)

One set of endpoints covers 16 payout rails, with the corridor as a path parameter:

```
POST /api/v3/bank/estimate/{corridor}   body: destination_amount, recipient_id, recipient_payment_details_id, [account_id], [source_tokens]
POST /api/v3/bank/initiate/{corridor}   body: estimation_id, source_token_address, [reference]
POST /api/v3/bank/confirm/{corridor}    body: transfer_id, actions[{type:"FundTransfer", data:{tx_hash}}]
```

Corridors: `sepa`, `ach`, `faster-payments` (bank-account corridors: `account_id` required, no confirm step); `pix`, `spei`, `fedwire`, `swift`, `cips`, `chats`, `fps_hk` (CPN: confirm step required); `imps`, `instapay`, `bi-fast`, `nip`, `ipp`, `pse` (offramp: no confirm). Branch on `required_actions` in the initiate response, not on the corridor name: when present, send the funds on-chain as described, then confirm. Each corridor needs its own `*Out3rdParty` capability `Active`. On `sepa` and `ach`, an individual recipient whose name equals the user's verified name is paid under `SepaOut1stParty` / `AchOut1stParty` instead (checked by the estimate); business recipients are always third party. `transfer_id` is also the id of the outbound activity (`GET /api/v2/activity/single/{transfer_id}`). In `Signature` mode `initiate` carries `transaction_authorization`. SEPA and ACH remain valid via the v2/v1 endpoints above. See [Corridor Transfers](https://docs.wirexapp.com/docs/retail-corridor-transfers) docs for field details.

## Recipients

Wirex BaaS supports 16 payment-detail types for recipients (`type` enum): Crypto, Sepa, FasterPayment, Ach, Swift, Spei, Card, Pix, FpsHk, Imps, Instapay, BiFast, Nip, Ipp, Pse, CrossChainCrypto. The main ones:

| Type            | Use Case                            | Key Fields                                |
|-----------------|-------------------------------------|-------------------------------------------|
| Card            | Push-to-Card transfers              | card_id (token, UUID), card_pan_last      |
| Sepa            | SEPA EUR bank transfers             | iban, bic                                 |
| Ach             | ACH USD bank transfers              | routing_number, account_number, legal_address (bank_name optional) |
| Crypto          | Crypto withdrawals                  | recipient_address (replaces `address`), network |
| FasterPayment   | UK Faster Payments (GBP)            | account_number, sort_code                 |
| Swift           | International wire transfers        | iban, bic, bank_country, bank_name, legal_address |

The others (Spei, Pix, FpsHk, Imps, Instapay, BiFast, Nip, Ipp, Pse, CrossChainCrypto) are listed in [references/RECIPIENTS.md](references/RECIPIENTS.md).

### Recipient CRUD Operations

| Operation                | Endpoint                                              |
|--------------------------|-------------------------------------------------------|
| List all recipients      | GET /api/v1/recipients                                |
| Get by ID                | GET /api/v1/recipients/{recipient_id}                 |
| Filter by type           | GET /api/v1/recipients/filter/type?type=Card          |
| Filter by currency/name/catalog | GET /api/v1/recipients/filter/currency, /name, /catalog |
| Record usage (for `sort=usage`) | POST /api/v1/recipients/{recipient_id}/usage    |
| Create recipient         | POST /api/v2/recipients                               |
| Update personal info     | PUT /api/v1/recipients/{recipient_id}                 |
| Update personal info + payment details | PUT /api/v2/recipients/{recipient_id}   |
| Delete recipient         | DELETE /api/v1/recipients/{recipient_id}              |

See [references/RECIPIENTS.md](references/RECIPIENTS.md) for full CRUD reference with all fields and payment type details.

## Activity Steps

All transfers progress through a series of activity steps. The exact steps vary by transfer type.

**SEPA/ACH:** Initiated → CryptoOut → Review → BankOut → Completed

**Push-to-Card:** Initiated → CryptoOut → Review → CardOut → Completed

### Step Descriptions

| Step      | Description                                      |
|-----------|--------------------------------------------------|
| Initiated | Transfer request received and validated          |
| CryptoOut | WUSD/WEUR burned from the user's wallet          |
| Review    | Compliance and risk checks in progress           |
| BankOut   | Funds sent via SEPA/ACH to recipient bank        |
| CardOut   | Funds sent via OCT to recipient card             |
| Completed | Transfer successfully delivered                  |

Activity `status` is `Pending`, `Completed` or `Failed` (there is no `Cancelled` status: a cancelled movement reads `Failed`). Other step types seen on the activity feed: `BankIn`, `CryptoIn`, `CardIn`, `Reversal`, `SyntheticWrap`, `SyntheticUnwrap`.

## Required Capabilities Summary

| Transfer Type         | Required Capabilities                   |
|----------------------|----------------------------------------|
| SEPA account setup    | SepaAccount                            |
| SEPA 1st-party send (corridor flow only) | SepaOut1stParty     |
| SEPA 3rd-party send (and every `POST /api/v1/bank/transfer`) | SepaOut3rdParty |
| ACH account setup     | AchAccount                             |
| ACH 1st-party send (corridor flow only) | AchOut1stParty       |
| ACH 3rd-party send (and every `POST /api/v1/bank/transfer`) | AchOut3rdParty |
| Push-to-Card          | CardTransfer                           |
| Corridor (v3) transfers | `<Corridor>Out3rdParty`, e.g. PixOut3rdParty |

## Webhooks

Transfer activity is reported via webhooks:

| Webhook Endpoint         | Purpose                              |
|--------------------------|--------------------------------------|
| /v2/webhooks/activities  | Transfer activity step updates       |
| /v2/webhooks/recipients  | Recipient creation/update events     |

See individual reference files for webhook payload examples.

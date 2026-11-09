# Wirex BaaS Corporate — Transfers, FX and Bank Accounts

Guides: [Bank Accounts](https://docs.wirexapp.com/docs/corporate-bank-accounts), [Activating Bank Account Details](https://docs.wirexapp.com/docs/corporate-account-activation), [Bank Transfers](https://docs.wirexapp.com/docs/corporate-bank-transfers), [Corridor Transfers](https://docs.wirexapp.com/docs/corporate-corridor-transfers), [Bulk Transfers](https://docs.wirexapp.com/docs/corporate-bulk-transfers), [Push to Card](https://docs.wirexapp.com/docs/corporate-push-to-card), [Card Transfer](https://docs.wirexapp.com/docs/corporate-card-transfer), [FX](https://docs.wirexapp.com/docs/corporate-fx).

## Table of Contents

- [Choosing a Payout Endpoint](#choosing-a-payout-endpoint)
- [Bank Account Activation](#bank-account-activation)
- [v1 / v2 Bank Transfers](#v1--v2-bank-transfers)
- [v3 Corridor Transfers](#v3-corridor-transfers)
- [Bulk Transfers](#bulk-transfers)
- [Push-to-Card](#push-to-card)
- [FX Swaps](#fx-swaps)
- [After Execution](#after-execution)
- [Errors](#errors)

---

## Choosing a Payout Endpoint

| You want to | Use |
|---|---|
| Pay a beneficiary described inline over SEPA, ACH or Faster Payments | v1 / v2 bank transfer |
| Pay a stored recipient over any rail (16 corridors) | v3 corridor transfer |
| Pay up to 50 on-chain crypto addresses at once | Bulk transfer |
| Pay an external Visa/Mastercard | Push-to-card (`/api/v1/cards/transfer`) |
| Convert one asset to another | FX |

Every transfer follows estimate then execute; in `Signature` mode (`GET /api/v1/config` `transactionAuthorizationMode`) the bank-transfer, corridor `initiate` and card-transfer executes also carry `transaction_authorization`, signed by the `employee_address` wallet over `I confirm that I'm executing <BankTransfer|CorridorTransferInitiate|CardTransfer> according to estimation <estimation_id> at <nonce>` (see [Transaction Authorization](https://docs.wirexapp.com/docs/corporate-transaction-authorization); a missing or non-matching one returns `401`). Money is debited from the corporation wallet (the chosen token); estimates quote one entry per token in `estimated_amounts[]` and expire at `expires_at` (Unix seconds). There is no cancel endpoint for any of them, and no status lookup by id: track outcomes in `GET /api/v1/activity/feed`.

## Bank Account Activation

A corporate bank account is a set of fiat details in the corporation's own name (IBAN, routing + account number, sort code + account number, CLABE). Deposits credit the corporation's on-chain balance.

Activation:

1. `GET /api/v1/corporations` — the `*Account` capability must be exactly `ActivationNotStarted` (`AchAccount`, `SpeiAccount`, `FasterPaymentsAccount`). Any other status gives `400` / `Capability does not need activation`. Read the capability, not `actions[]`: `ActivateAchDetails` appears while ACH can be activated, but no action exists for Faster Payments and its activation is accepted at `ActivationNotStarted`. ACH needs `XDDBridgeBase` on top of `SDD` (`AchAccount` reads `NotFulfilled` / `Verification requirements not fulfilled` until then; request it with `POST /api/v1/corporations/level-token`, which puts the whole corporation back into review until approved), then a Bridge profile (`external_providers[].bridge.status` `Pending` / `Active` / `Failed` ...); a `Failed` profile issues no numbers, contact Wirex. The same two levels gate `AchIn1stParty`, `AchIn3rdParty`, `AchOut1stParty`, `AchOut3rdParty` and `FedwireOut3rdParty`.
2. `POST /api/v1/bank/accounts` (`TransactionSu`, `AccountSu` or `AccountCreate`):

```json
{
  "account_type": "Ach"
}
```

Response `{"details_id": "<details_uuid>"}`. `account_type` values per the reference: `Sepa`, `Swift`, `FasterPayment`, `Ach`, `Spei` (list entries also use `Fedwire`; `FedNow` is not accepted on activation). Activating `Ach` also adds `Fedwire` and `FedNow` details to the same USD account (separate list entries, same account and routing numbers; `FedNow` is deposits only, no payout). Currency mapping: `Ach` and `Spei` USD, `FasterPayment` GBP, `Sepa` EUR. If an `Active` account in that currency exists the details attach to it (activating SPEI after ACH reuses the same USD account).

Note: docs differ on SEPA. The reference schema lists `Sepa` as a valid `account_type`, but the Activating Bank Account Details guide says `Sepa` is rejected (`400 ErrorInvalidField`, `expected: Ach|Spei|FasterPayment`) because SEPA is provisioned automatically on verification, and that `Swift` is refused by the handler (`Invalid value for account type`). The Corporation Profile guide lists an `ActivateSepaDetails` action pointing at this endpoint. Follow the corporation's `SepaAccount` status (the guide says to read the capability, not `actions[]`); if the call is rejected, wait for `SepaAccount` to turn `Active` and read the details.

3. `GET /api/v1/bank/accounts` (`TransactionSu`, `TransactionCreate` or `AccountView`) — poll until details are `Active`; there is no activation webhook. Item: `id` (**composite** `<accountId>:<detailsId>`, two UUIDs joined by `:`), `currency`, `status` (`Active`, `Pending`, `Blocked`, `Closed`), `account_holder`, `account_type` (`Sepa`, `Swift`, `FasterPayment`, `Ach`, `Fedwire`, `Spei`; v1 transfers take the whole `id`, v3 corridors only `<accountId>`), `created_at`, `details` (`iban`, `bic`, `account_number`, `sort_code`, `routing_number`, `clabe`, `mandatory_reference`).

If `details.mandatory_reference` is present the sender **must** put it in the transfer reference or the deposit cannot be matched; show it wherever account details are shown. Receiving capabilities differ by party (`SepaIn1stParty` vs `SepaIn3rdParty`, same for ACH and SPEI).

## v1 / v2 Bank Transfers

Rail (SEPA, ACH, Faster Payments) is implied by the details type behind `account_id`; there is no rail field. SPEI and SWIFT accounts are refused here (`400 ErrorNotSupported`, `Invalid account id`), and so are the `Fedwire` and `FedNow` entries of the USD account (estimate `400 ErrorNotSupported` `Invalid account id`, execute `400 ErrorInvalidField` `Invalid account type`): use corridor transfers.

1. Estimate: `POST /api/v1/bank/transfer/estimate` (no beneficiary) or `POST /api/v2/bank/transfer/estimate` (`recipient` and `recipient_account` **required on every rail**, format-checked at the estimate). Both work for SEPA, ACH and Faster Payments and return the same quote. Needs `TransactionSu` or `TransactionCreate`.

```json
{
  "account_id": "<accountId>:<detailsId>",
  "amount": 1000,
  "reference": "<comment>",
  "tokens": ["<token_address>"]
}
```

`reference` in the estimate body exists only in v2 and is ignored by the estimate (send it on execute); the v1 estimate takes `account_id`, `amount`, `tokens`. `amount` is what the beneficiary receives, truncated to 2 decimal places (below `0.01` is rejected).

Response: `id` (the estimation id), `amount` / `amount_precise` / `decimals`, `currency`, `expires_at` (20 minutes after the estimate), `estimated_amounts[]` (`amount` and `precise_amount` = the debit, fee included; `token_address`, `token_symbol`, `rate` = account currency per token, `rate_precise` / `rate_decimals`, `fee_amount` (omitted when `0`), `fee_precise_amount`, `fee_currency`; order not fixed). `tokens` defaults to every token in the company's list.

2. Execute: `POST /api/v1/bank/transfer`. Body: `account_id`, `token_address`, `recipient` (`first_name` + `last_name` for a person, or `company_name`), `recipient_account`, `reference`, and `estimation_id` (the estimate's `id`; the wallet is debited exactly the quoted `precise_amount`), plus `transaction_authorization` in `Signature` mode. An `amount` without `estimation_id` passes validation but is refused with `400 ErrorNotFound` `Entity not found` (no execution at the market rate); neither is `400 ErrorMissingField`. An estimate is single use and a refused execute spends it (`400 ErrorExpired` `Estimation expired or executed`: estimate again); there is no idempotency key, so check the activity feed after a timeout. `reference` is at most 255 characters (longer fails with `500`). Response `{"id": "<activity_id>"}`, the activity feed item id.

Beneficiary bank details by rail (`recipient_account`):

| Rail | Required fields |
|---|---|
| SEPA | `iban`, `bic` |
| ACH | `account_number`, `routing_number`, `legal_address`; `bank_name` optional |
| Faster Payments | `account_number`, `sort_code` |

Formats are the only check (IBAN and ABA check digits are not verified: a wrong IBAN is debited then returned): `iban` `^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$`, `bic` `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$`, `account_number` `^\d{8,18}$`, `routing_number` `^\d{9}$`, `sort_code` `^\d{6}$`. `legal_address` needs `line1`, `city`, `zip_code`, `country` (`line2` optional; `state` optional **except `US`**: `legal address.state is required for US`) and is triggered by the ACH field pair: any request with both `account_number` and `routing_number` needs it (`recipient account.legal address is required for ACH`, on a Faster Payments account too). An incomplete pair (IBAN without BIC, account number without sort code) fails with `Insufficient account details`.

Outbound capability checked: SEPA `SepaOut1stParty`, ACH `AchOut1stParty`, Faster Payments `FasterPaymentsOut3rdParty`. A corporation with only `SepaOut3rdParty` cannot use this endpoint for SEPA.

Settlement: Faster Payments near-instant, SEPA same or next business day, ACH one to three business days.

## v3 Corridor Transfers

Three calls; the third only for CPN corridors. All need `TransactionSu` or `TransactionCreate` and the corridor's capability `Active`.

| `{corridor}` | Rail | Currency | Capability | Provider |
|---|---|---|---|---|
| `sepa` | SEPA | EUR | `SepaOut3rdParty` | Bank |
| `ach` | ACH | USD | `AchOut3rdParty` | Bank |
| `faster-payments` | Faster Payments | GBP | `FasterPaymentsOut3rdParty` | Bank |
| `pix` | PIX | BRL | `PixOut3rdParty` | CPN |
| `spei` | SPEI | MXN | `SpeiOut3rdParty` | CPN |
| `fedwire` | FEDWIRE | USD | `FedwireOut3rdParty` | Bank |
| `swift` | WIRE | USD | `SwiftOut3rdParty` | CPN |
| `cips` | CIPS | CNY | `CipsOut3rdParty` | CPN |
| `chats` | CHATS | HKD | `ChatsOut3rdParty` | CPN |
| `fps_hk` | FPS | HKD | `FpsHkOut3rdParty` | CPN |
| `imps` | IMPS/NEFT/UPI | INR | `ImpsOut3rdParty` | Triple-A |
| `instapay` | InstaPay/PESONet | PHP | `InstapayOut3rdParty` | Triple-A |
| `bi-fast` | BI-FAST | IDR | `BiFastOut3rdParty` | Triple-A |
| `nip` | NIP | NGN | `NipOut3rdParty` | Triple-A |
| `ipp` | IPP | AED | `IppOut3rdParty` | Triple-A |
| `pse` | PSE | COP | `PseOut3rdParty` | Triple-A |

Corridor names are spelled inconsistently: `faster-payments` and `bi-fast` hyphenated, `fps_hk` underscore; case is ignored. Unknown values give `400` / `Unsupported corridor: <value>`. No endpoint lists corridors at runtime.

Provider rules: Bank corridors (`sepa`, `ach`, `faster-payments`, `fedwire`) require `account_id`, Wirex debits the wallet during `initiate`, and there is no confirm step. CPN corridors (`pix`, `spei`, `swift`, `cips`, `chats`, `fps_hk`) need no `account_id`, the corporation sends the funding transfer, and the confirm step is required. Triple-A corridors need neither (Wirex debits during `initiate`). Prerequisite capabilities: `sepa` `SepaAccount`; `ach` and `fedwire` `AchAccount` (`fedwire` pays from the same USD account as `ach`, and pays only `Fedwire` recipient details while `ach` pays only `Ach` details); `faster-payments` `FasterPaymentsAccount`; `spei` `SpeiAccount`; CPN `CpnExternalProfile`; Triple-A `TripleAExternalProfile` (the two profiles are provisioned by Wirex with no activation endpoint). FedNow is deposits only: there is no FedNow payout corridor.

1. `POST /api/v3/bank/estimate/{corridor}`:

```json
{
  "recipient_id": "<recipient_uuid>",
  "recipient_payment_details_id": "<payment_details_uuid>",
  "destination_amount": 100,
  "destination_currency": "<currency>",
  "account_id": "<account_uuid>",
  "source_tokens": ["<token_address>"]
}
```

`destination_currency` defaults to the corridor currency, the only value accepted (case-sensitive: `EUR` passes for `sepa`, `eur` is rejected); `account_id` only for `sepa`, `ach`, `faster-payments`, `fedwire` and it is a **plain UUID**, not the composite id (`Invalid account ID format`; only the format is checked). `destination_amount` is truncated to 2 decimal places (below `0.01` is rejected). For bank corridors `recipient_payment_details_id` is only format-checked: the payout goes to the recipient's details of the corridor's type, so an estimate for a recipient without that type still quotes and `initiate` then fails with `Invalid recipient details`. Response `id`, `amount` / `amount_precise` / `decimals`, `currency`, `expires_at` (bank corridors: 20 minutes), `estimated_amounts[]` (`amount` / `precise_amount` = the debit, fee included, exactly what `initiate` debits; `rate`, `rate_precise` / `rate_decimals`, `fee_amount`, `fee_precise_amount`, `fee_currency`; order not fixed).

2. `POST /api/v3/bank/initiate/{corridor}` with `estimation_id`, `source_token_address` (one quoted), optional `reference` (bank corridors: at most 255 characters), `transaction_authorization` in `Signature` mode. Response `transfer_id`, `status` (`processing` for bank and Triple-A corridors; CPN: `pending`, `processing`, `completed` or `failed`), `required_actions[]` (the key is omitted, not empty, when there is none). No `required_actions` means the transfer is already moving; confirm on a bank or Triple-A corridor returns `400` `Confirm step is supported only for CPN corridors`. For bank corridors the wallet is debited exactly the quoted amount, the estimate is single use (a refused `initiate` spends it: `ErrorExpired`, estimate again), the payout runs on the corridor of the estimate whatever the `initiate` path says (use the same `{corridor}` in both calls), and there is no idempotency key.

3. CPN only: when `required_actions` contains a `FundTransfer` (`data`: `chain_id`, `token_address`, `destination_address`, `amount` smallest unit string, `expires_at`), send that amount of that token to that address on that chain before `expires_at`, then `POST /api/v3/bank/confirm/{corridor}`:

```json
{
  "transfer_id": "<transfer_uuid>",
  "actions": [
    {
      "type": "FundTransfer",
      "data": {
        "tx_hash": "<funding_tx_hash>"
      }
    }
  ]
}
```

Response `transfer_id`, `status` (e.g. `processing`), `tx_hash`. Not confirming before `expires_at` abandons the transfer; a funded transfer cannot be recalled via the API.

## Bulk Transfers

Crypto destinations only; 1-50 recipients; one `currency` per batch. Two steps, and the API call alone moves no money.

1. `POST /api/v1/bulk/transfer` (`TransactionSu` or `TransactionCreate`) validates, **reserves** the batch total and approves it on-chain:

```json
{
  "recipients": [
    {
      "type": "Crypto",
      "currency": "WEUR",
      "amount": "1.50",
      "crypto": {
        "address": "<evm_address>",
        "network": "Base"
      }
    }
  ]
}
```

`type` must be `Crypto`; `currency` is `WUSD` or `WEUR`; `amount` is a JSON number or decimal string, **truncated to two decimals** (below `0.01` becomes zero and still returns `200`); `crypto.network` must be non-empty but the batch always runs on the corporation token's chain; `crypto.address` is only checked for presence, so validate `^0x[0-9a-fA-F]{40}$` yourself (a bad address stays reserved 24 hours).

Response: `transaction_id` (the **corporation id**, same on every batch), `operation_id` (unique per batch; key your records on it), `crypto_transfers[]` (`address`, `precise_amount`, `token_address`). Check every `precise_amount` before step 2.

The reservation lasts 24 hours; an unexecuted batch keeps its total unavailable (a second approval can fail with `ErrorInsufficientFunds`). No cancel endpoint.

2. On-chain: the corporation wallet sends a UserOperation calling `FundsManagement.executeOutgoingBatchTransaction` (resolve `FundsManagement` with `contractByName("FundsManagement")` from the ContractRegistry). Arguments: `transactionId` and `operationId` as `bytes16` (the UUIDs with dashes removed), `tokenAddress` from `crypto_transfers[0].token_address`, `recipients` and `amounts` (`precise_amount` as `uint256`) in response order. The signer must be an employee whose on-chain role is `Su`, `TransactionSu` or `TransactionCreate`; gas is sponsored by the paymaster. Wirex never executes the batch. Retry `Batch transaction not found` every few seconds right after step 1 (the approval needs a few seconds to land); `Total amount mismatch` means `amounts` differ from the approved total. A batch executes once.
3. Confirm in `GET /api/v1/activity/feed`: one `Crypto` / `Outbound` / `Completed` item per recipient; match by `operations[].hash` (the step 2 hash) and `destination.wallet.address`. There is no `Failed` item and no bulk status endpoint or webhook.

## Push-to-Card

Credits an external Visa or Mastercard over OCT rails. Requires `CardSu` (not `TransactionCreate`) and the `CardTransfer` capability `Active`.

1. Tokenize the destination card in the PCI environment (separate host; the request carries the corporation token as `Authorization: Bearer <token>`, and the card is bound to that corporation): `POST {pci_base_url}/b2b/cards/oct?user_id=<corporation_address>`, body `card_number`, `cardholder_name` (uppercase as printed), `is_saved` (boolean); response `{"value": "<card_token>"}`. `user_id` is the **corporation wallet address**, not a user id. PCI hosts: `https://wx-acquiring-card-manager-uat.wirexapp.com` (sandbox) and `https://wx-acquiring-card-manager.wirexapp.com` (production). Errors: `401` empty body (no or invalid corporation token), `404` `CompanyProfileNotFoundError` (KYB not approved yet), `500` `0000` (usually a non-corporation token such as the partner token).
2. Store it as a recipient payment detail of type `Card` (`card.card_id`, `card.card_pan_last`) with `POST /api/v2/recipients`. The token is `card.card_id`; pass it as `external_card_id`.
3. `POST /api/v1/cards/transfer/estimate`:

```json
{
  "external_card_id": "<card_token>",
  "amount": 250,
  "currency": "USD",
  "tokens": ["<token_address>"]
}
```

`amount` > 0; `tokens` at least one (**unified tokens like WUSD/WEUR accepted directly**); `currency` silently defaults to `EUR`. Response `estimation_id`, `amount`, `currency`, `fee_amount`, `expires_at`, `estimated_amounts[]`.

4. `POST /api/v1/cards/transfer` with `estimation_id` and `token_address` (one of the quoted). Response `{"id": "<activity_id>"}`. No reversal; a completed OCT is final.

## FX Swaps

Needs `TransactionSu` and the `StableExchange` capability `Active` (both FX endpoints check `StableExchange`, not `FxTransfer`). Wirex does not debit the wallet; nothing moves until you pay the deposit address on-chain.

1. `POST /api/v1/fx/estimate`: `source_asset_address`, `destination_asset_address` (both **regular** tokens from `GET /api/v1/config/tokens`), **exactly one** of `source_asset_amount` / `destination_asset_amount` (positive decimal strings), optional `correlation_id` (UUID, not echoed back). Response: `estimation_id`, `deposit_address`, `source_asset_amount`, `destination_asset_amount`, `trade_rate`, `expiration_time` (ISO 8601), plus the exact values `source_asset_amount_precise` / `source_asset_decimals`, `destination_asset_amount_precise` / `destination_asset_decimals`, `trade_rate_precise` / `rate_decimals` (the last two omitted when the rate does not convert).
2. Send exactly `source_asset_amount_precise` base units of the regular `source_asset_address` token from the corporation wallet to `deposit_address` before `expiration_time` and keep the tx hash. A corporation holding unified tokens must unwrap and send the underlying token in the same operation; depositing a unified token is not matched.
3. `POST /api/v1/fx` with `estimation_id` and `payment_transaction_hash` (`0x`-prefixed, 66 characters). Response `{"trade_id": "<trade_uuid>"}`.

Settlement appears in the activity feed and via `/v2/webhooks/balances`; there is no FX webhook and no trade lookup. Re-estimate rather than retrying an expired `estimation_id`.

## After Execution

1. The chosen token is debited from the corporation wallet (directly, or via the funding transfer for CPN corridors and FX).
2. The payout is submitted on its rail.
3. The item appears in `GET /api/v1/activity/feed` under the returned `id`.
4. Progress arrives at `POST {your_webhook_base_url}/v2/webhooks/activities` and `/v2/webhooks/balances`. Webhooks are not retried; poll the feed.

See [WEBHOOKS-AND-ACTIVITY.md](WEBHOOKS-AND-ACTIVITY.md) and [RECIPIENTS.md](RECIPIENTS.md).

## Errors

| HTTP | Reason | Message | Fix |
|---|---|---|---|
| 400 | `ErrorGeneral` | `Capability is not active` | Required capability not `Active` (FX: `StableExchange`; card transfer: `CardTransfer`; corridors: the corridor capability or its provider profile) |
| 400 | `ErrorGeneral` | `Capability does not need activation` | Capability not `ActivationNotStarted` |
| 400 | `ErrorInvalidField` | `Invalid format for account id` | v1 wants the composite id; v3 wants a plain UUID |
| 400 | `ErrorNotFound` / `ErrorNotSupported` | `Invalid account id` | Not owned, or rail not SEPA/ACH/Faster Payments |
| 400 | `ErrorMissingField` | `amount is required when estimation id missing` | Send `estimation_id` |
| 400 | `ErrorNotFound` | `Entity not found` | Bank-transfer execute sent `amount` without `estimation_id` |
| 400 | `ErrorExpired` | `Estimation expired or executed` | The estimate is single use, even after a refused execute: estimate again |
| 400 | `ErrorMissingField` | `recipient account.legal address is required for ACH` | Add `legal_address` |
| 400 | keyed | `Recipient not found or does not belong to you` | Recipient deleted or foreign |
| 400 | keyed | `Invalid recipient Payment Details ID` | Use `payment_details[].id` |
| 400 | `ErrorInvalidField` | `recipients exceeds maximum allowed` (`max: 50`), `Only crypto recipients are supported`, `All recipients must use the same currency` (`currency_mismatch`), `Recipient details are invalid` | Fix the bulk batch; errors name the entry as `recipients[i]` |
| 400 | `ErrorNotSupported` | `Invalid currency` (`unsupported_for_chain`) | No active token with that symbol on the chain |
| 400 | `ErrorInsufficientFunds` | `Insufficient funds` | Total exceeds the available (unreserved) balance |
| 500 | `ErrorGeneral` | `Failed to estimate card transfer`, `Failed to execute card transfer`, `Failed to estimate FX swap`, `Failed to execute FX swap` | Provider rejected, expired, already executed or lacking balance; re-estimate |
| 500 | `ErrorGeneral` | `Failed to read tokens` | Token catalogue unavailable; retry |
| 500 | `ErrorGeneral` | `Failed to request bulk transfer approval` | Read `GET /api/v1/wallets` before retrying; a reserved total is released after 24 hours |

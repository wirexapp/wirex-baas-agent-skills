# Wirex BaaS External Authorization Reference

Sources: https://docs.wirexapp.com/docs/retail-extauth-api, retail-extauth-risk-assessment, retail-extauth-cards, retail-extauth-creating-user-2, retail-extauth-overview.

## Authorize request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_type` | string | Yes | `POS`, `ATM`, `ePOS`, `MoneyTransfer` |
| `user_id` | UUID | Yes | User identifier |
| `transaction_id` | UUID | Yes | Card transaction identifier |
| `operation_type` | string | Yes | `Debit` (purchase/withdrawal) or `Credit` (refund) |
| `card_id` | UUID | Yes | Card identifier |
| `currency` | string | Yes | ISO 4217 currency code |
| `amount` | decimal | Yes | Transaction amount |
| `unique_operation_id` | UUID | Yes | Unique operation identifier (idempotency key) |
| `correlation_id` | UUID | No | Tracing identifier; treat as absent when missing |
| `preferred_payment_currency` | string | Yes | ISO 4217 code Wirex prefers to settle in; empty string when no preference |
| `rates_by_assets` | array | Yes | Currency pairs: `ticker` (`BASE/QUOTE`), `buy`, `sell` |
| `is_mandatory` | boolean | Yes | If `true`, processed regardless of your response |
| `related_external_operation_status` | string | Yes | `None` (first in chain), `Rejected` (previous rejected by partner), `Approved` (previous approved by partner) |
| `transaction_reason` | string | Yes | See below |
| `mcc` | string | No | 4-digit merchant category code |

Note: the sample request body in the docs omits `preferred_payment_currency` although the field table marks it required.

## transaction_reason values

| Value | Description |
|-------|-------------|
| `Authorization` | Authorization operation (single or incremental) |
| `Clearing` | Capture operation (direct, single, or multiple) |
| `Refund` | Refund (partial or full) |
| `Reversal` | Cancel authorizations/clearings (partial or full) |
| `OriginalCredit` | Credit operation |
| `Representment` | Cancel refunds/chargebacks |
| `MoneySend` | Credit operation |
| `DelayAuthorization` | Fuel dispenser scenarios or chargebacks |

## Authorize response fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_id` | UUID | Yes | Echo back |
| `is_allowed` | boolean | Yes | `true` approve, `false` decline |
| `decline_reason` | string | No | `InsufficientFunds` or `GeneralError` |

## Settle request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_type` | string | Yes | Channel type |
| `user_id` | UUID | Yes | User identifier |
| `transaction_id` | UUID | Yes | Card transaction identifier |
| `operation_type` | string | Yes | `Debit` or `Credit` |
| `card_id` | UUID | Yes | Card identifier |
| `currency` | string | Yes | Original transaction currency |
| `amount` | decimal | Yes | Original transaction amount |
| `unique_operation_id` | UUID | Yes | Unique operation identifier |
| `correlation_id` | UUID | No | Tracing identifier; treat as absent when missing |
| `settlement_currency` | string | Yes | Settlement currency |
| `settlement_amount` | decimal | Yes | Settlement amount |
| `settlement_decision` | int | Yes | `0` Approve, `1` Reject |
| `reject_reason` | string | No | Reason when rejecting |

## Settle response fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `is_processed` | boolean | Yes | Whether settlement was processed |
| `error_reason` | string | No | `InsufficientFunds` or `GeneralError` |
| `transaction_id` | UUID | Yes | Related transaction ID |

## Mandatory vs non-mandatory

| `is_mandatory` | Authorization behavior | Settlement behavior |
|----------------|------------------------|---------------------|
| `false` | Requires `is_allowed: true` | Normal processing |
| `true` | Processed regardless of response | Processed regardless of response |

Mandatory transactions include refunds, chargebacks and network corrections.

## Card webhook (activity)

`POST {your_webhook_base_url}/v2/webhooks/activities`

The payload is the v2 activity; the same activity is delivered again each time it changes.

| Field | Description |
|-------|-------------|
| `type` | `CardTransaction` |
| `user_address` | The cardholder's EOA |
| `source.card.id` | The card used |
| `status` | `Pending`, `Completed`, or `Failed`. A purchase refunded or reversed in full reads `Failed` |
| `operations[].operation_id` | One ledger movement; the `unique_operation_id` of the authorization request |
| `operations[].operation_reason` | `Authorization`, `Clearing`, `Refund`, `Reversal`, ... |
| `operations[].transaction_amount` | The movement in the transaction currency; negative debits the user |
| `id`, `created_at` | Identifier and timestamp |

Book each `Completed` operation once, keyed by `operation_id`.

## Screening request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `direction` | string | Yes | `Inbound` (screened as deposit) or `Outbound` (screened as transfer) |
| `user_address` | string | Yes | Address of your user (not the counterparty) |
| `amount` | number | Yes | In the transaction's own asset; > 0 |
| `asset_symbol` | string | Yes | e.g. `USDC` |
| `chain_name` | string | Yes | Case-sensitive network name (list below) |
| `transaction_hash` | string | Yes | On-chain hash |
| `sender_address` | string | Yes | Address funds moved from |
| `recipient_address` | string | Yes | Address funds moved to |

Address pattern shared by `user_address`, `sender_address`, `recipient_address`:

```
^(0x[a-fA-F0-9]{40}|C[A-Za-z2-7]{55}|G[A-Za-z2-7]{55}|T[1-9A-HJ-NP-Za-km-z]{33}|r[1-9A-HJ-NP-Za-km-z]{24,34})$
```

| Prefix | Chain family | Format |
|--------|--------------|--------|
| `0x` | EVM | 40 hex characters |
| `C` / `G` | Stellar | 55 base32 characters |
| `T` | Tron | 33 base58 characters |
| `r` | XRPL | 24-34 base58 characters |

## Supported networks (chain_name)

`ArbitrumNative`, `Arbitrum`, `CChain`, `CChainBridged`, `CChainBridgedBitcoin`, `CChainBridgedBinance`, `WrappedCChain`, `WrappedCChainBridgedEthereum`, `BinanceSmartChain`, `Bitcoin`, `Ethereum`, `EthereumBRZ`, `WrappedEthereum`, `Polygon`, `PolygonBRZ`, `PolygonBridgedBinance`, `WrappedPolygon`, `Cosmos`, `Tron`, `WrappedTron`, `Waves`, `Stellar`, `Ripple`, `Solana`, `Base`.

Anything else is refused with `chain_name: {value}` and `issue: invalid_value`.

## Screening validation errors

All `400`. Missing fields return `ErrorMissingField`; malformed ones `ErrorInvalidField`.

| Error description | `field` | `issue` | Resolution |
|-------------------|---------|---------|------------|
| `direction must be Inbound or Outbound` | `direction` | `invalid_value` | Exact casing |
| `user address must be a valid address` | `user_address` | `invalid_address` | Match pattern |
| `Invalid value for amount` | `amount` | `invalid_value` | Amount > 0 |
| `asset symbol is required` | `asset_symbol` | `missing` | Send symbol |
| `chain_name must be a supported network` | `chain_name` | `invalid_value` | Use supported list |
| `transaction hash is required` | `transaction_hash` | `missing` | Send hash |
| `sender address must be a valid address` | `sender_address` | `invalid_address` | Match pattern |
| `recipient address must be a valid address` | `recipient_address` | `invalid_address` | Match pattern |

`500` after validation: the transaction did not reach screening; retry with backoff.

## Limitations of the screening endpoint

- Response carries no verdict; flagged outcomes go through compliance channels.
- No deduplication: same `transaction_hash` twice creates two reports.
- No batch endpoint.
- `chain_name` accepts Bitcoin, Cosmos, Solana, Waves, but the address pattern only matches EVM, Stellar, Tron, XRPL: raise this with Wirex rather than using placeholder addresses.
- `chain_name` casing is its own vocabulary, not the token catalogue or `X-Chain-Id` names.
- Zero-value transactions are refused.

## FAQ (from docs)

- Master Account insufficient funds on an approved non-mandatory transaction: declined.
- Refunds: mandatory Credit transactions; Master Account credited, you receive a webhook to credit the user.
- History: standard Activity History endpoints.

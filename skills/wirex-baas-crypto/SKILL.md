---
name: wirex-baas-crypto
description: "Wirex BaaS crypto asset management — check balances, deposit crypto, withdraw tokens. Covers wallet balance queries (GET /api/v1/wallet), unified balance model (WUSD/WEUR on Base), multi-chain deposits via Rhino.fi (9 chains: Ethereum, Arbitrum, Polygon, Optimism, BSC, Base, Kaia, TRON, Solana), ERC20 on-chain withdrawals (two-phase delay pattern), and smart contract ABI reference."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Crypto Asset Management

This skill covers crypto asset management within the Wirex Banking-as-a-Service platform: the unified balance model, wallet queries, multi-chain deposit addresses, ERC20 withdrawals, token addresses, and smart contract ABIs.

## Unified Balance Model

Wirex BaaS uses a **unified balance model** where all user funds are represented as wrapped stablecoins on the **Base chain**:

| Token  | Represents | Chain | Decimals | Ratio |
|--------|-----------|-------|----------|-------|
| WUSD   | USD       | Base  | 18       | 1:1   |
| WEUR   | EUR       | Base  | 18       | 1:1   |

All balances across the platform (card spending, bank transfers, crypto deposits) are unified into these two tokens. There is no need to manage multiple token balances or perform manual conversions.

> Note: docs differ. The unified-balance guide (`retail-unified-balance`) lists only WUSD and WEUR; the crypto-assets overview (`retail-crypto-assets`) also mentions WGBP.

### Token Wrapping

- **Deposits**: When a user deposits USDC, USDT, or EURC, the tokens are bridged to Base and wrapped into WUSD or WEUR at a 1:1 ratio. The wrapping process mints the corresponding W-token.
- **Withdrawals**: When a user withdraws, WUSD unwraps to USDC on Base, and WEUR unwraps to EURC on Base. The process incorporates delay verification before execution to enhance security.

### Direct Credit Minting

WUSD/WEUR can also be minted directly (without a deposit) in the following scenarios:

- **Card refunds**: Merchant refunds credit WUSD/WEUR back to the wallet.
- **Bank transfers**: Incoming SEPA or ACH transfers mint WUSD/WEUR.
- **Peer-to-peer (P2P)**: Internal transfers between Wirex users.
- **Rewards**: Cashback, referral bonuses, and promotional credits.

## Wallet Queries

### GET /api/v1/wallet

Retrieve the user's wallet with its balances. Optional query parameter: `wallet_address`. (`GET /api/v1/wallets` returns all user wallets with balances.)

**Headers:**

| Header          | Value                          |
|-----------------|--------------------------------|
| Authorization   | Bearer `{access_token}`        |
| Content-Type    | application/json               |
| X-User-Wallet   | `{user_eoa_address}`           |
| X-Chain-Id      | `{chain_id}`                   |

**Response:**

```json
{
  "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "wallet_name": "Main Wallet",
  "wallet_status": "Confirmed",
  "wallet_type": "Primary",
  "balances": [
    {
      "token_symbol": "WUSD",
      "token_address": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
      "balance": 1.0,
      "reference_balance": 1.0,
      "reference_currency": "USD"
    }
  ]
}
```

- `balance` is a number in token units (not raw wei).
- `reference_balance` is the balance in the reference currency; `reference_currency` (ISO 4217) is determined by the user's residence country.
- `wallet_status`: `Unknown`, `Confirmed`, `Rejected`. `wallet_type`: `Primary`, `Secondary`, `Global`, `Card`. `chain_family` is set only for non-EVM wallets (e.g. `solana`).
- `GET /api/v3/wallet` (and `/api/v3/wallets`) read the wallet on whichever chain it lives on, regardless of the request's `X-Chain-Id`. They add `chain_id` and precise fields per balance: `balance_precise`, `decimals`, `reference_balance_precise`, `reference_decimals` (the reference pair is absent when no rate is available).

## Global Deposit Addresses (Multi-Chain via Rhino.fi)

Wirex uses **Rhino.fi** to generate deposit addresses across 9 supported chains (per the Global Deposit Addresses guide; the SDK guide's deposit-network list also names Stellar, and Arc as a possible destination chain). Addresses are created via the Wirex SDK (`sdk.crypto.smartDepositAddress.initializeSmartDepositAddresses()`, requires `rhinoApiKey` in `createSDK`) or the Rhino.fi SDK directly (API key provided by Wirex). Funds sent to them are bridged to Base and wrapped into WUSD/WEUR.

### Supported Chains and Tokens

| Chain     | Chain ID | USDT | USDC | EURC | Typical bridge time (guide timing table) | Address Type     |
|-----------|----------|------|------|------|---------------------|------------------|
| Ethereum  | 1        | Yes  | Yes  | No   | 3-5 minutes         | Shared EVM       |
| Arbitrum  | 42161    | Yes  | Yes  | No   | 1-3 minutes         | Shared EVM       |
| Polygon   | 137      | Yes  | Yes  | No   | 1-3 minutes         | Shared EVM       |
| Optimism  | 10       | Yes  | Yes  | No   | 1-3 minutes         | Shared EVM       |
| BSC       | 56       | Yes  | Yes  | No   | 1-3 minutes         | Shared EVM       |
| Base      | 8453     | Yes  | Yes  | Yes  | not stated          | Shared EVM       |
| Kaia      | 8217     | Yes  | No   | No   | not stated          | Shared EVM       |
| TRON      | n/a      | Yes  | No   | No   | 1-3 minutes         | Separate address |
| Solana    | n/a      | Yes  | Yes  | No   | 1-3 minutes         | Separate address |

> Note: docs differ. The guide's Deposit Flow step says Rhino.fi bridges to Base "typically 5-15 minutes"; its Timing Expectations table gives the shorter figures above. Times depend on source chain finality and Rhino.fi processing.

All EVM chains share a single global deposit address. TRON and Solana get separate addresses due to address-structure differences. Addresses are reusable across multiple deposits; each user has unique global addresses per chain family (EVM, TRON, Solana). Token contract addresses per chain are in [references/REFERENCE.md](references/REFERENCE.md).

**Minimum deposit:** 1 USDT / 1 USDC / 1 EURC; on TRON 2 USDT. Smaller amounts may not be processed. Sending an unsupported token: contact Wirex support (token rescue via Rhino.fi).

### Linking Global Addresses

After generating deposit addresses via the Rhino.fi SDK, link them to the Wirex account:

**POST /api/v1/wallets/global** (empty `200` response)

```json
{
  "wallet_address": "0x1234...abcd"
}
```

### Retrieving Wallets

**GET /api/v1/wallets**

Returns the user's wallets with balances. The OpenAPI schema declares the 200 response as a single `WalletResponse` object, while the guide example shows a JSON array of wallets (the array form is shown in [references/REFERENCE.md](references/REFERENCE.md)); global deposit addresses have `wallet_type: "Global"` (other types: `Primary`, `Secondary`, `Card`).

See [references/REFERENCE.md](references/REFERENCE.md) for the full Rhino.fi SDK configuration example, TRON/Solana address creation, and detailed request/response formats.

## ERC20 Withdrawals

ERC20 withdrawals use a **two-phase delay pattern** to enhance security. The flow is:

1. **Request phase**: The user initiates a withdrawal request (unwrap WUSD/WEUR + transfer USDC/EURC, encoded as call data). `ExecutionDelayPolicy.request(wallet, nonce, callData)` records it with a `valid_after` timestamp (now + delay).
2. **Wait phase**: The request remains pending until the `valid_after` time is reached.
3. **Execute phase**: After the delay expires, the original call data is submitted with the matching custom nonce and the unwrap + transfer executes.

Withdrawals run fully on-chain from the user's Smart Wallet, without Wirex backend involvement. On XRPL there is no delay: `POST /api/v1/withdrawal/execute` sends RLUSD immediately.

### Delay Values

| Operation         | Delay     |
|-------------------|-----------|
| Token transfers   | 3 seconds |
| Account changes   | 24 hours  |

The delay protects Wirex from frontrunning-based fraud.

Other `sdk.crypto.transfer` methods: `makeErc20TransferSynthetic(params)` (send synthetic tokens directly, no unwrap, no delay policy), `makeTransferWithoutDelayPolicy(params)` (unwrap a synthetic and send its base token in one op; the FX swap payment leg) and `batchTransfer({ tokenAddress, responses })` (several transfers in one batch).

### Wirex SDK Methods

The Wirex SDK (`@wirexapp/wpay-baas-sdk`) provides single-call and two-step approaches. Methods are namespaced under `sdk.crypto.transfer`; `tokenAddress` is a **synthetic** token (e.g. WUSD), unwrapped before its base token is sent.

#### Single-call (full transfer)

```typescript
// on-chain only: request -> wait out the delay -> final execution, no backend polling
const finalTxHash = await sdk.crypto.transfer.makeErc20TransferFull({
  tokenAddress: "0x...",
  recipientAddress: "0x...",
  amount: 100
});

// backend-driven: polls withdrawal requests until valid_after
await sdk.crypto.transfer.makeFullErc20Transfer({
  tokenAddress: "0x...",
  recipientAddress: "0x...",
  amount: 100 // number, in token units
});
// result: { firstPartTxHash, finalTxHash, success }
```

Both handle the two phases internally, waiting for the delay to pass before executing.

#### Two-step (manual control)

```typescript
// Step 1: Initiate the request
const requestTxHash = await sdk.crypto.transfer.makeErc20TransferFirstPart({
  tokenAddress: "0x...",
  recipientAddress: "0x...",
  amount: 100
}); // returns the request tx hash

// Step 2: fetch pending requests, wait until valid_after, then execute with call_data
const withdrawals = await sdk.api.withdrawal.getWithdrawalRequests();
const pending = withdrawals.find(w => w.to_address === "0x..."); // SDK still exposes to_address
await sdk.crypto.transfer.makeErc20TransferFinal(pending.call_data);
```

This approach gives the integrator control over the waiting period and allows for UI updates or user confirmations between steps.

### Pending Withdrawal Requests

**GET /api/v1/withdrawal/requests** (or via `sdk.api.withdrawal.getWithdrawalRequests()`)

Returns pending withdrawal requests as `{ "data": [...] }`:

| Field               | Description                                                        |
|---------------------|--------------------------------------------------------------------|
| wallet_address      | The user's Smart Wallet address (replaces `account_address`)       |
| token_address       | The base token being withdrawn (USDC/EURC)                         |
| destination_address | The destination address (replaces `to_address`)                    |
| amount              | Withdrawal amount (number)                                         |
| valid_after         | ISO 8601 timestamp after which execution is valid (e.g., `"2024-01-01T12:05:00.000Z"`) |
| valid_before        | ISO 8601 timestamp after which the request expires                 |
| hash                | Hash of the call data and nonce used to request the withdrawal     |
| call_data           | Encoded transaction data for execution                             |

`account_address` and `to_address` are deprecated but still returned with the same values; the TypeScript SDK still exposes only the old names.

## Webhooks

Wirex BaaS emits webhooks for crypto-related events:

| Webhook Endpoint              | Purpose                              |
|-------------------------------|--------------------------------------|
| /v2/webhooks/activities       | Deposit and transfer activity events |
| /v2/webhooks/balances         | Balance change notifications         |
| /v2/webhooks/erc-withdrawals  | Pending ERC20 withdrawal request (same fields as the endpoint above) |

See [references/REFERENCE.md](references/REFERENCE.md) for full webhook payload examples.

## FX Swap (stablecoin exchange)

Swaps between USDC and EURC, in either direction, are executed by Circle, not on-chain by the wallet. Three steps; requires the `StableExchange` capability `Active`, and both tokens listed in `GET /api/v1/config/tokens`:

1. `POST /api/v1/fx/estimate` with `source_asset_address`, `destination_asset_address` and exactly one of `source_asset_amount` / `destination_asset_amount` (decimal strings). Returns `estimation_id`, `trade_rate`, `destination_address` (`deposit_address` is deprecated), `expiration_time`; amounts are 2-decimal display values, with the exact values beside them as `source_asset_amount_precise` / `source_asset_decimals`, `destination_asset_amount_precise` / `destination_asset_decimals` and `trade_rate_precise` / `rate_decimals`.
2. Send `source_asset_amount_precise` base units of the source token on-chain to `destination_address` yourself and wait until mined.
3. `POST /api/v1/fx` with `estimation_id` and `payment_transaction_hash` (0x-prefixed, 66 chars). Returns `trade_id`.

The quote expiry includes the on-chain confirmation time.

## Token Addresses

See [overview ENVIRONMENTS.md](../wirex-baas-overview/references/ENVIRONMENTS.md) for complete token address tables (sandbox and production, Base and Stellar). Base mainnet (8453): WUSD `0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2`, WEUR `0x379e120C1921bFD8f5E0A1a3C699e7e800b66606` (18 decimals); USDC/USDT/EURC have 6 decimals (on Base Sepolia sandbox USDT has 18). Sandbox token addresses are also in the [sandbox skill](../wirex-baas-sandbox/SKILL.md).

## ABI Reference

Smart contract ABIs for ContractRegistry, Accounts, TokensRegistry, Kernel, and ERC20 are documented in [references/ABI-REFERENCE.md](references/ABI-REFERENCE.md).

# Wirex BaaS Crypto — Endpoint & Integration Reference

Detailed reference for all crypto-related endpoints, SDK integrations, webhook payloads, and token addresses.

## Table of Contents

- [Wallet Endpoint](#wallet-endpoint)
- [Global Addresses](#global-addresses)
- [Rhino.fi SDK Configuration](#rhinofi-sdk-configuration)
- [TRON and Solana Address Creation](#tron-and-solana-address-creation)
- [Withdrawal Requests Endpoint](#withdrawal-requests-endpoint)
- [Webhook Payloads](#webhook-payloads)
- [Token Addresses](#token-addresses)

---

## Wallet Endpoint

### GET /api/v1/wallet

Retrieve the user's wallet along with its balances. Optional query parameter: `wallet_address`. Auth: user token, or partner token plus `X-Chain-Id` and `X-User-Wallet`.

**Request Headers:**

| Header          | Required | Description                          |
|-----------------|----------|--------------------------------------|
| Authorization   | Yes      | Bearer `{access_token}`             |
| Content-Type    | Yes      | `application/json`                   |
| X-User-Wallet   | Yes (partner token) | The user's EOA address    |
| X-Chain-Id      | Yes (partner token) | The chain ID              |

**Response (200 OK):**

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
      "balance": 25.0,
      "reference_balance": 25.0,
      "reference_currency": "USD"
    },
    {
      "token_symbol": "WEUR",
      "token_address": "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606",
      "balance": 10.0,
      "reference_balance": 11.6,
      "reference_currency": "USD"
    }
  ]
}
```

**Field Descriptions:**

| Field              | Type   | Description                                       |
|--------------------|--------|---------------------------------------------------|
| wallet_address     | string | Address of this wallet (required)                 |
| wallet_name        | string | Display name, e.g. "Main Wallet"                  |
| wallet_status      | string | `Unknown`, `Confirmed`, `Rejected` (Confirmed = a correct AA wallet with all required policies) |
| wallet_type        | string | `Primary`, `Secondary`, `Global`, `Card`          |
| chain_family       | string | Only for non-EVM wallets, e.g. `solana`          |
| token_symbol       | string | Token ticker (WUSD, WEUR)                         |
| token_address      | string | Token contract address                            |
| balance            | number | Balance in token units                            |
| reference_balance  | number | Balance in the reference currency                 |
| reference_currency | string | ISO 4217 code; determined by the user's residence country (default USD) |

### GET /api/v3/wallet

Reads the same wallet on whichever chain it was deployed on, regardless of the chain of the request. Same optional `wallet_address` parameter and shape, plus `chain_id`, and per balance: `balance_precise` (base units as a decimal string scaled by `decimals`), `decimals`, `reference_balance_precise`, `reference_decimals` (the last two absent when no rate to the reference currency exists).

---

## Global Addresses

### POST /api/v1/wallets/global

Link a global deposit address (generated via Rhino.fi) to the account.

**Request Headers:**

| Header          | Required | Description                          |
|-----------------|----------|--------------------------------------|
| Authorization   | Yes      | Bearer `{access_token}`             |
| Content-Type    | Yes      | `application/json`                   |
| X-User-Wallet   | Yes      | The user's EOA address               |
| X-Chain-Id      | Yes      | The chain ID                         |

**Request Body:**

```json
{
  "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"
}
```

**Response (200 OK):** empty object `{}`. The linked wallet then appears in `GET /api/v1/wallets` with `wallet_type: "Global"`.

### GET /api/v1/wallets

Retrieve all wallets linked to the account.

**Request Headers:**

| Header          | Required | Description                          |
|-----------------|----------|--------------------------------------|
| Authorization   | Yes      | Bearer `{access_token}`             |
| Content-Type    | Yes      | `application/json`                   |
| X-User-Wallet   | Yes      | The user's EOA address               |
| X-Chain-Id      | Yes      | The chain ID                         |

No query parameters are documented; identify global wallets by `wallet_type: "Global"` (`GET /api/v3/wallets` does the same across every chain the user holds a wallet on and adds `chain_id`).

**Response (200 OK):**

> Note: docs differ. The OpenAPI reference declares the 200 schema as a single `WalletResponse` object; the guide (`retail-global-addresses`) shows a JSON array, as below.

```json
[
  {
    "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
    "wallet_name": "Main Wallet",
    "wallet_status": "Confirmed",
    "wallet_type": "Primary",
    "balances": []
  },
  {
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
    "wallet_name": "Global Wallet",
    "wallet_status": "Confirmed",
    "wallet_type": "Global",
    "balances": []
  }
]
```

---

## Rhino.fi SDK Configuration

Global addresses are created via the Wirex SDK or the Rhino.fi SDK directly. The Rhino.fi API key is provided by Wirex.

### Option A: Wirex SDK

```typescript
import { createSDK } from '@wirexapp/wpay-baas-sdk';

const sdk = await createSDK({
  env: 'dev',
  companyId: process.env.COMPANY_ID,
  getMainWalletClient: () => mainWalletClient,
  rhinoApiKey: process.env.RHINO_API_KEY, // enables Smart Deposit Addresses
});

const globalAddresses = await sdk.crypto.smartDepositAddress.initializeSmartDepositAddresses();
```

Without `rhinoApiKey`, accessing `sdk.crypto.smartDepositAddress` throws `ConfigurationError`. Other methods: `getAddresses()` (cached), `clearAddresses()`.

### Option B: Rhino.fi SDK

```typescript
import { RhinoSdk, SupportedChains } from "@rhino.fi/sdk";

const rhinoSdk = RhinoSdk({ apiKey: process.env.RHINO_API_KEY });

const supportedEVMChains = [
  SupportedChains.ETHEREUM,
  SupportedChains.ARBITRUM_ONE,
  SupportedChains.POLYGON,
  SupportedChains.OPTIMISM,
  SupportedChains.BNB_SMART_CHAIN,
  SupportedChains.KAIA,
];

// Step 1: create deposit addresses for EVM chains (one shared address)
const response = await rhinoSdk.api.depositAddresses.create({
  depositChains: supportedEVMChains,
  destinationChain: SupportedChains.BASE,
  destinationAddress: smartWalletAddress, // user's Base Smart Wallet
  bridgeIfNotSwappable: true,
  tokenOut: 'USDC',
  postBridgeData: { _tag: 'wirexwrap' },
  reusePolicy: 'reuse-existing',
});

if (response.response.status !== 200 || !response.data) {
  throw new Error(`Failed to create addresses: ${JSON.stringify(response.error)}`);
}

// Step 2: activate any inactive addresses
await Promise.all(
  response.data
    .filter((addr) => !addr.isActive)
    .map((addr) =>
      rhinoSdk.api.depositAddresses.activate({
        depositAddress: addr.depositAddress,
        depositChain: addr.depositChain,
      })
    )
);

// Step 3: link the global address to the Wirex account
await fetch("https://api-baas.wirexapp.com/api/v1/wallets/global", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${accessToken}`,
    "Content-Type": "application/json",
    "X-User-Wallet": userEoaAddress,
    "X-Chain-Id": chainId,
  },
  body: JSON.stringify({ wallet_address: response.data[0].depositAddress }),
});
```

### Supported Deposit Tokens per Chain

| Chain     | Chain ID | USDT | USDC | EURC |
|-----------|----------|------|------|------|
| Arbitrum  | 42161    | Yes  | Yes  | No   |
| Base      | 8453     | Yes  | Yes  | Yes  |
| BSC       | 56       | Yes  | Yes  | No   |
| Ethereum  | 1        | Yes  | Yes  | No   |
| Kaia      | 8217     | Yes  | No   | No   |
| Polygon   | 137      | Yes  | Yes  | No   |
| Optimism  | 10       | Yes  | Yes  | No   |
| Solana    | n/a      | Yes  | Yes  | No   |
| TRON      | n/a      | Yes  | No   | No   |

Minimum deposit: 1 USDT / 1 USDC / 1 EURC (1 USD equivalent or 1 EUR); on TRON 2 USDT (2 USD equivalent).

### Deposit Token Contract Addresses

| Chain     | USDT | USDC | EURC |
|-----------|------|------|------|
| Arbitrum One | `0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9` | `0xaf88d065e77c8cc2239327c5edb3a432268e5831` | -- |
| Base      | `0xfde4c96c8593536e31f229ea8f37b2ada2699bb2` | `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | `0x60a3e35cc302bfa44cb288bc5a4f316fdb1adb42` |
| BSC       | `0x55d398326f99059ff775485246999027b3197955` | `0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d` | -- |
| Ethereum  | `0xdac17f958d2ee523a2206206994597c13d831ec7` | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | -- |
| Kaia      | `0xd077a400968890eacc75cdc901f0356c943e4fdb` | -- | -- |
| Polygon   | `0xc2132d05d31c914a87c6611c10748aeb04b58e8f` | `0x3c499c542cef5e3811e1192ce70d8cc03d5c3359` | -- |
| Optimism  | `0x94b008aa00579c1307b0ef2c499ad98a8ce58e58` | `0x0b2c639c533813f4aa9d7837caf62653d097ff85` | -- |
| Solana    | `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` | `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` | -- |
| TRON      | `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` | -- | -- |

---

## TRON and Solana Address Creation

TRON and Solana have a different address structure and need separate address creation with the same options:

```typescript
const tronAddresses = await rhinoSdk.api.depositAddresses.create({
  depositChains: [SupportedChains.TRON],
  destinationChain: SupportedChains.BASE,
  destinationAddress: smartWalletAddress,
  // ... same options as above
});

const solanaAddresses = await rhinoSdk.api.depositAddresses.create({
  depositChains: [SupportedChains.SOLANA],
  destinationChain: SupportedChains.BASE,
  destinationAddress: smartWalletAddress,
  // ... same options as above
});
```

Activate inactive addresses the same way. Link each non-EVM address to the Wirex account separately via `POST /api/v1/wallets/global`.

---

## Withdrawal Requests Endpoint

### GET /api/v1/withdrawal/requests

Retrieve all pending ERC20 withdrawal requests for the account.

**Request Headers:**

| Header          | Required | Description                          |
|-----------------|----------|--------------------------------------|
| Authorization   | Yes      | Bearer `{access_token}`             |
| Content-Type    | Yes      | `application/json`                   |
| X-User-Wallet   | Yes      | The user's EOA address               |
| X-Chain-Id      | Yes      | The chain ID                         |

**Response (200 OK):**

```json
{
  "data": [
    {
      "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
      "token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "destination_address": "0xF4D2A0E30C7983EF65DC0DD938BED82C7E3745DB",
      "amount": 100.0,
      "valid_after": "2024-01-01T12:05:00.000Z",
      "valid_before": "2024-01-02T12:05:00.000Z",
      "hash": "0x8A7B6C5D4E3F2A1B0C9D8E7F6A5B4C3D2E1F0A9B8C7D6E5F4A3B2C1D0E9F8171",
      "call_data": "3F7D9E1C5A2B804D6E93F7C1A0B5D8E29F4A3B7C6D5E0F1A2B3C4D5E6F7A8B9..."
    }
  ]
}
```

**Field Descriptions:**

| Field               | Type   | Description                                                |
|---------------------|--------|------------------------------------------------------------|
| wallet_address      | string | The user's Smart Wallet address (replaces `account_address`) |
| token_address       | string | Base token being withdrawn (USDC/EURC)                     |
| destination_address | string | The destination address (replaces `to_address`)            |
| amount              | number | Withdrawal amount                                          |
| valid_after         | string | ISO 8601 timestamp after which execution is allowed        |
| valid_before        | string | ISO 8601 timestamp after which the request expires         |
| hash                | string | Hash of the call data and nonce used to request this withdrawal |
| call_data           | string | Encoded call data for finalizing the withdrawal            |

`account_address` and `to_address` are deprecated: still returned with the same values for backward compatibility (the TypeScript SDK still exposes only these).

The `valid_after` timestamp is set by the smart contract's `ExecutionDelayPolicy` (token transfers: 3 seconds; account changes: 24 hours). The withdrawal cannot be finalized before this time. The same fields are delivered by `POST {your_webhook_base_url}/v2/webhooks/erc-withdrawals` when a request is created.

### ZeroDev (direct) flow

Without the Wirex SDK: encode `withdraw(uint256 amount)` on the unified token (unwrap) plus an ERC20 `transfer` on the base token, batch them with `account.encodeCalls`, derive a custom nonce key from `keccak256(encodedCalls)` via `getCustomNonceKeyFromString(key, '0.7')`, call `ExecutionDelayPolicy.request(address wallet, uint256 nonce, bytes callData)` (returns `uint48`), wait for `valid_after`, then send a UserOperation with the original calls and the same custom nonce. Unified tokens use 18 decimals, USDC/EURC 6.

---

## Webhook Payloads

See [wirex-baas-webhooks reference](../wirex-baas-webhooks/references/REFERENCE.md) for complete crypto-related webhook payloads (activity, balance, ERC withdrawal).

---

## Token Addresses

See [overview ENVIRONMENTS.md](../wirex-baas-overview/references/ENVIRONMENTS.md) for complete token address tables (sandbox and production, Base and Stellar). Always verify token addresses against the on-chain `TokensRegistry` contract before integration.

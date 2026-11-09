# Wirex BaaS Environments Reference

Reference for Wirex BaaS environments, blockchain networks, contract registry addresses, token configurations, and shared sandbox test credentials.

---

## API Environments

### Core API

| Environment | Base URL | Description |
|---|---|---|
| Sandbox | `https://api-baas.wirexapp.tech` | Development and testing environment. Uses testnet blockchains and test credentials. No real funds are processed. |
| Production | `https://api-baas.wirexapp.com` | Live environment with real funds and mainnet blockchains. Requires production credentials from Wirex onboarding. |

### PCI-Compliant Card API

Card data for top-up and push-to-card is submitted to Wirex's PCI-compliant secure environment, never to the BaaS API. The recommended way to reach it is the [PCI Compliant SDK](https://docs.wirexapp.com/docs/retail-pci-sdk), which selects the environment by name; the base URLs below are for calling the card-manager API directly. These endpoints handle sensitive card data and are subject to additional security requirements.

| Environment | Base URL | Description |
|---|---|---|
| PCI Sandbox | `https://wx-acquiring-card-manager-uat.wirexapp.com` | Card tokenization testing |
| PCI Production | `https://wx-acquiring-card-manager.wirexapp.com` | Live card tokenization |

### Helper API

| Environment | Base URL | Description |
|---|---|---|
| Helper API (Sandbox only) | `https://ramc.wirexapp.tech` | Simulates external events that cannot be triggered through the standard API (bank deposits, transfer completions, card transactions). Available in Sandbox only; it does not exist in Production. |

---

## Blockchain Networks

### Production Networks

| Network | Chain ID | Type |
|---|---|---|
| **Base** | `8453` | EVM (Ethereum L2) |
| **Stellar** | `9223372036854775806` | Stellar Protocol |
| **Tempo** | `4217` | Production chain (regular tokens only) |

### Sandbox Networks

| Network | Chain ID | Type |
|---|---|---|
| **Base Sepolia** | `84532` | EVM Testnet |
| **Stellar Testnet** | `9223372036854775806` | Stellar Testnet |
| **XRPL** | `9223372036854775805` | XRP Ledger (non-EVM; Wirex-assigned ID, not EIP-155) |

XRPL is a settlement chain selected with the `X-Chain-Id` header; accounts are created via `POST /api/v1/accounts` instead of on-chain wallet deployment, and it settles in RLUSD. Confirm the XRPL chain ID for your target environment with Wirex. The ID above is the sandbox value from the XRPL addendum.

> **Important:** The Stellar chain ID value `9223372036854775806` is identical in both sandbox and production. Always ensure your base URL matches your intended environment (sandbox or production).

---

## Sandbox Test Credentials

The following shared credentials are available for quick sandbox testing. They are for initial integration testing only; contact Wirex for dedicated credentials for your company.

| Credential | Value |
|---|---|
| **client_id** | `3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB` |
| **client_secret** | `6FIY2GEQvdlgUEFHw4Dbii22_wCAqZ37lWV3TEMfTlkxrn8F5IbdgX9TiAvQUEsC` |
| **partner_id** | `0x00000000000000000000000000000044` |

### Quick Authentication Test

```bash
curl -X POST "https://api-baas.wirexapp.tech/api/v1/token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB",
    "client_secret": "6FIY2GEQvdlgUEFHw4Dbii22_wCAqZ37lWV3TEMfTlkxrn8F5IbdgX9TiAvQUEsC",
    "grant_type": "client_credentials"
  }'
```

Expected response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_at": 1700000000
}
```

---

## Contract Registry Addresses

Wirex provides a ContractRegistry address per chain and environment. All other contract addresses are resolved dynamically from the registry using `contractByName(name)`.

### Sandbox Contract Registries

| Network | Chain ID | Contract Registry Address |
|---|---|---|
| **Base Sepolia** | `84532` | `0xC801a0f38E20500B5840c4927553b3409890bc3c` |
| **Stellar Testnet** | `9223372036854775806` | `CB2F7E7QVPUHUCMKIWNBTEPLL2S3GYDGQJQECIRKQ2PRKL2U3XNXOSNO` |

### Production Contract Registries

| Network | Chain ID | Contract Registry Address |
|---|---|---|
| **Base** | `8453` | `0xAFa697ebC7919998AF5CdE325Fbe990dC926aae4` |
| **Stellar** | `9223372036854775806` | `CCRZBVBWNMDYOOQNJKB6TGMTSE5HE57RWQUGTN3AWBHMDHO45UCABJRE` |
| **Tempo** | `4217` | `0x17d78eFFa90B3679b3A0224B21f8be82493A3B2C` |

### Contracts Available from Registry

The registry resolves the following contract names (see the ABI Reference in the docs / crypto skill):

| Contract | Purpose |
|---|---|
| **Accounts** | User registration (`createUserAccountWithWallet`). |
| **FundsManagement** | Executor module for oracle transactions. |
| **ExecutionDelayPolicy** | Time-lock policy for wallets. |
| **TokensRegistry** | Supported token list. |

### Querying the Registry (EVM Example)

```javascript
const { ethers } = require('ethers');

const REGISTRY_ABI = [
  'function contractByName(string name) view returns (address)'
];

// RPC Provider URL is provided by Wirex per environment
const provider = new ethers.JsonRpcProvider(process.env.RPC_PROVIDER_URL);
const registry = new ethers.Contract(
  '0xC801a0f38E20500B5840c4927553b3409890bc3c',
  REGISTRY_ABI,
  provider
);

// Discover contract addresses
const accountsAddress = await registry.contractByName('Accounts');
const fundsAddress = await registry.contractByName('FundsManagement');
const delayPolicyAddress = await registry.contractByName('ExecutionDelayPolicy');
const tokensRegistryAddress = await registry.contractByName('TokensRegistry');
```

---

## Token Addresses

### Sandbox Tokens -- Base Sepolia (Chain ID: 84532)

| Token | Symbol | Address | Decimals |
|---|---|---|---|
| USD Coin | USDC | `0x7Af7cDbd557eD302F7538Db1e3d094C8BBcA665c` | 6 |
| Tether | USDT | `0x2C6c7c00ACa9B9D8446d107367485079b0471706` | 18 |
| Euro Coin | EURC | `0xF70461ffb413981852683657A310892227e3989e` | 6 |
| WUSD | WUSD | `0x0774164DC20524Bb239b39D1DC42573C3E4C6976` | 18 |
| WEUR | WEUR | `0x5c55F314624718019A326F16a62A05D6C6d8C8A2` | 18 |

### Production Tokens -- Base (Chain ID: 8453)

| Token | Symbol | Address | Decimals |
|---|---|---|---|
| USD Coin | USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | 6 |
| Tether | USDT | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | 6 |
| Euro Coin | EURC | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` | 6 |
| WUSD | WUSD | `0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2` | 18 |
| WEUR | WEUR | `0x379e120C1921bFD8f5E0A1a3C699e7e800b66606` | 18 |

### Production Tokens -- Tempo (Chain ID: 4217)

| Token | Symbol | Address | Decimals |
|---|---|---|---|
| USDT0 | USDT0 | `0x20C00000000000000000000014f22CA97301EB73` | 6 |

> **Tempo has no unified tokens.** `USDT0` is the only entry in the Tempo `TokensRegistry` and is a `Regular` token; `WUSD`/`WEUR` do not exist on Tempo. Balances on Tempo are held directly in `USDT0` at 6 decimals.

> Stellar token addresses are not published in the docs. Resolve them (and any other token) from `GET /api/v1/config/tokens`.

> **Note on Decimals:** USDC and EURC use 6 decimals; WUSD and WEUR use 18 on both sandbox and production. USDT uses 18 decimals on sandbox Base Sepolia but **6 on production Base**. The exponent behind every `precise_amount` is the token's own `decimals` (not a fixed 18) -- assuming wei for a 6-decimal token overstates the amount by 10^12. Read decimals from `GET /api/v1/config/tokens` or the `TokensRegistry`.

---

## Token Catalogue

```
GET /api/v1/config/tokens
```

Returns the tokens available to your company (per company and per chain). Use it to resolve `token_address` values and read each token's `decimals`. Read addresses from this endpoint rather than hardcoding them; the tables above are a convenience, not a contract.

```json
{
  "data": [
    {
      "address": "0x0774164DC20524Bb239b39D1DC42573C3E4C6976",
      "symbol": "WUSD",
      "default_symbol": "WUSD",
      "base_token_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "equivalent_symbols": ["USDC", "USDT"],
      "decimals": 18,
      "is_active": true,
      "supported_chain_ids": [8453],
      "token_type": "Synthetic"
    }
  ]
}
```

| `token_type` | What it is | Examples |
|---|---|---|
| `Synthetic` | A **unified token** (always has `base_token_address`) minted when a supported stablecoin is deposited, burned when value leaves | `WUSD`, `WEUR` |
| `Regular` | A plain ERC-20 stablecoin held at its own contract | `USDC`, `USDT`, `EURC` |

Treat any other `token_type` as one you do not handle. Balances are held in unified tokens; on-chain movements in and out of the platform happen in regular tokens.

## Client Application Configuration

```
GET /api/v1/config
```

Front-end bootstrap configuration for a company (auth provider settings, chain list, support integration, Apple Pay / Google Pay parameters). No token is required. Optional headers: `X-Company-Id` (company id as a UUID, recommended) and `X-Company-Name` (used only when `X-Company-Id` is not sent). With a Wirex token the token's company is answered and the headers are ignored; with neither a token nor a header the platform default company is answered; an unknown id or name returns `400`. Fields of note: `transactionAuthorizationMode` (`External` or `Signature` -- whether payouts need a wallet signature), `sdkAllowedDomains`, `topup`, `p2c_currencies`. A server-side integration takes its chain and contract configuration from the credentials above instead.

---

## Infrastructure Credentials

When deploying Smart Wallets directly (not using the Wirex SDK), you receive these endpoints per environment. Contact Wirex to obtain the specific URLs.

| Credential | Description |
|---|---|
| **Bundler RPC URL** | ZeroDev bundler for UserOperation submission |
| **Paymaster RPC URL** | ZeroDev paymaster for gas sponsorship |
| **RPC Provider URL** | Blockchain RPC endpoint for on-chain reads and transaction monitoring |

### Rhino.fi API Key

A **Rhino.fi API Key** is provided for multi-chain deposits: creating smart deposit addresses for cross-chain bridging via global addresses.

> **Note:** Credentials are environment-specific. Contact Wirex to obtain dedicated credentials for your company.

---

## Environment Selection Guide

| Use Case | Environment | Base URL | Chain ID |
|---|---|---|---|
| Initial development | Sandbox | `https://api-baas.wirexapp.tech` | `84532` (Base Sepolia) |
| Stellar integration testing | Sandbox | `https://api-baas.wirexapp.tech` | `9223372036854775806` |
| XRPL integration testing | Sandbox | `https://api-baas.wirexapp.tech` | `9223372036854775805` (confirm with Wirex) |
| Card tokenization testing | PCI Sandbox | `https://wx-acquiring-card-manager-uat.wirexapp.com` | n/a (no `X-Chain-Id` documented for the PCI host) |
| Pre-production validation | Sandbox | `https://api-baas.wirexapp.tech` | `84532` |
| Live Base operations | Production | `https://api-baas.wirexapp.com` | `8453` |
| Live Stellar operations | Production | `https://api-baas.wirexapp.com` | `9223372036854775806` |
| Live Tempo operations | Production | `https://api-baas.wirexapp.com` | `4217` |
| Live card tokenization | PCI Production | `https://wx-acquiring-card-manager.wirexapp.com` | n/a (no `X-Chain-Id` documented for the PCI host) |

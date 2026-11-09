---
name: wirex-baas-overview
description: "Wirex BaaS platform overview and getting started guide — start here for integration basics. Covers what Wirex BaaS is, the 6-step integration flow, partner onboarding, API environments (sandbox and production URLs), shared sandbox test credentials, required headers (Authorization, X-Chain-Id), error handling, blockchain networks (Base, Stellar, Tempo, XRPL), canonical token and contract registry addresses, MCP server setup, supported countries (72 card countries) with SEPA/ACH bank availability, and links to docs not covered by this plugin."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Platform Overview

## Introduction

Wirex BaaS (Banking-as-a-Service) lets partners embed blockchain-based financial services into their applications. Users get self-custodial wallets, payment cards, and multi-currency accounts without the partner building or maintaining the underlying infrastructure. Capabilities:

- **Self-Custodial Wallets** -- Account Abstraction (AA) smart contract wallets that users control: gas-free transactions, built-in delay mechanisms for withdrawals, registered in Wirex smart contracts.
- **Payment Cards** -- Visa cards linked to user wallets (virtual cards issued instantly, physical cards shipped to the user); crypto converts to fiat at point of sale.
- **Bank Accounts** -- EUR (SEPA) and USD (ACH) accounts for receiving and sending fiat transfers.
- **Multi-Chain Deposits** -- Users deposit USDC, USDT or EURC from supported chains; funds land in one unified balance (WUSD for USD, WEUR for EUR).
- **Push to Card** -- Transfer funds from a wallet to any external Visa or Mastercard.
- **Card Top-Up** -- Fund a wallet from an external Visa or Mastercard card (AFT rails, with 3DS).

All services are accessed through a REST API layer with OAuth2 authentication, standardized error handling, and blockchain transaction management. For how card spending works under the hood (Execution Delay Policy and Funds Management Executor modules, charge to Wirex Pay's Master Account), see the How it Works page of the docs.

---

## Integration Flow

Integrating with Wirex BaaS follows six sequential steps:

### Step 1: Partner Setup

Obtain credentials and configure webhooks (see [Partner Onboarding](#partner-onboarding)). Wirex provides, per environment:

- **client_id** -- UUID identifying your application
- **client_secret** -- Secret string for OAuth2 token exchange
- **partner_id** -- 16-byte hex identifier used in on-chain operations (e.g., `0x00000000000000000000000000000044` for the shared sandbox)

### Step 2: Authentication

Implement server-to-server token exchange using OAuth2 client credentials:

```
POST /api/v1/token
Content-Type: application/json

{
  "client_id": "<your-client-id>",
  "client_secret": "<your-client-secret>",
  "grant_type": "client_credentials"
}
```

The returned `access_token` is valid for 48 hours and is sent as a Bearer token. See the `wirex-baas-auth` skill.

### Step 3: Wallet Deployment

Deploy Smart Wallets using the ZeroDev SDK: create a kernel account with the required modules, install the FundsManagementExecutor and ExecutionDelayPolicy modules, then register in the Accounts contract. Resolve contract addresses from the ContractRegistry (see Environments reference).

### Step 4: On-Chain Registration

Register the wallet in the **Accounts** contract using your `partner_id` as the `parentEntity` parameter.

### Step 5: User Registration

Register users via API after on-chain registration (`POST /api/v2/user` with KYC data) and choose a KYC flow: Wirex Hosted, SumSub Shared, or KYC Sharing via API. Obtain a user-scoped token via `POST /api/v1/user/authorize` for user-specific operations.

### Step 6: Operations

Once users are verified:

- Issue virtual or physical Visa cards
- Move money: bank accounts (SEPA/ACH), push to card, card top-up, crypto
- Query balances and transaction history (activities)
- Receive webhook notifications for asynchronous events

Wirex's External Authorization model (partner-managed balances, no per-user wallet deployment) is a different integration path; see [More Documentation](#more-documentation).

## Partner Onboarding

Information exchanged with Wirex during integration setup.

**You provide to Wirex:**

- Webhook base URL (HTTPS), e.g. `https://api.partner.com/webhooks` -- Wirex configures the webhook endpoints for your company
- Privy App ID -- only if your application uses Privy SDK for wallet management / Privy-based auth
- A technical contact for integration support

**Wirex provides to you:**

- `client_id` and `client_secret` (per environment)
- `partner_id` (identifier for wallet operations)
- Webhook endpoint configuration
- Privy App ID registration (if using Privy-based auth)
- Blockchain RPC endpoints (if deploying wallets directly)
- Smart contract addresses (per chain and environment)

---

## Environments

Wirex BaaS provides separate environments for development and production use.

### Core API Environments

| Environment | Base URL | Purpose |
|---|---|---|
| **Sandbox** | `https://api-baas.wirexapp.tech` | Development and testing with test data |
| **Production** | `https://api-baas.wirexapp.com` | Live operations with real funds |

### PCI-Compliant Card Environments

Card data for top-up and push-to-card is submitted to Wirex's PCI-compliant secure environment, never to the BaaS API (subject to additional security requirements). The recommended way to reach it is the [PCI Compliant SDK](https://docs.wirexapp.com/docs/retail-pci-sdk), which selects the environment by name; the base URLs below are for calling the card-manager API directly:

| Environment | Base URL | Purpose |
|---|---|---|
| **PCI Sandbox** | `https://wx-acquiring-card-manager-uat.wirexapp.com` | Card tokenization testing |
| **PCI Production** | `https://wx-acquiring-card-manager.wirexapp.com` | Live card tokenization |

### Helper API

| Environment | Base URL | Purpose |
|---|---|---|
| **Helper API** | `https://ramc.wirexapp.tech` | Sandbox only: simulates external events (bank deposits, transfer completions, card transactions) |

### Blockchain Networks

Wirex BaaS operates on the following blockchain networks:

**Production Networks:**

| Network | Chain ID | Description |
|---|---|---|
| Base | `8453` | Ethereum L2 -- primary EVM chain |
| Stellar | `9223372036854775806` | Stellar network |
| Tempo | `4217` | Production chain; no unified tokens, balances held in `USDT0` |

**Sandbox Networks:**

| Network | Chain ID | Description |
|---|---|---|
| Base Sepolia | `84532` | Base testnet for development |
| Stellar Testnet | `9223372036854775806` | Stellar testnet (same chain ID as production) |
| XRPL | `9223372036854775805` | XRP Ledger, Wirex-assigned ID (not EIP-155); settles in RLUSD |

> **Note:** The Stellar chain ID is the same value (`9223372036854775806`) in both sandbox and production. Use the base URL that matches your environment (sandbox or production). XRPL has no EIP-155 chain ID; confirm the value for your environment with Wirex.

### Shared Sandbox Credentials

For quick testing (contact Wirex for dedicated credentials):

| Credential | Value |
|---|---|
| `client_id` | `3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB` |
| `client_secret` | `6FIY2GEQvdlgUEFHw4Dbii22_wCAqZ37lWV3TEMfTlkxrn8F5IbdgX9TiAvQUEsC` |
| `partner_id` | `0x00000000000000000000000000000044` |

---

## Credentials

Wirex provides the following credentials per environment:

| Credential | Format | Description |
|---|---|---|
| **client_id** | UUID string | Uniquely identifies your partner application. Passed in the token request body. |
| **client_secret** | Opaque string | Used alongside `client_id` to authenticate token requests. Must be stored securely and never exposed in client-side code. |
| **partner_id** | 16-byte hex string | On-chain identifier for Account Abstraction operations (e.g., `0x00000000000000000000000000000044` for the shared sandbox). Used as the `parentEntity` parameter when registering user wallets in the Accounts smart contract. Not secret but should be validated against expected value. Can be stored in application configuration. |

### Security Requirements

- Store `client_secret` in a secrets manager or encrypted environment variable. Never commit it to source control.
- Rotate credentials immediately if a compromise is suspected.
- Credentials are environment-specific: use separate credentials for Sandbox and Production.

---

## API Basics

### Protocol and Security

- **HTTPS only** -- All API communication uses HTTPS with TLS 1.2 or higher. Plain HTTP requests are rejected.
- **Content-Type** -- All request and response bodies use `application/json`.
- **Timeout** -- A 30-second timeout is recommended for API calls (Wirex webhook delivery uses a 10-second timeout). Use webhooks for async confirmation.
- **IP allowlisting** -- Available for `POST /api/v1/token`; contact Wirex. Contact Wirex too if you need the webhook source IPs.

### Required Headers

Every API request must include the following headers:

| Header | Required | Description |
|---|---|---|
| `Authorization` | Most endpoints | `Bearer <token>`: S2S token from `/api/v1/token`, or a user token from `/api/v1/user/authorize` |
| `X-Chain-Id` | Yes | Target chain ID (e.g., `84532` for Sandbox Base Sepolia, `8453` for Production Base). **Required for all requests.** |
| `Content-Type` | Requests with a JSON body | `application/json` |
| `X-Company-Id` | `GET /api/v1/config` without a token | Company id as a UUID |

Additional headers for user-specific operations:

| Header | When Required | Description |
|---|---|---|
| `X-User-Wallet` | S2S-token calls on a specific user | User's EOA (Externally Owned Account) address — **NOT the Smart Wallet address** |
| `X-User-Email` | S2S-token calls on a specific user | Email address of the user |
| `X-User-Id` | S2S-token calls on a specific user | User's UUID |

> With an S2S token, exactly **one** of `X-User-Wallet`, `X-User-Email`, or `X-User-Id` is required for endpoints that operate on a specific user. Multiple identity headers are **rejected** (`ErrorInvalidField`). A user token already identifies its user, so these headers are not needed. User-agnostic endpoints (token, config, user creation) do not require them. Sensitive operations also need a short-lived action token; see the `wirex-baas-auth` skill.

### User-Agnostic Endpoints

The following endpoints do not require user identity headers:

- `POST /api/v1/token` -- Authentication
- `POST /api/v1/user` -- User creation
- `POST /api/v2/user` -- User creation (v2)
- `GET /api/v1/config` -- Platform configuration
- `GET /api/v1/validation/rules` -- Validation rules

### API Versions

| Prefix | Contents |
|---|---|
| `/api/v1/` | Base surface: authentication, users, KYC, wallets, cards, bank accounts, recipients, activity |
| `/api/v2/` | Card issuance with a `delivery_id` invoice, recipients with payment details in one call, `[V2] Get user` / server-side create user, KYC data update, the KYC questionnaire, activity feed/search/single-item |
| `/api/v3/` | Corridor transfers: one estimate/initiate/confirm flow for every payment rail; card issuance, reads, reissue and order configuration; cross-chain wallet reads; activity feed/search/single-item |

A `v2` endpoint does not deprecate its `v1` counterpart; pick one flow per integration and follow it end to end.

### Pagination and Amounts

- List endpoints take `page_number` (1-indexed), `page_size` (default 25, **max 50**; larger values return `400 ErrorInvalidField`) and `sort` (`name` ascending default, or `usage`).
- Money appears as `amount` (decimal) and `precise_amount` (string integer in the token's smallest unit). Use `precise_amount` for on-chain transfers; the exponent is the token's own `decimals` from `GET /api/v1/config/tokens`, not a fixed 18.

### Multi-Chain Deposits (Global Addresses)

Users can deposit from these chains; funds end up in the unified stablecoin balance. Minimum deposit: 2 USD equivalent on Tron, 1 USD equivalent (or 1 EUR for EUR stablecoin) elsewhere.

| Chain | USDT | USDC | EURC |
|---|:--:|:--:|:--:|
| Arbitrum One, BSC, Ethereum, Polygon, Optimism, Solana | yes | yes | -- |
| Base | yes | yes | yes |
| Kaia, Tron | yes | -- | -- |
---

## MCP Server

Wirex BaaS hosts a remote Model Context Protocol (MCP) server so AI tools can work with the Wirex BaaS API and documentation.

**MCP Server URL:** `https://docs.wirexapp.com/mcp`

It provides direct API access, documentation search, real-time data from your Wirex BaaS account, and code generation assistance. The docs describe setup for Cursor, Windsurf and Claude Desktop; if your APIs require authentication, headers can be passed via query parameters or your MCP client's header configuration.

For setup details (config file locations, test prompts) and how to install these Agent Skills in Claude Code, Codex, Gemini CLI or via `npx skills`, see the [MCP Setup Reference](references/MCP-SETUP.md).

---

## Supported Countries

Non-custodial **card services** are available in 72 countries across four regions:

| Region | Country Count | Examples |
|---|---|---|
| **Europe** | 37 | United Kingdom, Germany, France, Spain, Italy, Netherlands, Sweden, Switzerland, Poland, Austria, and 27 more |
| **Asia-Pacific** | 7 | Australia, Hong Kong, Malaysia, New Zealand, Philippines, Taiwan, Thailand |
| **Latin America** | 9 | Argentina, Brazil, Chile, Colombia, Ecuador, El Salvador, Mexico, Panama, Peru |
| **Rest of the World** | 19 | UAE, South Africa, Japan, South Korea, Ukraine, Nigeria, Kenya, and 12 more |

Four more countries (Indonesia, Singapore, United States, Vietnam) appear only in the ACH bank-account list. For the complete list with ISO country codes, see the [Supported Regions Reference](references/SUPPORTED-REGIONS.md).

### Bank Account Availability

- **SEPA** -- EUR accounts, 29 countries (listed in the reference).
- **ACH** -- USD accounts (ACH and Fedwire), 48 countries (including the US; all US states and territories are supported except Texas (TX) and New York (NY), whose residents cannot open a USD account).

Availability depends on the user's country of residence. Check the user's `SepaAccount` / `AchAccount` capability via `GET /api/v2/user` (`Active`, `NotFulfilled`, `NotAvailable`). SEPA no longer appears automatically after KYC: it needs an explicit activation call (`POST /api/v1/bank/accounts` with `account_type: "Sepa"`, or the init/complete wallet-linking path); see the reference.

---

## Error Handling

All API errors follow a consistent JSON format:

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Human-readable message",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "field", "details": "email" },
    { "key": "issue", "details": "invalid_format" }
  ]
}
```

### Error Fields

| Field | Type | Description |
|---|---|---|
| `error_reason` | string | PascalCase error code (e.g., `ErrorInvalidField`, `ErrorPermissionDenied`, `ErrorNotFound`, `ErrorExpired`, `ErrorMissingField`, `ErrorAlreadyExists`, `ErrorNotSupported`, `ErrorConfigurationInvalid`) |
| `error_description` | string | Human-readable explanation of the error |
| `error_category` | object | Error classification object containing `category` (string) and `http_status_code` (integer) |
| `error_details` | array | Array of objects, each with `key` (string) and `details` (string) providing additional context |

### Error Categories

| Category | HTTP Status | Description | Recommended Action |
|---|---|---|---|
| `CategoryValidationFailure` | 400 | Invalid request parameters, missing headers, malformed data | Fix the request and retry |
| `CategoryUnauthorized` | 401 | Authentication failed (e.g., invalid or expired token) | Re-authenticate and retry |
| `CategoryForbidden` | 403 | Authenticated, but the operation is not permitted | Check `error_reason` |
| `CategoryInternalFailure` | 500 | Server-side failure | Check `error_reason` first; contact support if persistent |
| `CategoryTransientFailure` | 429 | Transient rejection (rate limiting) | Back off exponentially and retry |
| `CategoryTransportFailure` | 503 | A downstream service was unreachable | Check `error_reason`; contact support if persistent |

### Error Handling Best Practices

1. **Branch on `error_reason`**, not on the HTTP status -- a reason is not bound to one category across every endpoint. Use `error_category` only as a hint.
2. **Implement exponential backoff** for `CategoryTransientFailure` (429) errors.
3. **Do not retry** `CategoryValidationFailure` errors without modifying the request.
4. **Refresh tokens proactively** -- cache the S2S token and refresh 5 minutes before expiry to avoid `CategoryUnauthorized` errors.
5. **Log `error_reason` and `error_description`** for debugging and support escalations.

---

## References

- [Environments Reference](references/ENVIRONMENTS.md) -- Full environment URLs, chain IDs, contract registries, token addresses and the token catalogue
- [MCP Setup Reference](references/MCP-SETUP.md) -- MCP server configuration and Agent Skills installation
- [Supported Regions Reference](references/SUPPORTED-REGIONS.md) -- Complete country list with ISO codes and bank availability

## More Documentation

Sections of the Wirex docs not covered by this plugin:

- [Corporate developers](https://docs.wirexapp.com/docs/corporate-getting-started) -- Corporate API: environments, credentials, two-token (partner/corporation) authentication
- [TypeScript / JavaScript SDK](https://docs.wirexapp.com/docs/retail-sdk) -- typed SDK for authentication, BaaS API, on-chain wallet operations and crypto transfers
- [PCI Compliant SDK](https://docs.wirexapp.com/docs/retail-pci-sdk) -- browser SDK that collects and reveals card data inside Wirex-served iframes
- [External Authorization](https://docs.wirexapp.com/docs/retail-external-authorization) -- partner-managed balances with Master Account settlement ([overview](https://docs.wirexapp.com/docs/retail-extauth-overview), [authorization API](https://docs.wirexapp.com/docs/retail-extauth-api), [card transactions](https://docs.wirexapp.com/docs/retail-extauth-cards), [transaction screening](https://docs.wirexapp.com/docs/retail-extauth-risk-assessment))
- [Ripple (XRPL) integration addendum](https://docs.wirexapp.com/docs/retail-ripple-xrpl) -- where XRPL behavior differs from EVM

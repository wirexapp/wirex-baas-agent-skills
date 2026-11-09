---
name: wirex-baas-sdk
description: "Wirex BaaS TypeScript/JavaScript SDK (@wirexapp/wpay-baas-sdk) — official typed npm package wrapping OAuth2 token flow, BaaS REST services, and ZeroDev Kernel account-abstraction wallet operations. Covers installation (Node >= 18, viem peer dependency), createSDK options (env, companyId, chainId, getMainWalletClient, rhinoApiKey, logging), the MainWalletClient EIP-1193 contract, three auth paths (company OAuth2, Privy, JWT), the 7-step user registration flow (incl. single-signature allInOneStepOnboarding), sdk.api.baas.* services (incl. Circle FX swap estimate/execute), sdk.crypto.* modules (token transfers with or without the execution delay, synthetic token transfers, batch transfers (BaaS Corporate only), yield, smart deposit addresses), and typed error classes. Use when writing Node/TypeScript code against Wirex BaaS instead of raw HTTP."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS TypeScript / JavaScript SDK

## Overview

`@wirexapp/wpay-baas-sdk` is the official typed SDK for Wirex BaaS. One npm package wraps the OAuth2 token flow, all BaaS REST endpoints, and on-chain Account Abstraction wallet operations (ZeroDev Kernel V3.1). It is published on npm: https://www.npmjs.com/package/@wirexapp/wpay-baas-sdk.

> This is **not** the card-data SDK. Card collection, card reveal, the top-up 3DS step and the Apple Pay / Google Pay top-up checkout are covered by the PCI Compliant SDK (see the `wirex-baas-pci-sdk` skill), the recommended path for those surfaces, available for Web (`@wirexapp/card-*`), React Native, Flutter, iOS and Android. The two are installed and versioned independently and can be used together.

Use the SDK when you write Node.js / TypeScript code. For raw HTTP integration see the other skills (`wirex-baas-auth`, `wirex-baas-onboarding`, `wirex-baas-cards`, `wirex-baas-transfers`, `wirex-baas-crypto`). The SDK does not apply to External Authorization (see `wirex-baas-external-auth`): that model has no on-chain wallet.

## Requirements

| Requirement | Notes |
|-------------|-------|
| Node.js >= 18 | Required runtime |
| `viem ^2.49.3` | Peer dependency, install separately |
| `CLIENT_ID` / `CLIENT_SECRET` | OAuth2 credentials from Wirex partner onboarding |
| `COMPANY_ID` | Company identifier in hex format |

## Install

```
npm install @wirexapp/wpay-baas-sdk viem
```

## Initialization

```typescript
import { createSDK, type SDKEnvironment } from '@wirexapp/wpay-baas-sdk';

const sdk = await createSDK({
  env: 'dev',                         // 'dev' | 'prod'
  companyId: process.env.COMPANY_ID,  // hex company ID
  chainId: 8453,                      // optional, defaults to remote config defaultChain
  getMainWalletClient: () => mainWalletClient,
  rhinoApiKey: process.env.RHINO_API_KEY, // optional: Smart Deposit Addresses only
  enableLogging: true,                // optional, default false
  logger: customLogger,               // optional, needs enableLogging: true
});
```

`createSDK` is async: always `await` it. Parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `env` | `'dev' \| 'prod'` | Yes | Environment |
| `companyId` | `string` | Yes | Company identifier in hex |
| `companyName` | `string` | No | Sent as `X-Company-Name` on the remote-config fetch; selects that company's chain / contracts / default company |
| `configUrl` | `string` | No | Explicit remote-config URL, overrides `env` |
| `chainId` | `number` | No | `8453` Base, `84532` Base Sepolia, `5042` Arc, `5042002` Arc Testnet. Defaults to remote config `defaultChain` |
| `getMainWalletClient` | `() => MainWalletClient` | Yes | Factory returning the user's embedded wallet client |
| `enableLogging` | `boolean` | No | Default `false` |
| `logger` | `Logger` | No | Custom logger (requires `enableLogging: true`) |
| `rhinoApiKey` | `string` | No | Rhino.fi API key, required only for `sdk.crypto.smartDepositAddress` |

> Note: docs differ. The on-chain registration page shows `env: 'production'` / `'sandbox'` in a `createSDK` example; the SDK page uses `'dev'` / `'prod'`. Use the SDK page values.

## MainWalletClient contract

`getMainWalletClient` returns an object with `address: string` and `getEthereumProvider(): Promise<{ request(args: { method: string; params?: unknown[] }): Promise<unknown> }>`. The EIP-1193 provider must handle at minimum `eth_accounts` (resolve signer address), `personal_sign` (SIWE, auth challenges) and `eth_signTypedData_v4` (UserOperations, EIP-712). Adapter examples for a raw private key (via viem) and a Privy embedded wallet (`wallet.getEthereumProvider()`) are in [the reference](references/REFERENCE.md#mainwalletclient-adapters).

## Authentication (three paths)

### A. Company OAuth2 (client_credentials), standard B2B backend flow

```typescript
const tokenRes = await sdk.api.baas.token.getToken({
  grant_type: 'client_credentials',
  client_id: process.env.CLIENT_ID,
  client_secret: process.env.CLIENT_SECRET,
  audience: 'https://api-business.wirexpaychain.tech', // same for dev and prod
});

// prime SDK auth state with the company token + user EOA wallet
sdk.auth.setAuthState(
  { access_token: tokenRes.access_token, expires_at: tokenRes.expires_at },
  userEoaWallet,
);

// after user registration: per-user PSI token
await sdk.auth.login({ authorizationToken: tokenRes.access_token, userWallet: userEoaWallet });
sdk.auth.isAuthenticated(); // true
```

After `login`, all `sdk.api.baas.*` calls use the PSI token automatically.

### B. Privy (consumer apps)

```typescript
const authResponse = await sdk.auth.login({ privy: { accessToken, identityToken } });
const userResponse = await sdk.auth.registerUser({ privy: { accessToken, identityToken }, country: 'FR' });
```

`accessToken` comes from `getAccessToken()`, `identityToken` from `useIdentityToken()` (both `@privy-io/react-auth`).

### C. JWT (own tokens or non-Privy provider)

```typescript
await sdk.auth.login({ authorizationToken: 'your-jwt-token', userWallet: userEoaWallet });
await sdk.auth.registerUser({ authorizationToken: 'your-jwt-token', userWallet: userEoaWallet, country: 'FR', initialData });
```

### Token management

`isAuthenticated()` (boolean), `getAccessToken()` (`string | null`, null if expired), `ensureAuthenticated()` (throws `AuthenticationError`), `getAuthHeaders()` (`{ Authorization, X-User-Wallet }`), `getUserWallet()`, `setUserWallet(wallet)`, `setAuthState(response, wallet?)` (restore stored state), `clearAuth()` (logout). Also `login`, `loginCompany`, `registerUser`, `registerCompany`.

## User registration flow (steps 1-5 on-chain, 6-7 API)

1. `await sdk.crypto.wallet.getSmartWalletAddress()`
2. `sdk.crypto.accountAbstraction.isPolicyInstalled()` and `isExecutorInstalled()`
3. If either is false: `sdk.crypto.accountAbstraction.signInPolicyAndExecutor()` (result `receipt.transactionHash`). Separately: `signInPolicy()`, `signInExecutor()`.
   **Single-signature alternative (steps 3 + 5):** if **neither** is installed, `sdk.crypto.onboarding.allInOneStepOnboarding()` batches executor install, root-validator switch and Accounts registration into one UserOperation (the user signs once instead of three times). Otherwise use the per-step calls.
4. Privy only: link the smart wallet with SIWE through `useLinkWithSiwe` (`generateSiweMessage`, `linkWithSiwe` with `walletClientType: 'smart_wallet'`, `connectorType: 'kernel'`), signing with `sdk.crypto.wallet.getSmartWalletClient()`.
5. `await sdk.crypto.accountContract.registerInAccounts()`; check with `isWalletInAccounts()`. Corporate: `registerInCorporateAccounts()`.
6. `sdk.auth.registerUser(...)`. Privy form posts to `POST /api/v1/user/retail`; JWT form posts to `POST /api/v2/user` with `userWallet` (the user's EOA, sent as `wallet_address`), `country` (required by the type, not sent on this path) and `initialData` (`profile` + `residence_address`; required for companies on the Full verification model). The API sees the wallet a few seconds after step 5 (indexer delay): until then it returns `400 ErrorNotFound` -- wait and retry.
7. `sdk.auth.login(...)`; with JWT pass `userWallet` (sent as `X-User-Wallet` on every later call).

## Modules at a glance

Full method tables are in [the reference](references/REFERENCE.md).

| Namespace | Purpose |
|-----------|---------|
| `sdk.auth` | login / register / token state |
| `sdk.api.baas.token` | `getToken(request)` OAuth2 exchange |
| `sdk.api.baas.user` | `getUser`, `getUserV2`, `createUser`, `authorizeUser`, phone, KYC documents and tokens |
| `sdk.api.baas.wallet` | `getWallet`, `getWallets`, `createGlobalWallet` |
| `sdk.api.baas.cards` | issue, list, lifecycle, details/CVV/PIN, limits, card transfer, 3DS, delivery, order fees |
| `sdk.api.baas.confirmation` | `requestSms`, `verifySms`, `verifySignature` (action tokens) |
| `sdk.api.baas.bank` | accounts, bank and corridor transfers |
| `sdk.api.baas.swap` | Circle FX stablecoin swap: `estimate`, `execute` |
| `sdk.api.baas.recipients` | recipient CRUD and payment details |
| `sdk.api.baas.activity` | `getFeed`, `getById`, `getFullStatement`, `getRequestedErcWithdrawals` |
| `sdk.api.baas.rates` / `config` | `getRates(request)` / `getConfig()` |
| `sdk.api.withdrawal` | `getWithdrawalRequests()` |
| `sdk.crypto.wallet` | smart wallet address / clients, UserOperations |
| `sdk.crypto.accountAbstraction` | policy and executor install |
| `sdk.crypto.accountContract` | Accounts contract registration |
| `sdk.crypto.onboarding` | `allInOneStepOnboarding()` |
| `sdk.crypto.transfer` | token transfers (with / without delay policy), synthetic token transfer, batch (BaaS Corporate only) |
| `sdk.crypto.yield` | yield data, withdraw, switch token |
| `sdk.crypto.smartDepositAddress` | multi-chain deposit addresses (needs `rhinoApiKey`) |

## Common flows

### Sensitive card data (PAN / CVV / PIN) via SMS OTP action token

```typescript
const session = await sdk.api.baas.confirmation.requestSms({ action_type: 'GetCardDetails' });
const tokenRes = await sdk.api.baas.confirmation.verifySms({ session_id: session.session_id, code: userInputCode });
const details = await sdk.api.baas.cards.getCardDetails(cardId, { action_token: tokenRes.token });
// -> { card_number, expiry_date }
const cvv = await sdk.api.baas.cards.getCardCvv(cardId, { action_token: tokenRes.token }); // -> { cvv }
```

In UAT the OTP code is `000000`. `getCardDetails`, `getCardCvv` and `getCardPin` return raw values to your code, which is permitted only in a PCI DSS compliant environment. To show card data to the user without handling the PAN yourself use the PCI SDK instead (Web, React Native, Flutter, iOS, Android: skill `wirex-baas-pci-sdk`); you still mint the action token.

### Token transfer out of the wallet (ExecutionDelayPolicy)

`tokenAddress` must be a **synthetic** token (e.g. WUSD): it is unwrapped and its base token is sent.

```typescript
// single call: request -> read the request's validAfter and wait until the chain timestamp passes it -> final execution; no backend polling
const finalTxHash = await sdk.crypto.transfer.makeErc20TransferFull({
  tokenAddress: '0x...', recipientAddress: '0x...', amount: 100,
});

// backend-driven: firstPart -> poll withdrawal requests until valid_after -> final
const result = await sdk.crypto.transfer.makeFullErc20Transfer({ tokenAddress: '0x...', recipientAddress: '0x...', amount: 100 });
// result.firstPartTxHash, result.finalTxHash, result.success
```

Manual control: `makeErc20TransferFirstPart(params)` -> `sdk.api.withdrawal.getWithdrawalRequests()` (find yours, use its `call_data`) -> `makeErc20TransferFinal(callData)` after `valid_after`. Other methods: `makeErc20TransferSyntheticFull(params)` (send the synthetic token itself, no unwrap, through the ExecutionDelayPolicy in one call: request -> wait until `validAfter` -> transfer; the recipient receives e.g. WUSD and no base token moves), `makeErc20TransferSynthetic(params)` (same, single UserOperation without a `request(...)` first; on a smart wallet with the ExecutionDelayPolicy installed it reverts with `AA23 ... Operation should be requested first`, use `makeErc20TransferSyntheticFull` there), `makeTransferWithoutDelayPolicy(params)` (unwrap + send in one op, used for the FX swap payment leg), `batchTransfer({ tokenAddress, responses: [{ transaction_id, operation_id, crypto_transfers: [{ address, precise_amount }] }] })` (**BaaS Corporate only**: the ids come only from the corporate bulk-transfer API `POST /api/v1/bulk/transfer`, any other ids revert with `Batch transaction not found` and no funds move; retail integrations send one transfer per recipient; `precise_amount` in the token's smallest unit).

### FX swap (estimate -> pay -> execute)

```typescript
const estimate = await sdk.api.baas.swap.estimate({
  source_asset_address: '0x...',      // e.g. USDC
  destination_asset_address: '0x...', // e.g. EURC
  source_asset_amount: '100',         // or destination_asset_amount, exactly one
});
const paymentTransactionHash = await sdk.crypto.transfer.makeTransferWithoutDelayPolicy({
  tokenAddress: '0x...',              // wrapped synthetic of the source asset, e.g. WUSD
  recipientAddress: estimate.destination_address, // deposit_address is a deprecated mirror
  amount: estimate.source_asset_amount,
});
const { trade_id } = await sdk.api.baas.swap.execute({
  estimation_id: estimate.estimation_id,
  payment_transaction_hash: paymentTransactionHash,
});
```

The estimate carries `trade_rate` and `expiration_time` (RFC3339); pay and execute before it expires.

Under the hood `swap.estimate` calls `POST /api/v1/fx/estimate` and `swap.execute` calls `POST /api/v1/fx` (SDK 0.1.12 source; the docs do not state this mapping, REST side: guide `retail-fx`). Observed live in sandbox: the user needs an active capability (unverified user -> `400` "Capability is not active"); minimum source amount 10 (`400` "Amount is below minimum allowed amount", `error_details` `min_amount: 10`); both amounts at once -> `400` "Only one of source_asset_amount or destination_asset_amount can be provided"; the response also carries `*_precise` amounts, `*_decimals` and `rate_decimals`, and an estimate lives about 120 s.

### Yield

```typescript
const y = await sdk.crypto.yield.fetchYieldData(); // { apy, currentPendingYield, weeklyYield, lifeTimeYield }
await sdk.crypto.yield.withdraw();
await sdk.crypto.yield.switchYieldToken(sdk.crypto.getToken('WEUR'));
```

### Smart deposit addresses

```typescript
const addresses = await sdk.crypto.smartDepositAddress.initializeSmartDepositAddresses();
// each: depositChain, depositAddress, supportedTokens[]
```

Funds are bridged to the SDK chain: `8453`/`84532` -> `BASE`, `5042`/`5042002` -> `ARC` (Rhino.fi has no testnets, so testnet IDs resolve to the mainnet code). Deposit networks: the destination chain itself, Base, Arbitrum, BNB Chain, Ethereum, Kaia, Polygon, Optimism, TRON, Solana, Stellar. Chains the destination rejects are skipped with a warning (e.g. USDT-only Kaia and TRON towards Arc). Requires `rhinoApiKey`.

## Live check (sandbox, SDK 0.1.12, 2026-10-25)

Run against sandbox (`env: 'dev'`, `chainId: 84532`) with a fresh EOA and the raw-private-key adapter above. These worked as documented: `createSDK`, `getSmartWalletAddress`, `isPolicyInstalled`/`isExecutorInstalled` (false -> true), `onboarding.allInOneStepOnboarding()` (one sponsored UserOperation; the wallet was then in Accounts), `token.getToken` (`{ access_token, token_type: "Bearer", expires_at }`), `setAuthState`, `registerUser` (JWT + `initialData`, first try, no indexer retry needed), `login` (`{ access_token, expires_at }`), `isAuthenticated`, `getAuthHeaders` (`Authorization`, `X-User-Wallet`), `user.getUserV2`, `wallet.getWallet`, `bank.getAccounts` / `recipients.getRecipients` / `activity.getFeed` / `cards.getCards` (all `{ data: [] }`), `cards.getActive3dsRequests` (bare `[]`), `config.getConfig`, `withdrawal.getWithdrawalRequests`, `yield.fetchYieldData` (`{ apy: 5, currentPendingYield, weeklyYield, lifeTimeYield }`), `crypto.getToken('WEUR')`, `smartDepositAddress` without `rhinoApiKey` -> `ConfigurationError` "rhinoApiKey is required to use smartDepositAddress.", `clearAuth` + `ensureAuthenticated` -> `AuthenticationError` "User is not authenticated. Please login first.". Transfers, `swap.execute` and card issuance were not run through the SDK.

> `NetworkError` for a 4xx carries only "Request failed with status code 400" in its message: the SDK reads `response.data.message`, while Wirex errors use `error_description`. The API body is on `error.cause.response.data` (`cause` is the axios error; `error.statusCode` holds the status). HTTP 401/403 are thrown as `AuthenticationError` instead (SDK 0.1.12 source).

## Error handling

All errors extend `SDKError`; use `instanceof`.

| Class | Cause |
|-------|-------|
| `SDKError` | Base class |
| `ConfigurationError` | Invalid configuration |
| `NetworkError` | Network / HTTP errors |
| `ContractError` | Smart contract interaction errors |
| `WalletError` | Wallet-related errors |
| `TransactionError` | Transaction execution errors |
| `AuthenticationError` | Authentication failures: re-login |
| `ValidationError` | Input validation errors |

```typescript
import { SDKError, AuthenticationError } from '@wirexapp/wpay-baas-sdk';

try {
  await sdk.auth.login({ authorizationToken: 'token' });
} catch (error) {
  if (error instanceof AuthenticationError) { /* re-login */ }
}
```

## Exported types

`SDKConfig`, `SDKEnvironment`, `Logger`, `TokenInfo`, `ContractAddresses`, `Hex`, `TransactionHash`, `MainWalletClient`, `PrivyAuth`, `LoginUserParams`, `LoginCompanyParams`, `RegisterUserParams`, `RegisterCompanyParams`, `AuthResponse`, `RegisterUserResponse` (all from `@wirexapp/wpay-baas-sdk`).

## Documentation

- SDK: https://docs.wirexapp.com/docs/retail-sdk
- Wallet deployment: https://docs.wirexapp.com/docs/retail-onchain-registration
- Withdrawals: https://docs.wirexapp.com/docs/retail-withdrawals
- Global addresses: https://docs.wirexapp.com/docs/retail-global-addresses
- PCI SDK: https://docs.wirexapp.com/docs/retail-pci-sdk

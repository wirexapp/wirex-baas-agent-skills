# Wirex BaaS SDK Reference

Source: https://docs.wirexapp.com/docs/retail-sdk

## MainWalletClient adapters

Raw private key (tests / embedded wallets):

```typescript
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import type { MainWalletClient } from '@wirexapp/wpay-baas-sdk';

export function createWalletClientFromKey(privateKey: `0x${string}`, rpcUrl: string): MainWalletClient {
  const account = privateKeyToAccount(privateKey);
  const client = createWalletClient({ account, chain: baseSepolia, transport: http(rpcUrl) });
  return {
    address: account.address,
    getEthereumProvider: async () => ({
      request: async ({ method, params = [] }) => {
        if (method === 'eth_accounts') return [account.address];
        if (method === 'personal_sign') {
          const [data] = params as [`0x${string}`, string];
          return client.signMessage({ account, message: { raw: data } });
        }
        if (method === 'eth_signTypedData_v4') {
          const [, json] = params as [string, string];
          const { domain, types, primaryType, message } = JSON.parse(json);
          const { EIP712Domain: _, ...filteredTypes } = types;
          return client.signTypedData({ account, domain, types: filteredTypes, primaryType, message });
        }
        return (client.transport as any).request({ method, params });
      },
    }),
  };
}
```

Privy embedded wallet:

```typescript
function getPrivyWalletClient(wallet: ConnectedWallet): MainWalletClient {
  return { address: wallet.address, getEthereumProvider: () => wallet.getEthereumProvider() };
}
```

## `sdk.auth` — Authentication Service

| Method | Description |
| --- | --- |
| `login(params)` | Login retail user (Privy or JWT) |
| `loginCompany(params)` | Login company/corporation |
| `registerUser(params)` | Register retail user |
| `registerCompany(params)` | Register company/corporation |
| `getAccessToken()` | Get current access token (returns `null` if expired) |
| `isAuthenticated()` | Check if user is authenticated |
| `getUserWallet()` | Get current user wallet address |
| `setUserWallet(wallet)` | Set user wallet address |
| `setAuthState(response, userWallet?)` | Manually set auth state from an auth response |
| `ensureAuthenticated()` | Throws `AuthenticationError` if not authenticated |
| `clearAuth()` | Clear all authentication state |
| `getAuthHeaders()` | Get `Authorization` and `X-User-Wallet` headers |

**Authentication Parameters:**

All auth methods accept either Privy tokens or a JWT authorization token:

```typescript
// Option 1: Privy authentication
{
  privy: {
    accessToken: string;   // Privy access token
    identityToken: string; // Privy identity token
  }
}

// Option 2: JWT authentication
{
  authorizationToken: string; // Your JWT token
}
```

**Company Registration Parameters:**

```typescript
interface RegisterCompanyParams {
  privy?: PrivyAuth;
  authorizationToken?: string;
  companyAddress: string;
  companyName: string;
  registrationCountry: string;
  registrationNumber: string;
}
```

## `sdk.crypto.wallet` — Wallet Service

| Method | Description |
| --- | --- |
| `getSmartWalletAddress()` | Get Smart Wallet address |
| `getSmartWalletClient()` | Get Kernel client with Policy |
| `getSmartWalletClientWithoutPolicy()` | Get Kernel client without Policy |
| `getSmartAccountSigner()` | Get signer for Smart Account |
| `getMainWalletClient()` | Get main wallet client |
| `sendUserOperationsAndWaitReceipt(callData, smartWalletClient?, config?)` | Send user operations and wait for receipt |
| `sendUserOperationsWithNonceAndWaitReceipt(callData, nonce, config?)` | Send user operations with specific nonce |
| `invalidateLocalCache()` | Clear cached wallet clients |

`config` on both send methods is `{ waitOnChainBlocks?: number; applyUnwrapGasFloor?: boolean }`. `applyUnwrapGasFloor` estimates the UserOperation first and raises `callGasLimit` to a gas floor when the estimate comes back lower. The transfer service sets it for the batches that unwrap a synthetic token before transferring (`makeErc20TransferFull` execution step, `makeErc20TransferFinal`, `makeTransferWithoutDelayPolicy`); plain transfers, policy installs and batch transfers keep the bundler estimate.

## `sdk.crypto.accountAbstraction` — Account Abstraction Service

| Method | Description |
| --- | --- |
| `isPolicyInstalled()` | Check if Execution Delay Policy is installed |
| `isExecutorInstalled()` | Check if Funds Management Executor is installed |
| `signInPolicyAndExecutor()` | Install Policy and Executor together |
| `signInPolicy()` | Install Policy only |
| `signInExecutor()` | Install Executor only |
| `getExecutorInstallCall()` | Executor install as a batchable call (used by onboarding) |
| `getPolicyInstallCall()` | Policy install as a batchable call (used by onboarding) |

## `sdk.crypto.accountContract` — Account Contract Service

| Method | Description |
| --- | --- |
| `isWalletInAccounts()` | Check if wallet is registered in Accounts contract |
| `registerInAccounts()` | Register wallet in Accounts contract (retail) |
| `isWalletInCorporateAccounts()` | Check if wallet is registered in Corporate Accounts contract |
| `registerInCorporateAccounts()` | Register wallet in Corporate Accounts contract (B2B) |
| `getAccountRegistrationCall()` | Accounts registration as a batchable call (used by onboarding) |

## `sdk.crypto.onboarding` — Onboarding Service

| Method | Description |
| --- | --- |
| `allInOneStepOnboarding()` | Executor install + policy switch + Accounts registration in a single UserOperation, signed by the pre-policy client. Use only when neither the executor nor the policy is installed; otherwise run the per-step methods. |

## `sdk.crypto.transfer` — Transfer Service

| Method | Description |
| --- | --- |
| `makeErc20TransferFull(params)` | Full transfer in one call: `request(...)` → read the request's `validAfter` from the ExecutionDelayPolicy and wait until the chain timestamp passes it → submit the final execution under its custom nonce. No backend/withdrawal-request polling. |
| `makeFullErc20Transfer(params)` | Full transfer driven by the backend: firstPart → poll withdrawal requests and wait for `valid_after` → final. Requires the Withdrawal API. |
| `makeErc20TransferFirstPart(params)` | First part only: submit the ExecutionDelayPolicy `request(...)` (creates the withdrawal request) |
| `makeErc20TransferFinal(callData)` | Second part only: complete the transfer with the request's calldata under its custom nonce |
| `makeErc20TransferSynthetic(params)` | Send a synthetic token as is (no unwrap) in a single UserOperation, without a `request(...)` first. On a smart wallet with the ExecutionDelayPolicy installed it reverts with `AA23 … Operation should be requested first`; use `makeErc20TransferSyntheticFull` there. |
| `makeErc20TransferSyntheticFull(params)` | Send a synthetic token as is (no unwrap) through the ExecutionDelayPolicy in one call: `request(...)` → wait until `validAfter` → submit the `transfer` under its custom nonce. The recipient receives the synthetic token (e.g. WUSD); no base token moves. |
| `makeTransferWithoutDelayPolicy(params)` | Unwrap a synthetic and transfer its base token in a single op, bypassing the ExecutionDelayPolicy. Used for the on-chain payment leg of an FX swap. |
| `batchTransfer(params)` | **BaaS Corporate only.** Execute backend bulk-transfer responses: one UserOperation per response, each under the custom nonce of its calldata. Returns the transaction hashes in response order. The `transaction_id` and `operation_id` come only from the corporate bulk-transfer API (`POST /api/v1/bulk/transfer`); with any other ids it reverts in simulation with `Batch transaction not found` and no funds move. Retail integrations send one transfer per recipient. |

**Transfer Parameters:**

```typescript
interface Erc20TransferParams {
  tokenAddress: `0x${string}`;
  recipientAddress: `0x${string}`;
  amount: number;
}

// Used by makeErc20TransferSynthetic / makeErc20TransferSyntheticFull; the synthetic token is sent as is (no unwrap)
interface SyntheticTransferParams {
  tokenAddress: `0x${string}`;     // synthetic token, e.g. WUSD
  recipientAddress: `0x${string}`;
  amount: number;
}

interface BatchTransferParams {
  tokenAddress: `0x${string}`;
  responses: BatchTransferResponse[];
}

interface BatchTransferResponse {
  transaction_id: string; // GUID
  operation_id: string;   // GUID
  crypto_transfers: {
    address: string;
    precise_amount: string; // amount in the token's smallest unit
  }[];
}

// Used by makeTransferWithoutDelayPolicy (FX swap payment leg)
interface SwapTransferParams {
  tokenAddress: `0x${string}`;     // wrapped synthetic token to unwrap and send (e.g. WUSD)
  recipientAddress: `0x${string}`; // FX deposit address returned by swap.estimate
  amount: string;                  // amount of the source token (decimal string)
}
```

## `sdk.crypto.yield` — Yield Service

| Method | Description |
| --- | --- |
| `fetchYieldData()` | Get yield data (APY, pending, weekly, lifetime) |
| `getYieldDataForGraphic()` | Get data for graph visualization |
| `getWeeklyYield()` | Get weekly yield |
| `withdraw()` | Withdraw accumulated yield |
| `switchYieldToken(token)` | Switch yield token (`TokenInfo`, e.g. `sdk.crypto.getToken('WEUR')`) |

**Yield Data Structure:**

```typescript
interface IYieldData {
  apy: number;                 // annual rate in percent
  currentPendingYield: string; // accumulated yield pending withdrawal
  weeklyYield: string;         // weekly yield
  lifeTimeYield: string;       // claimed + pending
}
```

## `sdk.crypto.smartDepositAddress` — Smart Deposit Addresses

| Method | Description |
| --- | --- |
| `initializeSmartDepositAddresses(forceRefresh?)` | Create/get all deposit addresses |
| `getAddresses()` | Get cached addresses |
| `getDestinationChain()` | Rhino.fi chain code funds are bridged to |
| `clearAddresses()` | Clear address cache |

**Destination chain** follows the SDK `chainId`: `8453` / `84532` → `BASE`, `5042` / `5042002` → `ARC`. Rhino.fi has no testnet chains, so testnet ids resolve to the mainnet code.

The destination chain is itself requested as a deposit chain, so the EVM group also holds a same-chain address — `ARC` → `ARC` when the SDK runs on Arc, `BASE` → `BASE` on Base.

Deposit chains the destination rejects are skipped with a warning and the remaining chains in the group are still created: no bridgeable route (Rhino.fi `DepositAddressNoBridgableTokens`, e.g. USDT-only Kaia and TRON towards Arc) and chains Rhino.fi has not enabled for deposit addresses (`DepositAddressChainsNotSupported`).

**Supported deposit networks:**

* EVM: the destination chain (Base or Arc), Base, Arbitrum, BNB Chain, Ethereum, Kaia, Polygon, Optimism
* TRON
* Solana
* Stellar

## `sdk.api.withdrawal` — Withdrawal API

| Method | Description |
| --- | --- |
| `getWithdrawalRequests()` | Get list of withdrawal requests |

## `sdk.api.baas` — BaaS Module

Banking-as-a-Service module with the following sub-services:

## `sdk.api.baas.user` — User Service

| Method | Description |
| --- | --- |
| `getUser()` | Get current user |
| `getUserV2()` | Get current user (v2) |
| `createUser(request)` | Create a new user |
| `createRetailUser(request)` | Create a retail user |
| `validateRetailUser()` | Validate retail user |
| `authorizeUser(params)` | Authorize user |
| `updatePhoneNumber(request)` | Update phone number |
| `confirmPhoneNumber(request)` | Confirm phone number via OTP |
| `uploadDocument(formData)` | Upload verification document |
| `updateFreshdeskId(request)` | Update Freshdesk ID |
| `getSharingToken(request)` | Get sharing token |
| `setSharingToken(request)` | Set sharing token |
| `getVerificationToken()` | Get verification token |
| `getVerificationLink()` | Get verification link |

## `sdk.api.baas.activity` — Activity Service

| Method | Description |
| --- | --- |
| `getFeed(request?)` | Get activity feed |
| `getById(request)` | Get activity by ID |
| `getFullStatement(request)` | Get full statement |
| `getRequestedErcWithdrawals()` | Get requested ERC withdrawals |

## `sdk.api.baas.bank` — Bank Service

| Method | Description |
| --- | --- |
| `getAccounts(request?)` | Get bank accounts |
| `activateAccount(request)` | Activate bank account |
| `estimateTransfer(request)` | Estimate bank transfer |
| `executeTransfer(request)` | Execute bank transfer |
| `estimateCorridorTransferV2(corridor, request)` | Estimate corridor transfer (v2) |
| `executeCorridorTransferV2(corridor, request)` | Execute corridor transfer (v2) |

## `sdk.api.baas.swap` — Swap Service (FX)

Circle FX stablecoin swaps. Three-step flow: `estimate` (issues a deposit address) → on-chain payment to that address (`crypto.transfer.makeTransferWithoutDelayPolicy`) → `execute`.

| Method | Description |
| --- | --- |
| `estimate(request)` | Create a swap estimation and deposit address. Send exactly one of `source_asset_amount` / `destination_asset_amount`. |
| `execute(request)` | Execute the swap after the source tokens were sent to the deposit address. |

```typescript
type SwapEstimateRequest = {
  source_asset_address: string;      // token to swap from (e.g. USDC)
  destination_asset_address: string; // token to receive (e.g. EURC)
  correlation_id?: string;
} & (
  | { source_asset_amount: string; destination_asset_amount?: never }
  | { destination_asset_amount: string; source_asset_amount?: never }
);

interface SwapEstimateResponse {
  estimation_id: string;
  destination_address: string;       // send source tokens here (preferred)
  deposit_address: string;           // @deprecated — mirrors destination_address
  source_asset_address: string;
  source_asset_amount: string;
  destination_asset_address: string;
  destination_asset_amount: string;
  trade_rate: string;
  expiration_time: string;           // RFC3339, estimation expiry
}

interface SwapExecuteRequest {
  estimation_id: string;
  payment_transaction_hash: string;  // hash of the on-chain payment
}

interface SwapExecuteResponse {
  trade_id: string;
}
```

## `sdk.api.baas.cards` — Cards Service

| Method | Description |
| --- | --- |
| `getCards(request?)` | Get user cards |
| `getCard(cardId)` | Get card details |
| `getCardTransactions(request?)` | Get card transactions |
| `issuePlasticCard(request)` | Issue a plastic card |
| `issueVirtualCard(request)` | Issue a virtual card |
| `activateCard(cardId, request)` | Activate card |
| `blockCard(cardId)` | Block card |
| `unblockCard(cardId)` | Unblock card |
| `closeCard(cardId)` | Close card |
| `getCardDetails(cardId, request)` | Get card PAN and expiry |
| `getCardCvv(cardId, request)` | Get card CVV |
| `getCardPin(cardId, request)` | Get card PIN |
| `changeCardLimit(cardId, request)` | Change card limit |
| `changeCardName(cardId, request)` | Change card name |
| `estimateCardTransfer(request)` | Estimate card transfer |
| `executeCardTransfer(request)` | Execute card transfer |
| `getActive3dsRequests()` | Get active 3DS requests |
| `approve3dsRequest(transactionId)` | Approve 3DS request |
| `decline3dsRequest(transactionId)` | Decline 3DS request |
| `getDeliveryCountries()` | Get card delivery countries |
| `getDeliveryMethods(country)` | Get card delivery methods |
| `getOrderFees(type, country)` | Get card order fees |
| `createOrderFeesInvoice(type, country, request)` | Create order fees invoice |

> **Recommended:** reveal card data to the user through the PCI Compliant SDK (skill `wirex-baas-pci-sdk`). `getCardDetails`, `getCardCvv` and `getCardPin` return raw values to your code, which is permitted only in a PCI DSS compliant environment.

Sensitive card data (PAN, CVV, PIN) requires an action token obtained via SMS OTP:

```typescript
// 1. Request SMS OTP
const session = await sdk.api.baas.confirmation.requestSms({
  action_type: 'GetCardDetails',
});

// 2. Verify OTP → receive action token (UAT code is '000000')
const tokenRes = await sdk.api.baas.confirmation.verifySms({
  session_id: session.session_id,
  code: userInputCode,
});
const actionToken = tokenRes.token;

// 3. Use action token to retrieve sensitive data
const details = await sdk.api.baas.cards.getCardDetails(cardId, { action_token: actionToken });
// → { card_number: '4111111111111111', expiry_date: '12/2028' }

const cvv = await sdk.api.baas.cards.getCardCvv(cardId, { action_token: actionToken });
// → { cvv: '123' }
```

## `sdk.api.baas.config` — Config Service

| Method | Description |
| --- | --- |
| `getConfig()` | Get client app config |

## `sdk.api.baas.confirmation` — Confirmation Service

| Method | Description |
| --- | --- |
| `verifySignature(request)` | Verify signature for action confirmation |
| `requestSms(request)` | Request SMS confirmation code |
| `verifySms(request)` | Verify SMS confirmation code |

## `sdk.api.baas.recipients` — Recipients Service

| Method | Description |
| --- | --- |
| `getRecipients(request?)` | Get all recipients |
| `getRecipientsByCatalog(request)` | Get recipients by catalog |
| `getRecipientsByCurrency(request)` | Get recipients by currency |
| `getRecipientsByName(request)` | Get recipients by name |
| `getRecipientsByType(request)` | Get recipients by type |
| `getRecipientById(recipientId)` | Get recipient by ID |
| `createRecipient(request)` | Create recipient |
| `createRecipientV2(request)` | Create recipient (v2) |
| `updateRecipient(recipientId, request)` | Update recipient |
| `deleteRecipient(recipientId)` | Delete recipient |
| `createRecipientPaymentDetails(recipientId, request)` | Create payment details |
| `updateRecipientPaymentDetails(recipientId, paymentDetailsId, request)` | Update payment details |
| `deleteRecipientPaymentDetails(recipientId, paymentDetailsId)` | Delete payment details |
| `incrementRecipientUsage(recipientId)` | Increment recipient usage counter |

## `sdk.api.baas.rates` — Rates Service

| Method | Description |
| --- | --- |
| `getRates(request)` | Get exchange rates |

## `sdk.api.baas.token` — Token Service

| Method | Description |
| --- | --- |
| `getToken(request)` | Get OAuth2 token |

## `sdk.api.baas.wallet` — Wallet Service

| Method | Description |
| --- | --- |
| `getWallet(request?)` | Get wallet by ID or default |
| `getWallets()` | Get all wallets |
| `createGlobalWallet(request)` | Create global wallet |

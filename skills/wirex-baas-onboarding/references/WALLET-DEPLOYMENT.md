# Wallet Deployment Reference

## Architecture Overview

Wirex BaaS wallets are Account Abstraction smart wallets built on the **Kernel v3.1 Smart Account** framework, deployed on Base and registered in the Wirex Accounts contract. Before calling the Wirex API to register a user: (1) the Smart Wallet must be deployed, (2) the required policy and executor must be installed, (3) the wallet must be registered in the Accounts smart contract. The Wirex API validates that wallets are registered before accepting API registration requests.

| Component | Role | Description |
|-----------|------|-------------|
| **Kernel v3.1 Smart Account** | Wallet | Controlled by the user's EOA as signer; modular (validators, executors, policies); gas sponsorship via paymasters; batched transactions |
| **FundsManagement Executor** | Fund operations | Executor module (module type 2). Grants the Wirex oracle permission to execute specific predefined operations (card payments, withdrawals, card top-ups, fiat withdrawals). The oracle cannot arbitrarily move funds |
| **ExecutionDelayPolicy** | Security | Policy installed as the **root validator** (via `changeRootValidator`). Enforces a time delay on sensitive operations, lets the user cancel pending transactions within the delay window. Mandatory for all Wirex wallets |
| **Accounts contract registration** | Registry | Links the Smart Wallet to your `parentEntity` (`partner_id`, 16-byte / `bytes16`), lets Wirex associate the wallet with a user, records account and verification status on-chain |

The **EOA (Externally Owned Account)** is the signer/owner. The `user_address` sent to `POST /api/v2/user` is this EOA, not the Smart Wallet address.

---

## Deployment Options

| Option | Description |
|--------|-------------|
| **Wirex SDK** (Recommended) | `@wirexapp/wpay-baas-sdk`; abstracts deployment and configuration |
| **Direct Deployment (EVM)** | ZeroDev SDK for Kernel v3.1 wallets on Base |
| **Direct Deployment (Stellar)** | Crossmint SDK for Stellar smart wallets |

### Option 1: Wirex SDK (`@wirexapp/wpay-baas-sdk`)

Requires Node.js >= 18 and `viem ^2.49.3` (peer dependency).

```bash
npm install @wirexapp/wpay-baas-sdk viem
```

```typescript
import { createSDK } from '@wirexapp/wpay-baas-sdk';

const sdk = await createSDK({
  env: 'prod', // 'dev' | 'prod'; chain follows `chainId` or the remote config `defaultChain`
  companyId: process.env.COMPANY_ID, // your partner_id (hex) from Wirex onboarding
  enableLogging: true, // optional
  getMainWalletClient: async () => mainWalletClient, // user's EOA wallet client (Privy, WalletConnect, raw key adapter, ...)
});
```

`getMainWalletClient` must return an object with `address` and `getEthereumProvider()`; the EIP-1193 provider must handle at least `eth_accounts`, `personal_sign` and `eth_signTypedData_v4`.

> **Docs inconsistency:** the Wallet Deployment guide shows `env: 'production' | 'sandbox'`; the TypeScript SDK reference documents `env: 'dev' | 'prod'` (used here).

#### SDK Methods

| Module | Method | Purpose |
|--------|--------|---------|
| `sdk.crypto.wallet` | `getSmartWalletAddress()` | Get the Smart Wallet address |
| `sdk.crypto.wallet` | `getSmartWalletClient()` | Get Kernel account client |
| `sdk.crypto.accountAbstraction` | `isPolicyInstalled()` | Check if ExecutionDelayPolicy is installed (as root validator) |
| `sdk.crypto.accountAbstraction` | `isExecutorInstalled()` | Check if FundsManagement Executor is installed |
| `sdk.crypto.accountAbstraction` | `signInPolicyAndExecutor()` | Install both in one UserOperation |
| `sdk.crypto.accountAbstraction` | `signInPolicy()` | Install policy only |
| `sdk.crypto.accountAbstraction` | `signInExecutor()` | Install executor only |
| `sdk.crypto.accountContract` | `isWalletInAccounts()` | Check registration in the retail Accounts contract |
| `sdk.crypto.accountContract` | `registerInAccounts()` | Register wallet (retail) |
| `sdk.crypto.onboarding` | `allInOneStepOnboarding()` | Executor install + policy switch + Accounts registration in one UserOperation (one signature); only when neither module is installed |

#### Deployment Flow

```typescript
// 1. Check module state
const policyInstalled = await sdk.crypto.accountAbstraction.isPolicyInstalled();
const executorInstalled = await sdk.crypto.accountAbstraction.isExecutorInstalled();

// 2a. Fresh wallet: everything in one UserOperation, the user signs once
if (!policyInstalled && !executorInstalled) {
  await sdk.crypto.onboarding.allInOneStepOnboarding(); // also registers in Accounts
}
// 2b. Otherwise install the missing modules
else if (!policyInstalled || !executorInstalled) {
  await sdk.crypto.accountAbstraction.signInPolicyAndExecutor();
}

// 3. Register in Accounts contract
const isRegistered = await sdk.crypto.accountContract.isWalletInAccounts();
if (!isRegistered) {
  await sdk.crypto.accountContract.registerInAccounts();
}
```

Then wait for the `/v2/webhooks/wallets` webhook and call `POST /api/v2/user`.

---

### Option 2: ZeroDev SDK (EVM)

```bash
npm install @zerodev/sdk @zerodev/ecdsa-validator @zerodev/permissions viem
```

Wirex provides during onboarding:

| Configuration | Description |
|---------------|-------------|
| `bundlerRpc` | ZeroDev bundler endpoint |
| `paymasterRpc` | ZeroDev paymaster endpoint for gas sponsorship |
| `rpcUrl` | Blockchain RPC endpoint |
| `contractRegistryAddress` | Address used to resolve all other contract addresses |
| `partnerId` | Your 16-byte on-chain identifier |

Key points (condensed from the Wallet Deployment guide; see the ABI Reference for ABIs):

1. **Resolve contracts** from the ContractRegistry with `contractByName(name)` for `Accounts`, `FundsManagement`, `ExecutionDelayPolicy`.
2. **Create the Kernel account** with `createKernelAccount` (`kernelVersion: KERNEL_V3_1`, EntryPoint 0.7) using an ECDSA validator (`signerToEcdsaValidator`) as `sudo` for the initial deployment; use a paymaster client for gas sponsorship.
3. **Build three batched calls** and send them as **one UserOperation**:
   - `changeRootValidator(rootValidatorId, zeroAddress, enableData, '0x')` on the Kernel account -- installs ExecutionDelayPolicy as root validator (a permission validator with `toSudoPolicy({ policyAddress: executionDelayPolicy })`; `rootValidatorId = VALIDATOR_TYPE.PERMISSION` + identifier padded to 20 bytes);
   - `installModule(2, fundsManagementAddress, concatHex([zeroAddress, zeroHash]))` on the Kernel account -- installs the executor (module type 2);
   - `createUserAccountWithWallet(partnerId)` on the Accounts contract.
4. **Subsequent operations** use a client built with the policy validator (`toPermissionValidator` with the ExecutionDelayPolicy, `address` set to the policy address) pointing at the existing wallet address; the initial deployment uses the plain ECDSA validator.

---

### Option 3: Crossmint SDK (Stellar)

Stellar smart wallets use Crossmint's smart wallet infrastructure. Contact Wirex for Stellar-specific integration documentation and contract addresses.

1. Initialize the Crossmint wallet via `@crossmint/client-sdk-react-ui`.
2. Install the execution delay plugin on the smart wallet.
3. Register in the Accounts contract with your `partner_id`.

| Configuration from Wirex | Description |
|--------------------------|-------------|
| Crossmint API Key | For wallet initialization |
| Plugin Contract ID | Execution delay policy address |
| Accounts Contract ID | For user registration |
| Partner ID | 16-byte identifier (without `0x` prefix for Stellar) |

---

## Contract Addresses

Contract addresses differ per chain and environment (Sandbox/Production). Contact Wirex during onboarding for: **Accounts** (user registration), **FundsManagement** (executor for oracle transactions), **ExecutionDelayPolicy** (time-lock policy), **TokensRegistry** (supported token list). ContractRegistry addresses are in the Platform Overview.

---

## On-Chain Flow Sequence

| Step | Action | Description |
|------|--------|-------------|
| 1 | **Create signer** | From Privy, a private key, or WalletConnect |
| 2 | **Deploy Smart Wallet** | Single UserOperation with batched calls |
| 3 | **Install executor** | `installModule` (FundsManagement, module type 2) |
| 4 | **Install policy** | `changeRootValidator` (ExecutionDelayPolicy as root validator) |
| 5 | **Register on-chain** | `createUserAccountWithWallet(partnerId)` in the Accounts contract |
| 6 | **Event emitted** | Wirex listener detects `UserAccountCreated(parentEntity, owner)` |
| 7 | **Wirex verifies** | Backend checks the modules are installed and creates its internal record |
| 8 | **Webhook sent** | You receive the wallet confirmation at `/v2/webhooks/wallets` |

> With the ZeroDev flow, steps 2-5 are one batched UserOperation; with the Wirex SDK, `signInPolicyAndExecutor()` installs both modules in one UserOperation and `registerInAccounts()` registers separately.

---

## Wallet Webhook

When a wallet is registered on-chain, Wirex sends a webhook to your configured endpoint:

```
POST {your_webhook_base_url}/v2/webhooks/wallets
```

### Webhook Payload

```json
{
  "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "wallet_name": "Main Wallet",
  "wallet_status": "Confirmed",
  "wallet_type": "Primary",
  "balances": []
}
```

### Webhook Fields

| Field | Type | Description |
|-------|------|-------------|
| `wallet_address` | string | Smart Wallet address (0x-prefixed hex) |
| `wallet_name` | string | Display name for wallet |
| `wallet_status` | string | `Confirmed`, `Rejected`, or `Unknown` |
| `wallet_type` | string | `Primary`, `Secondary`, `Global`, or `Card` |
| `balances` | array | Token balances (empty in wallet creation webhook) |

### Wallet Status Values

| Status | Meaning |
|--------|---------|
| `Confirmed` | Wallet is properly configured as a Smart Wallet with required modules |
| `Rejected` | Wallet configuration is invalid or incomplete |
| `Unknown` | Status could not be determined |

### Webhook Handling Rules

- Wirex expects a **2xx response within 10 seconds**
- A failed delivery is retried up to 5 times with exponential backoff, then dropped; retries can arrive out of order and more than once
- Implement idempotent handlers for duplicate events
- Contact Wirex support for event replay

---

## Verification

If your application does not persist Smart Wallet setup state, use on-chain read calls to determine whether the wallet was created, modules installed and registration completed.

```typescript
import { KernelV3_1AccountAbi } from '@zerodev/sdk';
import { AccountsAbi } from './abi'; // see the ABI Reference

async function verifyWalletSetup(publicClient, smartWalletAddress, contracts, partnerId) {
  // 1. Executor installed? (moduleType 2 = Executor)
  const isExecutorInstalled = await publicClient.readContract({
    address: smartWalletAddress,
    abi: KernelV3_1AccountAbi,
    functionName: 'isModuleInstalled',
    args: [BigInt(2), contracts.fundsManagement, '0x'],
  });

  // 2. Policy installed? (root validator set)
  const rootValidator = await publicClient.readContract({
    address: smartWalletAddress,
    abi: KernelV3_1AccountAbi,
    functionName: 'rootValidator',
  });
  const isPolicyInstalled = !!rootValidator && rootValidator !== '0x';

  // 3. Registered in the Accounts contract?
  try {
    const account = await publicClient.readContract({
      address: contracts.accounts,
      abi: AccountsAbi,
      functionName: 'getUserAccount',
      args: [smartWalletAddress, partnerId], // (owner, parentEntity)
    });
    const isRegistered = account && account.status !== 0;
    return { isExecutorInstalled, isPolicyInstalled, isRegistered };
  } catch {
    return { isExecutorInstalled, isPolicyInstalled, isRegistered: false };
  }
}
```

`getUserAccount(owner, parentEntity)` returns a tuple `(status, verificationStatus)`.

| `status` | Meaning | `verificationStatus` | Meaning |
|----------|---------|----------------------|---------|
| 0 | None (not registered) | 0 | None |
| 1 | Pending | 1 | Applied |
| 2 | Active | 2 | InReview |
| 3 | Blocked | 3 | Approved |
| 4 | Deleted | 4 | Rejected |

The Accounts ABI also exposes `getWallet(parentEntity, wallet)` returning `(confirmationStatus, owner)`.


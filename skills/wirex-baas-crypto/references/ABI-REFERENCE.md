# Wirex BaaS Crypto — Smart Contract ABI Reference

This document provides ABI details for the core smart contracts used in the Wirex BaaS platform on Base chain. Use these ABIs for direct on-chain integration or for decoding transaction data.

## Table of Contents

- [ContractRegistry](#contractregistry)
- [Accounts](#accounts)
- [TokensRegistry](#tokensregistry)
- [Kernel v3.1](#kernel-v31)
- [ERC20 Standard](#erc20-standard)

---

## ContractRegistry

The `ContractRegistry` contract resolves contract addresses dynamically. You receive the registry address from Wirex during onboarding and use it to look up all other contract addresses. Addresses differ per chain and environment.

### contractByName

Retrieve a contract's proxy address by its registered name.

```solidity
function contractByName(string memory name) external view returns (address proxy)
```

**Parameters:**

| Name | Type   | Description                              |
|------|--------|------------------------------------------|
| name | string | Registered contract name (e.g., "Accounts", "TokensRegistry") |

**Returns:**

| Name  | Type    | Description                |
|-------|---------|----------------------------|
| proxy | address | Proxy address of the contract |

**Example usage (ethers.js):**

```typescript
const registryAbi = [
  "function contractByName(string memory name) external view returns (address)",
  "function contracts() external view returns (tuple(string name, address proxy)[])"
];

const registry = new ethers.Contract(registryAddress, registryAbi, provider);

// Get the Accounts contract address
const accountsAddress = await registry.contractByName("Accounts");
console.log("Accounts contract:", accountsAddress);
```

### contracts

Retrieve all registered contracts as an array of (name, proxy) tuples.

```solidity
function contracts() external view returns (tuple(string name, address proxy)[] memory)
```

**Returns:**

An array of tuples, each containing:

| Field | Type    | Description              |
|-------|---------|--------------------------|
| name  | string  | Registered contract name |
| proxy | address | Proxy address            |

**Example usage:**

```typescript
const allContracts = await registry.contracts();
for (const { name, proxy } of allContracts) {
  console.log(`${name}: ${proxy}`);
}
// Output:
// Accounts: 0x...
// TokensRegistry: 0x...
// ExecutionDelayPolicy: 0x...
// ...
```

### Contract Names

Use these names with `contractByName()`:

| Name                   | Purpose                                 |
|------------------------|-----------------------------------------|
| `Accounts`             | User registration                       |
| `FundsManagement`      | Executor module for oracle transactions |
| `ExecutionDelayPolicy` | Time-lock policy for wallets            |
| `TokensRegistry`       | Supported token list                    |

---

## Accounts

Used for user registration. The Smart Wallet calls `createUserAccountWithWallet` to register with Wirex under a parent entity (the BaaS partner).

### createUserAccountWithWallet

Register the calling Smart Wallet as a user account under a parent entity. No return value.

```solidity
function createUserAccountWithWallet(bytes16 parentEntity) external
```

**Parameters:**

| Name         | Type    | Description                                  |
|-------------|---------|----------------------------------------------|
| parentEntity | bytes16 | Your `partner_id` (16-byte hex)               |

### getUserAccount

Retrieve a user account by the owner's address and parent entity.

```solidity
function getUserAccount(address owner, bytes16 parentEntity) external view returns (
  tuple(uint8 status, uint8 verificationStatus)
)
```

**Parameters:**

| Name         | Type    | Description                       |
|-------------|---------|-----------------------------------|
| owner        | address | The EOA owner of the account      |
| parentEntity | bytes16 | The BaaS partner's entity ID      |

**Returns:**

| Name               | Type    | Description                           |
|-------------------|---------|---------------------------------------|
| status             | uint8   | Account status code (see table below) |
| verificationStatus | uint8   | KYC verification code (see table below) |

### getWallet

Retrieve wallet information for a specific account under a parent entity.

```solidity
function getWallet(bytes16 parentEntity, address wallet) external view returns (
  tuple(uint8 confirmationStatus, address owner)
)
```

**Parameters:**

| Name         | Type    | Description                       |
|-------------|---------|-----------------------------------|
| parentEntity | bytes16 | The BaaS partner's entity ID      |
| wallet       | address | The wallet address to look up     |

**Returns:**

| Name               | Type    | Description                           |
|-------------------|---------|---------------------------------------|
| confirmationStatus | uint8   | Wallet confirmation status (value meanings are not documented) |
| owner              | address | The owner of the wallet               |

### UserAccountCreated Event

Emitted when a new user account is created.

```solidity
event UserAccountCreated(
  bytes16 parentEntity,
  address owner
)
```

**Event Fields:**

| Field        | Type    | Indexed | Description                           |
|-------------|---------|---------|---------------------------------------|
| parentEntity | bytes16 | No      | The BaaS partner's entity ID          |
| owner        | address | No      | The owner of the new account          |

### Account Status Codes

| Code | Name                  |
|------|-----------------------|
| 0    | None (not registered) |
| 1    | Pending               |
| 2    | Active                |
| 3    | Blocked               |
| 4    | Deleted               |

### Verification Status Codes

| Code | Name     |
|------|----------|
| 0    | None     |
| 1    | Applied  |
| 2    | InReview |
| 3    | Approved |
| 4    | Rejected |

### Full ABI Fragment

```json
[
  {
    "inputs": [{ "name": "parentEntity", "type": "bytes16" }],
    "name": "createUserAccountWithWallet",
    "outputs": [],
    "type": "function"
  },
  {
    "inputs": [
      { "name": "owner", "type": "address" },
      { "name": "parentEntity", "type": "bytes16" }
    ],
    "name": "getUserAccount",
    "outputs": [
      {
        "components": [
          { "name": "status", "type": "uint8" },
          { "name": "verificationStatus", "type": "uint8" }
        ],
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "parentEntity", "type": "bytes16" },
      { "name": "wallet", "type": "address" }
    ],
    "name": "getWallet",
    "outputs": [
      {
        "components": [
          { "name": "confirmationStatus", "type": "uint8" },
          { "name": "owner", "type": "address" }
        ],
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "anonymous": false,
    "inputs": [
      { "indexed": false, "name": "parentEntity", "type": "bytes16" },
      { "indexed": false, "name": "owner", "type": "address" }
    ],
    "name": "UserAccountCreated",
    "type": "event"
  }
]
```

---

## TokensRegistry

The `TokensRegistry` contract maintains the list of all supported tokens on the platform.

### retrieveAllTokensV2

Retrieve all registered tokens (the supported token list) with their metadata.

```solidity
function retrieveAllTokensV2() external view returns (
  tuple(address tokenAddress, string symbol, string name, uint8 decimals, bool isActive)[] memory
)
```

**Returns:**

An array of tuples, each containing:

| Field        | Type    | Description                              |
|-------------|---------|------------------------------------------|
| tokenAddress | address | The token's contract address             |
| symbol       | string  | Token symbol (e.g., "WUSD", "USDC")     |
| name         | string  | Full token name                          |
| decimals     | uint8   | Number of decimals (6 for USDC, 18 for WUSD) |
| isActive     | bool    | Whether the token is currently active    |

**Example usage:**

```typescript
const tokensRegistryAbi = [
  "function retrieveAllTokensV2() external view returns (tuple(address tokenAddress, string symbol, string name, uint8 decimals, bool isActive)[])",
  "function getToken(address tokenAddress) external view returns (tuple(address tokenAddress, string symbol, string name, uint8 decimals, bool isActive))"
];

const tokensRegistry = new ethers.Contract(tokensRegistryAddress, tokensRegistryAbi, provider);

const allTokens = await tokensRegistry.retrieveAllTokensV2();
for (const token of allTokens) {
  console.log(`${token.symbol} (${token.tokenAddress}): ${token.decimals} decimals, active=${token.isActive}`);
}
```

### getToken

Retrieve metadata for a single token by its address.

```solidity
function getToken(address tokenAddress) external view returns (
  tuple(address tokenAddress, string symbol, string name, uint8 decimals, bool isActive) memory
)
```

**Parameters:**

| Name         | Type    | Description                    |
|-------------|---------|--------------------------------|
| tokenAddress | address | The token's contract address   |

**Returns:**

Same tuple structure as `retrieveAllTokensV2` for a single token.

### Full ABI Fragment

```json
[
  {
    "inputs": [],
    "name": "retrieveAllTokensV2",
    "outputs": [
      {
        "components": [
          { "name": "tokenAddress", "type": "address" },
          { "name": "symbol", "type": "string" },
          { "name": "name", "type": "string" },
          { "name": "decimals", "type": "uint8" },
          { "name": "isActive", "type": "bool" }
        ],
        "name": "",
        "type": "tuple[]"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [{ "name": "tokenAddress", "type": "address" }],
    "name": "getToken",
    "outputs": [
      {
        "components": [
          { "name": "tokenAddress", "type": "address" },
          { "name": "symbol", "type": "string" },
          { "name": "name", "type": "string" },
          { "name": "decimals", "type": "uint8" },
          { "name": "isActive", "type": "bool" }
        ],
        "name": "",
        "type": "tuple"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  }
]
```

---

## Kernel v3.1

The Kernel account ABI is provided by the ZeroDev SDK (`KernelV3_1AccountAbi` from `@zerodev/sdk`); for the complete ABI see the ZeroDev SDK documentation. Key functions used for Smart Wallet setup (module installation, policy as root validator) are listed below. The Wirex docs show only function names and argument names; the Solidity types and mutability below are taken from the ZeroDev Kernel v3.1 ABI, not from the Wirex docs.

### installModule

Install a module on the smart account (e.g. the executor module).

```solidity
function installModule(
  uint256 moduleType,
  address moduleAddress,
  bytes calldata initData
) external
```

**Parameters:**

| Name          | Type    | Description                                    |
|--------------|---------|------------------------------------------------|
| moduleType    | uint256 | Module type: 1=Validator, 2=Executor            |
| moduleAddress | address | Address of the module contract to install       |
| initData      | bytes   | Initialization data for the module              |

**Module Types:**

| Value | Type      | Description                                    |
|-------|-----------|------------------------------------------------|
| 1     | Validator | Validates user operations (signatures)         |
| 2     | Executor  | Executes actions on behalf of the account      |

### changeRootValidator

Change the root validator of the smart account. The root validator is the primary signature validation module.

```solidity
function changeRootValidator(
  bytes21 validatorId,
  address hook,
  bytes calldata validatorData,
  bytes calldata hookData
) external
```

**Parameters:**

| Name          | Type    | Description                                    |
|--------------|---------|------------------------------------------------|
| validatorId   | bytes21 | Identifier of the new root validator module     |
| hook          | address | Hook address to attach (address(0) for none)    |
| validatorData | bytes   | Configuration data for the validator            |
| hookData      | bytes   | Configuration data for the hook                 |

### isModuleInstalled

Check whether a specific module is installed on the account.

```solidity
function isModuleInstalled(
  uint256 moduleType,
  address moduleAddress,
  bytes calldata additionalContext // docs example passes '0x'
) external view returns (bool)
```

**Parameters:**

| Name          | Type    | Description                    |
|--------------|---------|--------------------------------|
| moduleType    | uint256 | Module type (1=Validator, 2=Executor) |
| moduleAddress | address | Address of the module contract |
| additionalContext | bytes | Pass `0x`                    |

**Returns:**

| Type | Description                         |
|------|-------------------------------------|
| bool | `true` if the module is installed   |

### rootValidator

Get the current root validator of the smart account.

```solidity
function rootValidator() external view returns (bytes21)
```

**Returns:**

| Type    | Description                              |
|---------|------------------------------------------|
| bytes21 | The identifier of the current root validator |

### Full ABI Fragment

```json
[
  {
    "inputs": [
      { "name": "moduleType", "type": "uint256" },
      { "name": "moduleAddress", "type": "address" },
      { "name": "initData", "type": "bytes" }
    ],
    "name": "installModule",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "validatorId", "type": "bytes21" },
      { "name": "hook", "type": "address" },
      { "name": "validatorData", "type": "bytes" },
      { "name": "hookData", "type": "bytes" }
    ],
    "name": "changeRootValidator",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "moduleType", "type": "uint256" },
      { "name": "moduleAddress", "type": "address" },
      { "name": "additionalContext", "type": "bytes" }
    ],
    "name": "isModuleInstalled",
    "outputs": [{ "name": "", "type": "bool" }],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "rootValidator",
    "outputs": [{ "name": "", "type": "bytes21" }],
    "stateMutability": "view",
    "type": "function"
  }
]
```

---

## ERC20 Standard

Standard ERC20 functions used for token interactions on the platform. These apply to WUSD, WEUR, USDC, USDT, and EURC.

### balanceOf

```solidity
function balanceOf(address account) external view returns (uint256)
```

Returns the token balance of the specified account.

### transfer

```solidity
function transfer(address to, uint256 amount) external returns (bool)
```

Transfer tokens from the caller to the specified address.

### approve

```solidity
function approve(address spender, uint256 amount) external returns (bool)
```

Approve a spender to transfer up to `amount` tokens on behalf of the caller.

### allowance

```solidity
function allowance(address owner, address spender) external view returns (uint256)
```

Returns the remaining number of tokens that `spender` is allowed to transfer on behalf of `owner`.

### decimals

```solidity
function decimals() external view returns (uint8)
```

Returns the number of decimals the token uses.

### symbol

```solidity
function symbol() external view returns (string memory)
```

Returns the token symbol.

### Full ABI Fragment

```json
[
  {
    "inputs": [{ "name": "account", "type": "address" }],
    "name": "balanceOf",
    "outputs": [{ "name": "", "type": "uint256" }],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "to", "type": "address" },
      { "name": "amount", "type": "uint256" }
    ],
    "name": "transfer",
    "outputs": [{ "name": "", "type": "bool" }],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "spender", "type": "address" },
      { "name": "amount", "type": "uint256" }
    ],
    "name": "approve",
    "outputs": [{ "name": "", "type": "bool" }],
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "inputs": [
      { "name": "owner", "type": "address" },
      { "name": "spender", "type": "address" }
    ],
    "name": "allowance",
    "outputs": [{ "name": "", "type": "uint256" }],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "decimals",
    "outputs": [{ "name": "", "type": "uint8" }],
    "stateMutability": "view",
    "type": "function"
  },
  {
    "inputs": [],
    "name": "symbol",
    "outputs": [{ "name": "", "type": "string" }],
    "stateMutability": "view",
    "type": "function"
  }
]
```

# Wirex BaaS Agent Skills

Agent skills for **Wirex BaaS** — a blockchain financial services platform providing Account Abstraction wallets, KYC verification, Visa card issuance, crypto asset management, and fiat banking (SEPA/ACH) via REST APIs.

You MUST read the SKILL.md file whenever the description of the skills below matches the user intent.

## Available Skills

### wirex-baas-overview
Platform overview and getting started guide — start here for integration basics. Covers what Wirex BaaS is, the 6-step integration flow, partner onboarding, API environments (sandbox and production URLs), sandbox test credentials, required headers, error handling, blockchain networks, token and contract addresses, MCP server setup, and supported countries.
- [SKILL.md](../skills/wirex-baas-overview/SKILL.md)

### wirex-baas-auth
Authentication — how to authenticate API requests. Server-to-Server OAuth2 token exchange, user-scoped token issuance, Privy-based authentication, action tokens and the X-User-Wallet identity header. Covers required headers, token caching strategy, and security best practices.
- [SKILL.md](../skills/wirex-baas-auth/SKILL.md)

### wirex-baas-onboarding
User onboarding — create users, deploy wallets, verify identity. Covers user registration, smart wallet deployment (ERC-4337 Account Abstraction), three KYC verification flows, user profile and capabilities, phone confirmation, and document upload.
- [SKILL.md](../skills/wirex-baas-onboarding/SKILL.md)

### wirex-baas-crypto
Crypto asset management — check balances, deposit crypto, withdraw tokens. Covers wallet balance queries, unified balance model (WUSD/WEUR on Base), multi-chain deposits via Rhino.fi, ERC20 on-chain withdrawals, and smart contract ABI reference.
- [SKILL.md](../skills/wirex-baas-crypto/SKILL.md)

### wirex-baas-cards
Visa card issuance and management — issue cards, retrieve sensitive details, manage limits, process 3DS. Covers virtual card creation, PCI-compliant card details retrieval, spending limits, card transactions, and 3D Secure authentication.
- [SKILL.md](../skills/wirex-baas-cards/SKILL.md)

### wirex-baas-transfers
Money transfers — send money to bank accounts and cards. Covers SEPA transfers (EUR), ACH transfers (USD), Push-to-Card payouts, and recipient management. All transfers follow the estimate-then-execute pattern.
- [SKILL.md](../skills/wirex-baas-transfers/SKILL.md)

### wirex-baas-webhooks
Webhooks and activity history — receive real-time event notifications and query transaction history. Covers all v2 webhook endpoints, v1 legacy webhooks, delivery specs, and the activity history feed.
- [SKILL.md](../skills/wirex-baas-webhooks/SKILL.md)

### wirex-baas-sandbox
Sandbox testing — simulate real-world scenarios in the development environment. Helper API for minting test tokens, simulating SEPA/ACH transactions, and card transactions (POS/EPOS/ATM/credit). Includes sandbox test credentials and token addresses.
- [SKILL.md](../skills/wirex-baas-sandbox/SKILL.md)

---
name: wirex-baas-onboarding
description: "Wirex BaaS user onboarding — create users, deploy wallets, verify identity. Covers user registration (POST /api/v2/user), smart wallet deployment (ERC-4337 Account Abstraction), three KYC verification flows (Wirex Hosted, SumSub Shared, KYC Sharing via API), user profile and capabilities (GET /api/v2/user), phone confirmation, and document upload."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Onboarding Skill

## Overview

Wirex BaaS onboarding is a **three-step process** that takes a user from zero state to a fully verified participant with access to crypto, card, and banking services. Before starting, check whether the user already exists (Step 0).

| Step | Action | Outcome |
|------|--------|---------|
| 1 | **Wallet Deployment** | Smart wallet deployed on Base with Kernel v3.1, executor and policy modules, then registered in the Wirex Accounts contract |
| 2 | **User Registration** | User record created in Wirex backend via `POST /api/v2/user` |
| 3 | **KYC Verification** | Identity verified through one of three flows; unlocks card and banking capabilities |

---

## Step 0: Check Whether the User Already Exists

```
POST /api/v1/user/retail/validate
```

Empty body; the user is identified from the access token and identity headers (Privy credentials). Works on the Privy and Crossmint paths only; with an S2S token call `GET /api/v2/user` instead. Response: `{ "users": [ { "id", "user_id", "email", "wallet_address", "user_address" } ] }`. `users` is a **list** and is **`null`, not an empty array, when the credentials are not registered** -- proceed to Step 1. A non-empty list means "already onboarded": route to login, do not run onboarding again. `id`/`wallet_address` are deprecated mirrors of `user_id`/`user_address`.

---

## Step 1: Smart Wallet Deployment

The wallet is an Account Abstraction smart wallet built on **Kernel v3.1**, controlled by the user's EOA as signer. It must be deployed, have both modules installed, and be registered in the Wirex **Accounts** contract (`createUserAccountWithWallet(partnerId)`) **before** `POST /api/v2/user` is called -- the API validates that the wallet is registered (otherwise `ErrorNotFound`).

- **FundsManagement Executor** -- grants the Wirex oracle permission to execute predefined operations on behalf of the wallet (card payments, withdrawals, top-ups); the oracle cannot arbitrarily move funds.
- **ExecutionDelayPolicy** -- installed as the **root validator**; enforces a time delay on sensitive operations, lets the user cancel pending transactions within the delay window. Mandatory for all Wirex wallets.

Deployment options:

| Option | Chain | Notes |
|--------|-------|-------|
| **Wirex SDK** (`@wirexapp/wpay-baas-sdk`) | EVM | Recommended; abstracts deployment and configuration |
| **ZeroDev SDK** (direct) | EVM (Base) | Kernel v3.1; config (`bundlerRpc`, `paymasterRpc`, `rpcUrl`, `contractRegistryAddress`, `partnerId`) is provided by Wirex |
| **Crossmint SDK** (direct) | Stellar | Contact Wirex for Stellar-specific docs and contract addresses |

After on-chain registration, Wirex detects the `UserAccountCreated` event, verifies the wallet and sends a webhook to `POST {your_webhook_base_url}/v2/webhooks/wallets`.

See [WALLET-DEPLOYMENT.md](references/WALLET-DEPLOYMENT.md) for the full deployment guide.

---

## Step 2: User Registration

> **WARNING:** `user_address` must be the user's **EOA address** (signer), NOT the Smart Wallet address. `user_address` replaces the former `wallet_address`; both are still accepted (if both are sent they must match). New integrations should send `user_address`.

### Standard Registration (S2S)

```
POST /api/v2/user
```

**Required headers:** `Authorization: Bearer {s2s_token}`, `Content-Type: application/json`, `X-Chain-Id: {chainId}`. User identity headers are not needed for this endpoint.

> **IMPORTANT:** `sharing_data` and `initial_data` are **mutually exclusive** — do not provide both in the same request.

> **Docs inconsistency:** the API reference schema marks `initial_data.is_pep`, all `profile` fields and `residence_address` city/country/line1/post_code as required, while the Hosted KYC guide registers with only email + country. The Hosted example below follows the guide. Always send `residence_address.country`: capabilities and the verification token depend on it, and it cannot be added afterwards.

#### Hosted KYC Request

```json
{
  "user_address": "0xAbC123...EOA",
  "initial_data": {
    "profile": {
      "email": "user@example.com"
    },
    "residence_address": {
      "country": "GB"
    }
  }
}
```

#### SumSub Shared KYC Request

> Requires prior approval from Wirex (3-sided data sharing agreement with SumSub).

```json
{
  "user_address": "0xAbC123...EOA",
  "sharing_data": {
    "sharing_token": "eyJhbGciOi...",
    "email": "user@example.com"
  }
}
```

Phone number from SumSub verification is **automatically confirmed** (no manual phone confirmation needed).

#### KYC Sharing via API Request

> Only available under the Enterprise model, after a detailed Wirex audit; may be rejected.

```json
{
  "user_address": "0xAbC123...EOA",
  "initial_data": {
    "profile": {
      "first_name": "Jane",
      "last_name": "Doe",
      "date_of_birth": "1990-01-15",
      "nationality": "GB",
      "email": "user@example.com",
      "phone_number": "+447700900123"
    },
    "residence_address": {
      "line1": "10 Downing Street",
      "line2": "",
      "city": "London",
      "state": "England",
      "post_code": "SW1A 2AA",
      "country": "GB"
    }
  }
}
```

The phone number provided during KYC sharing via API is **automatically confirmed**. After registration, upload documents via `POST /api/v1/user/documents` (see [KYC-FLOWS.md](references/KYC-FLOWS.md)).

#### Response

```json
{
  "id": "user-uuid"
}
```

### Privy Registration

For partners using Privy authentication (client-side). Headers: `Authorization: Bearer {privy_access_token}`, `Identity: Bearer {privy_identity_token}`, `X-Chain-Id`. The registered Privy user must have a linked email and a linked or embedded wallet.

```
POST /api/v1/user/retail
```

```json
{
  "country": "GB"
}
```

`country` is the ISO 3166-1 alpha-2 residence country (optional; omitted, it defaults to the country of the caller's IP address; the email and wallet come from the Privy identity token, not the body); optional `referrer_address` is the EOA of the referring user. Response: `{ "id": "..." }`. Afterwards exchange the Privy tokens for a Wirex user token (`POST /api/v1/user/authorize`).

---

## Step 3: KYC Verification

Three KYC flows are available, each suited to different integration depths. Wirex supports **only one verification flow at a time**; changing the configured flow may affect users already verified or in verification.

### KYC Flow Comparison

| Aspect | Hosted | SumSub Shared | Reliance |
|--------|--------|---------------|----------|
| **Complexity** | Low | Medium | High |
| **UI Ownership** | Hosted SumSub widget or SumSub SDK in partner app | None needed (user already verified in SumSub) | Fully partner-owned |
| **Data Collection** | Wirex collects all data | Partner's SumSub applicant is shared via token | Partner collects and submits |
| **Registration Fields** | `initial_data.profile.email` + `initial_data.residence_address.country` | `sharing_data.sharing_token` + `sharing_data.email` | Full `initial_data` (profile + residence_address) + documents |
| **Approval** | None | Wirex audit + 3-sided agreement | Wirex audit, Enterprise model |
| **Partner Effort** | Redirect user to URL or embed SumSub SDK | Generate SumSub share token | Do full KYC yourself, upload docs |
| **Best For** | Partners without existing KYC infrastructure | Partners already using SumSub | Partners with established KYC processes |

### Verification Statuses

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `None` | No verification submitted | Begin KYC flow |
| `Applied` | User has unfinished steps in the SumSub SDK, or incomplete data was provided in Shared / KYC-sharing-via-API flows | Finish the steps / supply missing data |
| `Pending` | Verification checks being executed on Wirex side | Wait |
| `InReview` | Verification checks being executed on Wirex side | Wait |
| `Approved` | Verification approved | Full access granted |
| `Canceled` | Verification cancelled (spelled with one `l`) | Contact Wirex support |
| `Rejected` | Verification rejected | Contact Wirex support |

### KYC Completion Endpoints

After registration, direct the user to complete KYC:

| Endpoint | Returns | Use Case |
|----------|---------|----------|
| `POST /api/v1/user/verification-link` | `{ "redirect_uri": "..." }` | Redirect user to the hosted SumSub widget |
| `POST /api/v1/user/verification-token` | `{ "token": "..." }` | Initialize the SumSub Web/Mobile SDK in-app |

Both are **POST** and accept an optional body `{ "verification_level": "SDD" }` (enum `N/A`, `BDD`, `SDD`, `XDDBridgeBase`, `EDD`). Omitted or unrecognised, the level falls back to `SDD` without an error; `XDDBridgeBase` (SDD + tax identification number) is required for ACH accounts. The SDK methods `getVerificationToken()` / `getVerificationLink()` send an empty body, so they always run at `SDD`; call the REST endpoint for any other level. Accepted documents: [Supported Identity Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-id-documents), [Supported Proof of Address Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-poa-documents).

**Questionnaire (SumSub Shared and KYC Sharing via API):** Wirex needs the `onboarding_survey_baas_v1` answers -- either pre-filled on the SumSub applicant or submitted after registration with `POST /api/v2/user/questionary` (`{ "questionary_id": "onboarding_survey_baas_v1", "sections": [...] }`, response `{}`). Users registered before this endpoint existed have no answers on file and need a submission. Sections, options and errors: [KYC-FLOWS.md](references/KYC-FLOWS.md#submitting-the-questionnaire-via-api).

See [KYC-FLOWS.md](references/KYC-FLOWS.md) for detailed flow walkthroughs with code examples.

---

## Post-Onboarding Access

| Feature | Available After |
|---------|----------------|
| Withdraw crypto to external wallets | Wallet deployment (immediate) |
| Virtual card issuance | KYC Approved |
| Physical card issuance | KYC Approved |
| SEPA banking | KYC Approved + capability active |
| ACH banking | KYC Approved + capability active |
| Faster Payments | KYC Approved + capability active |

---

## User Profile

After registration, retrieve the full user profile:

```
GET /api/v2/user
```

Headers: `Authorization` + `X-Chain-Id`; with an S2S token also exactly one of `X-User-Wallet` (EOA), `X-User-Email` or `X-User-Id`. The response includes `user_id`/`user_address` (the old `id`/`owner` are deprecated mirrors), profile with status, residence address, verification (status, levels, documents), an `external_providers` array, and a capabilities array that governs which features the user can access.

See [USER-PROFILE.md](references/USER-PROFILE.md) for the complete profile schema and capabilities system.

---

## Webhooks

Delivered to `{your_webhook_base_url}` + path. Delivery: HTTP POST JSON, 10 s timeout, a failed delivery is retried up to 5 times with exponential backoff and then dropped (retries can arrive out of order and more than once, so handlers must be idempotent), no auth headers (see the wirex-baas-webhooks skill).

### Wallet Webhook

```
POST /v2/webhooks/wallets
```

Fires after on-chain registration / when wallet status changes. Expects 2xx within 10 seconds.

```json
{
  "wallet_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "wallet_name": "Main Wallet",
  "wallet_status": "Confirmed",
  "wallet_type": "Primary",
  "balances": []
}
```

Wallet status values: `Confirmed` (properly configured with required modules), `Rejected` (invalid or incomplete configuration), `Unknown`. Wallet type values: `Primary`, `Secondary`, `Global`, `Card`.

### User Webhook

```
POST /v2/webhooks/user
```

Fires when user profile or verification status changes. The payload is the `GET /api/v2/user` object **without `capabilities`** (`user_id`, `user_address`, `chain_id`, `profile`, `residence_address`, `verification`, `external_providers`; `id`/`owner` are deprecated); after a verification change call `GET /api/v2/user` to read capabilities.

### User Webhook (Legacy)

> **Note:** This is a legacy webhook format that will be replaced with a v2 model in a future release. Both are delivered; treat the legacy one as superseded for new integrations.

```
POST /webhook/users
```

Fires when user status or verification status changes. Payload: `id`, `external_id` (user's EOA), `status` (`Pending`/`Active`/`Blocked`/`Deleted`), `verification_status`, `personal_details`.

---

## Quick Start Checklist

0. Check whether the user already exists (`POST /api/v1/user/retail/validate`).
1. Deploy smart wallet, install modules, register in Accounts contract, wait for the `/v2/webhooks/wallets` webhook (see [WALLET-DEPLOYMENT.md](references/WALLET-DEPLOYMENT.md)).
2. Register user via `POST /api/v2/user` with `user_address` = the **EOA address** (not the smart wallet address).
3. Choose a KYC flow and complete verification (see [KYC-FLOWS.md](references/KYC-FLOWS.md)).
4. Poll `GET /api/v2/user` or listen for the user webhook (`/v2/webhooks/user`) to confirm `verification.status == "Approved"`.
5. Check capabilities to gate feature access (see [USER-PROFILE.md](references/USER-PROFILE.md)).
6. User is fully onboarded -- proceed to cards, transfers, or crypto operations.

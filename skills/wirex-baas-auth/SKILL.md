---
name: wirex-baas-auth
description: "Wirex BaaS authentication — how to authenticate API requests. Server-to-Server OAuth2 token exchange (POST /api/v1/token), user-scoped token issuance (POST /api/v1/user/authorize), Privy and Crossmint identity-token authentication, action tokens for sensitive operations. Covers required headers (Authorization, X-Chain-Id, X-User-Wallet/Email/Id), token caching strategy (48h S2S validity, 5min refresh buffer), and security best practices."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS Authentication

## Overview

The retail API uses two bearer tokens that are not interchangeable: the **S2S token** represents your company, the **user token** represents one user. Three methods obtain them, each serving different integration patterns:

1. **Server-to-Server (S2S) OAuth2** -- Machine-to-machine authentication using client credentials. This is the foundation; all other auth methods build on top of it.
2. **User Token Issuance** -- Partner-issued tokens scoped to a specific user, obtained by presenting an S2S token with user identity headers.
3. **Privy / Crossmint Authentication** -- Third-party identity provider integration for retail user flows. The provider's tokens are exchanged for the same Wirex user token.

The S2S token is an HMAC-SHA256 signed JWT valid for 48 hours (172800 seconds). For a user token, read `expires_at` from the response. The platform recommends caching the S2S token and refreshing it 5 minutes before expiry.

Sensitive operations (card details, 3DS approval, phone confirmation) additionally need a short-lived **action token** on top of the bearer token -- see [Action Tokens](#action-tokens).

> The Corporate API uses the same two-step shape under different names (**partner token** and **corporation token**); it is not covered by this skill.

---

## Method 1: Server-to-Server (S2S) Authentication

S2S authentication is the primary method for backend integrations. It uses the OAuth2 client credentials grant to obtain an access token.

### Endpoint

```
POST /api/v1/token
```

This is a **user-agnostic** endpoint -- no user identity headers are required.

### Request

**Headers:**

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |

**Body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `client_id` | string | Yes | Your partner application UUID |
| `client_secret` | string | Yes | Your partner secret |
| `grant_type` | string | Yes | Must be `client_credentials` |

### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_at": 1700172800
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | string | HMAC-SHA256 signed JWT token |
| `token_type` | string | Always `Bearer` |
| `expires_at` | integer | Unix timestamp (seconds) when the token expires |

The token carries `company_id`, `azp` (your `client_id`), `scope` and standard `iat`/`exp` claims. The API reference examples show the same request with the legacy Auth0 flow; Auth0 is deprecated -- do not use it for new integrations.

### Token Details

| Property | Value |
|---|---|
| **Algorithm** | HMAC-SHA256 (HS256) |
| **Validity** | 48 hours from issuance |
| **Scope** | `partner:full` |
| **Format** | JWT (JSON Web Token) |

### Rate Limiting and IP Allowlisting

- `POST /api/v1/token` is rate-limited per IP and per client. Back off exponentially on `429`.
- IP allowlisting is available for this endpoint. Contact Wirex to configure allowed IPs for your credentials.

### Usage

Send the token as `Authorization: Bearer <access_token>`. Because the S2S token carries no user, most endpoints also need one [user identity header](#user-identity-headers) plus `X-Chain-Id`. Keep it on your backend only.

---

## Method 2: User Token Issuance

User tokens are scoped to a specific user and grant access to user-specific endpoints for that user only (balances, transfers, cards, KYC). Identity is inside the token, so requests carrying it need no identity headers. This makes it safe to hand to a client app so the client can call Wirex directly without ever seeing your `client_secret`. Obtain it by presenting a valid S2S token along with a user identity header.

### Endpoint

```
POST /api/v1/user/authorize
```

### Request

**Headers:**

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes | `Bearer <s2s_access_token>` |
| `X-Chain-Id` | Yes | Target chain ID (e.g., `84532` for Sandbox Base Sepolia, `8453` for Base) |
| `X-User-Wallet` | Yes | The user's EOA address (not the Smart Wallet address) |
| `Content-Type` | Yes | `application/json` |

The API reference security scheme for this endpoint lists `X-User-Wallet`; the Authorization tag text and the authentication guide also allow `X-User-Email` or `X-User-Id` (exactly one).

**Body:** Empty or `{}`

### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": 1700172800
}
```

The user token is a JWT with user-scoped claims. Use `expires_at` from the response for its lifetime. Treat it as that user's credential: scope it and expire it accordingly.

---

## Method 3: Privy / Crossmint Authentication

Privy authentication is designed for retail user flows where users authenticate directly through a Privy-powered frontend. Privy tokens are exchanged for a Wirex-issued token, used for all subsequent API calls.

### Prerequisites

1. Set up a Privy application at [privy.io](https://privy.io)
2. Provide your Privy App ID to Wirex during onboarding
3. Wirex configures your Privy App ID in your company credentials

### Token Exchange

```
POST /api/v1/user/authorize
```

The same endpoint as Method 2; Wirex validates the Privy tokens instead of an S2S token. Response: `{ "access_token": "...", "expires_at": ... }`.

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes | `Bearer <privy_access_token>` (from Privy SDK login) |
| `Identity` | Yes | `Bearer <privy_identity_token>` (from Privy SDK login) |
| `X-Chain-Id` | Yes | Target chain ID |

Privy tokens are validated against Privy's JWKS endpoint. The `aud` claim in the access token must match your configured Privy App ID.

### User Registration via Privy

For new users, register first (same three headers as above):

```
POST /api/v1/user/retail
```

**Body:**

```json
{
  "country": "US"
}
```

Email and wallet address are extracted from the Privy tokens. Response: `{ "id": "<user-uuid>" }`. Then call `POST /api/v1/user/authorize` to obtain the Wirex token.

### Crossmint

Wirex also accepts Crossmint tokens. The flow mirrors Privy: the acting user is taken from the provider's identity token (wallet address from its `linked_accounts` claim), so `X-User-*` headers are not sent. The outcome is the same Wirex token. Provider configuration is part of onboarding -- contact Wirex before building against this path.
---

## User Identity Headers

For endpoints that operate on a specific user, exactly one of the following headers must be provided:

| Header | Format | Description |
|---|---|---|
| `X-User-Wallet` | EOA address | The user's EOA address (the value passed as `user_address` at registration) -- not the Smart Wallet address |
| `X-User-Email` | Email string | The user's registered email address |
| `X-User-Id` | UUID string | The platform-assigned user identifier |

**Rules:**

- Exactly one identity header is required for user-specific calls. Multiple identity headers are rejected with `ErrorInvalidField` (`field: user_identifier`); none returns `ErrorMissingField` ("No valid user identifier provided").
- A user token already identifies its user, so identity headers are not needed when it is used.
- For all endpoints other than the user-agnostic ones below, identity headers are mandatory with an S2S token.

### User-Agnostic Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/token` | POST | S2S token exchange |
| `/api/v1/user` | POST | User registration (v1) |
| `/api/v2/user` | POST | User registration (v2) |
| `/api/v1/config` | GET | Application configuration |
| `/api/v1/validation/rules` | GET | Validation rules |

---

## Token Caching

The S2S token is valid for 48 hours and should be cached and refreshed proactively with a 5-minute buffer before expiry (`POST /api/v1/token` is rate-limited, so do not request a new token per call).

```
Token lifetime:  |<-------------- 48 hours ------------->|
                 |                                        |
Issue time       |--- Use cached token ---|--- Refresh ---|
                 t=0                    t=47h55m         t=48h
                                          ^
                                    5-min buffer
```

---

## Error Handling

### Error Response Format

```json
{
  "error_reason": "ErrorPermissionDenied",
  "error_description": "Invalid client credentials",
  "error_category": {
    "category": "CategoryUnauthorized",
    "http_status_code": 401
  },
  "error_details": [
    {"key": "field", "details": "client_secret"}
  ]
}
```

> **Note:** `error_category` is an **object** with `category` and `http_status_code` fields. `error_details` is an optional array providing field-level error context.
>
> Note: docs differ. The guides show `error_reason` as a string; the OpenAPI schema (`response.ErrorResponse`) models it as an object `{"reason": "..."}`. Branch on the string as the guide says.

### Common Authentication Errors

| Error Reason | HTTP | Category | Description |
|---|---|---|---|
| `ErrorPermissionDenied` | 401 | `CategoryUnauthorized` | Invalid credentials, credentials access not enabled, or invalid token signature |
| `ErrorExpired` | 401 | `CategoryUnauthorized` | Access token has expired |
| `ErrorMissingField` | 400 | `CategoryValidationFailure` | Required field or header missing |
| `ErrorInvalidField` | 400 | `CategoryValidationFailure` | Invalid value or multiple user identifiers provided |
| `ErrorNotSupported` | 401 | `CategoryUnauthorized` | Client credentials not supported for this company type |
| `ErrorNotFound` | 400 | `CategoryValidationFailure` | Requested user not found (or not in your company) |
| `ErrorConfigurationInvalid` | 500 | `CategoryInternalFailure` | Privy App ID not registered (Privy flow) |

---

## Action Tokens

Bearer tokens authenticate the caller. An action token proves the user just deliberately confirmed one specific thing, and is required **on top of** a bearer token for sensitive operations. It is minted for one `action_type` and rejected for any other; it is valid for **5 minutes**.

| `action_type` | Confirms | By signature | By SMS |
|---|---|---|---|
| `GetCardDetails` | Reading PAN, CVV and PIN | Yes | Yes |
| `3dsChallenge` | Approving or declining a 3DS challenge | Yes | No |

- By signature: `POST /api/v1/confirmation/signature/verify` with `action_type`, `message_signature`, `nonce` (Unix timestamp, no more than 5 minutes old) and optional `public_key` (required on XRPL). The user signs `By signing this I confirm that I am executing action {action_type} at {nonce}`. On EVM the signature is EIP-191 `personal_sign`; when the user's registered wallet is a smart contract, it is checked with the contract's ERC-1271 `isValidSignature`.
- By SMS: `POST /api/v1/confirmation/sms`, then `POST /api/v1/confirmation/sms/verify`.
- Phone confirmation also uses an action token.
- Failures: `ErrorExpired` (`action_token: expired`) -- mint a new one; `ErrorInvalidField` with `invalid_purpose` (minted for a different action, retrying does not help), `invalid_token` or `invalid_claims`.
- Do not mint action tokens speculatively.

KYC tokens (SumSub SDK token, SumSub share token) are not Wirex bearer credentials and do not go in the `Authorization` header; see the onboarding skill.

---

## Security Best Practices

- **Never expose `client_secret` in client-side code.** All token exchange must happen server-side.
- **Use a secrets manager** (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager) to store credentials.
- **Never commit credentials** to source control; rotate immediately if compromised.
- **Cache tokens** with a 5-minute buffer before expiry to avoid request failures.
- **Keep the S2S token on your backend only.** Hand a client app a user token instead -- a leaked S2S token exposes every user in your company, a leaked user token only one.
- **Always use HTTPS.** TLS 1.2 or higher is required; validate certificates.
- **Implement request timeouts.** 30-second timeout recommended.
- **Never log full tokens.** Truncate to first 10 characters if logging is needed.
- **Use idempotency keys** for mutation requests where supported.

---

## Complete Authentication Flow

1. `POST /api/v1/token` with `client_id` + `client_secret` → receive S2S token (48h validity)
2. `POST /api/v1/user/authorize` with `Bearer {s2s_token}` + `X-User-Wallet` + `X-Chain-Id` → receive user token (read `expires_at`)
3. Call user-scoped endpoints (wallets, cards, transfers) with `Bearer {user_token}` + `X-Chain-Id`
4. For card details / 3DS / phone confirmation, add an action token (5 min)

---

## References

- [Authentication Endpoint Reference](references/REFERENCE.md) -- Complete endpoint specifications, JWT claims, JavaScript code examples, token caching, and full request/response details

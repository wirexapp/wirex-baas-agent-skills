# Wirex BaaS Authentication -- Endpoint Reference

Complete endpoint specifications for all authentication-related API calls, including full request/response examples, JWT claims, headers, and error responses.

---

## Endpoints Overview

| Method | Endpoint | Auth Required | User Identity | Description |
|---|---|---|---|---|
| POST | `/api/v1/token` | No | No | S2S OAuth2 token exchange |
| POST | `/api/v1/user/authorize` | S2S Bearer + identity header, or Privy/Crossmint tokens | Yes (`X-User-Wallet`) | User token issuance |
| POST | `/api/v1/user/retail` | Privy tokens | No | Privy user registration |
| POST | `/api/v1/user` | S2S Bearer | No | User registration (v1) |
| POST | `/api/v2/user` | S2S Bearer | No | User registration (v2) |
| POST | `/api/v1/confirmation/signature/verify` | User/S2S Bearer | Yes | Mint action token by signature |
| POST | `/api/v1/confirmation/sms`, `/sms/verify` | User/S2S Bearer | Yes | Mint action token by SMS |

---

## POST /api/v1/token

Exchanges partner credentials for an S2S access token using OAuth2 client credentials grant.

### Request

**URL:** `{base_url}/api/v1/token`

**Method:** `POST`

**Headers:**

| Header | Value | Required |
|---|---|---|
| `Content-Type` | `application/json` | Yes |

**Body Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `client_id` | string | Yes | Partner application UUID. Provided during onboarding (per environment). |
| `client_secret` | string | Yes | Partner secret string. Must be kept confidential. |
| `grant_type` | string | Yes | Must be exactly `client_credentials`. |

### Success Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5cWdLN3h6UWlybUpnWmk5ek9hbUxYUTZkUTdLcFV1OSIsInNjb3BlIjoicGFydG5lcjpmdWxsIiwiaWF0IjoxNzAwMDAwMDAwLCJleHAiOjE3MDAxNzI4MDB9.abc123signature",
  "token_type": "Bearer",
  "expires_at": 1700172800
}
```

**Response Fields:**

| Field | Type | Description |
|---|---|---|
| `access_token` | string | JWT access token. Use as `Bearer {token}` in the Authorization header for subsequent requests. |
| `token_type` | string | Always `Bearer`. |
| `expires_at` | integer | Unix timestamp (seconds since epoch) when the token expires. The token is valid for 48 hours (172800 seconds) from issuance. |

> The OpenAPI schema describes `expires_at` as "the token lifetime in seconds" (example `172800`), while its own examples and the authentication guide show a Unix timestamp (e.g. `1744007319`). Treat it as an absolute timestamp as the guide does, and compare against the current time.

**Rate limiting:** this endpoint is rate-limited per IP and per client (`429`, `CategoryTransientFailure`); back off exponentially. IP allowlisting is available -- contact Wirex.

### Error Responses

**Invalid credentials (401):**

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

**Invalid grant type (400):**

```json
{
  "error_reason": "ErrorInvalidField",
  "error_description": "Invalid value for grant type",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  }
}
```

---

## POST /api/v1/user/authorize

Issues a user-scoped access token. Requires a valid S2S token and user identification.

### Request

**URL:** `{base_url}/api/v1/user/authorize`

**Method:** `POST`

**Headers:**

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <s2s_access_token>` | Yes |
| `X-Chain-Id` | Chain ID (e.g., `84532`, `8453`, `4217`, `9223372036854775806`) | Yes |
| `X-User-Wallet` | User's EOA address (not Smart Wallet) | Yes |
| `Content-Type` | `application/json` | Yes |

**Body:** Empty object `{}` or omitted.

The API reference security scheme for this endpoint names only `X-User-Wallet`; the Authorization tag text and the authentication guide also allow `X-User-Email` or `X-User-Id` (exactly one). With Privy/Crossmint tokens the `Authorization` + `Identity` headers replace the S2S token and identity header.

### Success Response (200 OK)

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": 1700172800
}
```

> The Authorization tag text of the API reference shows an older example `{"token": "..."}`; the response schema (`access_token`, `expires_at`) is what the endpoint returns.

### Error Responses

**Missing X-Chain-Id (400):**

```json
{
  "error_reason": "ErrorMissingField",
  "error_description": "X-Chain-Id header is missing",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  }
}
```

**User not found (400):**

```json
{
  "error_reason": "ErrorNotFound",
  "error_description": "Requested user was not found",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  }
}
```

**Expired S2S token (401):**

```json
{
  "error_reason": "ErrorExpired",
  "error_description": "Token is expired",
  "error_category": {
    "category": "CategoryUnauthorized",
    "http_status_code": 401
  }
}
```

---

## POST /api/v1/user/retail

Registers a new retail user authenticated through Privy.

### Request

**URL:** `{base_url}/api/v1/user/retail`

**Method:** `POST`

**Headers:**

| Header | Value | Required |
|---|---|---|
| `Authorization` | `Bearer <privy_access_token>` (from Privy SDK) | Yes |
| `Identity` | `Bearer <privy_identity_token>` (from Privy SDK) | Yes |
| `X-Chain-Id` | Chain ID | Yes |
| `Content-Type` | `application/json` | Yes |

**Body Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `country` | string | Yes (per guide) | User's country of residence (ISO 3166-1 alpha-2, e.g., `"US"`, `"GB"`). Email and wallet address are extracted from Privy tokens. |
| `referrer_address` | string | No | EOA address of the user who referred this user |

> Note: docs differ. The KYC guide (`retail-kyc-hosted`) marks `country` as required and shows `email` in the body; the OpenAPI schema (`request.UserCreateUserRetailRequest`) has only `country` and `referrer_address` and marks neither as required.

### Success Response (200 OK)

```json
{
  "id": "user-uuid"
}
```

The guide says this endpoint "also exchanges Privy tokens and returns a Wirex token", but the response schema only returns `id`. After registration, call `POST /api/v1/user/authorize` with the same Privy headers to obtain the Wirex token.

**Response Fields:**

| Field | Type | Description |
|---|---|---|
| `id` | string | Platform-assigned user identifier (UUID) |

### Privy Token Claims

| Claim | Token | Description |
|---|---|---|
| `sub` | Access token | Privy user ID |
| `aud` | Access token | Privy App ID (must match your configured App ID) |
| `linked_accounts` | Identity token | Array of linked wallets |

`linked_accounts` structure:

```json
{
  "linked_accounts": [
    {
      "type": "smart_wallet",
      "address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
      "chain_type": "ethereum"
    }
  ]
}
```

### Error Responses

**Expired Privy token (401):**

```json
{
  "error_reason": "ErrorExpired",
  "error_description": "Access token is expired",
  "error_category": {
    "category": "CategoryUnauthorized",
    "http_status_code": 401
  }
}
```

**App not registered (500):**

```json
{
  "error_reason": "ErrorConfigurationInvalid",
  "error_description": "Client application not registered",
  "error_category": {
    "category": "CategoryInternalFailure",
    "http_status_code": 500
  }
}
```

---

## JWT Token Structure

### S2S Token Claims

Decoded S2S JWT payload:

```json
{
  "iss": "https://api-baas.wirexapp.com/srv",
  "sub": "your-client-uuid",
  "azp": "your-client-uuid",
  "company_id": "your-company-uuid",
  "scope": "partner:full",
  "iat": 1739525600,
  "exp": 1739698400
}
```

| Claim | Type | Description |
|---|---|---|
| `iss` | string | Issuer. `https://api-baas.wirexapp.com/srv` (as shown in the guide's example) |
| `sub` | string | Subject -- the `client_id` (UUID) of the partner |
| `azp` | string | Authorized party -- same as `client_id` |
| `company_id` | string | Your company UUID |
| `scope` | string | Permission scope. S2S tokens have `partner:full` |
| `iat` | integer | Issued-at timestamp (Unix seconds) |
| `exp` | integer | Expiration timestamp (Unix seconds). `iat + 172800` (48 hours validity) |

### User Token Claims

User tokens include user-scoped claims in addition to the standard JWT fields. The exact claims are issued by the server and should be treated as opaque — use the token as a Bearer credential, do not parse claims for business logic.

---

## Headers Reference

### Common Headers

| Header | Format | Example | Description |
|---|---|---|---|
| `X-Chain-Id` | Numeric string | `84532` | Target blockchain network ID (required on all API requests per `retail-api-basics`) |
| `Authorization` | `Bearer <token>` | `Bearer eyJhbGciOi...` | S2S or user access token. Most endpoints |
| `Content-Type` | MIME type | `application/json` | Requests with a JSON body |
| `X-Company-Id` | UUID | `00000000-0000-0000-0000-000000000044` | Company id; used by `GET /api/v1/config` without a token |

### User Identity Headers

Exactly one is required for user-specific endpoints:

| Header | Format | Example | Description |
|---|---|---|---|
| `X-User-Wallet` | EOA address | `0x1234...5678` | User's EOA address (the `user_address` passed at registration; not Smart Wallet) |
| `X-User-Email` | Email string | `user@example.com` | User's registered email |
| `X-User-Id` | UUID string | `3f2b8c1e-...` | Platform user identifier (UUID) |

User tokens do not need identity headers.

### Header Selection

Provide **only one** user identity header per request. Sending multiple returns `ErrorInvalidField` (`field: user_identifier`, "Multiple user identifiers provided in headers. Only one is allowed"); sending none returns `ErrorMissingField` ("No valid user identifier provided").

### Privy Authentication Headers

| Header | Format | Example | Description |
|---|---|---|---|
| `Authorization` | `Bearer <token>` | `Bearer eyJhbGciOiJFUzI1Ni...` | Privy access token (Bearer-prefixed) |
| `Identity` | `Bearer <token>` | `Bearer eyJhbGciOiJFUzI1Ni...` | Privy identity token (Bearer-prefixed) |

Crossmint follows the same pattern with its identity token; contact Wirex to enable it.

### Valid Chain ID Values

| Chain ID | Network | Environment |
|---|---|---|
| `84532` | Base Sepolia | Sandbox |
| `9223372036854775806` | Stellar Testnet | Sandbox |
| `9223372036854775805` | XRPL (Wirex-assigned, not EIP-155) | Sandbox |
| `8453` | Base | Production |
| `9223372036854775806` | Stellar | Production |
| `4217` | Tempo | Production |

XRPL has no EIP-155 chain ID; confirm the value for your environment with Wirex. The authentication guide's examples also use `137` (Polygon), which the Environments page does not list as a supported chain.

---

## Error Response Format

All errors from authentication endpoints follow this format:

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

> **Note:** `error_category` is an **object** (not a string) containing `category` and `http_status_code`. `error_details` is an optional array with field-level context. Do not parse `error_description` (`retail-error-reference`).
>
> Note: docs differ. The guides and examples show `error_reason` as a string (branch on it as the guide says); the OpenAPI schema `response.ErrorResponse` models it as an object `{"reason": "..."}`, and `error_category` also has `grpc_status_code`.

### Error Categories

| Category | HTTP Status | Description |
|---|---|---|
| `CategoryValidationFailure` | 400 | Request is malformed, missing required fields, or contains invalid values. |
| `CategoryUnauthorized` | 401 | Authentication failed (token is invalid or expired, or credentials are wrong). |
| `CategoryForbidden` | 403 | Authenticated, but the operation is not permitted. |
| `CategoryTransientFailure` | 429 | Transient rejection (rate limiting). The docs say to back off exponentially on 429 for `POST /api/v1/token`. |
| `CategoryInternalFailure` | 500 | Server-side failure. `ErrorConfigurationInvalid` means a platform configuration problem: contact Wirex. |
| `CategoryTransportFailure` | 503 | A downstream service was unreachable. |

> Branch on `error_reason`, not on the HTTP status: a reason is not bound to one category across every endpoint (`retail-error-reference`). The docs give no per-category retry rules; retry advice in the Retry Strategy section is the skill's suggestion.

### S2S Token Exchange Errors

| HTTP | Error Reason | Description |
|---|---|---|
| 400 | `ErrorMissingField` | Missing `client_id` ("client id is required") or `client_secret` ("client secret is required") |
| 400 | `ErrorInvalidField` | "Invalid value for grant type" -- `grant_type` is not `client_credentials` |
| 401 | `ErrorPermissionDenied` | Invalid client credentials (unknown `client_id` or wrong `client_secret`) |
| 401 | `ErrorPermissionDenied` | Client credentials access is not enabled for this account |
| 401 | `ErrorNotSupported` | Client credentials not supported for this company type |

### S2S Request Errors (Bearer Token)

| HTTP | Error Reason | Description |
|---|---|---|
| 400 | `ErrorMissingField` | Missing Authorization Headers |
| 400 | `ErrorInvalidField` | Bearer token not in correct format |
| 401 | `ErrorExpired` | Token is expired |
| 401 | `ErrorPermissionDenied` | Token signature is not valid |
| 401 | `ErrorMissingField` | Client id claim is missing (`azp`) |
| 401 | `ErrorMissingField` | Company ID claim is missing |
| 400 | `ErrorMissingField` | X-Chain-Id header is missing |
| 400 | `ErrorMissingField` | No valid user identifier provided |
| 400 | `ErrorInvalidField` | Multiple user identifiers provided (only one allowed) |
| 400 | `ErrorNotFound` | Requested user was not found (does not exist or not in your company) |

### Privy Token Exchange Errors

| HTTP | Error Reason | Description |
|---|---|---|
| 400 | `ErrorMissingField` | Missing Authorization Headers |
| 400 | `ErrorMissingField` | Missing Identity Headers |
| 401 | `ErrorExpired` | Access token is expired |
| 401 | `ErrorExpired` | ID token is expired |
| 401 | `ErrorPermissionDenied` | Access token signature is not valid |
| 401 | `ErrorPermissionDenied` | ID token signature is not valid |
| 401 | `ErrorMissingField` | Linked accounts claim is missing |
| 400 | `ErrorMissingField` | Not all identifiers found in linked accounts |
| 500 | `ErrorConfigurationInvalid` | Client application not registered (Privy App ID not configured) |

### User Token Errors

| HTTP | Error Reason | Description |
|---|---|---|
| 401 | `ErrorExpired` | Token is expired |
| 401 | `ErrorPermissionDenied` | Token signature is not valid |
| 401 | `ErrorMissingField` | User ID claim is missing |
| 401 | `ErrorMissingField` | User email claim is missing |
| 401 | `ErrorMissingField` | User address claim is missing |

### Action Token Errors

| Error Reason | `error_details` | Meaning |
|---|---|---|
| `ErrorExpired` | `action_token: expired` | More than 5 minutes old -- mint a new one |
| `ErrorInvalidField` | `action_token: invalid_purpose` | Minted for a different `action_type` (not an expiry; retrying does not help) |
| `ErrorInvalidField` | `action_token: invalid_token` / `invalid_claims` | Malformed token / claims could not be parsed |
| `ErrorInvalidField` | `action_type: Invalid value for action type` (`issue: invalid_value`) | Unknown `action_type`, or `3dsChallenge` requested via SMS |

---

## Retry Strategy

> Suggestion (skill advice, not Wirex-specified): the Wirex docs only say to back off exponentially on `429` (`retail-authentication`, `retail-auth-tokens`). The schedule and code below are an example, not Wirex behaviour. Do not retry `ErrorConfigurationInvalid` (500): contact Wirex.

### Example Exponential Backoff

```
Attempt 1: Wait 1 second
Attempt 2: Wait 2 seconds
Attempt 3: Wait 4 seconds
Attempt 4: Wait 8 seconds
Attempt 5: Wait 16 seconds (max)
```

### Implementation (JavaScript)

```javascript
async function requestWithRetry(fn, maxRetries = 5) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      // error_category is an object: { category: "...", http_status_code: N }
      const category = error.response?.data?.error_category?.category;

      // Do not retry validation errors
      if (category === 'CategoryValidationFailure') {
        throw error;
      }

      // Re-authenticate on unauthorized errors
      if (category === 'CategoryUnauthorized') {
        await tokenCache.refresh();
        continue;
      }

      // Retry on transient failures (429); 500 retry here is a suggestion, not Wirex-specified
      if (
        category === 'CategoryTransientFailure' ||
        category === 'CategoryInternalFailure'
      ) {
        if (attempt === maxRetries) throw error;

        const delay = Math.min(1000 * Math.pow(2, attempt), 16000);

        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }

      throw error;
    }
  }
}
```

---

## Complete Integration Example

End-to-end example: authenticate, register a user, obtain a user token, and read the wallet.

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const BASE_URL = 'https://api-baas.wirexapp.tech';
// Shared sandbox credentials from the Environments page; contact Wirex for dedicated ones.
const CLIENT_ID = '3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB';
const CLIENT_SECRET = '6FIY2GEQvdlgUEFHw4Dbii22_wCAqZ37lWV3TEMfTlkxrn8F5IbdgX9TiAvQUEsC';
const CHAIN_ID = '84532'; // Sandbox Base Sepolia
const USER_ADDRESS = '0x...'; // the user's EOA address

async function main() {
  // Step 1: Obtain S2S token
  const tokenResponse = await axios.post(`${BASE_URL}/api/v1/token`, {
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    grant_type: 'client_credentials'
  }, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000
  });

  const s2sToken = tokenResponse.data.access_token;
  console.log(`S2S token obtained. Expires: ${new Date(tokenResponse.data.expires_at * 1000).toISOString()}`);

  // Step 2: Register a user (server-side; required: email, country; user_address is the EOA)
  const userResponse = await axios.post(`${BASE_URL}/api/v1/user`, {
    email: 'test-user@example.com',
    country: 'US',
    user_address: USER_ADDRESS
  }, {
    headers: {
      'Authorization': `Bearer ${s2sToken}`,
      'X-Chain-Id': CHAIN_ID,
      'Content-Type': 'application/json'
    },
    timeout: 30000
  });

  console.log(`User registered. Id: ${userResponse.data.id}`);

  // Step 3: Obtain user token
  const userTokenResponse = await axios.post(`${BASE_URL}/api/v1/user/authorize`, {}, {
    headers: {
      'Authorization': `Bearer ${s2sToken}`,
      'X-Chain-Id': CHAIN_ID,
      'X-User-Wallet': USER_ADDRESS,
      'Content-Type': 'application/json'
    },
    timeout: 30000
  });

  const userToken = userTokenResponse.data.access_token;
  console.log(`User token obtained. Expires: ${new Date(userTokenResponse.data.expires_at * 1000).toISOString()}`);

  // Step 4: Query the user's wallet (identity is in the user token; X-Chain-Id is still required)
  const walletResponse = await axios.get(`${BASE_URL}/api/v1/wallet`, {
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'X-Chain-Id': CHAIN_ID
    },
    timeout: 30000
  });

  console.log('Wallet:', JSON.stringify(walletResponse.data, null, 2));
}

main().catch(console.error);
```

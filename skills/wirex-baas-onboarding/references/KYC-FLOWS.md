# KYC Flows Reference

Wirex supports **only one verification flow at a time**; changing the configured flow may affect users who have already completed or are undergoing verification.

## Verification Levels

| Level | Description | Documents | Unlocks |
|-------|-------------|-----------|---------|
| `BDD` | Basic Due Diligence | PoI + selfie | Account creation, limited features |
| `SDD` | Standard Due Diligence | PoI + PoA + selfie | Bank accounts, cards, standard transfers; higher spending limits |
| `EDD` | Enhanced Due Diligence | Additional documentation | Higher limits, additional features |

PoI = Proof of Identity, PoA = Proof of Address. The API enum for `verification_level` is `N/A`, `BDD`, `SDD`, `XDDBridgeBase`, `EDD` (`XDDBridgeBase` = `SDD` plus tax identification number; required for ACH accounts; an omitted or unrecognised value falls back to `SDD`). Accepted PoI documents by issuing country: [Supported Identity Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-id-documents); accepted PoA documents: [Supported Proof of Address Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-poa-documents).

---

## Flow 1: Wirex Hosted KYC

The simplest integration. The partner registers the user with minimal data, then lets them complete KYC in the hosted SumSub widget or an embedded SumSub SDK.

### Step 1: Register User

Two registration methods:

| Method | Endpoint | Auth |
|--------|----------|------|
| S2S Registration | `POST /api/v2/user` | S2S token (backend-to-backend) |
| Privy Registration | `POST /api/v1/user/retail` | Privy tokens (frontend) |

```
POST /api/v2/user
Content-Type: application/json
Authorization: Bearer {partner_token}
X-Chain-Id: {chainId}
```

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

`user_address` replaces the former `wallet_address` (both accepted; if both are supplied they must match). Response: `{ "id": "<user uuid>" }`.

Privy variant: `POST /api/v1/user/retail` with `Authorization: Bearer {privy_access_token}`, `Identity: Bearer {privy_identity_token}`, `X-Chain-Id`, body `{ "country": "GB" }` (optional `referrer_address`; `country` omitted defaults to the country of the caller's IP address; email and wallet come from the Privy identity token).

> **Docs inconsistency:** the API reference schema for `POST /api/v2/user` lists `initial_data.is_pep`, every `profile` field and `residence_address` city/country/line1/post_code as required; the Hosted KYC guide (followed here) registers with only email + country.

### Step 2: Get Verification Link

```
POST /api/v1/user/verification-link
Authorization: Bearer {user_token}
X-Chain-Id: {chainId}
Content-Type: application/json
```

Optional body: `{ "verification_level": "SDD" }`.

**Response:**

```json
{
  "redirect_uri": "https://in.sumsub.com/idensic/l/#/HA0Z3b34F9YfWxhQ"
}
```

Open the URL in a browser or webview; the user completes verification in the hosted SumSub widget.

### Step 2 (Alternative): Get Verification Token

To embed the SumSub Web/Mobile SDK in your own UI:

```
POST /api/v1/user/verification-token
Authorization: Bearer {user_token}
X-Chain-Id: {chainId}
Content-Type: application/json
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

Use this token to initialize the SumSub SDK (see the SumSub SDK documentation). To brand the WebSDK, Wirex sets up a customization in the SumSub dashboard and sends you a name to pass as `customizationName` in `withConf` (WebSDK 2.x only; not available for the verification-link flow); see [Hosted KYC, WebSDK Customization](https://docs.wirexapp.com/docs/retail-kyc-hosted#websdk-customization).

With an S2S token, user identity headers apply: exactly one of `X-User-Wallet` (the EOA, not the Smart Wallet), `X-User-Email`, `X-User-Id`.

### Step 3: Wait for the result

User completes KYC -> SumSub sends the result to Wirex -> Wirex sends a webhook with the updated verification status (`/v2/webhooks/user`, or legacy `/webhook/users`; the v2 payload has no `capabilities`) and activates the account. Restricted operations (card issuance, fiat withdrawals) stay unavailable until KYC is approved.

The phone number the user enters in the SumSub form is stored on the profile and **automatically marked as confirmed**.

### Code Example (JavaScript)

```javascript
const API_BASE = 'https://api-baas.wirexapp.com';

// Step 1: Register
const registerResponse = await fetch(`${API_BASE}/api/v2/user`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${partnerToken}`,
    'X-Chain-Id': chainId.toString(),
  },
  body: JSON.stringify({
    user_address: '0xAbC123...EOA',
    initial_data: {
      profile: { email: 'user@example.com' },
      residence_address: { country: 'GB' },
    },
  }),
});
const { id: userId } = await registerResponse.json();

// Step 2: Get verification link (S2S token + user identity header)
const linkResponse = await fetch(`${API_BASE}/api/v1/user/verification-link`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${partnerToken}`,
    'X-User-Wallet': userEoaAddress,
    'X-Chain-Id': chainId.toString(),
  },
  body: JSON.stringify({}),
});
const { redirect_uri } = await linkResponse.json();
console.log(`Redirect user to: ${redirect_uri}`);
```

---

## Flow 2: SumSub Shared KYC

For partners whose users are already verified via SumSub. The partner shares the existing verification with Wirex via a `sharing_token`.

> **Approval required:** only available after a detailed Wirex audit (3-sided data sharing agreement with Wirex and SumSub); may be rejected. Contact your Wirex account manager.

### Prerequisites

- SumSub integration able to generate share tokens for external clients.
- Target client ID for Wirex: **`wirexapp.com_51921`**.
- The SumSub applicant must carry all data Wirex needs; otherwise verification stays incomplete until the user uploads the missing data/documents manually.

**Applicant data (required unless noted):** first name, last name, date of birth, nationality, phone, country, city, street, building number, postcode; state and street line 2 are optional.

**Documents:** selfie (liveness check, required); Proof of Identity (required; accepted document types per country: [Supported Identity Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-id-documents); must have more than 1 month of validity left); Proof of Address (required; issued within the last 6 months, see [Supported Proof of Address Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-poa-documents)). User age: 18-90.

**Questionnaire:** the applicant must have a completed SumSub questionnaire, `onboarding_survey_baas_v1`. Get it from your Wirex account manager, add it to your SumSub verification level, and keep section IDs, item IDs and option values unchanged -- Wirex reads answers by value. Instead of pre-filling it on the applicant, you can submit it via the Wirex API after registration -- see [Submitting the Questionnaire via API](#submitting-the-questionnaire-via-api).

| Section | Item | Type | Required | Options |
|---------|------|------|----------|---------|
| `productsServicesRequired` | `productsServicesRequired` | multiSelect | Yes | `Card purchases including restaurants, shopping, leisure`, `Send money to friends and family`, `Flights, hotels, car hire etc.`, `Mortgage/rent payments etc. and ATM withdrawals`, `Traditionally investing with banks etc.`, `Trading or investing in Crypto, including staking, mining & NFTs` |
| `employmentStatus` | `employmentStatus` | select | Yes | `Employed / Self Employed`, `Retired`, `Student / Not employed` |
| `occupation` | `occupation` | selectDropdown | Only when `employmentStatus` = `Employed / Self Employed` | `Agriculture / Natural Resources / Mining`, `Construction / Engineering`, `Education / Academic`, `Financial Services / Banking`, `Government / Public Sector / Defence`, `Healthcare / Medical / Pharmaceuticals`, `Hospitality / Travel / Tourism`, `Legal / Professional Services (Law, Accountancy, Consulting)`, `Manufacturing / Industrial`, `Media / Entertainment / Arts`, `Real Estate / Property Development`, `Retail / E-Commerce`, `Technology / IT Services`, `Transportation / Logistics / Shipping`, `Other` |
| `actualIncomeValue` | `actualIncomeValue` | select | Yes | `Up to 25,000`, `25,000 – 75,000`, `75,000 – 150,000`, `Over 150,000` |
| `sourceOfFunds` | `sourceOfFunds` | select | Yes | `Employment / Salary`, `Business Income / Self-Employment`, `Savings / Existing Investments`, `Inheritance`, `Gift`, `Other` |
| `annualTransactionVolume` | `annualTransactionVolume` | select | Yes | `Up to 25,000`, `25,000 – 75,000`, `75,000 – 150,000`, `Over 150,000` |
| `pepDeclaration` | `personalPepConfirmation` | select | Yes | `I am a PEP`, `I am not a PEP` |
| `pepDeclaration` | `personalPepExplanation` | textArea | Only when `personalPepConfirmation` = `I am a PEP` | free text |

### Step 1: Generate a Share Token

Use SumSub's "Generate Share Token" API (https://docs.sumsub.com/reference/generate-share-token) with the target client ID `wirexapp.com_51921`, once the user is verified in your SumSub flow.

### Step 2: Register User with Sharing Token

```
POST /api/v2/user
Content-Type: application/json
Authorization: Bearer {partner_token}
X-Chain-Id: {chainId}
```

```json
{
  "user_address": "0xAbC123...EOA",
  "sharing_data": {
    "sharing_token": "eyJhbGciOi...",
    "email": "user@example.com"
  }
}
```

> **IMPORTANT:** `sharing_data` and `initial_data` are mutually exclusive — do not provide both.

Wirex fetches the verification from SumSub, validates it and creates the account. The phone number from SumSub verification is **automatically confirmed**.

### Code Example (JavaScript)

```javascript
const API_BASE = 'https://api-baas.wirexapp.com';

const registerResponse = await fetch(`${API_BASE}/api/v2/user`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${partnerToken}`,
    'X-Chain-Id': chainId.toString(),
  },
  body: JSON.stringify({
    user_address: '0xAbC123...EOA',
    sharing_data: { sharing_token: sharingToken, email: 'user@example.com' },
  }),
});
const { id } = await registerResponse.json();
console.log(`User registered with shared KYC: ${id}`);
```

### Share Token Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Invalid sharing token | Token expired or malformed | Generate a new token |
| Share token rejected | Target client ID mismatch | Generate for `wirexapp.com_51921` |
| Verification not found | User not verified in SumSub | Complete user verification first |
| Agreement not active | Data sharing agreement missing | Contact Wirex account manager |

---

## Flow 3: KYC Sharing via API

The partner performs full KYC on its own platform and submits the verified data and documents via API.

> **Approval required:** only available under the Enterprise model, subject to a detailed Wirex audit; may be rejected.

You are responsible for performing identity verification to regulatory standards, maintaining verification records and audit trails, ensuring data accuracy and currency, and complying with applicable KYC/AML regulations.

### Step 1: Register User with Full Profile

```
POST /api/v2/user
Content-Type: application/json
Authorization: Bearer {partner_token}
X-Chain-Id: {chainId}
```

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
      "line2": "Flat 2",
      "city": "London",
      "post_code": "SW1A 2AA",
      "country": "GB"
    }
  }
}
```

The phone number provided here is **automatically confirmed**. The reference schema additionally lists `initial_data.is_pep` (boolean) as required.

### Step 2: Upload Documents

All documents must be uploaded before the account can be fully activated.

```
POST /api/v1/user/documents
Content-Type: multipart/form-data
Authorization: Bearer {user_token}
X-Chain-Id: {chainId}
```

Fields (all four are required in the API reference):

| Field | Values | Description |
|-------|--------|-------------|
| `document` | File | The document file |
| `document_type` | `identity_card`, `passport`, `driver_license`, `proof_of_address`, `other` | Document classification |
| `document_country` | ISO 3166-1 alpha-2 | Issuing country of the document |
| `side` | `front`, `back`, `none` | Which side of the document |

The KYC Sharing guide lists the required documents as selfie, proof of identity (passport / national ID / driver's license) and proof of address (utility bill / bank statement). Accepted documents: [Supported Identity Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-id-documents) (PoI, by issuing country) and [Supported Proof of Address Documents](https://docs.wirexapp.com/docs/retail-kyc-supported-poa-documents) (PoA).

> **Docs inconsistency:** the guide names the types `selfie`, `poi`, `poa`, and its error table lists `selfie` as a valid `document_type`; the API reference enum has no `selfie`, `poi` or `poa` (values above are from the reference).

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const API_BASE = 'https://api-baas.wirexapp.com';

async function uploadDocument(userToken, documentType, filePath, country, side = 'front') {
  const form = new FormData();
  form.append('document_type', documentType);
  form.append('document_country', country);
  form.append('side', side);
  form.append('document', fs.createReadStream(filePath));

  const response = await axios.post(`${API_BASE}/api/v1/user/documents`, form, {
    headers: { ...form.getHeaders(), Authorization: `Bearer ${userToken}` },
  });
  return response.data; // empty object on success
}

await uploadDocument(userToken, 'passport', './passport.jpg', 'GB', 'front');
await uploadDocument(userToken, 'proof_of_address', './utility_bill.pdf', 'GB', 'none');
```

### Correcting KYC Data

```
PUT /api/v2/user/kyc-data
```

Updates profile (`first_name`, `last_name`, `date_of_birth`, `nationality`, `phone_number`), `residence_address` and `is_pep` already on file -- to fix mistyped data before verification completes, not to re-verify. At least one of `profile` or `residence_address` is required (sending only `is_pep` is refused); every field is individually optional. Response `{}`. **Not available under the Wirex Hosted model** (corrections go through the hosted flow).

---

## Submitting the Questionnaire via API

Available in Flow 2 (SumSub Shared) and Flow 3 (KYC Sharing via API). Once the user is registered, submit the `onboarding_survey_baas_v1` answers (sections, items and option values from the [questionnaire table](#prerequisites)) directly to Wirex. In Flow 3 there is no SumSub applicant to pre-fill, so submit them once the user has completed verification.

- If the user has already completed SDD, the submission moves them onto the verification level that hosts the questionnaire, and a webhook with the updated `verification_status` follows.
- If SDD is not complete yet, the answers are recorded against the current level and `verification_status` does not change.
- **Existing users** registered before this endpoint existed have no answers on file -- call it for each of them.

```
POST /api/v2/user/questionary
Authorization: Bearer <access token>   # token type not specified in the guides
Content-Type: application/json
```

```json
{
  "questionary_id": "onboarding_survey_baas_v1",
  "sections": [
    { "section_id": "productsServicesRequired", "answers": [{ "item_id": "productsServicesRequired", "answers": ["Send money to friends and family"] }] },
    { "section_id": "employmentStatus", "answers": [{ "item_id": "employmentStatus", "answers": ["Employed / Self Employed"] }] },
    { "section_id": "occupation", "answers": [{ "item_id": "occupation", "answers": ["Technology / IT Services"] }] },
    { "section_id": "actualIncomeValue", "answers": [{ "item_id": "actualIncomeValue", "answers": ["25,000 – 75,000"] }] },
    { "section_id": "sourceOfFunds", "answers": [{ "item_id": "sourceOfFunds", "answers": ["Employment / Salary"] }] },
    { "section_id": "annualTransactionVolume", "answers": [{ "item_id": "annualTransactionVolume", "answers": ["25,000 – 75,000"] }] },
    { "section_id": "pepDeclaration", "answers": [{ "item_id": "personalPepConfirmation", "answers": ["I am not a PEP"] }] }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `questionary_id` | string | Yes | `onboarding_survey_baas_v1` |
| `sections` | array | Yes | At least one section |
| `sections[].section_id` | string | Yes | Section identifier |
| `sections[].answers` | array | Yes | At least one answer |
| `sections[].answers[].item_id` | string | Yes | Item identifier within the section |
| `sections[].answers[].answers` | array of string | Yes | One value for `select`/`selectDropdown`, several for `multiSelect` |

With `personalPepConfirmation` = `I am a PEP`, the `pepDeclaration` section must also carry `{ "item_id": "personalPepExplanation", "answers": ["<free text>"] }`.

**Response:** `{}`

Wirex validates every section against the definition, including conditional items; a submission missing a required answer is rejected as a whole (nothing is partially saved).

| Error Reason | Description | Resolution |
|--------------|-------------|------------|
| `ErrorGeneral` | `questionary_id` missing | Supply the questionnaire identifier |
| `ErrorGeneral` | Missing required questionary answer (`error_details` names `section_id` and `item_id`) | Supply the item |
| `ErrorGeneral` | `SubmitQuestionary is only supported for Trust\|Full verification model` | Not available for this company's verification model |
| `ErrorNotFound` | Account not found | Register the user first |
| `ErrorGeneral` | Account has no SumSub ID | User has not started verification yet |
| `ErrorGeneral` | No level configured for questionary | Contact your Wirex account manager |

> Documented only in the guides (`retail-kyc-shared`, `retail-kyc-api`); the API reference has no page for this endpoint yet.

**Observed live in sandbox (2026-10-25)** -- differs from the docs in places:

| Case | Result |
|------|--------|
| Full valid body, Trust-model company, BDD-only user | `200 {}`; levels stay `BDD` (matches the docs: SDD not complete) |
| Full valid body, Full-model company, user with BDD+SDD | `200 {}`; no new level or status change seen within 60 s (the docs promise a move to the questionnaire's level + webhook) |
| Full valid body, company registered with the older `Wirex` model | `200 {}` -- the model refusal from the table above was not returned |
| Same submission again | `200 {}` (resubmission allowed) |
| Option value not in the list (`sourceOfFunds` = `Lottery`) | `200 {}` -- option values are not validated |
| No `questionary_id` | `400 ErrorGeneral` "Request failed validation", `error_details` `[{ "key": "questionary_id", "details": "questionary_id is required" }]` |
| `Employed / Self Employed` without `occupation`; `I am a PEP` without `personalPepExplanation` | `400 ErrorGeneral` "Missing required questionary answer", `error_details` name `section_id` + `item_id` (+ `failed_method: SubmitQuestionary`) |

Send option values exactly as listed: the API accepts any string, but Wirex reads answers by value.

---

## Field Validation Patterns

Enforced patterns are listed in the Field Validation Rules page and published at runtime via `GET /api/v1/validation/rules` (published rules are not identical to enforced ones; the enforced pattern decides).

### Registration Fields

| Field | Type | Required | Validation | Example |
|-------|------|----------|------------|---------|
| `user_address` | string | Yes | EVM `0x` + 40 hex, Stellar `G…`/`C…`, XRPL `r…` or Tron `T…` — must be EOA, NOT Smart Wallet | `"0xAbC123...def"` |
| `initial_data.profile.email` | string | Yes | Valid email, unique | `"user@example.com"` |
| `initial_data.residence_address.country` | string | Yes | ISO 3166-1 alpha-2 (`^[A-Z]{2}$`) | `"GB"` |
| `initial_data.profile.first_name` | string | API flow only | `^[a-zA-Z][a-zA-Z\-' ]{1,50}$` (unaccented Latin only) | `"Jane"` |
| `initial_data.profile.last_name` | string | API flow only | `^[a-zA-Z][a-zA-Z\-' ]{1,50}$` | `"Doe"` |
| `initial_data.profile.date_of_birth` | string | API flow only | `YYYY-MM-DD` | `"1990-01-15"` |
| `initial_data.profile.nationality` | string | API flow only | ISO 3166-1 alpha-2 | `"GB"` |
| `initial_data.profile.phone_number` | string | API flow only | `^\+?\d{1,15}$` (E.164, e.g. `+447700900123`) | `"+447700900123"` |
| `sharing_data.sharing_token` | string | SumSub only | Valid SumSub share token for `wirexapp.com_51921` | `"eyJhbGciOi..."` |
| `sharing_data.email` | string | SumSub only | Valid email, unique | `"user@example.com"` |

### Address Fields (inside `initial_data.residence_address`)

| Field | Type | Required | Validation | Example |
|-------|------|----------|------------|---------|
| `line1` | string | Yes (API flow) | `^[A-Za-z0-9&.,''\-/() :+#]{2,100}$` | `"10 Downing Street"` |
| `line2` | string | No | Same as line1 | `"Flat 2"` |
| `city` | string | Yes (API flow) | `^[A-Za-z\s\-'.]{2,100}$` (no digits) | `"London"` |
| `state` | string | No | `^[A-Za-z][A-Za-z\s\-']{1,99}$` | `"England"` |
| `post_code` | string | Yes (API flow) | `^[A-Za-z0-9\s\-]{3,12}$` | `"SW1A 2AA"` |
| `country` | string | Yes | ISO 3166-1 alpha-2 | `"GB"` |

### Common Validation Errors

| Error Reason | Field | Description |
|-------------|-------|-------------|
| `ErrorInvalidField` | `user_address` | Invalid format (EVM `0x` + 40 hex, Stellar `G…`/`C…`, XRPL `r…` or Tron `T…`) |
| `ErrorInvalidField` | `email` | Invalid email format |
| `ErrorInvalidField` | `country` | Invalid ISO 3166-1 alpha-2 code |
| `ErrorInvalidField` | `sharing_token` | Invalid or expired SumSub sharing token |
| `ErrorNotFound` | wallet | Wallet not registered in Accounts contract — complete on-chain registration first |
| `ErrorAlreadyExists` | `email` | A user with this email already exists |
| `ErrorAlreadyExists` | wallet address | A user with this wallet already exists |

Providing both `sharing_data` and `initial_data` fails validation (mutually exclusive).

> The Hosted, Shared and API guides now show request validation failures on `POST /api/v2/user` as `ErrorGeneral` `Request failed validation`, with the field path as the `error_details` key (see the example under Error Handling); the `ErrorInvalidField` rows above are the older wording.

---

## Phone Confirmation

In all three flows the phone number is **automatically marked as confirmed** (from the SumSub form, the SumSub applicant, or the `phone_number` you submit); the guides state no separate confirmation step is required. A confirmed phone is used for **3DS Authentication** (OTP codes via SMS) and **Read Card Details** (OTP-based verification).

If you need to set or change the number manually, the endpoints below exist. All require `Authorization` plus the usual user identity (`X-User-Wallet: {userEoaAddress}`, `X-Chain-Id: {chainId}` when using an S2S token), and `Content-Type: application/json`.

### Step 1: Set Phone Number

```
PUT /api/v1/user/phone-number
```

```json
{ "phone_number": "+447700900123" }
```

Pattern `^\+?\d{1,15}$` (the `+` is optional per the enforced pattern; the reference example is `61412345678`). Response: `{}`.

### Step 2: Request SMS Code

```
POST /api/v1/confirmation/sms
```

```json
{ "action_type": "VerifyPhone" }
```

`action_type` enum: `GetCardDetails`, `3dsChallenge`, `VerifyPhone`. The SMS goes to the phone number provided during KYC.

**Response:**

```json
{
  "session_id": "00000000-0000-0000-0000-000000000001",
  "code_length": 6,
  "expires_at": "2021-01-01T00:00:00Z",
  "resend_at": "2021-01-01T00:00:00Z",
  "attempts_left": 3
}
```

### Step 3: Verify SMS Code

```
POST /api/v1/confirmation/sms/verify
```

```json
{ "session_id": "00000000-0000-0000-0000-000000000001", "code": "123456" }
```

**Response:** `{ "token": "<action token JWT>" }`

### Step 4: Confirm Phone Number

```
PUT /api/v1/user/phone-number/confirm
```

```json
{ "action_token": "<action token from step 3>" }
```

Response: `{}`.

---

## Verification Statuses

`verification.status` enum (API reference): `None`, `Pending`, `Approved`, `Rejected`, `Canceled`, `Applied`, `InReview`.

| Status | Description |
|--------|-------------|
| `None` | No verification submitted |
| `Applied` | User has unfinished steps in the SumSub SDK, or incomplete data was provided during Shared / KYC-sharing-via-API flows |
| `Pending` | Verification checks being executed on Wirex side |
| `InReview` | Verification checks being executed on Wirex side |
| `Approved` | Verification approved — user is ready to use all features |
| `Canceled` | Verification was cancelled — contact Wirex support |
| `Rejected` | Verification was rejected — contact Wirex support |

> **Docs inconsistency:** the KYC overview and User Information pages now list `None`, `Applied`, `InReview`, `Approved`, `Rejected`, `Canceled` (one `l`) and omit `Pending`, which stays in the API reference enum above. The docs do not publish a status transition diagram.

---

## Error Handling

All errors follow the standard format:

```json
{
  "error_reason": "ErrorGeneral",
  "error_description": "Request failed validation",
  "error_category": {
    "category": "CategoryValidationFailure",
    "http_status_code": 400
  },
  "error_details": [
    { "key": "initial_data.profile.email", "details": "Email is invalid or missing" }
  ]
}
```

### Registration Errors

| Error Reason | Description |
|-------------|-------------|
| `ErrorInvalidField` | Field format invalid (user_address, email, country, etc.) |
| `ErrorNotFound` | Wallet not registered in Accounts contract |
| `ErrorAlreadyExists` | Email or wallet address already registered |

The guides list these reasons without a per-reason HTTP status (the example response above shows `ErrorInvalidField` under `CategoryValidationFailure`, 400). Missing required fields are listed in the validation tables as "Missing / Required field", without a named reason.

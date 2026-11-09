# User Profile and Capabilities Reference

## User Profile Endpoint

```
GET /api/v2/user
Authorization: Bearer {token}
X-User-Wallet: {userEoaAddress}
X-Chain-Id: {chainId}
```

With an S2S token, provide **exactly one** of `X-User-Wallet` (EOA, not the Smart Wallet), `X-User-Email` or `X-User-Id` (more than one is rejected with `ErrorInvalidField`, none with `ErrorMissingField`). With a Wirex user token, identity is in the token. A missing user returns `400` with `ErrorNotFound` ("User account not found"). The guide says there is no `404`, but the API reference for `GET /api/v2/user` also lists a `404` "User not found" (docs differ; handle both). The capabilities block is assembled from the user's cards and bank accounts, so a card or banking outage fails the whole call with `500` rather than returning a partial profile.

The same object is delivered by the `POST {your_webhook_base_url}/v2/webhooks/user` webhook.

### Complete Response Schema

```json
{
  "id": "00000000-0000-0000-0000-000000000001",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "owner": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "user_address": "0xA7E41d5680dE394EaA2ed417169DFf56840Fb3EE",
  "chain_id": 8453,
  "profile": {
    "first_name": "Alex",
    "last_name": "Grey",
    "date_of_birth": "1990-01-15",
    "nationality": "GB",
    "email": "alex.grey@example.com",
    "phone_number": "+447700900123",
    "status": "Active"
  },
  "residence_address": {
    "line1": "123 High Street",
    "line2": "Flat 4B",
    "city": "London",
    "state": null,
    "post_code": "SW1A 1AA",
    "country": "GB"
  },
  "verification": {
    "status": "Approved",
    "levels": [
      { "status": "Approved", "type": "BDD", "name": "Basic Identity" },
      { "status": "Approved", "type": "SDD", "name": "Standard Due Diligence" }
    ],
    "documents": [
      { "type": "passport", "id": "doc_123", "file_type": "pdf", "added_date": "2024-01-15T10:30:00Z" }
    ]
  },
  "external_providers": [
    { "type": "cpn" }
  ],
  "capabilities": [
    {
      "type": "SepaAccount",
      "status": "Active",
      "verification_requirements": [ { "type": "SDD", "order": 1 } ],
      "prerequisites": []
    },
    {
      "type": "SepaOut1stParty",
      "status": "NotFulfilled",
      "status_reason": "Prerequisite SepaAccount is not active",
      "verification_requirements": [ { "type": "SDD", "order": 1 } ],
      "prerequisites": ["SepaAccount"]
    }
  ]
}
```

`id` and `owner` are **deprecated** mirrors of `user_id` and `user_address`; read the new names.

---

## Profile Statuses

| Status | Meaning | Description |
|--------|---------|-------------|
| `Active` | Fully operational | User account is active |
| `Pending` | Awaiting setup | User registered but not yet active |
| `Blocked` | Suspended | Account is blocked |
| `Deleted` | Closed | Account is deleted |

The docs list these four values (`Active`, `Pending`, `Blocked`, `Deleted`) without describing transitions.

---

## Verification Levels

| Level | Full Name | Documents | Unlocks |
|-------|-----------|-----------|---------|
| `BDD` | Basic Due Diligence | PoI + selfie | Account creation, limited features |
| `SDD` | Standard Due Diligence | PoI + PoA + selfie | Bank accounts, cards, standard transfers; higher spending limits |
| `EDD` | Enhanced Due Diligence | Additional documentation | Higher limits, additional features |

PoI = Proof of Identity, PoA = Proof of Address. The API enum (`verification.levels[].type`, `verification_requirements[].type`) is `N/A`, `BDD`, `SDD`, `XDDBridgeBase`, `EDD`. Each entry in `verification.levels` has `type`, `status` (`Pending`, `Approved`, `Rejected`, …) and a human-readable `name`.

---

## Capabilities System

Capabilities are the **feature-gating mechanism** in Wirex BaaS. Each capability represents a specific product or service that a user may or may not have access to. The capabilities array on the user profile dynamically reflects the user's current state.

### Capability Object Schema

```json
{
  "type": "VisaVirtualCard",
  "status": "ActivationNotStarted",
  "provider": "Wirex",
  "status_reason": "Activation in progress, please wait for confirmation",
  "verification_requirements": [ { "type": "SDD", "order": 1 } ],
  "prerequisites": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | The capability identifier (see tables below) |
| `status` | string | Current status of this capability for the user |
| `provider` | string | Which side serves the capability: `Wirex` or `Bridge` (shown on card capabilities in the Capabilities guide) |
| `status_reason` | string | Optional explanation of the status |
| `verification_requirements` | array of objects | Required verification levels, each `{ "type": "SDD", "order": 1 }`, ordered by `order` |
| `prerequisites` | array of strings | Other capability types that must be `Active` first |

### Capability Statuses

| Status | Meaning | User Action |
|--------|---------|-------------|
| `Active` | Capability is available for use | Feature is accessible |
| `ActivationNotStarted` | Requirements met, activation needed | Call the activation endpoint |
| `InProgress` | Activation in progress | Wait for completion |
| `NotFulfilled` | Requirements not met | Complete KYC or prerequisites |
| `NotRequired` | Present in the API reference enum; not described in the guides | — |
| `NotAvailable` | Not available for this user | Cannot be activated |
| `ExternalProviderRegistrationPending` | An external provider is still onboarding the user | Wait; the capability moves on its own |
| `ExternalProviderVerificationRequired` | Wallet ownership must be verified with the external provider | Complete the provider's wallet verification |

Typical flow: `NotFulfilled` → `ActivationNotStarted` → `InProgress` → `Active`.

---

## Capability Types

Bank account capabilities require KYC verification before activation. Example: `SepaOut1stParty` requires `SepaAccount`; read each capability's `prerequisites` array instead of assuming a rule.

### Card Capabilities

| Capability | Description |
|-----------|-------------|
| `VisaVirtualCard` | Issue virtual Visa cards |
| `VisaPlasticCard` | Issue physical Visa cards |
| `VisaMetalCard` | Issue metal Visa cards |
| `BridgeVirtualCard` | Virtual cards on the Bridge rail; resolved only where `VisaVirtualCard` is not active |
| `BridgePlasticCard` | Physical cards on the Bridge rail; resolved only where `VisaPlasticCard` is not active |
| `CardTransfer` | Push to card transfers |
| `CardTopup` | Top up the wallet from a payment card |
| `WalletTopup` | Top up from a device payment sheet (Apple Pay / Google Pay), separate from `CardTopup` (documented in the Capabilities guide) |

### SEPA Banking (Europe)

`SepaAccount` (SEPA bank account, IBAN), `SepaIn1stParty`, `SepaIn3rdParty`, `SepaOut1stParty`, `SepaOut3rdParty`.

### ACH Banking (United States)

`AchAccount`, `AchIn1stParty`, `AchIn3rdParty`, `AchOut1stParty`, `AchOut3rdParty`.

USD accounts support both ACH and Fedwire. ACH and Fedwire are supported in all US states and territories except Texas (TX) and New York (NY): users resident there cannot open a USD account ([Bank Account Availability](https://docs.wirexapp.com/docs/bank-account-availability)). Activation: `POST /api/v1/bank/accounts` ([Capabilities guide](https://docs.wirexapp.com/docs/retail-capabilities)).

### Faster Payments (United Kingdom)

`FasterPaymentsAccount`, `FasterPaymentsIn1stParty`, `FasterPaymentsIn3rdParty`, `FasterPaymentsOut1stParty`, `FasterPaymentsOut3rdParty`.

### SPEI (Mexico)

`SpeiAccount`, `SpeiIn1stParty`, `SpeiIn3rdParty`, `SpeiOut1stParty`, `SpeiOut3rdParty`.

### Regional / Other Outbound Capabilities

| Capability | Region | Description |
|-----------|--------|-------------|
| `PixOut3rdParty` | Brazil | Send Pix transfers |
| `FpsHkOut3rdParty` | Hong Kong | Send FPS HK transfers |
| `ChatsOut3rdParty` | Hong Kong | Send CHATS transfers |
| `CipsOut3rdParty` | China | Send CIPS transfers |
| `SwiftOut3rdParty` | — | Send SWIFT transfers |
| `ImpsOut3rdParty` | India | Send IMPS transfers |
| `InstapayOut3rdParty` | Philippines | Send InstaPay transfers |
| `BiFastOut3rdParty` | Indonesia | Send BI-FAST transfers |
| `NipOut3rdParty` | Nigeria | Send NIP transfers |
| `IppOut3rdParty` | Thailand | Send IPP transfers |
| `PseOut3rdParty` | Colombia | Send PSE transfers |

The API reference enum also contains `FedwireOut3rdParty`, `CpnExternalProfile`, `TripleAExternalProfile`, `SavingsAccount` and `Loan`, which the retail guides do not describe. `StableExchange` is described in the FX guide: it must be `Active` on the user for FX (users without it are refused on both FX endpoints).

---

## Feature Gating Code Examples

### JavaScript: Check If User Can Issue Virtual Card

```javascript
async function canIssueVirtualCard(userToken, userEoaAddress) {
  const response = await fetch('https://api-baas.wirexapp.com/api/v2/user', {
    headers: { Authorization: `Bearer ${userToken}`, 'X-User-Wallet': userEoaAddress, 'X-Chain-Id': '8453' },
  });
  const user = await response.json();

  const virtualCardCap = user.capabilities.find(
    (cap) => cap.type === 'VisaVirtualCard'
  );

  if (!virtualCardCap) {
    console.log('Virtual card capability not available for this user.');
    return false;
  }

  if (virtualCardCap.status === 'Active') {
    console.log('User can issue virtual cards.');
    return true;
  }

  if (virtualCardCap.status === 'NotFulfilled') {
    console.log(
      `Requirements not met: ${virtualCardCap.verification_requirements.map((r) => r.type).join(', ')}`
    );
    return false;
  }

  console.log(`Capability status: ${virtualCardCap.status}`);
  return false;
}
```

### JavaScript: Build Feature Menu from Capabilities

```javascript
async function buildFeatureMenu(userToken, userEoaAddress) {
  const response = await fetch('https://api-baas.wirexapp.com/api/v2/user', {
    headers: { Authorization: `Bearer ${userToken}`, 'X-User-Wallet': userEoaAddress, 'X-Chain-Id': '8453' },
  });
  const user = await response.json();

  const featureMap = {
    VisaVirtualCard: { label: 'Virtual Card', icon: 'credit-card' },
    VisaPlasticCard: { label: 'Physical Card', icon: 'card' },
    SepaAccount: { label: 'EUR Bank Account', icon: 'bank' },
    SepaOut3rdParty: { label: 'Send EUR', icon: 'send' },
    AchAccount: { label: 'USD Bank Account', icon: 'bank' },
    AchOut3rdParty: { label: 'Send USD', icon: 'send' },
    FasterPaymentsAccount: { label: 'GBP Bank Account', icon: 'bank' },
    FasterPaymentsOut3rdParty: { label: 'Send GBP', icon: 'send' },
  };

  const menuItems = [];

  for (const cap of user.capabilities) {
    const feature = featureMap[cap.type];
    if (!feature) continue;

    menuItems.push({
      ...feature,
      type: cap.type,
      enabled: cap.status === 'Active',
      status: cap.status,
      reason: cap.status_reason,
      requirements: cap.verification_requirements,
    });
  }

  return menuItems;
}
```

---

## Profile Response Field Reference

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string (UUID) | User account identifier |
| `user_address` | string | EOA address that owns this account |
| `id` | string | **Deprecated.** Mirrors `user_id` |
| `owner` | string | **Deprecated.** Mirrors `user_address` |
| `chain_id` | integer | Chain where the account was registered (e.g., 8453 for Base) |
| `profile` | object | User profile information |
| `residence_address` | object | User's residential address |
| `verification` | object | KYC verification status, levels and documents |
| `external_providers` | array | Linked external service providers |
| `capabilities` | array | List of capability objects |
| `last_login_ip` | string | IP address of the user's last non-S2S login; omitted until one is recorded |
| `tags` | array of string | Platform tags on the account; omitted when none |

### Profile Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `profile.status` | string | `Active`, `Pending`, `Blocked`, `Deleted` |
| `profile.email` | string | Registered email address |
| `profile.first_name` | string | First name (from KYC) |
| `profile.last_name` | string | Last name |
| `profile.date_of_birth` | string | `YYYY-MM-DD` |
| `profile.nationality` | string | ISO 3166-1 alpha-2 |
| `profile.phone_number` | string | Phone number with country code |
| `profile.registration_date` | string | When the user registered (ISO 8601, UTC) |

The profile object has no `phone_confirmed`, `created_at` or `updated_at` fields in the API reference.

### Residence Address Fields

| Field | Type | Description |
|-------|------|-------------|
| `residence_address.line1` | string | Street address line 1 |
| `residence_address.line2` | string | Street address line 2 (optional) |
| `residence_address.city` | string | City |
| `residence_address.state` | string | State or province (optional) |
| `residence_address.post_code` | string | Postal / ZIP code |
| `residence_address.country` | string | ISO 3166-1 alpha-2 |

### Verification Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `verification.status` | string | `None`, `Pending`, `Approved`, `Rejected`, `Canceled`, `Applied`, `InReview` |
| `verification.levels` | array | Objects with `type` (`BDD`, `SDD`, …), `status` and `name` |
| `verification.documents` | array | Submitted documents with `type` (passport, identity_card, driver_license, proof_of_address), `id`, `file_type`, `added_date` |

### External Providers

`external_providers` is an **array** of provider objects. Each has `type` (`Cpn`, `Triplea`, `WirexApp`), optional `account_id`, and a provider-specific sub-object (`cpn`, `triplea`, `wirex_app`, `freshdesk`) filled according to the type. `wirex_app` carries migration info (`user_id`, `sumsub_id`, `migration_stage`, `migration_status`); `triplea` carries `verification_status` (`None`, `Pending`, `Approved`, `Rejected`, `InReview`) and identifiers.

### Linking a Freshdesk Contact

```
PUT /api/v1/user/freshdesk-id
```

Body `{ "freshdesk_id": "1234567890" }` (required) stores the user's Freshdesk contact id on their Wirex profile so helpdesk tickets can be matched to the Wirex user.

---

## Common Patterns

### Poll for Verification Approval

```javascript
async function waitForApproval(userToken, userEoaAddress, maxAttempts = 60, intervalMs = 5000) {
  for (let i = 0; i < maxAttempts; i++) {
    const response = await fetch('https://api-baas.wirexapp.com/api/v2/user', {
      headers: { Authorization: `Bearer ${userToken}`, 'X-User-Wallet': userEoaAddress, 'X-Chain-Id': '8453' },
    });
    const user = await response.json();

    const status = user.verification.status;
    console.log(`Attempt ${i + 1}: Verification status = ${status}`);

    if (status === 'Approved') {
      console.log(`Verified levels: ${user.verification.levels.map((l) => l.type).join(', ')}`);
      return user;
    }

    if (status === 'Rejected' || status === 'Canceled') {
      throw new Error(`Verification ${status}`);
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }

  throw new Error('Verification polling timed out');
}
```

### Check All Requirements Before Action

```javascript
function canPerformAction(user, requiredCapability) {
  // Check profile is active
  if (user.profile.status !== 'Active') {
    return {
      allowed: false,
      reason: `Account is ${user.profile.status}`,
    };
  }

  // Check KYC is approved
  if (user.verification.status !== 'Approved') {
    return {
      allowed: false,
      reason: `KYC status is ${user.verification.status}`,
    };
  }

  // Check capability
  const cap = user.capabilities.find((c) => c.type === requiredCapability);

  if (!cap) {
    return {
      allowed: false,
      reason: `Capability ${requiredCapability} not found`,
    };
  }

  if (cap.status !== 'Active') {
    return {
      allowed: false,
      reason: cap.status_reason || `Capability status is ${cap.status}`,
      requirements: cap.verification_requirements,
      prerequisites: cap.prerequisites,
    };
  }

  return { allowed: true };
}
```

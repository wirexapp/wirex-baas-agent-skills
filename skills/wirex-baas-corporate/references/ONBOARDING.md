# Wirex BaaS Corporate — Onboarding, KYB and Capabilities

Detail for deploying the corporation wallet, registering on-chain and through the API, logging in, passing KYB and reading capabilities. Guides: [Onboarding a Corporation](https://docs.wirexapp.com/docs/corporate-onboarding), [Wallet Deployment](https://docs.wirexapp.com/docs/corporate-onchain-registration), [Registering a Corporation](https://docs.wirexapp.com/docs/corporate-registration), [Verification (KYB)](https://docs.wirexapp.com/docs/corporate-verification), [Corporation Profile](https://docs.wirexapp.com/docs/corporate-info), [Capabilities](https://docs.wirexapp.com/docs/corporate-capabilities).

## Table of Contents

- [Sequence](#sequence)
- [On-Chain Wallet Deployment](#on-chain-wallet-deployment)
- [Credentials and Contracts](#credentials-and-contracts)
- [API Registration](#api-registration)
- [Login](#login)
- [KYB Verification](#kyb-verification)
- [Corporation Profile](#corporation-profile)
- [Capabilities](#capabilities)
- [Wallets and Balances](#wallets-and-balances)
- [Global Wallets](#global-wallets)
- [Onboarding Errors](#onboarding-errors)

---

## Sequence

| Step | Action | Notes |
|---|---|---|
| 1 | `POST /api/v1/token` | Partner token |
| 2 | Deploy corporation wallet | Kernel v3.1 Account Abstraction wallet; its address is `corporation_address` |
| 3 | `installModule`, `changeRootValidator` | Install `FundsManagement` (executor, module type 2), `ExecutionDelayCorporatePolicy` and `CorporateValidator` |
| 4 | `createCorporationForCorporateWallet(partnerId, wallet)` on `CorporateAccounts` | Permissionless call; owner is the `creator` recorded in `CorporateValidator` install data |
| 5 | `POST /api/v1/corporations/register` | Owner only; legal details |
| 6 | `POST /api/v1/corporations/login` | Corporation token |
| 7 | `POST /api/v1/corporations/level-token` | KYB in the SumSub SDK |
| 8 | Poll `GET /api/v1/wallets` | Wait until the `Primary` wallet reads `Confirmed` before any funded flow |

A `/v2/webhooks/corporations` notification is delivered on each corporation state change, starting with the on-chain `CorporationCreated` event.

## On-Chain Wallet Deployment

- The corporation is an Account Abstraction wallet. There is no separate on-chain corporate entity: the wallet address is the corporation address used by every API call.
- `CorporateValidator` is the signer module of the root validator. On every UserOperation it recovers the signer and checks the signer's on-chain role in `CorporateAccounts`. Account-change operations need `Su` or `AccountSu`; every other operation needs `Su`, `TransactionSu` or `TransactionCreate`. This is what lets employees sign for the corporation.
- `ExecutionDelayCorporatePolicy` must be the root validator's **single** policy entry. A wallet with the retail `ExecutionDelayPolicy` is refused with `Policy is not the execution delay policy`.
- `CorporateValidator` install data is 36 bytes: `bytes16 parentEntity` followed by `address creator`. `parentEntity` is your `partner_id`. The `creator` becomes the corporation owner and is the address sent as `X-User-Wallet` at registration.
- `createCorporationForCorporateWallet(parentEntity, wallet)` reverts with: `Invalid parent entity`, `Invalid wallet address`, `Missing executor module`, `Policy data is not as it should be`, `Policy is not the execution delay policy`, `Signer is not CorporateValidator`, `ParentEntity mismatch`, `Creator not set in validator`, `Corporation already exists`.
- Read back with `getCorporation`: `status` 0 UNKNOWN, 1 PENDING, 2 ACTIVE, 3 BLOCKED, 4 DELETED; `verificationStatus` 0 UNKNOWN, 1 APPLIED, 2 IN_REVIEW, 3 APPROVED, 4 CANCELLED, 5 REJECTED; `walletStatus` 0 UNKNOWN, 1 CONFIRMED, 2 REJECTED. The Wirex KYC oracle advances these; they are not partner-writable.
- `createCorporation` is **obsolete**: it yields a single-key corporation that no employee can ever sign for. Do not use it for a new corporation.
- `@wirexapp/wpay-baas-sdk`: `registerInCorporateAccounts()` takes the obsolete `createCorporation` path, and its wallet setup helpers (`signInPolicyAndExecutor()`, `signInPolicy()`) install the retail policy and not `CorporateValidator`. Request the corporation wallet setup helper from Wirex instead.

Default on-chain roles are seeded in `CorporateAccounts` and match the API role ids; see [TEAM-AND-PERMISSIONS.md](TEAM-AND-PERMISSIONS.md).

## Credentials and Contracts

| Item | Detail |
|---|---|
| `client_id`, `client_secret` | Issued per environment; the company must be registered as a **corporate** company (a retail `client_id` gets `500` and `You're in the wrong place. Please go to retail api with this kind of requests.`). There are no shared corporate sandbox credentials; request them from your Wirex account manager |
| `partner_id` | 16-byte hex (`bytes16`); scopes every on-chain corporation, employee and role to your partner entity. Not secret |
| Bundler, paymaster, RPC | Returned by `GET /api/v1/config` (ZeroDev bundler and paymaster) |

ContractRegistry addresses (resolve every other contract with `contractByName(name)`):

| Environment | Chain | Chain ID | ContractRegistry |
|---|---|---|---|
| Sandbox | Base Sepolia | `84532` | `0xC801a0f38E20500B5840c4927553b3409890bc3c` |
| Sandbox | Stellar Testnet | `9223372036854775806` | `CB2F7E7QVPUHUCMKIWNBTEPLL2S3GYDGQJQECIRKQ2PRKL2U3XNXOSNO` |
| Production | Base | `8453` | `0xAFa697ebC7919998AF5CdE325Fbe990dC926aae4` |
| Production | Stellar | `9223372036854775806` | `CCRZBVBWNMDYOOQNJKB6TGMTSE5HE57RWQUGTN3AWBHMDHO45UCABJRE` |

Registry names: `CorporateAccounts`, `CorporateValidator`, `ExecutionDelayCorporatePolicy`, `FundsManagement`, `TokensRegistry`.

Platform tokens on Base (resolve at runtime from `GET /api/v1/config/tokens`):

| Token | Production (8453) | Sandbox (84532) |
|---|---|---|
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (6 dec) | `0x7Af7cDbd557eD302F7538Db1e3d094C8BBcA665c` (6 dec) |
| USDT | `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` (6 dec) | `0x2C6c7c00ACa9B9D8446d107367485079b0471706` (18 dec) |
| EURC | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` (6 dec) | `0xF70461ffb413981852683657A310892227e3989e` (6 dec) |
| WUSD | `0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2` (18 dec) | `0x0774164DC20524Bb239b39D1DC42573C3E4C6976` (18 dec) |
| WEUR | `0x379e120C1921bFD8f5E0A1a3C699e7e800b66606` (18 dec) | `0x5c55F314624718019A326F16a62A05D6C6d8C8A2` (18 dec) |

`WUSD` and `WEUR` are `Synthetic` unified tokens (balance-bearing, carry `base_token_address`); `USDC`, `USDT`, `EURC` are `Regular` ERC-20s.

## API Registration

```
POST /api/v1/corporations/register
```

Headers: `Authorization: Bearer <partner_token>`, `X-User-Wallet` (owner EOA), `X-User-Email` (owner email), `X-Chain-Id`. Both identity headers are required, otherwise `500 ErrorGeneral` / `Failed to get user from context`.

```json
{
  "corporation_address": "<corporation_wallet_address>",
  "corporation_name": "<legal_name>",
  "corporation_registration_number": "<UPPERCASE_NUMBER>",
  "corporation_registration_country": "GB"
}
```

Response: `{}`. Only `corporation_address` is required by the API, but send all four: a corporation without a country resolves to an empty capability set and every capability check fails with `Capability is not active`.

Checks: the caller's `X-User-Wallet` must equal the corporation's `owner_address` and the caller's employee record must hold the `Owner` role; otherwise `401 ErrorGeneral` / `Only owner of the corporation can register the corporation`. Registration returns no data; confirm with login and `GET /api/v1/corporations`. After registration the corporation is `Pending` and `verification_status` is `None` or `Pending`.

Server errors: `Failed to query corporation` (not registered on-chain for this `partner_id`), `Failed to query employee` (owner assignment did not land), `Failed to begin corporation registration` (downstream rejection, also when already registered), `Failed to complete employee registration` (retry).

## Login

```
POST /api/v1/corporations/login
```

Headers: `Authorization: Bearer <partner_token>`, `X-User-Wallet`, `X-User-Email`, `X-Chain-Id`. Body: `{"corporation_address": "<corporation_wallet_address>"}`. Response: `{"access_token": "<corporation_token>"}` with no expiry field; read `exp` from the JWT.

What login does: finds the employee by wallet, falls back to email; an `Invited` employee with no wallet is activated and bound to the supplied wallet and email (**this is how an invitee claims their account; there is no accept-invitation endpoint**); `Disabled` employees get `401` / `Employee is disabled`; an email already bound to another wallet gets `401` / `Employee registration is already completed`.

Token claims include `corporation_address`, `corporation_id`, `corporation_account_address` (primary wallet), `employee_id`, `employee_address`, `employee_email`, `role`, `role_id`, `permissions` (map of permission code to `true`), `chain_id`, `scope`, `provider`, `iat`, `exp`. The partner token `iss` ends in `/srv`; the corporation token `iss` does not.

Choosing a corporation: `GET /api/v1/employees/corporations` with the partner token and one identity header lists `corporation_descriptors[]` (`corporation_address`, `corporation_name`). Resolution order: wallet, then email, then employee id. A corporation whose record cannot be read is skipped, so a short list is not proof of no other memberships.

Privy and Crossmint identity tokens are accepted on `register`, `login` and `employees/corporations` instead of `X-User-*` headers; provider configuration is part of onboarding, contact Wirex first.

## KYB Verification

KYB runs in the SumSub SDK; Wirex issues the SDK token. There is no API for submitting, amending, cancelling or restarting KYB data.

1. `POST /api/v1/corporations/level-token` with `{"verification_level": "SDD"}` (requires `Su`). Levels: `SDD`, `EDD`, `XDDBridgeBase` (required, after `SDD`, for ACH and Fedwire; its token moves the whole corporation back into review: `verification_status` `Applied`, `verification_levels` emptied, SDD-gated capabilities `NotFulfilled` until approved), `XDDOpenPaydBase`. `N/A` is rejected (`400 ErrorInvalidField`); **any other unrecognised value, including lowercase `sdd` or a typo, silently produces an `SDD` token**.
2. Open the SumSub Web or Mobile SDK with the returned `token`. Tokens are short-lived; request a fresh one when the SDK reports expiry.
3. Track progress by webhook (`/v2/webhooks/corporations`) and by `GET /api/v1/corporations` (`verification_levels[]` is authoritative; `passed_levels[]` is obsolete).

`POST /api/v1/corporations/verification-token` (empty body, `Su`) is the `SDD` shorthand; use `level-token` for new integrations.

Level status flow: `None` -> `Pending` -> `Applied` -> `InReview` -> `Approved`, or `Rejected` / `Canceled`. Only `Approved` counts. A `Rejected` level needs Wirex intervention. Which levels a capability needs depends on the registration country; read `verification_requirements` on the capability.

Verification unlocks a capability, it does not activate it: most then read `ActivationNotStarted`.

## Corporation Profile

`GET /api/v1/corporations` is computed per request (capabilities are evaluated against country, verification levels, bank accounts and cards at call time). Fields: `corporation_address`, `owner_address`, `corporation_id`, `corporation_name`, `corporation_type` (`None`, `LimitedLiability`, `SoleTrader`, `Partnership`, `PublicLimitedCompany`, `JointStockCompany`, `Charity`), `registration_number`, `status`, `status_reason`, `verification_status`, `verification_levels[]`, `corporation_registration_address` and `corporation_contact_details` (both populated by KYB, not by registration; the address `country` drives capability evaluation), `freshdesk_id`, `capabilities[]`, `actions[]`.

Profile `status`: `Pending` -> `Active`; `Blocked`; `Deleted`. Advanced by Wirex only. While `Pending`, card and bank capabilities read `NotAvailable` / `Corporation profile is not active`.

`actions[]` lists what can be done now (match on `type`, not position): `Verify` (only while verification is in progress), `IssueVirtualCard`, `IssuePlasticCard`, `ActivateSepaDetails`, `ActivateAchDetails`, `ActivateSpeiDetails`, `ReceiveSepaTransfer`, `ReceiveAchDeposit`, `ReceiveSpeiDeposit`, `SendSepaTransfer`, `SendAchTransfer`, `SendSpeiTransfer`. `SendSpeiTransfer` and `ReceiveSpeiDeposit` are gated on `SpeiAccount`, not on the directional capability.

A `500` from this endpoint (`Failed to get corporate bank accounts` or `Failed to get corporate cards`) fails the whole call; treat it as transient and retry.

`PUT /api/v1/corporations/freshdesk-id` with `{"freshdesk_id": "<id>"}` stores the support identifier; response `{}`.

## Capabilities

Statuses: `Active`, `ActivationNotStarted` (call the activation endpoint), `InProgress`, `NotFulfilled` (missing verification level or prerequisite), `NotRequired`, `NotAvailable` (see `status_reason`).

`status_reason` values: `Country is not supported`; `Verification requirements not fulfilled`; `Prerequisite capability is not active yet`; `Prerequisite capability is not available`; `Corporation profile is not active`; `Account should be activated in order to use this capability`; `Account activation is in progress`; `This capability is no longer available for this account`; `You have reached the maximum number of virtual cards allowed` (30); `You have reached the maximum number of plastic cards allowed` (15); `Capability is not available for this corporation`.

Evaluation order: country, per-corporation overrides, verification levels, prerequisites, activation validators. `status_reason` names only the **first** unmet condition. A corporation with no registration address gets an **empty** capability list.

| Group | Capabilities |
|---|---|
| Cards | `VisaVirtualCard`, `VisaPlasticCard`, `CardTransfer` |
| SEPA | `SepaAccount`, `SepaIn1stParty`, `SepaIn3rdParty`, `SepaOut1stParty`, `SepaOut3rdParty` |
| ACH | `AchAccount`, `AchIn1stParty`, `AchIn3rdParty`, `AchOut1stParty`, `AchOut3rdParty` |
| SPEI | `SpeiAccount`, `SpeiIn1stParty`, `SpeiIn3rdParty`, `SpeiOut1stParty`, `SpeiOut3rdParty` |
| Faster Payments | `FasterPaymentsAccount`, `FasterPaymentsIn1stParty`, `FasterPaymentsIn3rdParty`, `FasterPaymentsOut1stParty`, `FasterPaymentsOut3rdParty` |
| CPN corridors | `CpnExternalProfile` (provisioned by Wirex), `PixOut3rdParty`, `SwiftOut3rdParty`, `CipsOut3rdParty`, `ChatsOut3rdParty`, `FpsHkOut3rdParty` |
| Fedwire (bank corridor) | `FedwireOut3rdParty`, prerequisite `AchAccount` (same USD account as ACH) |
| Triple-A corridors | `TripleAExternalProfile` (provisioned by Wirex), `ImpsOut3rdParty`, `InstapayOut3rdParty`, `BiFastOut3rdParty`, `NipOut3rdParty`, `IppOut3rdParty`, `PseOut3rdParty` |
| Exchange | `FxTransfer`, `StableExchange` |

The `*In*`, `*Out*` bank capabilities depend on the matching `*Account` capability, except `FasterPaymentsIn1stParty`, `FasterPaymentsIn3rdParty` and `FasterPaymentsOut1stParty`, which declare no prerequisite and can read `Active` before any Faster Payments account exists. Check `FasterPaymentsAccount` first.

`GET /api/v1/global/capabilities` (anonymous) returns the per-country product matrix before any corporation-specific evaluation; a country absent from the map returns an empty list.

Diagnosing a blocked capability: read `status_reason`; for verification compare `verification_requirements` with `verification_levels`; for prerequisites diagnose each entry of `prerequisites` first; for activation call `POST /api/v1/bank/accounts`; for card ceilings close a card.

## Wallets and Balances

`GET /api/v1/wallets` (no permission) returns `data[]` with `wallet_address`, `wallet_name` (`Main Wallet` for the primary unless renamed), `wallet_status` (`Unknown`, `Confirmed`, `Rejected`), `wallet_type` (`Primary`, `Secondary`, `Global`) and `balances[]` (`token_symbol`, `token_address`, `balance` (rounded to 2 decimals), `balance_precise` + `decimals` (exact, compute on these), `reference_balance`, `reference_currency`).

- The `Primary` wallet is the corporation wallet and funds every debit (card fees, bank and corridor transfers). It is created asynchronously after registration and starts `Unknown`; `Rejected` means the wallet configuration is invalid and re-registering does not repair it.
- Note: docs differ. The schema says `reference_currency` depends on the corporation's registration country; the endpoint always converts to `USD`. Do not present `reference_balance` as a local-currency figure.
- A wallet whose balance read fails returns an empty `balances` array rather than an error; do not treat it as a zero balance.
- Balances are held in unified tokens (`WUSD`, `WEUR`); a supported stablecoin is wrapped on deposit (`SyntheticWrap`), unwrapping is an on-chain operation you perform (`SyntheticUnwrap`). FX needs **regular** tokens; push-to-card accepts unified tokens directly.
- The Corporate API has no crypto withdrawal endpoint. Outbound crypto movement is on-chain from the corporation wallet; pending oracle-executed withdrawals are listed by `GET /api/v1/withdrawal/requests`.
- Funding routes: on-chain transfer to `corporation_address`, fiat deposit into a corporate bank account, cross-chain deposit to a global wallet, FX swap.

## Global Wallets

`POST /api/v1/wallets/global` (`AccountSu`, `AccountCreate`, `AccountManage` or `Su`) with `wallet_address` (required) and `wallet_name`; response `{}`. It is bookkeeping: the address is only checked to be non-zero (a typo registers successfully), the wallet appears with `wallet_type` `Global` and `wallet_status` `Unknown`. The bridged deposit address is created client-side with Rhino.fi (key under `auth.rhinoApiKey` in `GET /api/v1/config`), exactly as on retail; the two calls are independent. No endpoint renames, deregisters or lists global wallets separately; registering the same address twice fails with `Failed to create global wallet`.

## Onboarding Errors

| HTTP | Reason | Message | Meaning |
|---|---|---|---|
| 500 | `ErrorGeneral` | `Failed to get user from context` | `register` / `login` need both `X-User-Wallet` and `X-User-Email` |
| 401 | `ErrorGeneral` | `Only owner of the corporation can register the corporation` | Wrong signer or not Owner |
| 401 | `ErrorGeneral` | `Employee is disabled` | Disabled employee |
| 500 | `ErrorGeneral` | `Failed to query corporation wallets` | No primary wallet yet; finish on-chain registration |
| 403 | `ErrorPermissionDenied` | `User does not have required permissions` | `level-token` and `verification-token` need `Su`; `wallets/global` needs `AccountSu`, `AccountCreate` or `AccountManage` (log in again after a role change) |
| 500 | `ErrorGeneral` | `Failed to get verification token` | Not eligible for that level or provider rejected; check the level is not already `Approved` |
| 400 | `ErrorGeneral` | `Capability is not active` | Required capability is not `Active`; read `GET /api/v1/corporations` |

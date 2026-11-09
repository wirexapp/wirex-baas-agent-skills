---
name: wirex-baas-pci-sdk
description: "Wirex BaaS PCI Compliant SDK family — Web (@wirexapp/card-topup-web, card-oct-web, card-reveal-web, card-3ds-web, card-react, card-sdk-web), React Native (@wirexapp/mobile-sdk), Flutter (wirex_mobile_sdk), iOS (WirexMobileSDK), Android (com.wirexapp.baas:mobile-sdk). Collects and reveals card data inside Wirex-controlled iframes or native views so PAN/CVV never reach your app or servers. Covers Web setup (client id / partner id, domain allowlisting, environments uat/prod, user-token getBearerToken), CSP rules (frame-src, script-src), top-up card collection (tokenizeTopUp -> cardId), payout card collection (tokenizeOctDestination -> externalCardId), reveal of PAN/expiry/CVV/PIN with action token, 3DS challenge, appearance tokens and localization, React bindings, events, PciFrameRequestError and timeouts; and the mobile SDKs (credential provider, chainId, collect profiles, reveal sessions, 3DS session, Apple Pay / Google Pay top-up checkout). Use when building card entry, card reveal or 3DS UI in a browser or mobile app without entering PCI scope."
license: Apache-2.0
compatibility: "Requires network access. Compatible with Claude Code, Codex, and all Agent Skills spec tools."
metadata:
  author: wirex
  version: "1.0"
---

# Wirex BaaS PCI Compliant SDK

## Overview

A family of client SDKs for the card-data surfaces of the retail API (top-up source card entry, push-to-card destination card entry, reveal of an issued card, top-up 3DS step), recommended by the docs for every such surface. The user types or sees card data only inside Wirex-controlled surfaces (iframes in a browser, native views on mobile), so your code and servers never receive the PAN or CVV. Use it when your app collects or displays card data and you want it out of your PCI scope. What it produces (`card_id`, external card token, completed 3DS) feeds the same REST flows (top-up, push to card, card details).

| Platform | Distribution | Docs |
|----------|--------------|------|
| Web (browser) | npm `@wirexapp/*` packages | `retail-pci-sdk-web` |
| React Native (iOS, Android) | `@wirexapp/mobile-sdk` (npm) | `retail-pci-sdk-react-native` |
| Flutter (iOS, Android) | `wirex_mobile_sdk` (pub.dev) | `retail-pci-sdk-flutter` |
| iOS (Swift, UIKit) | `WirexMobileSDK` (Swift Package Manager or CocoaPods) | `retail-pci-sdk-ios` |
| Android (Kotlin, Views) | `com.wirexapp.baas:mobile-sdk` (Maven Central) | `retail-pci-sdk-android` |

Each platform has its own `-setup`, `-reveal`, `-collect` (web: `-topup-collect`, `-payout-collect`), `-3ds`, `-appearance` and `-errors` (web: `-events`) pages; mobile adds `-wallet`; web adds `-react`. Not covered by any SDK: 3DS for purchases with an issued card (in-app approve/decline, see `wirex-baas-cards`) and the Corporate API (the SDK uses the retail user token only). The sections from Packages to Going live checklist describe the **Web SDK**; mobile is in [Mobile SDKs](#mobile-sdks-react-native-flutter-ios-android).

> **Not the same package as the TypeScript SDK.** `@wirexapp/wpay-baas-sdk` (skill `wirex-baas-sdk`) wraps the REST API and on-chain wallet operations. The PCI SDK covers only card-data surfaces. Installed and versioned independently; can be used together.

Web docs describe version `1.0.0` (first stable release); mobile docs describe `0.3.15` (RN `@wirexapp/mobile-sdk`, Flutter `wirex_mobile_sdk`, iOS `WirexMobileSDK`, Android `com.wirexapp.baas:mobile-sdk`). All `@wirexapp/*` card packages release in lockstep because they share the frame message protocol: every `@wirexapp/card-*` entry and `@wirexapp/card-sdk-core` in your lockfile must show the same version, or the loader and frame refuse to communicate.

## Packages (Web SDK)

| Package | Produces | Main creator |
|---------|----------|--------------|
| `@wirexapp/card-topup-web` | `cardId` for an external top-up card | `createCardTopUpFields` / `createCardTopUpForm` |
| `@wirexapp/card-oct-web` | `externalCardId` for a payout destination card | `createOctDestinationFields` / `createOctDestinationForm` |
| `@wirexapp/card-reveal-web` | In-frame display of PAN, expiry, CVV, PIN of an issued card | `createCardReveal` |
| `@wirexapp/card-3ds-web` | 3DS challenge outcome | `createThreeDsChallenge` |
| `@wirexapp/card-react` | React components and hooks over all of the above | see React section |
| `@wirexapp/card-sdk-core` | Shared foundation, installed automatically | none |
| `@wirexapp/card-sdk-web` | Umbrella re-exporting every package above | none |

## Setup (Web SDK)

Inputs from Wirex onboarding:

| Input | What it is |
|-------|-----------|
| Client id (partner id) | Non-secret UUID; Wirex issues it as the partner id together with your production credentials. `clientId` in SDK config, sent as `?client=<id>` on the frame URL. Not authorization, it only selects the origin allowlist |
| Registered parent origins | Exact `https://` origins of pages embedding the fields (staging and production separately; wildcard subdomains accepted after review). Held by Wirex as the frames' `frame-ancestors`. An unregistered origin renders an empty, blocked frame |

**Domain allowlisting comes first**: it is required before the first integration test and has no self-service. Send your Wirex manager one request per environment (UAT and production have separate lists; production is not inherited from UAT) with the client id (partner id), parent origins (scheme + host, plus port if not default; no paths or trailing slash), wildcard origins if needed and the font CDN origin if used. List every origin in the embedding chain (if your page is itself framed, the outer origin too). Changes apply within seconds. Blank frame, a `frame-ancestors` CSP violation in the console, or "works on UAT but not production" all mean a missing origin. `GET /api/v1/config` returns `sdkAllowedDomains` (domains your integration may run the SDK on) when the company is resolved by a token or by `X-Company-Id`.
| User token | Per-user token from `POST /api/v1/user/authorize`, returned by your `getBearerToken` callback |
| Font CDN origin | Only needed with `fontUrl` / `fontFaces`; enters the frames' `font-src` |

There are no publishable keys, SDK secrets or rotation.

Install only what you use (`@wirexapp/card-sdk-core` comes as a dependency):

```bash
npm install @wirexapp/card-topup-web
npm install @wirexapp/card-oct-web
npm install @wirexapp/card-reveal-web
npm install @wirexapp/card-3ds-web
# React apps: npm install @wirexapp/card-react   (react >= 18 peer)
# Everything:  npm install @wirexapp/card-sdk-web
```

### Environments

Config is `{ environment, clientId }`; `environment` defaults to `'prod'`. You select an environment, never a URL.

| `environment` | Frame origin | Card data | Matching BaaS |
|---------------|--------------|-----------|---------------|
| `'prod'` | `https://frames.wirexapp.com` | Live | `https://api-baas.wirexapp.com` |
| `'uat'` | `https://frames.wirexapp.tech` | Test cards only | `https://api-baas.wirexapp.tech` |
| `'dev'` | `https://frames-dev.wirexapp.tech` | Test cards only | Wirex internal |

An unknown value throws at element creation: `PCI SDK: unknown environment "<value>" — expected 'dev', 'uat' or 'prod'.` A frame origin is bound to one backend: the bearer must come from the matching BaaS environment. Never self-host, bundle, cache or reverse-proxy the frame documents. Do not set `frameOrigin` / `framePath` (frame development only).

### Which token (user token only)

`getBearerToken: () => Promise<string>` must return a **user token**. S2S company tokens from `POST /api/v1/token` are not accepted and no identity headers substitute.

1. Backend: `POST /api/v1/token` (`grant_type: client_credentials`) -> S2S token, stays on backend.
2. Backend: `POST /api/v1/user/authorize` with the S2S token, `X-Chain-Id`, and exactly one of `X-User-Wallet` (the EOA, not the Smart Wallet), `X-User-Email`, `X-User-Id` -> `{ access_token, expires_at }`.
3. Send `access_token` to the browser over your session channel.
4. Refresh before `expires_at`.

The callback runs before each frame request, so return a fresh token every time. A token expiring between mount and submit is the most common cause of a failed tokenize.

| Element | When `getBearerToken` runs |
|---------|----------------------------|
| Per-field collect (`createCardTopUpFields`, `createOctDestinationFields`) | At tokenize only |
| Combined collect (`createCardTopUpForm`, `createOctDestinationForm`) | At mount and at tokenize |
| Reveal (`createCardReveal`) | At mount |

### Content Security Policy

```
Content-Security-Policy:
  frame-src https://frames.wirexapp.com;
  script-src 'self';
```

- `frame-src`: the frame origin for your environment (`https://frames.wirexapp.tech` in non-production) AND the 3DS orchestrator origin from your onboarding pack, the origin of `three_ds_state.url` (the 3DS page is served by a Wirex backend origin, not the frame origin).
- `script-src 'self'`: the SDK is bundled from npm.
- No `connect-src` entry is needed; the SDK makes no network calls from your page.

### Timeouts

Frame ready handshake 10 s (`PCI frame did not become ready in time`); init or tokenize request 30 s (`PCI frame request timed out`). A mount timeout is usually an unregistered parent origin.

### Sandbox test cards

`4242 4242 4242 4242` (Visa) and `5555 5555 5555 4444` (Mastercard) tokenize successfully; any future expiry and any 3-digit CVV pass. Ask your Wirex contact for 3DS challenge / frictionless triggers.

## Top-up card collection (`@wirexapp/card-topup-web`)

Requires the `CardTopup` capability active (`GET /api/v2/user`). Two variants with identical config and result; per-field is recommended, do not mix them.

| | Per-field | Combined |
|---|-----------|----------|
| Creator | `createCardTopUpFields(sdk, config)` | `createCardTopUpForm(sdk, config)` |
| Iframes | one each: `number`, `expiry`, `cvv`, `name` | one, stock layout |
| Mount | `field(name).mount(container)` x4 | `mount(container)` once |

Config: `{ auth: { getBearerToken }, appearance?, strings?, onChange? }`. `appearance` and `strings` are read at mount only.

```javascript
import { createCardTopUpFields } from '@wirexapp/card-topup-web';

const topUp = createCardTopUpFields(
  { environment: 'uat', clientId: '<client-uuid>' },
  {
    auth: { getBearerToken: () => session.getAccessToken() },
    onChange: state => { submitButton.disabled = !state.complete; },
  },
);
await topUp.field('number').mount(document.querySelector('#card-number'));
await topUp.field('expiry').mount(document.querySelector('#card-expiry'));
await topUp.field('cvv').mount(document.querySelector('#card-cvv'));
await topUp.field('name').mount(document.querySelector('#card-name'));

const result = await topUp.tokenizeTopUp({
  billingDetails: { line1: '1 High Street', city: 'London', zipCode: 'N1 9GU', country: 'GB' },
  label: 'Personal Visa',
});
// { cardId, brand, bin, last4, expiryMonth, expiryYear }
```

1. Mount all four fields (the number field aggregates the others and issues the request).
2. Gate submit on `onChange` state `{ complete, brand: 'Visa' | 'MasterCard' | 'unknown', fields: { number: { valid, touched }, ... } }`.
3. `tokenizeTopUp({ billingDetails: { line1*, line2, city*, state, zipCode*, country* (ISO alpha-2) }, label? })`. `label` falls back to the typed cardholder name. Store only `cardId`; `bin` and `last4` are safe to display.
4. `POST /api/v1/cards/topup/estimate` with `external_card_id` = `cardId`, `destination_amount`, `destination_token_address`; then `POST /api/v1/cards/topup/execute` with `estimation_id`. Headers: `Authorization`, `X-User-Wallet`, `X-Chain-Id`, `Content-Type: application/json`.
5. If the execute response has `three_ds_state.url`, run the 3DS element (below); `flow` is `Unknown` at execute, so always run it when `url` is present.
6. `topUp.destroy()` on view unmount.

Throws: `Field "<name>" is not part of the "topup" profile`; `Field "<name>" already created for this group`; `The card-number field is not mounted`.

## Payout card collection (`@wirexapp/card-oct-web`)

Requires `CardTransfer` capability. Profile `oct-destination` renders the card-number field only (no CVV, no expiry).

```javascript
import { createOctDestinationFields } from '@wirexapp/card-oct-web';

const oct = createOctDestinationFields(sdk, { auth: { getBearerToken }, onChange });
await oct.field('number').mount(document.querySelector('#destination-card-number'));
const result = await oct.tokenizeOctDestination({
  cardholderName: 'JANE DOE', cardLabel: 'Sister - Visa', isSaved: true, isThirdParty: true,
});
// { externalCardId, brand, bin, last4 }
```

Params: `cardholderName` (required, uppercase as printed), `cardLabel` (required), `isSaved` (required), `isThirdParty` (required; `false` if sender is the cardholder), `userId` (optional UUID, sent as `user_id` query parameter).

1. Create recipient: `POST /api/v2/recipients` with `type: "Card"`, `card.card_id` = `externalCardId`, `card.card_pan_last` = `last4`.
2. `POST /api/v1/cards/transfer/estimate` with `external_card_id` = `externalCardId`, `currency`, `amount`, `tokens`.
3. `POST /api/v1/cards/transfer` with `estimation_id`, `token_address`.

`externalCardId` is the card token, not the recipient `payment_details[].id` (not accepted by transfer endpoints). Any other field name throws `Field "<name>" is not part of the "oct-destination" profile`. Third-party transfers carry extra compliance requirements: see the push-to-card docs.

## Reveal (`@wirexapp/card-reveal-web`)

Shows PAN, expiry, CVV, PIN in an iframe; copy-to-clipboard runs inside the frame (only reveal gets `clipboard-write`). Your page never sees values.

1. Mint an `action_token` right before mounting (5 min validity, scope `GetCardDetails`, one token covers PAN/CVV/PIN; mint a fresh one each time the user opens the details view): `POST /api/v1/confirmation/signature/verify` with `{ action_type: "GetCardDetails", message_signature, nonce }`. Signed message: `By signing this I confirm that I am executing action GetCardDetails at <nonce>` where `nonce` is Unix seconds. SMS OTP gives the same token under field name `token`.
2. Mount:

```javascript
import { createCardReveal } from '@wirexapp/card-reveal-web';

const reveal = createCardReveal(sdk, {
  cardId, actionToken,
  fetchDetails: true, fetchCvv: true,
  fields: ['cardholder', 'number', 'expiry', 'cvv'],
  cardholderName: 'ALEX GREY',
  auth: { getBearerToken: () => session.getAccessToken(), userEmail: user.email, userWallet: user.walletAddress },
  onStateChange: ({ status, errorMessage }) => { if (status === 'error') showToast(errorMessage); },
  onCopied: ({ field }) => analytics.track('card_detail_copied', { field }),
});
await reveal.mount(document.querySelector('#card-details'));
reveal.destroy(); // when the view closes
```

3. Frame calls `POST /api/v1/cards/{cardId}/details` (`number`, `expiry`), `/cvv` (`cvv`), `/pin` (`pin`); `cardholder` is rendered from `cardholderName`. Do not proxy these through your backend.

`onStateChange` status: `loading`, `ready` (at least one row loaded; partial failure shows an em dash in failed rows), `error` (every fetch failed; expired token (older than 5 minutes), unknown card, wrong card status, backend failure). Option table and strings keys: [reference](references/REFERENCE.md#reveal-configuration).

## 3DS challenge (`@wirexapp/card-3ds-web`)

Runs the 3DS page for a card top-up: mount it whenever top-up execute returns `three_ds_state.url` (`flow` is `Unknown` at execute; the page runs the issuer device check, then completes frictionless or shows the challenge; a top-up whose page is never loaded stays `Pending`). It is not the in-app approval flow for purchases with an issued Wirex card (webhook-driven, see `wirex-baas-cards`). No `three_ds_state` means no 3DS step.

```javascript
import { createThreeDsChallenge } from '@wirexapp/card-3ds-web';

const challenge = createThreeDsChallenge({
  url: execute.three_ds_state.url,           // must be https://
  onComplete: status => finishTopUp(status), // exactly once
  onError: message => { showToast(message); finishTopUp('Failed'); },
  onLoad: () => hideSpinner(),
  title: '3DS Verification',
});
challenge.mount(document.querySelector('#threeds-container'));
```

`onComplete` status (case-insensitive): `Completed` (continue), `Pending` (reconcile via activity feed / webhooks), `Failed` (report). Other values: unknown, send user to activity feed. Treat a user-cancelled challenge as `Pending`, not `Failed`. Give the container explicit size (issuer pages assume 500x480 or larger) and a light background; cancel UI is yours, call `destroy()`. Errors via `onError`: `3DS verification URL is invalid`, `3DS verification returned no status`. Double mount throws `ThreeDsChallenge is already mounted`. Messages are accepted only from the challenge URL's HTTPS origin and the iframe the element created.

## Appearance and localization

Frames accept whitelisted typed tokens, not CSS. Invalid values are dropped with a console warning. `theme` is `light` or `dark` (anything else renders light). Re-theming needs a new element.

```javascript
const appearance = {
  theme: 'dark',
  variables: { colorText: '#FFFFFF', borderRadius: '12px' },
  brandBadge: { style: 'logo', tone: 'color' },
};
```

All tokens, value grammars, brand fonts (file URL only, CORS, registered CDN origin) and brand badge options: [reference](references/REFERENCE.md#appearance-variables). Labels and validation messages come from `strings` (already translated, English defaults, unknown keys ignored).

## React (`@wirexapp/card-react`)

`react >= 18` peer; components are client-only and StrictMode safe. Components: `CardTopUpProvider` + `useCardTopUp()` (`{ ready, state, tokenizeTopUp }`), `OctDestinationProvider` + `useOctDestination()` (`{ ready, state, tokenizeOctDestination }`), fields `CardNumberField`, `CardExpiryField`, `CardCvvField`, `CardholderNameField`, plus `CardReveal`, `ThreeDsChallenge`, and `PciFrameRequestError`. Provider props: `sdk`, `auth`, `appearance`, `strings`, `onChange`, `onReady`, `onMountError`, `children`. Under `OctDestinationProvider` only `CardNumberField` is valid (others throw). Details: [reference](references/REFERENCE.md#react-bindings).

## Errors and events

- Frame-reported failures (init, tokenize) reject with `PciFrameRequestError` (`message`, `status?`). Mount/lifecycle failures reject with plain `Error`.
- `Validation failed — ...` means a field is invalid; the inline message is already visible, show nothing extra. Other backend errors: generic failure plus retry. `Network error`: retry. `Card service is not configured`: contact Wirex.
- Never log a tokenize result beyond `cardId`/`externalCardId`, brand and `last4`; never put them in URLs.
- Always `destroy()` elements on unmount; elements are single-use.

```javascript
try {
  await topUp.field('number').mount(el);
} catch {
  showToast('Failed to load the secure card form');
}
```

Full error tables: [reference](references/REFERENCE.md#error-messages).

## Going live checklist

- Production domains allowlisted against the client id (partner id) by your Wirex manager; font CDN origin registered if used
- `environment` is `'prod'` or omitted
- `frame-src` allows frame origin and 3DS orchestrator origin
- All `@wirexapp/card-*` packages on one version
- `getBearerToken` returns a user token, refreshed before `expires_at`
- Mount failures and `PciFrameRequestError` handled; `destroy()` on unmount

## Mobile SDKs (React Native, Flutter, iOS, Android)

One package per platform (`@wirexapp/mobile-sdk`, `wirex_mobile_sdk`, `WirexMobileSDK`, `com.wirexapp.baas:mobile-sdk`; docs `0.3.15`; the RN and Flutter packages install the native SDKs at their own version). Card values are drawn in native views and never cross the JS/Dart bridge: your code gets tokens, states and events only. The SDK never mints, stores or moves credentials or money: your app supplies a credential provider and your backend prices and executes every top-up through the retail API. Unlike Web: no iframes, CSP or origin registration; `chainId` replaces `clientId`.

| Surface | Credentials | What it does | Result |
|---------|-------------|--------------|--------|
| Reveal | Yes | Sealed native rows with PAN, expiry, CVV, PIN | none (values stay native) |
| Collect | Yes (bearer + identity, no action token) | Native card form, profile `topup` or `oct-destination` | `cardId` / `externalCardId`, brand, bin, last4 |
| 3DS | No | Renders `three_ds_state.url`, reports the outcome | `completed` / `pending` / `failed` / `unknown` |
| Wallet | Yes | Wirex-hosted Apple Pay / Google Pay checkout for a top-up your backend priced | executed `id` + `status` (token mode) or wallet token (legacy) |

Requirements and install:

| Platform | Requirements | Install |
|----------|--------------|---------|
| React Native | RN 0.74+ with **New Architecture** (TurboModules; old architecture unsupported), React 18+, Node 18+, iOS 15+ / Xcode 26.5+, Android API 23+ with `mavenCentral()`; Expo needs a development build (not Expo Go) and the config plugin `"plugins": ["@wirexapp/mobile-sdk"]`; bare RN adds the Google Pay `<queries>` intents to `AndroidManifest.xml` | `npm install @wirexapp/mobile-sdk@0.3.15`, then `cd ios && pod install` |
| Flutter | Flutter 3.19+, Dart 3.3+, iOS 15+ / Xcode 26.5+, Android API 23+ | `flutter pub add wirex_mobile_sdk` (`^0.3.15`); `import 'package:wirex_mobile_sdk/wirex_mobile_sdk.dart';` |
| iOS | iOS 15+, Xcode 26.5+ | SwiftPM `https://github.com/wirexpay/baas-mobile-ios-sdk` from `0.3.15`, or `pod 'WirexMobileSDK', '~> 0.3.15'` |
| Android | API 23+, Java 17 bytecode, Kotlin 2.0+, `mavenCentral()` and `google()`; the SDK declares no permissions (`INTERNET` is yours) | `implementation("com.wirexapp.baas:mobile-sdk:0.3.15")` plus `kotlinx-coroutines-android` for the suspend APIs |

Integration values: `testMode` (`false` production, `true` Wirex test environment; card surfaces) or environment name `'production'`/`'test'` (wallet, `WirexWalletConfig.environment`); `chainId` (sent as `X-Chain-Id`, **required for Reveal and Collect**); optional wallet-only `clientId` (branding on the hosted checkout, not a credential; omit unless Wirex assigned one). No API takes a URL; an unknown environment name is an error.

Credential provider (one object, called on demand; RN `getAccessToken()` / `getActionToken(scope)`, Flutter/iOS/Android `accessToken()` / `actionToken(scope)`):
- Access token: the user token from `POST /api/v1/user/authorize`, sent as `Authorization: Bearer` as-is. The SDK never retries a `401`; refresh inside the callback, a stale token surfaces as `unauthorized`.
- Action token for Reveal, scope `cardData` (PAN, expiry, CVV) or `pin`: both scopes are answered with a `GetCardDetails` action token (signature verify or SMS OTP), valid 5 minutes. Throw `WirexDeclined` when the user backs out: the SDK reports declined, not error.
- Identity: set exactly one of `userEmail` or `userWallet` (both = `400`). Push changes with `WirexReveal.setIdentity` / `WirexCollect.setIdentity` (RN) only on a real change.
- Configure each surface once per process (cache the promise, clear it on failure).

Screen protection: values and the card form are drawn in a capture-proof layer (`FLAG_SECURE` on Android, secure layer on iOS, blank in the iOS Simulator). `dangerouslyDisableScreenProtection: true` is for simulator development and UI tests only; never ship it enabled.

Collect: profile `topup` -> `tokenizeTopUp({ billingDetails: { line1*, line2, city*, state, zipCode*, country* }, label? })` -> `cardId`, hand it to top-up estimate as `external_card_id`; profile `oct-destination` (`octDestination` in Flutter, `.octDestination` iOS, `OCT_DESTINATION` Android) -> `tokenizeOctDestination` -> `externalCardId` for `POST /api/v2/recipients` `card.card_id` and then `external_card_id` on push to card. `onChange` carries `isComplete`, `brand`, per-field validity, never values; enable submit only when complete and your own billing address is complete. Layouts: one form view, or a headless form with one view per field (RN `WirexCollect.createForm` + `WirexCollectFieldView`).

Reveal: one session per open details view; fields `pan`, `expiry`, `cvv`, `pin` (+ `cardholderName` drawn as given) call `/details`, `/cvv`, `/pin`; `load()` never rejects for a request failure, failures land in the snapshot (`idle`/`loading`/`ready`/`error`, per-field `loaded`/`failed`); a `pin` row fails on a virtual card or a card that is not `Active`, so omit `pin` for virtual cards. In RN rows re-mask when detached (`masksWhenDetached`, default `true`).

3DS: create a session on `three_ds_state.url`, mount the view full-size, and call `start()` only after the view is mounted (a challenge can appear within one frame). Endings: `outcome.error` present (challenge could not run; refused URL = `originRefused`) -> show error and reconcile; `unknown` without error (user closed it; payment can still complete) -> reconcile; `completed`/`pending`/`failed` is the challenge result and `pending` is not an error. The 3DS outcome is not the payment result: settle the top-up from its status/webhook.

Wallet (needs the `WalletTopup` capability, separate from `CardTopup`; iOS Apple Pay only, Android Google Pay only, RN and Flutter both): backend calls `POST /api/v1/cards/topup/estimate` with `payment_method` `apple_pay` / `google_pay` (short TTL; on `estimationExpired` re-price); checkout inputs `quote` (`estimationId`, `sourceAmount`), `providerConfig` passed **verbatim** from the `topup.providers.<name>` block of your app config (absent `apple_pay`/`google_pay` key = wallet not offered), `provider`, and `auth.checkoutToken`. Token mode: backend mints `POST /api/v1/cards/topup/token` (restricted token, one per armed quote, 15 minutes) and the checkout executes the top-up itself (events `executing` -> `executed`/`executeFailed`); legacy mode (omit `auth`) emits a wallet payment token for your backend to execute with. Never hand the user's session bearer to the checkout. The iOS Simulator reports Apple Pay unavailable: test on a device.

Per-platform class names follow one pattern: `WirexReveal`, `WirexCollect`, `WirexThreeDS`, `WirexWalletCheckoutView`, `WirexCredentialProvider`, `WirexDeclined`. Appearance (theme tokens, strings) and error shapes per surface are on each platform's `-appearance` and `-errors` pages.

## Documentation

- https://docs.wirexapp.com/docs/retail-pci-sdk (platform map, Capabilities by Platform)
- Web: https://docs.wirexapp.com/docs/retail-pci-sdk-web, `-web-setup`, `-web-topup-collect`, `-web-payout-collect`, `-web-reveal`, `-web-3ds`, `-web-appearance`, `-web-react`, `-web-events`
- React Native: https://docs.wirexapp.com/docs/retail-pci-sdk-react-native (+ `-setup`, `-reveal`, `-collect`, `-3ds`, `-wallet`, `-appearance`, `-errors`)
- Flutter: https://docs.wirexapp.com/docs/retail-pci-sdk-flutter (same suffixes)
- iOS: https://docs.wirexapp.com/docs/retail-pci-sdk-ios (same suffixes)
- Android: https://docs.wirexapp.com/docs/retail-pci-sdk-android (same suffixes)
- Restricted top-up token and 3DS handling: https://docs.wirexapp.com/docs/retail-topup-transfer

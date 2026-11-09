# Wirex BaaS PCI SDK Reference

Sources: https://docs.wirexapp.com/docs/retail-pci-sdk and the `retail-pci-sdk-*` pages. Everything below is the **Web SDK** (`retail-pci-sdk-web-*`); the mobile SDKs are summarized in SKILL.md and documented on the per-platform `retail-pci-sdk-react-native-*`, `-flutter-*`, `-ios-*` and `-android-*` pages.

## Tokenize results

Top-up (`tokenizeTopUp`):

```json
{
  "cardId": "c34908da-d980-4a9c-9b39-4dabd6f6144e",
  "brand": "Visa",
  "bin": "424242",
  "last4": "4242",
  "expiryMonth": 12,
  "expiryYear": 2028
}
```

Payout (`tokenizeOctDestination`):

```json
{
  "externalCardId": "63c4dd27-1f95-42b1-9a09-35cdda05f4c6",
  "brand": "Visa",
  "bin": "424242",
  "last4": "4242"
}
```

`brand` is `Visa`, `MasterCard` or `unknown`; `bin` is the first 6 digits; `expiryMonth` 1-12; `expiryYear` four digits.

## Top-up `tokenizeTopUp` params

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `billingDetails.line1` | string | Yes | First address line |
| `billingDetails.line2` | string | No | Second line |
| `billingDetails.city` | string | Yes | City |
| `billingDetails.state` | string | No | State or region |
| `billingDetails.zipCode` | string | Yes | Postal code |
| `billingDetails.country` | string | Yes | ISO 3166-1 alpha-2 |
| `label` | string | No | Saved-card nickname; falls back to typed cardholder name |

## Field validation (collect frames)

| Field | Rule | Message key |
|-------|------|-------------|
| `number` | Not empty | `errRequired` |
| `number` | 13-19 digits after stripping non-digits | `errCardNumber` |
| `number` | Brand detected as Visa or Mastercard | `errCardBrand` |
| `number` | Luhn check | `errCardLuhn` |
| `expiry` | `MM/YY`, month 01-12 | `errExpiryFormat` |
| `expiry` | End of expiry month in the future | `errExpired` |
| `cvv` | 3 or 4 digits | `errCvv` |
| `name` | Not empty after trimming | `errName` |

Per-field variant messages: `Validation failed — number: <message>`, `Validation failed — missing <field>` (sibling never mounted), `Validation failed — invalid <field>`.

## Strings keys

Collect (top-up; payout renders only the card-number keys): `cardNumberLabel` (Card Number), `expiryLabel` (MM/YY), `cvvLabel` (CVV), `nameLabel` (Full Name), `errRequired` (Required), `errCardNumber` (Card number must be 13-19 digits), `errCardBrand` (Only Visa/Mastercard cards are supported), `errCardLuhn` (Card number is invalid), `errExpiryFormat` (Use MM/YY format), `errExpired` (Card has expired), `errCvv` (CVV must be 3 or 4 digits), `errName` (Enter cardholder name).

Reveal: `cardholderLabel` (Cardholder), `cardNumberLabel` (Card Number), `expiryLabel` (Expiry date), `cvvLabel` (CVV/CVC), `pinLabel` (PIN), `copy` (Copy), `copied` (Copied), `loadError` (Failed to load card details).

## Reveal configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cardId` | string | Yes | Issued card to reveal |
| `actionToken` | string | Yes | Step-up token from confirmation, valid for 5 minutes |
| `fetchDetails` | boolean | Yes | Requests `number` and `expiry`; ignored when `fields` set |
| `fetchCvv` | boolean | Yes | Requests `cvv`; ignored when `fields` set |
| `fields` | array | No | Rows in order: `cardholder`, `number`, `expiry`, `cvv`, `pin`; drives which endpoints are called |
| `cardholderName` | string | No | Plain non-sensitive row |
| `auth.getBearerToken` | `() => Promise<string>` | Yes | Fresh user token |
| `auth.userEmail` | string | No | Sent as `X-User-Email` |
| `auth.userWallet` | string | No | Sent as `X-User-Wallet` |
| `appearance` | object | No | Styling tokens |
| `strings` | object | No | Translated labels |
| `onStateChange` | `(state) => void` | No | `{ status, errorMessage? }` |
| `onCopied` | `(event) => void` | No | `{ field }` only |

`fetchDetails` / `fetchCvv` are required by the TypeScript type even when `fields` is set. Without `fields`, rows are `cardholder`, then `number` + `expiry` if `fetchDetails`, then `cvv` if `fetchCvv`; `pin` is reachable only through `fields`. Chain id and API base URL are the frame service's own config, not settable.

Identity headers: a user token carries user id, wallet and email in its claims, so the API ignores these headers. Setting both is safe with a user token; an S2S token reads exactly one identity header and returns `ErrorInvalidField` (`field: user_identifier`) when given more.

Reveal row to endpoint: `number`/`expiry` -> `POST /api/v1/cards/{cardId}/details`; `cvv` -> `POST /api/v1/cards/{cardId}/cvv`; `pin` -> `POST /api/v1/cards/{cardId}/pin`; `cardholder` -> none.

Action token request (signature method):

```json
{
  "action_type": "GetCardDetails",
  "message_signature": "<signature of the message>",
  "nonce": 1700000000
}
```

Response carries `action_token`.

## Appearance variables

Color tokens: `colorText`, `colorLabel`, `colorPlaceholder`, `colorError`, `colorFocus`, `colorBackground`, `colorBorder`, `surfaceColor` (frame document background, default `transparent`). Font: `fontFamily` (font stack), `fontUrl` (one font file URL), `fontFaces` (`[{ url, weight?, style? }]`, takes precedence over `fontUrl`). Length: `fontSizeBase`, `fontSizeLabel`, `lineHeightBase`, `lineHeightLabel`, `borderRadius`, `borderWidth`, `spacingUnit`, `controlMinHeight`. Weight: `fontWeightBase`, `fontWeightLabel`.

Reveal-only: `copyIconSize` (length, default `20px`), `colorCopyIcon` (default `colorLabel`), `colorCopyIconHover` (default `colorText`), `colorCopyIconCopied` (default `colorFocus`).

Unknown tokens are dropped silently.

## Value grammars

| Type | Accepted | Max length |
|------|----------|-----------|
| color | `#RGB`..`#RRGGBBAA` hex, `rgb()`, `rgba()`, `hsl()`, `hsla()`, CSS named colors | 40 |
| length | number + `px`, `rem` or `em` (`12px`, `1.5rem`); unitless and `%` rejected | 12 |
| weight | `100`-`900`, `normal`, `bold` | n/a |
| font stack | comma-separated names (`YourBrand, Inter, sans-serif`) | 300 |
| font file URL | `https://` URL ending `.woff2`, `.woff`, `.otf` or `.ttf` (optional query) | 500 |

`var()`, `url()`, `calc()`, quotes, semicolons and braces are rejected.

## Brand fonts

Load from a font file URL, never a stylesheet. `fontFaces` items: `url` (required), `weight` (`100`-`900`, `normal`, `bold`, default `400`), `style` (`normal`/`italic`, default `normal`). Faces are named after the first family in `fontFamily`; without a valid `fontFamily`, `fontUrl` / `fontFaces` are dropped with a console warning. The font CDN origin must be registered against your client id, and the font host must send `Access-Control-Allow-Origin` covering the frame origin (`*` acceptable for public fonts). Without CORS the browser blocks the font silently (`net::ERR_FAILED` on a 200) and the next family renders.

## Brand badge (`appearance.brandBadge`)

| Option | Values | Default |
|--------|--------|---------|
| `show` | boolean | `true` |
| `style` | `logo`, `text` | `logo` |
| `tone` | `color`, `mono` (logo only, drawn in `colorLabel`) | `color` |
| `background` | color | `transparent` |
| `borderRadius` | length or `%` | `50%` |
| `size` | length or `%` | `24px` |
| `offsetX` / `offsetY` | signed length, no `%` | `0px` |

Default position: vertically centered, 16 px from the right edge.

## React bindings

Provider props (`CardTopUpProvider`, `OctDestinationProvider`):

| Prop | Required | Description |
|------|----------|-------------|
| `sdk` | Yes | `{ environment?, clientId? }` |
| `auth` | Yes | `{ getBearerToken }` |
| `appearance` | No | Styling tokens |
| `strings` | No | Translated labels |
| `onChange` | No | Aggregated validity and brand |
| `onReady` | No | Fires once when every field has mounted |
| `onMountError` | No | A field iframe failed to load or initialize |
| `children` | Yes | Field components and your layout |

Field components (`className` / `style` apply to the container only; styling comes from `appearance`): `CardNumberField` (`number`), `CardExpiryField` (`expiry`), `CardCvvField` (`cvv`), `CardholderNameField` (`name`).

```jsx
const { ready, state, tokenizeTopUp } = useCardTopUp();
const { cardId } = await tokenizeTopUp({ billingDetails: getBillingAddress() });
```

`CardReveal` props mirror the vanilla reveal config plus `sdk`, `className`, `style`, `onMountError`; it remounts and refetches when `cardId` or `actionToken` change. `ThreeDsChallenge` props mirror the vanilla 3DS config plus `className` and `style`.

Re-render rules: the collect group is destroyed and recreated (user input lost) when the values of `sdk.environment`, `sdk.clientId`, `sdk.frameOrigin`, `sdk.framePath` change or the provider profile is swapped. Changes to `auth`, `appearance`, `strings`, `onChange`, `onReady`, `onMountError` do not remount (latest used at next call; appearance is read at mount). Comparison is by value inside `sdk`, so an inline `sdk={{ ... }}` literal is fine.

Re-exported types: `PciAppearance`, `PciCollectChangeState`, `PciRevealElementConfig`, `PciRevealAuth`, tokenize parameter and result types.

## Error messages

| Message | Class | Cause | Resolution |
|---------|-------|-------|------------|
| `Validation failed — ...` | `PciFrameRequestError` | Field empty or invalid at tokenize | Show nothing extra |
| Backend error text with `status` | `PciFrameRequestError` | Tokenization rejected by Wirex | Generic failure, retry |
| `Network error` | `PciFrameRequestError` | Frame could not reach Wirex | Retry action |
| `Card service is not configured` | `PciFrameRequestError` | Frame service misconfiguration | Contact Wirex |
| `PCI frame did not become ready in time` | `Error` | Parent origin not registered, wrong environment, network, or version mismatch | Check origins, `environment`, align package versions |
| `PCI frame is not mounted` | `Error` | Tokenize before mount or after `destroy()` | Create a new element |
| `PCI frame request timed out` | `Error` | No response within 30 s | Retry |
| `PCI frame destroyed` | `Error` | `destroy()` while a request was in flight | Ignore during teardown |
| `PCI SDK: unknown environment "<value>"` | `Error` | `environment` not `dev`/`uat`/`prod` | Fix config |

`PciFrameRequestError` is re-exported by every capability package and `@wirexapp/card-react`, so `instanceof` works from any of them.

## What never reaches your page

PAN, CVV and expiry typed by the user; values fetched by reveal; clipboard content copied in a reveal frame; the frames' API endpoints (injected server-side). Events carry only validity flags, detected brand and tokenize results (`cardId` / `externalCardId`, brand, BIN, last 4, expiry month and year).

## Compliance notes

Frames sit inside Wirex's PCI DSS Level 1 Service Provider assessment (AOC on request); iframe embedding shapes the integration for SAQ A (confirm with your acquirer or assessor). Your responsibilities: never self-host/bundle/cache/proxy frame documents; never embed frames under an unregistered origin (every ancestor is checked); never log tokenize results beyond `cardId`, `externalCardId`, brand and `last4`; protect the bearer like any REST credential. Deviating voids applicability of Wirex's script-attack confirmation letter.

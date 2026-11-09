# Wirex BaaS Corporate — Employees, Roles and Permissions

Guides: [Team Management](https://docs.wirexapp.com/docs/corporate-team), [Employees](https://docs.wirexapp.com/docs/corporate-employees), [Roles](https://docs.wirexapp.com/docs/corporate-roles), [Permissions](https://docs.wirexapp.com/docs/corporate-permissions).

## Table of Contents

- [Employee Lifecycle](#employee-lifecycle)
- [Invite and Update](#invite-and-update)
- [Search, Read, Delete](#search-read-delete)
- [Default Roles](#default-roles)
- [Custom Roles](#custom-roles)
- [Permission Codes](#permission-codes)
- [Evaluation Rules](#evaluation-rules)
- [Endpoint Permission Matrix](#endpoint-permission-matrix)
- [Errors](#errors)

---

## Employee Lifecycle

`Invited` -> `Active` <-> `Disabled`; `Invalid` means the record could not be mapped.

1. `GET /api/v1/roles` — pick a `role_id`.
2. `POST /api/v1/employees/invite` — record is created as `Invited` with no wallet.
3. The employee calls `POST /api/v1/corporations/login` with a partner token and their own `X-User-Wallet` and `X-User-Email`; the record binds both and becomes `Active`. There is no accept-invitation endpoint and no password.
4. `PUT /api/v1/employees/{employeeId}/role` — change role.
5. The employee logs in again; permissions are frozen into the corporation token at login, so a role change (or a role edit) only applies to a new token.

## Invite and Update

`POST /api/v1/employees/invite` (needs `EmployeeSu` or `EmployeeManage`); response `{}`.

| Field | Required | Validation / notes |
|---|---|---|
| `first_name`, `last_name` | Yes | `^[a-zA-Z][a-zA-Z\-' ]{0,49}$`; unaccented Latin letters only |
| `email` | Yes | `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`; the employee logs in with it; cannot be changed later |
| `role_id` | Yes | UUID of a default role or one of this corporation's custom roles |
| `phone` | See note | `^\+\d{1,15}$` (E.164, no separators) |
| `department`, `job_title` | No | Free text, not enforced |
| `manager_address` | No | EVM address only, `^0x[a-fA-F0-9]{40}$` |
| `residence_address` | No | Object: `line1`, `city`, `country`, `postal_code` required when present; `line2`, `state` optional |

Note: docs differ. The API reference lists `phone` as optional; the Employees guide marks it required at invite and requires it on every employee. Because card embossing uses the employee name only when `first_name`, `last_name`, `email` and `phone` are all present, send `phone` for every employee.

Address field patterns: `line1`/`line2` `^[A-Za-z0-9&.,'’\-/() :+#]{2,100}$`; `city` `^[A-Za-z\s\-'.]{2,100}$` (no digits); `state` `^[A-Za-z][A-Za-z\s\-']{1,99}$`; `postal_code` `^[A-Za-z0-9\s\-]{3,12}$`; `country` `^[A-Z]{2}$`.

`PUT /api/v1/employees/{employeeId}` updates personal data (needs `EmployeeSu` or `EmployeeManage`): `first_name`, `last_name`, `phone`, `department`, `job_title`, `manager_address`, `residence_address`. `email` is accepted and **silently ignored** (returns `200`); to change an email delete and re-invite. Omit `phone` to keep it; an empty string is rejected. Updating personal data does not re-emboss existing cards.

`PUT /api/v1/employees/{employeeId}/role` body: `{"role_id": "<role_uuid>"}`; response `{}`.

## Search, Read, Delete

- `GET /api/v1/employees` — `page_number` (starts at `0`), `page_size`, `sort`. Needs `EmployeeSu`, `EmployeeManage` or `EmployeeView`.
- `GET /api/v1/employees/search` — `term` is required unless `manager_address` is given (then 2+ characters matching `^[A-Za-z0-9@._%+' -]{2,100}$`); `page_size` up to 100. Providing neither gives `Search term must contain at least 2 characters`.
- `GET /api/v1/employees/{employeeId}` — always allowed for your own record; others need `Su`, `EmployeeSu`, `EmployeeManage` or `EmployeeView` (`403` / `Insufficient permission to read this employee`). An id from another corporation returns `401` / `Employee does not belong to corporation` (same as an unknown id).
- `DELETE /api/v1/employees/{employeeId}` — `401` for another corporation's employee, for the Owner (`Owner cannot be deleted`) and for yourself (`Employee cannot delete itself`). Deleting does not close the employee's cards; close or block them first.

Employee item fields: `id` (the value passed as `employee_id` at card issuance), `corporation_address`, `owner_address` (the employee's own wallet once claimed; empty while `Invited`), `email`, `first_name`, `last_name`, `phone`, `department`, `job_title`, `manager_address`, `manager_name`, `role_id`, `status`, `residence_address`, `created_at`, `updated_at`.

## Default Roles

Seeded platform-wide in the `CorporateAccounts` contract (`is_global: true`); not editable or deletable.

| Role | Role id | Permissions |
|---|---|---|
| Owner | `ed7a5845-8727-4b06-9ba0-7d43ddc9e6aa` | `Su` |
| Admin | `31eba1db-0809-4d44-a479-0b696c4a2603` | `CardSu`, `EmployeeSu`, `TransactionSu`, `AccountSu` |
| Treasury | `ce3de0cc-bd42-4bc8-829c-e395fab506ef` | `TransactionSu`, `CardSu`, `AccountSu` |
| HR | `a1b2c3d4-e5f6-0718-29a0-b1c2d3e4f506` | `EmployeeSu` |
| Member | `7386b48f-df9c-49fe-8ccc-38b5b0b55932` | `TransactionCreate`, `TransactionView`, `CardView`, `AccountView`, `EmployeeView` |
| Viewer | `240d596c-8973-4203-827f-a2c994bceafa` | `TransactionView`, `CardView`, `AccountView`, `EmployeeView` |

The corporation always has exactly one Owner, assigned on-chain at registration. `Admin` and `Treasury` differ only by `EmployeeSu`.

## Custom Roles

- `POST /api/v1/roles` (`EmployeeSu`): `name` (trimmed, non-empty, at most 64 **bytes**, not characters) and `permissions` (at least one; duplicates collapse). Response is the role with `id`, `is_global: false`, timestamps.
- `PUT /api/v1/roles/{roleId}` (`EmployeeSu`): `name` and the **complete** permission set; it replaces, not adds.
- `DELETE /api/v1/roles/{roleId}` (`EmployeeSu`): defaults refused with `Default roles cannot be deleted`. Move employees off a role first; an employee whose role no longer resolves cannot get a usable token.
- `GET /api/v1/roles/{roleId}`: no permission; lets an employee read what their own role grants (the `role_id` claim).
- `Su` is refused for custom roles (`400`, `Su permission is not allowed for custom roles`) and the whole request is rejected.
- Permission names are case-sensitive: `transactioncreate` fails with `Unknown permission: transactioncreate`. Whitespace is trimmed; an empty entry gives `Permission name must not be empty`.
- A role edit does not reach employees who hold a live token; they pick it up at next login.

```json
{
  "name": "<role_name>",
  "permissions": ["TransactionCreate", "TransactionManage"]
}
```

## Permission Codes

The code is the key in the token's `permissions` claim.

| Permission | Code | Grants |
|---|---|---|
| `Su` | 101 | Everything. Cannot be assigned to a custom role |
| `CardSu` | 102 | Every card operation |
| `CardCreate` | 103 | Order cards, fee lookups and invoices; read fees, delivery options and the card order configuration |
| `CardViewDetails` | 104 | PAN, CVV, PIN; list and confirm 3DS requests |
| `CardManage` | 105 | Activate, block, unblock, close, rename; decide 3DS |
| `CardLimitManage` | 106 | Change card limits |
| `CardView` | 107 | List and read cards; read fees, delivery options and the card order configuration |
| `EmployeeSu` | 108 | Every employee and role operation |
| `EmployeeManage` | 109 | Invite, update, delete employees; change roles |
| `EmployeeView` | 110 | List and search employees; list roles |
| `TransactionSu` | 111 | Every transfer operation |
| `TransactionCreate` | 112 | Estimate and execute transfers |
| `TransactionManage` | 113 | Create, update, delete recipients |
| `TransactionView` | 114 | Read transfer data |
| `AccountSu` | 115 | Every bank account operation |
| `AccountCreate` | 116 | Activate bank account details |
| `AccountManage` | 117 | Modify account settings |
| `AccountView` | 118 | Read bank accounts |

`TransactionView`, `AccountManage` and `CardView` alone unlock no endpoint beyond what the matrix lists; they express read-only intent.

Suggested role designs from the docs: finance operator `TransactionCreate`; finance manager `TransactionCreate` + `TransactionManage`; card administrator `CardCreate`, `CardManage`, `CardLimitManage`, `CardView`; cardholder `CardView` + `CardViewDetails`; people operations `EmployeeManage` + `EmployeeView`; auditor `CardView`, `AccountView`, `EmployeeView` (card reads show only cards linked to the auditor's own employee record); treasury `AccountCreate` (activates bank details and deposit wallets).

## Evaluation Rules

1. `Su` overrides everything.
2. The permissions an endpoint declares are alternatives (any one suffices), not a conjunction.
3. An empty declaration admits any valid corporation token.
4. Failure returns `403` / `ErrorPermissionDenied` with `User does not have required permissions`; an empty permission set gives `User does not have any permissions`.
5. Permissions are resolved at login and frozen into the token.

Endpoints that require `Su` outright and cannot be delegated: `POST /api/v1/corporations/verification-token`, `POST /api/v1/corporations/level-token`. `POST /api/v1/wallets/global` was owner-only before October 2026; it now accepts `AccountSu`, `AccountCreate` or `AccountManage`. v3 cards: `GET /api/v3/cards` and `/{cardId}` need `CardSu` or `CardView`; `GET /api/v3/cards/config` needs `CardSu`, `CardCreate` or `CardView`; `POST /api/v3/cards/virtual` and `/plastic` need `CardSu` or `CardCreate`.

## Endpoint Permission Matrix

Employees and roles are in [ENDPOINTS.md](ENDPOINTS.md). Cross-domain gotchas:

| Area | Permission facts |
|---|---|
| Cards list | `CardSu` sees every card; `CardView` alone sees only cards linked to the caller and the `employee_id` filter is silently ignored |
| Card status changes | `CardSu`, `CardManage`; limits need `CardSu` or `CardLimitManage` |
| Card secrets and signature exchange | `CardSu`, `CardViewDetails` |
| 3DS | Read needs `CardViewDetails`, decide needs `CardManage`; a role with only one can see but not act (or act but not see) |
| Push-to-card | Both endpoints need `CardSu` only; `TransactionCreate` does not reach them |
| FX | `TransactionSu` only |
| Bank account activation | `TransactionSu`, `AccountSu`, `AccountCreate`; reading needs `TransactionSu`, `TransactionCreate` or `AccountView` |
| Transfers (v1, v2, v3, bulk) | `TransactionSu`, `TransactionCreate` |
| Recipients | Reads: none. Writes: `TransactionSu`, `TransactionManage`. Usage increment also accepts `TransactionCreate` |
| Activity feed, statement, withdrawal requests, wallets, corporation profile | none |

`allowed_actions` on a card reflects card status only, not the caller's permissions: a `CardView`-only caller can see `Close` listed and gets `403` when calling it.

## Errors

| HTTP | Reason | Message | Fix |
|---|---|---|---|
| 400 | `ErrorGeneral` (keyed) | `error_details` key `first_name`, `last_name`, `email`, `role_id`, `phone`, `manager_address`, `term`, `page_size` | Employee validation errors carry the field as the `key` |
| 400 | `ErrorGeneral` (keyed) | `Su permission is not allowed for custom roles`, `Unknown permission: <value>`, `At least one permission is required`, `Role name must be less than or equal to 64 bytes`, `Default roles cannot be deleted` | Fix role input |
| 500 | `ErrorGeneral` | `Failed to get role` | `role_id` does not exist for this corporation |
| 500 | `ErrorGeneral` | `Failed to invite employee` | Most often the email is already invited |
| 500 | `ErrorGeneral` | `Failed to create role` | Most often a duplicate role name |
| 500 | `ErrorGeneral` | `Failed to delete role` | Typically the role is still in use |

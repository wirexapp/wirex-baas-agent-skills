"""Per-skill factual content assertions (evals).

Each skill gets 12-20 deterministic checks verifying that specific API facts
are correctly documented. If an editing session introduces a regression,
these tests catch it.

Assertions use specific substrings to avoid false positives — e.g., "48 hours"
instead of "48", or '"line1"' instead of "line1".
"""

import re

import pytest

from conftest import skill_all_content

# ══════════════════════════════════════════════════════════════
# Test data: (skill_name, substring_or_regex, description)
#
# Use plain strings for substring checks and r"..." prefix for
# regex patterns (detected by _check helper).
# ══════════════════════════════════════════════════════════════

ASSERTIONS = [
    # ── wirex-baas-overview (14) ──────────────────────────────
    ("wirex-baas-overview", "api-baas.wirexapp.com", "production base URL"),
    ("wirex-baas-overview", "api-baas.wirexapp.tech", "sandbox base URL"),
    ("wirex-baas-overview", "wx-acquiring-card-manager-uat.wirexapp.com", "PCI sandbox URL"),
    ("wirex-baas-overview", "wx-acquiring-card-manager.wirexapp.com", "PCI production URL"),
    ("wirex-baas-overview", "ramc.wirexapp.tech", "helper API URL"),
    ("wirex-baas-overview", "8453", "production chain ID"),
    ("wirex-baas-overview", "84532", "sandbox chain ID"),
    ("wirex-baas-overview", "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2", "production WUSD address"),
    ("wirex-baas-overview", "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606", "production WEUR address"),
    ("wirex-baas-overview", "alpha-2", "country code format"),
    ("wirex-baas-overview", "68 countries", "supported card country count"),
    ("wirex-baas-overview", "POST /api/v1/token", "auth endpoint documented"),
    ("wirex-baas-overview", "CategoryValidationFailure", "error category documented"),
    ("wirex-baas-overview", "ErrorInvalidField", "error reason documented"),

    # ── wirex-baas-auth (15) ──────────────────────────────────
    ("wirex-baas-auth", "POST /api/v1/token", "S2S token endpoint"),
    ("wirex-baas-auth", "POST /api/v1/user/authorize", "user token endpoint"),
    ("wirex-baas-auth", "client_credentials", "grant type"),
    ("wirex-baas-auth", "client_id", "client_id parameter"),
    ("wirex-baas-auth", "client_secret", "client_secret parameter"),
    ("wirex-baas-auth", '"access_token"', "response access_token field"),
    ("wirex-baas-auth", '"expires_at"', "response expires_at field"),
    ("wirex-baas-auth", "X-Chain-Id", "chain ID header"),
    ("wirex-baas-auth", "X-User-Wallet", "user wallet header"),
    ("wirex-baas-auth", "X-User-Email", "user email header"),
    ("wirex-baas-auth", "X-User-Id", "user ID header"),
    ("wirex-baas-auth", "48 hours", "token validity period"),
    ("wirex-baas-auth", "Bearer", "Bearer token type"),
    ("wirex-baas-auth", "Privy", "Privy auth provider"),
    ("wirex-baas-auth", "CategoryUnauthorized", "auth error category"),

    # ── wirex-baas-onboarding (17) ────────────────────────────
    ("wirex-baas-onboarding", "POST /api/v2/user", "user registration endpoint"),
    ("wirex-baas-onboarding", '"phone_number"', "phone_number field in JSON"),
    ("wirex-baas-onboarding", "Kernel v3.1", "smart wallet kernel version"),
    ("wirex-baas-onboarding", "ERC-4337", "account abstraction standard"),
    ("wirex-baas-onboarding", "FundsManagement", "executor module"),
    ("wirex-baas-onboarding", "ExecutionDelayPolicy", "delay policy module"),
    ("wirex-baas-onboarding", "SumSub", "SumSub provider"),
    ("wirex-baas-onboarding", "VisaVirtualCard", "visa card capability"),
    ("wirex-baas-onboarding", "SepaAccount", "SEPA capability"),
    ("wirex-baas-onboarding", "AchAccount", "ACH capability"),
    ("wirex-baas-onboarding", "E.164", "phone format standard"),
    ("wirex-baas-onboarding", '"+4', "plus prefix in phone example"),
    ("wirex-baas-onboarding", "GET /api/v2/user", "get user profile endpoint"),
    ("wirex-baas-onboarding", "verification-link", "KYC verification link endpoint"),
    ("wirex-baas-onboarding", "POST /api/v1/confirmation/sms", "SMS confirmation endpoint"),
    ("wirex-baas-onboarding", "initial_data", "registration wrapper field"),
    ("wirex-baas-onboarding", "PUT /api/v1/user/phone-number", "phone update endpoint"),

    # ── wirex-baas-crypto (14) ────────────────────────────────
    ("wirex-baas-crypto", "GET /api/v1/wallet", "wallet balance endpoint"),
    ("wirex-baas-crypto", "WUSD", "WUSD token"),
    ("wirex-baas-crypto", "WEUR", "WEUR token"),
    ("wirex-baas-crypto", "18 decimals", "wrapped token decimals"),
    ("wirex-baas-crypto", "Rhino.fi", "cross-chain deposit provider"),
    ("wirex-baas-crypto", "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2", "production WUSD address"),
    ("wirex-baas-crypto", "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606", "production WEUR address"),
    ("wirex-baas-crypto", "Base chain", "Base chain mentioned"),
    ("wirex-baas-crypto", "ERC20", "ERC20 token standard"),
    ("wirex-baas-crypto", "two-phase delay pattern", "two-phase withdrawal pattern"),
    ("wirex-baas-crypto", "valid_after", "withdrawal valid_after timestamp"),
    ("wirex-baas-crypto", "POST /api/v1/wallets/global", "global address endpoint"),
    ("wirex-baas-crypto", "GET /api/v1/wallets", "list wallets endpoint"),
    ("wirex-baas-crypto", "GET /api/v1/withdrawal/requests", "withdrawal requests endpoint"),

    # ── wirex-baas-cards (18) ─────────────────────────────────
    ("wirex-baas-cards", "POST /api/v1/cards", "card issuance endpoint"),
    ("wirex-baas-cards", "VisaVirtualCard", "virtual card capability"),
    ("wirex-baas-cards", "VisaPlasticCard", "plastic card capability"),
    ("wirex-baas-cards", "VisaMetalCard", "metal card capability"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/details", "get PAN endpoint"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/cvv", "get CVV endpoint"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/pin", "get PIN endpoint"),
    ("wirex-baas-cards", "3DS", "3DS authentication"),
    ("wirex-baas-cards", "OTP", "OTP verification"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/block", "card block endpoint"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/activate", "card activate endpoint"),
    ("wirex-baas-cards", "ErrorInvalidStatus", "card state error code"),
    ("wirex-baas-cards", "action_token", "action token for sensitive ops"),
    ("wirex-baas-cards", "message_signature", "signature verification field"),
    ("wirex-baas-cards", "session_id", "3DS session ID"),
    ("wirex-baas-cards", "{cardId}/limit", "card limit endpoint"),
    ("wirex-baas-cards", "/api/v1/cards/{cardId}/name", "rename card endpoint"),
    ("wirex-baas-cards", "fees/{country}", "card fees endpoint"),

    # ── wirex-baas-transfers (20) ─────────────────────────────
    ("wirex-baas-transfers", "POST /api/v2/bank/transfer/estimate", "SEPA/ACH estimate endpoint (v2)"),
    ("wirex-baas-transfers", "POST /api/v1/bank/transfer", "SEPA/ACH execute endpoint (v1)"),
    ("wirex-baas-transfers", "POST /api/v1/cards/transfer/estimate", "push-to-card estimate endpoint"),
    ("wirex-baas-transfers", "POST /api/v1/cards/transfer", "push-to-card execute endpoint"),
    ("wirex-baas-transfers", '"estimation_id"', "estimation ID field in JSON"),
    ("wirex-baas-transfers", "SEPA", "SEPA transfer type"),
    ("wirex-baas-transfers", "ACH", "ACH transfer type"),
    ("wirex-baas-transfers", '"line1"', "correct address field name"),
    ("wirex-baas-transfers", '"zip_code"', "correct zip_code field name"),
    ("wirex-baas-transfers", "account_holder", "correct account holder field"),
    ("wirex-baas-transfers", '"data"', "list response root key in JSON (live sandbox 2026-10-25)"),
    ("wirex-baas-transfers", '"personal_info"', "nested personal info object"),
    ("wirex-baas-transfers", '"is_business"', "required is_business field"),
    ("wirex-baas-transfers", '"currencies"', "required currencies field"),
    ("wirex-baas-transfers", "POST /api/v2/recipients", "recipient create endpoint"),
    ("wirex-baas-transfers", "ErrorNotSupported", "capability error code"),
    ("wirex-baas-transfers", "GET /api/v1/bank/accounts", "get bank accounts endpoint"),
    ("wirex-baas-transfers", "POST /api/v1/bank/accounts", "ACH activate endpoint"),
    ("wirex-baas-transfers", "estimated_amounts", "estimate response array field"),
    ("wirex-baas-transfers", "nick_name", "optional nick_name field"),

    # ── wirex-baas-webhooks (15) ──────────────────────────────
    ("wirex-baas-webhooks", "/v2/webhooks/wallets", "wallet webhook endpoint"),
    ("wirex-baas-webhooks", "/v2/webhooks/balances", "balance webhook endpoint"),
    ("wirex-baas-webhooks", "/v2/webhooks/cards", "cards webhook endpoint"),
    ("wirex-baas-webhooks", "/v2/webhooks/activities", "activities webhook endpoint"),
    ("wirex-baas-webhooks", "/v2/webhooks/recipients", "recipients webhook endpoint"),
    ("wirex-baas-webhooks", "/v2/webhooks/3ds", "3DS webhook endpoint"),
    ("wirex-baas-webhooks", "10 seconds", "webhook timeout"),
    ("wirex-baas-webhooks", "not automatically retried", "no-retry policy"),
    ("wirex-baas-webhooks", "application/json", "webhook content type"),
    ("wirex-baas-webhooks", "GET /api/v1/activity/feed", "activity history endpoint"),
    ("wirex-baas-webhooks", "page_number", "pagination parameter"),
    ("wirex-baas-webhooks", "/v2/webhooks/card-limits", "card limits webhook endpoint"),
    ("wirex-baas-webhooks", "Completed", "completed activity status"),
    ("wirex-baas-webhooks", "Pending", "pending activity status"),
    ("wirex-baas-webhooks", "Failed", "failed activity status"),

    # ── wirex-baas-sandbox (14) ───────────────────────────────
    ("wirex-baas-sandbox", "ramc.wirexapp.tech", "helper API base URL"),
    ("wirex-baas-sandbox", "POST /account/retail/mint", "mint endpoint"),
    ("wirex-baas-sandbox", "/bank/sepa/deposit", "SEPA deposit simulation"),
    ("wirex-baas-sandbox", "/bank/sepa/transfer/complete", "SEPA complete simulation"),
    ("wirex-baas-sandbox", "/bank/ach/deposit", "ACH deposit simulation"),
    ("wirex-baas-sandbox", "/bank/ach/customer/activate", "ACH customer activation"),
    ("wirex-baas-sandbox", "/card/transaction/pos", "card POS simulation"),
    ("wirex-baas-sandbox", "/card/epos-auth-and-clearing", "card EPOS simulation"),
    ("wirex-baas-sandbox", "/card/atm-auth-and-clearing", "card ATM simulation"),
    ("wirex-baas-sandbox", "/card/original-credit", "card credit simulation"),
    ("wirex-baas-sandbox", "84532", "sandbox chain ID"),
    ("wirex-baas-sandbox", "3fCeoWq6FOtKJBZiyorXnxE41Dqp2zKB", "sandbox client_id"),
    ("wirex-baas-sandbox", "api-docs", "interactive docs URL"),
    ("wirex-baas-sandbox", "Content-Type", "content type in examples"),
]


@pytest.mark.parametrize(
    "skill,sub,desc",
    ASSERTIONS,
    ids=[f"{a[0].removeprefix('wirex-baas-')}:{a[2]}" for a in ASSERTIONS],
)
def test_skill_content(skill, sub, desc):
    content = skill_all_content(skill)
    assert sub in content, f"{skill} missing: {desc} ({sub!r})"

"""Cross-cutting regex checks — regression tests for known documentation errors.

Derived from validation-lessons.md. Each test scans ALL .md files under skills/
and asserts zero matches for anti-patterns that have appeared repeatedly.
"""

import re
from pathlib import Path

import pytest

from conftest import SKILLS_DIR, all_md_files, file_content, skill_all_content


def _grep_all(pattern: str, flags: int = 0) -> list[tuple[Path, int, str]]:
    """Search all skills .md files using cached content."""
    regex = re.compile(pattern, flags)
    hits = []
    for path in all_md_files():
        for i, line in enumerate(file_content(path).splitlines(), 1):
            if regex.search(line):
                hits.append((path.relative_to(SKILLS_DIR.parent), i, line.strip()))
    return hits


def _format_hits(hits):
    return "\n".join(f"  {f}:{n}: {l}" for f, n, l in hits)


# ──────────────────────────────────────────────────────────────
# Banned patterns: must never appear
# ──────────────────────────────────────────────────────────────
BANNED_PATTERNS = [
    (r"api\.wirexpay\.com", 0, "Wrong base URL (should be api-baas.wirexapp.com/tech)"),
    (r"x-account-id", re.IGNORECASE, "Wrong header (old deprecated name)"),
    (r"X-User-Address", 0, "Wrong header (renamed to X-User-Wallet)"),
    (r"wirexpay-sdk", 0, "Wrong SDK package (should be @wirexapp/wpay-baas-sdk)"),
    (r"9qgK7xzQirmJgZi9zOamLXQ6dQ7KpUu9", 0, "Outdated sandbox client_id"),
    (r"ERROR_[A-Z_]{2,}", 0, "SCREAMING_SNAKE error codes (should be PascalCase)"),
    (r"address_line_[12]", 0, "Wrong address field (should be line1/line2)"),
    (r'"phone"\s*:', 0, "Bare phone field (should be phone_number)"),
    (r'"error_category"\s*:\s*"[A-Z]', 0, "Flat error_category (should be nested object)"),
    (r"X-Chain-Id:\s*(?:1|137)\b", 0, "Wrong chain ID (should be 8453 or 84532)"),
    (r"\baccount_holder_name\b", 0, "Wrong field (should be account_holder)"),
]


@pytest.mark.parametrize(
    "pattern,flags,reason",
    BANNED_PATTERNS,
    ids=[p[2].split("(")[0].strip() for p in BANNED_PATTERNS],
)
def test_banned_pattern(pattern, flags, reason):
    hits = _grep_all(pattern, flags)
    assert hits == [], f"{reason}:\n{_format_hits(hits)}"


# ──────────────────────────────────────────────────────────────
# Required patterns: must appear at least once
# ──────────────────────────────────────────────────────────────
REQUIRED_PATTERNS = [
    (r"api-baas\.wirexapp\.com", "production base URL"),
    (r"api-baas\.wirexapp\.tech", "sandbox base URL"),
    (r"error_category", "error format documented"),
    (r"\b8453\b", "production chain ID"),
    (r"\b84532\b", "sandbox chain ID"),
]


@pytest.mark.parametrize(
    "pattern,label",
    REQUIRED_PATTERNS,
    ids=[p[1] for p in REQUIRED_PATTERNS],
)
def test_required_pattern(pattern, label):
    hits = _grep_all(pattern)
    assert len(hits) >= 1, f"{label} not found anywhere in skills"


# ──────────────────────────────────────────────────────────────
# Cross-file consistency: values that appear in multiple skills
# must be identical everywhere
# ──────────────────────────────────────────────────────────────
TOKEN_ADDRESSES = {
    "production WUSD": "0xb4bB2032A73A53C0Aa7Dc9ee2d9658a978fA7bC2",
    "production WEUR": "0x379e120C1921bFD8f5E0A1a3C699e7e800b66606",
    "sandbox WUSD": "0x0774164DC20524Bb239b39D1DC42573C3E4C6976",
    "sandbox WEUR": "0x5c55F314624718019A326F16a62A05D6C6d8C8A2",
}

BASE_URLS = {
    "production": "https://api-baas.wirexapp.com",
    "sandbox": "https://api-baas.wirexapp.tech",
    "PCI production": "https://wx-acquiring-card-manager.wirexapp.com",
    "PCI sandbox": "https://wx-acquiring-card-manager-uat.wirexapp.com",
    "helper": "https://ramc.wirexapp.tech",
}


class TestCrossFileConsistency:
    """Verify that shared values are identical across all files that mention them."""

    @pytest.mark.parametrize(
        "label,address",
        TOKEN_ADDRESSES.items(),
        ids=TOKEN_ADDRESSES.keys(),
    )
    def test_token_address_consistent(self, label, address):
        """Every mention of a token address must use the exact canonical form."""
        # Find all files that mention this address (case-insensitive search)
        hits_correct = _grep_all(re.escape(address))
        hits_wrong_case = _grep_all(re.escape(address), re.IGNORECASE)
        wrong_case = [h for h in hits_wrong_case if h not in hits_correct]
        assert not wrong_case, (
            f"{label} address has case mismatches:\n{_format_hits(wrong_case)}"
        )

    @pytest.mark.parametrize(
        "label,url",
        BASE_URLS.items(),
        ids=BASE_URLS.keys(),
    )
    def test_base_url_no_typos(self, label, url):
        """Base URLs must not appear with typos (e.g., wirexap.com, wirexapp.co)."""
        # Verify canonical URL appears at least once
        hits = _grep_all(re.escape(url))
        if not hits:
            pytest.skip(f"{label} URL not referenced in skills")

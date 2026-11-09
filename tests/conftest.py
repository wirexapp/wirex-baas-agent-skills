"""Shared fixtures for wirex-baas-skills test suite."""

from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
TESTS_DIR = Path(__file__).parent
SKILLS_DIR = ROOT_DIR / "skills"

SKILL_NAMES = [
    "wirex-baas-overview",
    "wirex-baas-auth",
    "wirex-baas-onboarding",
    "wirex-baas-crypto",
    "wirex-baas-cards",
    "wirex-baas-transfers",
    "wirex-baas-webhooks",
    "wirex-baas-sandbox",
    "wirex-baas-corporate",
    "wirex-baas-sdk",
    "wirex-baas-pci-sdk",
    "wirex-baas-external-auth",
]


@lru_cache(maxsize=1)
def all_md_files() -> tuple[Path, ...]:
    """Return paths to every .md file under skills/ (cached)."""
    return tuple(sorted(SKILLS_DIR.rglob("*.md")))


@lru_cache(maxsize=1)
def _all_file_contents() -> dict[Path, str]:
    """Read all .md files once and cache. Keyed by path."""
    return {p: p.read_text(encoding="utf-8") for p in all_md_files()}


def file_content(path: Path) -> str:
    """Get cached content of a single .md file."""
    return _all_file_contents()[path]


@lru_cache(maxsize=16)
def skill_all_content(skill_name: str) -> str:
    """Concatenated content of all .md files in a single skill (cached)."""
    skill_path = SKILLS_DIR / skill_name
    contents = _all_file_contents()
    return "\n".join(
        contents[p] for p in sorted(p for p in contents if p.is_relative_to(skill_path))
    )

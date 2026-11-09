"""AI-in-the-loop skill evals — verify Claude can use skills correctly.

Feeds each skill's content to `claude -p` in full isolation (no project context,
no tools, no memory), asks a question, then uses a second LLM call (judge) to
verify the answer contains all expected information.

Run with: make eval
Excluded from: make test (marked with @pytest.mark.ai)
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import skill_all_content

EVALS_DIR = Path(__file__).parent / "evals"

ANSWER_SYSTEM_PROMPT = (
    "You are answering questions about a financial API based ONLY on the "
    "documentation provided in the user message. Be concise and specific. "
    "Include exact endpoint paths, field names, and values when relevant. "
    "Do not make up information that is not in the documentation."
)

JUDGE_SYSTEM_PROMPT = (
    "You are an evaluation judge. You will receive an ANSWER and a list of CRITERIA.\n\n"
    "Your job is to check whether the ANSWER contains the information described in each "
    "criterion. You are NOT verifying factual accuracy — only checking if the answer "
    "addresses each point. If the answer mentions the required information, mark PASS.\n\n"
    "Respond with ONLY valid JSON in this exact format, no other text:\n"
    '{"results": [{"pass": true}, {"pass": false, "reason": "brief explanation"}]}\n\n'
    "The results array must have exactly one entry per criterion, in order."
)

# Max characters of the answer to send to the judge (keeps input short)
_JUDGE_ANSWER_LIMIT = 3000


def _load_evals():
    """Load all eval YAML files and return flat list of (skill, eval) tuples."""
    items = []
    for yaml_path in sorted(EVALS_DIR.glob("*.yaml")):
        skill_name = yaml_path.stem
        data = yaml.safe_load(yaml_path.read_text())
        for ev in data["evals"]:
            short_q = ev["question"][:60] + ("..." if len(ev["question"]) > 60 else "")
            test_id = f"{skill_name.removeprefix('wirex-baas-')}:{short_q}"
            items.append(pytest.param(skill_name, ev, id=test_id))
    return items


def _run_claude(prompt: str, system_prompt: str, max_turns: int = 1) -> str:
    """Run claude -p with full isolation and return the response text."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(
        [
            "claude",
            "-p",
            "--model", "haiku",
            "--system-prompt", system_prompt,
            "--tools", "",
            "--max-turns", str(max_turns),
            "--output-format", "text",
            # Without this the user's own settings (hooks, CLAUDE.md-driven
            # behaviour) leak into the "isolated" run and skew the answers.
            "--setting-sources=",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed (exit {result.returncode}): {result.stderr}")
    return result.stdout


def _parse_judge_json(text: str) -> list[dict]:
    """Extract and parse the JSON results from judge response."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    # Try direct parse first
    try:
        return json.loads(text)["results"]
    except (json.JSONDecodeError, KeyError):
        pass
    # Extract from code fence anywhere in the text
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())["results"]
        except (json.JSONDecodeError, KeyError):
            pass
    # Fallback: find last JSON object with "results" key
    for match in reversed(list(re.finditer(r'\{"results".*\}', text, re.DOTALL))):
        try:
            return json.loads(match.group())["results"]
        except (json.JSONDecodeError, KeyError):
            continue
    raise ValueError(f"Could not parse judge response as JSON:\n{text[:300]}")


def _judge_answer(answer: str, criteria: list[str]) -> list[dict]:
    """Use a second LLM call to evaluate the answer against criteria."""
    # Truncate answer to keep judge prompt short and reliable
    truncated = answer[:_JUDGE_ANSWER_LIMIT]
    if len(answer) > _JUDGE_ANSWER_LIMIT:
        truncated += "\n[... truncated]"

    criteria_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(criteria))
    prompt = (
        f"ANSWER:\n{truncated}\n\n"
        f"CRITERIA ({len(criteria)} items):\n{criteria_text}"
    )

    # Retry once if the judge fails to produce valid JSON
    last_err = None
    for attempt in range(2):
        response = _run_claude(prompt, JUDGE_SYSTEM_PROMPT, max_turns=3)
        try:
            return _parse_judge_json(response)
        except ValueError as e:
            last_err = e
    raise last_err


# Skip entire module if claude CLI is not available
pytestmark = [
    pytest.mark.ai,
    pytest.mark.skipif(
        shutil.which("claude") is None,
        reason="claude CLI not found on PATH",
    ),
]


@pytest.mark.parametrize("skill_name,ev", _load_evals())
def test_ai_eval(skill_name, ev):
    content = skill_all_content(skill_name)
    criteria = ev["criteria"]

    # Step 1: Get answer from isolated Haiku
    prompt = (
        f"Here is the complete documentation for the {skill_name} skill:\n\n"
        f"---\n{content}\n---\n\n"
        f"Question: {ev['question']}"
    )
    answer = _run_claude(prompt, ANSWER_SYSTEM_PROMPT)

    # Step 2: Judge the answer against criteria
    results = _judge_answer(answer, criteria)

    # Collect failures
    failures = []
    for i, (criterion, result) in enumerate(zip(criteria, results)):
        if not result.get("pass"):
            reason = result.get("reason", "no reason given")
            failures.append(f"  [{i+1}] {criterion}\n      → {reason}")

    assert not failures, (
        f"Answer failed {len(failures)}/{len(criteria)} criteria:\n"
        + "\n".join(failures)
        + f"\n\nAnswer was:\n{answer[:500]}"
    )

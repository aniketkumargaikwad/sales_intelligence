"""Shared helpers for Claude Code PreToolUse hooks.

Hooks are a convenience layer that stops mistakes early in a Claude Code session. The real
controls live in the engine and the database (docs/design.md §11), because hooks can be bypassed.
Exit code 2 blocks the tool call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, NoReturn

SECRET_PATTERNS = {
    "Anthropic API key": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "Slack token": re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "JWT / service key": re.compile(
        r"\beyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"
    ),
    "database URL with password": re.compile(r"postgres(ql)?://[^:\s/]+:[^@\s]{6,}@"),
    "hard-coded secret": re.compile(
        r"(?i)\b(api[_-]?key|secret|password|passwd|token)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"
    ),
}

SUPPRESSION_WRITE = re.compile(
    r"(?is)\b(delete\s+from|update|truncate(\s+table)?|drop\s+table)\s+"
    r"(public\.)?\"?suppression\b"
)


def read_event() -> dict[str, Any]:
    try:
        data: dict[str, Any] = json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}
    return data


def block(reason: str) -> NoReturn:
    print(reason, file=sys.stderr)
    sys.exit(2)


def find_secret(text: str) -> str | None:
    for name, pattern in SECRET_PATTERNS.items():
        if pattern.search(text):
            return name
    return None

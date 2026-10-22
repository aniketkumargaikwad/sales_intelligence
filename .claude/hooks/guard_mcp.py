#!/usr/bin/env python3
"""MCP tools: block sending mail, block suppression edits, and log every write-like call."""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import SUPPRESSION_WRITE, block, read_event

SEND_TOOL = re.compile(
    r"(?i)(send|reply|forward)_?(an_?)?(email|mail|message|draft)|draft_?send|send$"
)
READ_ONLY = re.compile(
    r"(?i)__(get|list|search|read|fetch|query|describe|find|lookup|show|count|check)[a-z_]*$"
)
LOG = Path(".claude/logs/mcp-writes.jsonl")


def main() -> None:
    event = read_event()
    tool = str(event.get("tool_name", ""))
    if not tool.startswith("mcp__"):
        return
    tool_input = event.get("tool_input", {})
    blob = json.dumps(tool_input)
    if SEND_TOOL.search(tool.split("__")[-1]):
        block(
            f"Blocked: {tool} sends a message. MCP mail servers are for triage only; replies "
            "are drafted into the approval queue and sent by the engine. See CLAUDE.md."
        )
    if SUPPRESSION_WRITE.search(blob):
        block("Blocked: the suppression list is append-only. Rows are never edited or removed.")
    if not READ_ONLY.search(tool):
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "tool": tool,
                        "session": event.get("session_id"),
                        "input_keys": sorted(tool_input) if isinstance(tool_input, dict) else [],
                    }
                )
                + "\n"
            )


if __name__ == "__main__":
    main()

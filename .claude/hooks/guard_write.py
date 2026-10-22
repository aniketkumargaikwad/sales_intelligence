#!/usr/bin/env python3
"""Block writing secrets into tracked files. `.env` files (git-ignored) are where secrets go."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import SUPPRESSION_WRITE, block, find_secret, read_event

SECRET_FILES = {".env", ".env.local", ".env.test"}


def main() -> None:
    event = read_event()
    tool_input = event.get("tool_input", {})
    path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    texts = [str(tool_input.get(key, "")) for key in ("content", "new_string", "new_source")]
    texts.extend(str(edit.get("new_string", "")) for edit in tool_input.get("edits", []) or [])
    text = "\n".join(texts)
    if Path(path).name in SECRET_FILES:
        return
    secret = find_secret(text)
    if secret:
        block(
            f"Blocked: this write to {path or 'a file'} contains what looks like a {secret}. "
            "Put secrets in .env (git-ignored) or GitHub/Vercel secrets, never in the repo."
        )
    if path.endswith(".sql") and "/db/migrations/" in path and SUPPRESSION_WRITE.search(text):
        block("Blocked: migrations must not update, delete or drop suppression rows.")


if __name__ == "__main__":
    main()

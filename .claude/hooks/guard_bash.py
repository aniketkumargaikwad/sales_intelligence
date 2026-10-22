#!/usr/bin/env python3
"""Block shell commands that would email prospects outside the engine, edit suppression,
or put a secret on the command line."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import SUPPRESSION_WRITE, block, find_secret, read_event

MAIL_SENDERS = re.compile(
    r"(?ix)("
    r"\bsendmail\b|\bmsmtp\b|\bswaks\b|\bmutt\b|\bmailx?\s+-s\b|\bssmtp\b"
    r"|\bsmtplib\b|\bnodemailer\b|\bsend_?message\(|\.sendmail\("
    r"|curl\b[^\n]*\bsmtps?://"
    r"|\b(nc|ncat|telnet|openssl\s+s_client)\b[^\n]*\b(25|465|587|2525)\b"
    r"|api\.(sendgrid|mailgun|postmarkapp|resend|brevo|sparkpost)\."
    r"|graph\.microsoft\.com[^\n]*sendMail"
    r"|gmail\.googleapis\.com[^\n]*send"
    r")"
)
ENGINE_SEND = re.compile(r"\bpython3?\s+-m\s+si\s+send\b")


def main() -> None:
    event = read_event()
    command = str(event.get("tool_input", {}).get("command", ""))
    if not command:
        return
    if MAIL_SENDERS.search(command) and not ENGINE_SEND.search(command):
        block(
            "Blocked: this command looks like it sends email directly. Only the engine sends "
            "mail (`python -m si send`), after approval, compliance and test-mode gates. "
            "See CLAUDE.md > Guardrails."
        )
    if SUPPRESSION_WRITE.search(command):
        block("Blocked: the suppression list is append-only. Rows are never edited or removed.")
    secret = find_secret(command)
    if secret:
        block(f"Blocked: the command contains what looks like a {secret}. Use .env or secrets.")


if __name__ == "__main__":
    main()

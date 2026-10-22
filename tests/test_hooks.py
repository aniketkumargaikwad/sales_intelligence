"""Claude Code PreToolUse hooks (.claude/hooks). Exit code 2 = blocked."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"

# Built by concatenation so this file itself never contains a secret-shaped string.
FAKE_ANTHROPIC_KEY = "sk-" + "ant-" + "api03-" + "x" * 40
FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


def run(hook: str, event: dict, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:  # type: ignore[type-arg]
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


def bash(command: str) -> subprocess.CompletedProcess[str]:
    return run("guard_bash.py", {"tool_name": "Bash", "tool_input": {"command": command}})


@pytest.mark.parametrize(
    "command",
    [
        "echo hi | sendmail lead@clinic.test",
        "python -c 'import smtplib; smtplib.SMTP(\"smtp.zoho.in\").sendmail(...)'",
        "curl --url smtps://smtp.gmail.com:465 --mail-rcpt x@y.test",
        "swaks --to lead@clinic.test",
        "curl -X POST https://api.sendgrid.com/v3/mail/send",
        "psql $DB -c \"delete from suppression where value = 'x'\"",
        "psql -c 'UPDATE public.suppression SET value = 1'",
        "psql -c 'truncate table suppression'",
        f"export SI_ANTHROPIC_API_KEY={FAKE_ANTHROPIC_KEY}",
    ],
)
def test_bash_blocks(command: str) -> None:
    result = bash(command)
    assert result.returncode == 2, result.stderr
    assert "Blocked" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "uv run python -m si check",
        "uv run python -m si send --offer voicesync",
        "uv run pytest -q",
        "psql -c 'insert into suppression (value) values (1)'",
        "grep -rn smtp_host si/",
    ],
)
def test_bash_allows(command: str) -> None:
    assert bash(command).returncode == 0


def write(path: str, content: str) -> subprocess.CompletedProcess[str]:
    return run(
        "guard_write.py",
        {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}},
    )


def test_write_blocks_secret_in_tracked_file() -> None:
    result = write("/repo/si/config/keys.py", f'KEY = "{FAKE_ANTHROPIC_KEY}"')
    assert result.returncode == 2 and "Anthropic API key" in result.stderr
    assert write("/repo/docs/x.md", f"aws {FAKE_AWS_KEY}").returncode == 2


def test_write_allows_env_and_placeholders() -> None:
    assert write("/repo/.env", f"SI_ANTHROPIC_API_KEY={FAKE_ANTHROPIC_KEY}").returncode == 0
    assert write("/repo/.env.example", "SI_ANTHROPIC_API_KEY=\nSI_SMTP_PASSWORD=").returncode == 0


def test_edit_new_string_is_checked() -> None:
    event = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "/r/a.py",
            "old_string": "x",
            "new_string": f"token = '{FAKE_ANTHROPIC_KEY}'",
        },
    }
    assert run("guard_write.py", event).returncode == 2


def test_migration_cannot_delete_suppression() -> None:
    result = write("/repo/db/migrations/0009_x.sql", "delete from suppression;")
    assert result.returncode == 2


def test_mcp_send_blocked_and_writes_logged(tmp_path: Path) -> None:
    sent = run("guard_mcp.py", {"tool_name": "mcp__gmail__send_email", "tool_input": {}}, tmp_path)
    assert sent.returncode == 2
    sql = run(
        "guard_mcp.py",
        {
            "tool_name": "mcp__supabase__execute_sql",
            "tool_input": {"query": "delete from suppression"},
        },
        tmp_path,
    )
    assert sql.returncode == 2
    ok = run(
        "guard_mcp.py",
        {"tool_name": "mcp__hubspot__create_contact", "tool_input": {"email": "a"}},
        tmp_path,
    )
    read = run(
        "guard_mcp.py", {"tool_name": "mcp__hubspot__get_contact", "tool_input": {}}, tmp_path
    )
    assert ok.returncode == 0 and read.returncode == 0
    lines = (tmp_path / ".claude/logs/mcp-writes.jsonl").read_text().splitlines()
    assert [json.loads(line)["tool"] for line in lines] == ["mcp__hubspot__create_contact"]


def test_non_mcp_tools_ignored(tmp_path: Path) -> None:
    assert run("guard_mcp.py", {"tool_name": "Read", "tool_input": {}}, tmp_path).returncode == 0

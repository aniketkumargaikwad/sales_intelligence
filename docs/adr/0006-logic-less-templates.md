# ADR-0006: Logic-less templates shared by engine and dashboard

Status: Accepted (design PR #1 merged 2026-10-22). Date: 2026-10-22.

## Context

Email 1 and follow-ups are fixed templates with a few LLM-filled slots (brief §1.4). The engine
(Python) renders them for sending; the dashboard (TypeScript) must show a **live preview** while the
operator edits a slot. Two different template engines would drift, and the preview would lie.

## Decision

Use **Mustache** (logic-less) for every email frame and step template in `templates/email/`.

- Python renders with a spec-compliant Mustache library; the dashboard renders with `mustache.js`.
- A shared fixture suite (`templates/email/fixtures/*.json` → expected HTML/text) runs in both
  test suites so the two renderers can't drift.
- Templates hold no logic, no prices and no customer names; those come from slots that the honesty
  gate checks. The frame owns the footer (identity, postal address, unsubscribe).
- The sender always re-renders and re-lints at send time; what was previewed is what is sent.

## Alternatives

- **Jinja2 + Nunjucks**: similar syntax but not identical semantics; logic in templates invites drift.
- **Render only in Python, preview via an API call**: needs an always-on Python service.
- **MJML**: nice for responsive email, but adds a build step; our frame is a hand-written,
  single-column table layout that doesn't need it.

## Consequences

- Templates are simple enough for the operator to edit.
- Any conditional layout (e.g. "show the phone line if present") becomes separate template variants.

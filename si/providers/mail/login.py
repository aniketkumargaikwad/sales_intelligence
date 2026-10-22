"""Mailbox login checks. Sending itself arrives in phase 6 and lives only in `si send`."""

from __future__ import annotations

import asyncio
import imaplib
import smtplib
import ssl

from si.checks.base import CheckResult
from si.config.settings import Settings


def _smtp_login(settings: Settings) -> None:
    assert settings.smtp_host and settings.smtp_user and settings.smtp_password
    context = ssl.create_default_context()
    password = settings.smtp_password.get_secret_value()
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, 465, context=context, timeout=20) as smtp:
            smtp.login(settings.smtp_user, password)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls(context=context)
            smtp.login(settings.smtp_user, password)


def _imap_login(settings: Settings) -> None:
    assert settings.imap_host and settings.imap_password
    user = settings.imap_user or settings.smtp_user
    assert user
    context = ssl.create_default_context()
    with imaplib.IMAP4_SSL(
        settings.imap_host, settings.imap_port, ssl_context=context, timeout=20
    ) as imap:
        imap.login(user, settings.imap_password.get_secret_value())
        imap.logout()


async def check_smtp(settings: Settings) -> CheckResult:
    component = "mailbox: smtp login"
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        return CheckResult.not_configured(
            component, "set SI_SMTP_HOST, SI_SMTP_USER, SI_SMTP_PASSWORD"
        )
    try:
        await asyncio.to_thread(_smtp_login, settings)
    except smtplib.SMTPAuthenticationError:
        return CheckResult.failing(
            component, f"{settings.smtp_user}: username or password rejected"
        )
    except (OSError, smtplib.SMTPException) as exc:
        return CheckResult.failing(component, f"{settings.smtp_host}: {exc}")
    return CheckResult.ok(component, f"{settings.smtp_user} at {settings.smtp_host}")


async def check_imap(settings: Settings) -> CheckResult:
    component = "mailbox: imap login"
    if not (
        settings.imap_host and settings.imap_password and (settings.imap_user or settings.smtp_user)
    ):
        return CheckResult.not_configured(
            component, "set SI_IMAP_HOST, SI_IMAP_USER, SI_IMAP_PASSWORD"
        )
    try:
        await asyncio.to_thread(_imap_login, settings)
    except imaplib.IMAP4.error as exc:
        return CheckResult.failing(component, f"login rejected: {exc}")
    except OSError as exc:
        return CheckResult.failing(component, f"{settings.imap_host}: {exc}")
    return CheckResult.ok(
        component, f"{settings.imap_user or settings.smtp_user} at {settings.imap_host}"
    )

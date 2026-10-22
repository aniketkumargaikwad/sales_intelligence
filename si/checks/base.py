from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["ok", "not_configured", "failing", "info"]


@dataclass(frozen=True)
class CheckResult:
    component: str
    status: Status
    detail: str

    @classmethod
    def ok(cls, component: str, detail: str = "") -> CheckResult:
        return cls(component, "ok", detail)

    @classmethod
    def not_configured(cls, component: str, detail: str = "") -> CheckResult:
        return cls(component, "not_configured", detail)

    @classmethod
    def failing(cls, component: str, detail: str) -> CheckResult:
        return cls(component, "failing", detail)

    @classmethod
    def info(cls, component: str, detail: str) -> CheckResult:
        return cls(component, "info", detail)

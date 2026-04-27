from __future__ import annotations

from typing import Protocol

from kitsune.domain.models import LaunchPlan, LaunchRequest, LaunchResult


class LauncherRuntime(Protocol):
    def build_plan(self, request: LaunchRequest) -> LaunchPlan:
        ...

    def start(self, plan: LaunchPlan) -> LaunchResult:
        ...

    def is_running(self, pid: int | None) -> bool:
        ...

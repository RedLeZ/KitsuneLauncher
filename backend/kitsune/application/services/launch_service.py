from __future__ import annotations

from kitsune.application.contracts.launcher_runtime import LauncherRuntime
from kitsune.domain.models import LaunchPlan, LaunchRequest, LaunchResult


class LaunchService:
    def __init__(self, runtime: LauncherRuntime) -> None:
        self.runtime = runtime

    def build_plan(self, request: LaunchRequest) -> LaunchPlan:
        username = request.username.strip()
        if not username:
            raise ValueError("username is required")
        if len(username) < 3 or len(username) > 16:
            raise ValueError("username length must be between 3 and 16")
        if not request.version.strip():
            raise ValueError("version is required")
        return self.runtime.build_plan(request)

    def start(self, plan: LaunchPlan) -> LaunchResult:
        return self.runtime.start(plan)

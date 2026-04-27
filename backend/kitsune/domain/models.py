from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LaunchRequest:
    username: str
    version: str
    minecraft_path: str
    java_path: str | None
    ram_gb: int = 4
    is_version_installed: bool = False
    extra_jvm_args: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LaunchPlan:
    version: str
    install_required: bool
    command_preview: list[str]
    launcher_options: dict[str, Any]
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LaunchResult:
    started: bool
    pid: int | None
    message: str

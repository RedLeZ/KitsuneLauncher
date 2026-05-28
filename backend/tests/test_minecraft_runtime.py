from __future__ import annotations

from types import SimpleNamespace

import kitsune.infrastructure.minecraft_runtime as minecraft_runtime
from kitsune.domain.models import LaunchPlan


class _FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid


def test_start_uses_generated_command_without_mutation(monkeypatch) -> None:
    runtime = minecraft_runtime.MinecraftLauncherRuntime()
    captured: dict[str, list[str] | str] = {}

    base_command = [
        "java",
        "-XstartOnFirstThread",
        "-jar",
        "minecraft.jar",
        "--username",
        "Player123",
        "--accessToken",
        "token",
        "--userType",
        "msa",
    ]

    def fake_get_minecraft_command(version: str, minecraft_path: str, options: dict) -> list[str]:
        captured["version"] = version
        captured["minecraft_path"] = minecraft_path
        captured["options"] = options
        return base_command.copy()

    def fake_popen(command: list[str], **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs["cwd"]
        return _FakeProcess(pid=4321)

    monkeypatch.setattr(minecraft_runtime.command, "get_minecraft_command", fake_get_minecraft_command)
    monkeypatch.setattr(minecraft_runtime.subprocess, "Popen", fake_popen)

    plan = LaunchPlan(
        version="1.21.5",
        install_required=False,
        command_preview=[],
        launcher_options={
            "username": "Player123",
            "uuid": "offline-uuid",
            "token": "",
            "gameDirectory": "/tmp/.minecraft",
        },
    )

    result = runtime.start(plan)

    assert result.started is True
    assert result.pid == 4321
    assert captured["command"] == base_command
    assert captured["cwd"] == "/tmp/.minecraft"
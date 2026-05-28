from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path

from kitsune.domain.models import LaunchPlan, LaunchRequest, LaunchResult

try:
    import minecraft_launcher_lib
    from minecraft_launcher_lib import command, install, utils
except Exception:
    minecraft_launcher_lib = None


def get_offline_uuid(username: str) -> str:
    """Generate offline UUID for demo/offline player."""
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, "OfflinePlayer:" + username))


def _build_launcher_options(request: LaunchRequest) -> dict[str, object]:
    options: dict[str, object] = {
        "username": request.username,
        "uuid": get_offline_uuid(request.username),
        "token": "",
        "demo": False,
        "launcherName": "Kitsune",
        "launcherVersion": "0.1",
        "gameDirectory": str(request.minecraft_path),
        "nativesDirectory": str(Path(request.minecraft_path) / "versions" / request.version / "natives"),
        "defaultExecutablePath": request.java_path or "java",
        "jvmArguments": [
            f"-Xmx{request.ram_gb}G",
            f"-Xms{request.ram_gb}G",
            *request.extra_jvm_args,
        ],
    }

    if request.java_path:
        options["executablePath"] = request.java_path

    return options


def _preview_command(version: str, minecraft_path: str, launcher_options: dict[str, object]) -> list[str]:
    if minecraft_launcher_lib is None:
        return ["<launcher lib unavailable>"]

    try:
        preview_cmd = command.get_minecraft_command(version, minecraft_path, launcher_options)
    except Exception:
        return ["<unable to preview>"]

    if len(preview_cmd) <= 5:
        return preview_cmd

    return preview_cmd[:5] + ["..."]


class MinecraftLauncherRuntime:
    def __init__(self) -> None:
        self._processes: dict[int, subprocess.Popen[str]] = {}

    def build_plan(self, request: LaunchRequest) -> LaunchPlan:
        """Build a launch plan with command preview and launcher options."""
        launcher_options = _build_launcher_options(request)
        command_preview = _preview_command(request.version, request.minecraft_path, launcher_options)

        notes = [
            "Preview command shown for diagnostics.",
            "Minecraft will be installed automatically before launch when needed.",
        ]

        return LaunchPlan(
            version=request.version,
            install_required=not request.is_version_installed,
            command_preview=command_preview,
            launcher_options=launcher_options,
            notes=notes,
        )

    def start(self, plan: LaunchPlan) -> LaunchResult:
        """Execute the Minecraft launch command."""
        if minecraft_launcher_lib is None:
            return LaunchResult(
                started=False,
                pid=None,
                message="minecraft-launcher-lib is unavailable in the current environment.",
            )

        try:
            version = plan.version
            minecraft_path = plan.launcher_options.get("gameDirectory")

            if not minecraft_path:
                return LaunchResult(
                    started=False,
                    pid=None,
                    message="Game directory not specified in launch options.",
                )

            if plan.install_required:
                install.install_minecraft_version(version, minecraft_path)

            minecraft_command = command.get_minecraft_command(version, minecraft_path, plan.launcher_options)

            creation_flags = 0
            if os.name == "nt":
                creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.HIGH_PRIORITY_CLASS

            proc = subprocess.Popen(
                minecraft_command,
                cwd=minecraft_path,
                creationflags=creation_flags,
            )

            self._processes[proc.pid] = proc

            return LaunchResult(
                started=True,
                pid=proc.pid,
                message=f"Minecraft process started with PID {proc.pid}.",
            )

        except FileNotFoundError as exc:
            return LaunchResult(
                started=False,
                pid=None,
                message=f"Java executable or Minecraft file not found: {exc}",
            )
        except Exception as exc:
            return LaunchResult(
                started=False,
                pid=None,
                message=f"Failed to start Minecraft: {exc}",
            )

    def is_running(self, pid: int | None) -> bool:
        if pid is None:
            return False

        process = self._processes.get(pid)
        if process is not None:
            running = process.poll() is None
            if not running:
                self._processes.pop(pid, None)
            return running

        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def get_available_versions(self) -> list[dict]:
        """Fetch list of available Minecraft versions from the manifest."""
        if minecraft_launcher_lib is None:
            return []

        try:
            manifest = utils.get_version_list()
            return [
                {
                    "id": v["id"],
                    "type": v["type"],
                    "releaseTime": v.get("releaseTime"),
                    "installed": False,
                }
                for v in manifest
            ]
        except Exception:
            return []

    def get_installed_versions(self, minecraft_path: str) -> list[dict]:
        """Get list of installed Minecraft versions."""
        if minecraft_launcher_lib is None:
            return []

        try:
            installed = utils.get_installed_versions(minecraft_path)
            return [
                {
                    "id": v["id"],
                    "type": v["type"],
                    "installed": True,
                }
                for v in installed
            ]
        except Exception:
            return []

    def download_version(self, version: str, minecraft_path: str) -> dict:
        """Download and install a Minecraft version."""
        if minecraft_launcher_lib is None:
            return {"success": False, "message": "minecraft-launcher-lib not available"}

        try:
            install.install_minecraft_version(version, minecraft_path)
            return {"success": True, "message": f"Version {version} downloaded successfully"}
        except Exception as exc:
            return {"success": False, "message": f"Failed to download version: {exc}"}


def default_minecraft_path() -> str:
    return utils.get_minecraft_directory()

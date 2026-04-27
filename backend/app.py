from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from kitsune.application.services.launch_service import LaunchService
from kitsune.domain.models import LaunchPlan, LaunchRequest
from kitsune.infrastructure.minecraft_runtime import MinecraftLauncherRuntime, default_minecraft_path

app = FastAPI(title="Kitsune Launcher Backend", version="0.1.0")

# CORS configuration for dev and Tauri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = LaunchService(runtime=MinecraftLauncherRuntime())


class LaunchPlanPayload(BaseModel):
    username: str = Field(min_length=3, max_length=16)
    version: str
    minecraft_path: str | None = None
    java_path: str | None = None
    ram_gb: int = Field(default=4, ge=2, le=32)
    is_version_installed: bool = False
    extra_jvm_args: list[str] = Field(default_factory=list)


class StartPayload(BaseModel):
    version: str
    install_required: bool
    command_preview: list[str]
    launcher_options: dict


class StatusPayload(BaseModel):
    pid: int | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/launch/plan")
def build_launch_plan(payload: LaunchPlanPayload) -> dict:
    request = LaunchRequest(
        username=payload.username,
        version=payload.version,
        minecraft_path=payload.minecraft_path or default_minecraft_path(),
        java_path=payload.java_path,
        ram_gb=payload.ram_gb,
        is_version_installed=payload.is_version_installed,
        extra_jvm_args=payload.extra_jvm_args,
    )
    try:
        plan = service.build_plan(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "version": plan.version,
        "install_required": plan.install_required,
        "command_preview": plan.command_preview,
        "launcher_options": plan.launcher_options,
        "notes": plan.notes,
    }


@app.post("/launch/start")
def start_launch(payload: StartPayload) -> dict:
    plan = LaunchPlan(
        version=payload.version,
        install_required=payload.install_required,
        command_preview=payload.command_preview,
        launcher_options=payload.launcher_options,
    )

    try:
        result = service.start(plan=plan)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "started": result.started,
        "pid": result.pid,
        "message": result.message,
    }


@app.post("/launch/status")
def launch_status(payload: StatusPayload) -> dict:
    running = service.runtime.is_running(payload.pid)
    return {
        "pid": payload.pid,
        "running": running,
        "message": "Minecraft is running" if running else "Minecraft is not running",
    }


@app.get("/versions")
def list_available_versions() -> dict:
    """List available Minecraft versions from the manifest."""
    runtime = service.runtime
    versions = runtime.get_available_versions()
    return {"versions": versions, "count": len(versions)}


@app.get("/versions/installed")
def list_installed_versions(minecraft_path: str | None = None) -> dict:
    """List installed Minecraft versions."""
    runtime = service.runtime
    path = minecraft_path or default_minecraft_path()
    versions = runtime.get_installed_versions(path)
    return {"versions": versions, "count": len(versions)}


class DownloadVersionPayload(BaseModel):
    version: str
    minecraft_path: str | None = None


@app.post("/versions/download")
def download_version(payload: DownloadVersionPayload) -> dict:
    """Download and install a specific Minecraft version."""
    runtime = service.runtime
    path = payload.minecraft_path or default_minecraft_path()
    result = runtime.download_version(payload.version, path)
    return result

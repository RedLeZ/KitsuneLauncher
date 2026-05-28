#!/usr/bin/env python3
"""
build_release.py

Cross-platform build helper for KitsuneLauncher.

Usage: python tools/build_release.py [--skip-ui] [--skip-backend] [--skip-tauri]

This script will:
- build the Vite UI
- build the Python backend into a single binary using PyInstaller
- copy the backend binary into src-tauri/sidecars
- run `cargo tauri build` to produce desktop bundles

Notes:
- Requires Node.js, npm, Python (3.8+), PyInstaller, Rust/Cargo and Tauri build deps
- Run from repository root: `python tools/build_release.py`
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
BACKEND_DIR = ROOT / "backend"
TAURI_DIR = ROOT / "src-tauri"
SIDECAR_DIR = TAURI_DIR / "sidecars"


def run(cmd, cwd=None, env=None):
    print(f"> {cmd} (cwd={cwd or os.getcwd()})")
    subprocess.run(cmd, shell=True, check=True, cwd=cwd, env=env)


def build_ui():
    print("\n==> Building UI (Vite)")
    if not UI_DIR.exists():
        raise SystemExit("ui directory not found")
    run("npm ci", cwd=str(UI_DIR))
    run("npm run build", cwd=str(UI_DIR))


def build_backend():
    print("\n==> Packaging backend (PyInstaller)")
    if not BACKEND_DIR.exists():
        raise SystemExit("backend directory not found")

    venv_dir = BACKEND_DIR / ".venv"
    python_bin = sys.executable
    # create venv if needed
    if not venv_dir.exists():
        print("Creating virtualenv for backend...")
        run(f"{shlex.quote(str(python_bin))} -m venv {shlex.quote(str(venv_dir))}")

    # Activate environment commands differ by platform; call pip via the venv python
    venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not venv_python.exists():
        raise SystemExit("Failed to find python in backend venv")

    # Install requirements + pyinstaller
    run(f"{shlex.quote(str(venv_python))} -m pip install -r requirements.txt pyinstaller", cwd=str(BACKEND_DIR))

    # Build with PyInstaller
    if os.name == "nt":
        output_name = "kitsune-backend.exe"
        run(f"{shlex.quote(str(venv_python))} -m PyInstaller --noconfirm --onefile --name kitsune-backend app.py", cwd=str(BACKEND_DIR))
        built_bin = BACKEND_DIR / "dist" / "kitsune-backend.exe"
    else:
        output_name = "kitsune-backend"
        run(f"{shlex.quote(str(venv_python))} -m PyInstaller --noconfirm --onefile --name kitsune-backend app.py", cwd=str(BACKEND_DIR))
        built_bin = BACKEND_DIR / "dist" / "kitsune-backend"

    if not built_bin.exists():
        raise SystemExit(f"Backend binary not found at {built_bin}")

    # Ensure sidecar directory exists
    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)

    sidecar_target = SIDECAR_DIR / output_name
    shutil.copy2(built_bin, sidecar_target)

    # Make executable on Unix
    if os.name != "nt":
        sidecar_target.chmod(sidecar_target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Also create platform-suffixed copies that Tauri's build script may look for
    # e.g. kitsune-backend-x86_64-apple-darwin
    try:
        if sys.platform == "darwin":
            # create common macOS triples
            archs = ["x86_64", "aarch64"]
            for arch in archs:
                suffixed = SIDECAR_DIR / f"{output_name}-{arch}-apple-darwin"
                shutil.copy2(sidecar_target, suffixed)
                suffixed.chmod(suffixed.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        elif sys.platform.startswith("linux"):
            arch = platform.machine()
            # common linux triple variants
            candidates = [f"{output_name}-{arch}-unknown-linux-gnu", f"{output_name}-{arch}-linux-gnu"]
            for name in candidates:
                path = SIDECAR_DIR / name
                shutil.copy2(sidecar_target, path)
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        # Non-fatal; best-effort
        pass
    print(f"Copied backend sidecar to {sidecar_target}")
    return sidecar_target


def build_tauri():
    print("\n==> Building Tauri bundle (cargo tauri build)")
    if not TAURI_DIR.exists():
        raise SystemExit("src-tauri directory not found")

    # Ensure UI built
    dist_dir = UI_DIR / "dist"
    if not dist_dir.exists():
        print("UI dist not found, building UI first...")
        build_ui()

    # Check if `cargo tauri` is available, otherwise offer to install or use npx fallback
    cargo_path = shutil.which("cargo")
    tauri_available = False
    if cargo_path:
        try:
            subprocess.run(["cargo", "tauri", "-V"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            tauri_available = True
        except Exception:
            tauri_available = False

    if tauri_available:
        run("cargo tauri build", cwd=str(ROOT))
        return

    print("\n`cargo tauri` not available on PATH.")
    choice = input("Install tauri-cli via `cargo install tauri-cli` now? [Y/n] ").strip().lower()
    if choice in ("", "y", "yes"):
        if not cargo_path:
            raise SystemExit("`cargo` not found. Install Rust toolchain first (rustup). Aborting.")
        print("Installing tauri-cli via cargo...")
        run("cargo install tauri-cli")
        print("tauri-cli installed. Running `cargo tauri build`...")
        run("cargo tauri build", cwd=str(ROOT))
        return

    print("Falling back to `npx tauri build`. This requires Node and @tauri-apps/cli installed locally.")
    # Try npx fallback
    try:
        run("npx tauri build", cwd=str(ROOT))
    except subprocess.CalledProcessError:
        raise SystemExit("Both cargo tauri and npx tauri build failed. Install one and retry.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-ui", action="store_true")
    parser.add_argument("--skip-backend", action="store_true")
    parser.add_argument("--skip-tauri", action="store_true")
    args = parser.parse_args()

    try:
        if not args.skip_ui:
            build_ui()
        if not args.skip_backend:
            build_backend()
        if not args.skip_tauri:
            build_tauri()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(1)

    print("\nAll done. Build artifacts are available in src-tauri/target/release/bundle (mac: .app/.dmg, windows: .msi/.exe depending on config)")


if __name__ == "__main__":
    main()

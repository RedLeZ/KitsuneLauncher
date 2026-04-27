# Kitsune Launcher v2 Bootstrap

## What This Is

This is the clean rewrite of Kitsune Launcher.

- `old/`: legacy code kept only as reference
- `backend/`: Python services, launch flow, and optional Numba acceleration
- `ui/`: web frontend used by the desktop shell
- `src-tauri/`: Tauri desktop wrapper and packaging config

## Current Plan

The rewrite is being built in this order:

1. Get the launch flow working end-to-end first.
2. Package the Python backend so the desktop app can start it automatically.
3. Add version management, Modrinth/mod features, and settings.
4. Add profile/auth screens.
5. Use Numba only for real CPU-heavy code after profiling.

## What Is Already Done

- Launch plan contracts and service scaffold are in place
- Backend can build launch plans and start Minecraft through `minecraft-launcher-lib`
- Frontend can call `/launch/plan` and `/launch/start`
- Backend has version download/list endpoints started
- Optional Numba scaffold exists for future optimization work

## How To Run It For Testing

### Backend

1. `cd backend`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn app:app --host 127.0.0.1 --port 8765 --reload`

### Frontend

1. `cd ui`
2. `npm install`
3. `npm run dev`

## How To Test The Current Flow

1. Open the frontend in the browser.
2. Enter a username, version, and RAM amount.
3. Click `Build Launch Plan`.
4. If the version is not installed, download it first.
5. Click `Start Minecraft`.
6. Confirm the backend returns a PID or an error message.
7. If you want to verify the process is alive, call `/launch/status` with the PID.

## What Works Right Now

- Build a launch plan from the UI
- Generate the real command with `minecraft-launcher-lib`
- Download versions through the backend
- Start the game and get the process PID back
- Check if the PID is still alive through the backend status endpoint

## Next Step

Package the backend into a standalone executable and make Tauri start it automatically. That is the missing step before this becomes a single double-clickable desktop app.

## Next Tasks

1. Package the Python backend as a sidecar or standalone executable
2. Wire Tauri to start the backend on app launch
3. Finish version list fetching and polish the download flow
4. Add Modrinth install/list endpoints and UI
5. Add settings persistence and profile/auth screens
6. Profile the backend and apply Numba only where it helps

## Note from Red

The UI is now just HTML and CSS and some JS,  so you can easily change it as you see fit.
If you need help with anything, let me know. If you want to change anything, you can also call me.

use std::process::{Child, Command, Stdio};
use std::io::{BufRead, BufReader};
use std::sync::{Arc, Mutex};
use std::thread;

use tauri::Manager;

#[derive(Default)]
pub struct BackendState {
    backend_process: Arc<Mutex<Option<Child>>>,
}

#[tauri::command]
fn ping_backend() -> String {
    "pong".to_string()
}

fn find_sidecar_path() -> Option<std::path::PathBuf> {
    // Try a few likely locations relative to the running executable.
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidates = [
                dir.join("sidecars").join("kitsune-backend"),
                dir.join("kitsune-backend"),
                dir.join("../Resources/sidecars").join("kitsune-backend"),
                dir.join("../Resources").join("sidecars").join("kitsune-backend"),
            ];
            for c in candidates.iter() {
                let c = std::path::PathBuf::from(c);
                if c.exists() {
                    return Some(c);
                }
            }
        }
    }
    None
}

fn start_backend(app_handle: &tauri::AppHandle) -> Result<(), String> {
    let sidecar = find_sidecar_path().ok_or_else(|| "Failed to locate kitsune-backend sidecar".to_string())?;

    let mut cmd = Command::new(sidecar);
    cmd.stdout(Stdio::piped()).stderr(Stdio::piped());

    let mut child = cmd.spawn().map_err(|e| format!("Failed to spawn backend: {}", e))?;

    // Clone handles for logging threads
    if let Some(stdout) = child.stdout.take() {
        let mut reader = BufReader::new(stdout);
        thread::spawn(move || {
            let mut line = String::new();
            while let Ok(bytes) = reader.read_line(&mut line) {
                if bytes == 0 { break; }
                print!("[backend stdout] {}", line);
                line.clear();
            }
        });
    }

    if let Some(stderr) = child.stderr.take() {
        let mut reader = BufReader::new(stderr);
        thread::spawn(move || {
            let mut line = String::new();
            while let Ok(bytes) = reader.read_line(&mut line) {
                if bytes == 0 { break; }
                eprint!("[backend stderr] {}", line);
                line.clear();
            }
        });
    }

    let backend_state = app_handle.state::<BackendState>();
    *backend_state.backend_process.lock().expect("backend process lock") = Some(child);

    Ok(())
}

fn stop_backend(app_handle: &tauri::AppHandle) {
    let backend_state = app_handle.state::<BackendState>();
    let child = {
        backend_state
            .backend_process
            .lock()
            .expect("backend process lock")
            .take()
    };

    if let Some(mut child) = child {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .manage(BackendState::default())
        .invoke_handler(tauri::generate_handler![ping_backend])
        .setup(|app| {
            let app_handle = app.handle().clone();
            start_backend(&app_handle)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                stop_backend(window.app_handle());
            }
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::ExitRequested { .. } = event {
            stop_backend(app_handle);
        }
    });
}

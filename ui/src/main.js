const backendBase = "http://127.0.0.1:8765";

const form = document.getElementById("launch-form");
const output = document.getElementById("output");
const versionSelect = document.getElementById("version");
const versionActionsDiv = document.getElementById("version-actions");
const downloadBtn = document.getElementById("download-version-btn");
const startBtn = document.getElementById("launch-start-btn");
const launcherRoot = document.getElementById("launcher-root");
const loadingScreen = document.getElementById("startup-loading");
const loadingStatus = document.getElementById("startup-loading-status");
const retryBtn = document.getElementById("startup-retry");

let currentPlan = null;
let installedVersions = new Set();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForBackendReady(timeoutMs = 30000, intervalMs = 600) {
  const deadline = Date.now() + timeoutMs;
  let attempts = 0;

  while (Date.now() < deadline) {
    attempts += 1;
    loadingStatus.textContent = `Waiting for backend on ${backendBase} (attempt ${attempts})`;
    try {
      const res = await fetch(`${backendBase}/health`, { cache: "no-store" });
      if (res.ok) {
        return;
      }
    } catch {
      // Keep polling until timeout.
    }
    await sleep(intervalMs);
  }

  throw new Error("Backend startup timeout");
}

function showLauncher() {
  loadingScreen.style.display = "none";
  launcherRoot.classList.remove("hidden");
}

function showLoadingError(error) {
  loadingStatus.textContent = "Backend is taking longer than expected.";
  retryBtn.hidden = false;
  output.textContent = JSON.stringify(
    {
      error: "Failed to reach backend during startup",
      detail: String(error),
      hint: `Make sure backend is running on ${backendBase}`,
    },
    null,
    2
  );
}

async function startLauncher() {
  retryBtn.hidden = true;
  loadingStatus.textContent = `Waiting for backend on ${backendBase}`;
  try {
    await waitForBackendReady();
    showLauncher();
    await initializeVersions();
  } catch (error) {
    showLoadingError(error);
  }
}

// Load versions on page load
async function initializeVersions() {
  try {
    output.textContent = "Loading versions...";
    
    // Fetch available and installed versions in parallel
    const [availableRes, installedRes] = await Promise.all([
      fetch(`${backendBase}/versions`),
      fetch(`${backendBase}/versions/installed`),
    ]);

    const availableData = await availableRes.json();
    const installedData = await installedRes.json();

    if (availableData.versions) {
      // Build a set of installed version IDs for quick lookup
      installedVersions = new Set(installedData.versions?.map((v) => v.id) || []);

      // Populate version select, prioritizing releases
      const releases = availableData.versions
        .filter((v) => v.type === "release")
        .slice(0, 50); // Limit to 50 most recent

      versionSelect.innerHTML = releases
        .map((v) => {
          const installed = installedVersions.has(v.id) ? " ✓" : "";
          return `<option value="${v.id}">${v.id}${installed}</option>`;
        })
        .join("");

      // Pre-select latest stable release
      if (releases.length > 0) {
        versionSelect.value = releases[0].id;
      }

      output.textContent = `Loaded ${availableData.count} versions. ${installedVersions.size} installed.`;
    } else {
      output.textContent = "Error: Could not fetch versions";
    }
  } catch (error) {
    output.textContent = JSON.stringify({
      error: "Failed to initialize versions",
      detail: String(error),
      hint: `Make sure backend is running on ${backendBase}`,
    }, null, 2);
  }
}

retryBtn?.addEventListener("click", () => {
  startLauncher();
});

// Start launcher only after backend is responsive.
startLauncher();

// Handle form submission
form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username")?.value ?? "";
  const version = document.getElementById("version")?.value ?? "";
  const ram = Number(document.getElementById("ram")?.value ?? 4);

  output.textContent = "Building launch plan...";
  versionActionsDiv.style.display = "none";

  try {
    const response = await fetch(`${backendBase}/launch/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        version,
        ram_gb: ram,
        is_version_installed: installedVersions.has(version),
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      output.textContent = JSON.stringify({ error: data }, null, 2);
      return;
    }

    // Store plan for start action
    currentPlan = data;
    output.textContent = JSON.stringify(data, null, 2);

    // Show action buttons
    versionActionsDiv.style.display = "grid";

    // Update download button text
    if (installedVersions.has(version)) {
      downloadBtn.textContent = "✓ Already Downloaded";
      downloadBtn.disabled = true;
    } else {
      downloadBtn.textContent = "⬇ Download Version";
      downloadBtn.disabled = false;
    }
  } catch (error) {
    output.textContent = JSON.stringify({
      error: String(error),
      hint: `Make sure backend is running on ${backendBase}`,
    }, null, 2);
  }
});

// Handle download
downloadBtn?.addEventListener("click", async () => {
  const version = document.getElementById("version")?.value ?? "";
  output.textContent = `Downloading version ${version}...`;
  downloadBtn.disabled = true;

  try {
    const response = await fetch(`${backendBase}/versions/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version }),
    });

    const data = await response.json();
    if (!response.ok) {
      output.textContent = JSON.stringify({ error: data }, null, 2);
      downloadBtn.disabled = false;
      return;
    }

    if (data.success) {
      installedVersions.add(version);
      output.textContent = `✓ ${data.message}\n\nNow you can launch!`;
      downloadBtn.textContent = "✓ Downloaded";
      downloadBtn.disabled = true;
    } else {
      output.textContent = JSON.stringify({ error: data.message }, null, 2);
      downloadBtn.disabled = false;
    }
  } catch (error) {
    output.textContent = JSON.stringify({
      error: String(error),
      hint: "Make sure backend is running",
    }, null, 2);
    downloadBtn.disabled = false;
  }
});

// Handle start
startBtn?.addEventListener("click", async () => {
  if (!currentPlan) {
    output.textContent = "No launch plan available. Please run the form first.";
    return;
  }

  output.textContent = "Starting Minecraft...";
  startBtn.disabled = true;

  try {
    const response = await fetch(`${backendBase}/launch/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version: currentPlan.version,
        install_required: currentPlan.install_required,
        command_preview: currentPlan.command_preview,
        launcher_options: currentPlan.launcher_options,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      output.textContent = JSON.stringify({ error: data }, null, 2);
      startBtn.disabled = false;
      return;
    }

    if (data.started) {
      output.textContent = JSON.stringify(
        { status: "✓ Launched", ...data, note: "Minecraft process is running" },
        null,
        2
      );
    } else {
      output.textContent = JSON.stringify(
        { status: "Launch Failed", ...data },
        null,
        2
      );
    }

    startBtn.disabled = false;
  } catch (error) {
    output.textContent = JSON.stringify({
      error: String(error),
      hint: `Make sure backend is running on ${backendBase}`,
    }, null, 2);
    startBtn.disabled = false;
  }
});

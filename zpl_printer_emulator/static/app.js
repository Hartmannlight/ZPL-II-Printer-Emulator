const image = document.querySelector("#label-image");
const emptyState = document.querySelector("#empty-state");
const labelStrip = document.querySelector("#label-strip");
const labelWrap = document.querySelector("#label-wrap");
const jobsList = document.querySelector("#jobs-list");
const jobCount = document.querySelector("#job-count");
const statusText = document.querySelector("#status");
const printer = document.querySelector("#printer");
const soundToggle = document.querySelector("#sound-toggle");
const soundState = document.querySelector("#sound-state");
const soundAction = document.querySelector("#sound-action");
const testPrintButton = document.querySelector("#test-print");
const modeButtons = [...document.querySelectorAll(".mode-button")];

let latestRenderedId = null;
let soundEnabled = true;
let viewMode = localStorage.getItem("zpl-printer-view-mode") || "latest";
let latestImageSrc = "";
let stripSignature = "";
let printAnimationTimer = null;
const fallbackFeedDurationMs = 2200;
const printSound = new Audio("/static/printer-sound.mp4");
printSound.preload = "auto";
printSound.volume = 0.65;

function updateSoundToggle() {
  soundState.textContent = soundEnabled ? "Sound: on" : "Sound: off";
  soundAction.textContent = soundEnabled ? "Click to mute" : "Click to enable";
  soundToggle.setAttribute("aria-pressed", soundEnabled ? "true" : "false");
}

soundToggle.addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  updateSoundToggle();
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setViewMode(button.dataset.mode);
  });
});

testPrintButton.addEventListener("click", async () => {
  testPrintButton.disabled = true;
  statusText.textContent = "Sending test print";
  try {
    const response = await fetch("/api/test-print", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ zpl: buildTestLabel() }),
    });
    if (!response.ok) {
      throw new Error("Test print failed");
    }
    await loadJobs();
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    testPrintButton.disabled = false;
  }
});

async function loadJobs() {
  const response = await fetch("/api/jobs?limit=24", { cache: "no-store" });
  if (!response.ok) {
    statusText.textContent = "Unable to load jobs";
    return;
  }

  const jobs = await response.json();
  renderJobs(jobs);
  await renderLabels(jobs);

  const latestRendered = jobs.find((job) => job.status === "rendered" && job.has_image);
  if (latestRendered && latestRendered.id !== latestRenderedId) {
    latestRenderedId = latestRendered.id;
    statusText.textContent = "Printed label rendered";
    pulsePrinter();
    playPrintSound();
  } else if (jobs.length === 0) {
    statusText.textContent = "Waiting for print jobs";
  } else if (jobs[0].status === "rendering") {
    statusText.textContent = "Rendering latest print job";
  } else if (jobs[0].status === "failed") {
    statusText.textContent = "Latest print job failed";
  }
}

function renderJobs(jobs) {
  jobCount.textContent = `${jobs.length} ${jobs.length === 1 ? "job" : "jobs"}`;
  jobsList.replaceChildren(
    ...jobs.map((job) => {
      const item = document.createElement("article");
      item.className = `job ${job.status}`;
      const created = new Date(job.created_at).toLocaleTimeString();
      const preview = job.has_image
        ? `<img class="job-thumb" alt="" src="/api/jobs/${job.id}/image">`
        : `<div class="job-thumb-placeholder">ZPL</div>`;
      item.innerHTML = `
        ${preview}
        <div>
          <strong>${job.status}</strong>
          <span>${created}</span>
          <span>${job.bytes_received} bytes</span>
          ${job.error ? `<span>${escapeHtml(job.error)}</span>` : ""}
        </div>
      `;
      return item;
    }),
  );
}

async function renderLabels(jobs) {
  const renderedJobs = jobs.filter((job) => job.status === "rendered" && job.has_image);
  const latestRendered = renderedJobs[0];
  const hasLabels = renderedJobs.length > 0;

  image.style.display = viewMode === "latest" && hasLabels ? "block" : "none";
  labelStrip.style.display = viewMode === "strip" && hasLabels ? "flex" : "none";
  emptyState.style.display = hasLabels ? "none" : "grid";

  if (!hasLabels) {
    image.removeAttribute("src");
    labelStrip.replaceChildren();
    latestImageSrc = "";
    stripSignature = "";
    return;
  }

  const nextImageSrc = `/api/jobs/${latestRendered.id}/image?t=${latestRendered.id}`;
  if (nextImageSrc !== latestImageSrc) {
    latestImageSrc = nextImageSrc;
    image.src = nextImageSrc;
    await decodeImage(image);
  }

  const stripJobs = renderedJobs.slice(0, 18);
  const nextStripSignature = stripJobs.map((job) => job.id).join("|");
  let firstStripImage = null;
  if (nextStripSignature !== stripSignature) {
    stripSignature = nextStripSignature;
    labelStrip.replaceChildren(
      ...stripJobs.map((job) => {
        const stripImage = document.createElement("img");
        stripImage.className = "strip-label";
        stripImage.alt = "";
        stripImage.src = `/api/jobs/${job.id}/image?t=${job.id}`;
        if (!firstStripImage) {
          firstStripImage = stripImage;
        }
        return stripImage;
      }),
    );
    if (firstStripImage) {
      await decodeImage(firstStripImage);
    }
  }
}

function setViewMode(mode) {
  viewMode = mode === "strip" ? "strip" : "latest";
  localStorage.setItem("zpl-printer-view-mode", viewMode);
  document.body.dataset.viewMode = viewMode;
  modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === viewMode);
    button.setAttribute("aria-pressed", button.dataset.mode === viewMode ? "true" : "false");
  });
  loadJobs();
}

function pulsePrinter() {
  printer.classList.remove("printing");
  if (printAnimationTimer) {
    window.clearTimeout(printAnimationTimer);
  }

  const feedDuration = getFeedDurationMs();
  printer.style.setProperty("--feed-duration", `${feedDuration}ms`);
  printer.style.setProperty("--feed-start", getFeedStart());
  printer.style.setProperty("--strip-feed-start", getStripFeedStart());
  labelWrap.getBoundingClientRect();
  window.requestAnimationFrame(() => {
    printer.classList.add("printing");
    printAnimationTimer = window.setTimeout(() => {
      printer.classList.remove("printing");
      printAnimationTimer = null;
    }, feedDuration + 80);
  });
}

function playPrintSound() {
  if (!soundEnabled) {
    return;
  }
  printSound.currentTime = 0;
  printSound.play().catch(() => {
    statusText.textContent = "Printed label rendered. Click once to allow sound.";
  });
}

function getFeedDurationMs() {
  if (Number.isFinite(printSound.duration) && printSound.duration > 0) {
    return Math.max(1800, Math.round(printSound.duration * 1000));
  }
  return fallbackFeedDurationMs;
}

function getFeedStart() {
  const activeOutput = viewMode === "strip" ? labelStrip : image;
  const height = activeOutput.getBoundingClientRect().height || 220;
  const distance = Math.min(Math.max(height + 38, 210), viewMode === "strip" ? 420 : 320);
  return `-${Math.round(distance)}px`;
}

function getStripFeedStart() {
  const newestStripLabel = labelStrip.querySelector(".strip-label");
  if (!newestStripLabel) {
    return "-240px";
  }

  const height = newestStripLabel.getBoundingClientRect().height || 220;
  const style = window.getComputedStyle(newestStripLabel);
  const marginTop = Number.parseFloat(style.marginTop) || 0;
  const marginBottom = Number.parseFloat(style.marginBottom) || 0;
  return `-${Math.round(height + marginTop + marginBottom)}px`;
}

async function decodeImage(element) {
  if (!element || element.complete) {
    return;
  }
  if (typeof element.decode === "function") {
    try {
      await element.decode();
      return;
    } catch {
      // Fall back to load/error events below.
    }
  }
  await new Promise((resolve) => {
    element.addEventListener("load", resolve, { once: true });
    element.addEventListener("error", resolve, { once: true });
  });
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

function buildTestLabel() {
  const now = new Date().toLocaleTimeString();
  return `^XA
^PW400
^LL220
^FO24,24^A0N,30,30^FDZPL-II Emulator^FS
^FO24,68^A0N,22,22^FDVirtual print test^FS
^FO24,104^BY2
^BCN,70,Y,N,N
^FD${Date.now()}^FS
^FO24,190^A0N,20,20^FD${now}^FS
^XZ`;
}

updateSoundToggle();
setViewMode(viewMode);
loadJobs();
setInterval(loadJobs, 1200);

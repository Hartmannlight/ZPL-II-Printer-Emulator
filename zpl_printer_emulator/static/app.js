const image = document.querySelector("#label-image");
const emptyState = document.querySelector("#empty-state");
const jobsList = document.querySelector("#jobs-list");
const statusText = document.querySelector("#status");
const printer = document.querySelector("#printer");
const soundToggle = document.querySelector("#sound-toggle");
const soundState = document.querySelector("#sound-state");
const soundAction = document.querySelector("#sound-action");

let latestRenderedId = null;
let soundEnabled = true;
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

async function loadJobs() {
  const response = await fetch("/api/jobs?limit=12", { cache: "no-store" });
  if (!response.ok) {
    statusText.textContent = "Unable to load jobs";
    return;
  }

  const jobs = await response.json();
  renderJobs(jobs);

  const latestRendered = jobs.find((job) => job.status === "rendered" && job.has_image);
  if (latestRendered && latestRendered.id !== latestRenderedId) {
    latestRenderedId = latestRendered.id;
    image.src = `/api/jobs/${latestRendered.id}/image?t=${Date.now()}`;
    image.style.display = "block";
    emptyState.style.display = "none";
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
  jobsList.replaceChildren(
    ...jobs.map((job) => {
      const item = document.createElement("article");
      item.className = `job ${job.status}`;
      const created = new Date(job.created_at).toLocaleTimeString();
      item.innerHTML = `
        <strong>${job.status}</strong>
        <span>${created}</span>
        <span>${job.bytes_received} bytes</span>
        ${job.error ? `<span>${escapeHtml(job.error)}</span>` : ""}
      `;
      return item;
    }),
  );
}

function pulsePrinter() {
  printer.classList.remove("printing");
  window.requestAnimationFrame(() => {
    printer.classList.add("printing");
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

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

updateSoundToggle();
loadJobs();
setInterval(loadJobs, 1200);

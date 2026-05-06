const image = document.querySelector("#label-image");
const emptyState = document.querySelector("#empty-state");
const jobsList = document.querySelector("#jobs-list");
const statusText = document.querySelector("#status");
const printer = document.querySelector("#printer");
const soundToggle = document.querySelector("#sound-toggle");

let latestRenderedId = null;
let soundEnabled = false;
let audioContext = null;

soundToggle.addEventListener("click", () => {
  soundEnabled = !soundEnabled;
  soundToggle.textContent = soundEnabled ? "Sound on" : "Sound off";
  soundToggle.setAttribute("aria-pressed", soundEnabled ? "true" : "false");
  if (soundEnabled && audioContext === null) {
    audioContext = new AudioContext();
  }
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
  if (!soundEnabled || audioContext === null) {
    return;
  }
  const osc = audioContext.createOscillator();
  const gain = audioContext.createGain();
  osc.type = "square";
  osc.frequency.setValueAtTime(175, audioContext.currentTime);
  osc.frequency.linearRampToValueAtTime(125, audioContext.currentTime + 0.12);
  gain.gain.setValueAtTime(0.05, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.14);
  osc.connect(gain);
  gain.connect(audioContext.destination);
  osc.start();
  osc.stop(audioContext.currentTime + 0.15);
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value;
  return span.innerHTML;
}

loadJobs();
setInterval(loadJobs, 1200);

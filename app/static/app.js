const form = document.querySelector("#mosh-form");
const statusEl = document.querySelector("#status");
const generateButton = document.querySelector("#generate");
const resultVideo = document.querySelector("#result");
const downloadLink = document.querySelector("#download");

let resultUrl = null;

bindPreview("clip-a", "preview-a");
bindPreview("clip-b", "preview-b");

document.querySelectorAll("[data-set-time]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.querySelector(`#${button.dataset.setTime}`);
    const video = document.querySelector(`#${button.dataset.video}`);
    input.value = secondsToTimestamp(video.currentTime);
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  clearResult();
  setStatus("processing...");
  generateButton.disabled = true;

  try {
    const clipA = document.querySelector("#clip-a").files[0];
    const clipB = document.querySelector("#clip-b").files[0];

    if (!clipA || !clipB) {
      throw new Error("choose both clips first.");
    }

    const formData = new FormData();
    formData.append("clip_a", clipA);
    formData.append("clip_b", clipB);
    formData.append("a_start", document.querySelector("#a-start").value);
    formData.append("a_end", document.querySelector("#a-end").value);
    formData.append("b_start", document.querySelector("#b-start").value);
    formData.append("b_end", document.querySelector("#b-end").value);
    formData.append("resolution", document.querySelector("#resolution").value);
    formData.append(
      "mosh",
      document.querySelector("#mosh").checked ? "true" : "false",
    );

    const response = await fetch("/mosh", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await readErrorMessage(response));
    }

    const blob = await response.blob();
    resultUrl = URL.createObjectURL(blob);

    resultVideo.src = resultUrl;
    resultVideo.hidden = false;

    downloadLink.href = resultUrl;
    downloadLink.hidden = false;

    setStatus("done.");
  } catch (error) {
    setStatus(error.message || "something went wrong.", true);
  } finally {
    generateButton.disabled = false;
  }
});

function bindPreview(inputId, videoId) {
  const input = document.querySelector(`#${inputId}`);
  const video = document.querySelector(`#${videoId}`);

  input.addEventListener("change", () => {
    const file = input.files[0];

    if (!file) {
      video.removeAttribute("src");
      return;
    }

    video.src = URL.createObjectURL(file);
  });
}

async function readErrorMessage(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = await response.json();

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (data.detail && typeof data.detail.message === "string") {
      return data.detail.message;
    }

    return JSON.stringify(data);
  }

  return await response.text();
}

function secondsToTimestamp(seconds) {
  const safeSeconds = Number.isFinite(seconds) ? seconds : 0;
  const wholeSeconds = Math.floor(safeSeconds);
  const hours = Math.floor(wholeSeconds / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const secs = wholeSeconds % 60;
  const milliseconds = Math.round((safeSeconds - wholeSeconds) * 1000);

  const base = [
    hours.toString().padStart(2, "0"),
    minutes.toString().padStart(2, "0"),
    secs.toString().padStart(2, "0"),
  ].join(":");

  if (milliseconds === 0) {
    return base;
  }

  return `${base}.${milliseconds.toString().padStart(3, "0")}`;
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function clearResult() {
  if (resultUrl) {
    URL.revokeObjectURL(resultUrl);
    resultUrl = null;
  }

  resultVideo.hidden = true;
  resultVideo.removeAttribute("src");

  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
}

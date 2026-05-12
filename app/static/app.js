const form = document.querySelector("#mosh-form");
const statusEl = document.querySelector("#status");
const generateButton = document.querySelector("#generate");
const resultWrap = document.querySelector("#result-wrap");
const resultVideo = document.querySelector("#result");
const downloadLink = document.querySelector("#download");
const clearResultButton = document.querySelector("#clear-result");
const resultNote = document.querySelector("#result-note");

let resultUrl = null;

bindPreview({
  inputId: "clip-a",
  videoId: "preview-a",
  currentId: "current-a",
  durationId: "duration-a",
  startId: "a-start",
  endId: "a-end",
});

bindPreview({
  inputId: "clip-b",
  videoId: "preview-b",
  currentId: "current-b",
  durationId: "duration-b",
  startId: "b-start",
  endId: "b-end",
});

document.querySelectorAll("[data-set-time]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.querySelector(`#${button.dataset.setTime}`);
    const video = document.querySelector(`#${button.dataset.video}`);

    input.value = secondsToTimestamp(video.currentTime);
  });
});

document.querySelectorAll("[data-jump-time]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.querySelector(`#${button.dataset.jumpTime}`);
    const video = document.querySelector(`#${button.dataset.video}`);
    const seconds = timestampToSeconds(input.value);

    if (seconds === null) {
      setStatus(`cannot jump to invalid time: ${input.value}`, true);
      return;
    }

    video.currentTime = seconds;
  });
});

document.querySelectorAll("[data-full-range]").forEach((button) => {
  button.addEventListener("click", () => {
    const clipKey = button.dataset.fullRange;
    const video = document.querySelector(`#${button.dataset.video}`);
    const startInput = document.querySelector(`#${clipKey}-start`);
    const endInput = document.querySelector(`#${clipKey}-end`);

    startInput.value = "00:00:00";

    if (Number.isFinite(video.duration)) {
      endInput.value = secondsToTimestamp(video.duration);
    } else {
      setStatus("load a video before setting the full range.", true);
    }
  });
});

clearResultButton.addEventListener("click", () => {
  clearResult();
  setStatus("");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  clearResult();
  setStatus("processing...");
  resultNote.textContent = "processing local video files...";
  generateButton.disabled = true;

  try {
    const clipA = document.querySelector("#clip-a").files[0];
    const clipB = document.querySelector("#clip-b").files[0];

    if (!clipA || !clipB) {
      throw new Error("choose both clips first.");
    }

    validateRange("a");
    validateRange("b");

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
    resultWrap.hidden = false;

    downloadLink.href = resultUrl;

    setStatus("done.");
    resultNote.textContent = "result ready.";
  } catch (error) {
    setStatus(error.message || "something went wrong.", true);
    resultNote.textContent = "generation failed.";
  } finally {
    generateButton.disabled = false;
  }
});

function bindPreview({
  inputId,
  videoId,
  currentId,
  durationId,
  startId,
  endId,
}) {
  const input = document.querySelector(`#${inputId}`);
  const video = document.querySelector(`#${videoId}`);
  const current = document.querySelector(`#${currentId}`);
  const duration = document.querySelector(`#${durationId}`);
  const start = document.querySelector(`#${startId}`);
  const end = document.querySelector(`#${endId}`);

  input.addEventListener("change", () => {
    const file = input.files[0];

    if (!file) {
      video.removeAttribute("src");
      current.textContent = "00:00:00";
      duration.textContent = "--:--";
      start.value = "00:00:00";
      end.value = "00:00:03";
      return;
    }

    video.src = URL.createObjectURL(file);
    current.textContent = "00:00:00";
    duration.textContent = "loading...";
    start.value = "00:00:00";
  });

  video.addEventListener("loadedmetadata", () => {
    current.textContent = secondsToTimestamp(video.currentTime);

    if (Number.isFinite(video.duration)) {
      duration.textContent = secondsToTimestamp(video.duration);
      end.value = secondsToTimestamp(Math.min(video.duration, 3));
    } else {
      duration.textContent = "--:--";
      end.value = "00:00:03";
    }
  });

  video.addEventListener("timeupdate", () => {
    current.textContent = secondsToTimestamp(video.currentTime);
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

function validateRange(clipKey) {
  const startInput = document.querySelector(`#${clipKey}-start`);
  const endInput = document.querySelector(`#${clipKey}-end`);

  const start = timestampToSeconds(startInput.value);
  const end = timestampToSeconds(endInput.value);

  if (start === null) {
    throw new Error(`clip ${clipKey} start is not a valid time.`);
  }

  if (end === null) {
    throw new Error(`clip ${clipKey} end is not a valid time.`);
  }

  if (end <= start) {
    throw new Error(
      `clip ${clipKey} end must be later than clip ${clipKey} start.`,
    );
  }

  if (end - start < 0.25) {
    throw new Error(`clip ${clipKey} must be at least 0.25 seconds long.`);
  }
}

function timestampToSeconds(value) {
  const match = value
    .trim()
    .match(/^(?:(\d{1,2}):)?(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?$/);

  if (!match) {
    return null;
  }

  const hours = Number(match[1] || 0);
  const minutes = Number(match[2]);
  const seconds = Number(match[3]);
  const milliseconds = Number((match[4] || "0").padEnd(3, "0"));

  if (minutes > 59 || seconds > 59) {
    return null;
  }

  return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
}

function secondsToTimestamp(seconds) {
  const safeSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const totalMilliseconds = Math.round(safeSeconds * 1000);

  const wholeSeconds = Math.floor(totalMilliseconds / 1000);
  const milliseconds = totalMilliseconds % 1000;

  const hours = Math.floor(wholeSeconds / 3600);
  const minutes = Math.floor((wholeSeconds % 3600) / 60);
  const secs = wholeSeconds % 60;

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

  resultWrap.hidden = true;
  resultVideo.removeAttribute("src");

  downloadLink.removeAttribute("href");
  resultNote.textContent = "generate a transition to preview it here.";
}

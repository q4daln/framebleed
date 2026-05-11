from __future__ import annotations

import asyncio
import re
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "output"
STATIC_DIR = ROOT / "app" / "static"

ALLOWED_EXTENSIONS = {
    ".mov",
    ".mp4",
    ".m4v",
    ".avi",
    ".mkv",
    ".webm",
}

ALLOWED_RESOLUTIONS = {
    "original",
    "1080p",
    "720p",
}

TIME_PATTERN = re.compile(
    r"^(?:(?P<hours>\d{1,2}):)?(?P<minutes>\d{1,2}):(?P<seconds>\d{1,2})(?:\.(?P<milliseconds>\d{1,3}))?$"
)

PROCESS_LOCK = asyncio.Lock()

app = FastAPI(title="framebleed")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mosh")
async def create_mosh(
    clip_a: UploadFile = File(...),
    clip_b: UploadFile = File(...),
    a_start: str = Form(...),
    a_end: str = Form(...),
    b_start: str = Form(...),
    b_end: str = Form(...),
    resolution: str = Form("1080p"),
    mosh: bool = Form(True),
) -> FileResponse:
    validate_upload(clip_a, "clip a")
    validate_upload(clip_b, "clip b")
    validate_resolution(resolution)

    a_start_seconds = parse_time(a_start, "clip a start")
    a_end_seconds = parse_time(a_end, "clip a end")
    b_start_seconds = parse_time(b_start, "clip b start")
    b_end_seconds = parse_time(b_end, "clip b end")

    validate_time_range(a_start_seconds, a_end_seconds, "clip a")
    validate_time_range(b_start_seconds, b_end_seconds, "clip b")

    job_id = uuid.uuid4().hex

    job_uploads_dir = UPLOADS_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id

    job_uploads_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)

    clip_a_path = job_uploads_dir / upload_filename(clip_a, "clip_a")
    clip_b_path = job_uploads_dir / upload_filename(clip_b, "clip_b")
    output_path = job_output_dir / "result.mp4"

    await save_upload(clip_a, clip_a_path)
    await save_upload(clip_b, clip_b_path)

    command = [
        "python3",
        str(ROOT / "mosh.py"),
        "--clip-a",
        str(clip_a_path),
        "--clip-b",
        str(clip_b_path),
        "--a-start",
        a_start,
        "--a-end",
        a_end,
        "--b-start",
        b_start,
        "--b-end",
        b_end,
        "--resolution",
        resolution,
        "--output",
        str(output_path),
    ]

    if mosh:
        command.append("--mosh")

    async with PROCESS_LOCK:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "framebleed failed to process the video",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    if not output_path.exists():
        raise HTTPException(
            status_code=500,
            detail="framebleed finished but no output file was created",
        )

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename="framebleed.mp4",
    )


async def save_upload(upload: UploadFile, destination: Path) -> None:
    with destination.open("wb") as file:
        while chunk := await upload.read(1024 * 1024):
            file.write(chunk)


def upload_filename(upload: UploadFile, stem: str) -> str:
    suffix = Path(upload.filename or "").suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        suffix = ".mov"

    return f"{stem}{suffix}"


def validate_upload(upload: UploadFile, label: str) -> None:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()

    if not filename:
        raise HTTPException(status_code=400, detail=f"{label} is missing.")

    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"{label} must be a video file: {allowed}",
        )


def validate_resolution(resolution: str) -> None:
    if resolution not in ALLOWED_RESOLUTIONS:
        allowed = ", ".join(sorted(ALLOWED_RESOLUTIONS))
        raise HTTPException(
            status_code=400,
            detail=f"resolution must be one of: {allowed}",
        )


def parse_time(value: str, label: str) -> float:
    match = TIME_PATTERN.match(value.strip())

    if not match:
        raise HTTPException(
            status_code=400,
            detail=f"{label} must use mm:ss, hh:mm:ss, or hh:mm:ss.mmm format.",
        )

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    milliseconds_raw = match.group("milliseconds") or "0"

    if minutes > 59:
        raise HTTPException(status_code=400, detail=f"{label} has invalid minutes.")

    if seconds > 59:
        raise HTTPException(status_code=400, detail=f"{label} has invalid seconds.")

    milliseconds = int(milliseconds_raw.ljust(3, "0"))

    return (hours * 3600) + (minutes * 60) + seconds + (milliseconds / 1000)


def validate_time_range(start: float, end: float, label: str) -> None:
    if end <= start:
        raise HTTPException(
            status_code=400,
            detail=f"{label} end must be later than {label} start.",
        )

    if end - start < 0.25:
        raise HTTPException(
            status_code=400,
            detail=f"{label} must be at least 0.25 seconds long.",
        )

from __future__ import annotations

import asyncio
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

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

PROCESS_LOCK = asyncio.Lock()

app = FastAPI(title="framebleed")


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

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKING_DIR = ROOT / "working"


def run(command: list[str]) -> None:
    print("\nRunning:")
    print(" ".join(command))

    result = subprocess.run(command)

    if result.returncode != 0:
        raise SystemExit(f"\nCommand failed with exit code {result.returncode}")


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg was not found. Install it with: brew install ffmpeg")

    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe was not found. Install it with: brew install ffmpeg")


def scale_filter(resolution: str) -> str | None:
    if resolution == "original":
        return None

    if resolution == "1080p":
        return "scale=-2:1080"

    if resolution == "720p":
        return "scale=-2:720"

    raise ValueError(f"Unsupported resolution: {resolution}")


def trim_to_intermediate(
    input_path: Path,
    output_path: Path,
    start: str,
    end: str,
    resolution: str,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        start,
        "-to",
        end,
        "-i",
        str(input_path),
        "-an",
    ]

    vf = scale_filter(resolution)
    if vf:
        command.extend(["-vf", vf])

    command.extend(
        [
            "-c:v",
            "mpeg4",
            "-q:v",
            "3",
            "-bf",
            "0",
            "-g",
            "9999",
            str(output_path),
        ]
    )

    run(command)


def concat_intermediates(first: Path, second: Path, output_path: Path) -> None:
    concat_file = WORKING_DIR / "concat.txt"

    concat_file.write_text(
        f"file '{first.resolve()}'\nfile '{second.resolve()}'\n",
        encoding="utf-8",
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]
    )


def export_mp4(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        [
            "ffmpeg",
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Framebleed: trim two clips, join them, and export a video."
    )

    parser.add_argument("--clip-a", required=True, help="Path to the first video clip.")
    parser.add_argument(
        "--clip-b", required=True, help="Path to the second video clip."
    )

    parser.add_argument("--a-start", required=True, help="Start time for clip A.")
    parser.add_argument("--a-end", required=True, help="End time for clip A.")

    parser.add_argument("--b-start", required=True, help="Start time for clip B.")
    parser.add_argument("--b-end", required=True, help="End time for clip B.")

    parser.add_argument(
        "--resolution",
        default="1080p",
        choices=["original", "1080p", "720p"],
        help="Output resolution.",
    )

    parser.add_argument(
        "--output",
        default="output/final.mp4",
        help="Output file path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    require_ffmpeg()

    clip_a = Path(args.clip_a)
    clip_b = Path(args.clip_b)
    output = Path(args.output)

    if not clip_a.exists():
        raise SystemExit(f"Clip A does not exist: {clip_a}")

    if not clip_b.exists():
        raise SystemExit(f"Clip B does not exist: {clip_b}")

    WORKING_DIR.mkdir(exist_ok=True)

    a_intermediate = WORKING_DIR / "a.avi"
    b_intermediate = WORKING_DIR / "b.avi"
    joined = WORKING_DIR / "joined.avi"

    trim_to_intermediate(
        input_path=clip_a,
        output_path=a_intermediate,
        start=args.a_start,
        end=args.a_end,
        resolution=args.resolution,
    )

    trim_to_intermediate(
        input_path=clip_b,
        output_path=b_intermediate,
        start=args.b_start,
        end=args.b_end,
        resolution=args.resolution,
    )

    concat_intermediates(a_intermediate, b_intermediate, joined)
    export_mp4(joined, output)

    print(f"\nDone. Exported: {output}")


if __name__ == "__main__":
    main()

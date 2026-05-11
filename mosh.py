#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import struct
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


def run_capture(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise SystemExit(result.stderr.strip())

    return result.stdout


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


def iframe_indexes(input_path: Path) -> list[int]:
    output = run_capture(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=best_effort_timestamp_time,pict_type,key_frame",
            "-of",
            "csv=p=0",
            str(input_path),
        ]
    )

    indexes: list[int] = []

    for index, line in enumerate(output.splitlines()):
        parts = line.split(",")

        if len(parts) < 3:
            continue

        key_frame = parts[0]
        pict_type = parts[2]

        if key_frame == "1" and pict_type == "I":
            indexes.append(index)

    return indexes


def is_video_chunk(chunk_id: bytes) -> bool:
    return (
        len(chunk_id) == 4 and chunk_id[:2].isdigit() and chunk_id[2:] in {b"dc", b"db"}
    )


def remove_avi_video_chunk(
    input_path: Path, output_path: Path, video_chunk_index: int
) -> None:
    data = input_path.read_bytes()

    if data[:4] != b"RIFF" or data[8:12] != b"AVI ":
        raise SystemExit(f"Not an AVI file: {input_path}")

    output = bytearray()
    output.extend(data[:12])

    position = 12
    removed = False

    while position + 8 <= len(data):
        chunk_id = data[position : position + 4]
        chunk_size = struct.unpack_from("<I", data, position + 4)[0]
        chunk_body_start = position + 8
        chunk_body_end = chunk_body_start + chunk_size
        chunk_end = chunk_body_end + (chunk_size % 2)

        if chunk_body_end > len(data):
            raise SystemExit("AVI chunk parsing failed.")

        if (
            chunk_id == b"LIST"
            and data[chunk_body_start : chunk_body_start + 4] == b"movi"
        ):
            new_body, removed = remove_chunk_from_movi(
                data=data,
                start=chunk_body_start,
                end=chunk_body_end,
                video_chunk_index=video_chunk_index,
            )

            output.extend(b"LIST")
            output.extend(struct.pack("<I", len(new_body)))
            output.extend(new_body)

            if len(new_body) % 2:
                output.extend(b"\x00")

        elif chunk_id == b"idx1":
            pass

        else:
            output.extend(data[position:chunk_end])

        position = chunk_end

    if not removed:
        raise SystemExit(f"Could not remove video chunk index {video_chunk_index}")

    struct.pack_into("<I", output, 4, len(output) - 8)
    output_path.write_bytes(output)

    print(f"\nRemoved video chunk index {video_chunk_index}: {output_path}")


def remove_chunk_from_movi(
    data: bytes,
    start: int,
    end: int,
    video_chunk_index: int,
) -> tuple[bytes, bool]:
    output = bytearray()
    output.extend(b"movi")

    position = start + 4
    current_video_chunk = 0
    removed = False

    while position + 8 <= end:
        chunk_id = data[position : position + 4]
        chunk_size = struct.unpack_from("<I", data, position + 4)[0]
        chunk_body_start = position + 8
        chunk_body_end = chunk_body_start + chunk_size
        chunk_end = chunk_body_end + (chunk_size % 2)

        if chunk_body_end > end:
            break

        if is_video_chunk(chunk_id):
            if current_video_chunk == video_chunk_index:
                removed = True
            else:
                output.extend(data[position:chunk_end])

            current_video_chunk += 1

        else:
            output.extend(data[position:chunk_end])

        position = chunk_end

    return bytes(output), removed


def export_mp4(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    run(
        [
            "ffmpeg",
            "-y",
            "-err_detect",
            "ignore_err",
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

    parser.add_argument(
        "--mosh",
        action="store_true",
        help="Remove the transition I-frame before export.",
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
    moshed = WORKING_DIR / "moshed.avi"

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

    export_source = joined

    if args.mosh:
        indexes = iframe_indexes(joined)

        if len(indexes) < 2:
            raise SystemExit("Could not find a transition I-frame to remove.")

        transition_iframe = indexes[1]
        remove_avi_video_chunk(joined, moshed, transition_iframe)
        export_source = moshed

    export_mp4(export_source, output)

    print(f"\nDone. Exported: {output}")


if __name__ == "__main__":
    main()

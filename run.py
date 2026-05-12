from __future__ import annotations

import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

APP_URL = "http://127.0.0.1:8000"


def main() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg was not found. install it with: brew install ffmpeg")

    if shutil.which("ffprobe") is None:
        raise SystemExit("ffprobe was not found. install it with: brew install ffmpeg")

    if not Path("app/main.py").exists():
        raise SystemExit("run this from the framebleed project root.")

    print("starting framebleed...")
    print(f"open {APP_URL}")
    print("press ctrl+c to stop.\n")

    webbrowser.open(APP_URL)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            check=False,
        )
    except KeyboardInterrupt:
        print("\nframebleed stopped.")


if __name__ == "__main__":
    main()

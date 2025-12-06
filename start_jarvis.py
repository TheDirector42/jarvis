import argparse
import subprocess
import sys
import time
from pathlib import Path


def launch(process_args):
    return subprocess.Popen([sys.executable, *process_args])


def main():
    parser = argparse.ArgumentParser(description="Launch Jarvis HUD and/or voice assistant.")
    parser.add_argument("--no-hud", action="store_true", help="Do not start the desktop HUD.")
    parser.add_argument("--no-voice", action="store_true", help="Do not start the voice assistant (main.py).")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    processes = []

    try:
        if not args.no_hud:
            processes.append(launch([str(here / "jarvis_desktop.py")]))
        if not args.no_voice:
            processes.append(launch([str(here / "main.py")]))

        while processes:
            alive = []
            for p in processes:
                if p.poll() is None:
                    alive.append(p)
            processes = alive
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    main()

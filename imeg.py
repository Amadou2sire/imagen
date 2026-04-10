#!/usr/bin/env python3
"""Small IMEG launcher for backend/frontend dev servers."""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

ASCII_IMEG = r"""
  ___ __  __ _____ ____
 |_ _|  \/  | ____/ ___|
  | || |\/| |  _|| |  _
  | || |  | | |__| |_| |
 |___|_|  |_|_____\____|
"""


class ManagedProcess:
    def __init__(self, name: str, cmd: list[str], cwd: Path) -> None:
        self.name = name
        self.cmd = cmd
        self.cwd = cwd
        self.proc: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            self.cmd,
            cwd=self.cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        def _reader() -> None:
            assert self.proc is not None
            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                print(f"[{self.name}] {line}", end="")

        self._thread = threading.Thread(target=_reader, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        self.proc.send_signal(signal.SIGINT)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()



def _backend_cmd() -> list[str]:
    venv_python = BACKEND_DIR / "venv" / "bin" / "python"
    python_exec = str(venv_python) if venv_python.exists() else sys.executable
    return [
        python_exec,
        "-m",
        "uvicorn",
        "main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]



def _frontend_cmd() -> list[str]:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm est introuvable dans le PATH.")
    return [npm, "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]



def _print_banner() -> None:
    print(ASCII_IMEG)
    print("IMEG launcher")
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:5173")
    print()



def _run_targets(run_backend: bool, run_frontend: bool) -> int:
    processes: list[ManagedProcess] = []

    try:
        if run_backend:
            processes.append(ManagedProcess("backend", _backend_cmd(), BACKEND_DIR))
        if run_frontend:
            processes.append(ManagedProcess("frontend", _frontend_cmd(), FRONTEND_DIR))

        if not processes:
            print("Aucun service selectionne.")
            return 1

        for managed in processes:
            managed.start()

        print("Services lances. Ctrl+C pour arreter.")

        while True:
            exited = [p for p in processes if p.proc and p.proc.poll() is not None]
            if exited:
                for p in exited:
                    code = p.proc.poll() if p.proc else "?"
                    print(f"Le service {p.name} s'est arrete (code={code}).")
                return 1
            signal.pause()

    except KeyboardInterrupt:
        print("\nArret des services...")
        return 0
    except RuntimeError as err:
        print(f"Erreur: {err}")
        return 1
    finally:
        for managed in processes:
            managed.stop()



def _menu() -> str:
    print("Selectionne un mode:")
    print("1) Tout lancer (backend + frontend)")
    print("2) Backend uniquement")
    print("3) Frontend uniquement")
    print("4) Quitter")
    while True:
        choice = input("> ").strip()
        if choice in {"1", "2", "3", "4"}:
            return choice
        print("Choix invalide. Essaie 1, 2, 3 ou 4.")



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IMEG dev launcher")
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["all", "backend", "frontend", "menu"],
        default="menu",
        help="Mode de lancement",
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    _print_banner()

    mode = args.mode
    if mode == "menu":
        selected = _menu()
        if selected == "1":
            mode = "all"
        elif selected == "2":
            mode = "backend"
        elif selected == "3":
            mode = "frontend"
        else:
            print("Au revoir.")
            return 0

    if mode == "all":
        return _run_targets(run_backend=True, run_frontend=True)
    if mode == "backend":
        return _run_targets(run_backend=True, run_frontend=False)
    if mode == "frontend":
        return _run_targets(run_backend=False, run_frontend=True)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

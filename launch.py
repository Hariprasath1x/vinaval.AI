"""
launch.py — Vinaval AI Robust Launcher
=======================================
Single source of truth for startup configuration.
This script replaces the brittle `start cmd /k` approach in start.bat.

What it does:
  1. Kills any orphaned processes on the backend/frontend ports.
  2. Starts uvicorn (backend) and streamlit (frontend) as managed subprocesses.
  3. Waits with health checks until BOTH are genuinely reachable.
  4. Opens the browser only after confirmed HTTP 200.
  5. On Ctrl+C, terminates BOTH child processes cleanly.
  6. Logs everything to logs/startup_<timestamp>.log.
"""

import os
import sys
import subprocess
import socket
import time
import signal
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# SINGLE SOURCE OF TRUTH — all ports/addresses defined here only
# ─────────────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.resolve()
BACKEND_DIR  = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
VENV_PYTHON  = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
LOG_DIR      = ROOT / "logs"
LOG_FILE     = LOG_DIR / f"startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

BACKEND_HOST  = "127.0.0.1"
BACKEND_PORT  = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 8501

HEALTH_TIMEOUT  = 90   # seconds to wait for each server to come up
HEALTH_INTERVAL = 1    # seconds between health-check polls


# ─────────────────────────────────────────────────────────────────────────────
# Logging: writes to both stdout and a log file
# ─────────────────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
# Force UTF-8 on stdout so emoji/Unicode work on Windows cp1252 terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        console_handler,
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────
def kill_port(port: int) -> None:
    """Kill any process currently holding a TCP LISTEN on the given port."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = int(parts[-1])
                if pid == 0:
                    continue
                sub = subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, text=True,
                )
                if sub.returncode == 0:
                    log.info(f"  Killed orphaned PID {pid} (was holding port {port})")
                else:
                    log.warning(f"  Could not kill PID {pid}: {sub.stderr.strip()}")
                time.sleep(0.5)
    except Exception as exc:
        log.warning(f"  Port cleanup error for {port}: {exc}")


def is_port_open(host: str, port: int) -> bool:
    """Return True if a TCP connection can be made to host:port."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, label: str = "") -> bool:
    """Spin-poll until the port is open or HEALTH_TIMEOUT elapses."""
    deadline = time.time() + HEALTH_TIMEOUT
    dots = 0
    while time.time() < deadline:
        if is_port_open(host, port):
            return True
        sys.stdout.write(".")
        sys.stdout.flush()
        dots += 1
        time.sleep(HEALTH_INTERVAL)
    print()  # newline after dots
    return False


def wait_for_http(url: str) -> bool:
    """Spin-poll URL until it returns a non-5xx HTTP response."""
    deadline = time.time() + HEALTH_TIMEOUT
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status < 500:
                    return True
        except Exception:
            pass
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(HEALTH_INTERVAL)
    print()
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Main launcher
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Header ──
    log.info("=" * 60)
    log.info("  Vinaval AI — Robust Launcher")
    log.info("=" * 60)
    log.info(f"  Root             : {ROOT}")
    log.info(f"  Python (venv)    : {VENV_PYTHON}")
    log.info(f"  Working dir      : {os.getcwd()}")
    log.info(f"  Backend address  : http://{BACKEND_HOST}:{BACKEND_PORT}")
    log.info(f"  Frontend address : http://{FRONTEND_HOST}:{FRONTEND_PORT}")
    log.info(f"  Log file         : {LOG_FILE}")

    # ── Pre-flight checks ──
    if not VENV_PYTHON.exists():
        log.error(f"Virtual environment not found: {VENV_PYTHON}")
        log.error(
            "Please create it first:\n"
            "  cd backend\n"
            "  python -m venv venv\n"
            "  venv\\Scripts\\pip install -r requirements.txt"
        )
        sys.exit(1)

    if not (FRONTEND_DIR / "app.py").exists():
        log.error(f"frontend/app.py not found at: {FRONTEND_DIR / 'app.py'}")
        sys.exit(1)

    # Streamlit version for log
    try:
        ver = subprocess.run(
            [str(VENV_PYTHON), "-m", "streamlit", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        log.info(f"  Streamlit        : {ver.stdout.strip()}")
    except Exception as exc:
        log.warning(f"  Streamlit version check failed: {exc}")

    # ── Step 1: Kill orphans ──
    log.info("")
    log.info("Step 1 — Cleaning up orphaned processes on ports...")
    kill_port(BACKEND_PORT)
    kill_port(FRONTEND_PORT)
    time.sleep(1)  # Allow OS to release port bindings

    # ── Step 2: Start Backend ──
    log.info("")
    log.info("Step 2 — Starting FastAPI Backend (uvicorn)...")
    backend_env = os.environ.copy()
    backend_env["HF_HUB_OFFLINE"] = "1"   # Skip HuggingFace model-update network check

    backend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "uvicorn",
            "app.main:app",
            "--reload",
            "--host", BACKEND_HOST,
            "--port", str(BACKEND_PORT),
        ],
        cwd=str(BACKEND_DIR),
        env=backend_env,
    )
    log.info(f"  Backend PID: {backend_proc.pid}")

    # ── Step 3: Wait for backend health ──
    log.info(f"  Waiting for backend on port {BACKEND_PORT} (up to {HEALTH_TIMEOUT}s) ", )
    t0 = time.time()
    if not wait_for_port(BACKEND_HOST, BACKEND_PORT, "backend"):
        log.error(f"\nBackend did not start within {HEALTH_TIMEOUT}s. Aborting.")
        backend_proc.terminate()
        sys.exit(1)
    log.info(f"  [OK] Backend ready in {time.time() - t0:.1f}s")

    # ── Step 4: Start Frontend ──
    log.info("")
    log.info("Step 4 — Starting Streamlit Frontend...")
    frontend_proc = subprocess.Popen(
        [
            str(VENV_PYTHON), "-m", "streamlit", "run", "app.py",
            "--server.address", FRONTEND_HOST,
            "--server.port", str(FRONTEND_PORT),
            "--server.headless", "true",
        ],
        cwd=str(FRONTEND_DIR),
        env=os.environ.copy(),
    )
    log.info(f"  Frontend PID: {frontend_proc.pid}")

    # ── Step 5: Wait for frontend HTTP health ──
    frontend_url = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
    log.info(f"  Waiting for frontend at {frontend_url} (up to {HEALTH_TIMEOUT}s) ")
    t0 = time.time()
    if not wait_for_http(frontend_url):
        log.error(f"\nFrontend did not respond within {HEALTH_TIMEOUT}s. Aborting.")
        backend_proc.terminate()
        frontend_proc.terminate()
        sys.exit(1)
    log.info(f"  [OK] Frontend ready in {time.time() - t0:.1f}s")

    # ── Step 6: Open browser ──
    log.info("")
    log.info(f"Step 6 — Opening browser at {frontend_url}")
    try:
        import webbrowser
        webbrowser.open(frontend_url)
    except Exception as exc:
        log.warning(f"  Could not open browser automatically: {exc}")
        log.info(f"  Please open manually: {frontend_url}")

    log.info("")
    log.info("=" * 60)
    log.info("  [READY] Application is running!")
    log.info(f"  Backend  : http://{BACKEND_HOST}:{BACKEND_PORT}")
    log.info(f"  Frontend : {frontend_url}")
    log.info("  Press Ctrl+C to stop BOTH servers.")
    log.info("=" * 60)

    # ── Step 7: Monitor & graceful shutdown ──
    def shutdown(signum=None, frame=None):
        log.info("\nShutdown requested — stopping servers...")
        for proc, name in [(frontend_proc, "Frontend"), (backend_proc, "Backend")]:
            proc.terminate()
            try:
                proc.wait(timeout=5)
                log.info(f"  {name} stopped.")
            except subprocess.TimeoutExpired:
                proc.kill()
                log.info(f"  {name} force-killed.")
        log.info("Both servers stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Keep alive; exit if either child crashes unexpectedly
    while True:
        time.sleep(2)
        ret = backend_proc.poll()
        if ret is not None:
            if ret in (-1, 1, -2, -15):  # likely Ctrl+C / SIGINT / SIGTERM
                log.info("Backend stopped (user exit).")
            else:
                log.error(f"Backend crashed unexpectedly (exit code {ret})!")
            shutdown()
        ret = frontend_proc.poll()
        if ret is not None:
            if ret in (-1, 1, -2, -15):
                log.info("Frontend stopped (user exit).")
            else:
                log.error(f"Frontend crashed unexpectedly (exit code {ret})!")
            shutdown()


if __name__ == "__main__":
    main()

"""
launch.py — Vinaval AI Robust Launcher
=======================================
Single source of truth for startup configuration.

What it does:
  1. Kills any orphaned processes on the backend port.
  2. Starts uvicorn (backend) as a managed subprocess.
  3. Waits with health checks until it is genuinely reachable.
  4. On Ctrl+C, terminates the child process cleanly.
  5. Logs everything to logs/startup_<timestamp>.log.
  
Note: The React frontend should be started separately using `npm run dev` in the frontend directory.
"""

import os
import sys
import subprocess
import socket
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# SINGLE SOURCE OF TRUTH — all ports/addresses defined here only
# ─────────────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.resolve()
BACKEND_DIR  = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
if sys.platform == "win32":
    VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
else:
    unix_venv_py = BACKEND_DIR / "venv" / "bin" / "python"
    VENV_PYTHON = unix_venv_py if unix_venv_py.exists() else Path(sys.executable)

LOG_DIR      = ROOT / "logs"
LOG_FILE     = LOG_DIR / f"startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

BACKEND_HOST  = "127.0.0.1"
BACKEND_PORT  = 8000

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
        if sys.platform == "win32":
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
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                if line.strip().isdigit():
                    pid = int(line.strip())
                    if pid == os.getpid():
                        continue
                    os.kill(pid, signal.SIGTERM)
                    log.info(f"  Killed orphaned PID {pid} (was holding port {port})")
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


# ─────────────────────────────────────────────────────────────────────────────
# Main launcher
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # ── Header ──
    log.info("=" * 60)
    log.info("  Vinaval AI — Robust Launcher (Backend Only)")
    log.info("=" * 60)
    log.info(f"  Root             : {ROOT}")
    log.info(f"  Python (venv)    : {VENV_PYTHON}")
    log.info(f"  Working dir      : {os.getcwd()}")
    log.info(f"  Backend address  : http://{BACKEND_HOST}:{BACKEND_PORT}")
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

    # ── Step 1: Kill orphans ──
    log.info("")
    log.info("Step 1 — Cleaning up orphaned processes on backend port...")
    kill_port(BACKEND_PORT)
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

    log.info("")
    log.info("=" * 60)
    log.info("  [READY] Backend is running!")
    log.info(f"  Backend API : http://{BACKEND_HOST}:{BACKEND_PORT}")
    log.info("=" * 60)
    log.info("  👉 TO START THE FRONTEND:")
    log.info("     Open a new terminal, and run:")
    log.info("     cd frontend")
    log.info("     npm install")
    log.info("     npm run dev")
    log.info("=" * 60)
    log.info("  Press Ctrl+C to stop the backend server.")

    # ── Step 4: Monitor & graceful shutdown ──
    def shutdown(signum=None, frame=None):
        log.info("\nShutdown requested — stopping backend...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
            log.info("  Backend stopped.")
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            log.info("  Backend force-killed.")
        log.info("Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    # Keep alive; exit if child crashes unexpectedly
    while True:
        time.sleep(2)
        ret = backend_proc.poll()
        if ret is not None:
            if ret in (-1, 1, -2, -15):  # likely Ctrl+C / SIGINT / SIGTERM
                log.info("Backend stopped (user exit).")
            else:
                log.error(f"Backend crashed unexpectedly (exit code {ret})!")
            shutdown()

if __name__ == "__main__":
    main()

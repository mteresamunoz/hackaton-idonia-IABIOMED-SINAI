"""
Logging configuration — Hackathon IABiomed 2026 — SINAI-UJA

Each module gets its own log file in logs/<module_name>.log
in addition to writing to the console. This allows debugging without relying only
on the terminal, and errors are captured for later analysis.
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str, log_dir: str | Path | None = None) -> logging.Logger:
    """
    Returns a logger configured with:
      - Console output (INFO+)
      - File output (DEBUG+) in logs/<name>.log (or in log_dir if passed)

    Args:
        name: Name of the module (use __name__).
        log_dir: Custom directory where the .log will be saved. If None, uses logs/.
    """
    logger = logging.getLogger(name)

    # If it already has handlers and no folder change is requested, return it as is
    if logger.handlers and log_dir is None:
        return logger

    logger.setLevel(logging.DEBUG)

    # If a custom folder is requested, clean up old file handlers
    # to avoid duplicates or writing to old paths
    if log_dir is not None:
        for h in list(logger.handlers):
            if isinstance(h, logging.FileHandler):
                logger.removeHandler(h)
                h.close()

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Console (only if it doesn't exist)
    has_console = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    if not has_console:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)

    # Module's own file
    target_dir = Path(log_dir) if log_dir else LOG_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(".", "_").replace("\\", "_").replace("/", "_")
    file_path = target_dir / f"{safe_name}.log"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

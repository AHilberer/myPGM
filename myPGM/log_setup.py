"""Logging configuration for the myPGM application.

Messages go to the terminal (stderr) and to a rotating log file in the
user's application data folder, e.g. on macOS
~/Library/Application Support/myPGM/mypgm.log. Start with --debug for
detailed messages (files loaded, fits, sessions).
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "mypgm.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# set by setup_logging, shown in the unexpected-error dialog
log_file_path = None


def default_log_dir():
    """Per-user application data folder (needs the QApplication name to be set)."""
    from PyQt5.QtCore import QStandardPaths
    location = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(location) if location else None


def setup_logging(debug=False, log_dir=None):
    """Configure the 'myPGM' logger. Returns the log file path, or None if the
    file could not be created (messages then only go to the terminal).

    Safe to call again: handlers from a previous call are replaced.
    """
    global log_file_path
    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("myPGM")
    for handler in list(logger.handlers):
        if getattr(handler, "_mypgm", False):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(level)
    logger.propagate = False   # our handlers only, no duplicates via the root logger

    formatter = logging.Formatter(LOG_FORMAT)
    handlers = []
    # no stderr when started without a console (e.g. pythonw on Windows)
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler(sys.stderr))

    log_file_path = None
    file_error = None
    try:
        log_dir = Path(log_dir) if log_dir is not None else default_log_dir()
        if log_dir is not None:
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / LOG_FILE_NAME
            handlers.append(RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3,
                                                encoding="utf-8"))
            log_file_path = path
    except OSError as exc:
        file_error = exc

    for handler in handlers:
        handler._mypgm = True
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if file_error is not None:
        logger.warning("Could not create the log file: %s", file_error)
    return log_file_path

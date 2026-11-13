"""Automatic session backup, recovered after a crash.

Each myPGM window has its own backup file in the user's application data
folder, autosave_session_<pid>_<start time>_<random>.json, locked
(autosave_session_....lock) while the window is open: several windows never
recover or delete each other's backups. A backup whose lock is no longer held
was left by a window that did not close normally, and is offered for recovery.
"""
import glob
import json
import logging
import os
import threading
import time
import uuid

from PyQt5.QtCore import QLockFile

logger = logging.getLogger(__name__)

PREFIX = "autosave_session"
DISCARDED_SUFFIX = ".discarded.json"


def write_json(data, file_path):
    """Write data as JSON, through a temporary file, so that a crash never leaves
    a half-written file. Compact: indented, every number of every spectrum took a
    line (about 2x larger)."""
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle)
    os.replace(tmp_path, file_path)


def _lock(path):
    lock = QLockFile(path)
    lock.setStaleLockTime(0)        # only the owner process being gone matters
    return lock


class SessionBackup:
    """The backup file of one window, written in a background thread."""

    def __init__(self, folder):
        self.folder = folder
        base = os.path.join(folder, f"{PREFIX}_{os.getpid()}_"
                                    f"{int(time.time())}_{uuid.uuid4().hex[:6]}")
        self.path = base + ".json"
        self._lock = _lock(base + ".lock")
        if not self._lock.tryLock(0):
            logger.warning("Could not lock the session backup %s", base + ".lock")
        self._fingerprint = None    # of the content written last
        self._thread = None
        self._failed = False        # warned once, then only debug messages

    def is_up_to_date(self, fingerprint):
        """True if this content is already backed up, or a backup is being written
        (the next one waits for the next autosave)."""
        return (fingerprint == self._fingerprint
                or (self._thread is not None and self._thread.is_alive()))

    def write(self, session, fingerprint):
        """Encode and write the session (collected by the caller) in a thread, so
        that large sessions do not freeze the app."""
        self._fingerprint = fingerprint

        def write():
            try:
                write_json(session, self.path)
                logger.debug("Session backup written to %s", self.path)
            except OSError as exc:
                if not self._failed:
                    self._failed = True
                    logger.warning("Could not write the session backup (no automatic backup "
                                   "until this is fixed): %s", exc)
                else:
                    logger.debug("Could not write the session backup: %s", exc)

        self._thread = threading.Thread(target=write, name="session-backup", daemon=True)
        self._thread.start()

    def flush(self):
        """Wait for a backup being written, if any."""
        if self._thread is not None:
            self._thread.join(timeout=30)

    def remove(self):
        self.flush()                # so that a write in progress cannot re-create it
        self._fingerprint = None
        if os.path.exists(self.path):
            os.remove(self.path)

    def close(self):
        """The window closed normally: no recovery needed next time."""
        self.remove()
        self._lock.unlock()

    def orphans(self):
        """Backups left by windows that did not close normally (their lock is not
        held any more), newest first. Backups of windows still open are skipped.
        Also cleans up what crashed windows left without a backup."""
        orphans = []
        for path in glob.glob(os.path.join(self.folder, PREFIX + "*.json")):
            if path == self.path or path.endswith(DISCARDED_SUFFIX):
                continue
            lock = _lock(os.path.splitext(path)[0] + ".lock")
            if not lock.tryLock(0):
                continue                # another myPGM window is still using it
            lock.unlock()               # stale lock of a crashed window: cleaned up
            orphans.append(path)
        # half-written backups of windows that crashed while writing one
        for tmp_path in glob.glob(os.path.join(self.folder, PREFIX + "*.json.tmp")):
            lock = _lock(tmp_path[:-len(".json.tmp")] + ".lock")
            if lock.tryLock(0):         # its window is gone (a live one may be writing it)
                lock.unlock()
                os.remove(tmp_path)
        # locks left by windows that crashed with nothing to back up
        for lock_path in glob.glob(os.path.join(self.folder, PREFIX + "*.lock")):
            if os.path.exists(os.path.splitext(lock_path)[0] + ".json"):
                continue
            lock = _lock(lock_path)
            if lock.tryLock(0):
                lock.unlock()           # removes the stale lock file
        return sorted(orphans, key=os.path.getmtime, reverse=True)

    @staticmethod
    def set_aside(path):
        """Keep a backup that will not be recovered as *.discarded.json, out of the
        backups offered at startup. Returns its new path."""
        discarded = os.path.splitext(path)[0] + DISCARDED_SUFFIX
        os.replace(path, discarded)
        return discarded

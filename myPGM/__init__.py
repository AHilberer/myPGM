import sys
import os
import ctypes
import logging
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLocale, QLoggingCategory

from myPGM.helpers import load_style, get_app_icon
from myPGM.ui.main_ui import MainWindow
from myPGM.data_model import PressureGaugeDataManager
from myPGM.presenter import Presenter
from myPGM import log_setup

logger = logging.getLogger(__name__)

def _set_windows_appusermodelid():
    """Improve Windows taskbar icon association for non-frozen launches."""
    if os.name != "nt":
        return

    app_id = "myPGM.myPressureGaugeMonitor"
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

REPEATED_ERROR_WINDOW_S = 10


def _install_excepthook():
    """Show unexpected errors in a dialog instead of letting PyQt abort the app.
    An error identical to one shown less than REPEATED_ERROR_WINDOW_S ago (after
    its dialog was closed), or raised while an error dialog is open, is only
    logged with a repeat count: a repeated error does not flood the screen."""
    state = {"dialog_open": False, "closed_at": {}, "repeats": {}}

    def excepthook(exc_type, exc_value, exc_tb):
        key = (exc_type.__name__, str(exc_value))
        closed_at = state["closed_at"].get(key)
        recent = closed_at is not None and time.monotonic() - closed_at < REPEATED_ERROR_WINDOW_S
        if state["dialog_open"] or recent:
            state["repeats"][key] = state["repeats"].get(key, 0) + 1
            logger.error("Unexpected error repeated (%d times, not shown again): %s: %s",
                         state["repeats"][key], *key)
            return
        state["repeats"][key] = 0
        logger.error("Unexpected error", exc_info=(exc_type, exc_value, exc_tb))
        if QApplication.instance() is not None:
            text = f"{exc_type.__name__}: {exc_value}"
            if log_setup.log_file_path is not None:
                text += f"\n\nDetails were saved in the log file:\n{log_setup.log_file_path}"
            state["dialog_open"] = True
            try:
                QMessageBox.critical(None, "Unexpected error", text)
            finally:
                state["dialog_open"] = False
                state["closed_at"][key] = time.monotonic()
    sys.excepthook = excepthook

def main():
    _set_windows_appusermodelid()
    # Qt 5's Wayland backend warns on every window activation it cannot perform
    # ("Wayland does not support QWindow::requestActivate()"); harmless, so muted.
    # A QT_LOGGING_RULES environment variable still overrides this.
    QLoggingCategory.setFilterRules("qt.qpa.wayland.warning=false")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("myPGM")
    # after setApplicationName, which sets the log folder name
    log_file = log_setup.setup_logging(debug="--debug" in sys.argv)
    _install_excepthook()
    logger.info("myPGM started%s, log file: %s",
                " in debug mode" if "--debug" in sys.argv else "", log_file)
    app_icon = get_app_icon()
    # decimal '.'
    QLocale.setDefault(QLocale(QLocale.C))

    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    try:
        style = load_style('light-mode.qss')
        app.setStyleSheet(style)
    except Exception as exc:
        logger.warning("Could not load the light-mode stylesheet: %s", exc)
    model = PressureGaugeDataManager()
    view = MainWindow()
    if not app_icon.isNull():
        view.setWindowIcon(app_icon)
    # example session (fitted spectra in the PvPm table) only on request: --demo
    demo = "--demo" in sys.argv
    backup_dir = log_setup.default_log_dir()
    presenter = Presenter(model, view, demo=demo,
                          backup_dir=str(backup_dir) if backup_dir is not None else None)
    presenter.view.show()
    if not demo:
        presenter.offer_recovery()

    sys.exit(app.exec_())


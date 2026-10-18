import sys
import os
import ctypes
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLocale

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

def _install_excepthook():
    """Show unexpected errors in a dialog instead of letting PyQt abort the app."""
    def excepthook(exc_type, exc_value, exc_tb):
        logger.error("Unexpected error", exc_info=(exc_type, exc_value, exc_tb))
        if QApplication.instance() is not None:
            text = f"{exc_type.__name__}: {exc_value}"
            if log_setup.log_file_path is not None:
                text += f"\n\nDetails were saved in the log file:\n{log_setup.log_file_path}"
            QMessageBox.critical(None, "Unexpected error", text)
    sys.excepthook = excepthook

def main():
    _set_windows_appusermodelid()
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
    # example spectra are only loaded on request: python run.py --demo
    presenter = Presenter(model, view, test_mode="--demo" in sys.argv)
    presenter.view.show()

    sys.exit(app.exec_())


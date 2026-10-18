import sys
import os
import ctypes
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QLocale

from myPGM.helpers import load_style, get_app_icon
from myPGM.ui.main_ui import MainWindow
from myPGM.data_model import PressureGaugeDataManager
from myPGM.presenter import Presenter


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
        traceback.print_exception(exc_type, exc_value, exc_tb)
        if QApplication.instance() is not None:
            QMessageBox.critical(None, "Unexpected error",
                                 f"{exc_type.__name__}: {exc_value}")
    sys.excepthook = excepthook


def main():
#    os.chdir(os.path.abspath(__file__).replace(os.path.basename(__file__), ""))
    _set_windows_appusermodelid()
    _install_excepthook()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("myPGM")
    app_icon = get_app_icon()
    # decimal '.'
    QLocale.setDefault(QLocale(QLocale.C))

    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    try:
        style = load_style('light-mode.qss')
        app.setStyleSheet(style)
    except Exception as e:
        print(e)
        pass
    model = PressureGaugeDataManager()
    view = MainWindow()
    if not app_icon.isNull():
        view.setWindowIcon(app_icon)
    presenter = Presenter(model, view, test_mode=True)
    presenter.view.show()
    #presenter.initialize_example()

    sys.exit(app.exec_())


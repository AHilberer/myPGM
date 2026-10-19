import os

# Qt must be headless for tests (and CI); set before any PyQt5 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest


RESOURCES = Path(__file__).resolve().parents[1] / "myPGM" / "resources"


@pytest.fixture(scope="session")
def resources():
    return RESOURCES


def dispose(view):
    """Close a main window and delete it with its side windows. Windows that are
    only closed stay alive and slow down every later stylesheet change."""
    from PyQt5.QtWidgets import QApplication
    view.close_guard = None
    view.close()
    for window in (view.PvPmTableWindow, view.PvPmPlotWindow,
                   view.additional_toolbox_window, view.font_size_window, view):
        if window is not None:
            window.deleteLater()
    QApplication.processEvents()


@pytest.fixture(autouse=True)
def no_blocking_questions(monkeypatch):
    """Closing a window with unsaved changes asks Save/Discard/Cancel, and startup
    may offer to recover a backup: answer them in tests instead of blocking."""
    from myPGM.ui.main_ui import MainWindow
    monkeypatch.setattr(MainWindow, "ask_save_changes", lambda self: "discard")
    monkeypatch.setattr(MainWindow, "ask_recover_session", lambda self, when: False)


@pytest.fixture(scope="session")
def qapp():
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app


@pytest.fixture
def gui(qapp):
    """Main window + presenter with the example files loaded.

    Error popups are recorded in gui.errors instead of being shown.
    """
    from myPGM.helpers import load_style
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter

    qapp.setStyleSheet(load_style("light-mode.qss"))
    view = MainWindow()
    presenter = Presenter(PressureGaugeDataManager(), view, test_mode=True)

    class Gui:
        pass
    g = Gui()
    g.app, g.view, g.presenter, g.errors = qapp, view, presenter, []
    # dialogs only: _show_error still logs
    presenter._error_dialog = lambda text, title="Error": g.errors.append(title)
    view.fit_error_popup_window = lambda: g.errors.append("Fit error")
    g.file_id = lambda name: next(
        i for i in presenter.ordered_files_to_display if presenter.model[i].filename == name
    )

    yield g

    dispose(view)
    qapp.setStyleSheet("")


@pytest.fixture
def demo(qapp):
    from myPGM.helpers import load_style
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    qapp.setStyleSheet(load_style("light-mode.qss"))
    view = MainWindow()
    errors = []
    # record error popups instead of showing them, before the demo is built
    view.fit_error_popup_window = lambda: errors.append("Fit error")
    from PyQt5.QtWidgets import QMessageBox
    original_exec = QMessageBox.exec_
    QMessageBox.exec_ = lambda self: errors.append(self.windowTitle())
    try:
        presenter = Presenter(PressureGaugeDataManager(), view, demo=True)
    finally:
        QMessageBox.exec_ = original_exec
    yield presenter, view, errors
    dispose(view)
    qapp.setStyleSheet("")

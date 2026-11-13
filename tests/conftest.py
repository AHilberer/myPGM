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
def delete_leftover_windows():
    """Delete the top-level widgets a test leaves behind. Disposing a main window does
    not delete everything: pyqtgraph's plot option panels and menus stay alive as
    parentless widgets (about 2000 per window). Each later stylesheet change restyles
    all of them, and the tests got slower and slower (6 s per window at the end)."""
    from PyQt5 import sip
    from PyQt5.QtCore import QEvent
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    before = ({sip.unwrapinstance(w) for w in app.topLevelWidgets()}
              if app is not None else set())
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        # a top-level widget with a parent (combo box popup, submenu) belongs to it
        if (sip.unwrapinstance(widget) not in before and not sip.isdeleted(widget)
                and widget.parent() is None):
            widget.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    """Settings (theme, font size, folders) in a temporary folder: tests must not
    read or change the user's own settings."""
    from PyQt5.QtCore import QSettings
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path / "settings"))
    return tmp_path / "settings"


@pytest.fixture(autouse=True)
def no_blocking_questions(monkeypatch):
    """Closing a window with unsaved changes asks Save/Discard/Cancel: answer it in
    tests instead of blocking. (Recovering a backup is a non-blocking banner.)"""
    from myPGM.ui.main_ui import MainWindow
    monkeypatch.setattr(MainWindow, "ask_save_changes", lambda self: "discard")


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
    from myPGM.ui import theme
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter

    qapp.setStyleSheet(theme.stylesheet(dark=False))
    view = MainWindow()
    presenter = Presenter(PressureGaugeDataManager(), view, test_mode=True)

    class Gui:
        pass
    g = Gui()
    g.app, g.view, g.presenter, g.errors = qapp, view, presenter, []
    # dialogs only: _show_error still logs
    presenter._error_dialog = lambda text, title="Error": g.errors.append(title)
    g.fit_error_reasons = []
    view.fit_error_popup_window = lambda reason="": (g.errors.append("Fit error"),
                                                     g.fit_error_reasons.append(reason))
    g.file_id = lambda name: next(
        i for i in presenter.ordered_files_to_display if presenter.model[i].filename == name
    )

    yield g

    dispose(view)
    qapp.setStyleSheet("")


@pytest.fixture
def demo(qapp):
    from myPGM.ui import theme
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    qapp.setStyleSheet(theme.stylesheet(dark=False))
    view = MainWindow()
    errors = []
    # record error popups instead of showing them, before the demo is built
    view.fit_error_popup_window = lambda reason="": errors.append("Fit error")
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

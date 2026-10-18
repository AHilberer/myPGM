import os

# Qt must be headless for tests (and CI); set before any PyQt5 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest


RESOURCES = Path(__file__).resolve().parents[1] / "myPGM" / "resources"


@pytest.fixture(scope="session")
def resources():
    return RESOURCES


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

    view.close()
    for window in (view.PvPmTableWindow, view.PvPmPlotWindow,
                   view.additional_toolbox_window, view.font_size_window, view):
        if window is not None:
            window.deleteLater()
    qapp.setStyleSheet("")
    qapp.processEvents()

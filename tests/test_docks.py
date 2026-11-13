"""Bottom panels (DESIGN.md §1 "Bottom dock area", IMPLEMENTATION_PLAN step 3): the
pressure log and the P vs Pm plot in docks, undockable, closable, sized and saved."""
import pytest
from PyQt5.QtCore import Qt

from conftest import dispose
from myPGM.ui.docks import MIN_HEIGHT
from myPGM.ui.widgets import GAP


def _settle(app):
    for _ in range(4):
        app.processEvents()


@pytest.fixture
def shown(gui):
    """The gui window shown at the mockup size (dock sizes need a shown window)."""
    gui.view.resize(1440, 1010)
    gui.view.show()
    _settle(gui.app)
    return gui


def test_panels_are_docked_side_by_side(gui):
    view = gui.view
    assert view.log_dock.widget().isAncestorOf(view.PvPmTableWindow)
    assert view.plot_dock.widget().isAncestorOf(view.PvPmPlotWindow)
    for dock in (view.log_dock, view.plot_dock):
        assert view.dockWidgetArea(dock) == Qt.BottomDockWidgetArea
        assert dock.allowedAreas() == Qt.BottomDockWidgetArea
        assert dock.objectName()                 # needed by saveState
    assert not hasattr(view, "toggle_PvPm_button")
    view_menu = [a.text() for a in view.view_menu.actions()]
    assert view_menu == ["Pressure log", "P vs Pm"]


def test_headers(demo):
    _presenter, view, _ = demo
    log_header, plot_header = view.log_dock.header, view.plot_dock.header
    assert log_header.title_label.text() == "PRESSURE LOG"
    assert plot_header.title_label.text() == "P VS PM"
    table = view.PvPmTableWindow
    for widget in [table.count_label] + table.header_actions:
        assert log_header.isAncestorOf(widget)
    assert table.count_label.text() == "4 points"
    assert plot_header.isAncestorOf(view.PvPmPlotWindow.legend_label)
    legend = view.PvPmPlotWindow.legend_label.text()
    assert "Ruby2020" in legend and "H2 vibron" in legend
    assert log_header.close_button.toolTip() == "Hide the pressure log"


def test_point_count(gui):
    table = gui.view.PvPmTableWindow
    assert table.count_label.text() == "No points"          # step 5: empty state wording
    table.table_widget.rows_changed.emit(1)
    assert table.count_label.text() == "1 point"


def test_columns_button_menu(gui):
    menu = gui.view.PvPmTableWindow.table_widget.column_menu()
    assert "σx (fit)" in [a.text() for a in menu.actions()]


def test_undock_and_dock_back(shown):
    view, dock = shown.view, shown.view.plot_dock
    header = dock.header
    assert header.float_button.toolTip() == "Undock" and header.caption.isHidden()
    header.float_button.click()
    _settle(shown.app)
    assert dock.isFloating()
    assert header.float_button.toolTip() == "Dock back"
    assert not header.caption.isHidden() and header.title_label.text() == "P vs Pm"
    # the log takes the whole width, floating panels keep their own size
    assert view.log_dock.width() == view.width()
    assert dock.maximumHeight() > view.height()
    header.float_button.click()
    _settle(shown.app)
    assert not dock.isFloating() and header.title_label.text() == "P VS PM"


def test_default_sizes(shown):
    view = shown.view
    view._default_dock_sizes()
    _settle(shown.app)
    assert view.log_dock.height() == pytest.approx(0.28 * view.height(), abs=20)
    total = view.log_dock.width() + view.plot_dock.width()
    assert view.log_dock.width() / total == pytest.approx(0.7, abs=0.03)


def test_bottom_area_height_limits(shown):
    view = shown.view
    for dock in (view.log_dock, view.plot_dock):
        assert dock.minimumHeight() == MIN_HEIGHT
        assert dock.maximumHeight() == int(view.height() * 0.5)
    view.resizeDocks([view.log_dock], [900], Qt.Vertical)
    _settle(shown.app)
    assert view.log_dock.height() <= view.height() * 0.5


def test_hiding_both_panels_gives_the_workspace_the_full_height(shown):
    view, bar = shown.view, shown.view.top_bar
    assert view.workspace_layout.contentsMargins().bottom() == 0
    bar.log_toggle.click()
    bar.plot_toggle.click()
    _settle(shown.app)
    assert view.workspace_layout.contentsMargins().bottom() == GAP
    assert view.centralWidget().height() > view.height() - 100
    bar.plot_toggle.click()
    _settle(shown.app)
    assert view.workspace_layout.contentsMargins().bottom() == 0
    # the shown panel takes the whole width, 8 px from both window edges
    assert view.plot_dock.width() == view.width()
    margins = view.plot_dock.widget().layout().contentsMargins()
    assert (margins.left(), margins.right(), margins.bottom()) == (GAP, GAP, GAP)


def test_panel_layout_is_restored(shown, qapp):
    from myPGM.ui.main_ui import MainWindow
    shown.view.top_bar.plot_toggle.click()
    shown.view.close()                       # saves the layout
    view = MainWindow()
    try:
        assert view.plot_dock.isHidden() and not view.log_dock.isHidden()
        assert not view.top_bar.plot_toggle.isChecked()
    finally:
        dispose(view)


def test_new_point_is_scrolled_into_view(gui, monkeypatch):
    table = gui.view.PvPmTableWindow.table_widget
    scrolled = []
    monkeypatch.setattr(table, "_scroll_to_number", scrolled.append)
    gui.presenter.add_current_PToolbox_to_table()
    assert scrolled == [1]
    table.updatetable()                       # no new point: no scroll
    assert scrolled == [1]

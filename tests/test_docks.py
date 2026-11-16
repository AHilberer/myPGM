"""Bottom panels (DESIGN.md §1 "Bottom dock area"): the
pressure log and the P vs Pm plot in docks, undockable, closable, sized and saved."""
import pytest
from PyQt5.QtCore import QPoint, QRect, Qt

from conftest import dispose
from myPGM.ui.docks import MIN_HEIGHT
from myPGM.ui.widgets import GAP


def _settle(app):
    for _ in range(4):
        app.processEvents()


@pytest.fixture
def shown(gui):
    """The gui window shown at the default size, 1440 x 1010 (dock sizes need a shown window)."""
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


@pytest.mark.parametrize("environ, platform, expected", [
    # Wayland session with XWayland: xcb, so floating docks can be dragged
    ({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, "linux", "xcb"),
    ({"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}, "linux", "xcb"),
    # the user's choice is kept
    ({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0", "QT_QPA_PLATFORM": "wayland"},
     "linux", "wayland"),
    # no XWayland, X11 session, other systems: untouched
    ({"WAYLAND_DISPLAY": "wayland-0"}, "linux", None),
    ({"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}, "linux", None),
    ({"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":0"}, "darwin", None),
])
def test_xcb_is_preferred_on_wayland(environ, platform, expected):
    from myPGM import _prefer_xcb_on_wayland
    _prefer_xcb_on_wayland(environ, platform)
    assert environ.get("QT_QPA_PLATFORM") == expected


def _send_mouse(widget, kind, global_pos, button=Qt.LeftButton):
    from PyQt5.QtCore import QEvent
    from PyQt5.QtGui import QMouseEvent
    from PyQt5.QtWidgets import QApplication
    event_type = {"press": QEvent.MouseButtonPress, "move": QEvent.MouseMove,
                  "release": QEvent.MouseButtonRelease}[kind]
    QApplication.sendEvent(widget, QMouseEvent(
        event_type, widget.mapFromGlobal(global_pos), global_pos,
        Qt.NoButton if kind == "move" else button,
        Qt.NoButton if kind == "release" else button, Qt.NoModifier))


def test_floating_panel_has_wide_resize_edges(shown):
    from myPGM.ui.docks import CORNER, EDGE
    dock = shown.view.log_dock
    assert all(grip.isHidden() for grip in dock.grips)      # docked: separators resize it
    dock.header.float_button.click()
    _settle(shown.app)
    width, height = dock.width(), dock.height()
    by_edges = {int(grip.edges): grip for grip in dock.grips}
    assert len(by_edges) == 8 and not any(grip.isHidden() for grip in dock.grips)
    right = by_edges[int(Qt.RightEdge)]
    assert right.geometry().getRect() == (width - EDGE, CORNER, EDGE, height - 2 * CORNER)
    assert right.cursor().shape() == Qt.SizeHorCursor
    corner = by_edges[int(Qt.BottomEdge | Qt.RightEdge)]
    assert corner.geometry().getRect() == (width - CORNER, height - CORNER, CORNER, CORNER)
    assert corner.cursor().shape() == Qt.SizeFDiagCursor
    # the grips are on top: the header and the body do not take the edge clicks
    assert dock.childAt(width - 2, height // 2) is right
    assert dock.childAt(2, 2) is by_edges[int(Qt.TopEdge | Qt.LeftEdge)]
    # the header buttons stay clear of the grips
    close = dock.header.close_button
    close_rect = QRect(close.mapTo(dock, QPoint(0, 0)), close.size())
    assert not any(grip.geometry().intersects(close_rect) for grip in dock.grips)
    dock.header.float_button.click()
    _settle(shown.app)
    assert all(grip.isHidden() for grip in dock.grips)


def test_dragging_a_grip_resizes_the_floating_panel(shown, monkeypatch):
    from PyQt5.QtGui import QWindow
    dock = shown.view.plot_dock
    dock.header.float_button.click()
    _settle(shown.app)
    dock.setGeometry(300, 200, 600, 400)
    _settle(shown.app)
    # no window manager resize (macOS with Qt 5): the grip moves the edges itself
    monkeypatch.setattr(QWindow, "startSystemResize", lambda self, edges: False)
    grip = next(g for g in dock.grips if int(g.edges) == int(Qt.BottomEdge | Qt.RightEdge))
    start = grip.mapToGlobal(grip.rect().center())
    _send_mouse(grip, "press", start)
    _send_mouse(grip, "move", start + QPoint(120, 80))
    _send_mouse(grip, "release", start + QPoint(120, 80))
    assert dock.geometry().getRect() == (300, 200, 720, 480)
    # the left edge: the right edge stays, and the panel keeps its minimum size
    grip = next(g for g in dock.grips if int(g.edges) == int(Qt.LeftEdge))
    start = grip.mapToGlobal(grip.rect().center())
    _send_mouse(grip, "press", start)
    _send_mouse(grip, "move", start + QPoint(5000, 0))
    _send_mouse(grip, "release", start + QPoint(5000, 0))
    minimum = dock.minimumSize().expandedTo(dock.minimumSizeHint()).width()
    assert dock.width() == minimum and dock.geometry().right() == 300 + 720 - 1


def test_grip_uses_the_window_manager_resize_when_available(shown, monkeypatch):
    from PyQt5.QtGui import QWindow
    dock = shown.view.plot_dock
    dock.header.float_button.click()
    _settle(shown.app)
    asked = []
    monkeypatch.setattr(QWindow, "startSystemResize",
                        lambda self, edges: asked.append(int(edges)) or True)
    grip = next(g for g in dock.grips if int(g.edges) == int(Qt.TopEdge))
    geometry = dock.geometry()
    start = grip.mapToGlobal(grip.rect().center())
    _send_mouse(grip, "press", start)
    _send_mouse(grip, "move", start + QPoint(0, -50))
    assert asked == [int(Qt.TopEdge)] and dock.geometry() == geometry

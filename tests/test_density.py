"""Density, colours and empty state (DESIGN.md §3, §4b, §5; IMPLEMENTATION_PLAN step 5):
file list rows, pressure log, calibration-coloured selectors, startup state and the
recovery banner."""
import os

import pytest
from PyQt5.QtCore import QMimeData, QUrl

from conftest import dispose
from myPGM import calibrations as C
from myPGM import fit_models as F
from myPGM.ui.FileListViewerWidget import NO_VALUE, ROW_HEIGHT


def _settle(app):
    for _ in range(4):
        app.processEvents()


def _fit(gui, name, model=F.DoubleVoigt):
    fid = gui.file_id(name)
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.fit_mode = model
    gui.presenter.fit_current_file()
    return gui.presenter.model[fid]


def _headers(table):
    return [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]


@pytest.fixture
def empty(qapp):
    """A window at startup: no spectrum, no logged point."""
    from myPGM.ui import theme
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    qapp.setStyleSheet(theme.stylesheet(dark=False))
    view = MainWindow()
    presenter = Presenter(PressureGaugeDataManager(), view)
    presenter._error_dialog = lambda *args, **kwargs: None
    yield view, presenter
    dispose(view)


# --- file list --------------------------------------------------------------------------

def test_file_rows_show_the_fitted_pressure(gui):
    sidebar = gui.view.file_list_widget
    delegate, lookup = sidebar.delegate, gui.presenter.model.get
    ruby = lookup(gui.file_id("Example_Ruby_1.asc"))
    assert delegate.pressure_text(ruby) == NO_VALUE
    assert delegate.tooltip(ruby) == "Example_Ruby_1.asc · Not fitted"
    _fit(gui, "Example_Ruby_1.asc")
    assert delegate.pressure_text(ruby) == f"{ruby.P:.3f}"
    assert delegate.tooltip(ruby) == "Example_Ruby_1.asc · Ruby2020 · Double Voigt"
    assert sidebar.list_widget.sizeHintForRow(0) >= ROW_HEIGHT


# --- pressure log ---------------------------------------------------------------------------

def test_log_shows_p_alone_and_an_optional_sigma_p_column(gui):
    obj = _fit(gui, "Example_Ruby_1.asc")
    gui.view.prompt_fit_pm = lambda current: 8.0
    gui.presenter.add_current_fit_to_table()
    table = gui.view.PvPmTableWindow.table_widget
    headers = _headers(table)
    sigma = headers.index("σP (fit)")
    assert headers.index("P (GPa)") + 1 == sigma
    assert table.item(0, headers.index("P (GPa)")).text() == f"{obj.P:.3f}"
    assert table.isColumnHidden(sigma)
    menu = {a.text(): a for a in table.column_menu().actions()}
    menu["σP (fit)"].setChecked(True)
    assert not table.isColumnHidden(sigma)
    assert table.item(0, sigma).text() == f"{obj.P_err:.3f}"


def test_log_density_and_header(gui):
    from myPGM.ui.PvPmTable import _header_text
    table = gui.view.PvPmTableWindow.table_widget
    table.set_font_size(13)
    assert table.verticalHeader().defaultSectionSize() == 26
    assert _header_text("σP (fit)") == "σP (FIT)" and _header_text("Pm (bar)") == "PM (BAR)"
    assert not table.alternatingRowColors() and not table.showGrid()


def test_current_point_is_highlighted_and_ringed(demo):
    presenter, view, _ = demo
    table, plot = view.PvPmTableWindow.table_widget, view.PvPmPlotWindow
    current = presenter.model[presenter.current_selected_file]
    row = table.current_row()
    assert row is not None
    assert table.item(row, _headers(table).index("file")).text() == current.filename
    xs, ys = plot.current_ring.getData()
    assert list(xs) == [current.Pm] and list(ys) == pytest.approx([current.P])
    # a spectrum that is not in the log: no highlighted row, no ring
    diamond = next(i for i in presenter.ordered_files_to_display
                   if presenter.model[i].filename == "Example_diam_Raman.asc")
    presenter.file_selected_from_file_list(diamond)
    assert table.current_row() is None and len(plot.current_ring.getData()[0]) == 0


# --- calibration-coloured selectors ------------------------------------------------------------

def test_calibration_selector_follows_the_calibration_family(gui):
    toolbox = gui.view.ptoolbox
    assert toolbox.calibration_combo.property("calib") == "ruby"
    toolbox.calibration_combo.setCurrentText(C.SamariumDatchi.name)
    assert toolbox.calibration_combo.property("calib") == "samarium"
    assert 'QComboBox#calibration_combo[calib="samarium"]' in gui.app.styleSheet()


def test_fit_model_selector_is_coloured_by_kind_of_model(gui):
    """Double models red, Single models green, Raman edge grey (as before the
    redesign), whatever the calibration."""
    from myPGM.ui import theme
    combo = gui.view.fit_model_combo
    kinds = {F.DoubleVoigt.name: "double", F.SingleLorentzian.name: "single",
             F.RamanEdge.name: "edge"}
    for name, kind in kinds.items():
        combo.setCurrentText(name)
        assert combo.property("model") == kind
        assert f'QComboBox#fit_model_combo[model="{kind}"]' in gui.app.styleSheet()
    gui.view.ptoolbox.calibration_combo.setCurrentText(C.SamariumDatchi.name)
    # the colour is the model's kind, not the calibration (samarium is not a kind)
    current = gui.presenter.fit_models[combo.currentText()]
    assert combo.property("model") == theme.model_family(current)
    assert combo.styleSheet() == ""
    # list items: a dot in the colour of each kind
    from PyQt5.QtWidgets import QStyleOptionViewItem
    delegate, model = combo.itemDelegate(), combo.model()
    for row in range(combo.count()):
        option = QStyleOptionViewItem()
        delegate.initStyleOption(option, model.index(row, 0))
        assert not option.icon.isNull()
    assert theme.model_color(F.DoubleVoigt) != theme.model_color(F.SingleVoigt)
    assert combo.itemIcon(combo.currentIndex()).isNull()   # closed selector: text only


def test_x_axis_title_follows_the_calibration(gui):
    gui.view.ptoolbox.calibration_combo.setCurrentText(C.H2Vibron.name)
    assert gui.view.data_widget.getAxis("bottom").labelText == "ν (cm⁻¹)"
    assert gui.view.deriv_widget.plotItem.titleLabel.text == "dI/dν"


# --- startup / empty state ----------------------------------------------------------------------

def test_startup_shows_the_empty_state(empty, qapp):
    view, _presenter = empty
    assert view.center_stack.currentWidget() is view.empty_center
    assert view.file_list_widget.list_stack.currentWidget() is view.file_list_widget.empty_box
    table_window = view.PvPmTableWindow
    assert table_window.count_label.text() == "No points"
    assert not table_window.table_widget.empty_label.isHidden()
    plot = view.PvPmPlotWindow
    assert not plot.empty_label.isHidden() and plot.legend_label.isHidden()
    assert not plot.plot_graph.getPlotItem().getAxis("left").isVisible()
    assert view.top_bar.save_status_text() == "Not saved yet"


def test_dropped_files_leave_the_empty_state(empty, resources):
    view, presenter = empty
    view.files_dropped.emit([str(resources / "Example_Ruby_1.asc")])
    assert view.file_list_widget.list_widget.count() == 1
    assert view.center_stack.currentWidget() is not view.empty_center
    assert view.file_list_widget.list_stack.currentWidget() is view.file_list_widget.list_widget


def test_dropped_paths_are_local_files(empty, resources, tmp_path):
    view, _presenter = empty
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(resources / "Example_H2.txt")),
                  QUrl.fromLocalFile(str(tmp_path)),                   # a folder
                  QUrl("https://example.org/spectrum.asc")])
    assert view._dropped_paths(mime) == [str(resources / "Example_H2.txt")]


def test_empty_center_actions(empty, monkeypatch):
    view, presenter = empty
    asked = []
    monkeypatch.setattr(view, "get_file_via_dialog", lambda: asked.append("files"))
    monkeypatch.setattr(view, "select_directory_from_dialog", lambda: asked.append("folder"))
    monkeypatch.setattr(view, "get_open_session_filename_dialog", lambda: asked.append("session"))
    center = view.empty_center
    for widget in (center.add_button, center.folder_button, center.session_button):
        widget.click()
    assert asked == ["files", "folder", "session"]


def test_demo_link_loads_the_demo_session(empty):
    view, presenter = empty
    view.empty_center.demo_button.click()
    assert view.file_list_widget.list_widget.count() == 5
    assert len(presenter.model.table_entries()) == 4
    assert not presenter.has_unsaved_changes()
    assert view.center_stack.currentWidget() is not view.empty_center


def test_empty_glyph_follows_the_calibration(empty):
    from myPGM.ui import theme
    view, _presenter = empty
    view.ptoolbox.calibration_combo.setCurrentText(C.H2Vibron.name)
    assert view.empty_center._color == theme.calib_color(C.H2Vibron)


# --- recovery banner ---------------------------------------------------------------------------

def _backup_dir_with_orphan(tmp_path):
    import json
    folder = tmp_path / "appdata"
    folder.mkdir()
    with open(folder / "autosave_session.json", "w", encoding="utf-8") as f:   # no lock
        json.dump({"files": []}, f)
    return folder


def test_banner_goes_when_something_else_is_loaded(qapp, tmp_path, resources):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    folder = _backup_dir_with_orphan(tmp_path)
    view = MainWindow()
    try:
        presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(folder))
        assert presenter.offer_recovery()
        banner = view.recovery_banner
        assert not banner.isHidden() and "did not close normally" in banner.message.text()
        view.files_dropped.emit([str(resources / "Example_Ruby_1.asc")])
        assert banner.isHidden()
        assert os.path.exists(folder / "autosave_session.discarded.json")   # kept aside
        assert not presenter.offer_recovery()
    finally:
        dispose(view)


def test_banner_buttons(qapp, tmp_path):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    folder = _backup_dir_with_orphan(tmp_path)
    view = MainWindow()
    try:
        presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(folder))
        presenter.offer_recovery()
        view.recovery_banner.recover_button.click()
        assert view.recovery_banner.isHidden()
        assert not os.path.exists(folder / "autosave_session.json")       # recovered
    finally:
        dispose(view)

"""Polish (IMPLEMENTATION_PLAN step 7): λ from the fit, log columns spread over the
table, keyboard focus and navigation, names of icon-only controls."""
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractButton, QCheckBox

from myPGM import fit_models as F


def _settle(app):
    for _ in range(4):
        app.processEvents()


def _fit(gui, name="Example_Ruby_1.asc", model=F.DoubleVoigt):
    fid = gui.file_id(name)
    gui.presenter.file_selected_from_file_list(fid)
    gui.presenter.fit_mode = model
    gui.presenter.fit_current_file()
    return gui.presenter.model[fid]


# --- λ from the fit (DESIGN.md §1, Parameters) ---------------------------------------------

def test_fitted_lambda_has_a_fit_tag(gui):
    toolbox = gui.view.ptoolbox
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    assert not toolbox.x_spinbox.property("fitted") and toolbox.x_fit_tag.isHidden()
    _fit(gui)
    assert toolbox.x_spinbox.property("fitted") and not toolbox.x_fit_tag.isHidden()
    toolbox.x_spinbox.setValue(toolbox.x_spinbox.value() + 0.5)     # typed by the user
    assert not toolbox.x_spinbox.property("fitted")
    _fit(gui)
    toolbox.P_spinbox.setValue(10.0)                    # λ computed from a typed P
    assert not toolbox.x_spinbox.property("fitted")


def test_fit_tag_for_an_edge_and_back_on_reselect(gui):
    toolbox = gui.view.ptoolbox
    _fit(gui)
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_2.asc"))  # not fitted
    assert not toolbox.x_spinbox.property("fitted")
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    assert toolbox.x_spinbox.property("fitted")


# --- pressure log columns -------------------------------------------------------------------

def _column_widths(table):
    """(sum of the shown sections, sum of their content widths, viewport width)."""
    header = table.horizontalHeader()
    shown = [c for c in range(table.columnCount()) if not table.isColumnHidden(c)]
    total = sum(header.sectionSize(c) for c in shown)
    contents = sum(max(header.sectionSizeFromContents(c).width(), table.sizeHintForColumn(c))
                   for c in shown)
    return shown, total, contents, table.viewport().width()


def test_log_columns_fill_the_table_width(gui):
    view = gui.view
    view.resize(1440, 1010)
    view.show()
    _settle(gui.app)
    table = view.PvPmTableWindow.table_widget
    # spread over the table when the contents fit, else as wide as the contents (and the
    # table scrolls); which case applies depends on the platform's default font
    shown, total, contents, viewport = _column_widths(table)
    assert total == max(contents, viewport)             # empty log
    _fit(gui)
    gui.view.prompt_fit_pm = lambda current: 8.0
    gui.presenter.add_current_fit_to_table()
    _settle(gui.app)
    for col in shown:                                   # never narrower than the contents
        assert table.horizontalHeader().sectionSize(col) >= table.sizeHintForColumn(col)
    shown, total, contents, viewport = _column_widths(table)
    assert total == max(contents, viewport)


def test_log_columns_spread_when_they_fit(gui):
    view = gui.view
    view.resize(2400, 1010)                             # wide enough on every platform
    view.show()
    _settle(gui.app)
    table = view.PvPmTableWindow.table_widget
    _, total, contents, viewport = _column_widths(table)
    assert contents < viewport and total == viewport


# --- keyboard -----------------------------------------------------------------------------------

def test_buttons_take_focus_from_the_keyboard_only(gui):
    for b in (gui.view.fit_button, gui.view.top_bar.settings_button, gui.view.CHullBg_button):
        assert b.focusPolicy() == Qt.TabFocus


def test_tab_goes_from_calibration_to_fit_model_to_lambda(gui):
    toolbox = gui.view.ptoolbox
    assert toolbox.calibration_combo.nextInFocusChain() is gui.view.fit_model_combo
    chain = gui.view.fit_model_combo.nextInFocusChain()
    while not chain.focusPolicy() & Qt.TabFocus:        # labels are in the chain too
        chain = chain.nextInFocusChain()
    assert chain is toolbox.x_spinbox or toolbox.x_spinbox.isAncestorOf(chain)


def test_focus_styles_for_borderless_controls(gui):
    sheet = gui.app.styleSheet()
    for selector in ('QPushButton[role="segment"]:focus', 'QPushButton[role="nav"]:focus',
                     'QPushButton[role="link"]:focus', "QCheckBox::indicator:focus"):
        assert selector in sheet


def test_icon_only_controls_have_names(gui):
    view = gui.view
    view.open_settings()
    for root in (view, view.settings_dialog):
        for b in root.findChildren(QAbstractButton):
            if b.objectName().startswith("qt_") or not b.isVisibleTo(root):
                continue
            if not b.text().strip():
                assert b.accessibleName() or b.toolTip(), b
    assert view.Spectro_use_button.accessibleName()
    for check in view.settings_dialog.findChildren(QCheckBox):
        assert check.text() or check.accessibleName()


# --- empty states ------------------------------------------------------------------------

def test_empty_states_paint_their_dashed_border(gui):
    from myPGM.ui.widgets import DashedFrame
    assert isinstance(gui.view.file_list_widget.empty_box, DashedFrame)
    assert isinstance(gui.view.empty_center.drop_zone, DashedFrame)
    # Qt draws QSS dashes as faint dots: no dashed border rule is left
    assert not re.search(r"border[a-z-]*:[^;]*dashed", gui.app.styleSheet())

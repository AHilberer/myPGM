"""Center column (DESIGN.md §1, IMPLEMENTATION_PLAN step 4): fitted pressure card, fit
toolbar, legend row with the dI/dλ toggle, and the "Add point to log" dialog."""
import pytest
from PyQt5.QtCore import Qt

from myPGM import calibrations as C
from myPGM import fit_models as F
from myPGM.ui.center import NO_VALUE


def _settle(app):
    for _ in range(4):
        app.processEvents()


def _select(gui, name):
    fid = gui.file_id(name)
    gui.presenter.file_selected_from_file_list(fid)
    return gui.presenter.model[fid]


def _fit(gui, name, model=F.DoubleVoigt):
    obj = _select(gui, name)
    gui.presenter.fit_mode = model
    gui.presenter.fit_current_file()
    return obj


# --- fitted pressure card ---------------------------------------------------------------

def test_card_before_and_after_a_fit(gui):
    card = gui.view.pressure_card
    _select(gui, "Example_Ruby_1.asc")
    assert card.value_label.text() == NO_VALUE
    assert not gui.view.add_fitted_button.isEnabled()
    assert card.model_pill.isHidden() and card.x_pill.isHidden()
    assert "Ruby2020" in card.calib_pill.text()
    assert gui.view.current_file_label.text() == "Example_Ruby_1.asc"

    obj = _fit(gui, "Example_Ruby_1.asc")
    assert card.value_label.text() == f"{obj.P:.3f}" and "±" not in card.value_label.text()
    assert gui.view.add_fitted_button.isEnabled()
    assert card.model_pill.text() == "Double Voigt"
    assert card.x_pill.text().startswith("λ ") and card.x_pill.text().endswith(" nm")

    _select(gui, "Example_Ruby_2.asc")                     # not fitted: cleared
    assert card.value_label.text() == NO_VALUE and not gui.view.add_fitted_button.isEnabled()


def test_card_pm_field_holds_the_toolbox_pm(gui):
    view = gui.view
    assert view.pressure_card.pm_field.isAncestorOf(view.ptoolbox.Pm_spinbox)
    _fit(gui, "Example_Ruby_1.asc")
    view.ptoolbox.Pm_spinbox.setValue(12.5)
    gui.presenter.add_current_fit_to_table()
    table = gui.presenter.model
    assert [o.Pm for o in table.values() if o.include_in_table] == [12.5]


def test_file_pill_is_elided_but_keeps_the_full_text(gui):
    pill = gui.view.current_file_label
    long_name = "a_very_long_acquisition_name_" * 6 + ".asc"
    pill.setText(long_name)
    assert pill.text() == long_name and pill.toolTip() == long_name
    assert "…" in super(type(pill), pill).text()
    assert pill.sizeHint().width() <= pill.MAX_WIDTH + 40     # + padding


# --- fit toolbar --------------------------------------------------------------------------

def test_fit_range_split_button(gui):
    view = gui.view
    _select(gui, "Example_Ruby_1.asc")
    edit = view.fit_range_edit_button
    assert not edit.isEnabled() and view.legend_row.range_item.isHidden()
    view.fit_range_enable_button.click()
    assert edit.isEnabled() and not view.legend_row.range_item.isHidden()
    edit.click()
    assert edit.isChecked() and view.fit_range_overlay.shown
    assert view.fit_range_overlay.label.textItem.toPlainText().startswith("Drag the edges · ")
    assert view.fit_range_overlay.label.textItem.toPlainText().endswith(" nm")
    view.fit_range_enable_button.click()                   # range off: editing stops
    assert not edit.isEnabled() and not edit.isChecked()
    assert not view.fit_range_overlay.shown


def test_background_segment(gui):
    view = gui.view
    obj = _select(gui, "Example_Ruby_1.asc")
    group = view.bg_segment.group
    assert group.exclusive() and group.checkedButton() is view.ResetBg_button
    view.CHullBg_button.click()
    assert obj.bg is not None and group.checkedButton() is view.CHullBg_button
    view.ResetBg_button.click()
    assert obj.bg is None and group.checkedButton() is view.ResetBg_button

    # Manual: picking, then a second click with no point leaves things as they were
    view.ManualBg_button.click()
    assert view.click_ManualBg_enabled and not view.legend_row.hint.isHidden()
    view.ManualBg_button.click()
    assert not view.click_ManualBg_enabled and view.legend_row.hint.isHidden()
    assert group.checkedButton() is view.ResetBg_button and obj.bg is None


def test_background_kind_is_kept_per_spectrum(gui):
    view = gui.view
    group = view.bg_segment.group
    _select(gui, "Example_Ruby_1.asc")
    view.CHullBg_button.click()
    _select(gui, "Example_Ruby_2.asc")
    assert group.checkedButton() is view.ResetBg_button
    _select(gui, "Example_Ruby_1.asc")
    assert group.checkedButton() is view.CHullBg_button


def test_smoothing_stepper(gui):
    view = gui.view
    obj = _select(gui, "Example_Ruby_1.asc")
    view.smoothing_plus.click()
    view.smoothing_plus.click()
    assert view.smoothing_factor.value() == 3 and obj.current_smoothing == 3
    view.smoothing_minus.click()
    assert view.smoothing_factor.value() == 2
    view.smoothing_factor.setValue(1)
    view.smoothing_minus.click()
    assert view.smoothing_factor.value() == 1               # minimum


def test_derivative_pill(gui):
    view = gui.view
    pane = view.splitter.widget(1)
    assert not view.Derivative_button.isChecked() and pane.isHidden()
    view.Derivative_button.click()
    assert view.Derivative_button.isChecked() and not pane.isHidden()
    view.Derivative_button.click()
    assert not view.Derivative_button.isChecked() and pane.isHidden()


def test_derivative_pill_names_the_x_axis(gui):
    gui.presenter.buffer.set_calibration(C.H2Vibron)
    _fit(gui, "Example_H2.txt", F.SingleLorentzian)
    assert gui.view.Derivative_button.text().strip() == "dI/dν"
    assert gui.view.deriv_widget.plotItem.titleLabel.text == "dI/dν"
    assert not gui.view.deriv_widget.getAxis("left").label.isVisible()


def test_toolbar_keeps_one_line_at_1280(gui):
    view = gui.view
    view.resize(1280, 800)
    view.show()
    _settle(gui.app)
    toolbar = view.fit_toolbar
    assert toolbar.width() >= toolbar.minimumSizeHint().width()
    items = [view.fit_button, view.click_fit_button, view.fit_range_edit_button,
             view.bg_segment, view.smoothing_plus]
    centers = {item.mapTo(toolbar, item.rect().center()).y() for item in items}
    assert max(centers) - min(centers) <= 1
    right = view.smoothing_plus.mapTo(toolbar, view.smoothing_plus.rect().topRight()).x()
    assert right < toolbar.width()


def test_theme_switch_redraws_the_center(gui):
    gui.view.switch_to_dark()
    gui.view.switch_to_light()                     # icons with an on_role are refreshed
    assert gui.view.fit_range_edit_button._theme_icon[3] == "onac"


# --- "Add point to log" --------------------------------------------------------------------

def test_add_point_dialog(qapp):
    from myPGM.ui.dialogs import AddPointDialog
    dialog = AddPointDialog("Ruby2020 · λ 694.280 nm", 24.0)
    try:
        assert dialog.spinbox.value() == 24.0
        assert dialog.add_button.isDefault()
        dialog.spinbox.lineEdit().setText("31,5")          # comma accepted
        assert dialog.value() == 31.5
    finally:
        dialog.deleteLater()


@pytest.mark.parametrize("accepted", [True, False])
def test_add_point_to_log_asks_for_pm(gui, monkeypatch, accepted):
    from myPGM.ui.dialogs import AddPointDialog
    summaries = []

    def answer(self):
        summaries.append(self.summary_label.text())
        self.spinbox.setValue(30.0)
        return int(accepted)
    monkeypatch.setattr(AddPointDialog, "exec_", answer)
    gui.view.PToolbox_toTable_button.click()
    points = [o for o in gui.presenter.model.values() if o.include_in_table]
    assert "GPa" in summaries[0] and summaries[0].startswith(gui.presenter.buffer.calib.name)
    if accepted:
        assert [o.Pm for o in points] == [30.0]
        assert gui.view.ptoolbox.Pm_spinbox.value() == 30.0
    else:
        assert points == []


def test_add_point_button_in_parameters_card(gui):
    view = gui.view
    assert view.ptoolbox.isAncestorOf(view.PToolbox_toTable_button)
    assert view.PToolbox_toTable_button.text().strip() == "Add point to log"
    assert view.add_fitted_button.text().strip() == "Add fit to log"
    assert view.pressure_card.isAncestorOf(view.add_fitted_button)
    assert Qt.AlignRight & view.ptoolbox.Pm_spinbox.alignment()

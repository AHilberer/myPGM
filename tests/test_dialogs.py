"""Popups in the style of the app: messages (instead of QMessageBox), selector lists,
the additional toolbox window and pyqtgraph's menus and export dialog."""
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QWidget


def _messages():
    from myPGM.ui import dialogs
    return dialogs


# --- messages -------------------------------------------------------------------------------

def test_message_buttons_and_choices(gui):
    d = _messages()
    box = d.MessageDialog("Save changes before closing?", "Unsaved.", "question",
                          buttons=(("Discard", "-discard"), ("Cancel", "cancel"), ("Save", "save")),
                          default="save", escape="cancel", parent=gui.view)
    assert box.parent() is gui.view and box.isModal()
    assert box.title() == "Save changes before closing?" and box.text() == "Unsaved."
    save, discard = box.buttons["save"], box.buttons["discard"]
    assert save.property("primary") and save.isDefault() and not discard.property("primary")
    # Discard on the left, apart from Cancel / Save
    box.show()
    assert discard.x() < box.buttons["cancel"].x() < save.x()
    assert box.focusWidget() is save
    discard.click()
    assert box.choice == "discard"
    box.show()
    QTest.keyClick(box, Qt.Key_Escape)
    assert box.choice == "cancel" and not box.isVisible()


def test_message_kinds_use_theme_colours(gui):
    from myPGM.ui import theme
    d = _messages()
    error = d.MessageDialog("The fit failed", "reason", parent=gui.view)
    assert list(error.buttons) == ["ok"] and error.choice == "ok"
    assert theme.qcolor(theme.tokens()["bad"]).name() in error.icon_label.styleSheet()
    assert not error.icon_label.pixmap().isNull()
    question = d.MessageDialog("Save?", kind="question", parent=gui.view)
    assert theme.qcolor(theme.tokens()["info"]).name() in question.icon_label.styleSheet()
    assert not question.text_label.isVisibleTo(question)      # no text: title only


def test_ask_save_changes_maps_the_buttons(gui, monkeypatch):
    # (the gui fixture replaces MainWindow.ask_save_changes, which returns this)
    d = _messages()
    for clicked, expected in (("save", "save"), ("discard", "discard"), ("cancel", "cancel")):
        monkeypatch.setattr(d.MessageDialog, "exec_",
                            lambda self, c=clicked: self.buttons[c].click())
        assert d.ask_save_changes(gui.view) == expected
    monkeypatch.setattr(d.MessageDialog, "exec_", lambda self: self.reject())   # Esc / ×
    assert d.ask_save_changes(gui.view) == "cancel"


def test_no_platform_message_box_left():
    import pathlib
    import myPGM
    root = pathlib.Path(myPGM.__file__).parent
    users = [p.name for p in root.rglob("*.py") if "QMessageBox(" in p.read_text(encoding="utf-8")
             or "QMessageBox." in p.read_text(encoding="utf-8")]
    assert users == []


# --- selector lists -------------------------------------------------------------------------

def test_calibration_list_like_the_fit_model_list(gui):
    from PyQt5.QtGui import QBrush
    from myPGM.ui.widgets import DotItemDelegate
    combo = gui.view.ptoolbox.calibration_combo
    assert isinstance(combo.itemDelegate(), DotItemDelegate)
    assert isinstance(gui.view.fit_model_combo.itemDelegate(), DotItemDelegate)
    assert combo.maxVisibleItems() == combo.count()            # no scrolling
    # neutral rows: the colour is on the selector and in the dots
    item = combo.model().item(0)
    assert item.background() == QBrush() and item.foreground() == QBrush()


# --- additional toolbox window --------------------------------------------------------------

def test_toolbox_window_cards_keep_their_height(gui):
    window = gui.view.additional_toolbox_window
    window.show()
    window.adjustSize()
    natural = window.params_card.height()
    window.resize(window.width(), window.height() + 300)
    gui.app.processEvents()
    assert window.params_card.height() == natural
    assert window.gauge_card.height() == natural               # side by side, same height
    window.hide()


# --- pyqtgraph menu and export dialog ---------------------------------------------------------

def test_plot_axis_menus_are_not_capped(gui):
    menu = gui.view.PvPmPlotWindow.plot_graph.plotItem.vb.menu
    assert all(form.mouseCheck.parentWidget().maximumWidth() > 1000 for form in menu.ctrl)


def test_export_dialog_in_the_app_style(gui):
    plot = gui.view.PvPmPlotWindow
    scene = plot.plot_graph.scene()
    scene.contextMenuItem = plot.plot_graph.plotItem
    scene.contextMenu[0].trigger()                          # right-click menu › Export…
    dialog = scene.exportDialog
    try:
        assert dialog.isVisible() and dialog.objectName() == "ExportDialog"
        assert dialog.windowTitle() == "Export plot"
        assert dialog.ui.exportBtn.property("primary")
        assert dialog.ui.label.text() == "Item to export"
        # the options without pyqtgraph's 'params' heading
        top = dialog.ui.paramTree.invisibleRootItem()
        assert top.childCount() > 0 and top.child(0).text(0) != "params"
        plot.show_export_dialog()                           # shown again: same dialog
        assert scene.exportDialog is dialog
        assert all(isinstance(w, QWidget) for w in dialog.findChildren(QWidget))
    finally:
        dialog.close()


def test_clear_log_asks_first(gui, monkeypatch):
    d = _messages()
    log = gui.view.PvPmTableWindow
    asked = []
    monkeypatch.setattr(d.MessageDialog, "exec_",
                        lambda self: (asked.append(self.title()), self.buttons["cancel"].click()))
    log.clear_table_button.click()                          # empty log: nothing to ask
    assert asked == []
    gui.presenter.add_current_PToolbox_to_table()
    log.clear_table_button.click()                          # Cancel: kept
    assert asked == ["Clear the pressure log?"] and len(gui.presenter.model.table_entries()) == 1
    monkeypatch.setattr(d.MessageDialog, "exec_", lambda self: self.buttons["clear"].click())
    log.clear_table_button.click()
    assert gui.presenter.model.table_entries() == []


def test_top_bar_tooltips_use_the_platform_shortcut_text(gui):
    from PyQt5.QtGui import QKeySequence
    bar = gui.view.top_bar
    assert QKeySequence(QKeySequence.Open).toString(QKeySequence.NativeText) in bar.open_button.toolTip()

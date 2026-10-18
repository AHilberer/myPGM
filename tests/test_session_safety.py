"""Unsaved-changes prompt on close, automatic backup and recovery."""
import json
import os

import pytest

from myPGM import fit_models as F
from conftest import dispose


@pytest.fixture
def app(qapp, tmp_path, monkeypatch):
    """Main window + presenter with the example files and a backup folder.
    app.answers: what the 'Save changes?' question returns, in order."""
    from myPGM.helpers import load_style
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter

    qapp.setStyleSheet(load_style("light-mode.qss"))
    view = MainWindow()
    backup_dir = tmp_path / "appdata"
    backup_dir.mkdir()
    presenter = Presenter(PressureGaugeDataManager(), view, test_mode=True,
                          backup_dir=str(backup_dir))

    class App:
        pass
    a = App()
    a.view, a.presenter, a.asked, a.answers = view, presenter, [], []
    a.backup = backup_dir / "autosave_session.json"
    a.session_file = tmp_path / "saved.json"
    monkeypatch.setattr(view, "ask_save_changes",
                        lambda: a.asked.append("save?") or (a.answers.pop(0) if a.answers else "discard"))
    monkeypatch.setattr(view, "get_save_session_filename_dialog", lambda: str(a.session_file))
    monkeypatch.setattr(view, "get_open_session_filename_dialog", lambda: str(a.session_file))
    presenter._error_dialog = lambda text, title="": a.asked.append(title)

    def fit(name="Example_Ruby_1.asc"):
        fid = next(i for i in presenter.ordered_files_to_display
                   if presenter.model[i].filename == name)
        presenter.file_selected_from_file_list(fid)
        presenter.fit_mode = F.DoubleVoigt
        presenter.fit_current_file()
    a.fit = fit
    yield a
    dispose(view)


# --- unsaved changes -----------------------------------------------------------------------

def test_no_question_when_nothing_changed(app):
    assert not app.presenter.has_unsaved_changes()
    assert app.presenter.confirm_close()
    assert app.asked == []


def test_typing_in_the_toolbox_alone_is_not_unsaved_work(app):
    app.presenter.buffer.set_Pm(12.0)
    app.presenter.buffer.set_x(695.0)
    assert not app.presenter.has_unsaved_changes()


@pytest.mark.parametrize("change", ["fit", "smoothing", "table", "delete"])
def test_changes_are_detected(app, change):
    p = app.presenter
    if change == "fit":
        app.fit()
    elif change == "smoothing":
        p.file_selected_from_file_list(p.ordered_files_to_display[1])
        p.smoothen(5)
    elif change == "table":
        p.add_current_PToolbox_to_table()
    elif change == "delete":
        p.file_selected_from_file_list(p.ordered_files_to_display[0])
        p.delete_current_file()
    assert p.has_unsaved_changes()


def test_cancel_keeps_the_window_open(app):
    app.view.show()
    app.fit()
    app.answers = ["cancel"]
    app.view.close()
    assert app.asked == ["save?"] and app.view.isVisible()


def test_save_writes_the_session_then_closes(app):
    app.fit()
    app.answers = ["save"]
    assert app.presenter.confirm_close()
    saved = json.loads(app.session_file.read_text(encoding="utf-8"))
    assert any(f["fit_result"] is not None for f in saved["files"])


def test_cancelling_the_save_dialog_keeps_the_window_open(app, monkeypatch):
    app.fit()
    app.answers = ["save"]
    monkeypatch.setattr(app.view, "get_save_session_filename_dialog", lambda: None)
    assert not app.presenter.confirm_close()


def test_discard_closes_without_saving(app):
    app.fit()
    app.answers = ["discard"]
    assert app.presenter.confirm_close()
    assert not app.session_file.exists()


def test_saving_or_loading_clears_unsaved_changes(app):
    app.fit()
    assert app.presenter.save_session()
    assert not app.presenter.has_unsaved_changes()
    app.fit("Example_Ruby_2.asc")
    assert app.presenter.has_unsaved_changes()
    assert app.presenter.load_session()
    assert not app.presenter.has_unsaved_changes()


def test_demo_session_starts_without_unsaved_changes(demo):
    presenter, _view, _ = demo
    assert not presenter.has_unsaved_changes()


# --- automatic backup ------------------------------------------------------------------------

def test_backup_written_only_when_there_are_unsaved_changes(app):
    assert app.presenter.autosave_timer.interval() == 30_000
    app.presenter.autosave()
    app.presenter.flush_backup()
    assert not app.backup.exists()
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    backup = json.loads(app.backup.read_text(encoding="utf-8"))
    assert any(f["fit_result"] is not None for f in backup["files"])


def test_backup_removed_after_save_and_after_normal_close(app):
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    assert app.backup.exists()
    app.presenter.save_session()
    assert not app.backup.exists()
    app.fit("Example_Ruby_2.asc")
    app.presenter.autosave()
    app.presenter.flush_backup()
    app.answers = ["discard"]
    assert app.presenter.confirm_close()
    assert not app.backup.exists()


def test_no_backup_folder_means_no_backup(gui):
    assert gui.presenter.backup_path is None and gui.presenter.autosave_timer is None
    gui.presenter.autosave()                       # no error


# --- recovery ---------------------------------------------------------------------------------

def _crashed_session(app):
    """Unsaved work backed up, then the app 'crashes' (no normal close)."""
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    return app.presenter.model[app.presenter.current_selected_file].P


def _new_app(app, qapp, answer):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    view = MainWindow()
    view.ask_recover_session = lambda when: answer
    presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(app.backup.parent))
    presenter._error_dialog = lambda *args: None
    return view, presenter


def test_recover_backup_at_next_start(app, qapp):
    P = _crashed_session(app)
    view, presenter = _new_app(app, qapp, answer=True)
    assert presenter.offer_recovery()
    fitted = [o for o in presenter.model.values() if o.fit_result is not None]
    assert len(presenter.model) == 5 and fitted[0].P == pytest.approx(P)
    assert presenter.has_unsaved_changes()          # recovered work still has to be saved
    dispose(view)


def test_declined_backup_is_kept_aside(app, qapp):
    _crashed_session(app)
    view, presenter = _new_app(app, qapp, answer=False)
    assert not presenter.offer_recovery()
    assert len(presenter.model) == 0
    assert not app.backup.exists()
    assert (app.backup.parent / "autosave_session.discarded.json").exists()
    assert not presenter.offer_recovery()           # not offered twice
    dispose(view)

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
    a.backup_dir = backup_dir
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
    assert not os.path.exists(app.presenter.backup_path)
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    backup = json.loads(open(app.presenter.backup_path, encoding="utf-8").read())
    assert any(f["fit_result"] is not None for f in backup["files"])


def test_backup_removed_after_save_and_after_normal_close(app):
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    assert os.path.exists(app.presenter.backup_path)
    app.presenter.save_session()
    assert not os.path.exists(app.presenter.backup_path)
    app.fit("Example_Ruby_2.asc")
    app.presenter.autosave()
    app.presenter.flush_backup()
    app.answers = ["discard"]
    assert app.presenter.confirm_close()
    assert not os.path.exists(app.presenter.backup_path)


def test_no_backup_folder_means_no_backup(gui):
    assert gui.presenter.backup_path is None and gui.presenter.autosave_timer is None
    gui.presenter.autosave()                       # no error


# --- recovery ---------------------------------------------------------------------------------

def _crashed_session(app):
    """Unsaved work backed up, then the window 'crashes': no normal close, so the
    backup stays on disk and its lock is no longer held."""
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    app.presenter._backup_lock.unlock()
    return app.presenter.model[app.presenter.current_selected_file].P


def _new_app(app, answer):
    from myPGM.ui.main_ui import MainWindow
    from myPGM.data_model import PressureGaugeDataManager
    from myPGM.presenter import Presenter
    view = MainWindow()
    asked = []
    view.ask_recover_session = lambda when: asked.append(when) or answer
    presenter = Presenter(PressureGaugeDataManager(), view, backup_dir=str(app.backup_dir))
    presenter._error_dialog = lambda *args: None
    return view, presenter, asked


def test_each_window_has_its_own_locked_backup(app):
    path = app.presenter.backup_path
    assert os.path.basename(path).startswith("autosave_session_") and path.endswith(".json")
    assert os.path.exists(os.path.splitext(path)[0] + ".lock")


def test_recover_backup_at_next_start(app):
    P = _crashed_session(app)
    crashed_backup = app.presenter.backup_path
    view, presenter, asked = _new_app(app, answer=True)
    assert presenter.offer_recovery() and len(asked) == 1
    fitted = [o for o in presenter.model.values() if o.fit_result is not None]
    assert len(presenter.model) == 5 and fitted[0].P == pytest.approx(P)
    assert presenter.has_unsaved_changes()          # recovered work still has to be saved
    assert not os.path.exists(crashed_backup)       # now backed up by the new window
    dispose(view)


def test_declined_backup_is_kept_aside(app):
    _crashed_session(app)
    crashed_backup = app.presenter.backup_path
    view, presenter, _ = _new_app(app, answer=False)
    assert not presenter.offer_recovery()
    assert len(presenter.model) == 0
    assert not os.path.exists(crashed_backup)
    assert os.path.exists(os.path.splitext(crashed_backup)[0] + ".discarded.json")
    assert not presenter.offer_recovery()           # not offered twice
    dispose(view)


def test_backup_of_a_window_still_open_is_left_alone(app):
    # first window: unsaved work backed up, and still open (lock held)
    app.fit()
    app.presenter.autosave()
    app.presenter.flush_backup()
    view, presenter, asked = _new_app(app, answer=True)
    assert not presenter.offer_recovery() and asked == []
    assert os.path.exists(app.presenter.backup_path)
    # closing the second window does not touch the first window's backup
    assert presenter.confirm_close()
    assert os.path.exists(app.presenter.backup_path)
    dispose(view)


def test_stale_lock_of_a_crashed_process_is_detected(app):
    # a backup and a lock file left by a process that no longer exists
    base = os.path.join(str(app.backup_dir), "autosave_session_999999_1")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"files": []}, f)
    import socket
    with open(base + ".lock", "w") as f:
        f.write(f"999999\npython3\n{socket.gethostname()}\n")
    view, presenter, asked = _new_app(app, answer=False)
    assert presenter._orphan_backups() == [base + ".json"]
    dispose(view)


def test_backup_from_the_previous_version_is_offered(app):
    legacy = os.path.join(str(app.backup_dir), "autosave_session.json")   # no lock file
    with open(legacy, "w", encoding="utf-8") as f:
        json.dump({"files": []}, f)
    view, presenter, asked = _new_app(app, answer=False)
    assert presenter.offer_recovery() is False and len(asked) == 1
    assert os.path.exists(os.path.join(str(app.backup_dir), "autosave_session.discarded.json"))
    dispose(view)

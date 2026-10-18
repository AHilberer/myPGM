import logging
import sys
from logging.handlers import RotatingFileHandler

import pytest

from myPGM import log_setup


@pytest.fixture
def clean_logger():
    """Restore the 'myPGM' logger after each test (setup_logging changes it)."""
    logger = logging.getLogger("myPGM")
    saved = (list(logger.handlers), logger.level, logger.propagate, log_setup.log_file_path)
    yield logger
    for handler in list(logger.handlers):
        if handler not in saved[0]:
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(saved[1])
    logger.propagate = saved[2]
    log_setup.log_file_path = saved[3]


def _read(path):
    for handler in logging.getLogger("myPGM").handlers:
        handler.flush()
    return path.read_text(encoding="utf-8")


def test_log_file_created_in_given_folder(clean_logger, tmp_path):
    path = log_setup.setup_logging(log_dir=tmp_path / "logs")
    assert path == tmp_path / "logs" / "mypgm.log" == log_setup.log_file_path
    logging.getLogger("myPGM.presenter").warning("something went wrong")
    text = _read(path)
    assert "WARNING myPGM.presenter: something went wrong" in text


def test_debug_messages_only_in_debug_mode(clean_logger, tmp_path):
    path = log_setup.setup_logging(log_dir=tmp_path)
    logging.getLogger("myPGM.presenter").debug("detail 1")
    assert "detail 1" not in _read(path)
    log_setup.setup_logging(debug=True, log_dir=tmp_path)
    logging.getLogger("myPGM.presenter").debug("detail 2")
    assert "detail 2" in _read(path)


def test_setup_twice_does_not_duplicate_messages(clean_logger, tmp_path):
    log_setup.setup_logging(log_dir=tmp_path)
    path = log_setup.setup_logging(log_dir=tmp_path)
    ours = [h for h in clean_logger.handlers if getattr(h, "_mypgm", False)]
    assert len(ours) == 2          # terminal + file
    logging.getLogger("myPGM").info("once")
    assert _read(path).count("once") == 1


def test_log_file_rotates(clean_logger, tmp_path):
    log_setup.setup_logging(log_dir=tmp_path)
    file_handler = next(h for h in clean_logger.handlers if isinstance(h, RotatingFileHandler))
    assert file_handler.maxBytes == 1_000_000 and file_handler.backupCount == 3


def test_unusable_log_folder_falls_back_to_terminal(clean_logger, tmp_path):
    not_a_folder = tmp_path / "file.txt"
    not_a_folder.write_text("x")
    assert log_setup.setup_logging(log_dir=not_a_folder) is None
    assert log_setup.log_file_path is None
    assert not any(isinstance(h, RotatingFileHandler) for h in clean_logger.handlers)


def test_default_log_folder_is_per_user_app_data(qapp):
    folder = log_setup.default_log_dir()
    assert folder is not None and folder.is_absolute()
    assert "myPGM" in str(folder) or qapp.applicationName() in str(folder)


# --- what the app logs -------------------------------------------------------------------

def test_errors_shown_to_the_user_are_logged(gui, tmp_path, caplog):
    bad = tmp_path / "bad.asc"
    bad.write_text("hello\n")
    with caplog.at_level(logging.WARNING, logger="myPGM"):
        gui.presenter._add_files([str(bad)])
    assert gui.errors == ["File load error"]
    assert any("File load error" in r.getMessage() and "bad.asc" in r.getMessage()
               for r in caplog.records)


@pytest.mark.filterwarnings("ignore:divide by zero:RuntimeWarning")
def test_fit_failure_is_logged_with_reason(gui, caplog):
    gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
    gui.presenter.buffer.x0 = 0               # makes the pressure calculation fail
    with caplog.at_level(logging.WARNING, logger="myPGM"):
        gui.presenter.fit_current_file()
    assert gui.errors == ["Fit error"]
    assert any(r.getMessage().startswith("Fit error: Example_Ruby_1.asc") for r in caplog.records)


def test_debug_messages_for_fits_and_sessions(gui, tmp_path, caplog, monkeypatch):
    session = tmp_path / "s.json"
    monkeypatch.setattr(gui.view, "get_save_session_filename_dialog", lambda: str(session))
    monkeypatch.setattr(gui.view, "get_open_session_filename_dialog", lambda: str(session))
    with caplog.at_level(logging.DEBUG, logger="myPGM"):
        gui.presenter.file_selected_from_file_list(gui.file_id("Example_Ruby_1.asc"))
        gui.presenter.fit_current_file()
        gui.presenter.save_session()
        gui.presenter.load_session()
    messages = [r.getMessage() for r in caplog.records]
    assert any(m.startswith("Fitted Example_Ruby_1.asc with Double Voigt, Ruby2020") for m in messages)
    assert any(m.startswith("Session saved to") for m in messages)
    assert any(m.startswith("Session loaded from") for m in messages)


def test_loaded_files_are_logged_in_debug_mode(gui, resources, caplog):
    with caplog.at_level(logging.DEBUG, logger="myPGM"):
        gui.presenter._add_files([str(resources / "Example_Ruby_2.asc")])
    assert any(r.getMessage().startswith("Loaded ") and "Example_Ruby_2.asc (1024 points)" in r.getMessage()
               for r in caplog.records)


def test_unexpected_error_dialog_points_to_log_file(qapp, clean_logger, tmp_path, monkeypatch):
    import myPGM
    from PyQt5.QtWidgets import QMessageBox
    log_setup.setup_logging(log_dir=tmp_path)
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: shown.append(text))
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)   # restored after the test
    myPGM._install_excepthook()
    try:
        raise ValueError("boom")
    except ValueError:
        sys.excepthook(*sys.exc_info())
    assert "ValueError: boom" in shown[0] and str(tmp_path / "mypgm.log") in shown[0]
    assert "Traceback" in _read(tmp_path / "mypgm.log")


def test_repeated_error_shows_one_dialog(qapp, clean_logger, tmp_path, monkeypatch, caplog):
    import myPGM
    from PyQt5.QtWidgets import QMessageBox
    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: shown.append(text))
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)   # restored after the test
    clock = [1000.0]
    monkeypatch.setattr(myPGM.time, "monotonic", lambda: clock[0])
    myPGM._install_excepthook()

    def raise_(exc):
        try:
            raise exc
        except Exception:
            sys.excepthook(*sys.exc_info())

    with caplog.at_level(logging.ERROR, logger="myPGM"):
        for _ in range(6):
            raise_(TypeError("same error"))
        assert len(shown) == 1                                   # not 6 dialogs
        assert "repeated (5 times" in caplog.records[-1].getMessage()
        raise_(ValueError("another error"))                      # a different error is shown
        assert len(shown) == 2
        clock[0] += myPGM.REPEATED_ERROR_WINDOW_S + 1            # much later: shown again
        raise_(TypeError("same error"))
        assert len(shown) == 3


def test_errors_raised_while_the_dialog_is_open_are_only_logged(qapp, clean_logger, monkeypatch):
    import myPGM
    from PyQt5.QtWidgets import QMessageBox
    shown = []

    def critical(parent, title, text):
        shown.append(text)
        if len(shown) == 1:                                       # error while the dialog is open
            try:
                raise KeyError("during dialog")
            except KeyError:
                sys.excepthook(*sys.exc_info())

    monkeypatch.setattr(QMessageBox, "critical", critical)
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    myPGM._install_excepthook()
    try:
        raise TypeError("first")
    except TypeError:
        sys.excepthook(*sys.exc_info())
    assert len(shown) == 1

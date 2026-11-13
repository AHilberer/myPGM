"""Per-user settings kept between launches: theme, font size and the folders
last used in file dialogs.

They are stored in an INI file in the user's configuration folder:
~/.config/myPGM/myPGM.ini on Linux and macOS, %APPDATA%\\myPGM\\myPGM.ini on
Windows. The reference positions (x0) are not kept on purpose: they are
measured for each experiment, and a value from a previous one would silently
give wrong pressures.
"""
from pathlib import Path

from PyQt5.QtCore import QSettings


def app_settings():
    # explicit organisation and application names: setting the QApplication
    # organisation instead would move the log and backup folder
    return QSettings(QSettings.IniFormat, QSettings.UserScope, "myPGM", "myPGM")


def last_dir(kind):
    """Folder last used for this kind of file ('' if none, or if it is gone)."""
    folder = app_settings().value(f"folders/{kind}", "", type=str)
    return folder if folder and Path(folder).is_dir() else ""


def remember_dir(kind, path):
    """Remember the folder of path (a file or a folder) for the next dialog."""
    if path:
        path = Path(path)
        app_settings().setValue(f"folders/{kind}", str(path if path.is_dir() else path.parent))

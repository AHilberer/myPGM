"""Per-user settings kept between launches: the Settings window values (theme, font
size, autosave, visible log columns...), the window layout and the folders
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


# --- values of the Settings window (DESIGN.md §4) -------------------------------------------

THEMES = ("light", "dark", "system")
FONT_SIZE_RANGE = (8, 30)
AUTOSAVE_MIN_S = 5
AUTOSAVE_MAX_S = 24 * 3600

DEFAULTS = {
    "theme": "light",
    "font_size": 13,                    # px (DESIGN.md §2, 13 px base)
    "additional_toolbox": False,
    "session/autosave": True,
    "session/autosave_interval_s": 30,
    "session/offer_recovery": True,
    "logging/debug": False,
}


def setting(key):
    """Stored value of a Settings window entry (its default if not set, or invalid)."""
    default = DEFAULTS[key]
    value = app_settings().value(key, default, type=type(default))
    if key == "theme" and value not in THEMES:
        return default
    if key == "font_size" and not FONT_SIZE_RANGE[0] <= value <= FONT_SIZE_RANGE[1]:
        return default
    if key == "session/autosave_interval_s":
        return min(max(value, AUTOSAVE_MIN_S), AUTOSAVE_MAX_S)
    return value


def set_setting(key, value):
    app_settings().setValue(key, value)


def column_visibility():
    """Pressure log columns shown or hidden by the user: {key: bool}. Columns the user
    never chose are not listed (they keep their default, see PvPmTable.COLUMNS)."""
    settings = app_settings()
    settings.beginGroup("log_columns")
    stored = {key: settings.value(key, type=bool) for key in settings.childKeys()}
    settings.endGroup()
    return stored


def set_column_visibility(key, visible):
    app_settings().setValue(f"log_columns/{key}", bool(visible))

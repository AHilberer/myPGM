"""Settings window (DESIGN.md §4): a section list on the left,
the section on the right, Restore defaults / Cancel / Save at the bottom.

The window only edits values: set_values() fills it, `saved` gives the edited values
when Save is clicked, and the main window applies and stores them. Cancel (or Esc)
discards the edits."""
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from myPGM import settings as S
from myPGM.ui import icons, theme
from myPGM.ui.center import Segmented, Stepper
from myPGM.ui.widgets import Button, button, divider, label

SOURCE_URL = "https://github.com/AHilberer/myPGM"
ISSUES_URL = "https://github.com/AHilberer/myPGM/issues"
SECTIONS = ("General", "Session", "Pressure log", "Logging", "About")
NAV_WIDTH = 188


def _row(title, description, control, line=True):
    """Title (medium) and muted description on the left, control on the right, a 1 px
    line under it."""
    row = QVBoxLayout()
    row.setSpacing(14)
    content = QHBoxLayout()
    content.setSpacing(16)
    text = QVBoxLayout()
    text.setSpacing(2)
    text.addWidget(label(title, "row-title"))
    note = label(description, "muted-12")
    note.setWordWrap(True)
    text.addWidget(note)
    content.addLayout(text, 1)
    if isinstance(control, QWidget):
        if not control.accessibleName():
            control.setAccessibleName(title)        # check boxes have no text of their own
        content.addWidget(control, 0, Qt.AlignVCenter)
    else:
        content.addLayout(control)
    row.addLayout(content)
    if line:
        row.addWidget(divider(vertical=False))
    return row


def _check():
    box = QCheckBox()
    box.setCursor(Qt.PointingHandCursor)
    return box


class SettingsDialog(QDialog):
    """Non-modal, one instance per main window (MainWindow.open_settings)."""

    saved = pyqtSignal(dict)

    def __init__(self, columns, parent=None):
        """columns: (key, label, shown by default) of the pressure log's optional
        columns, in table order."""
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Settings")
        self.setModal(False)
        self.resize(820, 600)
        self.setMinimumSize(640, 440)
        self.columns = list(columns)
        self.log_dir = None                 # set by the main window (Open log folder)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._nav())
        self.stack = QStackedWidget()
        for build in (self._general_page, self._session_page, self._log_page,
                      self._logging_page, self._about_page):
            self.stack.addWidget(self._page(build()))
        body.addWidget(self.stack, 1)
        layout.addLayout(body, 1)
        layout.addWidget(self._footer())

        self.show_section("General")
        self.restyle()

    # --- frame ------------------------------------------------------------------------------

    def _header(self):
        header = QFrame()
        header.setObjectName("SettingsHeader")
        header.setAttribute(Qt.WA_StyledBackground, True)
        header.setFixedHeight(52)
        row = QHBoxLayout(header)
        row.setContentsMargins(18, 0, 18, 0)
        row.setSpacing(10)
        self.header_icon = QLabel()
        title = QLabel("Settings")
        title.setObjectName("SettingsTitle")
        row.addWidget(self.header_icon)
        row.addWidget(title)
        row.addWidget(label("myPGM", "muted-12"))
        row.addStretch(1)
        return header

    def _nav(self):
        nav = QFrame()
        nav.setObjectName("SettingsNav")
        nav.setAttribute(Qt.WA_StyledBackground, True)
        nav.setFixedWidth(NAV_WIDTH)
        column = QVBoxLayout(nav)
        column.setContentsMargins(10, 12, 10, 12)
        column.setSpacing(2)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = {}
        for index, name in enumerate(SECTIONS):
            entry = Button(name, 34)
            entry.setProperty("role", "nav")
            entry.setCheckable(True)
            entry.setCursor(Qt.PointingHandCursor)
            entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            entry.clicked.connect(lambda _checked, name=name: self.show_section(name))
            self.nav_group.addButton(entry, index)
            self.nav_buttons[name] = entry
            column.addWidget(entry)
        column.addStretch(1)
        return nav

    def _footer(self):
        footer = QFrame()
        footer.setObjectName("SettingsFooter")
        footer.setAttribute(Qt.WA_StyledBackground, True)
        row = QHBoxLayout(footer)
        row.setContentsMargins(18, 12, 18, 12)
        row.setSpacing(8)
        self.restore_button = button("Restore defaults", 34, role="text",
                                     tooltip="Default values in every section (not saved yet)")
        self.cancel_button = button("Cancel", 34)
        self.save_button = button("Save", 34, primary=True)
        self.save_button.setDefault(True)
        self.save_button.setAutoDefault(True)
        self.cancel_button.setAutoDefault(False)
        self.restore_button.setAutoDefault(False)
        row.addWidget(self.restore_button)
        row.addStretch(1)
        row.addWidget(self.cancel_button)
        row.addWidget(self.save_button)
        self.restore_button.clicked.connect(self.restore_defaults)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._save)
        return footer

    @staticmethod
    def _page(content):
        """Section content (20 × 24 px padding), scrolled if the window is small."""
        scroll = QScrollArea()
        scroll.setObjectName("SettingsPage")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _section(title):
        content = QWidget()
        content.setObjectName("SettingsContent")
        column = QVBoxLayout(content)
        column.setContentsMargins(24, 20, 24, 20)
        column.setSpacing(18)
        column.addWidget(label(title, "settings-title"))
        return content, column

    # --- sections ------------------------------------------------------------------------------

    def _general_page(self):
        content, column = self._section("General")
        self.theme_buttons = {mode: Button(mode.capitalize(), 30) for mode in S.THEMES}
        self.theme_segment = Segmented(list(self.theme_buttons.values()))
        column.addLayout(_row("Theme", "Same as the toggle in the top bar.", self.theme_segment))

        low, high = S.FONT_SIZE_RANGE
        self.font_spin = QSpinBox()
        self.font_spin.setRange(low, high)
        self.font_spin.setSuffix(" px")
        self.font_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.font_spin.setAccessibleName("Interface font size")
        self.font_minus = Button("−", 32, 30)
        self.font_minus.setToolTip("Smaller")
        self.font_plus = Button("+", 32, 30)
        self.font_plus.setToolTip("Larger")
        stepper = Stepper(self.font_spin, self.font_minus, self.font_plus)
        self.font_spin.setFixedWidth(64)
        column.addLayout(_row("Interface font size", "Text and plot labels.", stepper))

        self.toolbox_check = _check()
        column.addLayout(_row("Additional pressure toolbox",
                              "Shows a second pressure toolbox window.",
                              self.toolbox_check, line=False))
        column.addStretch(1)
        return content

    def _session_page(self):
        content, column = self._section("Session")
        self.autosave_check = _check()
        column.addLayout(_row("Autosave", "Keeps a recovery copy of the session while you work.",
                              self.autosave_check))

        self.interval_spin = QSpinBox()
        self.interval_spin.setObjectName("IntervalSpin")
        self.interval_spin.setButtonSymbols(QSpinBox.NoButtons)
        self.interval_spin.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.interval_spin.setFixedSize(72, 34)
        self.interval_spin.setAccessibleName("Autosave interval")
        self.interval_unit = QComboBox()
        self.interval_unit.addItems(["seconds", "minutes"])
        self.interval_unit.setFixedHeight(34)
        self.interval_unit.setMinimumWidth(112)
        self.interval_unit.setAccessibleName("Autosave interval unit")
        self._unit_index = 0
        self.interval_unit.currentIndexChanged.connect(self._convert_interval)
        self._set_interval_range()
        interval = QHBoxLayout()
        interval.setSpacing(8)
        interval.addWidget(self.interval_spin)
        interval.addWidget(self.interval_unit)
        column.addLayout(_row("Autosave every",
                              f"Default {S.DEFAULTS['session/autosave_interval_s']} s. "
                              "Shorter is safer, longer writes less often.", interval))
        self.autosave_check.toggled.connect(self._update_interval_enabled)

        self.recovery_check = _check()
        column.addLayout(_row("Offer to recover an unsaved session at startup",
                              "After a crash or a forced quit.", self.recovery_check, line=False))
        column.addStretch(1)
        return content

    def _log_page(self):
        content, column = self._section("Pressure log")
        note = label("Columns shown in the table and written to the CSV export. "
                     "Same choices as right-clicking the table header.", "muted-12")
        note.setWordWrap(True)
        column.addWidget(note)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        self.column_checks = {}
        for index, (key, text, _shown) in enumerate(self.columns):
            tile = QFrame()
            tile.setObjectName("ColumnTile")
            tile.setAttribute(Qt.WA_StyledBackground, True)
            tile.setFixedHeight(32)
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(10, 0, 10, 0)
            check = QCheckBox(text)
            check.setCursor(Qt.PointingHandCursor)
            check.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            tile_layout.addWidget(check)
            self.column_checks[key] = check
            grid.addWidget(tile, index // 3, index % 3)
        for col in range(3):
            grid.setColumnStretch(col, 1)
        column.addLayout(grid)
        column.addStretch(1)
        return content

    def _logging_page(self):
        content, column = self._section("Logging")
        self.debug_check = _check()
        column.addLayout(_row("Debug logging",
                              "More detail in the log file, useful when reporting an issue.",
                              self.debug_check))
        self.log_folder_button = button("Open log folder", 32)
        self.log_folder_button.clicked.connect(self.open_log_folder)
        column.addLayout(_row("Log folder", "Where myPGM writes its log files.",
                              self.log_folder_button, line=False))
        column.addStretch(1)
        return content

    def _about_page(self):
        content, column = self._section("About")
        identity = QHBoxLayout()
        identity.setSpacing(14)
        self.about_mark = QLabel()
        identity.addWidget(self.about_mark)
        names = QVBoxLayout()
        names.setSpacing(2)
        self.about_name = QLabel()
        self.about_name.setObjectName("AboutName")
        self.about_name.setTextFormat(Qt.RichText)
        names.addWidget(self.about_name)
        names.addWidget(label("Pressure Gauge Monitor for high-pressure experiments", "muted-12"))
        identity.addLayout(names, 1)
        column.addLayout(identity)
        self.source_button = button("Source on GitHub", 32, tooltip=SOURCE_URL)
        self.issue_button = button("Report an issue", 32, tooltip=ISSUES_URL)
        self.source_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SOURCE_URL)))
        self.issue_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ISSUES_URL)))
        links = QHBoxLayout()
        links.setSpacing(8)
        links.addWidget(self.source_button)
        links.addWidget(self.issue_button)
        links.addStretch(1)
        column.addLayout(links)
        column.addStretch(1)
        self.set_version("dev")
        return content

    # --- navigation ---------------------------------------------------------------------------

    def show_section(self, name):
        index = SECTIONS.index(name)
        self.stack.setCurrentIndex(index)
        for entry_name, entry in self.nav_buttons.items():
            current = entry_name == name
            entry.setChecked(current)
            # weight 600 for the current section (QSS cannot change the font on :checked)
            entry.setProperty("current", current)
            entry.style().unpolish(entry)
            entry.style().polish(entry)

    def current_section(self):
        return SECTIONS[self.stack.currentIndex()]

    # --- autosave interval -----------------------------------------------------------------------

    def _minutes(self):
        return self.interval_unit.currentIndex() == 1

    def _set_interval_range(self):
        if self._minutes():
            self.interval_spin.setRange(1, S.AUTOSAVE_MAX_S // 60)
        else:
            self.interval_spin.setRange(S.AUTOSAVE_MIN_S, S.AUTOSAVE_MAX_S)

    def _convert_interval(self, index):
        """Same interval in the other unit (rounded to whole minutes)."""
        seconds = self.interval_spin.value() * (60 if self._unit_index == 1 else 1)
        self._unit_index = index
        self._set_interval_range()
        self.interval_spin.setValue(max(1, round(seconds / 60)) if index == 1 else seconds)

    def interval_seconds(self):
        seconds = self.interval_spin.value() * (60 if self._minutes() else 1)
        return min(max(seconds, S.AUTOSAVE_MIN_S), S.AUTOSAVE_MAX_S)

    def set_interval_seconds(self, seconds):
        minutes = seconds >= 60 and seconds % 60 == 0
        self.interval_unit.blockSignals(True)
        self.interval_unit.setCurrentIndex(1 if minutes else 0)
        self.interval_unit.blockSignals(False)
        self._unit_index = self.interval_unit.currentIndex()
        self._set_interval_range()
        self.interval_spin.setValue(seconds // 60 if minutes else seconds)

    def _update_interval_enabled(self, enabled):
        self.interval_spin.setEnabled(enabled)
        self.interval_unit.setEnabled(enabled)

    # --- values ------------------------------------------------------------------------------

    @staticmethod
    def default_values(columns):
        return {
            "theme": S.DEFAULTS["theme"],
            "font_size": S.DEFAULTS["font_size"],
            "additional_toolbox": S.DEFAULTS["additional_toolbox"],
            "autosave": S.DEFAULTS["session/autosave"],
            "autosave_interval_s": S.DEFAULTS["session/autosave_interval_s"],
            "offer_recovery": S.DEFAULTS["session/offer_recovery"],
            "columns": {key: shown for key, _text, shown in columns},
            "debug": S.DEFAULTS["logging/debug"],
        }

    def set_values(self, values):
        self.theme_segment.check(self.theme_buttons[values["theme"]])
        self.font_spin.setValue(values["font_size"])
        self.toolbox_check.setChecked(values["additional_toolbox"])
        self.autosave_check.setChecked(values["autosave"])
        self.set_interval_seconds(values["autosave_interval_s"])
        self._update_interval_enabled(values["autosave"])
        self.recovery_check.setChecked(values["offer_recovery"])
        for key, check in self.column_checks.items():
            check.setChecked(values["columns"].get(key, False))
        self.debug_check.setChecked(values["debug"])

    def values(self):
        checked = self.theme_segment.group.checkedButton()
        theme_mode = next((mode for mode, b in self.theme_buttons.items() if b is checked),
                          S.DEFAULTS["theme"])
        return {
            "theme": theme_mode,
            "font_size": self.font_spin.value(),
            "additional_toolbox": self.toolbox_check.isChecked(),
            "autosave": self.autosave_check.isChecked(),
            "autosave_interval_s": self.interval_seconds(),
            "offer_recovery": self.recovery_check.isChecked(),
            "columns": {key: check.isChecked() for key, check in self.column_checks.items()},
            "debug": self.debug_check.isChecked(),
        }

    def set_theme_mode(self, mode):
        """The top-bar toggle changed the theme while the window is open."""
        self.theme_segment.check(self.theme_buttons[mode])

    def restore_defaults(self):
        """Default values in every section; nothing is applied before Save."""
        self.set_values(self.default_values(self.columns))

    def _save(self):
        self.saved.emit(self.values())
        self.accept()

    # --- other -------------------------------------------------------------------------------

    def set_version(self, version):
        self.about_name.setText(
            f'myPGM <span style="font-family:\'{theme.mono_family()}\'; font-weight:{theme.qt5_weight(500)}; '
            f'color:{theme.qcolor(theme.tokens()["mu"]).name()}">v{version}</span>')
        self._version = version

    def open_log_folder(self):
        if self.log_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.log_dir)))

    def restyle(self):
        muted = theme.qcolor(theme.tokens()["mu"]).name()
        self.header_icon.setPixmap(icons.pixmap("settings", muted, 18))
        self.about_mark.setPixmap(icons.app_mark(44))
        self.set_version(getattr(self, "_version", "dev"))

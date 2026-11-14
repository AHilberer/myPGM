"""Top bar of the main window (DESIGN.md §1.1): app mark and name, session name and
save status on the left; panel toggles, Open / Save / Export CSV, the theme toggle and
the Settings button on the right."""
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from myPGM.ui import icons, theme
from myPGM.ui.widgets import Collapser, ElidedLabel, button, divider, icon_button, label

HEIGHT = 48


def _shortcut_text(key):
    """The platform's text for a standard shortcut: ⌘O on macOS, Ctrl+O elsewhere."""
    return QKeySequence(key).toString(QKeySequence.NativeText)


class TopBar(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # app mark and name
        self.mark = QLabel()
        self.mark.setObjectName("AppMark")
        layout.addWidget(self.mark)
        # (in a widget of its own: hidden as a whole when the bar is narrow)
        self.names = QWidget()
        names = QVBoxLayout(self.names)
        names.setContentsMargins(0, 0, 0, 0)
        names.setSpacing(0)
        self.app_name = QLabel("myPGM")
        self.app_name.setObjectName("AppName")
        self.app_subtitle = QLabel("Pressure Gauge Monitor")
        self.app_subtitle.setObjectName("AppSubtitle")
        # stretches keep the two lines together instead of splitting the bar's height
        names.addStretch(1)
        names.addWidget(self.app_name)
        names.addWidget(self.app_subtitle)
        names.addStretch(1)
        layout.addWidget(self.names)
        layout.addSpacing(10)
        layout.addWidget(divider(length=28))
        layout.addSpacing(10)

        # session name and save status
        self.session_caption = label("Session", "muted-13")
        layout.addWidget(self.session_caption)
        self.session_label = ElidedLabel("Untitled session")
        self.session_label.setObjectName("SessionName")
        self.session_label.setMinimumWidth(60)
        layout.addWidget(self.session_label)
        layout.addSpacing(4)
        self.save_pill = QLabel()
        self.save_pill.setObjectName("SavePill")
        self.save_pill.setFixedHeight(24)
        layout.addWidget(self.save_pill, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        # panels shown below the workspace (separate windows until they are docks)
        self.log_toggle = icon_button("table", "Pressure log", size=34, icon_size=16)
        self.plot_toggle = icon_button("chart-scatter", "P vs Pm plot", size=34, icon_size=16)
        for toggle in (self.log_toggle, self.plot_toggle):
            toggle.setCheckable(True)
            layout.addWidget(toggle)
        layout.addSpacing(4)
        layout.addWidget(divider(length=24))
        layout.addSpacing(4)

        self.open_button = self._text_button(
            "folder-open", "Open", f"Open a session ({_shortcut_text(QKeySequence.Open)})")
        self.save_button = self._text_button(
            "save", "Save", f"Save the session ({_shortcut_text(QKeySequence.Save)})")
        self.export_button = self._text_button("download", "Export CSV",
                                               "Export the pressure log to a CSV file")
        for text_button in (self.open_button, self.save_button, self.export_button):
            layout.addWidget(text_button)

        self.theme_button = icon_button("moon", "Dark theme", size=34, icon_size=16)
        self.theme_button.setProperty("role", "quiet-icon")
        layout.addWidget(self.theme_button)
        self.settings_button = icon_button("settings", "Settings", size=34, icon_size=16)
        self.settings_button.setProperty("role", "quiet-icon")
        layout.addWidget(self.settings_button)

        # narrow window: the app name, "Session", then the button texts make room, so
        # the bar never sets the window's minimum width (widgets.Collapser)
        self.collapser = Collapser(self, [self.names, self.session_caption,
                                          self.export_button, self.open_button,
                                          self.save_button])

        self.app_version = "dev"
        # save status: "Not saved yet", or the time since the last save / backup
        self._saved_at = None
        self._saved_kind = None
        self._pill_timer = QTimer(self)
        self._pill_timer.timeout.connect(self._update_pill)
        self._pill_timer.start(5000)
        self.restyle()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(hint.width() - self.collapser.min_width_saving())
        return hint

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.collapser.fit(event.size().width())

    @staticmethod
    def _text_button(icon_name, text, tooltip):
        return button(text, 34, role="toolbar", icon_name=icon_name, tooltip=tooltip)

    # --- content ---------------------------------------------------------------------------

    def set_version(self, version):
        self.app_version = version
        self.app_subtitle.setText(f"Pressure Gauge Monitor · v{version}")

    def set_session_name(self, name):
        self.session_label.setText(name or "Untitled session")
        self.session_label.setToolTip(name or "")
        self.session_label.update()

    def set_save_status(self, kind, when=None):
        """kind: None (not saved yet), 'saved' or 'autosaved'; when: time.time()."""
        self._saved_kind = kind
        self._saved_at = when if when is not None else time.time()
        self._update_pill()

    def save_status_text(self):
        if self._saved_kind is None:
            return "Not saved yet"
        seconds = max(0, int(time.time() - self._saved_at))
        if seconds < 5:
            ago = "just now"
        elif seconds < 60:
            ago = f"{seconds} s ago"
        elif seconds < 3600:
            ago = f"{seconds // 60} min ago"
        else:
            ago = time.strftime("at %H:%M", time.localtime(self._saved_at))
        return f"{'Autosaved' if self._saved_kind == 'autosaved' else 'Saved'} {ago}"

    def _update_pill(self):
        t = theme.tokens()
        dot = theme.qcolor(t["ac"] if self._saved_kind else t["mu"]).name()
        self.save_pill.setText(f'<span style="color:{dot}">●</span>&nbsp; {self.save_status_text()}')

    def set_dark(self, dark):
        """Theme toggle shows what it switches to: moon in light theme, sun in dark."""
        self.theme_button._theme_icon = ("sun" if dark else "moon", "tx", 16)
        self.theme_button.setToolTip("Light theme" if dark else "Dark theme")
        self.theme_button.setAccessibleName(self.theme_button.toolTip())

    def restyle(self):
        """Colours that are not in the stylesheet (app mark, pill dot)."""
        self.mark.setPixmap(icons.app_mark(24))
        self._update_pill()

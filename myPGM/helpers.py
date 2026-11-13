import numpy as np
from PyQt5.QtWidgets import (QFrame,
                             QDoubleSpinBox,
                             QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QLabel,
                             QPushButton,
                             QWidget,
                             QSlider,
                             QApplication)
from PyQt5.QtCore import Qt, pyqtSignal, QLocale
from PyQt5.QtGui import QIcon, QFontInfo
from functools import wraps
from importlib.resources import files

FONT_RULE_MARKER = "/* myPGM font size */"

def set_app_theme(style):
    """Apply a theme stylesheet to the whole application, keeping the font size rule."""
    app = QApplication.instance()
    _, marker, font_rule = app.styleSheet().partition(FONT_RULE_MARKER)
    app.setStyleSheet(style + marker + font_rule)

DEFAULT_FONT_PX = 15

def current_app_font_px():
    """Pixel size of the font currently used by the application widgets. Qt gives
    -1 when it cannot resolve one (seen on Windows): the point size is then
    converted, and DEFAULT_FONT_PX used as a last resort (-1 px fonts were set)."""
    font = QApplication.font()
    size = QFontInfo(font).pixelSize()
    if size <= 0 and font.pointSizeF() > 0:
        size = round(font.pointSizeF() * QApplication.primaryScreen().logicalDotsPerInch() / 72)
    return size if size > 0 else DEFAULT_FONT_PX

def set_app_font_size(size):
    """Set the global font size, keeping the current theme stylesheet."""
    app = QApplication.instance()
    base_style = app.styleSheet().split(FONT_RULE_MARKER)[0]
    app.setStyleSheet(f"{base_style}{FONT_RULE_MARKER}\n* {{ font-size: {size}px; }}\n")

class FontSizeWindow(QWidget):

    # widgets drawn outside of Qt stylesheets (plots, table) listen to this
    font_size_changed = pyqtSignal(int)

    def __init__(self, current_size=DEFAULT_FONT_PX):
        super().__init__()

        self.setObjectName("FontSizeWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Font size control")

        layout = QVBoxLayout(self)

        self.label = QLabel("Adjust global font size")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(8)
        self.slider.setMaximum(30)
        # start from the size in use: nothing changes until the slider is moved
        self.slider.setValue(current_size)
        layout.addWidget(self.slider)

        self.value_label = QLabel(f"{self.slider.value()}px")
        layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(self.set_font_size)

    def set_font_size(self, size):
        set_app_font_size(size)
        self.value_label.setText(f"{size}px")
        self.font_size_changed.emit(size)

class SmartDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLocale(QLocale.c())
    def valueFromText(self, text):
        text = text.replace(",", ".")
        return float(text)
    def validate(self, text, pos):
        text = text.replace(",", ".")
        return super().validate(text, pos)

class SmartDoubleDialog(QDialog):
    def __init__(self, valuename='Value:', parent=None):
        super().__init__(parent)
        
        self.setObjectName("SmartDoubleDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        
        self.spinbox = SmartDoubleSpinBox()
        self.spinbox.setDecimals(2)
        self.spinbox.setRange(-np.inf, np.inf)
        self.spinbox.setSingleStep(0.1)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(valuename))
        layout.addWidget(self.spinbox)

        # Buttons
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def value(self):
        return self.spinbox.value()

class MyHSeparator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

class MyVSeparator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)

class PressureCalculationFailed(Exception):
    pass

def pressure_valid(func):
    @wraps(func)
    # self refers to presenter 
    def wrapper(self, *args, **kwargs):
        try:
            res = func(self, *args, **kwargs)
            if hasattr(self, "_get_toolbox_context") and hasattr(self, "sender"):
                toolbox, _ = self._get_toolbox_context(self.sender())
                toolbox.set_valid_colors(True)
            else:
                self.view.ptoolbox.set_valid_colors(True)
            return res
        except PressureCalculationFailed:
            if hasattr(self, "_get_toolbox_context") and hasattr(self, "sender"):
                toolbox, _ = self._get_toolbox_context(self.sender())
                toolbox.set_valid_colors(False)
            else:
                self.view.ptoolbox.set_valid_colors(False)
            return None
    return wrapper

def validate_scalar(value, name="Value"):
    if np.iscomplex(value):
        raise PressureCalculationFailed(f"{name} is complex")
    if np.isnan(value) or np.isinf(value):
        raise PressureCalculationFailed(f"{name} is NaN or infinite")
    return True

def load_style(qssfile):
    return files("myPGM.ui").joinpath(qssfile).read_text(encoding="utf-8")

def get_app_icon():
    """Return the application icon with a safe fallback order."""
    icon_candidates = [
        files("myPGM").joinpath("resources/icons/AppIcon512.png"),
        files("myPGM").joinpath("resources/icons/AppIcon256.png"),
        files("myPGM").joinpath("resources/icons/AppIcon128.png"),
    ]

    for icon_path in icon_candidates:
        try:
            if icon_path.is_file():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    return icon
        except Exception:
            continue

    return QIcon()

def customparse_file2data(f):
    def _split_line(line, delimiter):
        # For whitespace-separated files, collapse repeated spaces/tabs.
        if delimiter == ' ':
            return line.strip().split()
        return line.strip().split(delimiter)

    def _to_float(token):
        return float(token.strip().replace(',', '.'))

    with open(f, 'r') as file:
        lines = file.readlines()

    # Evaluate candidate delimiters by counting how many lines can be parsed
    # into at least two numeric columns.
    candidates = ['\t', ';', ' ', ',']
    best_delimiter = None
    best_score = (-1, -1)

    for delimiter in candidates:
        valid_lines = 0
        total_cols = 0
        for line in lines:
            sp = _split_line(line, delimiter)
            if len(sp) < 2:
                continue
            try:
                _ = [_to_float(v) for v in sp]
                valid_lines += 1
                total_cols += len(sp)
            except ValueError:
                continue

        score = (valid_lines, total_cols)
        if score > best_score:
            best_score = score
            best_delimiter = delimiter

    data_rows = []
    for line in lines:
        sp = _split_line(line, best_delimiter)
        if len(sp) < 2:
            continue
        try:
            # first two columns only: rows with more values (e.g. a numeric
            # header line) made the array ragged
            data_rows.append([_to_float(v) for v in sp][:2])
        except ValueError:
            continue

    if not data_rows:
        raise RuntimeError("No numeric data found in file")

    return np.array(data_rows, dtype=np.float64)

def _single_column_values(f):
    """Values of a one-number-per-line file (header/footer lines skipped), or None."""
    with open(f, 'r') as file:
        data_lines = []
        for line in file:
            try:
                data_lines.append(float(line.strip().replace(',', '.')))
            except ValueError:
                pass
    return np.array(data_lines, dtype=np.float64) if data_lines else None

def _strictly_monotonic(values):
    steps = np.diff(values)
    return bool(np.all(steps > 0) or np.all(steps < 0))

def spectro_calibration_reader(f):
    """x axis of an alternative spectrometer calibration: the first column of a
    two-column file, or a single-column file. A calibration axis is strictly
    monotonic, which decides between the two readings of a line like '690,01'
    (two columns, or one value with a decimal comma: it was read as 690)."""
    readings = []
    try:
        readings.append(customparse_file2data(f)[:, 0])      # two-column file
    except RuntimeError:
        pass
    single = _single_column_values(f)
    if single is not None:
        readings.append(single)
    if not readings:
        raise RuntimeError("No numeric data found in spectrometer calibration file")
    for data in readings:
        if _strictly_monotonic(data):
            return data
    return readings[0]

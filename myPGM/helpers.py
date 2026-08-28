import numpy as np
from copy import deepcopy
from scipy.optimize import minimize
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
from PyQt5.QtCore import (Qt, 
                         QObject, 
                         pyqtSignal, 
                         QAbstractListModel, 
                         QModelIndex, 
                         QLocale)

from PyQt5.QtGui import QIcon, QFont
import csv
from functools import wraps
# compatibility bridge
try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files

class FontSizeWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Font size control")

        layout = QVBoxLayout(self)

        self.label = QLabel("Adjust global font size")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(8)
        self.slider.setMaximum(30)
        self.slider.setValue(15)
        layout.addWidget(self.slider)

        self.value_label = QLabel()
        layout.addWidget(self.value_label)

        self.set_font_size(self.slider.value())

        self.slider.valueChanged.connect(self.set_font_size)

    def set_font_size(self, size):
        app = QApplication.instance()
        app.setStyleSheet(f"""
            * {{
                font-size: {size}px;
            }}
        """)
        self.value_label.setText(f"{size}px")

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
        except PressureCalculationFailed as err:
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
            data_rows.append([_to_float(v) for v in sp])
        except ValueError:
            continue

    if not data_rows:
        raise RuntimeError("No numeric data found in file")

    data = np.array(data_rows, dtype=np.float64)
    return data[:, :2]

def spectro_calibration_reader(f):
    try:
        # two-column file
        data = customparse_file2data(f)[:, 0]
        return data

    except Exception:
        # single-column file (?)
        with open(f, 'r') as file:
            data_lines = []
            for line in file:
                try:
                    # in case of header/footer
                    v = float(line.strip().replace(',', '.'))
                    data_lines.append(v)
                except ValueError:
                    #print(line)
                    pass

            if not data_lines:
                raise RuntimeError("No numeric data found in spectrometer calibration file")

            data = np.array(data_lines, dtype=np.float64)
        return data


if __name__ == '__main__':
    
    import os

    f1 = os.path.dirname(__file__)+'/resources/'+'Example_Ruby_1.asc'
    f2 = os.path.dirname(__file__)+'/resources/'+'alternate_spectro_calib_2cols.asc'
    f3 = os.path.dirname(__file__)+'/resources/'+'alternate_spectro_calib_1col_header.asc'    


    print(customparse_file2data(f1))

    print(spectro_calibration_reader(f2))
    print(spectro_calibration_reader(f3))


    print(all(spectro_calibration_reader(f2) == spectro_calibration_reader(f3)))
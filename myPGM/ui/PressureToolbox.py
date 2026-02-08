#import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, 
                             QWidget, 
                             QPushButton, 
                             QComboBox, 
                             QLabel,
                             QLineEdit,
                             QVBoxLayout,
                             QHBoxLayout,
                             QFormLayout,
                             QGridLayout,
                             QFrame,
                             QGroupBox,
                             QSpinBox,
                             QDoubleSpinBox,)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, Qt

from myPGM.calibrations import HPCalibration
from myPGM.helpers import MyHSeparator, MyVSeparator


class PressureToolbox(QWidget):

    calibChanged = pyqtSignal(HPCalibration)
    PmChanged = pyqtSignal(float)
    PChanged = pyqtSignal(float)
    xChanged = pyqtSignal(float)
    TChanged = pyqtSignal(float)
    x0Changed = pyqtSignal(float)
    T0Changed = pyqtSignal(float)

    GREEN = LIGHTMODEGREEN = "#ccffcc"
    RED = LIGHTMODERED = "#ee6b6e"
    BLUE = LIGHTMODEBLUE = "#c1d9ff"

    DARKMODEGREEN = "#3b8132"
    DARKMODERED = "#c30010"
    DARKMODEBLUE = "#0077b6"

    def __init__(self):
        super().__init__()

        ToolboxGroup = QGroupBox("Pressure toolbox")
        Toolboxlayout = QHBoxLayout()

        self.Pm_spinbox = QDoubleSpinBox()
        self.Pm_spinbox.setObjectName("Pm_spinbox")
        self.Pm_spinbox.setDecimals(2)
        self.Pm_spinbox.setRange(-np.inf, np.inf)
        self.Pm_spinbox.setSingleStep(0.1)
        self.Pm_spinbox.setStyleSheet(f"background: {PressureToolbox.BLUE};")
        self.Pm_spinbox.setMinimumWidth(80)

        self.P_spinbox = QDoubleSpinBox()
        self.P_spinbox.setObjectName("P_spinbox")
        self.P_spinbox.setDecimals(3)
        self.P_spinbox.setRange(-np.inf, np.inf)
        self.P_spinbox.setSingleStep(0.1)
#        self.P_spinbox.setStyleSheet("background: #ccffcc;")
        self.P_spinbox.setMinimumWidth(80)

        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setObjectName("x_spinbox")
        self.x_spinbox.setDecimals(3)
        self.x_spinbox.setSingleStep(0.01)
        self.x_spinbox.setRange(-np.inf, +np.inf)
        self.x_spinbox.setMinimumWidth(80)

        self.x0_spinbox = QDoubleSpinBox()
        self.x0_spinbox.setObjectName("x0_spinbox")
        self.x0_spinbox.setDecimals(3)
        self.x0_spinbox.setSingleStep(0.01)
        self.x0_spinbox.setRange(-np.inf, +np.inf)
        self.x0_spinbox.setMinimumWidth(80)

        self.T_spinbox = QDoubleSpinBox()
        self.T_spinbox.setObjectName("T_spinbox")
        self.T_spinbox.setDecimals(0)
        self.T_spinbox.setRange(-np.inf, +np.inf)
        self.T_spinbox.setSingleStep(1)
        self.T_spinbox.setMinimumWidth(80)

        self.T0_spinbox = QDoubleSpinBox()
        self.T0_spinbox.setObjectName("T0_spinbox")
        self.T0_spinbox.setDecimals(0)
        self.T0_spinbox.setRange(-np.inf, +np.inf)
        self.T0_spinbox.setSingleStep(1)
        self.T0_spinbox.setMinimumWidth(80)

        self._xP_bgcolor = None

        self.calibration_combo = QComboBox()
        self.calibration_combo.setObjectName("calibration_combo")
        self.calibration_combo.setMinimumWidth(160)

        self.x_label = QLabel("lambda (nm)")
        self.x0_label = QLabel("lambda0 (nm)")

        pressure_form = QFormLayout()
        pressure_form.addRow(QLabel("Pm (bar)"), self.Pm_spinbox)
        pressure_form.addRow(QLabel("P (GPa)"), self.P_spinbox)

        # Calib params form
        param_form = QHBoxLayout()
        form_x = QFormLayout()
        form_x.addRow(self.x_label, self.x_spinbox)
        form_x.addRow(self.x0_label, self.x0_spinbox)
        form_T = QFormLayout()
        form_T.addRow(QLabel("T (K)"), self.T_spinbox)
        form_T.addRow(QLabel("T0 (K)"), self.T0_spinbox)
        param_form.addLayout(form_x)
        param_form.addLayout(form_T)

        calibration_form = QFormLayout()
        calibration_form.addRow(QLabel("Calibration: "), self.calibration_combo)

        self.Tcor_Label = QLabel("NA")
        calibration_form.addRow(QLabel("T correction: "), self.Tcor_Label)


        Toolboxlayout.addLayout(calibration_form, stretch=4)
        Toolboxlayout.addWidget(MyVSeparator())

        Toolboxlayout.addLayout(param_form, stretch=2)
        Toolboxlayout.addWidget(MyVSeparator())

        Toolboxlayout.addLayout(pressure_form, stretch=2)

        self.setLayout(Toolboxlayout)

    def initialize(self, calib_dict):
        self.calibrations = calib_dict
        self.init_calib_combo()
        self.init_connects()
        self.set_valid_colors(True)

    def init_connects(self):
        self.calibration_combo.currentTextChanged.connect(self.calib_changed)
        self.Pm_spinbox.valueChanged.connect(self.PmChanged.emit)
        self.P_spinbox.valueChanged.connect(self.PChanged.emit)
        self.x_spinbox.valueChanged.connect(self.xChanged.emit)
        self.T_spinbox.valueChanged.connect(self.TChanged.emit)
        self.x0_spinbox.valueChanged.connect(self.x0Changed.emit)
        self.T0_spinbox.valueChanged.connect(self.T0Changed.emit)

    def init_calib_combo(self):
        if self.calibrations is not None:
            self.calibration_combo.addItems(self.calibrations.keys())

            for k, v in self.calibrations.items():
                ind = self.calibration_combo.findText(k)
                self.calibration_combo.model().item(ind).setBackground(QColor(v.color))
        else:
            raise ImportError('Error loading calibrations.')

    def calib_changed(self, newcalib_name):
        newcalib = self.calibrations[newcalib_name]

        self.set_calib(newcalib)
        self.calibChanged.emit(newcalib)

    def set_Pmval(self, Pm):
        self.Pm_spinbox.blockSignals(True)
        self.Pm_spinbox.setValue(Pm)
        self.Pm_spinbox.blockSignals(False)

    def set_Pval(self, P):
        self.P_spinbox.blockSignals(True)
        self.P_spinbox.setValue(P)
        self.P_spinbox.blockSignals(False)

    def set_xval(self, x):
        self.x_spinbox.blockSignals(True)
        self.x_spinbox.setValue(x)
        self.x_spinbox.blockSignals(False)

    def set_Tval(self, T):
        self.T_spinbox.blockSignals(True)
        self.T_spinbox.setValue(T)
        self.T_spinbox.blockSignals(False)

    def set_x0val(self, x0):
        self.x0_spinbox.blockSignals(True)
        self.x0_spinbox.setValue(x0)
        self.x0_spinbox.blockSignals(False)

    def set_T0val(self, T0):
        self.T0_spinbox.blockSignals(True)
        self.T0_spinbox.setValue(T0)
        self.T0_spinbox.blockSignals(False)

    def set_calib(self, newcalib):

        self.Tcor_Label.setText(newcalib.Tcor_name)

        self.calibration_combo.setStyleSheet(
            "background-color: {};\
             selection-background-color: k;".format(newcalib.color))

        self.x_label.setText(
            "{} ({})".format(newcalib.xname, newcalib.xunit)
        )
        self.x0_label.setText(
            "{}0 ({})".format(newcalib.xname, newcalib.xunit)
        )

#        Upon calib change by user :
#        buffer.set_calibration(newcalib) is called from presenter
#        toolbox.set_state_from_buffer(buffer) is called from presenter
#        toolbox.set_calib is called from toolbox.set_state_buffer below
#        hence x0 is set. 
        
        # if calib is set not from the user through GUI we need this:
        s = self.calibration_combo.currentText()
        if s != newcalib.name:
            ind = self.calibration_combo.findText(newcalib.name, 
                                            Qt.MatchExactly)
            self.calibration_combo.blockSignals(True)
            self.calibration_combo.setCurrentIndex(ind)
            self.calibration_combo.blockSignals(False)

        self.x_spinbox.setSingleStep(newcalib.xstep)
        self.x0_spinbox.setSingleStep(newcalib.xstep)

    
    def set_state_from_buffer(self, buffer):
        # buffer is a PressureGaugeDataObject

        # no signal here!
        self.set_Pmval(buffer.Pm)
        self.set_Pval(buffer.P)        
        self.set_xval(buffer.x)
        self.set_x0val(buffer.x0)
        self.set_Tval(buffer.T)
        self.set_T0val(buffer.T0)
        self.set_calib(buffer.calib)

    def set_valid_colors(self, valid):
        if valid:
            # green
            self.P_spinbox.setStyleSheet(f"background: {PressureToolbox.GREEN};")
            self.x_spinbox.setStyleSheet(f"background: {PressureToolbox.GREEN};")
            self._xP_bgcolor = PressureToolbox.GREEN
        else:
            # red
            self.P_spinbox.setStyleSheet(f"background: {PressureToolbox.RED};")
            self.x_spinbox.setStyleSheet(f"background: {PressureToolbox.RED};")
            self._xP_bgcolor = PressureToolbox.RED

    def set_dark_mode(self):
        PressureToolbox.GREEN = PressureToolbox.DARKMODEGREEN
        PressureToolbox.RED = PressureToolbox.DARKMODERED
        PressureToolbox.BLUE = PressureToolbox.DARKMODEBLUE
        
        if self._xP_bgcolor == PressureToolbox.LIGHTMODEGREEN:
            self.set_valid_colors(True)
        elif self._xP_bgcolor == PressureToolbox.LIGHTMODERED:
            self.set_valid_colors(False)

        self.Pm_spinbox.setStyleSheet(f"background: {PressureToolbox.BLUE};")


    def set_light_mode(self):
        PressureToolbox.GREEN = PressureToolbox.LIGHTMODEGREEN
        PressureToolbox.RED = PressureToolbox.LIGHTMODERED
        PressureToolbox.BLUE = PressureToolbox.LIGHTMODEBLUE

        if self._xP_bgcolor == PressureToolbox.DARKMODEGREEN:
            self.set_valid_colors(True)
        elif self._xP_bgcolor == PressureToolbox.DARKMODERED:
            self.set_valid_colors(False)

        self.Pm_spinbox.setStyleSheet(f"background: {PressureToolbox.BLUE};")
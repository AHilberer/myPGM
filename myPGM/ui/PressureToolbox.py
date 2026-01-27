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
from PyQt5.QtCore import pyqtSignal

from myPGM.calibrations import HPCalibration
from myPGM.ui.main_ui import MyHSeparator, MyVSeparator


class PressureToolbox(QWidget):

    calibChanged = pyqtSignal(HPCalibration)
    PChanged = pyqtSignal(float)
    xChanged = pyqtSignal(float)
    TChanged = pyqtSignal(float)
    x0Changed = pyqtSignal(float)
    T0Changed = pyqtSignal(float)

    def __init__(self, calib_dict):
        super().__init__()

        self.calibrations = calib_dict

        ToolboxGroup = QGroupBox("Pressure toolbox")
        Toolboxlayout = QHBoxLayout()

        self.Pm_spinbox = QDoubleSpinBox()
        self.Pm_spinbox.setObjectName("Pm_spinbox")
        self.Pm_spinbox.setDecimals(2)
        self.Pm_spinbox.setRange(-np.inf, np.inf)
        self.Pm_spinbox.setSingleStep(0.1)
        self.Pm_spinbox.setStyleSheet("background: #c1d9ff;")
        self.Pm_spinbox.setMinimumWidth(80)

        self.P_spinbox = QDoubleSpinBox()
        self.P_spinbox.setObjectName("P_spinbox")
        self.P_spinbox.setDecimals(3)
        self.P_spinbox.setRange(-np.inf, np.inf)
        self.P_spinbox.setSingleStep(0.1)
        self.P_spinbox.setStyleSheet("background: #ccffcc;")
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


        Toolboxlayout.addLayout(calibration_form, stretch=2)
        Toolboxlayout.addWidget(MyVSeparator())

        Toolboxlayout.addLayout(param_form, stretch=2)
        Toolboxlayout.addWidget(MyVSeparator())

        Toolboxlayout.addLayout(pressure_form, stretch=2)

        self.setLayout(Toolboxlayout)

        self.init_calib_combo()
        self.init_connects()


    def init_connects(self):
        self.calibration_combo.currentTextChanged.connect(self.update_calib)
        
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


    # def update(self):
    #     # if P is modified, change the value of x
    #     if self.P_spinbox.hasFocus():
    #         self.buffer.P = self.P_spinbox.value()

    #         try:
    #             self.buffer.compute_x_from_P()
    #             self.x_spinbox.setValue(self.buffer.x)

    #             self.x_spinbox.setStyleSheet("background: #ccffcc;")  # green
    #         except:
    #             self.x_spinbox.setStyleSheet("background: #ec5353;")  # red
    #             print("Error computing x from P")

    #     else:  # anything else than P has been manually changed, update the buffer
    #         # read everything stupidly
    #         if self.buffer is not None:
    #             self.buffer.Pm = self.Pm_spinbox.value()
    #             self.buffer.x = self.x_spinbox.value()
    #             self.buffer.T = self.T_spinbox.value()
    #             self.buffer.x0 = self.x0_spinbox.value()
    #             self.buffer.T0 = self.T0_spinbox.value()

    #             try:
    #                 self.buffer.compute_P_from_x()
    #                 self.P_spinbox.setValue(self.buffer.P)

    #                 self.P_spinbox.setStyleSheet("background: #ccffcc;")  # green
    #             except:
    #                 self.P_spinbox.setStyleSheet("background: #ec5353;")  # red
    #                 print("Error computing P from x")


    def set_state(self, buffer):
        # buffer is a PressureGaugeDataObject
        
        self.P_spinbox.blockSignals(True)
        self.x_spinbox.blockSignals(True)
        self.T_spinbox.blockSignals(True)
        self.x0_spinbox.blockSignals(True)
        self.T0_spinbox.blockSignals(True)

        self.Pm_spinbox.setValue(buffer.Pm)
        self.P_spinbox.setValue(buffer.P)
        self.x_spinbox.setValue(buffer.x)
        self.T_spinbox.setValue(buffer.T)
        self.x0_spinbox.setValue(buffer.x0)
        self.T0_spinbox.setValue(buffer.T0)

        self.P_spinbox.blockSignals(False)
        self.x_spinbox.blockSignals(False)
        self.T_spinbox.blockSignals(False)
        self.x0_spinbox.blockSignals(False)
        self.T0_spinbox.blockSignals(False)

        # do I need this ? 
        self.update_calib(buffer.calib.name)


    def update_calib(self, new_text_key):

        newcalib = self.calibrations[new_text_key]

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

        self.x_spinbox.setSingleStep(newcalib.xstep)
        self.x0_spinbox.setSingleStep(newcalib.xstep)

#        # note that this should call update() but it does not at __init__ !!
#       /!\ /!\
        self.x0_spinbox.setValue(newcalib.x0default)    # /!\
        
        self.calibChanged.emit(newcalib)
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
from myPGM.ui.main_ui import MyHSeparator, MyVSeparator


class PressureToolbox(QWidget):
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

        self.populate_calib_combo()

        self.create_connects()

    def create_connects(self):

        self.Pm_spinbox.valueChanged.connect(self.update)
        self.P_spinbox.valueChanged.connect(self.update)
        self.x_spinbox.valueChanged.connect(self.update)
        self.x0_spinbox.valueChanged.connect(self.update)
        self.T_spinbox.valueChanged.connect(self.update)
        self.T0_spinbox.valueChanged.connect(self.update)

        self.calibration_combo.currentIndexChanged.connect(self.update_calib)

    def disconnect(self):

        self.Pm_spinbox.valueChanged.disconnect()
        self.P_spinbox.valueChanged.disconnect()
        self.x_spinbox.valueChanged.disconnect()
        self.x0_spinbox.valueChanged.disconnect()
        self.T_spinbox.valueChanged.disconnect()
        self.T0_spinbox.valueChanged.disconnect()

        self.calibration_combo.currentIndexChanged.disconnect()

    def populate_calib_combo(self):
        if self.calibrations is not None:
            self.calibration_combo.addItems(self.calibrations.keys())

            for k, v in self.calibrations.items():
                ind = self.calibration_combo.findText(k)
                self.calibration_combo.model().item(ind).setBackground(QColor(v.color))
        else:
            raise ImportError('Error loading calibrations.')

    def set_state(self, buffer):
        # buffer is a PressureGaugeDataObject
        
        # self.buffer  always reflect the current state
        self.buffer = buffer

        self.disconnect()
        self.Pm_spinbox.setValue(self.buffer.Pm)
        self.P_spinbox.setValue(self.buffer.P)
        self.x_spinbox.setValue(self.buffer.x)
        self.T_spinbox.setValue(self.buffer.T)
        self.x0_spinbox.setValue(self.buffer.x0)
        self.T0_spinbox.setValue(self.buffer.T0)
        self.create_connects()

        self.Tcor_Label.setText(self.buffer.calib.Tcor_name)
        self.calibration_combo.setCurrentText(self.buffer.calib.name)
        
        newind = self.calibration_combo.currentIndex()
        tmp_color = self.calibration_combo.model().item(newind).background().color().getRgb()
        self.calibration_combo.setStyleSheet(
                "background-color: rgba{};\
                        selection-background-color: k;".format(tmp_color))

        self.update_calib(newind)
        self.update()


    def update(self):
        # if P is modified, change the value of x
        if self.P_spinbox.hasFocus():
            self.buffer.P = self.P_spinbox.value()

            try:
                self.buffer.compute_x_from_P()
                self.x_spinbox.setValue(self.buffer.x)

                self.x_spinbox.setStyleSheet("background: #ccffcc;")  # green
            except:
                self.x_spinbox.setStyleSheet("background: #ec5353;")  # red
                print("Error computing x from P")

        else:  # anything else than P has been manually changed, update the buffer
            # read everything stupidly
            if self.buffer is not None:
                self.buffer.Pm = self.Pm_spinbox.value()
                self.buffer.x = self.x_spinbox.value()
                self.buffer.T = self.T_spinbox.value()
                self.buffer.x0 = self.x0_spinbox.value()
                self.buffer.T0 = self.T0_spinbox.value()

                try:
                    self.buffer.compute_P_from_x()
                    self.P_spinbox.setValue(self.buffer.P)

                    self.P_spinbox.setStyleSheet("background: #ccffcc;")  # green
                except:
                    self.P_spinbox.setStyleSheet("background: #ec5353;")  # red
                    print("Error computing P from x")

    def update_calib(self, newind):
        self.buffer.calib = self.calibrations[self.calibration_combo.currentText()]

        self.Tcor_Label.setText(self.buffer.calib.Tcor_name)

        tmp_color = self.calibration_combo.model().item(newind).background().color().getRgb()
        self.calibration_combo.setStyleSheet(
            "background-color: rgba{};\
                    selection-background-color: k;".format(tmp_color)
        )

        self.x_label.setText(
            "{} ({})".format(self.buffer.calib.xname, self.buffer.calib.xunit)
        )
        self.x0_label.setText(
            "{}0 ({})".format(self.buffer.calib.xname, self.buffer.calib.xunit)
        )

        self.x_spinbox.setSingleStep(self.buffer.calib.xstep)
        self.x0_spinbox.setSingleStep(self.buffer.calib.xstep)
        # note that this should call update() but it does not at __init__ !!
        self.x0_spinbox.setValue(self.buffer.calib.x0default)

        # self.plot_data() # a priori no need to call plot_data here
        #self.calib_change_signal.emit(self.buffer.calib)


import numpy as np
from PyQt5.QtWidgets import (QWidget,
                             QAbstractSpinBox,
                             QComboBox,
                             QFrame,
                             QGridLayout,
                             QLabel,
                             QHBoxLayout,
                             QVBoxLayout,)
from PyQt5.QtCore import QEvent, pyqtSignal, Qt

from myPGM.calibrations import HPCalibration
from myPGM.helpers import SmartDoubleSpinBox
from myPGM.ui import theme
from myPGM.ui.widgets import GAP, Card, DotItemDelegate, label, x_symbol, x_unit

INPUT_HEIGHT = 36

class PressureToolbox(QWidget):

    calibChanged = pyqtSignal(HPCalibration)
    PmChanged = pyqtSignal(float)
    calib_shown = pyqtSignal(object)        # calibration now shown (colours follow it)
    PChanged = pyqtSignal(float)
    xChanged = pyqtSignal(float)
    TChanged = pyqtSignal(float)
    x0Changed = pyqtSignal(float)
    T0Changed = pyqtSignal(float)

    # field backgrounds: valid / invalid pressure, T not at room temperature, Pm
    GREEN = LIGHTMODEGREEN = theme.LIGHT["ok"]
    RED = LIGHTMODERED = theme.LIGHT["bad"]
    BLUE = LIGHTMODEBLUE = theme.LIGHT["info"]
    ORANGE = LIGHTMODEORANGE = theme.LIGHT["warn"]

    DARKMODEGREEN = theme.DARK["ok"]
    DARKMODERED = theme.DARK["bad"]
    DARKMODEBLUE = theme.DARK["info"]
    DARKMODEORANGE = theme.DARK["warn"]

    def __init__(self, inspector=False):
        """inspector: laid out as the main window's inspector cards (stacked, no Pm
        field: the window shows Pm next to "Add fit to log"). Otherwise a standalone
        window (the additional toolbox) with the cards side by side and a Pm field."""
        super().__init__()

        self.setObjectName("PressureToolbox")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.inspector = inspector
        if not inspector:
            self.setWindowTitle("myPGM - Additional pressure toolbox")

        self.Pm_spinbox = self._spinbox("Pm_spinbox", decimals=2, step=0.1)
        self.P_spinbox = self._spinbox("P_spinbox", decimals=3, step=0.1)
        self.P_spinbox.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.x_spinbox = self._spinbox("x_spinbox", decimals=3, step=0.01)
        self.x0_spinbox = self._spinbox("x0_spinbox", decimals=3, step=0.01)
        # λ from the fit: accent border and a small "fit" tag (DESIGN.md §1, Parameters)
        self.x_fit_tag = QLabel("fit", self.x_spinbox)
        self.x_fit_tag.setObjectName("FitTag")
        self.x_fit_tag.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.x_fit_tag.setToolTip("Value from the fit of the spectrum")
        self.x_fit_tag.hide()
        self.x_spinbox.setProperty("fitted", False)
        self.x_spinbox.installEventFilter(self)
        self.T_spinbox = self._spinbox("T_spinbox", decimals=1, step=1)
        self.T0_spinbox = self._spinbox("T0_spinbox", decimals=1, step=1)

        self._valid = True
        self._T_bgcolor = None
        self._calib = None              # current calibration, gives the selector colour

        # --- PRESSURE GAUGE card -------------------------------------------------------
        self.gauge_card = Card("Pressure gauge", spacing=6)
        self.calibration_combo = QComboBox()
        self.calibration_combo.setObjectName("calibration_combo")
        self.calibration_combo.setMinimumWidth(160)
        self.calibration_combo.setFixedHeight(INPUT_HEIGHT)
        self.gauge_card.body.addSpacing(4)
        self.gauge_card.body.addWidget(label("Calibration", "field"))
        self.gauge_card.body.addWidget(self.calibration_combo)
        self.Tcor_Label = QLabel("NA")
        self.Tcor_Label.setProperty("role", "caption")
        self.gauge_card.body.addWidget(self.Tcor_Label)
        # the main window puts the fit model selector here
        self.fit_model_slot = QVBoxLayout()
        self.fit_model_slot.setContentsMargins(0, 6, 0, 0)
        self.fit_model_slot.setSpacing(6)
        self.gauge_card.body.addLayout(self.fit_model_slot)

        # --- PARAMETERS card -----------------------------------------------------------
        self.params_card = Card("Parameters", spacing=10)
        self.params_card.header.addWidget(label("λ ⇄ P linked", "caption"))
        self.x_label = label("λ (nm)", "field")
        self.x0_label = label("λ₀ (nm)", "field")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        for column, (field_label, spinbox) in enumerate(
                ((self.x_label, self.x_spinbox), (self.x0_label, self.x0_spinbox))):
            grid.addWidget(field_label, 0, column)
            grid.addWidget(spinbox, 1, column)
        grid.setRowMinimumHeight(2, 4)
        for column, (text, spinbox) in enumerate(
                (("T (K)", self.T_spinbox), ("T₀ (K)", self.T0_spinbox))):
            grid.addWidget(label(text, "field"), 3, column)
            grid.addWidget(spinbox, 4, column)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.params_card.body.addLayout(grid)

        # highlighted pressure row
        pressure_row = QFrame()
        pressure_row.setObjectName("PressureRow")
        pressure_row.setAttribute(Qt.WA_StyledBackground, True)
        row_layout = QHBoxLayout(pressure_row)
        row_layout.setContentsMargins(14, 6, 6, 6)
        row_layout.setSpacing(8)
        p_label = QLabel("P (GPa)")
        p_label.setObjectName("PressureLabel")
        row_layout.addWidget(p_label)
        row_layout.addWidget(self.P_spinbox, 1)
        self.params_card.body.addWidget(pressure_row)

        if not inspector:
            pm_row = QHBoxLayout()
            pm_row.setSpacing(8)
            pm_row.addWidget(label("Membrane pressure Pm", "field"))
            pm_row.addWidget(self.Pm_spinbox, 1)
            pm_row.addWidget(label("bar", "muted"))
            self.params_card.body.addLayout(pm_row)

        # the main window puts its "Add point to log" button here
        self.add_point_slot = QVBoxLayout()
        self.add_point_slot.setContentsMargins(0, 2, 0, 0)
        self.params_card.body.addLayout(self.add_point_slot)

        if inspector:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(GAP)
            layout.addWidget(self.gauge_card)
            layout.addWidget(self.params_card)
        else:
            # the two cards side by side, as high as their contents: a taller window
            # leaves the space under them instead of stretching the cards
            outer = QVBoxLayout(self)
            outer.setContentsMargins(GAP, GAP, GAP, GAP)
            layout = QHBoxLayout()
            layout.setSpacing(GAP)
            self.gauge_card.body.addStretch(1)
            layout.addWidget(self.gauge_card)
            layout.addWidget(self.params_card)
            outer.addLayout(layout)
            outer.addStretch(1)

    @staticmethod
    def _spinbox(name, decimals, step):
        spinbox = SmartDoubleSpinBox()
        spinbox.setObjectName(name)
        spinbox.setDecimals(decimals)
        spinbox.setRange(-np.inf, np.inf)
        spinbox.setSingleStep(step)
        # arrows and the mouse wheel still step the value; no spin buttons (DESIGN.md)
        spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
        spinbox.setFixedHeight(INPUT_HEIGHT)
        spinbox.setMinimumWidth(96)
        return spinbox

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
        self.T_spinbox.valueChanged.connect(self.update_T_spinbox_style)
        self.T_spinbox.valueChanged.connect(self.TChanged.emit)
        self.x0_spinbox.valueChanged.connect(self.x0Changed.emit)
        self.T0_spinbox.valueChanged.connect(self.T0Changed.emit)
        # λ typed, or computed from a typed P: no longer the fitted value
        for spinbox in (self.x_spinbox, self.P_spinbox):
            spinbox.valueChanged.connect(lambda _value: self.set_x_fitted(False))

    def init_calib_combo(self):
        if self.calibrations is not None:
            self.calibration_combo.addItems(self.calibrations.keys())
            # the whole list, without scrolling
            self.calibration_combo.setMaxVisibleItems(len(self.calibrations))
            # a dot in the family colour (DESIGN.md §3), as in the fit model list
            self.calibration_combo.setItemDelegate(DotItemDelegate(
                lambda name: (theme.calib_color(self.calibrations[name])
                              if name in self.calibrations else None),
                self.calibration_combo))
        else:
            raise ImportError('Error loading calibrations.')

    def _style_calib_combo(self):
        """The calibration selector follows the calibration family (DESIGN.md §3): the
        `calib` property picks the generated rules of the stylesheet
        (theme._selector_rules)."""
        family = theme.calib_family(self._calib) or ""
        combo = self.calibration_combo
        if combo.property("calib") != family:
            combo.setProperty("calib", family)
            combo.style().unpolish(combo)
            combo.style().polish(combo)

    def calib_changed(self, newcalib_name):
        newcalib = self.calibrations[newcalib_name]

        # self.set_calib will be called from 
        # set_state_from_buffer in on_calib_changed(presenter.py)
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
        self.update_T_spinbox_style(T)

    def set_x0val(self, x0):
        self.x0_spinbox.blockSignals(True)
        self.x0_spinbox.setValue(x0)
        self.x0_spinbox.blockSignals(False)

    def set_T0val(self, T0):
        self.T0_spinbox.blockSignals(True)
        self.T0_spinbox.setValue(T0)
        self.T0_spinbox.blockSignals(False)

    def set_calib(self, newcalib):

        self.Tcor_Label.setText(f"T correction · {newcalib.Tcor_name}")

        self._calib = newcalib
        self._style_calib_combo()
        self.calib_shown.emit(newcalib)

        symbol, unit = x_symbol(newcalib), x_unit(newcalib)
        self.x_label.setText(f"{symbol} ({unit})")
        self.x0_label.setText(f"{symbol}₀ ({unit})")

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

        # greyed out for calibrations that do not use x0 (H2 vibron)
        uses_x0 = getattr(newcalib, "uses_x0", True)
        self.x0_spinbox.setEnabled(uses_x0)
        self.x0_label.setEnabled(uses_x0)
        self.x0_spinbox.setToolTip("" if uses_x0 else "Not used by this calibration")
    
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
        self.set_x_fitted(self.x_from_fit(buffer))

    @staticmethod
    def fitted_position(fit_model, fit_result):
        """x found by a fit (the peak used for the pressure, or the edge), or None."""
        if fit_model is None or fit_result is None:
            return None
        try:
            opti = fit_result["opti"]
            return float(opti if fit_model.type == "edge" else opti[fit_model.position_index(opti)])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    @classmethod
    def x_from_fit(cls, buffer):
        """True if the buffer's x is the position found by its fit."""
        fitted = cls.fitted_position(getattr(buffer, "fit_model", None),
                                     getattr(buffer, "fit_result", None))
        return (fitted is not None and buffer.x is not None
                and bool(np.isclose(fitted, float(buffer.x), rtol=0, atol=1e-9)))

    def shows_fit(self, fit_model, fit_result):
        """True if the λ field shows the position of this fit (to its 3 decimals)."""
        fitted = self.fitted_position(fit_model, fit_result)
        return fitted is not None and abs(fitted - self.x_spinbox.value()) < 0.0005 + 1e-12

    def set_x_fitted(self, fitted):
        if self.x_spinbox.property("fitted") == fitted:
            return
        self.x_spinbox.setProperty("fitted", fitted)
        self.x_spinbox.style().unpolish(self.x_spinbox)
        self.x_spinbox.style().polish(self.x_spinbox)
        self.x_fit_tag.setVisible(fitted)
        self._place_fit_tag()

    def _place_fit_tag(self):
        tag = self.x_fit_tag
        tag.adjustSize()
        box = self.x_spinbox.rect()
        tag.move(box.right() - tag.width() - 9, (box.height() - tag.height()) // 2)

    def eventFilter(self, obj, event):
        if obj is self.x_spinbox and event.type() == QEvent.Resize:
            self._place_fit_tag()
        return super().eventFilter(obj, event)

    def set_valid_colors(self, valid):
        """No colour while x and P are valid (the P row is always highlighted); a red
        background on both when the calibration cannot give a pressure."""
        self._valid = valid
        style = "" if valid else f"background: {PressureToolbox.RED};"
        self.P_spinbox.setStyleSheet(style)
        self.x_spinbox.setStyleSheet(style)

    def update_T_spinbox_style(self, T):
        if T > 298:
            self.T_spinbox.setStyleSheet(f"background: {PressureToolbox.ORANGE};")
            self._T_bgcolor = PressureToolbox.ORANGE
        else:
            self.T_spinbox.setStyleSheet("")
            self._T_bgcolor = None

    def _set_mode_colors(self, dark):
        PressureToolbox.GREEN = PressureToolbox.DARKMODEGREEN if dark else PressureToolbox.LIGHTMODEGREEN
        PressureToolbox.RED = PressureToolbox.DARKMODERED if dark else PressureToolbox.LIGHTMODERED
        PressureToolbox.BLUE = PressureToolbox.DARKMODEBLUE if dark else PressureToolbox.LIGHTMODEBLUE
        PressureToolbox.ORANGE = (PressureToolbox.DARKMODEORANGE if dark
                                  else PressureToolbox.LIGHTMODEORANGE)
        self.set_valid_colors(self._valid)
        self.update_T_spinbox_style(self.T_spinbox.value())
        self._restyle_calibrations()

    def set_dark_mode(self):
        self._set_mode_colors(dark=True)

    def set_light_mode(self):
        self._set_mode_colors(dark=False)

    def _restyle_calibrations(self):
        self._style_calib_combo()

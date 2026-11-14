import logging
import os

import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow,
    QPushButton,
    QFileDialog,
    QWidget,
    QCheckBox,
    QComboBox,
    QFrame,
    QVBoxLayout,
    QAction,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QStackedWidget,
)
from PyQt5 import sip
from PyQt5.QtCore import (
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import QGuiApplication, QKeySequence, QRegion

from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import InterpolatedUnivariateSpline
from myPGM.helpers import get_app_icon, set_app_font_size
from myPGM import log_setup
from myPGM import settings as S
from myPGM.settings import app_settings, last_dir, remember_dir

from myPGM.ui.PvPmPlot import PvPmPlotWindow
from myPGM.ui.PvPmTable import COLUMNS as LOG_COLUMNS, HPTableWindow
from myPGM.ui.FileListViewerWidget import FileListViewerWidget
from myPGM.ui.PressureToolbox import PressureToolbox
from myPGM.ui.TopBar import TopBar
from myPGM.ui.docks import MIN_HEIGHT as MIN_DOCK_HEIGHT, PanelDock
from myPGM.ui import dialogs, icons, theme
from myPGM.ui.widgets import (GAP, Button, Card, DashedSplitter, ElidedLabel,
                              ModelItemDelegate, button,
                              divider, hbox, label,
                              x_symbol, x_unit)
from myPGM.ui.center import (EmptyCenter, FitRangeEditOverlay, FitToolbar, LegendRow,
                             PeakLabel, Pill,
                             PressureCard, Segmented, SplitButton, Stepper,
                             dashed_marker_pen, peak_name)
from myPGM.ui.banner import RecoveryBanner
from myPGM.ui.dialogs import AddPointDialog
from myPGM.ui.settings_dialog import SettingsDialog

import pyqtgraph as pg

SIDEBAR_WIDTH = 240         # default column widths of the workspace (DESIGN.md §1)
SIDEBAR_MIN_WIDTH = 200
INSPECTOR_WIDTH = 300
INSPECTOR_MIN_WIDTH = 270
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1440, 1010
DOCK_HEIGHT_FRACTION = 0.28     # default height of the bottom panels (DESIGN.md §1)
MAX_DOCK_HEIGHT_FRACTION = 0.5
LOG_WIDTH_FRACTION = 0.7        # pressure log | P vs Pm split
LAYOUT_VERSION = 1              # saveState / restoreState version of the dock layout
QWIDGETSIZE_MAX = 16777215

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):

    #####################################################################################
        # ? Signals setup
    theme_switched = pyqtSignal()
    fit_from_click_signal = pyqtSignal(object)
    start_auto_fit_signal = pyqtSignal(object)
    subtract_ManualBg_signal = pyqtSignal(object)
    add_current_fit_signal = pyqtSignal(object)
    add_point_requested = pyqtSignal()
    open_session_signal = pyqtSignal()
    files_dropped = pyqtSignal(list)        # local paths dropped on the window
    demo_requested = pyqtSignal()           # "Explore the demo session" (empty state)
    save_session_signal = pyqtSignal()
    save_session_as_signal = pyqtSignal()
    settings_saved = pyqtSignal()           # Settings window: Save (autosave values for the presenter)

    def __init__(self):
        super().__init__()
        # Setup Main window parameters
        self.setWindowTitle("myPGM - Pressure Gauge Monitor")
        
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        # keeps the window on screen after a resize (resizeEvent); owned by the window,
        # so it cannot fire once the window is deleted (QTimer.singleShot with a method
        # of the window could, which crashed the Windows tests)
        self._screen_timer = QTimer(self)
        self._screen_timer.setSingleShot(True)
        self._screen_timer.setInterval(0)
        self._screen_timer.timeout.connect(self._keep_on_screen)
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)   # fitted to the screen by _place_window

        pg.setConfigOption('leftButtonPan', False)

        self._setup_menus()

        # the theme recorded at startup, before a saved dark theme is applied below
        theme.set_current(False)
        self.plot_label_color = theme.tokens()["mu"]
        self.fit_color = theme.calib_color(None)      # set from the plotted calibration
        # font size of the Settings window (13 px base, DESIGN.md §2); plots and the
        # PvPm table use it too, kept in sync by set_font_size
        self.plot_font_px = S.setting("font_size")
        set_app_font_size(self.plot_font_px)
        self.settings_dialog = None             # created when first opened

        self._create_fit_controls()
        self._create_plots()
        # pressure toolbox as inspector cards; its Pm field goes in the center, next to
        # "Add fit to log" (DESIGN.md: no Pm in the inspector)
        self.ptoolbox = PressureToolbox(inspector=True)

        #####################################################################################
        # #? Layout (DESIGN.md §1): top bar, then spectra sidebar | center | inspector

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_bar = TopBar()
        main_layout.addWidget(self.top_bar)

        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.setObjectName("Workspace")
        self.workspace_splitter.setHandleWidth(GAP)
        self.workspace_splitter.setChildrenCollapsible(False)
        # bottom margin: none while docked panels are shown (their separator is the gap)
        self.workspace_layout = QVBoxLayout()
        self.workspace_layout.setContentsMargins(GAP, GAP, GAP, GAP)
        self.workspace_layout.setSpacing(GAP)
        # backup of an unsaved session found at startup (DESIGN.md §4b)
        self.recovery_banner = RecoveryBanner()
        self.workspace_layout.addWidget(self.recovery_banner)
        self.workspace_layout.addWidget(self.workspace_splitter, 1)
        main_layout.addLayout(self.workspace_layout, 1)

        self.file_list_widget = FileListViewerWidget()
        self.file_list_widget.setMinimumWidth(SIDEBAR_MIN_WIDTH)
        self.dir_label = self.file_list_widget.dir_label
        self.workspace_splitter.addWidget(self.file_list_widget)
        self.workspace_splitter.addWidget(self._build_center())
        self.workspace_splitter.addWidget(self._build_inspector())
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)
        self.workspace_splitter.setSizes([SIDEBAR_WIDTH, DEFAULT_WIDTH - SIDEBAR_WIDTH - INSPECTOR_WIDTH,
                                          INSPECTOR_WIDTH])
        self._style_plots()

        #####################################################################################
        # #? Bottom panels: pressure log and P vs Pm plot, side by side in docks

        self.PvPmTableWindow = HPTableWindow()
        self.PvPmPlotWindow = PvPmPlotWindow()
        self._setup_docks()
        self._layout_restored = self._restore_layout()
        if not self._layout_restored:
            self._place_window()
        self._connect_top_bar()                 # toggles start from the restored layout

        self.set_font_size(self.plot_font_px)

        self.additional_toolbox_window = PressureToolbox()

        # set by the presenter: called on close, returns False to keep the window open
        self.close_guard = None

        # theme chosen in a previous launch (light by default; "system" follows the OS)
        if theme.mode_is_dark(S.setting("theme")):
            self._apply_theme(dark=True, remember=False)

    #####################################################################################
    # ? Window construction

    def _setup_menus(self):
        menubar = self.menuBar()

        #####################################################################################
        # #? Setup Files menu
        files_menu = menubar.addMenu("Files")

        self.open_session_action = QAction("Open session...", self)
        self.save_session_action = QAction("Save session", self)
        self.save_session_as_action = QAction("Save session as...", self)
        # Ctrl+O, Ctrl+S, Ctrl+Shift+S (Cmd on macOS)
        self.open_session_action.setShortcut(QKeySequence.Open)
        self.save_session_action.setShortcut(QKeySequence.Save)
        self.save_session_as_action.setShortcut(QKeySequence.SaveAs)
        self.open_session_action.triggered.connect(self.open_session_signal.emit)
        self.save_session_action.triggered.connect(self.save_session_signal.emit)
        self.save_session_as_action.triggered.connect(self.save_session_as_signal.emit)
        files_menu.addAction(self.open_session_action)
        files_menu.addAction(self.save_session_action)
        files_menu.addAction(self.save_session_as_action)
        # theme, font size and the additional pressure toolbox are in the Settings
        # window (DESIGN.md §4); on macOS this action goes to the app menu, with Cmd+,
        files_menu.addSeparator()
        self.settings_action = QAction("Settings…", self)
        self.settings_action.setMenuRole(QAction.PreferencesRole)
        shortcuts = QKeySequence.keyBindings(QKeySequence.Preferences)
        self.settings_action.setShortcuts(shortcuts or [QKeySequence("Ctrl+,")])
        self.settings_action.triggered.connect(self.open_settings)
        files_menu.addAction(self.settings_action)

        #####################################################################################
        # #? View menu: the bottom panels (filled by _setup_docks)
        self.view_menu = menubar.addMenu("View")

        #####################################################################################
        # #? Exit button setup
        exit_menu = menubar.addMenu("Exit")

        exit_action = QAction(" Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)        # Ctrl+Q (Cmd+Q on macOS)
        exit_action.triggered.connect(self.close)
        exit_menu.addAction(exit_action)

    def _create_fit_controls(self):
        """Buttons of the spectrum card, the fit model selector and the spectrometer
        calibration controls (placed by _build_center and _build_inspector)."""
        self.fit_button = button("Fit", 32, role="soft-primary", icon_name="fit-peak",
                                 icon_role="act",
                                 tooltip="Fit the spectrum (in the fit range when it is on)")
        self.fit_button.clicked.connect(self.auto_fit)

        self.click_fit_button = button("Click-to-fit", 32, icon_name="crosshair",
                                       tooltip="Click near a peak on the spectrum to fit it")
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        self.click_fit_enabled = False

        # Fit range split button: use the range | edit it (DESIGN.md §1)
        self.fit_range_enable_button = button("Fit range", 32, icon_name="fit-range",
                                              tooltip="Restrict the fit to a range")
        self.fit_range_enable_button.setCheckable(True)
        self.fit_range_enable_button.clicked.connect(self.toggle_fit_range)
        self.fit_range_enabled = False

        self.fit_range_edit_button = Button(height=32, width=32)
        icons.set_icon(self.fit_range_edit_button, "pencil", "tx", 14, on_role="onac")
        self.fit_range_edit_button.setToolTip("Edit fit range (drag its edges on the plot)")
        self.fit_range_edit_button.setAccessibleName("Edit fit range")
        self.fit_range_edit_button.setCheckable(True)
        self.fit_range_edit_button.setEnabled(False)        # while the fit range is off
        self.fit_range_edit_button.clicked.connect(self.toggle_fit_range_edit)
        self.fit_range_edit_enabled = False

        self.fit_model_combo = QComboBox()
        self.fit_model_combo.setObjectName("fit_model_combo")
        self.fit_model_combo.setMinimumWidth(100)
        self.fit_model_combo.setFixedHeight(36)
        # colour dot of each model's kind in the list (not in the closed selector)
        self.fit_model_combo.setItemDelegate(ModelItemDelegate(
            lambda name: getattr(self, "_fit_models", {}).get(name), self.fit_model_combo))

        # Background: Auto / Manual / None, an exclusive segmented control
        self.CHullBg_button = Button("Auto", 28)
        self.CHullBg_button.setToolTip("Subtract an automatic (convex hull) background")
        self.CHullBg_button.clicked.connect(lambda: self._background_chosen("auto"))
        self.ManualBg_button = Button("Manual", 28)
        self.ManualBg_button.setToolTip(
            "Click background points on the spectrum, then Manual again to subtract")
        self.ManualBg_button.clicked.connect(self.toggle_ManualBg)
        self.click_ManualBg_enabled = False
        self.ManualBg_points = []
        self.temp_bg = None
        self.ResetBg_button = Button("None", 28)
        self.ResetBg_button.setToolTip("Remove the subtracted background")
        self.ResetBg_button.clicked.connect(lambda: self._background_chosen("none"))
        self._bg_kinds = {}         # spectrum id -> "auto" / "manual", chosen in this session
        self._bg_obj = None         # spectrum shown, and whether it has a background
        self._bg_applied = False

        self.smoothing_factor = QSpinBox()      # smoothing window, in points
        self.smoothing_factor.setRange(1, 999)
        self.smoothing_factor.setValue(1)
        self.smoothing_factor.setButtonSymbols(QSpinBox.NoButtons)
        self.smoothing_factor.setToolTip("Smoothing window, in points")
        self.smoothing_minus = Button("−", 30, 28)
        self.smoothing_minus.setToolTip("Less smoothing")
        self.smoothing_plus = Button("+", 30, 28)
        self.smoothing_plus.setToolTip("More smoothing")

        # derivative pane toggle, a pill in the legend row
        self.Derivative_button = button("dI/dλ", 28, role="pill", icon_name="derivative",
                                        tooltip="Show the derivative under the spectrum")
        self.Derivative_button.setCheckable(True)
        self.Derivative_button.clicked.connect(self.toggle_derivative)
        self.Derivative_enabled = False

        # spectrometer calibration (inspector)
        self.LoadSpectro_button = QPushButton("Load…", self)
        self.LoadSpectro_button.setToolTip("Load a spectrometer calibration file")
        self.Spectro_use_button = QCheckBox(self)
        self.Spectro_use_button.setToolTip("Use spectrometer calibration")
        self.Spectro_use_button.setAccessibleName("Use spectrometer calibration")
        self.Spectro_filename_label = ElidedLabel("No calibration file", self)

        # fit -> pressure log (center), and point from the parameters alone (inspector)
        self.add_fitted_button = button("Add fit to log", 40, primary=True, icon_name="plus",
                                        tooltip="Add the fitted point to the pressure log, "
                                                "with the membrane pressure Pm")
        self.add_fitted_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_fitted_button.clicked.connect(self.add_current_fit)

        self.PToolbox_toTable_button = button(
            "Add point to log", 36, role="accent", icon_name="plus", icon_role="act",
            tooltip="Add a point from the λ, T and P values alone (no spectrum)")
        self.PToolbox_toTable_button.clicked.connect(self.add_point_to_log)

    def _create_plots(self):
        self.splitter = DashedSplitter(Qt.Vertical)
        self.splitter.setObjectName("PlotSplitter")
        self.splitter.setHandleWidth(9)             # dashed line between spectrum and dI/dx

        # #? Actual spectral data
        self.data_widget = pg.PlotWidget()
        styles = self._label_styles()
        self.data_widget.setLabel("bottom", "Spectral unit", **styles)
        self.data_widget.setLabel("left", "Intensity", **styles)
        self.data_scatter = pg.ScatterPlotItem(symbol='o', size=3, pen=None)
        self.data_widget.addItem(self.data_scatter)
        self.data_fit_pen = pg.mkPen(color=self.fit_color, width=2)
        self.data_fit_line = pg.PlotDataItem(name='Fit',pen=self.data_fit_pen,)
        # manual background being picked: points and spline (accent, set by _style_plots)
        self.data_bg_scatter = pg.ScatterPlotItem(symbol='s', size=8, pen=None)
        self.data_bg_line = pg.PlotDataItem(name='Bg')
        # dashed marker at the fitted peak or edge, with its label (no plot title:
        # the pressure is in the card above)
        self.data_edge_marker = pg.InfiniteLine(pos=None, angle=90, movable=False)
        self.peak_label = PeakLabel()
        self.data_widget.plotItem.vb.sigRangeChanged.connect(
            lambda *_: self.peak_label.place(self.data_widget.plotItem.vb))

        self.data_widget.setMenuEnabled(False)
        self.data_scatter.scene().sigMouseClicked.connect(self.data_plot_click)

        self.fit_range_selector = ResizeOnlyLinearRegion(movable=False)
        self.fit_range_selector_edited = False
        self.fit_range_selector.sigRegionChangeFinished.connect(self.fit_range_changed)
        self.fit_range_overlay = FitRangeEditOverlay(self.data_widget, self.fit_range_selector)

        #####################################################################################
        # #? Setup derivative plotting section
        self.deriv_widget = pg.PlotWidget()
        # no axis titles (the spectrum's x title is just above): a small "dI/dλ" at the
        # top left, and raw values without an SI prefix
        self.deriv_widget.getAxis("left").enableAutoSIPrefix(False)
        self._deriv_symbol = "x"

        self.deriv_scatter = pg.ScatterPlotItem(symbol='o', size=3, pen=None)
        self.deriv_widget.addItem(self.deriv_scatter)
        self.deriv_zero_line = pg.InfiniteLine(pos=0, angle=0, movable=False)
        self.deriv_widget.addItem(self.deriv_zero_line, ignoreBounds=True)
        self.deriv_edge_marker = pg.InfiniteLine(pos=None, angle=90, movable=False)

        self.deriv_widget.setMenuEnabled(False)
        self.deriv_scatter.scene().sigMouseClicked.connect(self.deriv_plot_click)

        self.splitter.addWidget(self.data_widget)
        self.splitter.addWidget(self.deriv_widget)
        self.splitter.setSizes([300, 150])          # derivative ≈ 1/3 of the height
        self.splitter.widget(1).hide()

    def _build_center(self):
        """Center column (DESIGN.md §1): the fitted pressure card, then the spectrum card
        (fit toolbar, legend row, spectrum and derivative plots)."""
        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)

        # file of the shown spectrum (and the file list messages), in the pills row
        self.current_file_label = Pill("No file selected", muted=True)
        self.pressure_card = PressureCard(self.ptoolbox.Pm_spinbox, self.add_fitted_button,
                                          self.current_file_label)
        layout.addWidget(self.pressure_card)

        spectrum_card = Card(spacing=0)
        spectrum_card.body.setContentsMargins(0, 0, 0, 0)
        self.background_label = label("Background", "caption")
        self.smoothing_label = label("Smoothing", "caption")
        self.bg_segment = Segmented([self.CHullBg_button, self.ManualBg_button,
                                     self.ResetBg_button])
        self.bg_segment.check(self.ResetBg_button)
        stepper = Stepper(self.smoothing_factor, self.smoothing_minus, self.smoothing_plus)
        self.fit_toolbar = FitToolbar(
            [self.fit_button, self.click_fit_button,
             SplitButton(self.fit_range_enable_button, self.fit_range_edit_button),
             divider(length=22), self.background_label, self.bg_segment,
             divider(length=22), self.smoothing_label, stepper, 1],
            optional_labels=[self.background_label, self.smoothing_label],
            compact_buttons=[self.click_fit_button, self.fit_range_enable_button])
        spectrum_card.body.addWidget(self.fit_toolbar)
        self.legend_row = LegendRow(self.Derivative_button)
        spectrum_card.body.addWidget(self.legend_row)
        plots = QWidget()
        plots_layout = QVBoxLayout(plots)
        plots_layout.setContentsMargins(4, 4, 12, 8)
        plots_layout.addWidget(self.splitter)
        spectrum_card.body.addWidget(plots, 1)
        layout.addWidget(spectrum_card, 1)

        # no spectrum loaded: one card with the drop zone instead (DESIGN.md §4b)
        self.empty_center = EmptyCenter()
        self.empty_center.add_button.clicked.connect(self.file_list_widget.add_button.click)
        self.empty_center.folder_button.clicked.connect(
            self.file_list_widget.selectdir_button.click)
        self.empty_center.session_button.clicked.connect(self.open_session_signal.emit)
        self.empty_center.demo_button.clicked.connect(self.demo_requested.emit)
        self.ptoolbox.calib_shown.connect(self._update_empty_glyph)
        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(self.empty_center)
        self.center_stack.addWidget(center)
        self._work_center = center
        model = self.file_list_widget.list_widget.model()
        for signal in (model.rowsInserted, model.rowsRemoved, model.modelReset):
            signal.connect(self._update_center_page)
        self._update_center_page()
        self.setAcceptDrops(True)
        return self.center_stack

    def _update_center_page(self, *_args):
        empty = self.file_list_widget.is_empty()
        self.center_stack.setCurrentWidget(self.empty_center if empty else self._work_center)

    def _update_empty_glyph(self, *_args):
        self.empty_center.set_color(theme.calib_color(self.ptoolbox._calib))

    @staticmethod
    def _dropped_paths(mime):
        if not mime.hasUrls():
            return []
        # Qt gives '/' separators on Windows too: native paths, as from the file dialog
        return [os.path.normpath(url.toLocalFile()) for url in mime.urls()
                if url.isLocalFile() and os.path.isfile(url.toLocalFile())]

    def dragEnterEvent(self, event):
        if self._dropped_paths(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = self._dropped_paths(event.mimeData())
        if paths:
            event.acceptProposedAction()
            remember_dir("spectra", paths[0])
            self.files_dropped.emit(paths)

    def _build_inspector(self):
        """Right column: Pressure gauge, Parameters and Spectrometer cards."""
        self.ptoolbox.fit_model_slot.addWidget(label("Fit model", "field"))
        self.ptoolbox.fit_model_slot.addWidget(self.fit_model_combo)
        self.ptoolbox._style_calib_combo()
        self.ptoolbox.add_point_slot.addWidget(self.PToolbox_toTable_button)
        # Tab follows the cards: calibration, fit model, then the parameters
        QWidget.setTabOrder(self.ptoolbox.calibration_combo, self.fit_model_combo)
        QWidget.setTabOrder(self.fit_model_combo, self.ptoolbox.x_spinbox)

        spectro_card = Card("Spectrometer", spacing=10)
        self.Spectro_filename_label.setProperty("role", "muted-13")
        spectro_card.body.addLayout(hbox(self.Spectro_filename_label, 1, self.LoadSpectro_button))
        use_label = label("Use spectrometer calibration", "muted-13")
        use_label.setBuddy(self.Spectro_use_button)
        spectro_card.body.addLayout(hbox(use_label, 1, self.Spectro_use_button))

        inspector = QWidget()
        inspector.setObjectName("Inspector")
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP)
        layout.addWidget(self.ptoolbox)
        layout.addWidget(spectro_card)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName("InspectorScroll")
        scroll.setFocusPolicy(Qt.NoFocus)           # Tab goes to its fields, not to it
        scroll.setWidget(inspector)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setAutoFillBackground(False)
        inspector.setAutoFillBackground(False)
        scroll.setMinimumWidth(INSPECTOR_MIN_WIDTH)
        return scroll

    def _setup_docks(self):
        """Pressure log (≈ 70 %) and P vs Pm (≈ 30 %) side by side under the workspace
        (DESIGN.md §1, "Bottom dock area")."""
        self.log_dock = PanelDock("Pressure log", "PressureLogDock", self.PvPmTableWindow,
                                  "Hide the pressure log")
        self.log_dock.add_header_widgets(self.PvPmTableWindow.header_widgets,
                                         self.PvPmTableWindow.header_actions)
        self.plot_dock = PanelDock("P vs Pm", "PvPmDock", self.PvPmPlotWindow,
                                   "Hide the P vs Pm plot", body_padding=8)
        self.plot_dock.add_header_widgets([self.PvPmPlotWindow.legend_label])
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)
        self.splitDockWidget(self.log_dock, self.plot_dock, Qt.Horizontal)
        self._docks = (self.log_dock, self.plot_dock)
        for dock in self._docks:
            action = dock.toggleViewAction()
            action.setText(dock.windowTitle())
            self.view_menu.addAction(action)
            dock.visibilityChanged.connect(self._schedule_panel_update)
            dock.topLevelChanged.connect(self._schedule_panel_update)
        self._default_dock_sizes()

    def _default_dock_sizes(self):
        height = self.height() if self.height() > 0 else DEFAULT_HEIGHT
        width = self.width() if self.width() > 0 else DEFAULT_WIDTH
        self.resizeDocks([self.log_dock], [int(height * DOCK_HEIGHT_FRACTION)], Qt.Vertical)
        self.resizeDocks([self.log_dock, self.plot_dock],
                         [int(width * LOG_WIDTH_FRACTION), int(width * (1 - LOG_WIDTH_FRACTION))],
                         Qt.Horizontal)

    def _schedule_panel_update(self, *_args):
        # after Qt has laid the docks out
        QTimer.singleShot(0, self._update_panels)

    def _update_panels(self):
        """Workspace bottom gap and dock height limits after a dock is shown, hidden,
        undocked or docked."""
        if sip.isdeleted(self):
            return
        docked = [d for d in self._docks if not d.isHidden() and not d.isFloating()]
        margins = self.workspace_layout.contentsMargins()
        bottom = 0 if docked else GAP
        if margins.bottom() != bottom:
            self.workspace_layout.setContentsMargins(GAP, GAP, GAP, bottom)
        self._limit_dock_heights()
        for dock in self._docks:
            dock.update_margins()

    def _limit_dock_heights(self):
        """Docked panels take at most half the window height: the spectrum keeps the
        rest. Floating panels keep their own size."""
        limit = max(MIN_DOCK_HEIGHT, int(self.height() * MAX_DOCK_HEIGHT_FRACTION))
        for dock in self._docks:
            dock.setMaximumHeight(QWIDGETSIZE_MAX if dock.isFloating() else limit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_docks"):
            self._limit_dock_heights()
        # widened or heightened by its content: Qt grows a window to its layout's new
        # minimum size, which can push it off the screen (macOS: off its right edge).
        # Such a resize lands exactly on the minimum; a resize by the user does not.
        old, new = event.oldSize(), event.size()
        if old.isValid() and ((new.width() > old.width() and new.width() == self.minimumWidth())
                              or (new.height() > old.height()
                                  and new.height() == self.minimumHeight())):
            self._screen_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_shown_once", False):
            self._shown_once = True
            if not self._layout_restored:
                self._default_dock_sizes()      # with the final window size
            else:
                # saved on a screen that may no longer be there (external display)
                self._screen_timer.start()
            self._schedule_panel_update()
            # open at the last close (Settings › General › Additional pressure toolbox)
            if S.setting("additional_toolbox"):
                QTimer.singleShot(0, lambda: self.set_additional_toolbox_visible(True))

    def _connect_top_bar(self):
        bar = self.top_bar
        bar.open_button.clicked.connect(self.open_session_signal.emit)
        bar.save_button.clicked.connect(self.save_session_signal.emit)
        bar.export_button.clicked.connect(self.PvPmTableWindow.save_data_to_csv)
        bar.theme_button.clicked.connect(self.toggle_theme)
        bar.settings_button.clicked.connect(self.open_settings)
        # panel toggles show / hide the docks where they were (docked or floating), and
        # follow them when they are hidden with their × or the View menu
        for dock, toggle in ((self.log_dock, bar.log_toggle), (self.plot_dock, bar.plot_toggle)):
            action = dock.toggleViewAction()
            # the action is only checked once the window is shown
            toggle.setChecked(not dock.isHidden())
            toggle.clicked.connect(dock.setVisible)
            action.toggled.connect(toggle.setChecked)

    # --- window geometry and panel layout, kept between launches ---------------------------

    def _restore_layout(self):
        settings = app_settings()
        geometry = settings.value("window/geometry")
        state = settings.value("window/state")
        if geometry is None or state is None:
            return False
        if not (self.restoreGeometry(geometry) and self.restoreState(state, LAYOUT_VERSION)):
            return False
        return True

    def save_layout(self):
        settings = app_settings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState(LAYOUT_VERSION))

    # session shown in the top bar (set by the presenter)
    def set_version(self, version):
        self.top_bar.set_version(version)

    def set_session_name(self, name):
        self.top_bar.set_session_name(name)

    def set_save_status(self, kind, when=None):
        self.top_bar.set_save_status(kind, when)

    #####################################################################################
    # ? Main window methods

    def _place_window(self):
        """Fit the main window in the available area of the screen (small laptop
        screens too); a window that cannot shrink to the screen starts at its edge."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        self._fit_in(screen.availableGeometry(), centre=True)

    def _fit_in(self, area, centre):
        """Size the window to `area` (never below its layout's minimum, which Qt applies
        anyway) and place it inside: centred, or moved by as little as possible."""
        frame, inner = self.frameGeometry(), self.geometry()
        frame_w, frame_h = frame.width() - inner.width(), frame.height() - inner.height()
        minimum = self.minimumSizeHint().expandedTo(self.minimumSize())
        width = max(min(inner.width(), area.width() - frame_w), minimum.width())
        height = max(min(inner.height(), area.height() - frame_h), minimum.height())
        if centre:
            x = area.left() + (area.width() - width - frame_w) // 2
            y = area.top() + (area.height() - height - frame_h) // 2
        else:
            x = min(frame.left(), area.left() + area.width() - width - frame_w)
            y = min(frame.top(), area.top() + area.height() - height - frame_h)
        x, y = max(area.left(), x), max(area.top(), y)
        self.setGeometry(x + inner.left() - frame.left(), y + inner.top() - frame.top(),
                         width, height)

    def _keep_on_screen(self):
        """Bring the window back inside the screen if part of it is off every screen
        (a window spanning two screens is left alone)."""
        if (not self.isVisible() or self.isMinimized() or self.isMaximized()
                or self.isFullScreen()):
            return
        frame = self.frameGeometry()
        desktop = QRegion()
        for screen in QGuiApplication.screens():
            desktop += QRegion(screen.availableGeometry())
        if QRegion(frame).subtracted(desktop).isEmpty():
            return
        screen = (QGuiApplication.screenAt(frame.center())
                  or QGuiApplication.screenAt(frame.topLeft())
                  or QGuiApplication.primaryScreen())
        if screen is not None:
            self._fit_in(screen.availableGeometry(), centre=False)

    def closeEvent(self, event):
        if self.close_guard is not None and not self.close_guard():
            event.ignore()
            return
        self.save_layout()
        # shown again at the next launch if it is open now (Settings › General)
        S.set_setting("additional_toolbox", self.additional_toolbox_window.isVisible())
        # close the side windows owned by this main window (not every app window,
        # which recursed between main windows); floating panels close with it
        self.additional_toolbox_window.close()
        if self.settings_dialog is not None:
            self.settings_dialog.close()
        super().closeEvent(event)

    def toggle_theme(self):
        if theme.is_dark():
            self.switch_to_light()
        else:
            self.switch_to_dark()
        if self.settings_dialog is not None and self.settings_dialog.isVisible():
            self.settings_dialog.set_theme_mode(S.setting("theme"))

    def switch_to_dark(self):
        self._apply_theme(dark=True)

    def switch_to_light(self):
        self._apply_theme(dark=False)

    def set_theme_mode(self, mode):
        """'light', 'dark' or 'system' (Settings › General › Theme)."""
        S.set_setting("theme", mode)
        dark = theme.mode_is_dark(mode)
        if dark != theme.is_dark():
            self._apply_theme(dark, remember=False)

    def _apply_theme(self, dark, remember=True):
        """remember: store the theme as the user's choice (the top-bar toggle); not for
        a theme that follows the system."""
        try:
            # app-wide, so that every window and dialog follows the theme
            theme.apply_theme(dark=dark)
        except OSError as exc:
            logger.warning("Could not load the theme stylesheet: %s", exc)
            theme.set_current(dark)
        if remember:
            S.set_setting("theme", "dark" if dark else "light")

        # pyqtgraph plots are not styled by the Qt stylesheet
        self._style_plots()
        # icons and other colours drawn in code
        self.top_bar.set_dark(dark)
        icons.refresh()
        self.top_bar.restyle()
        self.file_list_widget.restyle()
        self.pressure_card.restyle()
        self.recovery_banner.restyle()
        self._style_fit_model_combo()
        if self.settings_dialog is not None:
            self.settings_dialog.restyle()
        self._update_empty_glyph()
        for dock in self._docks:
            dock.restyle()

        for themed in (self.ptoolbox, self.additional_toolbox_window, self.PvPmPlotWindow):
            if dark:
                themed.set_dark_mode()
            else:
                themed.set_light_mode()

        self.theme_switched.emit()

    def _style_plots(self):
        """Colours of the spectrum and derivative plots from the theme tokens
        (DESIGN.md §6). The fit line and markers follow the plotted calibration."""
        t = theme.tokens()
        self.plot_label_color = t["mu"]
        for widget, scatter in ((self.data_widget, self.data_scatter),
                                (self.deriv_widget, self.deriv_scatter)):
            scatter.setBrush(pg.mkBrush(theme.qcolor(t["dot"])))
            theme.style_axes(widget, t)
        # fit range: soft accent band with accent edges
        self.fit_range_selector.setBrush(pg.mkBrush(theme.qcolor(t["acs"])))
        hover = theme.qcolor(t["acs"])
        hover.setAlphaF(min(1.0, hover.alphaF() * 1.8))
        self.fit_range_selector.setHoverBrush(pg.mkBrush(hover))
        self._style_fit_range()
        self.fit_range_overlay.restyle()
        # fitted peak / edge: dashed marker and label; derivative zero line
        for marker in (self.data_edge_marker, self.deriv_edge_marker):
            marker.setPen(dashed_marker_pen())
        self.peak_label.restyle()
        self.deriv_zero_line.setPen(pg.mkPen(theme.qcolor(t["grid"]), width=1))
        self.data_bg_line.setPen(pg.mkPen(theme.qcolor(t["ac"]), width=2))
        self.data_bg_scatter.setBrush(pg.mkBrush(theme.qcolor(t["ac"])))
        self._set_deriv_title()
        self.legend_row.restyle()
        self.update_plot_fonts()
        self._set_fit_color(self.fit_color)

    def _style_fit_range(self):
        """Band edges: 1 px, 2 px while they are edited (dragged)."""
        accent = theme.qcolor(theme.tokens()["ac"])
        width = 2 if self.fit_range_edit_enabled else 1
        for line in self.fit_range_selector.lines:
            line.setPen(pg.mkPen(accent, width=width))
            line.setHoverPen(pg.mkPen(accent, width=width + 1))

    def _set_fit_color(self, color):
        self.fit_color = color
        self.data_fit_pen = pg.mkPen(color=color, width=2)
        self.data_fit_line.setPen(self.data_fit_pen)
        self.legend_row.set_fit_color(color)

    def populate_fit_models_combo(self, model_dict):
        if model_dict is not None:
            # coloured by kind of model: Double red, Single green, Raman edge grey
            self._fit_models = dict(model_dict)
            self.fit_model_combo.addItems(model_dict.keys())
            self.fit_model_combo.currentIndexChanged.connect(self._style_fit_model_combo)
            self._style_fit_model_combo()
        else:
            raise ImportError('Error loading fit models.')

    def _style_fit_model_combo(self, *_args):
        """Tint of the selected model's kind (the `model` property picks the generated
        rules of the stylesheet, theme._selector_rules) and a colour dot per item."""
        models = getattr(self, "_fit_models", {})
        combo = self.fit_model_combo
        family = theme.model_family(models.get(combo.currentText())) or ""
        if combo.property("model") != family:
            combo.setProperty("model", family)
            combo.style().unpolish(combo)
            combo.style().polish(combo)


    def set_current_point(self, obj_id):
        """The point shown (selected spectrum or recalled log entry): its log row is
        highlighted and its P vs Pm marker ringed (DESIGN.md §1)."""
        self.PvPmTableWindow.table_widget.set_current_id(obj_id)
        self.PvPmPlotWindow.set_current_id(obj_id)

    def add_current_fit(self):
        self.add_current_fit_signal.emit(None)

    def prompt_fit_pm(self, current_pm):
        """Pm of a fit added to the log: the Pm field of the fitted pressure card, next
        to "Add fit to log" (it replaced the Pm dialog)."""
        self.ptoolbox.Pm_spinbox.interpretText()        # text typed without Enter
        return self.ptoolbox.Pm_spinbox.value()

    def add_point_to_log(self):
        """"Add point to log" (Parameters card): asks for Pm, then the presenter adds
        a point from the λ, T and P values alone (DESIGN.md §1)."""
        toolbox = self.ptoolbox
        calib = toolbox._calib
        symbol, unit = x_symbol(calib), x_unit(calib)
        summary = (f"{calib.name if calib is not None else ''} · "
                   f"{symbol} {toolbox.x_spinbox.value():.3f} {unit} · "
                   f"T {toolbox.T_spinbox.value():.1f} K → "
                   f'<span style="font-family:{theme.mono_family()}; font-weight:{theme.qt5_weight(600)}; '
                   f'color:{theme.tokens()["tx"]}">P {toolbox.P_spinbox.value():.3f} GPa</span>')
        pm = self.prompt_point_pm(summary, toolbox.Pm_spinbox.value())
        if pm is None:
            return
        was_blocked = toolbox.Pm_spinbox.blockSignals(True)
        toolbox.Pm_spinbox.setValue(pm)
        toolbox.Pm_spinbox.blockSignals(was_blocked)
        toolbox.PmChanged.emit(pm)              # the presenter's copy of the toolbox
        self.add_point_requested.emit()

    def prompt_point_pm(self, summary, current_pm):
        """Pm of a point added from the parameters, None if cancelled."""
        dialog = AddPointDialog(summary, current_pm, parent=self)
        if dialog.exec_():
            return dialog.value()
        return None

    def toggle_derivative(self, checked=None):
        """Show / hide the derivative under the spectrum (the dI/dλ pill)."""
        self.Derivative_enabled = not self.Derivative_enabled
        self.splitter.widget(1).setVisible(self.Derivative_enabled)
        self.Derivative_button.setChecked(self.Derivative_enabled)

    def toggle_fit_range(self):
        if self.fit_range_enabled:
            self.data_widget.removeItem(self.fit_range_selector)
            self.fit_range_edit_button.setChecked(False)
            self.turn_off_fit_range_edit()
            self.fit_range_edit_enabled = False
        else:
            # Do not let the selector item influence ViewBox auto-range.
            self.data_widget.addItem(self.fit_range_selector, ignoreBounds=True)
        self.fit_range_enabled = not self.fit_range_enabled
        # editing needs the range: the pencil is disabled while it is off
        self.fit_range_edit_button.setEnabled(self.fit_range_enabled)
        self.legend_row.show_range(self.fit_range_enabled)

    def toggle_fit_range_edit(self):
        if self.fit_range_enabled:
            if self.fit_range_edit_enabled:
                self.turn_off_fit_range_edit()
            else:
                self.turn_on_fit_range_edit()
        else:
            self.fit_range_edit_button.setChecked(False)
            self.turn_off_fit_range_edit()
        self.fit_range_edit_button.setChecked(self.fit_range_edit_enabled)

    def turn_on_fit_range_edit(self):
        if self.fit_range_enabled:
            self.fit_range_selector.setMovable(True)
            self.fit_range_edit_enabled = True
            self.fit_range_overlay.show(True)
            self._style_fit_range()

    def turn_off_fit_range_edit(self):
        if self.fit_range_enabled:
            self.fit_range_selector.setMovable(False)
            self.fit_range_edit_enabled = False
        self.fit_range_overlay.show(False)
        self._style_fit_range()

    def fit_range_changed(self):
        self.fit_range_selector_edited = True

    def get_file_via_dialog(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Text and ASC files (*.txt *.asc);;All Files (*)")
        if last_dir("spectra"):
            file_dialog.setDirectory(last_dir("spectra"))

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                remember_dir("spectra", selected_files[0])
            return selected_files
        else:
            return None

    def get_save_session_filename_dialog(self):
        options = QFileDialog.Options()
        file_name, file_type = QFileDialog.getSaveFileName(
            self,
            "Save session",
            last_dir("sessions"),
            "Session Files (*.json);;All Files (*)",
            options=options,
        )
        if file_type == "Session Files (*.json)":
            if file_name and not file_name.endswith(".json"):
                file_name += ".json"
        remember_dir("sessions", file_name)
        return file_name or None

    def get_open_session_filename_dialog(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open session",
            last_dir("sessions"),
            "Session Files (*.json);;All Files (*)",
            options=options,
        )
        remember_dir("sessions", file_name)
        return file_name or None

    def select_directory_from_dialog(self):
        options = QFileDialog.Options()
        # starts in the last acquisition folder, which is not selected automatically:
        # "Load latest" must not load from a previous experiment's folder
        dir_name = QFileDialog.getExistingDirectory(
            self, "Select Directory", last_dir("acquisition"), options=options
        )
        remember_dir("acquisition", dir_name)
        if dir_name:
            self.file_list_widget.set_directory(dir_name)
        return dir_name

    def _set_deriv_title(self):
        self.deriv_widget.setTitle(f"dI/d{self._deriv_symbol}", justify="left",
                                   color=theme.qcolor(theme.tokens()["mu"]).name(), size="12px")

    def set_x_axis(self, calib):
        """x of the spectrum plots in the calibration's symbol and unit: axis title,
        fit range label, dI/dλ toggle and derivative title."""
        symbol, unit = x_symbol(calib), x_unit(calib)
        self.data_widget.setLabel("bottom", f"{symbol} ({unit})")
        self.fit_range_overlay.unit = unit
        self.Derivative_button.setText(f" dI/d{symbol}")
        self._deriv_symbol = symbol
        self._set_deriv_title()

    def plot_data(self, x, y, buffer, preserve_view=False):
        self._clear_fit_items()
        calib = buffer.calib
        self._plot_calib = calib
        self.set_x_axis(calib)
        # not fitted until plot_fit: "—" in the fitted pressure card
        self.pressure_card.clear(calib)
        # "fit" tag on λ: set again by plot_fit if Parameters shows this spectrum's fit
        self.ptoolbox.set_x_fitted(False)
        # the fit line of this spectrum is drawn in its calibration's colour
        self._set_fit_color(theme.calib_color(calib))

        self.data_scatter.setData(x, y)
        if not preserve_view:
            self.data_widget.autoRange()

        # derivative data
        # along increasing x, as the Raman edge search (files can store x decreasing)
        order = np.argsort(x, kind="stable")
        dI = np.empty(len(y))
        dI[order] = gaussian_filter1d(np.asarray(y)[order], mode="nearest", sigma=1, order=1)
        self.deriv_scatter.setData(x, dI)
        if not preserve_view:
            self.deriv_widget.autoRange()

    def clear_spectrum(self):
        """No spectrum selected (deleted, or a session opened without one): empty plots
        instead of the previous spectrum."""
        self._clear_fit_items()
        self.data_scatter.setData([], [])
        self.deriv_scatter.setData([], [])
        self.pressure_card.clear(getattr(self, "_plot_calib", None))
        self.ptoolbox.set_x_fitted(False)
        self.show_background(None, False)
        self.set_current_point(None)

    def _clear_fit_items(self):
        for widget, item in ((self.data_widget, self.data_edge_marker),
                             (self.deriv_widget, self.deriv_edge_marker),
                             (self.data_widget, self.data_fit_line),
                             (self.data_widget, self.peak_label)):
            widget.removeItem(item)
        self.data_fit_line.setData([], [])

    def toggle_click_fit(self):
        self.click_fit_enabled = not self.click_fit_enabled

    def data_plot_click(self, event):
        if self._is_zoom_click(event):
            self._zoom(self.data_widget, self.data_scatter)
        elif event.button() == Qt.LeftButton:
            if self.click_fit_enabled:
                self.click_to_fit(event, 'data')
            elif self.click_ManualBg_enabled:
                self.set_ManualBg(event)

    def deriv_plot_click(self, event):
        if self._is_zoom_click(event):
            self._zoom(self.deriv_widget, self.deriv_scatter)
        elif event.button() == Qt.LeftButton:
            if self.click_fit_enabled:
                self.click_to_fit(event, 'deriv')

    @staticmethod
    def _is_zoom_click(event):
        # right click, or ctrl + left click
        return event.button() == Qt.RightButton or (
            event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier)

    @staticmethod
    def _zoom(widget, scatter):
        """Zoom out by 2, or back to the full spectrum once zoomed out past it."""
        view_range = np.array(widget.plotItem.vb.viewRange()) * 2
        curve_x = scatter.getData()[0]
        if (view_range[0][1] - view_range[0][0]) > np.max(curve_x) - np.min(curve_x):
            widget.autoRange()
        else:
            widget.plotItem.vb.scaleBy((2, 2))

    def auto_fit(self):
        self.start_auto_fit_signal.emit(None)

    def click_to_fit(self, mouseClickEvent, window):
        if self.click_fit_enabled:
            scene_coords = mouseClickEvent.scenePos()
            widget = self.data_widget if window == 'data' else self.deriv_widget
            vb = widget.plotItem.vb
            # ignore clicks outside the plot area (axes, margins)
            if not vb.sceneBoundingRect().contains(scene_coords):
                return
            click_point = vb.mapSceneToView(scene_coords)

            self.fit_from_click_signal.emit(click_point.x())

            self.toggle_click_fit()
            self.click_fit_button.setChecked(False)

    @staticmethod
    def _fitted_position(fit_model, fit_result):
        """Fitted peak position (peak models) or edge position, None if unknown."""
        opti = fit_result.get("opti") if fit_result is not None else None
        if opti is None:
            return None
        if fit_model.type == "peak":
            return float(opti[fit_model.position_index(opti)])
        return float(np.ravel(opti)[0])

    def plot_fit(self, P, fit_model, fit_result, x, y, P_err=None):
        """Fit line (peak models), dashed marker at the fitted peak / edge with its label,
        and the value in the fitted pressure card (without the fit uncertainty,
        DESIGN.md §5)."""
        self._clear_fit_items()
        if self.ptoolbox.shows_fit(fit_model, fit_result):
            self.ptoolbox.set_x_fitted(True)

        if fit_model.type == "peak":
            # drawn over the whole spectrum, not only the fitting range
            x = np.asarray(x)
            self.data_fit_line.setData(x, fit_model.func(x, *fit_result["opti"]))
            self.data_widget.addItem(self.data_fit_line)
        elif fit_model.type != "edge":
            logger.warning("Plot of fit type %r not implemented", fit_model.type)
            return

        calib = getattr(self, "_plot_calib", None)
        symbol, unit = x_symbol(calib), x_unit(calib)
        position = self._fitted_position(fit_model, fit_result)
        position_text = f"{symbol} {position:.3f} {unit}" if position is not None else ""
        if position is not None:
            for widget, marker in ((self.data_widget, self.data_edge_marker),
                                   (self.deriv_widget, self.deriv_edge_marker)):
                marker.setValue(position)
                widget.addItem(marker, ignoreBounds=True)
            name = peak_name(calib, fit_model)
            title = f"{name} · {position:.3f} {unit}" if name else position_text
            self.peak_label.set_content(position, title, f"P {P:.3f} GPa")
            self.data_widget.addItem(self.peak_label, ignoreBounds=True)
            self.peak_label.place(self.data_widget.plotItem.vb)
        self.pressure_card.set_fit(P, fit_model.name, position_text)
        self.file_list_widget.refresh()            # fitted P and dot of the row

    def ask_save_changes(self, action="closing"):
        """'save', 'discard' or 'cancel'."""
        return dialogs.ask_save_changes(self, action)

    def show_recovery_banner(self, when):
        """Offer to recover a backup (banner under the top bar; it replaced the startup
        message box). The presenter is told through recovery_banner's signals."""
        self.recovery_banner.show_backup(when)

    def hide_recovery_banner(self):
        self.recovery_banner.hide()

    def fit_error_popup_window(self, reason=""):
        # why, e.g. not enough points in the fit range (it was only in the log)
        dialogs.show_error(self, "The fit failed", reason, window_title="Fit error")

    def set_additional_toolbox_visible(self, visible):
        self.additional_toolbox_window.setVisible(visible)
        if visible:
            self.additional_toolbox_window.raise_()

    # --- Settings window (DESIGN.md §4) ---------------------------------------------------------

    @staticmethod
    def _optional_log_columns():
        return [(key, header, shown) for key, header, _numeric, shown in LOG_COLUMNS
                if key != "#"]

    def open_settings(self):
        """Gear button, Files › Settings… (Cmd+, on macOS). One window: opened again,
        it comes to the front; once closed, it reopens with the values in use."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self._optional_log_columns(), self)
            self.settings_dialog.saved.connect(self.apply_settings)
        dialog = self.settings_dialog
        if not dialog.isVisible():
            dialog.set_version(self.top_bar.app_version)
            dialog.log_dir = log_setup.log_dir()
            dialog.log_folder_button.setEnabled(dialog.log_dir is not None)
            dialog.set_values(self.current_settings())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def current_settings(self):
        """Values in use, as shown in the Settings window."""
        table = self.PvPmTableWindow.table_widget
        return {
            "theme": S.setting("theme"),
            "font_size": self.plot_font_px,
            "additional_toolbox": self.additional_toolbox_window.isVisible(),
            "autosave": S.setting("session/autosave"),
            "autosave_interval_s": S.setting("session/autosave_interval_s"),
            "offer_recovery": S.setting("session/offer_recovery"),
            "columns": {key: table.is_column_shown(key)
                        for key, _header, _shown in self._optional_log_columns()},
            "debug": log_setup.is_debug(),
        }

    def apply_settings(self, values):
        """Save in the Settings window: apply what changed and store every value."""
        self.set_theme_mode(values["theme"])
        if values["font_size"] != self.plot_font_px:
            set_app_font_size(values["font_size"])
            self.set_font_size(values["font_size"])
        S.set_setting("font_size", values["font_size"])
        self.set_additional_toolbox_visible(values["additional_toolbox"])
        S.set_setting("additional_toolbox", values["additional_toolbox"])
        table = self.PvPmTableWindow.table_widget
        for key, shown in values["columns"].items():
            # only the changed ones: a column left as it is keeps its automatic
            # behaviour (T is shown when a temperature is not 298 K)
            if shown != table.is_column_shown(key):
                table.set_column_visible(key, shown)
        S.set_setting("session/autosave", values["autosave"])
        S.set_setting("session/autosave_interval_s", values["autosave_interval_s"])
        S.set_setting("session/offer_recovery", values["offer_recovery"])
        if values["debug"] != log_setup.is_debug():
            log_setup.set_debug(values["debug"])
            logger.info("Debug logging %s", "on" if values["debug"] else "off")
        S.set_setting("logging/debug", values["debug"])
        self.settings_saved.emit()

    def set_font_size(self, size):
        # pyqtgraph items and the PvPm table are not reached by the app stylesheet
        self.plot_font_px = size
        self.update_plot_fonts()
        self.PvPmTableWindow.table_widget.set_font_size(size)
        self.PvPmPlotWindow.set_font_size(size)

    def _label_styles(self):
        return theme.label_styles(self.plot_label_color, self.plot_font_px)

    def update_plot_fonts(self):
        styles = self._label_styles()
        # numbers in the mono font (DESIGN.md §2)
        tick_font = theme.mono_font(self.plot_font_px)
        for widget in (self.data_widget, self.deriv_widget):
            for side in ("left", "bottom"):
                axis = widget.getAxis(side)
                # setLabel without a text would hide the label
                widget.setLabel(side, axis.labelText, **styles)
                axis.setStyle(tickFont=tick_font)

    def toggle_ManualBg(self):
        """Manual background: a first click starts picking points on the spectrum, a
        second one subtracts the background through them (2 points or more)."""
        if not self.click_ManualBg_enabled:
            self.data_widget.addItem(self.data_bg_line)
            self.data_widget.addItem(self.data_bg_scatter)
            self.click_ManualBg_enabled = True
            self.legend_row.set_hint("Click background points, then Manual again to subtract")
            return
        bg = self.temp_bg if self.ManualBg_points else None
        self._end_manual_bg()
        if bg is not None:
            if self._bg_obj is not None:
                self._bg_kinds[self._bg_obj] = "manual"
            self.subtract_ManualBg_signal.emit(bg)
        else:
            self._show_background_state()       # nothing subtracted

    def _end_manual_bg(self):
        """Leave point picking, without subtracting anything."""
        if not self.click_ManualBg_enabled:
            return
        self.ManualBg_points = []
        self.temp_bg = None
        self.data_bg_line.setData([], [])
        self.data_bg_scatter.setData([], [])
        self.data_widget.removeItem(self.data_bg_line)
        self.data_widget.removeItem(self.data_bg_scatter)
        self.click_ManualBg_enabled = False
        self.legend_row.set_hint("")

    def _background_chosen(self, kind):
        """Auto or None clicked (before the presenter subtracts or removes it)."""
        self._end_manual_bg()
        if self._bg_obj is not None and kind == "auto":
            self._bg_kinds[self._bg_obj] = "auto"

    def show_background(self, obj_id, applied):
        """Background segment of the shown spectrum (set by the presenter): None when it
        has no background, else the kind chosen for it (none checked if unknown, e.g.
        from a session: backgrounds add up and their kind is not saved)."""
        if obj_id != self._bg_obj:
            self._end_manual_bg()
        self._bg_obj, self._bg_applied = obj_id, applied
        if not applied:
            self._bg_kinds.pop(obj_id, None)
        self._show_background_state()

    def _show_background_state(self):
        if not self._bg_applied:
            self.bg_segment.check(self.ResetBg_button)
            return
        kind = self._bg_kinds.get(self._bg_obj)
        self.bg_segment.check({"auto": self.CHullBg_button,
                               "manual": self.ManualBg_button}.get(kind))

    def set_ManualBg(self, mouseClickEvent):
        if self.click_ManualBg_enabled:
            scene_coords = mouseClickEvent.scenePos()
            vb = self.data_widget.plotItem.vb
            if not vb.sceneBoundingRect().contains(scene_coords):
                return
            click_point = vb.mapSceneToView(scene_coords)
            x_click, y_click = click_point.x(), click_point.y()
            self.ManualBg_points.append([x_click, y_click])
            self.plot_ManualBg()

    def plot_ManualBg(self):
        curve_data_x = self.data_scatter.getData()[0]

        temp = np.array(self.ManualBg_points)
        x_bg = temp[:, 0]
        y_bg = temp[:, 1]
        
        self.data_bg_scatter.setData(x_bg,y_bg)
        
        # sort bg points, dropping duplicate x (the spline needs strictly increasing x)
        x_bg, unique_idx = np.unique(x_bg, return_index=True)
        y_bg = y_bg[unique_idx]

        # spline through the clicked points, flat beyond the outermost ones
        # (extrapolating the polynomial made the background swing at the edges)
        # no background from a single point: never a previous background reused
        self.temp_bg = None
        if len(x_bg) >= 2:
            spl_order = len(x_bg) - 1 if len(x_bg) - 1 <= 5 else 5
            spl = InterpolatedUnivariateSpline(x_bg, y_bg, k=spl_order)
            self.temp_bg = spl(np.clip(curve_data_x, x_bg[0], x_bg[-1]))
            self.data_bg_line.setData(curve_data_x,self.temp_bg)
        return self.temp_bg

class ResizeOnlyLinearRegion(pg.LinearRegionItem):
    def __init__(self, *args, **kwargs):
        # Grab movable if passed
        movable = kwargs.pop("movable", True)
        super().__init__(*args, **kwargs)

        self.setMovable(movable)  # set whole-region movability
        self.updateEdgeCursors()

    def setMovable(self, movable):
        super().setMovable(movable)
        self.updateEdgeCursors()

    def updateEdgeCursors(self):
        """Set resize cursor on edges only if the region is movable"""
        for line in self.lines:
            if self.movable:   # check the whole region movability
                line.setCursor(Qt.SizeHorCursor)
            else:
                line.unsetCursor()

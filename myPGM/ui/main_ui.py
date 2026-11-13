import logging

import numpy as np
from PyQt5.QtWidgets import (
    QMainWindow,
    QLabel,
    QPushButton,
    QFileDialog,
    QWidget,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QMessageBox,
    QAction,
    QGridLayout,
    QSplitter,
    QSpinBox,
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QGuiApplication, QKeySequence

from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import InterpolatedUnivariateSpline
from myPGM.helpers import (get_app_icon,
                          MyHSeparator, 
                          MyVSeparator, 
                          SmartDoubleDialog,
                          FontSizeWindow,
                          set_app_font_size,
                          current_app_font_px,)
from myPGM.settings import app_settings, last_dir, remember_dir

from myPGM.ui.PvPmPlot import PvPmPlotWindow
from myPGM.ui.PvPmTable import HPTableWindow
from myPGM.ui.FileListViewerWidget import FileListViewerWidget
from myPGM.ui.PressureToolbox import PressureToolbox
from myPGM.ui import theme

import pyqtgraph as pg

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):

    #####################################################################################
        # ? Signals setup
    theme_switched = pyqtSignal()
    fit_from_click_signal = pyqtSignal(object)
    start_auto_fit_signal = pyqtSignal(object)
    subtract_ManualBg_signal = pyqtSignal(object)
    add_current_fit_signal = pyqtSignal(object)
    open_session_signal = pyqtSignal()
    save_session_signal = pyqtSignal()
    save_session_as_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Setup Main window parameters
        self.setWindowTitle("myPGM - Pressure Gauge Monitor")
        
        app_icon = get_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)

        self.resize(800, 1000)          # placed on screen by _arrange_windows

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Main layout: pressure toolbox on top, files and fitting below
        main_layout = QVBoxLayout(central_widget)

        # Top panel
        top_panel_layout = QHBoxLayout()
        main_layout.addLayout(top_panel_layout)

        # Bottom panel
        bottom_panel_layout = QHBoxLayout()
        main_layout.addLayout(bottom_panel_layout)

        pg.setConfigOption('leftButtonPan', False)
 
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
        #####################################################################################
        # #? Setup Theme switch menu
        theme_menu = menubar.addMenu("Theme")

        dark_action = QAction("Dark mode", self)
        light_action = QAction("Light Mode", self)
        dark_action.triggered.connect(self.switch_to_dark)
        light_action.triggered.connect(self.switch_to_light)
        theme_menu.addAction(dark_action)
        theme_menu.addAction(light_action)

        #####################################################################################
        # #? Setup PToolbox menu
        ptoolbox_menu = menubar.addMenu("PToolbox")

        additional_toolbox = QAction("Toggle additional PToolbox", self)
        additional_toolbox.triggered.connect(self.toggle_additional_ptoolbox)
        ptoolbox_menu.addAction(additional_toolbox)
        #####################################################################################
        # #? Setup font size menu
        fontsize_menu = menubar.addMenu("Font size")
        fontsize_setting = QAction("Set font size", self)
        fontsize_setting.triggered.connect(self.show_font_size_window)
        fontsize_menu.addAction(fontsize_setting)

        #####################################################################################

        # #? Exit button setup
        exit_menu = menubar.addMenu("Exit")

        exit_action = QAction(" Exit", self)
        exit_action.setShortcut(QKeySequence.Quit)        # Ctrl+Q (Cmd+Q on macOS)
        exit_action.triggered.connect(self.close)
        exit_menu.addAction(exit_action)

        #####################################################################################
        # ? Setup Pressure Toolbox in the top panel

        PToolboxGroup = QGroupBox('Pressure toolbox')
        PToolboxLayout = QHBoxLayout()
        
        self.ptoolbox = PressureToolbox()

        self.PToolbox_toTable_button = QPushButton('Add \nto\n table')

        PToolboxLayout.addWidget(self.ptoolbox, stretch=10)
        PToolboxLayout.addWidget(self.PToolbox_toTable_button, stretch=1)
        PToolboxGroup.setLayout(PToolboxLayout)
        top_panel_layout.addWidget(PToolboxGroup)

        #################################################################################### Main Bottom Panel ###################################################################################""

        #####################################################################################
        # ? Setup left part of bottom panel

        FileManagementBox = QGroupBox("File management")
        FileManagementLayout = QVBoxLayout()
        FileManagementBox.setLayout(FileManagementLayout)

        self.file_list_widget = FileListViewerWidget()

        FileManagementLayout.addWidget(self.file_list_widget)

        bottom_panel_layout.addWidget(FileManagementBox, stretch=1)

        #####################################################################################
        # #? Setup right part of bottom panel

        FitBox = QGroupBox("File fitting")
        FitBoxLayout = QVBoxLayout()
        FitBox.setLayout(FitBoxLayout)
        bottom_panel_layout.addWidget(FitBox, stretch=10)

        #####################################################################################
        # #? Setup loaded file info section

        FileInfoBoxLayout = QVBoxLayout()
        self.current_file_label = QLabel("No file selected", self)
        FileInfoBoxLayout.addWidget(self.current_file_label)

        self.dir_label = QLabel("No directory selected", self)
        FileInfoBoxLayout.addWidget(self.dir_label)

        FitBoxLayout.addLayout(FileInfoBoxLayout)
        FitBoxLayout.addWidget(MyHSeparator())

        #####################################################################################
        # ? Data correction + fit section
        InteractionBox = QHBoxLayout()

        FitOptionBox = QVBoxLayout()

        FitButtonsBox = QGridLayout()

        self.fit_button = QPushButton("Fit", self)
        self.fit_button.setProperty("primary", True)
        self.fit_button.clicked.connect(self.auto_fit)

        FitButtonsBox.addWidget(self.fit_button, 0, 0)

        self.click_fit_button = QPushButton("Click-to-fit", self)
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        self.click_fit_enabled = False

        FitButtonsBox.addWidget(self.click_fit_button, 0, 1)

        self.fit_range_enable_button = QPushButton("Fit range", self)
        self.fit_range_enable_button.setCheckable(True)
        self.fit_range_enable_button.clicked.connect(self.toggle_fit_range)
        self.fit_range_enabled = False

        FitButtonsBox.addWidget(self.fit_range_enable_button, 1, 0)
        
        self.fit_range_edit_button = QPushButton("Edit", self)
        self.fit_range_edit_button.setCheckable(True)
        self.fit_range_edit_button.clicked.connect(self.toggle_fit_range_edit)
        self.fit_range_edit_enabled = False

        FitButtonsBox.addWidget(self.fit_range_edit_button, 1, 1)

        FitOptionBox.addLayout(FitButtonsBox)

        self.fit_model_combo = QComboBox()
        self.fit_model_combo.setObjectName("fit_model_combo")
        self.fit_model_combo.setMinimumWidth(100)

        FitOptionBox.addWidget(self.fit_model_combo)

        InteractionBox.addLayout(FitOptionBox)

        InteractionBox.addWidget(MyVSeparator())
        
        CorrectionBox = QVBoxLayout()

        BgBox = QHBoxLayout()

        self.CHullBg_button = QPushButton("Auto Bg", self)
   
        BgBox.addWidget(self.CHullBg_button, stretch=3)

        self.ManualBg_button = QPushButton("Manual Bg", self)
        self.ManualBg_button.setCheckable(True)
        self.ManualBg_button.clicked.connect(self.toggle_ManualBg)
        self.click_ManualBg_enabled = False
        self.ManualBg_points = []
        self.temp_bg = None
        BgBox.addWidget(self.ManualBg_button, stretch=3)

        self.ResetBg_button = QPushButton("Reset Bg", self)
        BgBox.addWidget(self.ResetBg_button, stretch=3)

        SpectroCalibBox = QHBoxLayout()
        self.LoadSpectro_button = QPushButton("Load spectro", self)
        SpectroCalibBox.addWidget(self.LoadSpectro_button, stretch=3)

        self.Spectro_use_button = QPushButton("Use", self)
        self.Spectro_use_button.setCheckable(True)
        SpectroCalibBox.addWidget(self.Spectro_use_button, stretch=3)

        self.Spectro_filename_label = QLabel("None", self)
        SpectroCalibBox.addWidget(self.Spectro_filename_label, stretch=3)

        SmoothBox = QHBoxLayout()
        SmoothBox.addWidget(QLabel("Smoothing:", self), stretch=1)

        self.smoothing_factor = QSpinBox()      # smoothing window, in points
        self.smoothing_factor.setRange(1, 999)
        self.smoothing_factor.setValue(1)
        
        SmoothBox.addWidget(self.smoothing_factor, stretch=1)

        self.Derivative_button = QPushButton("Toggle derivative", self)
        self.Derivative_button.clicked.connect(self.toggle_derivative)
        self.Derivative_enabled = False
        SmoothBox.addWidget(self.Derivative_button, stretch=2)

        CorrectionBox.addLayout(BgBox)
        CorrectionBox.addLayout(SpectroCalibBox)
        CorrectionBox.addLayout(SmoothBox)

        InteractionBox.addLayout(CorrectionBox)

        FitBoxLayout.addLayout(InteractionBox)

        #####################################################################################
        # #? Setup data plotting section
        PlotLayout = QVBoxLayout()
        self.splitter = QSplitter(Qt.Vertical)
        # the theme recorded at startup, before a saved dark theme is applied below
        theme.set_current(False)
        self.plot_label_color = theme.tokens()["mu"]
        self.fit_color = theme.calib_color(None)      # set from the plotted calibration
        # plots and the PvPm table use the app font size, kept in sync by set_font_size
        self.plot_font_px = current_app_font_px()
        # font size chosen in a previous launch (the slider range)
        saved_font_px = app_settings().value("font_size", 0, type=int)
        if 8 <= saved_font_px <= 30:
            set_app_font_size(saved_font_px)
            self.plot_font_px = saved_font_px
        self.plot_title_size = f"{self.plot_font_px + 4}px"
        self.font_size_window = None

        # #? Actual spectral data
        self.data_widget = pg.PlotWidget()
        styles = self._label_styles()
        self.data_widget.setLabel("bottom", "Spectral unit", **styles)
        self.data_widget.setLabel("left", "Intensity (a.u.)", **styles)
        self.data_scatter = pg.ScatterPlotItem(symbol='o', size=3, pen=None)
        self.data_widget.addItem(self.data_scatter)
        self.data_fit_pen = pg.mkPen(color=self.fit_color, width=2)
        self.data_bg_pen = pg.mkPen(color='darkviolet', width=3)
        self.data_bg_scatter = pg.ScatterPlotItem(symbol='s', size=8, brush='darkviolet')
        self.data_fit_line = pg.PlotDataItem(name='Fit',pen=self.data_fit_pen,)
        self.data_bg_line = pg.PlotDataItem(name='Bg',pen=self.data_bg_pen)
        self.data_edge_marker = pg.InfiniteLine(pos=None, angle=90, pen=self.data_fit_pen, movable=False)
        
        self.data_widget.setMenuEnabled(False)
        self.data_scatter.scene().sigMouseClicked.connect(self.data_plot_click)

        self.fit_range_selector = ResizeOnlyLinearRegion(movable=False)
        self.fit_range_selector_edited = False
        self.fit_range_selector.sigRegionChangeFinished.connect(self.fit_range_changed)

        #####################################################################################
        # #? Setup derivative plotting section
        self.deriv_widget = pg.PlotWidget()
        self.deriv_widget.setLabel("bottom", "Spectral unit", **styles)
        self.deriv_widget.setLabel("left", "dI/dx", **styles)

        self.deriv_scatter = pg.ScatterPlotItem(symbol='o', size=3, pen=None)
        self.deriv_widget.addItem(self.deriv_scatter)
        self.deriv_edge_marker = pg.InfiniteLine(pos=None, angle=90, pen=self.data_fit_pen, movable=False)
        self._style_plots()

        self.deriv_widget.setMenuEnabled(False)
        self.deriv_scatter.scene().sigMouseClicked.connect(self.deriv_plot_click)

        self.splitter.addWidget(self.data_widget)
        self.splitter.addWidget(self.deriv_widget)
        PlotLayout.addWidget(self.splitter)
        self.splitter.setSizes([300, 200])
        self.splitter.widget(1).hide()

        FitBoxLayout.addLayout(PlotLayout)

        self.table_interactions = QHBoxLayout()
        self.add_fitted_button = QPushButton("Add fit to table")
        self.add_fitted_button.setProperty("primary", True)
        self.add_fitted_button.clicked.connect(self.add_current_fit)
        self.table_interactions.addWidget(self.add_fitted_button, stretch=3)

        self.toggle_PvPm_button = QPushButton("P vs Pm")
        self.toggle_PvPm_button.clicked.connect(self.toggle_PvPm)
        self.table_interactions.addWidget(self.toggle_PvPm_button, stretch=1)
        FitBoxLayout.addLayout(self.table_interactions)

        #####################################################################################
        # #? Setup PvPm table and plotwindow

        self.PvPmTableWindow = HPTableWindow()
        self.PvPmPlotWindow = PvPmPlotWindow()
        self.PvPmTableWindow.show()
        self.PvPmPlotWindow.show()
        # placed once shown: showing polishes the widgets, which can enlarge the
        # windows' minimum size (to 823 px for the table on Windows CI)
        self._arrange_windows()

        self.set_font_size(self.plot_font_px)

        self.additional_toolbox_window = PressureToolbox()

        # set by the presenter: called on close, returns False to keep the window open
        self.close_guard = None

        # theme chosen in a previous launch (light by default)
        if app_settings().value("theme", "light", type=str) == "dark":
            self.switch_to_dark()

    #####################################################################################
    # ? Main window methods

    def _arrange_windows(self):
        """Place the main window and, to its right, the PvPm table and plot,
        all within the available area of the screen (small laptop screens too)."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        gap = 10

        def fit(widget, x, y):
            """Place the window frame (title bar and borders included) at x, y, moved
            back inside the screen if needed."""
            frame, inner = widget.frameGeometry(), widget.geometry()
            frame_w, frame_h = frame.width() - inner.width(), frame.height() - inner.height()
            # never below the minimum size of the window's layout, which Qt applies
            # anyway: a window that cannot shrink to the screen starts at its edge
            minimum = widget.minimumSizeHint().expandedTo(widget.minimumSize())
            width = max(min(inner.width(), area.width() - frame_w), minimum.width())
            height = max(min(inner.height(), area.height() - frame_h), minimum.height())
            x = max(area.left(), min(x, area.right() + 1 - width - frame_w))
            y = max(area.top(), min(y, area.bottom() + 1 - height - frame_h))
            widget.setGeometry(x + inner.left() - frame.left(), y + inner.top() - frame.top(),
                               width, height)

        fit(self, area.left() + 100, area.top() + 100)
        side_x = self.frameGeometry().right() + gap
        fit(self.PvPmTableWindow, side_x, self.frameGeometry().top())
        fit(self.PvPmPlotWindow, side_x, self.PvPmTableWindow.frameGeometry().bottom() + gap)

    def closeEvent(self, event):
        if self.close_guard is not None and not self.close_guard():
            event.ignore()
            return
        # close the side windows owned by this main window (not every app window,
        # which recursed between main windows)
        for window in (self.PvPmTableWindow, self.PvPmPlotWindow,
                       self.additional_toolbox_window, self.font_size_window):
            if window is not None:
                window.close()
        super().closeEvent(event)

    def switch_to_dark(self):
        self._apply_theme(dark=True)

    def switch_to_light(self):
        self._apply_theme(dark=False)

    def _apply_theme(self, dark):
        try:
            # app-wide, so that every window and dialog follows the theme
            theme.apply_theme(dark=dark)
        except OSError as exc:
            logger.warning("Could not load the theme stylesheet: %s", exc)
            theme.set_current(dark)
        app_settings().setValue("theme", "dark" if dark else "light")

        # pyqtgraph plots are not styled by the Qt stylesheet
        self._style_plots()

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
        for line in self.fit_range_selector.lines:
            line.setPen(pg.mkPen(theme.qcolor(t["ac"]), width=1))
            line.setHoverPen(pg.mkPen(theme.qcolor(t["ac"]), width=2))
        self.update_plot_fonts()
        self._set_fit_color(self.fit_color)

    def _set_fit_color(self, color):
        self.fit_color = color
        self.data_fit_pen = pg.mkPen(color=color, width=2)
        self.data_fit_line.setPen(self.data_fit_pen)
        marker_pen = pg.mkPen(color=color, width=1.5, style=Qt.DashLine)
        self.data_edge_marker.setPen(marker_pen)
        self.deriv_edge_marker.setPen(marker_pen)

    def populate_fit_models_combo(self, model_dict):
        if model_dict is not None:
            self.fit_model_combo.addItems(model_dict.keys())

            for k, v in model_dict.items():
                ind = self.fit_model_combo.findText(k)
                self.fit_model_combo.model().item(ind).setBackground(QColor(v.color))
            
            tmp_color = (
            self.fit_model_combo.model()
            .item(self.fit_model_combo.currentIndex())
            .background()
            .color()
            .getRgb()
            )
            self.fit_model_combo.setStyleSheet(
                "background-color: rgba{};".format(tmp_color)
            )
        else:
            raise ImportError('Error loading fit models.')

    def add_current_fit(self):
        self.add_current_fit_signal.emit(None)

    def prompt_fit_pm(self, current_pm):

        dialog = SmartDoubleDialog(valuename='Pm (bar):', parent=self)
        dialog.setWindowTitle("Input Pm")
        # start from the last Pm, selected: typing replaces it, Enter keeps it
        if current_pm is not None:
            dialog.spinbox.setValue(float(current_pm))
        dialog.spinbox.selectAll()
        dialog.spinbox.setFocus()
        if dialog.exec_():
            return dialog.value()
        return None

    def toggle_derivative(self, checked):
        if self.Derivative_enabled:
            self.splitter.widget(1).hide()
        else:
            self.splitter.widget(1).show()
        self.Derivative_enabled = not self.Derivative_enabled

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

    def toggle_fit_range_edit(self):
        if self.fit_range_enabled:
            if self.fit_range_edit_enabled:
                self.turn_off_fit_range_edit()
            else:
                self.turn_on_fit_range_edit()
        else:
            self.fit_range_edit_button.setChecked(False)
            self.turn_off_fit_range_edit()
    
    def turn_on_fit_range_edit(self):
        if self.fit_range_enabled:
            self.fit_range_selector.setMovable(True)
            self.fit_range_edit_enabled = True
    
    def turn_off_fit_range_edit(self):
        if self.fit_range_enabled:
            self.fit_range_selector.setMovable(False)
            self.fit_range_edit_enabled = False

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
            self.dir_label.setText(f"Selected directory: {dir_name}")
        return dir_name

    def plot_data(self, x, y, buffer, preserve_view=False):
        self.data_widget.removeItem(self.data_edge_marker)
        self.deriv_widget.removeItem(self.deriv_edge_marker)
        self.data_widget.removeItem(self.data_fit_line)
        self.data_fit_line.setData([],[])
        self._set_plot_title('Not fitted')

        self.data_widget.setLabel("bottom", f"{buffer.calib.xname} ({buffer.calib.xunit})")
        self.data_widget.setLabel("left", 'Intensity')
        # the fit line of this spectrum is drawn in its calibration's colour
        self._set_fit_color(theme.calib_color(buffer.calib))

        self.data_scatter.setData(x, y)
        if not preserve_view:
            self.data_widget.autoRange()

    # derivative data
        self.deriv_widget.setLabel("bottom", f"{buffer.calib.xname} ({buffer.calib.xunit})")
        self.deriv_widget.setLabel("left", 'dI/dx')

        # along increasing x, as the Raman edge search (files can store x decreasing)
        order = np.argsort(x, kind="stable")
        dI = np.empty(len(y))
        dI[order] = gaussian_filter1d(np.asarray(y)[order], mode="nearest", sigma=1, order=1)
        self.deriv_scatter.setData(x, dI)
        if not preserve_view:
            self.deriv_widget.autoRange()

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
    def _pressure_title(P, P_err=None):
        """Title with the statistical fit uncertainty, when there is one."""
        if P_err is None:
            return f"Fitted pressure : {P : > 10.3f} GPa"
        err = f"{P_err:.3f}" if round(P_err, 3) > 0 else "<0.001"
        return f"Fitted pressure : {P : > 10.3f} \u00b1 {err} GPa"

    def plot_fit(self, P, fit_model, fit_result, x, y, P_err=None):
        self.data_widget.removeItem(self.data_edge_marker)
        self.deriv_widget.removeItem(self.deriv_edge_marker)
        self.data_widget.removeItem(self.data_fit_line)

        if fit_model.type == "peak":
            # drawn over the whole spectrum, not only the fitting range
            x = np.asarray(x)
            self.data_fit_line.setData(x, fit_model.func(x, *fit_result["opti"]))
            self.data_widget.addItem(self.data_fit_line)
            self._set_plot_title(self._pressure_title(P, P_err))

        elif fit_model.type == "edge":
            self.data_edge_marker.setValue(fit_result["opti"])
            self.data_widget.addItem(self.data_edge_marker)
            self.deriv_edge_marker.setValue(fit_result["opti"])
            self.deriv_widget.addItem(self.deriv_edge_marker)
            self._set_plot_title(self._pressure_title(P, P_err))

        else:
            logger.warning("Plot of fit type %r not implemented", fit_model.type)

    def ask_save_changes(self):
        """'save', 'discard' or 'cancel'."""
        answer = QMessageBox.question(
            self, "Unsaved changes",
            "The session has unsaved changes (spectra, fits or table points).\n"
            "Save them before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save)
        return {QMessageBox.Save: "save", QMessageBox.Discard: "discard"}.get(answer, "cancel")

    def ask_recover_session(self, when):
        answer = QMessageBox.question(
            self, "Recover session",
            f"myPGM did not close normally last time.\n"
            f"A backup of the unsaved session from {when} was found.\n\n"
            "Recover it?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return answer == QMessageBox.Yes

    def fit_error_popup_window(self, reason=""):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setText("The fit failed.")
        # why, e.g. not enough points in the fit range (it was only in the log)
        msg.setInformativeText(reason)
        msg.setWindowTitle("Fit error")
        msg.exec_()

    def toggle_PvPm(self):
        if self.PvPmTableWindow.isVisible() or self.PvPmPlotWindow.isVisible():
            self.PvPmTableWindow.hide()
            self.PvPmPlotWindow.hide()
        else:
            self.PvPmTableWindow.show()
            self.PvPmPlotWindow.show()

    def toggle_additional_ptoolbox(self):
        if self.additional_toolbox_window.isVisible():
            self.additional_toolbox_window.hide()
        else:
            self.additional_toolbox_window.show()

    def show_font_size_window(self):
        # created once, so reopening it keeps the chosen size
        if self.font_size_window is None:
            self.font_size_window = FontSizeWindow(self.plot_font_px)
            self.font_size_window.font_size_changed.connect(self.set_font_size)
            self.font_size_window.font_size_changed.connect(
                lambda size: app_settings().setValue("font_size", size))
        self.font_size_window.show()
        self.font_size_window.raise_()

    def set_font_size(self, size):
        # pyqtgraph items and the PvPm table are not reached by the app stylesheet
        self.plot_font_px = size
        self.update_plot_fonts()
        self.PvPmTableWindow.table_widget.set_font_size(size)
        self.PvPmPlotWindow.set_font_size(size)

    def _label_styles(self):
        return theme.label_styles(self.plot_label_color, self.plot_font_px)

    def _set_plot_title(self, text):
        self.data_widget.setTitle(text, color=theme.tokens()["tx"], size=self.plot_title_size)

    def update_plot_fonts(self):
        styles = self._label_styles()
        # numbers in the mono font (DESIGN.md §2)
        tick_font = theme.mono_font(self.plot_font_px)
        for widget in (self.data_widget, self.deriv_widget):
            widget.setLabel("left", **styles)
            widget.setLabel("bottom", **styles)
            for side in ("left", "bottom"):
                widget.getAxis(side).setStyle(tickFont=tick_font)
        self.plot_title_size = f"{self.plot_font_px + 4}px"
        # re-apply the current title with the new size (none before the first plot)
        if self.data_widget.plotItem.titleLabel.text:
            self._set_plot_title(self.data_widget.plotItem.titleLabel.text)

    def toggle_ManualBg(self):
        if self.click_ManualBg_enabled and self.ManualBg_points != []:
            self.subtract_ManualBg_signal.emit(self.temp_bg)
            self.ManualBg_points = []
            self.temp_bg = None
            self.data_bg_line.setData([],[])
            self.data_bg_scatter.setData([],[])
            self.ManualBg_button.setText("Manual Bg")
            self.data_widget.removeItem(self.data_bg_line)
            self.data_widget.removeItem(self.data_bg_scatter)

        else:
            self.data_widget.addItem(self.data_bg_line)
            self.data_widget.addItem(self.data_bg_scatter)
        self.click_ManualBg_enabled = not self.click_ManualBg_enabled

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

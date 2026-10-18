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
from PyQt5.QtGui import QColor, QFont, QGuiApplication

from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import InterpolatedUnivariateSpline
from myPGM.helpers import (load_style, 
                          get_app_icon, 
                          MyHSeparator, 
                          MyVSeparator, 
                          SmartDoubleDialog,
                          FontSizeWindow,
                          set_app_theme,
                          current_app_font_px,)

from myPGM.ui.PvPmPlot import PvPmPlotWindow
from myPGM.ui.PvPmTable import HPTableWindow
from myPGM.ui.FileListViewerWidget import FileListViewerWidget
from myPGM.ui.PressureToolbox import PressureToolbox

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

        open_session_action = QAction("Open session", self)
        save_session_action = QAction("Save session", self)
        open_session_action.triggered.connect(self.open_session_signal.emit)
        save_session_action.triggered.connect(self.save_session_signal.emit)
        files_menu.addAction(open_session_action)
        files_menu.addAction(save_session_action)
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
        self.plot_label_color = "black"
        # plots and the PvPm table use the app font size, kept in sync by set_font_size
        self.plot_font_px = current_app_font_px()
        self.plot_title_size = f"{self.plot_font_px + 4}px"
        self.font_size_window = None

        # #? Actual spectral data
        self.data_widget = pg.PlotWidget()
        self.data_widget.setBackground("white")
        styles = self._label_styles()
        self.data_widget.setLabel("bottom", "Spectral unit", **styles)
        self.data_widget.setLabel("left", "Intensity (a.u.)", **styles)
        self.data_scatter = pg.ScatterPlotItem(symbol='o', size=4, brush='grey')
        self.data_widget.addItem(self.data_scatter)
        self.data_fit_pen = pg.mkPen(color='red', width=3)
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
        self.deriv_widget.setBackground("white")
        self.deriv_widget.setLabel("bottom", "Spectral unit", **styles)
        self.deriv_widget.setLabel("left", "dI/dx", **styles)

        self.deriv_scatter = pg.ScatterPlotItem(symbol='o', size=4, brush='grey')
        self.deriv_widget.addItem(self.deriv_scatter)
        self.deriv_edge_marker = pg.InfiniteLine(pos=None, angle=90, pen=self.data_fit_pen, movable=False)

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
        self._arrange_windows()
        self.PvPmTableWindow.show()
        self.PvPmPlotWindow.show()

        self.set_font_size(self.plot_font_px)

        self.additional_toolbox_window = PressureToolbox()

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
            width = min(widget.width(), area.width())
            height = min(widget.height(), area.height())
            x = max(area.left(), min(x, area.right() - width))
            y = max(area.top(), min(y, area.bottom() - height))
            widget.setGeometry(x, y, width, height)

        fit(self, area.left() + 100, area.top() + 100)
        side_x = self.geometry().right() + gap
        fit(self.PvPmTableWindow, side_x, self.geometry().top())
        fit(self.PvPmPlotWindow, side_x, self.PvPmTableWindow.geometry().bottom() + gap)

    def closeEvent(self, event):
        # close the side windows owned by this main window (not every app window,
        # which recursed between main windows)
        for window in (self.PvPmTableWindow, self.PvPmPlotWindow,
                       self.additional_toolbox_window, self.font_size_window):
            if window is not None:
                window.close()
        super().closeEvent(event)

    def switch_to_dark(self):
        self._apply_theme('dark-mode.qss', label_color="white", plot_background="#202020", dark=True)

    def switch_to_light(self):
        self._apply_theme('light-mode.qss', label_color="black", plot_background="white", dark=False)

    def _apply_theme(self, qss_file, label_color, plot_background, dark):
        try:
            style = load_style(qss_file)
        except OSError as exc:
            logger.warning("Could not load stylesheet %s: %s", qss_file, exc)
        else:
            # app-wide, so that every window and dialog follows the theme
            set_app_theme(style)
        self.plot_label_color = label_color

        # pyqtgraph plots are not styled by the Qt stylesheet
        styles = self._label_styles()
        for widget in (self.data_widget, self.deriv_widget):
            widget.setBackground(plot_background)
            widget.setLabel("left", **styles)
            widget.setLabel("bottom", **styles)

        for themed in (self.ptoolbox, self.additional_toolbox_window, self.PvPmPlotWindow):
            if dark:
                themed.set_dark_mode()
            else:
                themed.set_light_mode()

        self.theme_switched.emit()

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

        dialog = SmartDoubleDialog(valuename='Pm (bar):')

        dialog.setWindowTitle("Input Pm")
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
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Text and ASC files (*.txt *.asc);;All Files (*)")

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            return selected_files
        else:
            return None

    def get_save_session_filename_dialog(self):
        options = QFileDialog.Options()
        file_name, file_type = QFileDialog.getSaveFileName(
            self,
            "Save session",
            "",
            "Session Files (*.json);;All Files (*)",
            options=options,
        )
        if file_type == "Session Files (*.json)":
            if file_name and not file_name.endswith(".json"):
                file_name += ".json"
        return file_name or None

    def get_open_session_filename_dialog(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open session",
            "",
            "Session Files (*.json);;All Files (*)",
            options=options,
        )
        return file_name or None

    def select_directory_from_dialog(self):
        options = QFileDialog.Options()
        dir_name = QFileDialog.getExistingDirectory(
            self, "Select Directory", options=options
        )
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

        self.data_scatter.setData(x, y)
        if not preserve_view:
            self.data_widget.autoRange()

    # derivative data
        self.deriv_widget.setLabel("bottom", f"{buffer.calib.xname} ({buffer.calib.xunit})")
        self.deriv_widget.setLabel("left", 'dI/dx')

        dI = gaussian_filter1d(y, mode="nearest", sigma=1, order=1)
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

            x_click, y_click = click_point.x(), click_point.y()
            self.fit_from_click_signal.emit(x_click)

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

    def fit_error_popup_window(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Attempted fit couldn't converge.")
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
        self.font_size_window.show()
        self.font_size_window.raise_()

    def set_font_size(self, size):
        # pyqtgraph items and the PvPm table are not reached by the app stylesheet
        self.plot_font_px = size
        self.update_plot_fonts()
        self.PvPmTableWindow.table_widget.set_font_size(size)
        self.PvPmPlotWindow.set_font_size(size)

    def _label_styles(self):
        return {"color": self.plot_label_color, "font-size": f"{self.plot_font_px}px"}

    def _set_plot_title(self, text):
        self.data_widget.setTitle(text, color=self.plot_label_color, size=self.plot_title_size)

    def update_plot_fonts(self):
        styles = self._label_styles()
        tick_font = QFont()
        tick_font.setPixelSize(self.plot_font_px)
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

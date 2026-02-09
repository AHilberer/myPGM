import os
import numpy as np
from copy import deepcopy
from scipy.optimize import curve_fit
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QPushButton,
    QFileDialog,
    QWidget,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QDoubleSpinBox,
    QGroupBox,
    QMessageBox,
    QAction,
    QGridLayout,
    QSplitter,
    
)
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QIcon

from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import InterpolatedUnivariateSpline
from myPGM.helpers import load_style, MyHSeparator, MyVSeparator

from myPGM.ui.PvPmPlot import PvPmPlotWindow
from myPGM.ui.PvPmTable import HPTableWindow
from myPGM.ui.FileListViewerWidget import FileListViewerWidget
from myPGM.ui.PressureToolbox import PressureToolbox

import pyqtgraph as pg


class MainWindow(QMainWindow):

    #####################################################################################
        # ? Signals setup
    theme_switched = pyqtSignal()
    fit_from_click_signal = pyqtSignal(object)
    start_auto_fit_signal = pyqtSignal(object)
    subtract_ManualBg_signal = pyqtSignal(object)
    modified_fit_range_signal = pyqtSignal(object)
    add_current_fit_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        # Setup Main window parameters
        self.setWindowTitle("myPGM - myPressureGaugeMonitor")

        # self.icon_path = os.path.join(os.path.dirname(
        #                         os.path.abspath(__file__)),
        #                  'resources/myPGM_logo.png')
        # self.setWindowIcon(QIcon(self.icon_path))

        x = 100
        y = 100
        width = 800
        height = 800
        self.setGeometry(x, y, width, height)
        # self.setWindowIcon(QIcon('resources/PGMicon.png'))

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Use a QHBoxLayout for the main layout
        main_layout = QVBoxLayout(central_widget)

        # Create a new panel on the left
        top_panel_layout = QHBoxLayout()
        main_layout.addLayout(top_panel_layout)

        # Create a new panel on the right
        bottom_panel_layout = QHBoxLayout()
        main_layout.addLayout(bottom_panel_layout)

        pg.setConfigOption('leftButtonPan', False)
 
        #####################################################################################
        # #? Setup Parameters table window
        menubar = self.menuBar()
        # self.ParamWindow = ParameterWindow()
        # param_menu = menubar.addMenu('Parameters')
        # open_param_action = QAction('Change parameters', self)
        # open_param_action.triggered.connect(self.toggle_params)
        # param_menu.addAction(open_param_action)

        #####################################################################################
        # #? Setup Theme switch menu
        files_menu = menubar.addMenu("Files")

        open_session_action = QAction("Open session", self)
        save_session_action = QAction("Save session", self)
        open_session_action.triggered.connect(self.switch_to_dark)
        save_session_action.triggered.connect(self.switch_to_light)
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

        PToolboxSubactionsLayout = QVBoxLayout()        
        addPToolbox_instance = QPushButton('New PToolbox')
        addToTable = QPushButton('Add to Table')

        PToolboxSubactionsLayout.addWidget(addPToolbox_instance)
        PToolboxSubactionsLayout.addWidget(addToTable)

        PToolboxLayout.addWidget(self.ptoolbox, stretch=10)
        PToolboxLayout.addLayout(PToolboxSubactionsLayout, stretch=1)
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

        SmoothBox = QHBoxLayout()
        SmoothBox.addWidget(QLabel("Smoothing:", self), stretch=1)

        self.smoothing_factor = QDoubleSpinBox()
        self.smoothing_factor.setDecimals(0)
        self.smoothing_factor.setRange(1, +np.inf)
        self.smoothing_factor.setValue(1)
        
        SmoothBox.addWidget(self.smoothing_factor, stretch=1)

        self.Derivative_button = QPushButton("Toggle derivative", self)
        self.Derivative_button.clicked.connect(self.toggle_derivative)
        self.Derivative_enabled = False
        SmoothBox.addWidget(self.Derivative_button, stretch=2)

        CorrectionBox.addLayout(BgBox)
        CorrectionBox.addLayout(SmoothBox)

        InteractionBox.addLayout(CorrectionBox)

        FitBoxLayout.addLayout(InteractionBox)

        #####################################################################################
        # #? Setup data plotting section
        PlotLayout = QVBoxLayout()
        self.splitter = QSplitter(Qt.Vertical)
        self.plot_label_color = "black"

        # #? Actual spectral data
        self.data_widget = pg.PlotWidget()
        self.data_widget.setBackground("white")
        styles = {"color": "black", "font-size": "16px"}
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
        styles = {"color": "black", "font-size": "16px"}
        self.deriv_widget.setLabel("bottom", "Spectral unit", **styles)
        self.deriv_widget.setLabel("left", "I' (a.u.)", **styles)

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

        # splitter.setStyleSheet("QSplitter::handle {background: rgb(55, 100, 110);} ")
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
        self.PvPmTableWindow.show()

        self.PvPmPlotWindow = PvPmPlotWindow()
        self.PvPmPlotWindow.show()
#
#        self.data.changed.connect(self.PvPmTableWindow.table_widget.updatetable)
#        self.data.changed.connect(self.PvPmPlotWindow.updateplot)



    #####################################################################################
    # ? Main window methods


    def closeEvent(self, event):
        for window in QApplication.topLevelWidgets():
            window.close()

    def switch_to_dark(self):
        try:
            style = load_style('dark-mode.qss')
            self.setStyleSheet(style)
            self.PvPmTableWindow.setStyleSheet(style)
            self.PvPmPlotWindow.setStyleSheet(style)
        except:
            pass
        self.plot_label_color = "white"

        # some parameters seem to be unaffected by the style import ...
        # thus we use the following fix

#        self.PvPmPlotWindow.plot_graph.setBackground("#202020")
        styles = {"color": self.plot_label_color, "font-size": "16px"}
#        self.PvPmPlotWindow.plot_graph.setLabel("left", "P (GPa)", **styles)
#        self.PvPmPlotWindow.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
        self.data_widget.setBackground("#202020")
        self.data_widget.setLabel("left", **styles)
        self.data_widget.setLabel("bottom", **styles)
        self.deriv_widget.setBackground("#202020")
        self.deriv_widget.setLabel("left", **styles)
        self.deriv_widget.setLabel("bottom", **styles)

        self.ptoolbox.set_dark_mode()
        self.PvPmPlotWindow.set_dark_mode()
#        self.PvPmPlotWindow.updateplot()

        #self.theme_switched.emit() #need to replot data ?

    def switch_to_light(self):
        try:
            style = load_style('light-mode.qss')
            self.setStyleSheet(style)
            self.PvPmTableWindow.setStyleSheet(style)
            self.PvPmPlotWindow.setStyleSheet(style)
        except:
            pass
        self.plot_label_color = "black"

        # some parameters seem to be unaffected by the style import ...
        # thus we use the following fix
        
        #self.PvPmPlotWindow.plot_graph.setBackground("white")
        styles = {"color": self.plot_label_color, "font-size": "16px"}
        #self.PvPmPlotWindow.plot_graph.setLabel("left", "P (GPa)", **styles)
        #self.PvPmPlotWindow.plot_graph.setLabel("bottom", "Pm (bar)", **styles)

        self.data_widget.setBackground("white")
        self.data_widget.setLabel("left", **styles)
        self.data_widget.setLabel("bottom", **styles)
        self.deriv_widget.setBackground("white")
        self.deriv_widget.setLabel("left", **styles)
        self.deriv_widget.setLabel("bottom", **styles)

        self.ptoolbox.set_light_mode()
        self.PvPmPlotWindow.set_light_mode()
        #self.PvPmPlotWindow.updateplot()

        #self.theme_switched.emit() #need to replot data ?


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
                "background-color: rgba{};    selection-background-color: k;".format(tmp_color)
            )
        else:
            raise ImportError('Error loading fit models.')


    def add_current_fit(self):
        self.add_current_fit_signal.emit(None)

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
            self.data_widget.addItem(self.fit_range_selector)
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
        if self.fit_range_enabled:
            self.modified_fit_range_signal.emit(self.fit_range_selector.getRegion())

    def get_file_via_dialog(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Text and ASC files (*.txt *.asc);;All Files (*)")

        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            return selected_files
        else:
            return None


    def select_directory_from_dialog(self):
        options = QFileDialog.Options()
        dir_name = QFileDialog.getExistingDirectory(
            self, "Select Directory", options=options
        )
        if dir_name:
            self.dir_label.setText(f"Selected directory: {dir_name}")
        return dir_name



    def plot_data(self, x, y, buffer):
        self.data_widget.removeItem(self.data_edge_marker)
        self.deriv_widget.removeItem(self.deriv_edge_marker)
        self.data_widget.removeItem(self.data_fit_line)
        self.data_fit_line.setData([],[])
        self.data_widget.setTitle('Not fitted', color=self.plot_label_color, size="16pt")

        self.data_widget.setLabel("bottom", f"{buffer.calib.xname} ({buffer.calib.xunit})")
        self.data_widget.setLabel("left", 'Intensity')

        self.data_scatter.setData(x, y)
        self.data_widget.autoRange()

    # derivative data
        self.deriv_widget.setLabel("bottom", f"{buffer.calib.xname} ({buffer.calib.xunit})")
        self.deriv_widget.setLabel("left", 'Intensity')

        dI = gaussian_filter1d(y, mode="nearest", sigma=1, order=1)
        self.deriv_scatter.setData(x, dI)
        self.deriv_widget.autoRange()



    def toggle_click_fit(self):
        self.click_fit_enabled = not self.click_fit_enabled

    def data_plot_click(self, event):
        if event.button() == Qt.RightButton or (
            event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        ):
            view_range = np.array(self.data_widget.plotItem.vb.viewRange()) * 2
            curve_data = self.data_scatter.getData()
            x_range = np.max(curve_data[0]) - np.min(curve_data[0])
            if (view_range[0][1] - view_range[0][0]) > x_range:
                #self.auto_range = True
                self.data_widget.autoRange()
            else:
                #self.auto_range = False
                self.data_widget.plotItem.vb.scaleBy((2, 2))
            #self.emit_sig_range_changed()
        elif event.button() == Qt.LeftButton:
            if self.click_fit_enabled:
                self.click_to_fit(event, 'data')
            elif self.click_ManualBg_enabled:
                self.set_ManualBg(event)



    def deriv_plot_click(self, event):
        if event.button() == Qt.RightButton or (
            event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        ):
            view_range = np.array(self.deriv_widget.plotItem.vb.viewRange()) * 2
            curve_data = self.deriv_scatter.getData()
            x_range = np.max(curve_data[0]) - np.min(curve_data[0])
            if (view_range[0][1] - view_range[0][0]) > x_range:
                #self.auto_range = True
                self.deriv_widget.autoRange()
            else:
                #self.auto_range = False
                self.deriv_widget.plotItem.vb.scaleBy((2, 2))
            #self.emit_sig_range_changed()
        elif event.button() == Qt.LeftButton:
            if self.click_fit_enabled:
                self.click_to_fit(event, 'deriv')

    def auto_fit(self):
        self.start_auto_fit_signal.emit(None)

    def click_to_fit(self, mouseClickEvent, window):
        if self.click_fit_enabled:
            scene_coords = mouseClickEvent.scenePos()
            if window == 'data':
                vb = self.data_widget.plotItem.vb
                if self.data_widget.sceneBoundingRect().contains(scene_coords):
                    click_point = vb.mapSceneToView(scene_coords)
            elif window == 'deriv':
                vb = self.deriv_widget.plotItem.vb
                if self.deriv_widget.sceneBoundingRect().contains(scene_coords):
                    click_point = vb.mapSceneToView(scene_coords)

            x_click, y_click = click_point.x(), click_point.y()
            self.fit_from_click_signal.emit(x_click)

            self.toggle_click_fit()
            self.click_fit_button.setChecked(False)


    def plot_fit(self, P, fit_model, fit_result, x, y):
        self.data_widget.removeItem(self.data_edge_marker)
        self.deriv_widget.removeItem(self.deriv_edge_marker)
        self.data_widget.removeItem(self.data_fit_line)

        if fit_model.type == "peak":
            fitted = [
                fit_model.func(wvl, *fit_result["opti"])
                for wvl in x
            ]
            self.data_fit_line.setData(x, fitted)
            self.data_widget.addItem(self.data_fit_line)
            self.data_widget.setTitle(f"Fitted pressure : {P : > 10.3f} GPa", color=self.plot_label_color, size="16pt")

        elif fit_model.type == "edge":
            self.data_edge_marker.setValue(fit_result["opti"])
            self.data_widget.addItem(self.data_edge_marker)
            self.deriv_edge_marker.setValue(fit_result["opti"])
                
            self.deriv_widget.addItem(self.deriv_edge_marker)

            self.data_widget.setTitle(f"Fitted pressure : {P : > 10.3f} GPa", color=self.plot_label_color, size="16pt")
                                
        else:
                print("Plot fit not implemented")


    def fit_error_popup_window(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Attempted fit couldn't converge.")
        msg.setWindowTitle("Fit error")
        msg.exec_()

    def add_ptoolbox_widget(self):
        pass # HERE


    def toggle_PvPm(self):
        if self.PvPmTableWindow.isVisible() or self.PvPmPlotWindow.isVisible():
            self.PvPmTableWindow.hide()
            self.PvPmPlotWindow.hide()
        else:
            self.PvPmTableWindow.show()
            self.PvPmPlotWindow.show()



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
        # if self.click_ManualBg_enabled:
        #    self.ManualBg_button.setText('test')

    def set_ManualBg(self, mouseClickEvent):
        if self.click_ManualBg_enabled:
            scene_coords = mouseClickEvent.scenePos()
            vb = self.data_widget.plotItem.vb
            if self.data_widget.sceneBoundingRect().contains(scene_coords):
                click_point = vb.mapSceneToView(scene_coords)
                x_click, y_click = click_point.x(), click_point.y()
            self.ManualBg_points.append([x_click, y_click])
            #current_spectrum.bg = self.plot_ManualBg()
            self.plot_ManualBg()


    def plot_ManualBg(self):
        curve_data_x = self.data_scatter.getData()[0]

        temp = np.array(self.ManualBg_points)
        x_bg = temp[:, 0]
        y_bg = temp[:, 1]
        
        self.data_bg_scatter.setData(x_bg,y_bg)
        
        # sort bg points
        y_bg = y_bg[np.argsort(x_bg)]
        x_bg = np.sort(x_bg)

        # spline fit:
        if len(x_bg) >= 2:
            spl_order = len(x_bg) - 1 if len(x_bg) - 1 <= 5 else 5
            spl = InterpolatedUnivariateSpline(x_bg, y_bg, k=spl_order)
            self.temp_bg = spl(curve_data_x)
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

if __name__ == "__main__":
    print("Only MainWindow was executed.")

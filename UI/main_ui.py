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
    QListView,
    QGridLayout,
    QStyle,
    QFormLayout,
    QSplitter,
    QFrame,
    
)
from PyQt5.QtCore import (
    QFileInfo,
    Qt,
    QModelIndex,
    QItemSelectionModel,
    pyqtSlot,
    QSize,
    QAbstractListModel,
    pyqtSignal,
)
from PyQt5.QtGui import QColor, QIcon

from scipy.ndimage import uniform_filter1d, gaussian_filter1d
from scipy.interpolate import InterpolatedUnivariateSpline

from UI.PvPm_plot_window import PmPPlotWindow
from UI.PvPm_table_window import HPTableWidget, HPTableWindow, HPDataTable, HPData

from UI.FileListViewerWidget import FileListViewerWidget

import pyqtgraph as pg

demo_mode = True

class MainWindow(QMainWindow):

    #####################################################################################
        # ? Signals setup
    theme_switched = pyqtSignal()
    import_calib_signal = pyqtSignal(object)
    import_fit_models_signal = pyqtSignal(object)


    def __init__(self, model):
        super().__init__()
        self.model = model
        # Setup Main window parameters
        self.setWindowTitle("myPGM - PressureGaugeMonitor")
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
        # this will be our initial state
        self.buffer = None
        self.calibrations = None
        self.fit_models = None
        
        ##################################### Main Top Panel ###################################################################################
        # #? PRL style toolbox
        ToolboxGroup = QGroupBox("Pressure toolbox")
        Toolboxlayout = QHBoxLayout()
        self.Pm_spinbox = QDoubleSpinBox()
        self.Pm_spinbox.setObjectName("Pm_spinbox")
        self.Pm_spinbox.setDecimals(2)
        self.Pm_spinbox.setRange(-np.inf, np.inf)
        self.Pm_spinbox.setSingleStep(0.1)
        self.Pm_spinbox.setStyleSheet("background: #0066CC;")
        self.Pm_spinbox.setMinimumWidth(80)

        self.P_spinbox = QDoubleSpinBox()
        self.P_spinbox.setObjectName("P_spinbox")
        self.P_spinbox.setDecimals(3)
        self.P_spinbox.setRange(-np.inf, np.inf)
        self.P_spinbox.setSingleStep(0.1)
        self.P_spinbox.setStyleSheet("background: #4a8542;")
        self.P_spinbox.setMinimumWidth(80)

        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setObjectName("x_spinbox")
        self.x_spinbox.setDecimals(2)
        self.x_spinbox.setRange(-np.inf, +np.inf)
        self.x_spinbox.setMinimumWidth(80)

        self.T_spinbox = QDoubleSpinBox()
        self.T_spinbox.setObjectName("T_spinbox")
        self.T_spinbox.setDecimals(0)
        self.T_spinbox.setRange(-np.inf, +np.inf)
        self.T_spinbox.setSingleStep(1)

        self.x0_spinbox = QDoubleSpinBox()
        self.x0_spinbox.setObjectName("x0_spinbox")
        self.x0_spinbox.setDecimals(2)
        self.x0_spinbox.setRange(-np.inf, +np.inf)

        self.T0_spinbox = QDoubleSpinBox()
        self.T0_spinbox.setObjectName("T0_spinbox")
        self.T0_spinbox.setDecimals(0)
        self.T0_spinbox.setRange(-np.inf, +np.inf)
        self.T0_spinbox.setSingleStep(1)

        self.calibration_combo = QComboBox()
        self.calibration_combo.setObjectName("calibration_combo")
        self.calibration_combo.setMinimumWidth(150)


        self.x_label = QLabel("lambda (nm)")
        self.x0_label = QLabel("lambda0 (nm)")

        # pressure form
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

        self.add_button = QPushButton("+")
        self.add_button.setMinimumWidth(25)

        self.removelast_button = QPushButton("-")
        self.removelast_button.setMinimumWidth(25)

        self.table_button = QPushButton("P vs Pm")
        self.table_button.setMinimumWidth(70)
        self.table_button.setMinimumHeight(60)

        mini_actions_form = QVBoxLayout()
        actions_form = QHBoxLayout()

        mini_actions_form.addWidget(self.add_button)
        mini_actions_form.addWidget(self.removelast_button)
        actions_form.addLayout(mini_actions_form)
        actions_form.addWidget(self.table_button)

        Toolboxlayout.addLayout(calibration_form, stretch=1)

        # Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyVSeparator())
        # Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(param_form, stretch=5)

        # Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyVSeparator())
        # Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(pressure_form, stretch=2)

        # Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyVSeparator())
        # Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(actions_form, stretch=1)

        ToolboxGroup.setLayout(Toolboxlayout)
        top_panel_layout.addWidget(ToolboxGroup)



        # ? Toolbox connections
        self.table_button.clicked.connect(self.toggle_PvPm)


        self.Pm_spinbox.valueChanged.connect(self.update_toolbox)
        self.P_spinbox.valueChanged.connect(self.update_toolbox)

        self.x_spinbox.valueChanged.connect(self.update_toolbox)
        self.x0_spinbox.valueChanged.connect(self.update_toolbox)
        self.T_spinbox.valueChanged.connect(self.update_toolbox)
        self.T0_spinbox.valueChanged.connect(self.update_toolbox)

        self.add_button.clicked.connect(self.add_to_table)
        self.removelast_button.clicked.connect(self.removelast)

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

        CorrectionBox = QVBoxLayout()

        BgBox = QHBoxLayout()

        self.CHullBg_button = QPushButton("Auto Bg", self)
        #self.CHullBg_button.clicked.connect(self.CHull_Bg)
        # self.CHullBg_button.setStyleSheet("background-color : white")
        # self.CHullBg_button.setIcon(QIcon(os.path.dirname(__file__)+'/resources/icons/auto_bg.png'))
        # self.CHullBg_button.setIconSize(QSize(45,45))
        # self.CHullBg_button.setFixedSize(QSize(50,50))

        BgBox.addWidget(self.CHullBg_button, stretch=3)

        self.ManualBg_button = QPushButton("Manual Bg", self)
        self.ManualBg_button.setCheckable(True)
        self.ManualBg_button.clicked.connect(self.toggle_ManualBg)
        self.click_ManualBg_enabled = False
        self.ManualBg_points = []
        self.plotted_Bg_points = None
        self.current_spline = None
        BgBox.addWidget(self.ManualBg_button, stretch=3)

        self.ResetBg_button = QPushButton("Reset Bg", self)
        #self.ResetBg_button.clicked.connect(self.Reset_Bg)
        BgBox.addWidget(self.ResetBg_button, stretch=3)

        SmoothBox = QHBoxLayout()
        SmoothBox.addWidget(QLabel("Smoothing:", self), stretch=1)

        self.smoothing_factor = QDoubleSpinBox()
        self.smoothing_factor.setDecimals(0)
        self.smoothing_factor.setRange(1, +np.inf)
        self.smoothing_factor.setValue(1)
        
        SmoothBox.addWidget(self.smoothing_factor, stretch=1)

        self.Derivative_button = QPushButton("Toggle derivative", self)
        self.Derivative_button.clicked.connect(self.Toggle_derivative)
        self.Derivative_enabled = False
        SmoothBox.addWidget(self.Derivative_button, stretch=2)

        CorrectionBox.addLayout(BgBox)
        CorrectionBox.addLayout(SmoothBox)

        InteractionBox.addLayout(CorrectionBox)

        InteractionBox.addWidget(MyVSeparator())

        FitOptionBox = QVBoxLayout()

        FitButtonsBox = QVBoxLayout()

        self.fit_button = QPushButton("Fit", self)
        
        FitButtonsBox.addWidget(self.fit_button)

        self.click_fit_button = QPushButton("Click-to-fit", self)
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        self.click_fit_enabled = False
        FitButtonsBox.addWidget(self.click_fit_button)

        FitOptionBox.addLayout(FitButtonsBox)

        self.fit_model_combo = QComboBox()
        self.fit_model_combo.setObjectName("fit_model_combo")
        self.fit_model_combo.setMinimumWidth(100)
        

        self.fit_model_combo.currentIndexChanged.connect(self.update_fit_model)

        FitOptionBox.addWidget(self.fit_model_combo)

        InteractionBox.addLayout(FitOptionBox)

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

        self.add_fitted_button = QPushButton("Add fit to table")
        #self.add_fitted_button.clicked.connect(self.add_current_fit)
        FitBoxLayout.addWidget(self.add_fitted_button)

        #####################################################################################
        # #? Setup PvPm table and plotwindow

        self.data = HPDataTable()

        self.DataTableWindow = HPTableWindow(self.data, self.calibrations)

        self.PvPmPlotWindow = PmPPlotWindow(self.data, self.calibrations)

        self.data.changed.connect(self.DataTableWindow.table_widget.updatetable)
        self.data.changed.connect(self.PvPmPlotWindow.updateplot)


    #####################################################################################
    # ? Main window methods


    def closeEvent(self, event):
        for window in QApplication.topLevelWidgets():
            window.close()

    def switch_to_dark(self):
        try:
            with open("dark-mode.qss", "r") as file:
                qss = file.read()
                self.setStyleSheet(qss)
                self.DataTableWindow.setStyleSheet(qss)
                #self.PvPmPlotWindow.setStyleSheet(qss)
        except:
            pass
        self.plot_label_color = "white"

        # some parameters seem to be unaffected by the style import ...
        # thus we use the following fix

        self.PvPmPlotWindow.plot_graph.setBackground("#202020")
        styles = {"color": self.plot_label_color, "font-size": "16px"}
        self.PvPmPlotWindow.plot_graph.setLabel("left", "P (GPa)", **styles)
        self.PvPmPlotWindow.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
        self.data_widget.setBackground("#202020")
        self.data_widget.setLabel("left", **styles)
        self.data_widget.setLabel("bottom", **styles)
        self.deriv_widget.setBackground("#202020")
        self.deriv_widget.setLabel("left", **styles)
        self.deriv_widget.setLabel("bottom", **styles)
        self.PvPmPlotWindow.updateplot()

        #self.theme_switched.emit() #need to replot data ?

    def switch_to_light(self):
        try:
            with open("light-mode.qss", "r") as file:
                qss = file.read()
                self.setStyleSheet(qss)
                self.DataTableWindow.setStyleSheet(qss)
                #self.PvPmPlotWindow.setStyleSheet(qss)
        except:
            pass
        self.plot_label_color = "black"

        # some parameters seem to be unaffected by the style import ...
        # thus we use the following fix
        
        self.PvPmPlotWindow.plot_graph.setBackground("white")
        styles = {"color": self.plot_label_color, "font-size": "16px"}
        self.PvPmPlotWindow.plot_graph.setLabel("left", "P (GPa)", **styles)
        self.PvPmPlotWindow.plot_graph.setLabel("bottom", "Pm (bar)", **styles)

        self.data_widget.setBackground("white")
        self.data_widget.setLabel("left", **styles)
        self.data_widget.setLabel("bottom", **styles)
        self.deriv_widget.setBackground("white")
        self.deriv_widget.setLabel("left", **styles)
        self.deriv_widget.setLabel("bottom", **styles)
        self.PvPmPlotWindow.updateplot()

        #self.theme_switched.emit() #need to replot data ?

    def load_calibrations(self, calib_dict):
        self.calibrations = calib_dict
        #{a.name: a for a in calib_list}

    def load_fit_models(self, models_dict):
        self.fit_models = models_dict
        #{a.name: a for a in model_list}

    def startup_buffer(self):
        if self.calibrations is not None:
            self.buffer = HPData(
                Pm=0,
                P=0,
                x=694.28,
                T=298,
                x0=694.28,
                T0=298,
                calib=self.calibrations["Ruby2020"],
                file="No",
            )
            self.Pm_spinbox.setValue(self.buffer.Pm)
            self.P_spinbox.setValue(self.buffer.P)
            self.x_spinbox.setValue(self.buffer.x)
            self.T_spinbox.setValue(self.buffer.T)
            self.x0_spinbox.setValue(self.buffer.x0)
            self.T0_spinbox.setValue(self.buffer.T0)
            self.Tcor_Label.setText(self.buffer.calib.Tcor_name)
            self.calibration_combo.setCurrentText(self.buffer.calib.name)
            newind = self.calibration_combo.currentIndex()
            col1 = self.calibration_combo.model().item(newind).background().color().getRgb()
            self.calibration_combo.setStyleSheet(
                "background-color: rgba{};\
                        selection-background-color: k;".format(col1)
            )
        else:
            raise ImportError('Error loading calibrations.')


    def populate_calib_combo(self):
        if self.calibrations is not None:
            self.calibration_combo.addItems(self.calibrations.keys())

            for k, v in self.calibrations.items():
                ind = self.calibration_combo.findText(k)
                self.calibration_combo.model().item(ind).setBackground(QColor(v.color))
        else:
            raise ImportError('Error loading calibrations.')

    def populate_fit_models_combo(self):
        if self.fit_models is not None:
            self.fit_model_combo.addItems(self.fit_models.keys())

            for k, v in self.fit_models.items():
                ind = self.fit_model_combo.findText(k)
                self.fit_model_combo.model().item(ind).setBackground(QColor(v.color))
            
            col1 = (
            self.fit_model_combo.model()
            .item(self.fit_model_combo.currentIndex())
            .background()
            .color()
            .getRgb()
            )
            self.fit_model_combo.setStyleSheet(
                "background-color: rgba{};    selection-background-color: k;".format(col1)
            )
        else:
            raise ImportError('Erro loading fit models.')

    def add_to_table(self):
        self.buffer.file = "No"
        self.data.add(self.buffer)

    def removelast(self):
        if len(self.data) > 0:
            self.data.removelast()

        # update is called two time, not very good but working

    def update_toolbox(self, s):
        if self.P_spinbox.hasFocus():
            self.buffer.P = self.P_spinbox.value()

            try:
                self.buffer.invcalcP()
                self.x_spinbox.setValue(self.buffer.x)

                self.x_spinbox.setStyleSheet("background: #4a8542;")  # green
            except:
                self.x_spinbox.setStyleSheet("background: #ff7575;")  # red
        else:  # anything else than P has been manually changed:
            # read everything stupidly
            self.buffer.Pm = self.Pm_spinbox.value()
            self.buffer.x = self.x_spinbox.value()
            self.buffer.T = self.T_spinbox.value()
            self.buffer.x0 = self.x0_spinbox.value()
            self.buffer.T0 = self.T0_spinbox.value()

            try:
                self.buffer.calcP()
                self.P_spinbox.setValue(self.buffer.P)

                self.P_spinbox.setStyleSheet("background: #4a8542;")  # green
            except:
                self.P_spinbox.setStyleSheet("background: #ff7575;")  # red

    def update_calib(self, newind):
        self.buffer.calib = self.calibrations[self.calibration_combo.currentText()]

        self.Tcor_Label.setText(self.buffer.calib.Tcor_name)

        col1 = self.calibration_combo.model().item(newind).background().color().getRgb()
        self.calibration_combo.setStyleSheet(
            "background-color: rgba{};\
                    selection-background-color: k;".format(col1)
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

    def add_current_fit(self):
        if self.current_selected_file_index is not None:
            current_spectrum = self.file_list_model.data(
                self.current_selected_file_index, role=Qt.UserRole
            )
            if current_spectrum.fit_toolbox_config is not None:
                current_spectrum.fit_toolbox_config.file = current_spectrum.name
                current_spectrum.fit_toolbox_config.Pm = self.buffer.Pm
                self.data.add(current_spectrum.fit_toolbox_config)

    def Toggle_derivative(self, checked):
        if self.Derivative_enabled:
            self.splitter.widget(1).hide()
        else:
            self.splitter.widget(1).show()
        self.Derivative_enabled = not self.Derivative_enabled

    # @pyqtSlot()
    # def add_file(self):
    #     file_dialog = QFileDialog()
    #     file_dialog.setFileMode(QFileDialog.ExistingFiles)
    #     file_dialog.setNameFilter("Text and ASC files (*.txt *.asc);;All Files (*)")

    #     if file_dialog.exec_():
    #         selected_files = file_dialog.selectedFiles()
    #         for file in selected_files:
    #             file_info = QFileInfo(file)
    #             file_name = file_info.fileName()
    #             new_item = helpers.MySpectrumItem(file_name, file)

    #             new_item.data = helpers.customparse_file2data(file)
    #             new_item.normalize_data()
    #             new_item.current_smoothing = 1
    #             self.file_list_model.addItem(new_item)

    @pyqtSlot()
    def delete_file(self):
        selected_index = self.list_widget.currentIndex()
        if selected_index.isValid():
            self.file_list_model.deleteItem(selected_index.row())

    def select_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        dir_name = QFileDialog.getExistingDirectory(
            self, "Select Directory", options=options
        )
        if dir_name:
            self.dir_name = dir_name
            self.dir_label.setText(f"Selected directory: {dir_name}")

    # @pyqtSlot()
    # def load_latest_file(self):
    #     if hasattr(self, "dir_name"):
    #         file_names = [
    #             f
    #             for f in os.listdir(self.dir_name)
    #             if os.path.isfile(os.path.join(self.dir_name, f)) and ".asc" in f
    #         ]
    #         if file_names:
    #             file_names.sort(
    #                 key=lambda f: os.path.getmtime(os.path.join(self.dir_name, f))
    #             )
    #             latest_file_name = file_names[-1]
    #             file = os.path.join(self.dir_name, latest_file_name)
    #             file_info = QFileInfo(file)
    #             file_name = file_info.fileName()
    #             new_item = helpers.MySpectrumItem(file_name, file)

    #             new_item.data = helpers.customparse_file2data(file)
    #             new_item.normalize_data()
    #             new_item.current_smoothing = 1

    #             self.file_list_model.addItem(new_item)
    #         else:
    #             msg = QMessageBox()
    #             msg.setIcon(QMessageBox.Critical)
    #             msg.setText("No files in selected directory.")
    #             msg.setWindowTitle("Error")
    #             msg.exec_()
    #     else:
    #         msg = QMessageBox()
    #         msg.setIcon(QMessageBox.Critical)
    #         msg.setText("No directory selected.")
    #         msg.setWindowTitle("Error")
    #         msg.exec_()

    @pyqtSlot(QModelIndex)
    def item_clicked(self, index):
        selected_item = self.file_list_model.data(index, role=Qt.UserRole)
        self.current_file_path = selected_item.path
        self.current_file_label.setText(f"{self.current_file_path}")
        self.smoothing_factor.setValue(selected_item.current_smoothing)
        if selected_item.fit_toolbox_config is not None:
            self.buffer = deepcopy(selected_item.fit_toolbox_config)
            self.Pm_spinbox.setValue(self.buffer.Pm)
            self.P_spinbox.setValue(self.buffer.P)
            self.x_spinbox.setValue(self.buffer.x)
            self.T_spinbox.setValue(self.buffer.T)
            self.x0_spinbox.setValue(self.buffer.x0)
            self.T0_spinbox.setValue(self.buffer.T0)
            self.calibration_combo.setCurrentText(self.buffer.calib.name)
        #self.plot_data()
        if selected_item.fit_result is not None:
            self.plot_fit(selected_item)
        else:
            self.data_fit_line.setData([],[])
            self.data_widget.setTitle('Not fitted', color=self.plot_label_color, size="16pt")
        


    def move_up(self):
        selected_index = self.list_widget.currentIndex()
        # print(selected_index.row())
        # Check if there's a valid selection and if the selected index is not the first item
        if selected_index.isValid() and selected_index.row() > 0:
            # Get the row number of the selected item
            current_row = selected_index.row()

            # Get the item data of the selected item
            item = self.file_list_model.data(selected_index, role=Qt.UserRole)

            # Remove the item from the current position
            self.file_list_model.beginRemoveRows(QModelIndex(), current_row, current_row)
            del self.file_list_model.items[current_row]
            self.file_list_model.endRemoveRows()

            # Calculate the new row number after moving up
            new_row = current_row - 1

            # Insert the item at the new position
            self.file_list_model.beginInsertRows(QModelIndex(), new_row, new_row)
            self.file_list_model.items.insert(new_row, item)
            self.file_list_model.endInsertRows()

            # Select the item at the new position
            new_index = self.file_list_model.index(new_row, 0)
            self.list_widget.selectionModel().clearSelection()
            # self.list_widget.selectionModel().setCurrentIndex(selected_index, QItemSelectionModel.Deselect)

            self.list_widget.selectionModel().setCurrentIndex(
                new_index, QItemSelectionModel.Select
            )

    def move_down(self):
        selected_index = self.list_widget.currentIndex()

        # Check if there's a valid selection and if the selected index is not the first item
        if (
            selected_index.isValid()
            and selected_index.row() < self.file_list_model.rowCount()
        ):
            self.list_widget.selectionModel().clearSelection()
            # Get the row number of the selected item
            current_row = selected_index.row()

            # Get the item data of the selected item
            item = self.file_list_model.data(selected_index, role=Qt.UserRole)

            # Remove the item from the current position
            self.file_list_model.beginRemoveRows(QModelIndex(), current_row, current_row)
            del self.file_list_model.items[current_row]
            self.file_list_model.endRemoveRows()

            # Calculate the new row number after moving up
            new_row = current_row + 1

            # Insert the item at the new position
            self.file_list_model.beginInsertRows(QModelIndex(), new_row, new_row)
            self.file_list_model.items.insert(new_row, item)
            self.file_list_model.endInsertRows()

            # Select the item at the new position
            new_index = self.file_list_model.index(new_row, 0)
            self.list_widget.selectionModel().clearSelection()
            self.list_widget.selectionModel().setCurrentIndex(
                new_index, QItemSelectionModel.Select
            )


    def plot_data(self, x, y):
        self.data_widget.removeItem(self.data_edge_marker)
        self.deriv_widget.removeItem(self.deriv_edge_marker)
        self.data_widget.removeItem(self.data_fit_line)
        self.data_fit_line.setData([],[])
        self.data_widget.setTitle('Not fitted', color=self.plot_label_color, size="16pt")

        self.data_widget.setLabel("bottom", f"{self.buffer.calib.xname} ({self.buffer.calib.xunit})")
        self.data_widget.setLabel("left", 'Intensity')

        self.data_scatter.setData(x, y)
        self.data_widget.autoRange()

    # derivative data
        self.deriv_widget.setLabel("bottom", f"{self.buffer.calib.xname} ({self.buffer.calib.xunit})")
        self.deriv_widget.setLabel("left", 'Intensity')

        dI = gaussian_filter1d(y, mode="nearest", sigma=1, order=1)
        self.deriv_scatter.setData(x, dI)
        self.deriv_widget.autoRange()


    def update_fit_model(self):
        self.fit_mode = self.fit_models[self.fit_model_combo.currentText()]

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

            self.fit_mode = self.fit_models[self.fit_model_combo.currentText()]

            if self.current_selected_file_index is not None:
                current_spectrum = self.file_list_model.data(
                    self.current_selected_file_index, role=Qt.UserRole
                )
                current_spectrum.fit_model = self.fit_mode

            if current_spectrum.corrected_data is None:
                x = current_spectrum.data[:, 0]
                y = current_spectrum.data[:, 1]
            else:
                x = current_spectrum.corrected_data[:, 0]
                y = current_spectrum.corrected_data[:, 1]

            if self.fit_mode.type == "edge":
                best_x = x_click
                self.x_spinbox.setValue(best_x)
                res = {"opti": best_x, "cov": None}
                current_spectrum.fit_toolbox_config = deepcopy(self.buffer)
                current_spectrum.fit_result = res
                self.plot_fit(current_spectrum)

            elif self.fit_mode.type == "peak":
                res = self.do_fit(self.fit_mode, x, y, guess_peak=x_click)
                # print('done fit')
                current_spectrum.fit_toolbox_config = deepcopy(self.buffer)
                current_spectrum.fit_result = res
                self.plot_fit(current_spectrum)

            else:
                print("Click to fit not implemented")

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
            self.data_widget.setTitle(f"Fitted pressure : {P : > 10.2f} GPa", color=self.plot_label_color, size="16pt")

        elif fit_model.type == "edge":
            self.data_edge_marker.setValue(fit_result["opti"])
            self.data_widget.addItem(self.data_edge_marker)
            self.deriv_edge_marker.setValue(fit_result["opti"])
                
            self.deriv_widget.addItem(self.deriv_edge_marker)

            self.data_widget.setTitle(f"Fitted pressure : {P : > 10.2f} GPa", color=self.plot_label_color, size="16pt")
                                
        else:
                print("Plot fit not implemented")

    def fit_error_popup_window(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Attempted fit couldn't converge.")
        msg.setWindowTitle("Fit error")
        msg.exec_()

    def toggle_PvPm(self):
        if self.DataTableWindow.isVisible() or self.PvPmPlotWindow.isVisible():
            self.DataTableWindow.hide()
            self.PvPmPlotWindow.hide()
        else:
            self.DataTableWindow.show()
            self.PvPmPlotWindow.show()



    def toggle_ManualBg(self):
        if self.click_ManualBg_enabled and self.ManualBg_points != []:
            self.subtract_ManualBg()
            self.ManualBg_points = []
            self.data_bg_line.setData([],[])
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
        current_spectrum = self.file_list_model.data(
            self.current_selected_file_index, role=Qt.UserRole
        )
        if self.click_ManualBg_enabled:
            scene_coords = mouseClickEvent.scenePos()
            vb = self.data_widget.plotItem.vb
            if self.data_widget.sceneBoundingRect().contains(scene_coords):
                click_point = vb.mapSceneToView(scene_coords)
                x_click, y_click = click_point.x(), click_point.y()
            self.ManualBg_points.append([x_click, y_click])
            current_spectrum.bg = self.plot_ManualBg()

    def plot_ManualBg(self):
        interp = None
        current_spectrum = self.file_list_model.data(
            self.current_selected_file_index, role=Qt.UserRole
        )
        if current_spectrum.corrected_data is None:
            x = current_spectrum.data[:, 0]
            y = current_spectrum.data[:, 1]
        else:
            x = current_spectrum.corrected_data[:, 0]
            y = current_spectrum.corrected_data[:, 1]

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
            interp = spl(x)
            self.data_bg_line.setData(x,interp)
        return interp

    def subtract_ManualBg(self):
        current_spectrum = self.file_list_model.data(
            self.current_selected_file_index, role=Qt.UserRole
        )
        if current_spectrum.corrected_data is None:
            x = current_spectrum.data[:, 0]
            y = current_spectrum.data[:, 1]
        else:
            x = current_spectrum.corrected_data[:, 0]
            y = current_spectrum.corrected_data[:, 1]
        corrected = y - current_spectrum.bg
        current_spectrum.corrected_data = np.column_stack((x, corrected))
        self.plot_data()




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

# class CustomFileListModel(QAbstractListModel):
#     itemAdded = pyqtSignal()  # Signal emitted when an item is added
#     itemDeleted = pyqtSignal()  # Signal emitted when an item is deleted

#     def __init__(self, items=None, parent=None):
#         super().__init__(parent)
#         self.items = items or []

#     def rowCount(self, parent=QModelIndex()):
#         return len(self.items)

#     def data(self, index, role=Qt.DisplayRole):
#         if role == Qt.DisplayRole:
#             return self.items[index.row()].name
#         elif role == Qt.UserRole:
#             return self.items[index.row()]

#     def addItem(self, item):
#         self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
#         self.items.append(item)
#         self.endInsertRows()
#         self.itemAdded.emit()  # Emit signal to notify the view

#     def deleteItem(self, index):
#         self.beginRemoveRows(QModelIndex(), index, index)
#         del self.items[index]
#         self.endRemoveRows()
#         self.itemDeleted.emit()  # Emit signal to notify the view

if __name__ == "__main__":
    print("Only MainWindow was executed.")

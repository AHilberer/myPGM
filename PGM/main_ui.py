import os
import numpy as np
from copy import deepcopy
from scipy.optimize import curve_fit
from PyQt5.QtWidgets import (QMainWindow,
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
                             QSplitter)
from PyQt5.QtCore import QFileInfo, Qt, QModelIndex,QItemSelectionModel, pyqtSlot, QSize
from PyQt5.QtGui import QColor, QIcon

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import uniform_filter1d
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d

from fit_models import *
from PvPm_plot_window import *
from PvPm_table_window import *
from Parameter_window import *

import helpers
from calibrations import *

Setup_mode = True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()


        # Setup Main window parameters
        self.setWindowTitle("myPGM - PressureGaugeMonitor")
        x = 100
        y = 100
        width = 800
        height = 800
        self.setGeometry(x, y, width, height)
        #self.setWindowIcon(QIcon('resources/PGMicon.png'))

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

#####################################################################################
#? Calibrations setup
        
        self.calibrations = {a.name:a for a in calib_list}
#####################################################################################
#? Fit models setups
        
        self.models = {a.name:a for a in model_list}

#####################################################################################
# #? Exit button setup
        menubar = self.menuBar()
        exit_menu = menubar.addMenu(' Exit')

        exit_action = QAction(' Exit', self)
        exit_action.triggered.connect(self.close)
        exit_menu.addAction(exit_action)    

#####################################################################################
# #? Setup Parameters table window

        self.ParamWindow = ParameterWindow()
        param_menu = menubar.addMenu('Parameters')
        open_param_action = QAction('Change parameters', self)
        open_param_action.triggered.connect(self.toggle_params)
        param_menu.addAction(open_param_action)

#####################################################################################
        # this will be our initial state
        self.buffer = helpers.HPData(Pm = 0,
                                     P = 0,
                                     x = 694.28,
                                     T = 298,
                                     x0 = 694.28,
                                     T0 = 298,
                                     calib = self.calibrations['Ruby2020'],
                                     file = 'No')
 
        
     ##################################################################################### Main Top Panel ###################################################################################"" 
# #? PRL style toolbox
        ToolboxGroup = QGroupBox('Pressure toolbox')
        Toolboxlayout = QHBoxLayout()
        self.Pm_spinbox = QDoubleSpinBox()
        self.Pm_spinbox.setObjectName('Pm_spinbox')
        self.Pm_spinbox.setDecimals(2)
        self.Pm_spinbox.setRange(-np.inf, np.inf)
        self.Pm_spinbox.setSingleStep(.1)
        self.Pm_spinbox.setStyleSheet("background: #C5E1FC;")
        self.Pm_spinbox.setMinimumWidth(80)

        self.P_spinbox = QDoubleSpinBox()
        self.P_spinbox.setObjectName('P_spinbox')
        self.P_spinbox.setDecimals(3)
        self.P_spinbox.setRange(-np.inf, np.inf)
        self.P_spinbox.setSingleStep(.1)
        self.P_spinbox.setStyleSheet("background: #c6fcc5;")
        self.P_spinbox.setMinimumWidth(80)


        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setObjectName('x_spinbox')
        self.x_spinbox.setDecimals(2)
        self.x_spinbox.setRange(-np.inf, +np.inf)
        self.x_spinbox.setMinimumWidth(80)

        self.T_spinbox = QDoubleSpinBox()
        self.T_spinbox.setObjectName('T_spinbox')
        self.T_spinbox.setDecimals(0)
        self.T_spinbox.setRange(-np.inf, +np.inf)
        self.T_spinbox.setSingleStep(1)

        self.x0_spinbox = QDoubleSpinBox()
        self.x0_spinbox.setObjectName('x0_spinbox')
        self.x0_spinbox.setDecimals(2)
        self.x0_spinbox.setRange(-np.inf, +np.inf)

        self.T0_spinbox = QDoubleSpinBox()
        self.T0_spinbox.setObjectName('T0_spinbox')
        self.T0_spinbox.setDecimals(0)
        self.T0_spinbox.setRange(-np.inf, +np.inf)
        self.T0_spinbox.setSingleStep(1)


        self.calibration_combo = QComboBox()
        self.calibration_combo.setObjectName('calibration_combo')
        self.calibration_combo.setMinimumWidth(150)
        self.calibration_combo.addItems( self.calibrations.keys() )
        
        for k, v in self.calibrations.items():
            ind = self.calibration_combo.findText( k )
            self.calibration_combo.model().item(ind).setBackground(QColor(v.color))

        self.x_label = QLabel('lambda (nm)')
        self.x0_label = QLabel('lambda0 (nm)')

        # pressure form
        pressure_form = QFormLayout()
        pressure_form.addRow(QLabel('Pm (bar)'), self.Pm_spinbox)
        pressure_form.addRow(QLabel('P (GPa)'), self.P_spinbox)

        # Calib params form
        param_form = QHBoxLayout()
        form_x = QFormLayout()
        form_x.addRow(self.x_label, self.x_spinbox)
        form_x.addRow(self.x0_label, self.x0_spinbox)
        form_T = QFormLayout()
        form_T.addRow(QLabel('T (K)'), self.T_spinbox)
        form_T.addRow(QLabel('T0 (K)'), self.T0_spinbox)
        param_form.addLayout(form_x)
        param_form.addLayout(form_T)

        self.Tcor_Label = QLabel('NA')

        calibration_form = QFormLayout()
        calibration_form.addRow(QLabel('Calibration: '), self.calibration_combo)
        calibration_form.addRow(QLabel('T correction: '), self.Tcor_Label)


        self.add_button = QPushButton('+')
        self.add_button.setMinimumWidth(25)

        self.removelast_button = QPushButton('-')
        self.removelast_button.setMinimumWidth(25)

        self.table_button = QPushButton('P vs Pm')
        self.table_button.setMinimumWidth(70)
        self.table_button.setMinimumHeight(60)

        mini_actions_form = QVBoxLayout()
        actions_form = QHBoxLayout()

        mini_actions_form.addWidget(self.add_button)
        mini_actions_form.addWidget(self.removelast_button)
        actions_form.addLayout(mini_actions_form)
        actions_form.addWidget(self.table_button)

        Toolboxlayout.addLayout(calibration_form, stretch=1)

        #Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(helpers.MyVSeparator())
        #Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(param_form, stretch=5)

        #Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(helpers.MyVSeparator())
        #Toolboxlayout.addStretch()
        
        Toolboxlayout.addLayout(pressure_form, stretch=2)

        #Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(helpers.MyVSeparator())
        #Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(actions_form, stretch=1)

        ToolboxGroup.setLayout(Toolboxlayout)
        top_panel_layout.addWidget(ToolboxGroup)
    

        self.Pm_spinbox.setValue(self.buffer.Pm)
        self.P_spinbox.setValue(self.buffer.P)
        self.x_spinbox.setValue(self.buffer.x)
        self.T_spinbox.setValue(self.buffer.T)
        self.x0_spinbox.setValue(self.buffer.x0)
        self.T0_spinbox.setValue(self.buffer.T0)
        self.calibration_combo.setCurrentText(self.buffer.calib.name) 
        newind = self.calibration_combo.currentIndex()
        col1 = self.calibration_combo.model()\
                            .item(newind).background().color().getRgb() 
        self.calibration_combo.setStyleSheet("background-color: rgba{};\
                    selection-background-color: k;".format(col1))
        

#? Toolbox connections
        self.table_button.clicked.connect(self.toggle_PvPm)

        self.calibration_combo.currentIndexChanged.connect(self.update_calib)

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
#? Setup left part of bottom panel

        FileManagementBox = QGroupBox("File management")
        FileManagementLayout = QVBoxLayout()
        FileManagementBox.setLayout(FileManagementLayout)
        bottom_panel_layout.addWidget(FileManagementBox, stretch = 1)

#####################################################################################
#? Setup file loading section
        
        FileLoadLayout = QGridLayout()

        self.add_button = QPushButton("Add file", self)
        pixmapi = getattr(QStyle, 'SP_FileIcon')
        icon = self.style().standardIcon(pixmapi)
        self.add_button.setIcon(icon)
        self.add_button.clicked.connect(self.add_file)
        FileLoadLayout.addWidget(self.add_button, 0,0)

        self.delete_button = QPushButton("Delete file ", self)
        pixmapi = getattr(QStyle, 'SP_DialogDiscardButton')
        icon = self.style().standardIcon(pixmapi)
        self.delete_button.setIcon(icon)
        self.delete_button.clicked.connect(self.delete_file)
        FileLoadLayout.addWidget(self.delete_button, 0,1)
        
        self.selectdir_button = QPushButton("Select directory", self)
        pixmapi = getattr(QStyle, 'SP_DirIcon')
        icon = self.style().standardIcon(pixmapi)
        self.selectdir_button.setIcon(icon)
        self.selectdir_button.clicked.connect(self.select_directory)
        FileLoadLayout.addWidget(self.selectdir_button, 1,0)

        self.loadlatest_button = QPushButton("Load latest", self)
        pixmapi = getattr(QStyle, 'SP_BrowserReload')
        icon = self.style().standardIcon(pixmapi)
        self.loadlatest_button.setIcon(icon)
        self.loadlatest_button.clicked.connect(self.load_latest_file)
        FileLoadLayout.addWidget(self.loadlatest_button, 1,1)

        FileManagementLayout.addLayout(FileLoadLayout)



        self.custom_model = helpers.CustomFileListModel()
        self.list_widget = QListView(self)
        self.list_widget.setModel(self.custom_model)
        FileManagementLayout.addWidget(self.list_widget)
        self.list_widget.clicked.connect(self.item_clicked)
        self.current_selected_file_index = None
        self.list_widget.selectionModel().selectionChanged.connect(self.selection_changed)


        MoveLayout = QHBoxLayout()

        self.up_button = QPushButton("Move up", self)
        pixmapi = getattr(QStyle, 'SP_ArrowUp')
        icon = self.style().standardIcon(pixmapi)
        self.up_button.setIcon(icon)
        self.up_button.clicked.connect(self.move_up)
        MoveLayout.addWidget(self.up_button)

        self.down_button = QPushButton("Move down", self)
        pixmapi = getattr(QStyle, 'SP_ArrowDown')
        icon = self.style().standardIcon(pixmapi)
        self.down_button.setIcon(icon)
        self.down_button.clicked.connect(self.move_down)
        MoveLayout.addWidget(self.down_button)

        
        FileManagementLayout.addLayout(MoveLayout)


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



       #####################################################################################
#? Data correction + fit section

        datafitbox = QHBoxLayout()

        self.CHullBg_button = QPushButton(self)
        self.CHullBg_button.clicked.connect(self.CHull_Bg)

        self.CHullBg_button.setIcon(QIcon('./resources/icons/auto_bg.png'))
        self.CHullBg_button.setStyleSheet("background-color : white") 
        self.CHullBg_button.setIconSize(QSize(45,45))
        self.CHullBg_button.setFixedSize(QSize(50,50)) 

        datafitbox.addWidget(self.CHullBg_button, stretch=3)

        
        datafitbox.addWidget(QLabel('Smoothing:', self), stretch=1)

        self.smoothing_factor = QDoubleSpinBox()
        self.smoothing_factor.setDecimals(0)
        self.smoothing_factor.setRange(1, +np.inf)
        self.smoothing_factor.setValue(1)
        self.smoothing_factor.valueChanged.connect(self.smoothen)
        
        datafitbox.addWidget(self.smoothing_factor, stretch=3)

        FitBoxLayout.addLayout(datafitbox)


        self.fit_button = QPushButton("Fit", self)
        self.fit_button.clicked.connect(self.fit)
        datafitbox.addWidget(self.fit_button)

        self.fit_model_combo = QComboBox()
        self.fit_model_combo.setObjectName('fit_model_combo')
        self.fit_model_combo.setMinimumWidth(100)
        self.fit_model_combo.addItems( self.models.keys() )
        for k, v in self.models.items():
            ind = self.fit_model_combo.findText( k )
            self.fit_model_combo.model().item(ind).setBackground(QColor(v.color))

        self.fit_model_combo.currentIndexChanged.connect(self.update_fit_model)
        self.update_fit_model()
        datafitbox.addWidget(self.fit_model_combo)
        
        self.click_fit_button = QPushButton("Click-to-Fit", self)
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        datafitbox.addWidget(self.click_fit_button)
        self.click_enabled = False

        FitBoxLayout.addLayout(datafitbox)

 

        #####################################################################################
# #? Setup data plotting section
        PlotLayout = QVBoxLayout()
        splitter = QSplitter(Qt.Vertical)

        datawidget = QWidget()
        DataPlotBoxLayout = QVBoxLayout()

        spectrum_plot = MplCanvas(self)
        self.axes = spectrum_plot.axes
        self.figure = spectrum_plot.figure
        self.canvas = FigureCanvas(self.figure)
        self.axes.set_ylabel('Intensity')
        self.axes.set_xlabel('spectral unit')

        toolbar = NavigationToolbar(self.canvas, self)
        DataPlotBoxLayout.addWidget(self.canvas)
        DataPlotBoxLayout.addWidget(toolbar)
        self.canvas.mpl_connect('button_press_event', self.click_fit)

        datawidget.setLayout(DataPlotBoxLayout)        

#####################################################################################
# #? Setup derivative plotting section
        
        derivwidget = QWidget()
        DataPlotBoxLayout = QVBoxLayout()

        deriv_plot = MplCanvas(self)
        self.deriv_axes = deriv_plot.axes
        self.deriv_figure = deriv_plot.figure
        self.deriv_canvas = FigureCanvas(self.deriv_figure)
        self.deriv_axes.set_ylabel('Intensity')
        self.deriv_axes.set_xlabel('spectral unit')

        deriv_toolbar = NavigationToolbar(self.deriv_canvas, self)
        DataPlotBoxLayout.addWidget(self.deriv_canvas)
        DataPlotBoxLayout.addWidget(deriv_toolbar)
        self.deriv_canvas.mpl_connect('button_press_event', self.click_fit)
        derivwidget.setLayout(DataPlotBoxLayout)     
        
        splitter.addWidget(datawidget)
        splitter.addWidget(derivwidget)
        PlotLayout.addWidget(splitter)
        splitter.setSizes([300,200])
        #splitter.setStyleSheet("QSplitter::handle {background: rgb(55, 100, 110);} ")
        FitBoxLayout.addLayout(PlotLayout)



        self.add_fitted_button = QPushButton("Add current fit")
        self.add_fitted_button.clicked.connect(self.add_current_fit)
        FitBoxLayout.addWidget(self.add_fitted_button)


#####################################################################################
# #? Setup PvPm table and plotwindow

        self.data = helpers.HPDataTable()       

        self.DataTableWindow = HPTableWindow(self.data, self.calibrations)

        #self.PvPmPlot = PvPmPlotWindow()
        self.PvPmPlotWindow = PmPPlotWindow(self.data, self.calibrations)

        self.data.changed.connect(self.DataTableWindow.table_widget.updatetable)
        self.data.changed.connect(self.PvPmPlotWindow.updateplot)


# #####################################################################################
# #? Create special startup config for debugging

        if Setup_mode :
            example_files = ['Example_diam_Raman.asc','Example_Ruby_1.asc','Example_Ruby_2.asc', 'Example_Ruby_3.asc', 'Example_H2.txt']
            for i, file in enumerate(example_files):
                latest_file_path= os.path.dirname(__file__)+'/resources/'+file

                file_info = QFileInfo(latest_file_path)
                file_name = file_info.fileName()
                list_item = helpers.MySpectrumItem(file_name, latest_file_path)


                list_item.data = helpers.customparse_file2data(latest_file_path)
                list_item.normalize_data()
                
                self.custom_model.addItem(list_item)
                list_item.current_smoothing = self.smoothing_factor.value()
                self.plot_data()


#####################################################################################
#? Main window methods
                
    def add_to_table(self):
        self.buffer.file = 'No'
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
            
                self.x_spinbox.setStyleSheet("background: #c6fcc5;") # green
            except:
                self.x_spinbox.setStyleSheet("background: #ff7575;") # red
        else: # anything else than P has been manually changed:
            # read everything stupidly
            self.buffer.Pm = self.Pm_spinbox.value()
            self.buffer.x = self.x_spinbox.value()
            self.buffer.T = self.T_spinbox.value()
            self.buffer.x0 = self.x0_spinbox.value()
            self.buffer.T0 = self.T0_spinbox.value()

            try:
                self.buffer.calcP()
                self.P_spinbox.setValue(self.buffer.P)
                
                self.P_spinbox.setStyleSheet("background: #c6fcc5;") # green
            except:
                self.P_spinbox.setStyleSheet("background: #ff7575;") # red
            


    def update_calib(self, newind):
        self.buffer.calib = self.calibrations[ self.calibration_combo.currentText() ]

        self.Tcor_Label.setText( self.buffer.calib.Tcor_name )

        col1 = self.calibration_combo.model()\
                            .item(newind).background().color().getRgb() 
        self.calibration_combo.setStyleSheet("background-color: rgba{};\
                    selection-background-color: k;".format(col1))

        self.x_label.setText('{} ({})'.format(self.buffer.calib.xname, 
                                                    self.buffer.calib.xunit))
        self.x0_label.setText('{}0 ({})'.format(self.buffer.calib.xname, 
                                                    self.buffer.calib.xunit))

        self.x_spinbox.setSingleStep(self.buffer.calib.xstep)
        self.x0_spinbox.setSingleStep(self.buffer.calib.xstep)
        # note that this should call update() but it does not at __init__ !!
        self.x0_spinbox.setValue(self.buffer.calib.x0default) 

        #self.plot_data() # a priori no need to call plot_data here


    def add_current_fit(self):
        if self.current_selected_file_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
            if current_spectrum.fit_toolbox_config is not None:
                current_spectrum.fit_toolbox_config.file = current_spectrum.name
                self.data.add(current_spectrum.fit_toolbox_config)

    def toggle_params(self, checked):
        if self.ParamWindow.isVisible():
            self.ParamWindow.hide()

        else:
            self.ParamWindow.show()


    @pyqtSlot()
    def add_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            for file in selected_files:
                file_info = QFileInfo(file)
                file_name = file_info.fileName()
                new_item = helpers.MySpectrumItem(file_name, file)

                new_item.data = helpers.customparse_file2data(file)
                new_item.normalize_data()
                new_item.current_smoothing = 1
                self.custom_model.addItem(new_item)
                
    
    @pyqtSlot()
    def delete_file(self):
        selected_index = self.list_widget.currentIndex()
        if selected_index.isValid():
            self.custom_model.deleteItem(selected_index.row())

    def select_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        dir_name = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)
        if dir_name:
            self.dir_name = dir_name
            self.dir_label.setText(f"Selected directory: {dir_name}")

    @pyqtSlot()
    def load_latest_file(self):
        if hasattr(self, 'dir_name'):
            file_names = [f for f in os.listdir(self.dir_name) if os.path.isfile(os.path.join(self.dir_name, f)) and '.asc' in f]
            if file_names:
                file_names.sort(key=lambda f: os.path.getmtime(os.path.join(self.dir_name, f)))
                latest_file_name = file_names[-1]
                file = os.path.join(self.dir_name, latest_file_name)
                file_info = QFileInfo(file)
                file_name = file_info.fileName()
                new_item = helpers.MySpectrumItem(file_name, file)

                new_item.data = helpers.customparse_file2data(file)
                new_item.normalize_data()
                new_item.current_smoothing = 1

                self.custom_model.addItem(new_item)
            else:
                msg=QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("No files in selected directory.")
                msg.setWindowTitle("Error")
                msg.exec_()
        else:
            msg=QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No directory selected.")
            msg.setWindowTitle("Error")
            msg.exec_()
    

    @pyqtSlot(QModelIndex)
    def item_clicked(self, index):
        selected_item = self.custom_model.data(index, role=Qt.UserRole)
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
        self.plot_data()
        if selected_item.fit_result is not None:
            self.plot_fit(selected_item)
    
    @pyqtSlot()
    def selection_changed(self):
        # Update the current_selected_index when the selection changes
        selected_index = self.list_widget.currentIndex()
        if selected_index.isValid():
            self.current_selected_file_index = selected_index
        else:
            self.current_selected_file_index = None

    def move_up(self):
        selected_index = self.list_widget.currentIndex()
        #print(selected_index.row())
        # Check if there's a valid selection and if the selected index is not the first item
        if selected_index.isValid() and selected_index.row() > 0:
            # Get the row number of the selected item
            current_row = selected_index.row()

            # Get the item data of the selected item
            item = self.custom_model.data(selected_index, role=Qt.UserRole)

            # Remove the item from the current position
            self.custom_model.beginRemoveRows(QModelIndex(), current_row, current_row)
            del self.custom_model.items[current_row]
            self.custom_model.endRemoveRows()

            # Calculate the new row number after moving up
            new_row = current_row - 1

            # Insert the item at the new position
            self.custom_model.beginInsertRows(QModelIndex(), new_row, new_row)
            self.custom_model.items.insert(new_row, item)
            self.custom_model.endInsertRows()

            # Select the item at the new position
            new_index = self.custom_model.index(new_row, 0)
            self.list_widget.selectionModel().clearSelection()
            #self.list_widget.selectionModel().setCurrentIndex(selected_index, QItemSelectionModel.Deselect)

            self.list_widget.selectionModel().setCurrentIndex(new_index, QItemSelectionModel.Select)


    def move_down(self):
        selected_index = self.list_widget.currentIndex()

        # Check if there's a valid selection and if the selected index is not the first item
        if selected_index.isValid() and selected_index.row() < self.custom_model.rowCount():
            self.list_widget.selectionModel().clearSelection()
            # Get the row number of the selected item
            current_row = selected_index.row()

            # Get the item data of the selected item
            item = self.custom_model.data(selected_index, role=Qt.UserRole)

            # Remove the item from the current position
            self.custom_model.beginRemoveRows(QModelIndex(), current_row, current_row)
            del self.custom_model.items[current_row]
            self.custom_model.endRemoveRows()

            # Calculate the new row number after moving up
            new_row = current_row + 1

            # Insert the item at the new position
            self.custom_model.beginInsertRows(QModelIndex(), new_row, new_row)
            self.custom_model.items.insert(new_row, item)
            self.custom_model.endInsertRows()

            # Select the item at the new position
            new_index = self.custom_model.index(new_row, 0)
            self.list_widget.selectionModel().clearSelection()
            self.list_widget.selectionModel().setCurrentIndex(new_index, QItemSelectionModel.Select)

    def plot_data(self):
        if self.current_selected_file_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
            if hasattr(current_spectrum, 'data'):
                # spectral data
                self.axes.clear()
                self.axes.set_ylabel('Intensity')
                self.axes.set_xlabel(f'{self.buffer.calib.xname} ({self.buffer.calib.xunit})')
                if current_spectrum.corrected_data is None:
                    self.axes.scatter(current_spectrum.data[:,0], 
                                      current_spectrum.data[:,1],
                                      c = 'gray', 
                                      s = 5)
                else :
                    self.axes.scatter(current_spectrum.corrected_data[:,0], 
                                      current_spectrum.corrected_data[:,1],
                                      c = 'gray', 
                                      s = 5)
                self.canvas.draw()

                # derivative data
                self.deriv_axes.clear()
                self.deriv_axes.set_ylabel(r'dI/d$\nu$')
                self.deriv_axes.set_xlabel(f'{self.buffer.calib.xname} ({self.buffer.calib.xunit})')
                if current_spectrum.corrected_data is None:
                    x=current_spectrum.data[:,0]
                    y=current_spectrum.data[:,1]
                else :
                    x=current_spectrum.corrected_data[:,0]
                    y=current_spectrum.corrected_data[:,1]
                dI = gaussian_filter1d(y,mode='nearest', sigma=1, order=1)
                self.deriv_axes.scatter(x,dI,c = "gray",s = 5)
                self.deriv_canvas.draw()

    def smoothen(self):
        if self.current_selected_file_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
            smooth_window = int(self.smoothing_factor.value()//1)
            current_spectrum.current_smoothing = self.smoothing_factor.value()
            current_spectrum.corrected_data = np.column_stack((current_spectrum.data[:,0],uniform_filter1d(current_spectrum.data[:,1], size=smooth_window)))
            self.plot_data() 
            if current_spectrum.fit_result is not None:
                self.plot_fit(current_spectrum)
    
    def update_fit_model(self):
        col1 = self.fit_model_combo.model().item(
            self.fit_model_combo.currentIndex()).background().color().getRgb()
        self.fit_model_combo.setStyleSheet("background-color: rgba{};    selection-background-color: k;".format(col1))

        fit_mode  = self.fit_model_combo.currentText()


    def fit(self):
        fit_mode  = self.models[ self.fit_model_combo.currentText() ]
        if self.current_selected_file_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
            current_spectrum.fit_model = fit_mode

            if current_spectrum.corrected_data is None:
                x=current_spectrum.data[:,0]
                y=current_spectrum.data[:,1]
            else :
                x=current_spectrum.corrected_data[:,0]
                y=current_spectrum.corrected_data[:,1]

            res = self.do_fit(fit_mode, x, y)
            current_spectrum.fit_toolbox_config = deepcopy(self.buffer)
            current_spectrum.fit_result = res
            self.plot_fit(current_spectrum)


    def do_fit(self, model, x, y, guess_peak=None):
        
        if model.type == 'peak':
            try:
                popt, pcov = curve_fit(model.func, x, y, p0=model.get_pinit(x, y, guess_peak=guess_peak))
            
        # for now we use the number of args..
                if len(popt) < 7:       # Samarium
                    best_x = popt[2] 
                elif len(popt) < 8:     # Ruby Gaussian
                    best_x = np.max([ popt[2], popt[5] ])
                else:                   # Ruby Voigt
                    best_x = np.max([ popt[2], popt[6] ])

                self.x_spinbox.setValue(best_x)
                return {"opti":popt,"cov":pcov}
            
            except RuntimeError:
                msg=QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("Attempted fit couldn't converge.")
                msg.setWindowTitle("Fit error")
                msg.exec_()
                return
            else:
                return
        elif model.type == 'edge':
            grad = np.gradient(y)
            best_x = x[np.argmin(grad)]
            self.x_spinbox.setValue(best_x)
            return {"opti":best_x,"cov":None}

    def toggle_click_fit(self):
        self.click_enabled = not self.click_enabled
        
    def click_fit(self, event):
        if self.click_enabled and event.button == 1 and event.inaxes:
            x_click, y_click = event.xdata, event.ydata

            fit_mode  = self.models[ self.fit_model_combo.currentText() ]

            if self.current_selected_file_index is not None:
                current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
                current_spectrum.fit_model = fit_mode

            if current_spectrum.corrected_data is None:
                x=current_spectrum.data[:,0]
                y=current_spectrum.data[:,1]
            else :
                x=current_spectrum.corrected_data[:,0]
                y=current_spectrum.corrected_data[:,1]

            if fit_mode.type == 'edge':
                best_x = x_click
                self.x_spinbox.setValue(best_x)
                res =  {"opti":best_x,"cov":None}
                current_spectrum.fit_toolbox_config = deepcopy(self.buffer)
                current_spectrum.fit_result = res
                self.plot_fit(current_spectrum)


            elif fit_mode.type == 'peak':
                res = self.do_fit(fit_mode, x, y, guess_peak=x_click)
                #print('done fit')
                current_spectrum.fit_toolbox_config = deepcopy(self.buffer)
                current_spectrum.fit_result = res
                self.plot_fit(current_spectrum)

            else:
                print('Click to fit not implemented')

            self.toggle_click_fit()
            self.click_fit_button.setChecked(False)


    def plot_fit(self, my_spectrum):
        if my_spectrum.fit_result is not None:
            # any previous fit will be cleared,
            # previously plotted raw data will NOT be cleared
            _ = [l.remove() for l in self.axes.lines]
            _ = [l.remove() for l in self.deriv_axes.lines]
            if my_spectrum.corrected_data is None:
                x=my_spectrum.data[:,0]
                y=my_spectrum.data[:,1]
            else :
                x=my_spectrum.corrected_data[:,0]
                y=my_spectrum.corrected_data[:,1]

            if my_spectrum.fit_model.type == 'peak':
                fitted = [my_spectrum.fit_model.func(wvl, *my_spectrum.fit_result['opti']) for wvl in x]
                self.axes.plot(x, 
                               fitted, 
                               '-',
                               c = 'r', 
                               label='best fit')
                self.axes.set_title(f'Fitted pressure : {my_spectrum.fit_toolbox_config.P : > 10.2f} GPa')
                self.axes.legend(frameon=False)
                self.canvas.draw()
            
            elif my_spectrum.fit_model.type == 'edge':
                self.axes.axvline(my_spectrum.fit_result['opti'], color='red', ls='--', label='edge')
                self.deriv_axes.axvline(my_spectrum.fit_result['opti'], color='red', ls='--', label='edge')
                self.axes.set_title(f'Fitted pressure : {my_spectrum.fit_toolbox_config.P : > 10.2f} GPa')
                self.axes.legend(frameon=False)
                self.canvas.draw()
                self.deriv_canvas.draw()
            else:
                print('Plot fit not implemented')

    def toggle_PvPm(self):
        if self.DataTableWindow.isVisible() or self.PvPmPlotWindow.isVisible():
            self.DataTableWindow.hide()
            self.PvPmPlotWindow.hide()
        else:
            self.DataTableWindow.show()
            self.PvPmPlotWindow.show()

    def CHull_Bg(self):
        current_spectrum = self.custom_model.data(self.current_selected_file_index, role=Qt.UserRole)
        if current_spectrum.corrected_data is None:
            x=current_spectrum.data[:,0]
            y=current_spectrum.data[:,1]
        else :
            x=current_spectrum.corrected_data[:,0]
            y=current_spectrum.corrected_data[:,1]
        
        v = ConvexHull(np.column_stack((x,y))).vertices
        v = np.roll(v, -v.argmin())
        anchors = v[:v.argmax()]
        bg = np.interp(x, x[anchors], y[anchors])
        corrected = y - bg

        current_spectrum.corrected_data = np.column_stack((x,corrected))
        self.plot_data()


import os
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow,
                             QLabel,
                             QPushButton,
                             QFileDialog,
                             QWidget,
                             QComboBox,
                             QVBoxLayout,
                             QHBoxLayout,
                             QTableWidgetItem,
                             QDoubleSpinBox,
                             QGroupBox,
                             QTableView,
                             QStyledItemDelegate,
                             QLineEdit,
                             QMessageBox, 
                             QAction,
                             QListView,
                             QGridLayout,
                             QStyle,
                             QFormLayout,
                             QFrame
                             
                             )
from PyQt5.QtCore import QFileInfo, Qt, QAbstractListModel, QModelIndex, pyqtSignal,QItemSelectionModel, pyqtSlot
from PyQt5.QtGui import QColor

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import uniform_filter1d
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d

from pressure_models import *
from PvPm_plot_window import *
from PvPm_table_window import *
from Parameter_window import *

from plot_canvas import *

import helpers
import calibfuncs
from calibrations import *

Setup_mode = True


class MyQSeparator(QFrame):
	def __init__(self):
		super().__init__()
		self.setFrameShape(QFrame.HLine)
		self.setFrameShadow(QFrame.Sunken)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()


        # Setup Main window parameters
        self.setWindowTitle("myPGM - PressureGaugeMonitor")
        self.setGeometry(100, 100, 800, 1000)
        #self.setWindowIcon(QIcon('resources/PGMicon.png'))

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Use a QHBoxLayout for the main layout
        main_layout = QHBoxLayout(central_widget)


        # Create a new panel on the left
        left_panel_layout = QVBoxLayout()
        main_layout.addLayout(left_panel_layout)

        # Create a new panel on the right
        right_panel_layout = QVBoxLayout()
        main_layout.addLayout(right_panel_layout)

#####################################################################################
#? Calibrations setup
        
        calib_list = [Ruby2020, 
					  SamariumDatchi, 
					  Akahama2006, 
					  cBNDatchi]
        
        self.calibrations = {a.name:a for a in calib_list}

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
 
        
        ##################################################################################### Main left Panel ###################################################################################"" 

#####################################################################################
#? Setup file loading section

        FileBox = QGroupBox("File management")
        FileBoxLayout = QGridLayout()

        self.add_button = QPushButton("Add file", self)
        pixmapi = getattr(QStyle, 'SP_FileIcon')
        icon = self.style().standardIcon(pixmapi)
        self.add_button.setIcon(icon)
        self.add_button.clicked.connect(self.add_file)
        FileBoxLayout.addWidget(self.add_button, 0,0)

        self.delete_button = QPushButton("Delete file ", self)
        pixmapi = getattr(QStyle, 'SP_DialogDiscardButton')
        icon = self.style().standardIcon(pixmapi)
        self.delete_button.setIcon(icon)
        self.delete_button.clicked.connect(self.delete_file)
        FileBoxLayout.addWidget(self.delete_button, 0,1)
        
        self.selectdir_button = QPushButton("Select directory", self)
        pixmapi = getattr(QStyle, 'SP_DirIcon')
        icon = self.style().standardIcon(pixmapi)
        self.selectdir_button.setIcon(icon)
        self.selectdir_button.clicked.connect(self.select_directory)
        FileBoxLayout.addWidget(self.selectdir_button, 1,0)

        self.loadlatest_button = QPushButton("Load latest", self)
        pixmapi = getattr(QStyle, 'SP_BrowserReload')
        icon = self.style().standardIcon(pixmapi)
        self.loadlatest_button.setIcon(icon)
        self.loadlatest_button.clicked.connect(self.load_latest_file)
        FileBoxLayout.addWidget(self.loadlatest_button, 1,1)

        FileBox.setLayout(FileBoxLayout)
        left_panel_layout.addWidget(FileBox)



        self.custom_model = helpers.CustomFileListModel()
        self.list_widget = QListView(self)
        self.list_widget.setModel(self.custom_model)
        left_panel_layout.addWidget(self.list_widget)
        self.list_widget.clicked.connect(self.item_clicked)
        self.current_selected_index = None
        self.list_widget.selectionModel().selectionChanged.connect(self.selection_changed)


        MoveBox = QGroupBox()
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

        MoveBox.setLayout(MoveLayout)
        left_panel_layout.addWidget(MoveBox)



        ##################################################################################### Main right Panel ###################################################################################"" 
# #? PRL style toolbox
        ToolboxGroup = QGroupBox('Pressure Toolbox')
        Toolboxlayout = QVBoxLayout()
        self.Pm_spinbox = QDoubleSpinBox()
        self.Pm_spinbox.setObjectName('Pm_spinbox')
        self.Pm_spinbox.setDecimals(2)
        self.Pm_spinbox.setRange(-np.inf, np.inf)
        self.Pm_spinbox.setSingleStep(.1)

        self.P_spinbox = QDoubleSpinBox()
        self.P_spinbox.setObjectName('P_spinbox')
        self.P_spinbox.setDecimals(3)
        self.P_spinbox.setRange(-np.inf, np.inf)
        self.P_spinbox.setSingleStep(.1)

        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setObjectName('x_spinbox')
        self.x_spinbox.setDecimals(3)
        self.x_spinbox.setRange(-np.inf, +np.inf)

        self.T_spinbox = QDoubleSpinBox()
        self.T_spinbox.setObjectName('T_spinbox')
        self.T_spinbox.setDecimals(0)
        self.T_spinbox.setRange(-np.inf, +np.inf)
        self.T_spinbox.setSingleStep(1)

        self.x0_spinbox = QDoubleSpinBox()
        self.x0_spinbox.setObjectName('x0_spinbox')
        self.x0_spinbox.setDecimals(3)
        self.x0_spinbox.setRange(-np.inf, +np.inf)

        self.T0_spinbox = QDoubleSpinBox()
        self.T0_spinbox.setObjectName('T0_spinbox')
        self.T0_spinbox.setDecimals(0)
        self.T0_spinbox.setRange(-np.inf, +np.inf)
        self.T0_spinbox.setSingleStep(1)


        self.calibration_combo = QComboBox()
        self.calibration_combo.setObjectName('calibration_combo')
        self.calibration_combo.setMinimumWidth(100)
        self.calibration_combo.addItems( self.calibrations.keys() )
		
        for k, v in self.calibrations.items():
            ind = self.calibration_combo.findText( k )
            self.calibration_combo.model().item(ind).setBackground(QColor(v.color))

        self.x_label = QLabel('lambda (nm)')
        self.x0_label = QLabel('lambda0 (nm)')

		# pressure form
        pressure_form = QHBoxLayout()
        pressure_form.addWidget(QLabel('Pm (bar)'))
        pressure_form.addWidget(self.Pm_spinbox)
        pressure_form.addWidget(QLabel('P (GPa)'))
        pressure_form.addWidget(self.P_spinbox)


		# Calib params form
        param_form = QGridLayout()
        param_form.addWidget(self.x_label, 0, 0)
        param_form.addWidget(self.x_spinbox, 0, 1)
        param_form.addWidget(self.x0_label, 0, 2)
        param_form.addWidget(self.x0_spinbox, 0, 3)

        param_form.addWidget(QLabel('T (K)'), 1, 0)
        param_form.addWidget(self.T_spinbox, 1, 1)
        param_form.addWidget(QLabel('T0 (K)'), 1, 2)
        param_form.addWidget(self.T0_spinbox, 1, 3)


        self.Tcor_Label = QLabel('NA')

        calibration_form = QFormLayout()
        calibration_form.addRow(QLabel('Calibration: '), self.calibration_combo)
        calibration_form.addRow(QLabel('T correction: '), self.Tcor_Label)


        self.add_button = QPushButton('+')
        self.add_button.setMinimumWidth(25)

        self.removelast_button = QPushButton('-')
        self.removelast_button.setMinimumWidth(25)

        self.table_button = QPushButton('Table')
        self.table_button.setMinimumWidth(70)

        self.PmPplot_button = QPushButton('P vs Pm')
        self.PmPplot_button.setMinimumWidth(70)

        actions_form = QHBoxLayout()

        actions_form.addWidget(self.add_button)
        actions_form.addWidget(self.removelast_button)
        actions_form.addWidget(self.table_button)
        actions_form.addWidget(self.PmPplot_button)

        Toolboxlayout.addLayout(pressure_form)

        Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyQSeparator())
        Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(param_form)

        Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyQSeparator())
        Toolboxlayout.addStretch()
		
        Toolboxlayout.addLayout(calibration_form)

        Toolboxlayout.addStretch()
        Toolboxlayout.addWidget(MyQSeparator())
        Toolboxlayout.addStretch()

        Toolboxlayout.addLayout(actions_form)

        ToolboxGroup.setLayout(Toolboxlayout)
        right_panel_layout.addWidget(ToolboxGroup)
	

#? Toolbox connections
        self.table_button.clicked.connect(self.toggle_PvPm)

        #####################################################################################
# #? Setup loaded file info section

        FitBoxGroup = QGroupBox("File fitting")
        FitBoxLayout = QVBoxLayout()

        FileInfoBoxLayout = QVBoxLayout()
        self.current_file_label = QLabel("No file selected", self)
        FileInfoBoxLayout.addWidget(self.current_file_label)

        self.dir_label = QLabel("No directory selected", self)
        FileInfoBoxLayout.addWidget(self.dir_label)

        FitBoxLayout.addLayout(FileInfoBoxLayout)



       #####################################################################################
#? Data correction section

        CorrectionBoxLayout = QHBoxLayout()

        self.CHullBg_button = QPushButton("CHull Background", self)
        self.CHullBg_button.clicked.connect(self.CHull_Bg)
        CorrectionBoxLayout.addWidget(self.CHullBg_button, stretch=3)

        
        CorrectionBoxLayout.addWidget(QLabel('Smoothing window:', self), stretch=1)

        self.smoothing_factor = QDoubleSpinBox()
        self.smoothing_factor.setDecimals(0)
        self.smoothing_factor.setRange(1, +np.inf)
        self.smoothing_factor.setValue(1)
        self.smoothing_factor.valueChanged.connect(self.smoothen)
        CorrectionBoxLayout.addWidget(self.smoothing_factor, stretch=3)

        FitBoxLayout.addLayout(CorrectionBoxLayout)


        #####################################################################################
#? Setup Fitting section


        FitButtonsLayout = QHBoxLayout()

        self.fit_button = QPushButton("Fit", self)
        self.fit_button.clicked.connect(self.fit)
        FitButtonsLayout.addWidget(self.fit_button)

        self.fit_type_selector = QComboBox(self)
        self.fit_type_selector.addItems(['Ruby', 'Samarium', 'Raman'])
        gauge_colors = ['lightcoral', 'royalblue', 'darkgrey']
        for ind in range(len(['Ruby', 'Samarium', 'Raman'])):
            self.fit_type_selector.model().item(ind).setBackground(QColor(gauge_colors[ind]))

        self.fit_type_selector.currentIndexChanged.connect(self.update_fit_type)
        self.update_fit_type()
        FitButtonsLayout.addWidget(self.fit_type_selector)
        
        self.click_fit_button = QPushButton("Enable Click-to-Fit", self)
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        FitButtonsLayout.addWidget(self.click_fit_button)
        self.click_enabled = False

        FitBoxLayout.addLayout(FitButtonsLayout)

 

        #####################################################################################
# #? Setup data plotting section

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

        FitBoxLayout.addLayout(DataPlotBoxLayout)

#####################################################################################
# #? Setup derivative plotting section

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

        FitBoxLayout.addLayout(DataPlotBoxLayout)

        self.add_fitted_button = QPushButton("Add current fit")
        self.add_fitted_button.clicked.connect(self.add_current_fit)
        FitBoxLayout.addWidget(self.add_fitted_button)

        FitBoxGroup.setLayout(FitBoxLayout)
        right_panel_layout.addWidget(FitBoxGroup)
        # Add the nested QVBoxLayout to the main layout

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
            example_files = ['Example_diam_Raman.asc','Example_Ruby_1.asc','Example_Ruby_2.asc', 'Example_Ruby_3.asc']
            for i, file in enumerate(example_files):
                latest_file_path= os.path.dirname(__file__)+'/resources/'+file

                file_info = QFileInfo(latest_file_path)
                file_name = file_info.fileName()
                list_item = helpers.MySpectrumItem(file_name, latest_file_path)

                with open(latest_file_path) as f:
                    lines = f.readlines()
                    if 'Date' in lines[0]:
                        data = np.loadtxt(latest_file_path, skiprows=35, dtype=str)
                        list_item.data = data.astype(np.float64)
                        list_item.normalize_data()

                    else:
                        data = np.loadtxt(latest_file_path, dtype=str)
                        list_item.data = data.astype(np.float64)
                        list_item.normalize_data()
                
                self.custom_model.addItem(list_item)
                list_item.current_smoothing = self.smoothing_factor.value()
                self.plot_data()


#####################################################################################
#? Main window methods
                
    def add_current_fit(self):
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if current_spectrum.fit_result is not None:
                if current_spectrum.fitted_gauge == 'Samarium':
                    R1 = current_spectrum.fit_result['opti'][2]
                    P = SmPressure(R1)
                
                
                elif current_spectrum.fitted_gauge == 'Ruby':
                    R1 = np.max([current_spectrum.fit_result['opti'][2], current_spectrum.fit_result['opti'][5]])
                    P = RubyPressure(R1)

                elif current_spectrum.fitted_gauge == 'Raman':
                    R1 = current_spectrum.fit_result['opti']
                    P = Raman_akahama(current_spectrum.fit_result['opti'])
                
                new_point = helpers.HPData(Pm = 0, 
	     		  					P = P,
	      		  					x = R1,
	       	 	  					T = 298,
	      		  					x0 = 694.281,
	      		  					T0 = 298, 
	      		  					calib = self.calibrations['Ruby2020'],
	      		  					file = current_spectrum.name)

                self.data.add(new_point)

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

                with open(file) as f:
                    lines = f.readlines()
                    if 'Date' in lines[0]:
                        data = np.loadtxt(file, skiprows=35, dtype=str)
                        new_item.data = data.astype(np.float64)
                        new_item.normalize_data()

                    else:
                        data = np.loadtxt(file, dtype=str)
                        new_item.data = data.astype(np.float64)
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

                with open(file) as f:
                    lines = f.readlines()
                    if 'Date' in lines[0]:
                        data = np.loadtxt(file, skiprows=35, dtype=str)
                        new_item.data = data.astype(np.float64)
                        new_item.normalize_data()

                    else:
                        data = np.loadtxt(file, dtype=str)
                        new_item.data = data.astype(np.float64)
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
        if selected_item.fitted_gauge is not None:
            self.fit_type_selector.setCurrentText(selected_item.fitted_gauge)
        self.plot_data()
        if selected_item.fit_result is not None:
            self.plot_fit(selected_item)
    
    @pyqtSlot()
    def selection_changed(self):
        # Update the current_selected_index when the selection changes
        selected_index = self.list_widget.currentIndex()
        if selected_index.isValid():
            self.current_selected_index = selected_index
        else:
            self.current_selected_index = None

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
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if hasattr(current_spectrum, 'data'):
                # spectral data
                self.axes.clear()
                self.axes.set_ylabel('Intensity')
                self.axes.set_xlabel(current_spectrum.spectral_unit)
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
                self.deriv_axes.set_xlabel(current_spectrum.spectral_unit)
                if current_spectrum.corrected_data is None:
                    dI = gaussian_filter1d(current_spectrum.data[:,1],mode='nearest', sigma=1, order=1)
                    self.deriv_axes.scatter(current_spectrum.data[:,0], 
                                            dI, 
                                            c = "crimson",
                                            s = 5)
                else :
                    dI = gaussian_filter1d(current_spectrum.corrected_data[:,1],mode='nearest', sigma=1, order=1)
                    self.deriv_axes.scatter(current_spectrum.corrected_data[:,0], 
                                            dI, 
                                            c = "crimson",
                                            s = 5)
                self.deriv_canvas.draw()

    def smoothen(self):
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            smooth_window = int(self.smoothing_factor.value()//1)
            current_spectrum.current_smoothing = self.smoothing_factor.value()
            current_spectrum.corrected_data = np.column_stack((current_spectrum.data[:,0],uniform_filter1d(current_spectrum.data[:,1], size=smooth_window)))
            self.plot_data() 
            if current_spectrum.fit_result is not None:
                self.plot_fit(current_spectrum)
    
    def update_fit_type(self):
        col1 = self.fit_type_selector.model().item(
		    self.fit_type_selector.currentIndex()).background().color().getRgb()
        self.fit_type_selector.setStyleSheet("background-color: rgba{};	selection-background-color: k;".format(col1))

        fit_mode  = self.fit_type_selector.currentText()
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if fit_mode == 'Samarium':
                current_spectrum.spectral_unit = r"$\lambda$ (nm)"
            elif fit_mode == 'Ruby':
                current_spectrum.spectral_unit = r"$\lambda$ (nm)"
            elif fit_mode == 'Raman':
                current_spectrum.spectral_unit = r"$\nu$ (cm$^{-1}$)"
            self.deriv_axes.set_xlabel(current_spectrum.spectral_unit)
            self.axes.set_xlabel(current_spectrum.spectral_unit)
            self.deriv_canvas.draw()
            self.canvas.draw()

    def fit(self):
        fit_mode  = self.fit_type_selector.currentText()
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            current_spectrum.fitted_gauge = fit_mode

            if fit_mode == 'Samarium':
                self.Sm_fit()
            elif fit_mode == 'Ruby':
                self.Ruby_fit()
            elif fit_mode == 'Raman':
                self.Raman_fit()
            else:
                print('Not implemented')

    def Sm_fit(self, guess_peak=None):
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if current_spectrum.corrected_data is None:
                x=current_spectrum.data[:,0]
                y=current_spectrum.data[:,1]
            else :
                x=current_spectrum.corrected_data[:,0]
                y=current_spectrum.corrected_data[:,1]

            pk, prop = find_peaks(y, height = max(y)/2, width=10)
            #print([x[a] for a in pk])
            if guess_peak == None :
                guess_peak = x[pk[np.argmax(prop['peak_heights'])]]

            #print('Guess : ', guess_peak)
            pinit = [y[0], 1-y[0], guess_peak, 2e-1]

            init = [Sm_model(wvl, *pinit) for wvl in x]

            popt, pcov = curve_fit(Sm_model, x, y, p0=pinit)

            current_spectrum.fit_result = {"opti":popt,"cov":pcov}

            self.plot_fit(current_spectrum)

            R1 = popt[2]
            P = SmPressure(R1)

            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(R1,3), 'File':current_spectrum.name}, index=[0])
            #self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            #self.update_PvPm()

    def Ruby_fit(self, guess_peak=None):
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if current_spectrum.corrected_data is None:
                x=current_spectrum.data[:,0]
                y=current_spectrum.data[:,1]
            else :
                x=current_spectrum.corrected_data[:,0]
                y=current_spectrum.corrected_data[:,1]

            pk, prop = find_peaks(y, height = max(y)/2, width=10)
            #print([x[a] for a in pk])
            if guess_peak == None:
                guess_peak = x[pk[np.argmax(prop['peak_heights'])]]

            #print('Guess : ', guess_peak)
            
            # This was for two gaussians:
            # pinit = [y[0], 1-y[0], guess_peak-1.5, 2e-1,  1-y[0], guess_peak, 2e-1]
            # This is for two voigts:
            pinit = [y[0], 1-y[0], guess_peak-1.5, 2e-2, 2e-1,  
                           1-y[0], guess_peak,     2e-2, 2e-1]

            fitbounds = ( [0,           0,  690,   0,   0,  
                                        0,  690,   0,   0],
                          [np.inf, np.inf,  900,   2,   2,  
                                   np.inf,  900,   2,   2] )

            init = [Ruby_model_voigts(wvl, *pinit) for wvl in x]
  #          self.axes.scatter(x, init, label='init')

            popt, pcov = curve_fit(Ruby_model_voigts, 
                                   x, 
                                   y, 
                                   p0=pinit,
                                   bounds=fitbounds)

            #print(popt)

            current_spectrum.fit_result = {"opti":popt,"cov":pcov}

            self.plot_fit(current_spectrum)
            
            # this was for two gaussians:
            # R1 = np.max([popt[2], popt[5]])
            # this is for two voigts:
            R1 = np.max([popt[2], popt[6]])
            
            P = RubyPressure(R1)
            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(R1,3), 'File':current_spectrum.name}, index=[0])
            #self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            #self.update_PvPm()

    def Raman_fit(self, guess_peak=None):
        if self.current_selected_index is not None:
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            if guess_peak == None:
                if current_spectrum.corrected_data is None:
                    x=current_spectrum.data[:,0]
                    y=current_spectrum.data[:,1]
                else :
                    x=current_spectrum.corrected_data[:,0]
                    y=current_spectrum.corrected_data[:,1]

                grad = np.gradient(y)
                nu_min = x[np.argmin(grad)]
            else:
                nu_min=guess_peak
            P = Raman_akahama(nu_min)
            current_spectrum.fit_result = {"opti":nu_min,"cov":None}

            self.plot_fit(current_spectrum)
            
            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(nu_min,3), 'File':current_spectrum.name}, index=[0])
            #self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            #self.update_PvPm()

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

            if my_spectrum.fitted_gauge == 'Samarium':
                fitted = [Sm_model(wvl, *my_spectrum.fit_result['opti']) for wvl in x]
                R1 = my_spectrum.fit_result['opti'][2]
                P = SmPressure(R1)
                self.axes.plot(x, 
                               fitted, 
                               '-',
                               c = 'r', 
                               label='best fit')
                self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
                self.axes.legend(frameon=False)
                self.canvas.draw()

            elif my_spectrum.fitted_gauge == 'Ruby':
                fitted = [Ruby_model_voigts(wvl, *my_spectrum.fit_result['opti']) for wvl in x]
                # this was for two gaussians:
                #R1 = np.max([my_spectrum.fit_result['opti'][2], my_spectrum.fit_result['opti'][5]])
                # this is for two voigts:
                R1 = np.max([my_spectrum.fit_result['opti'][2], my_spectrum.fit_result['opti'][6]])
                P = RubyPressure(R1)
                self.axes.plot(x, 
                               fitted, 
                               '-',
                               c = 'r', 
                               label='best fit')
                self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
                self.axes.legend(frameon=False)
                self.canvas.draw()

            elif my_spectrum.fitted_gauge == 'Raman':
                self.axes.axvline(my_spectrum.fit_result['opti'], color='green', ls='--')
                self.deriv_axes.axvline(my_spectrum.fit_result['opti'], color='green', ls='--')
                P = Raman_akahama(my_spectrum.fit_result['opti'])
                self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
                self.canvas.draw()
                self.deriv_canvas.draw()

            else:
                print('Not implemented')

    def toggle_PvPm(self):
        if self.DataTableWindow.isVisible() or self.PvPmPlotWindow.isVisible():
            self.DataTableWindow.hide()
            self.PvPmPlotWindow.hide()
        else:
            self.DataTableWindow.show()
            self.PvPmPlotWindow.show()

    def plot_PvPm(self):
        self.PvPmPlot.axes.clear()
        self.PvPmPlot.axes.set_ylabel(r'$P$ (GPa)')
        self.PvPmPlot.axes.set_xlabel(r"$P_m$ (bar)")
        temp = self.PvPm_df.replace('', np.nan).dropna(subset=['Pm', 'P'])
        self.PvPmPlot.axes.plot(temp['Pm'].astype(np.float16), temp['P'].astype(np.float16), marker='.')
        self.PvPmPlot.canvas.draw()

    def save_PvPm(self):
        if hasattr(self, 'dir_name'):
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Table", self.dir_name, "All Files (*)", options=options)
            temp = self.PvPm_df.replace('', np.nan).dropna(subset=['Pm', 'P'])
            temp.to_csv(file_name+".csv")

        else:
            msg=QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No directory selected.")
            msg.setWindowTitle("Error")
            msg.exec_()


    def open_PvPm(self):
        if hasattr(self, 'dir_name'):
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_name, _ = QFileDialog.getOpenFileName(self, "Save Table", self.dir_name, "All Files (*)", options=options)
            self.PvPm_df = pd.read_csv(file_name, delimiter = ',', index_col=0)

            self.update_PvPm()
        else:
            msg=QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No directory selected.")
            msg.setWindowTitle("Error")
            msg.exec_()


    def toggle_click_fit(self):
        self.click_enabled = not self.click_enabled
        
    def click_fit(self, event):
        if self.click_enabled and event.button == 1 and event.inaxes:
            x_click, y_click = event.xdata, event.ydata
            fit_mode  = self.fit_type_selector.currentText()
            current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
            current_spectrum.fitted_gauge = fit_mode
            if fit_mode == 'Samarium':
                self.Sm_fit(guess_peak=x_click)
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

            elif fit_mode == 'Ruby':
                self.Ruby_fit(guess_peak=x_click)
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

            elif fit_mode == 'Raman':
                nu_min = x_click
                self.Raman_fit(guess_peak = nu_min)
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

            else:
                print('Not implemented')
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

    def CHull_Bg(self):
        current_spectrum = self.custom_model.data(self.current_selected_index, role=Qt.UserRole)
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


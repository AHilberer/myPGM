import os
import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import pandas as pd
from PyQt5.QtWidgets import (QMainWindow,
                             QLabel,
                             QPushButton,
                             QFileDialog,
                             QGridLayout,
                             QWidget,
                             QTableWidget,
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
                             QMenuBar,
                             QMenu,
                             QAction,
                             QListWidget,
                             QListWidgetItem)
from PyQt5.QtCore import QFileInfo, Qt
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import uniform_filter1d
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d

from pressure_models import *
from PvPm_plot_window import *
from PvPm_table_window import *
from plotting_canvas import *

Setup_mode = True


class EditableDelegate(QStyledItemDelegate):
    """A delegate that allows for cell editing"""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()


        menubar = self.menuBar()
        help_menu = menubar.addMenu(' Help')
        exit_menu = menubar.addMenu(' Exit')

        exit_action = QAction(' Exit', self)
        exit_action.triggered.connect(self.close)
        exit_menu.addAction(exit_action)    
        help_menu.addAction(exit_action) 

        # Setup Main window parameters
        self.setWindowTitle("PressureGaugeMonitor_Online")
        self.setGeometry(100, 100, 800, 1000)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)


        # Use a QHBoxLayout for the main layout
        main_layout = QHBoxLayout(central_widget)


        # Create a new panel (NewPanelBox) on the left
        left_panel_layout = QVBoxLayout()

        # Setup new panel content (for illustration purposes)
        

        # Add the nested QVBoxLayout for the new panel to the main layout
        main_layout.addLayout(left_panel_layout)


        # Create a new panel (PanelBox) on the left
        right_panel_layout = QVBoxLayout()

#####################################################################################
#? Setup file loading section

        self.corrected_data = None
        self.current_unit = r"$\lambda$ (nm)"


        FileBox = QGroupBox("File management")
        FileBoxLayout = QHBoxLayout()

        self.select_dir_button = QPushButton("Add Directory", self)
        self.select_dir_button.clicked.connect(self.select_directory)
        FileBoxLayout.addWidget(self.select_dir_button)

        self.add_button = QPushButton("Add single file", self)
        self.add_button.clicked.connect(self.add_file)
        FileBoxLayout.addWidget(self.add_button)

        self.delete_button = QPushButton("Delete single file ", self)
        self.delete_button.clicked.connect(self.delete_file)
        FileBoxLayout.addWidget(self.delete_button)
        
        FileBox.setLayout(FileBoxLayout)
        left_panel_layout.addWidget(FileBox)

        self.list_widget = QListWidget(self)
        left_panel_layout.addWidget(self.list_widget)
        self.list_widget.itemClicked.connect(self.display_selected_file)







        #####################################################################################
#? Setup Fitting section


        FitBox = QGroupBox("Fitting")
        FitBoxLayout = QHBoxLayout()

        self.fit_button = QPushButton("Fit", self)
        self.fit_button.clicked.connect(self.fit)
        FitBoxLayout.addWidget(self.fit_button)

        self.fit_type_selector = QComboBox(self)
        self.fit_type_selector.addItems(['Ruby', 'Samarium', 'Raman'])
        gauge_colors = ['lightcoral', 'royalblue', 'darkgrey']
        for ind in range(len(['Ruby', 'Samarium', 'Raman'])):
            self.fit_type_selector.model().item(ind).setBackground(QColor(gauge_colors[ind]))

        self.fit_type_selector.currentIndexChanged.connect(self.update_fit_type)
        self.update_fit_type()
        FitBoxLayout.addWidget(self.fit_type_selector)
        
        self.click_fit_button = QPushButton("Enable Click-to-Fit", self)
        self.click_fit_button.setCheckable(True)
        self.click_fit_button.clicked.connect(self.toggle_click_fit)
        FitBoxLayout.addWidget(self.click_fit_button)
        self.click_enabled = False

        FitBox.setLayout(FitBoxLayout)
        right_panel_layout.addWidget(FitBox)

        #####################################################################################
#? Data correction section

        CorrectionBox = QGroupBox("Data correction")
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

        CorrectionBox.setLayout(CorrectionBoxLayout)
        right_panel_layout.addWidget(CorrectionBox)

        #####################################################################################
# #? Setup loaded file info section

        FileInfoBox = QGroupBox("File info")
        FileInfoBoxLayout = QVBoxLayout()

        self.dir_label = QLabel("No directory selected", self)
        FileInfoBoxLayout.addWidget(self.dir_label)
        self.loaded_filename = None

        self.data_label = QLabel("No data loaded", self)
        FileInfoBoxLayout.addWidget(self.data_label)

        FileInfoBox.setLayout(FileInfoBoxLayout)
        right_panel_layout.addWidget(FileInfoBox)

        #####################################################################################
# #? Setup data plotting section

        DataPlotBox = QGroupBox()
        DataPlotBoxLayout = QVBoxLayout()

        spectrum_plot = MplCanvas(self)
        self.axes = spectrum_plot.axes
        self.figure = spectrum_plot.figure
        self.canvas = FigureCanvas(self.figure)
        self.axes.set_ylabel('Intensity')
        self.axes.set_xlabel(self.current_unit)

        toolbar = NavigationToolbar(self.canvas, self)
        DataPlotBoxLayout.addWidget(self.canvas)
        DataPlotBoxLayout.addWidget(toolbar)
        self.canvas.mpl_connect('button_press_event', self.click_fit)

        DataPlotBox.setLayout(DataPlotBoxLayout)
        right_panel_layout.addWidget(DataPlotBox)

#####################################################################################
# #? Setup derivative plotting section

        DataPlotBox = QGroupBox()
        DataPlotBoxLayout = QVBoxLayout()

        deriv_plot = MplCanvas(self)
        self.deriv_axes = deriv_plot.axes
        self.deriv_figure = deriv_plot.figure
        self.deriv_canvas = FigureCanvas(self.deriv_figure)
        self.deriv_axes.set_ylabel('Intensity')
        self.deriv_axes.set_xlabel(self.current_unit)

        deriv_toolbar = NavigationToolbar(self.deriv_canvas, self)
        DataPlotBoxLayout.addWidget(self.deriv_canvas)
        DataPlotBoxLayout.addWidget(deriv_toolbar)
        self.deriv_canvas.mpl_connect('button_press_event', self.click_fit)

        DataPlotBox.setLayout(DataPlotBoxLayout)
        right_panel_layout.addWidget(DataPlotBox)

        # Add the nested QVBoxLayout to the main layout
        main_layout.addLayout(right_panel_layout)


#####################################################################################
# #? Setup PvPm table window

        self.PvPmTable = QTableView()
        #file = '/home/hilberera/Documents/Manips/2023-09_CDMX14_AlH3_noH/Raman/PvPm_20230913_1000.csv'
        
        self.PvPm_df = pd.DataFrame({'Pm':'', 'P':'', 'lambda':'', 'File':''}, index=[0])

        self.PvPm_data_inst = PandasModel(self.PvPm_df)
        delegate = EditableDelegate()
        self.PvPm_data_inst.dataChanged.connect(self.plot_PvPm)
        self.PvPmTable.setModel(self.PvPm_data_inst)
        self.PvPmTable.setItemDelegate(delegate)
        self.PvPmTable.setAlternatingRowColors(True)
        self.PvPmTable.setSelectionBehavior(QTableView.SelectRows)
        self.PvPmTable.setWindowTitle('PvPm table')
        self.PvPmTable.setGeometry(900, 100, 450, 400)

# #####################################################################################
# #? Setup PvPm section and associated buttons

        PvPmBox = QGroupBox('PvPm table')
        PvPmBoxLayout = QHBoxLayout()

        self.PvPmPlot = PvPmPlotWindow()
        self.PvPm_toggle_button = QPushButton("Toggle PvPm table")
        self.PvPm_toggle_button.clicked.connect(self.toggle_PvPm)
        PvPmBoxLayout.addWidget(self.PvPm_toggle_button)
        #self.PvPmTable.itemChanged.connect(self.plot_PvPm)
        #self.PvPmTable.itemChanged.connect(self.predict_from_lambda)


        self.PvPm_save_button = QPushButton("Save PvPm table")
        self.PvPm_save_button.clicked.connect(self.save_PvPm)
        PvPmBoxLayout.addWidget(self.PvPm_save_button)
        
        self.PvPm_open_button = QPushButton("Open PvPm table")
        self.PvPm_open_button.clicked.connect(self.open_PvPm)
        PvPmBoxLayout.addWidget(self.PvPm_open_button)

        PvPmBox.setLayout(PvPmBoxLayout)
        right_panel_layout.addWidget(PvPmBox)


# #####################################################################################
# #? Create special startup config for debugging

        if Setup_mode :
            #print(os.path.dirname(__file__))
            latest_file_path= os.path.dirname(__file__)+'/resources/Example_diam_Raman.asc'

            file_info = QFileInfo(latest_file_path)
            file_name = file_info.fileName()
            list_item = QListWidgetItem(file_name)
            list_item.setData(Qt.UserRole, latest_file_path)
            self.list_widget.addItem(list_item)

            with open(latest_file_path) as f:
                lines = f.readlines()
                if 'Date' in lines[0]:
                    data = np.loadtxt(latest_file_path, skiprows=35, dtype=str)
                    self.data = data.astype(np.float64)
                    self.normalize_data()

                else:
                    data = np.loadtxt(latest_file_path, dtype=str)
                    self.data = data.astype(np.float64)
                    self.normalize_data()

            self.data_label.setText(f"Loaded file : {'Example_diam_Raman.asc'}")
            self.loaded_filename = 'Example_diam_Raman.asc'
            self.plot_data()


#####################################################################################
#? Main window methods
    
    def smoothen(self):
        smooth_window = int(self.smoothing_factor.value()//1)
        self.corrected_data = np.column_stack((self.data[:,0],uniform_filter1d(self.data[:,1], size=smooth_window)))
        self.plot_data()

    def select_directory(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        dir_name = QFileDialog.getExistingDirectory(self, "Select Directory", options=options)
        if dir_name:
            self.dir_name = dir_name
            self.dir_label.setText(f"Selected directory: {dir_name}")
            
    def add_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            for file in selected_files:
                file_info = QFileInfo(file)
                file_name = file_info.fileName()

                list_item = QListWidgetItem(file_name)
                list_item.setData(Qt.UserRole, file)
                self.list_widget.addItem(list_item)
        
    def delete_file(self):
        selected_item = self.list_widget.currentItem()
        if selected_item is not None:
            self.list_widget.takeItem(self.list_widget.row(selected_item))

    def display_selected_file(self, item):
        file_path = item.data(Qt.UserRole)
        print(f'Selected File: {file_path}')

    def normalize_data(self):
        self.data[:,1]=self.data[:,1]/max(self.data[:,1])

    def plot_data(self):
        if hasattr(self, 'data'):
            # spectral data
            self.axes.clear()
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlabel(self.current_unit)
            if self.corrected_data is None:
                self.axes.plot(self.data[:,0], self.data[:,1])
            else :
                self.axes.plot(self.corrected_data[:,0], self.corrected_data[:,1])
            self.canvas.draw()

            # derivative data
            self.deriv_axes.clear()
            self.deriv_axes.set_ylabel(r'dI/d$\nu$')
            self.deriv_axes.set_xlabel(self.current_unit)
            if self.corrected_data is None:
                dI = gaussian_filter1d(self.data[:,1],mode='nearest', sigma=1, order=1)
                self.deriv_axes.plot(self.data[:,0], dI, color="crimson")
            else :
                dI = gaussian_filter1d(self.corrected_data[:,1],mode='nearest', sigma=1, order=1)
                self.deriv_axes.plot(self.corrected_data[:,0], dI, color="crimson")
            self.deriv_canvas.draw()

        else:
            self.data_label.setText("No data to plot")
    
    def update_fit_type(self):
        col1 = self.fit_type_selector.model().item(
		    self.fit_type_selector.currentIndex()).background().color().getRgb()
        self.fit_type_selector.setStyleSheet("background-color: rgba{};	selection-background-color: k;".format(col1))

        fit_mode  = self.fit_type_selector.currentText()
        if fit_mode == 'Samarium':
            self.current_unit = r"$\lambda$ (nm)"
        elif fit_mode == 'Ruby':
            self.current_unit = r"$\lambda$ (nm)"
        elif fit_mode == 'Raman':
            self.current_unit = r"$\nu$ (cm$^{-1}$)"
            
    def fit(self):
        fit_mode  = self.fit_type_selector.currentText()
        if fit_mode == 'Samarium':
            self.Sm_fit()
        elif fit_mode == 'Ruby':
            self.Ruby_fit()
        elif fit_mode == 'Raman':
            self.Raman_fit()
        else:
           print('Not implemented')

    def Sm_fit(self, guess_peak=None):
        if hasattr(self, 'data'):
            if self.corrected_data is None:
                x=self.data[:,0]
                y=self.data[:,1]
            else :
                x=self.corrected_data[:,0]
                y=self.corrected_data[:,1]

            pk, prop = find_peaks(y, height = max(y)/2, width=10)
            #print([x[a] for a in pk])
            if guess_peak == None :
                guess_peak = x[pk[np.argmax(prop['peak_heights'])]]

            #print('Guess : ', guess_peak)
            pinit = [y[0], 1-y[0], guess_peak, 2e-1]

            init = [Sm_model(wvl, *pinit) for wvl in x]

            popt, pcov = curve_fit(Sm_model, x, y, p0=pinit)
            fit = [Sm_model(wvl, *popt) for wvl in x]

            R1 = popt[2]
            P = SmPressure(R1)
            #print('Fitted R1:', R1, 'nm')
            #print(P)
            self.axes.clear()
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlabel(self.current_unit)
            self.axes.plot(x, y, label = 'data', markersize=1)
            #lt.plot(x, init, '--', label='initial fit')
            self.axes.plot(x, fit, '-', label='best fit')

            #plt.xlim([R1-plot_window, R1+plot_window])
            self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
            self.axes.legend(frameon=False)
            self.canvas.draw()

            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(R1,3), 'File':self.loaded_filename}, index=[0])
            self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            self.update_PvPm()

    def Ruby_fit(self, guess_peak=None):
        if hasattr(self, 'data'):
            if self.corrected_data is None:
                x=self.data[:,0]
                y=self.data[:,1]
            else :
                x=self.corrected_data[:,0]
                y=self.corrected_data[:,1]

            pk, prop = find_peaks(y, height = max(y)/2, width=10)
            #print([x[a] for a in pk])
            if guess_peak == None:
                guess_peak = x[pk[np.argmax(prop['peak_heights'])]]

            #print('Guess : ', guess_peak)
            pinit = [y[0], 1-y[0], guess_peak-1.5, 2e-1,  1-y[0], guess_peak, 2e-1]

            init = [Ruby_model(wvl, *pinit) for wvl in x]

            popt, pcov = curve_fit(Ruby_model, x, y, p0=pinit)
            fit = [Ruby_model(wvl, *popt) for wvl in x]

            R1 = np.max([popt[2], popt[5]])
            P = RubyPressure(R1)
            #print('Fitted R1:', R1, 'nm')
            #print(P)
            self.axes.clear()
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlabel(self.current_unit)
            self.axes.plot(x, y, label = 'data', markersize=1)
            #lt.plot(x, init, '--', label='initial fit')
            self.axes.plot(x, fit, '-', label='best fit')

            #plt.xlim([R1-plot_window, R1+plot_window])
            self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
            self.axes.legend(frameon=False)

            self.canvas.draw()
            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(R1,3), 'File':self.loaded_filename}, index=[0])
            self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            self.update_PvPm()

    def Raman_fit(self):
        if hasattr(self, 'data'):
            if self.corrected_data is None:
                x=self.data[:,0]
                y=self.data[:,1]
            else :
                x=self.corrected_data[:,0]
                y=self.corrected_data[:,1]

            grad = np.gradient(y)
            nu_min = x[np.argmin(grad)]
            P = Raman_akahama(nu_min)

            self.axes.clear()
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlabel(self.current_unit)
            self.axes.plot(x, y, label = 'data', markersize=1)
            #lt.plot(x, init, '--', label='initial fit')
            self.axes.axvline(nu_min, color='green', ls='--')
            self.deriv_axes.axvline(nu_min, color='green', ls='--')

            #self.axes.set_xlim([1200, nu_min+200])

            #plt.xlim([R1-plot_window, R1+plot_window])
            self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
            #self.axes.legend(frameon=False)
            self.canvas.draw()
            self.deriv_canvas.draw()

            
            new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(nu_min,3), 'File':self.loaded_filename}, index=[0])
            self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
            self.update_PvPm()

    def toggle_PvPm(self):
        if self.PvPmTable.isVisible() or self.PvPmPlot.isVisible():
            self.PvPmTable.hide()
            self.PvPmPlot.hide()
        else:
            self.PvPmTable.show()
            self.PvPmPlot.show()

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

    def update_PvPm(self):
        self.PvPm_data_inst = PandasModel(self.PvPm_df)
        self.PvPm_data_inst.dataChanged.connect(self.plot_PvPm)
        self.PvPmTable.setModel(self.PvPm_data_inst)
        self.plot_PvPm()

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


    def predict_from_lambda(self, item):
        row = item.row()
        col = item.column()
        if col == 2:
            if (self.PvPmTable.item(row, 2) != None) and (self.PvPmTable.item(row, 2).text() != ''):
                fit_mode  = self.fit_type_selector.currentText()
                lambda_test = float(self.PvPmTable.item(row, 2).text().strip())
                if fit_mode == 'Samarium':
                    P = SmPressure(lambda_test)
                elif fit_mode == 'Ruby':
                    P = RubyPressure(lambda_test)
                elif fit_mode == 'Raman':
                    P = Raman_akahama(lambda_test)
                else:
                    print('Not implemented')
                self.PvPmTable.setItem(row, 1, QTableWidgetItem(str(round(P,2))))

    def toggle_click_fit(self):
        self.click_enabled = not self.click_enabled
        
    def click_fit(self, event):
        if self.click_enabled and event.button == 1 and event.inaxes:
            x_click, y_click = event.xdata, event.ydata
            fit_mode  = self.fit_type_selector.currentText()
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
                P = Raman_akahama(nu_min)
                self.plot_data()
                self.axes.axvline(nu_min, color='green', ls='--')
                self.deriv_axes.axvline(nu_min, color='green', ls='--')

                self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
                #self.axes.legend(frameon=False)
                self.canvas.draw()
                self.deriv_canvas.draw()

                new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(nu_min,3), 'File':self.loaded_filename}, index=[0])
                self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
                self.update_PvPm()
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

            else:
                print('Not implemented')
                self.toggle_click_fit()
                self.click_fit_button.setChecked(False)

    def CHull_Bg(self):
        if self.corrected_data is None:
            x=self.data[:,0]
            y=self.data[:,1]
        else :
            x=self.corrected_data[:,0]
            y=self.corrected_data[:,1]
        
        v = ConvexHull(np.column_stack((x,y))).vertices
        v = np.roll(v, -v.argmin())
        anchors = v[:v.argmax()]
        bg = np.interp(x, x[anchors], y[anchors])
        corrected = y - bg

        self.corrected_data = np.column_stack((x,corrected))
        self.corrected_data[:,1]=self.corrected_data[:,1]/max(self.corrected_data[:,1])
        self.plot_data()


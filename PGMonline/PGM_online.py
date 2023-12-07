import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Qt5Agg')
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import csv
import pandas as pd
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
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
                             QMessageBox)

from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from scipy.ndimage import uniform_filter1d
from scipy.spatial import ConvexHull


Setup_mode = False

def Sm_model(x, c, a1, x1, sigma1):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2))

def SmPressure(lambda_Sm, lambda_Sm_0=685.41):
    # Datchi 1997
    delta_lambda = abs(lambda_Sm-lambda_Sm_0)
    P = 4.032*delta_lambda*(1 + 9.29e-3*delta_lambda)/(1 + 2.32e-2*delta_lambda)
    return P

def Ruby_model(x, c, a1, x1, sigma1, a2, x2, sigma2):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2)) + a2*np.exp(-(x-x2)**2/(2*sigma2**2))

def RubyPressure(lambda_ruby, lambda_ruby_0=694.25):
    # ruby2020: High Pressure Research 
    # https://doi.org/10.1080/08957959.2020.1791107
    delta_lambda_ruby = abs(lambda_ruby-lambda_ruby_0)
    P = 1.87e3*(delta_lambda_ruby/lambda_ruby_0)* \
                (1 + 5.63*(delta_lambda_ruby/lambda_ruby_0))
    return P

def Raman_akahama(nu, nu0=1334, K0=547, K0p=3.75):
    # Akahama2006
    # https://doi.org/10.1063/1.2335683
    delta_nu = abs(nu-nu0)
    P = K0*(delta_nu/nu0)*(1 + 0.5*(K0p-1)*(delta_nu/nu0))
    return P



class EditableDelegate(QStyledItemDelegate):
    """A delegate that allows for cell editing"""

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        return editor


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.corrected_data = None
        self.current_unit = r"$\lambda$ (nm)"
#####################################################################################
#? Setup Main window parameters

        self.setWindowTitle("PressureGaugeMonitor_Online")
        self.setGeometry(100, 100, 800, 800)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        grid_layout = QVBoxLayout(central_widget)
        
#####################################################################################
#? Setup file loading section

        FileBox = QGroupBox("File loading")
        FileBoxLayout = QHBoxLayout()

        self.select_dir_button = QPushButton("Select Directory", self)
        self.select_dir_button.clicked.connect(self.select_directory)
        FileBoxLayout.addWidget(self.select_dir_button)

        self.load_latest_button = QPushButton("Load Latest File", self)
        self.load_latest_button.clicked.connect(self.load_latest_file)
        FileBoxLayout.addWidget(self.load_latest_button)
        
        self.load_specific_button = QPushButton("Load Specific File", self)
        self.load_specific_button.clicked.connect(self.load_specific_file)
        FileBoxLayout.addWidget(self.load_specific_button)

        FileBox.setLayout(FileBoxLayout)
        grid_layout.addWidget(FileBox)

        
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
        # associated connection in plot section setup

        FitBox.setLayout(FitBoxLayout)
        grid_layout.addWidget(FitBox)
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
        grid_layout.addWidget(CorrectionBox)

# #####################################################################################
# #? Setup loaded file info section

        FileInfoBox = QGroupBox("File info")
        FileInfoBoxLayout = QVBoxLayout()

        self.dir_label = QLabel("No directory selected", self)
        FileInfoBoxLayout.addWidget(self.dir_label)
        self.loaded_filename = None

        self.data_label = QLabel("No data loaded", self)
        FileInfoBoxLayout.addWidget(self.data_label)

        FileInfoBox.setLayout(FileInfoBoxLayout)
        grid_layout.addWidget(FileInfoBox)

# #####################################################################################
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
        grid_layout.addWidget(DataPlotBox)


# #####################################################################################
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
        grid_layout.addWidget(PvPmBox)


# #####################################################################################
# #? Create special startup config for debugging

        if Setup_mode :
            latest_file_path= '/resources/Example_diam_Raman.asc'
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
            
    def load_specific_file(self):
        if hasattr(self, 'dir_name'):
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_name, _ = QFileDialog.getOpenFileName(self, "Load Data", self.dir_name, "Text Files (*.asc);;All Files (*)", options=options)
            if file_name:
                with open(file_name) as f:
                    lines = f.readlines()
                    if 'Date' in lines[0]:
                        data = np.loadtxt(file_name, skiprows=35, dtype=str)
                        self.data = data.astype(np.float64)
                        self.normalize_data()
                        self.corrected_data = None


                    else:
                        data = np.loadtxt(file_name, dtype=str)
                        self.data = data.astype(np.float64)
                        self.normalize_data()
                        self.corrected_data = None

                self.data_label.setText(f"Loaded file : {file_name[len(self.dir_name)+1:]}")
                self.loaded_filename = file_name[len(self.dir_name)+1:]
                self.plot_data()
            else:
                self.data_label.setText("No files in selected directory")
        else:
            self.data_label.setText("No directory selected")
        
    def load_latest_file(self):
            if hasattr(self, 'dir_name'):
                file_names = [f for f in os.listdir(self.dir_name) if os.path.isfile(os.path.join(self.dir_name, f)) and '.asc' in f]
                if file_names:
                    file_names.sort(key=lambda f: os.path.getmtime(os.path.join(self.dir_name, f)))
                    latest_file_name = file_names[-1]
                    latest_file_path = os.path.join(self.dir_name, latest_file_name)
                    with open(latest_file_path) as f:
                        lines = f.readlines()
                        if 'Date' in lines[0]:
                            data = np.loadtxt(latest_file_path, skiprows=35, dtype=str)
                            self.data = data.astype(np.float64)
                            self.corrected_data = None
                            self.normalize_data()

                        else:
                            data = np.loadtxt(latest_file_path, dtype=str)
                            self.data = data.astype(np.float64)
                            self.corrected_data = None
                            self.normalize_data()

                    self.data_label.setText(f"Loaded file : {latest_file_name}")
                    self.loaded_filename = latest_file_name
                    self.plot_data()
                else:
                    self.data_label.setText("No files in selected directory")
            else:
                self.data_label.setText("No directory selected")

    def normalize_data(self):
        self.data[:,1]=self.data[:,1]/max(self.data[:,1])

    def plot_data(self):
        if hasattr(self, 'data'):
            self.axes.clear()
            self.axes.set_ylabel('Intensity')
            self.axes.set_xlabel(self.current_unit)
            if self.corrected_data is None:
                self.axes.plot(self.data[:,0], self.data[:,1])
            else :
                self.axes.plot(self.corrected_data[:,0], self.corrected_data[:,1])
            self.canvas.draw()
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
            self.axes.axvline(nu_min, color='crimson', ls='--')
            #self.axes.set_xlim([1200, nu_min+200])

            #plt.xlim([R1-plot_window, R1+plot_window])
            self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
            #self.axes.legend(frameon=False)
            self.canvas.draw()
            
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
            elif fit_mode == 'Ruby':
                self.Ruby_fit(guess_peak=x_click)
            elif fit_mode == 'Raman':
                nu_min = x_click
                P = Raman_akahama(nu_min)

                self.plot_data()
                
                self.axes.axvline(nu_min, color='crimson', ls='--')

                self.axes.set_title(f'Fitted pressure : {P : > 10.2f} GPa')
                #self.axes.legend(frameon=False)
                self.canvas.draw()
                new_row = pd.DataFrame({'Pm':'', 'P':round(P,2), 'lambda':round(nu_min,3), 'File':self.loaded_filename}, index=[0])
                self.PvPm_df = pd.concat([self.PvPm_df,new_row], ignore_index=True)
                self.update_PvPm()
            else:
                print('Not implemented')

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


#####################################################################################
#? Define plot canvas class

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = plt.Figure(tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        plt.tight_layout()
        super(MplCanvas, self).__init__(fig)

#####################################################################################
#? Define PvPm table class

class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe"""

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._dataframe)
        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(self._dataframe.iloc[index.row(), index.column()])

        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            self._dataframe.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index,index)
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])
            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])
        return None

#####################################################################################
#? Define PvPm plot class

class PvPmPlotWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PvPm Plot")
        self.setGeometry(900, 550, 450, 350)
        PmP_plot = MplCanvas(self)
        self.axes = PmP_plot.axes
        self.figure = PmP_plot.figure
        self.canvas = FigureCanvas(self.figure)
        self.axes.set_ylabel(r'$P$ (GPa)')
        self.axes.set_xlabel(r"$P_m$ (bar)")
        #self.axes.plot([0,1,2,3,4], [10,1,20,3,40])

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

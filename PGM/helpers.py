import numpy as np
import pandas as pd
from copy import deepcopy
from scipy.optimize import minimize
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QAbstractListModel, QModelIndex
from scipy.signal import find_peaks
from inspect import getfullargspec

class MySpectrumItem:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.data = None
        self.corrected_data = None
        self.current_smoothing = None
        self.spectral_unit = r"$\lambda$ (nm)"
        self.fitted_gauge = None
        self.fit_result = None
        self.fit_config = None
        self.fit_model = None

    def normalize_data(self):
        self.data[:,1] = self.data[:,1]-np.min(self.data[:,1])
        self.data[:,1]=self.data[:,1]/max(self.data[:,1])

class CustomFileListModel(QAbstractListModel):
    itemAdded = pyqtSignal()  # Signal emitted when an item is added
    itemDeleted = pyqtSignal()  # Signal emitted when an item is deleted

    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.items)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.items[index.row()].name
        elif role == Qt.UserRole:
            return self.items[index.row()]

    def addItem(self, item):
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self.items.append(item)
        self.endInsertRows()
        self.itemAdded.emit()  # Emit signal to notify the view

    def deleteItem(self, index):
        self.beginRemoveRows(QModelIndex(), index, index)
        del self.items[index]
        self.endRemoveRows()
        self.itemDeleted.emit()  # Emit signal to notify the view



class HPCalibration():
    ''' A general HP calibration object '''
    def __init__(self, name, func, Tcor_name, 
                    xname, xunit, x0default, xstep, color):
        self.name = name
        self.func = func
        self.Tcor_name = Tcor_name
        self.xname = xname
        self.xunit = xunit
        self.x0default = x0default
        self.xstep = xstep  # x step in spinboxes using mousewheel
        self.color = color  # color printed in calibration combobox

    def __repr__(self):
        return 'HPCalibration : ' + str( self.__dict__ )

    def invfunc(self, p, *args, **kwargs):
        res = minimize( lambda x: ( self.func(x, *args, **kwargs) - p )**2, 
                                    x0=self.x0default, tol=1e-6)
        return res.x[0]


class GaugeFitModel():
    ''' A general pressure gauge fitting model object '''
    def __init__(self, name, func,type, color):
        self.name = name
        self.func = func
        self.type = type
        self.color = color  # color printed in calibration combobox

    def get_pinit(self, x, y, guess_peak=None):
    
        pinit = list()
        
        xbin = x[1] - x[0] # nm/px or /!\ cm-1/px
        if guess_peak == None:
            pk, prop = find_peaks(y - np.min(y), height = np.ptp(y)/2, width=0.1/xbin)
            pk = pk[np.argsort(prop['peak_heights'])]
            prop['peak_heights'].sort()
            pinit.append( y[0] )
            params = getfullargspec(self.func).args[1:]
            if (len(params)-1)%3 == 0:
                param_per_peak = 3
                peak_number = (len(params)-1)//3
                for i in range(peak_number):
                    pinit.append( 0.5 )                         # height
                    pinit.append( x[pk[i]]  )                   # position
                    pinit.append( prop['widths'][i] * xbin )    # sigma
                   #print(prop['widths'][i] * xbin)
            elif (len(params)-1)%4 == 0:
                param_per_peak = 4
                peak_number = (len(params)-1)//4
                for i in range(peak_number):
                    pinit.append( 0.5 )                         # height
                    pinit.append( x[pk[i]]  )                   # position
                    pinit.append( prop['widths'][i] * xbin/2 ) # sigma
                    pinit.append( prop['widths'][i] * xbin/2 ) # gamma
        else:
            pinit.append( y[0] )
            params = getfullargspec(self.func).args[1:]
            if (len(params)-1)%3 == 0:
                param_per_peak = 3
                peak_number = (len(params)-1)//3
                for i in range(peak_number):
                    pinit.append( 0.5 )                         # height
                    pinit.append( guess_peak  )                   # position
                    pinit.append( 0.5 )    # sigma
            elif (len(params)-1)%4 == 0:
                param_per_peak = 4
                peak_number = (len(params)-1)//4
                for i in range(peak_number):
                    pinit.append( 0.5 )                         # height
                    pinit.append( guess_peak  )                   # position
                    pinit.append( 0.2 ) # sigma
                    pinit.append( 0.2 ) # gamma
        return pinit


    def __repr__(self):
        return 'GaugeFitModel : ' + str( self.__dict__ )
    


class HPData():

    def __init__(self, Pm, P, x, T, x0, T0, calib, file):
        super().__init__()

        self.Pm = Pm
        self.P = P
        self.x = x
        self.T = T
        self.x0 = x0
        self.T0 = T0
        self.calib = calib
        self.file = file

    def __repr__(self):
        return str(self.df)

    def calcP(self):
        self.P = self.calib.func(self.x, self.T, self.x0, self.T0)

    def invcalcP(self):
        self.x = self.calib.invfunc(self.P, self.T, self.x0, self.T0)

    # SOMETHING TO RETRIEVE THE CALIB OBJECT BY ITS NAME ?

    @property
    def df(self):       
        _df = pd.DataFrame({'Pm': self.Pm,
                            'P' : self.P, 
                            'x' : self.x,
                            'T' : self.T,
                            'x0': self.x0,
                            'T0': self.T0,
                            'calib': self.calib.name,
                            'file' : self.file}, index=[0])
        return _df



class HPDataTable(QObject):
    
    changed = pyqtSignal()

    def __init__(self, df=None, calibrations=None):
        super().__init__()  
    
        self.datalist = []

        if df is not None:
            self.reconstruct_from_df(df, calibrations)

    def __repr__(self):
        return str( self.df )

    def __getitem__(self, index):
        return self.datalist[index]

    def __setitem__(self, index, HPDataobj):
        self.datalist[index] = HPDataobj
        self.changed.emit()

    def __len__(self):
        return len(self.datalist)


    def recalc_item_P(self, index):
        # method implemented to emit change!
        self.datalist[index].calcP()
        self.changed.emit()

    def reinvcalc_item_P(self, index):
        self.datalist[index].invcalcP()
        self.changed.emit()

    def setitemval(self, item, attr, val):
        if val != getattr(self.datalist[item],attr): 
            setattr(self.datalist[item], attr, val)
            self.changed.emit()

    def add(self, buffer):
        # NB:  deepcopy fails if HPData inherits from QObject !
        # deepcopy absolutely necessary here
        # Here I work with the HPData object
        self.datalist.append( deepcopy(buffer) )
        self.changed.emit()

    def removelast(self):
        # Here I work with the HPData object
        self.datalist = self.datalist[:-1]
        self.changed.emit()

    def removespecific(self, index):
        del self.datalist[index]
        self.changed.emit()

    def reconstruct_from_df(self, df, calibrations):
        # erases the previous content!
        self.datalist = []
        for _, row in df.iterrows():
            HPdi = HPData(Pm = row['Pm'],
                          P  = row['P'], 
                          x  = row['x'], 
                          T  = row['T'], 
                          x0 = row['x0'], 
                          T0 = row['T0'],
                          calib = calibrations[row['calib']], # retrieve calib
                          file = row['file'])
            self.datalist.append(HPdi)
        self.changed.emit()

    @property
    def df(self):
        # should be used only as a REPRESENTATION of HPDataTable
        _df = pd.DataFrame(columns=['Pm','P','x','T','x0','T0','calib','file'])
        for xi in self.datalist:
            _df = pd.concat([_df, xi.df ], ignore_index=True)
        return _df
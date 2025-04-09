import os
import time
import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks
from inspect import getfullargspec
import helpers
from scipy.spatial import ConvexHull
from scipy.ndimage import uniform_filter1d, gaussian_filter1d
from scipy.optimize import curve_fit


class PressureGaugeDataObject:
    """
    This classes represents a pressure gauge spectrum, with all its associated properties.
    """

    def __init__(self):
        """
        Initialize the PressureGaugeDataObject with an ID.
        """

        self.id = int(time.time() * 1000)

        # Attributes related to spectral measurement data
        self.filename = None
        self.path = None
        self.original_data = None
        self.normalized_data = None
        self.corrected_data = None
        self.bg = None
        self.current_smoothing = None
        self.fit_model = None
        self.fit_result = None
        self.fitted_data = None
        self.fit_toolbox_config = None

        # Attributes related to pressure determination from a calibration
        self.calib = None
        self.Pm = None
        self.P = None
        self.x = None
        self.T = None
        self.x0 = None
        self.T0 = None

        # Attributes related to visualization
        self.include_in_filelist = False
        self.filelist_id = None
        self.include_in_table = False
        self.table_id = None
        
    def __repr__(self):
        """
        Return a string representation of the PressureGaugeDataObject.

        :return: str
        """
        return f"PressureGaugeDataObject(id={self.id}, name={self.filename}, path={self.path})"

    def load_spectral_data_file(self, file_name, file_path):
        self.filename = file_name
        self.path = file_path
        self.original_data = helpers.customparse_file2data(self.path)
        self.normalize_data()
        self.current_smoothing = 1


    def normalize_data(self):
        self.normalized_data = np.zeros(self.original_data.shape)
        self.normalized_data[:,1] = self.original_data[:,1]-np.min(self.original_data[:,1])
        self.normalized_data[:,1]=self.original_data[:,1]/max(self.original_data[:,1])

    def compute_P_from_x(self):
        self.P = self.calib.func(self.x, self.T, self.x0, self.T0)

    def invcalcP(self):
        self.x = self.calib.invfunc(self.P, self.T, self.x0, self.T0)

    def get_data_to_process(self):
        """
        Get the data to be processed. If corrected_data is available, use it; otherwise, use normalized_data.
        """
        if self.corrected_data is not None:
            return self.corrected_data[:, 0], self.corrected_data[:, 1]
        else:
            return self.normalized_data[:, 0], self.normalized_data[:, 1]
    
    def smoothen(self,smooth_window):
        """
        Smooth the spectrum using a uniform filter.
        :param smooth_window: int, size of the smoothing window
        """
        if self.original_data is not None:
            self.corrected_data = np.column_stack(
                (
                    self.normalized_data[:, 0],
                    uniform_filter1d(self.normalized_data[:, 1], size=smooth_window),
                )
            )
            #self.plot_data()
        else:
            raise ValueError("No original data to smooth.")
        
    def convexhull_bg(self):
        """
        Calculate a spectrum background using the convex hull method.
        """

        x, y = self.get_data_to_process()
        v = ConvexHull(np.column_stack((x, y))).vertices
        v = np.roll(v, -v.argmin())
        anchors = v[: v.argmax()]
        self.bg = np.interp(x, x[anchors], y[anchors])
        corrected = y - self.bg

        self.corrected_data = np.column_stack((x, corrected))
        # self.plot_data()

    def reset_bg(self):
        self.corrected_data = None
        self.bg = None
        #self.plot_data()
    
    def subtract_external_bg(self, bg):
        """
        Subtract an external background from the spectrum.
        """
        x, y = self.get_data_to_process()
        if len(bg) != len(x):
            raise ValueError("Background and data arrays must have the same length.")
        else:
            corrected = y - bg
            self.corrected_data = np.column_stack((x, corrected))
        #self.plot_data()

    def fit_data(self):
        """
        Fit the spectrum using the selected model, and update the pressure estimate.
        :param fit_model: GaugeFitModel
        """
        x,y = self.get_data_to_process()
        try:
            self.fit_result = self.fit_procedure(self.fit_model, x, y)
            if self.fit_model.type == "peak":
                fitted = [self.fit_model.func(wvl, *self.fit_result["opti"]) for wvl in x]
                self.fitted_data = np.column_stack((x, fitted))
                popt = self.fit_result["opti"]
                # for now we use the number of args..
                if len(popt) < 7:  # Samarium
                    best_x = popt[2]
                elif len(popt) < 8:  # Ruby Gaussian
                    best_x = np.max([popt[2], popt[5]])
                else:  # Ruby Voigt
                    best_x = np.max([popt[2], popt[6]])

                
            elif self.fit_model.type == "edge":
                self.fitted_data = self.fit_result["opti"]
            else:
                raise ValueError("Fit type not implemented")
            
            self.x = best_x
            self.compute_P_from_x()
        except:
            raise RuntimeError("Fit failed to converge.")
            # msg = QMessageBox()
            # msg.setIcon(QMessageBox.Critical)
            # msg.setText("Attempted fit couldn't converge.")
            # msg.setWindowTitle("Fit error")
            # msg.exec_()

    def fit_procedure(self, model, x, y, guess_peak=None):
        if model.type == "peak":
            try:
                popt, pcov = curve_fit(
                    model.func, x, y, p0=model.get_pinit(x, y, guess_peak=guess_peak)
                )

                # self.x_spinbox.setValue(best_x)
                return {"opti": popt, "cov": pcov}

            except RuntimeError:
                # msg = QMessageBox()
                # msg.setIcon(QMessageBox.Critical)
                # msg.setText("Attempted fit couldn't converge.")
                # msg.setWindowTitle("Fit error")
                # msg.exec_()
                return

        elif model.type == "edge":
            grad = np.gradient(y)
            best_x = x[np.argmin(grad)]
            # self.x_spinbox.setValue(best_x)
            return {"opti": best_x, "cov": None}


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
                                    x0=self.x0default, method='Powell', tol=1e-6)
        
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
        
        xbin = x[1] - x[0] # nm/px or cm-1/px
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
                    pinit.append( 0.5 )             # height
                    pinit.append( guess_peak -1.5*i ) # idiot trick for the 2nd peak
                    pinit.append( 0.5 )    # sigma
            elif (len(params)-1)%4 == 0:
                param_per_peak = 4
                peak_number = (len(params)-1)//4
                for i in range(peak_number):
                    pinit.append( 0.5 )             # height
                    pinit.append( guess_peak -1.5*i ) # idiot trick for the 2nd peak
                    pinit.append( 0.2 ) # sigma
                    pinit.append( 0.2 ) # gamma
        return pinit


    def __repr__(self):
        return 'GaugeFitModel : ' + str( self.__dict__ )

class PressureGaugeDataManager:
    """
    A class to manage and store all instances of PressureGaugeDataObject.
    """

    def __init__(self):
        """
        Initialize the PressureGaugeDataManager with an empty list of objects.
        """
        self.instances = []

    def add_instance(self, instance):
        """
        Add a PressureGaugeDataObject instance to the manager.

        :param instance: PressureGaugeDataObject
        """
        if isinstance(instance, PressureGaugeDataObject):
            self.instances.append(instance)
        else:
            raise TypeError("Only instances of PressureGaugeDataObject can be added.")

    def get_instance_by_id(self, instance_id):
        """
        Retrieve a PressureGaugeDataObject instance by its ID.

        :param instance_id: int
        :return: PressureGaugeDataObject or None
        """
        for instance in self.instances:
            if instance.id == instance_id:
                return instance
        return None

    def remove_instance_by_id(self, instance_id):
        """
        Remove a PressureGaugeDataObject instance by its ID.

        :param instance_id: int
        """
        self.instances = [inst for inst in self.instances if inst.id != instance_id]

    def __repr__(self):
        """
        Return a string representation of the PressureGaugeDataManager.

        :return: str
        """
        return f"PressureGaugeDataManager({len(self.instances)} instances)"


if __name__ == '__main__':

    test_obj = PressureGaugeDataObject()
    data_manager = PressureGaugeDataManager()
    data_manager.add_instance(test_obj)
    print(data_manager)
    print(data_manager.get_instance_by_id(test_obj.id))
    test_file = 'Example_Ruby_1.asc'
    test_path = os.path.dirname(__file__) + "/resources/" + test_file
    test_obj.load_spectral_data_file(test_file, test_path)
    


import os
import time
import numpy as np
from scipy.optimize import minimize
from scipy.signal import find_peaks
from inspect import getfullargspec
import myPGM.helpers
import myPGM.calibrations
import myPGM.fit_models
from scipy.spatial import ConvexHull
from scipy.ndimage import uniform_filter1d, gaussian_filter1d
from scipy.optimize import curve_fit
from collections.abc import MutableMapping

import matplotlib.pyplot as plt


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
        return f"PressureGaugeDataObject(id={self.id}, name={self.filename}, P={self.P})"

    def __str__(self):

        return f"PressureGaugeDataObject(id={self.id}, name={self.filename}, P={self.P})"

    def load_spectral_data_file(self, file_name, file_path):
        self.filename = file_name
        self.path = file_path
        self.original_data = myPGM.helpers.customparse_file2data(self.path)
        self.normalize_data()
        self.current_smoothing = 1
        self.include_in_filelist = True


    def set_calibration(self, calib):
        """
        Set the calibration for the pressure gauge data object.
        :param calib: HPCalibration
        """
        self.calib = calib
        self.x0 = self.calib.x0default
        self.T0 = 0
        self.T = 0

    def set_fit_model(self, fit_model):
        """
        Set the fit model for the pressure gauge data object.
        :param fit_model: GaugeFitModel
        """
        self.fit_model = fit_model


    def normalize_data(self):
        self.normalized_data = np.zeros(self.original_data.shape)
        self.normalized_data[:,0] = self.original_data[:,0]
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

    def fit_data(self, guess_peak=None):
        """
        Fit the spectrum using the selected model, and update the pressure estimate.
        :param fit_model: GaugeFitModel
        """
        x,y = self.get_data_to_process()
        
        try:
            
            self.fit_result = self.fit_procedure(self.fit_model, x, y, guess_peak=guess_peak)
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
                best_x = self.fitted_data
            else:
                raise ValueError("Fit type not implemented")
            
            self.x = best_x
            self.compute_P_from_x()
        except:
            raise RuntimeError("Fit failed to converge.")
            

    def fit_procedure(self, model, x, y, guess_peak=None):
        if model.type == "peak":
            try:
                popt, pcov = curve_fit(
                    model.func, x, y, p0=model.get_pinit(x, y, guess_peak=guess_peak)
                    )

                    # self.x_spinbox.setValue(best_x)
                return {"opti": popt, "cov": pcov}

            except:
                 raise RuntimeError("Fit failed to converge.")

        elif model.type == "edge":
            if guess_peak is not None:
                best_x = guess_peak
            else:
                grad = np.gradient(y)
                best_x = x[np.argmin(grad)]
            # self.x_spinbox.setValue(best_x)
            return {"opti": best_x, "cov": None}




class PressureGaugeDataManager(MutableMapping):
    def __init__(self, *args, **kwargs):
        '''Use the object dict'''

        super().__init__()
        self.__dict__.update(*args, **kwargs)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]

    def __delitem__(self, key):
        del self.__dict__[key]

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __repr__(self):
        return f"{type(self).__name__} ({len(self.__dict__)} pressure gauge data point(s))"

    def add_instance(self, instance):
        """
        Add a PressureGaugeDataObject instance to the manager.

        :param instance: PressureGaugeDataObject
        """
        if isinstance(instance, PressureGaugeDataObject):
            self.__dict__[instance.id] = instance
        else:
            raise TypeError("Only instances of PressureGaugeDataObject can be added.")

if __name__ == '__main__': #! to be verified
    import calibrations
    import fit_models
    data_manager = PressureGaugeDataManager()
    a = PressureGaugeDataObject()
    data_manager.add_instance(a)
    test_file = 'Example_Ruby_3.asc'
    test_path = os.path.dirname(__file__) + "/resources/" + test_file
    
    a.load_spectral_data_file(test_file, test_path)

    # plt.figure()
    # plt.plot(test_obj.original_data[:,0], test_obj.original_data[:,1])
    # plt.show()
    a.set_calibration(calibrations.Ruby2020)
    a.set_fit_model(fit_models.DoubleVoigt)
    a.fit_data()
    print(f'Fitted ruby wavelength: {a.x} nm')
    print(f'Fitted pressure: {a.P} GPa')
    print('##################################################################')
    print([k for k in data_manager.values()])

 
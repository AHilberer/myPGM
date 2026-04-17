import os
import time
import numpy as np

import myPGM.helpers

from scipy.spatial import ConvexHull
from scipy.ndimage import uniform_filter1d
from scipy.optimize import curve_fit
from collections.abc import MutableMapping


def _array_to_list(value):
    if value is None:
        return None
    return np.asarray(value).tolist()


def _list_to_array(value):
    if value is None:
        return None
    return np.asarray(value)


def _json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


def _fit_result_to_dict(fit_result):
    if fit_result is None:
        return None
    opti = fit_result.get("opti")
    cov = fit_result.get("cov")
    return {
        "opti": _array_to_list(opti)
        if isinstance(opti, (list, tuple, np.ndarray))
        else _json_scalar(opti),
        "cov": _array_to_list(cov),
    }


def _fit_result_from_dict(payload):
    if payload is None:
        return None
    opti = payload.get("opti")
    cov = payload.get("cov")
    if isinstance(opti, list):
        opti = np.asarray(opti)
    if isinstance(cov, list):
        cov = np.asarray(cov)
    return {"opti": opti, "cov": cov}


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
        self.full_path = None
        self.original_data = None
        self.normalized_data = None
        self.corrected_data = None
        self.bg = None
        self.current_smoothing = None
        self.fit_model = None
        self.fit_result = None
        self.fitted_data = None
        self.fit_toolbox_config = None
        self.fitting_range = None

        # Attributes related to pressure determination from a calibration
        self.calib = None
        self.Pm = None
        self.P = None
        self.x = None
        self.T = 298      # default T and T0 are 298 at __init__ for script use
        self.x0 = None    # in GUI T, T0 are set at 298 independently.
        self.T0 = 298     # x0, T0 are set in set_calibration

        # Attributes related to visualization
        self.include_in_filelist = False
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

    @staticmethod
    def generate_id():
        """
        Generate a unique ID based on the current time in milliseconds.

        :return: int
        """
        return int(time.time() * 1000)
    

    def load_spectral_data_file(self, file_name, file_path):
        self.filename = file_name
        self.full_path = file_path
        self.original_data = myPGM.helpers.customparse_file2data(self.full_path)
        self.normalize_data()
        self.current_smoothing = 1
        self.include_in_filelist = True
        
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

    def to_dict(self):
        return {
            "id": _json_scalar(self.id),
            "filename": self.filename,
            "full_path": self.full_path,
            "original_data": _array_to_list(self.original_data),
            "normalized_data": _array_to_list(self.normalized_data),
            "corrected_data": _array_to_list(self.corrected_data),
            "bg": _array_to_list(self.bg),
            "current_smoothing": _json_scalar(self.current_smoothing),
            "fit_model": self.fit_model.name if self.fit_model else None,
            "fit_result": _fit_result_to_dict(self.fit_result),
            "fitted_data": _array_to_list(self.fitted_data),
            "fit_toolbox_config": self.fit_toolbox_config,
            "fitting_range": list(self.fitting_range) if self.fitting_range is not None else None,
            "calib": self.calib.name if self.calib else None,
            "Pm": _json_scalar(self.Pm),
            "P": _json_scalar(self.P),
            "x": _json_scalar(self.x),
            "T": _json_scalar(self.T),
            "x0": _json_scalar(self.x0),
            "T0": _json_scalar(self.T0),
            "include_in_filelist": self.include_in_filelist,
            "include_in_table": self.include_in_table,
            "table_id": _json_scalar(self.table_id),
        }

    @classmethod
    def from_dict(cls, payload, calib_dict=None, model_dict=None):
        obj = cls()
        obj.id = payload.get("id", obj.id)
        obj.filename = payload.get("filename")
        obj.full_path = payload.get("full_path")
        obj.original_data = _list_to_array(payload.get("original_data"))
        obj.normalized_data = _list_to_array(payload.get("normalized_data"))
        obj.corrected_data = _list_to_array(payload.get("corrected_data"))
        obj.bg = _list_to_array(payload.get("bg"))
        obj.current_smoothing = payload.get("current_smoothing")

        calib_name = payload.get("calib")
        if calib_dict is not None and calib_name in calib_dict:
            obj.calib = calib_dict[calib_name]
        else:
            obj.calib = None

        fit_model_name = payload.get("fit_model")
        if model_dict is not None and fit_model_name in model_dict:
            obj.fit_model = model_dict[fit_model_name]
        else:
            obj.fit_model = None

        obj.fit_result = _fit_result_from_dict(payload.get("fit_result"))
        obj.fitted_data = _list_to_array(payload.get("fitted_data"))
        obj.fit_toolbox_config = payload.get("fit_toolbox_config")
        obj.fitting_range = payload.get("fitting_range")

        obj.Pm = payload.get("Pm")
        obj.P = payload.get("P")
        obj.x = payload.get("x")
        obj.T = payload.get("T", 298)
        obj.x0 = payload.get("x0")
        obj.T0 = payload.get("T0", 298)

        obj.include_in_filelist = payload.get("include_in_filelist", False)
        obj.include_in_table = payload.get("include_in_table", False)
        obj.table_id = payload.get("table_id")
        return obj


#    We may choose to use such read-only properties to avoid problems?
#    @property
#    def P(self):
#        return self._P

#   or even, extreme but very safe : 
#   @property
#   def P(self):
#       return self._P
#  
#   @P.setter
#   def P(self, value):
#       self._P = value
#       self.compute_x_from_P()

    def set_calibration(self, calib):
        """
        Set the calibration for the pressure gauge data object.
        :param calib: HPCalibration
        """
        self.calib = calib

        self.set_x0(self.calib.x0default)
        self.set_T0(self.calib.T0default)

    def set_Pm(self, Pm):
        self.Pm = Pm
        return self.Pm

    def set_P(self, P):
        self.P = P
        self._compute_x_from_P()
        return self.x

    def set_x(self, x):
        self.x = x
        self._compute_P_from_x()
        return self.P

    def set_x0(self, x0):
        self.x0 = x0
        self._compute_P_from_x()
        return self.P

    def set_T(self, T):
        self.T = T
        self._compute_P_from_x()
        return self.P

    def set_T0(self, T0):
        self.T0 = T0
        self._compute_P_from_x()
        return self.P

    def _compute_P_from_x(self):
        try:
            if self.x is not None:
                self.P = self.calib.func(self.x, self.T, self.x0, self.T0)
                myPGM.helpers.validate_scalar(self.P, 'Pressure')
            else:
                self.P = None
        except Exception as e:
            raise myPGM.helpers.PressureCalculationFailed(
                f'Pressure Calculation Failed: {e}') from e

    def _compute_x_from_P(self):
        try:
            if self.P is not None:
                self.x = self.calib.invfunc(self.P, self.T, self.x0, self.T0)
                myPGM.helpers.validate_scalar(self.x, 'x')
            else:
                self.x = None
        except Exception as e:
            raise myPGM.helpers.PressureCalculationFailed(
                f'Pressure Calculation Failed: {e}') from e

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
            if self.bg is not None:
                filtered = uniform_filter1d(self.normalized_data[:, 1], size=smooth_window)-self.bg
            else:
                filtered = uniform_filter1d(self.normalized_data[:, 1], size=smooth_window)
            self.corrected_data = np.column_stack(
                (self.normalized_data[:, 0], filtered)
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
            self.bg = bg
        #self.plot_data()


    def spectro_recalib(self, new_x):
        try:
            x, y = self.get_data_to_process()
            if len(new_x) != len(y):
                raise ValueError(
                    f"Calibration length mismatch: expected {len(y)} points, got {len(new_x)}."
                )
            self.corrected_data = np.column_stack(
                (new_x, y)
            )
        except Exception as exc:
            raise RuntimeError(f'Failed to recalibrate spectrometer: {exc}') from exc
    
    def reset_spectro_recalib(self):
        x, y = self.get_data_to_process()
        self.corrected_data = np.column_stack(
                (self.normalized_data[:, 0], y)
            )

    def fit_data(self, guess_peak=None):
        """
        Fit the spectrum using the selected model, and update the pressure estimate.
        :param fit_model: GaugeFitModel
        """
        x,y = self.get_data_to_process()
        if self.fitting_range is not None:
            mask = (x >= self.fitting_range[0]) & (x <= self.fitting_range[1])
            x = x[mask]
            y = y[mask]
        
        try:
            
            self.fit_result = self.fit_procedure(self.fit_model, x, y, guess_peak=guess_peak)
            if self.fit_model.type == "peak":
                fitted = [self.fit_model.func(wvl, *self.fit_result["opti"]) for wvl in x]
                self.fitted_data = np.column_stack((x, fitted))
                popt = self.fit_result["opti"]

                # for now we use the number of args.... (crappy)
                if len(popt) < 7:  # Samarium / Hydrogen (?)
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
            
            self.set_x(best_x)
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

    def clear(self):
        self.__dict__.clear()

    def add_instance(self, instance):
        """
        Add a PressureGaugeDataObject instance to the manager.

        :param instance: PressureGaugeDataObject
        """
        if isinstance(instance, PressureGaugeDataObject):
            self.__dict__[instance.id] = instance
        else:
            raise TypeError("Only instances of PressureGaugeDataObject can be added.")
        
    def delete_instance(self, instance_id):
        """
        Delete a PressureGaugeDataObject instance from the manager by its ID.

        :param instance_id: int
        """
        if instance_id in self.__dict__:
            del self.__dict__[instance_id]
        else:
            raise KeyError(f"No instance with ID {instance_id} found.")
        

if __name__ == '__main__':

    from myPGM import calibrations, fit_models
    
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

    print('##################################################################')
    # test reverse
    a.set_P(6)
    print(f' pressure: {a.P} GPa')
    print(f' ruby wavelength: {a.x} nm')

    print('##################################################################')
    a.set_calibration(calibrations.cBNDatchi)
    
    # force error
    a.set_x(1045)
    a.set_x0(0)
    a.set_T0(0)
    #a.set_P(0)

    print(a.P)
    print(a.x, a.x0, a.T, a.T0)
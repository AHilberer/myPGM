import numpy as np
from scipy.special import voigt_profile as voigt
from scipy.signal import find_peaks
from inspect import getfullargspec

class GaugeFitModel():
    ''' A general pressure gauge fitting model object '''
    def __init__(self, name, func,type, color):
        self.name = name
        self.func = func
        self.type = type
        self.color = color  # color printed in calibration combobox

    def get_pinit(self, x, y, guess_peak=None):
        ''' Initial parameters: offset c, then per peak height, position and
            width(s): (a, x, sigma) or, for Voigt, (a, x, sigma, gamma). '''
        n_params = len(getfullargspec(self.func).args) - 2   # minus x and c
        params_per_peak = 3 if n_params % 3 == 0 else 4
        peak_number = n_params // params_per_peak

        if guess_peak is None:
            xbin = x[1] - x[0] # nm/px or cm-1/px
            positions, widths = self._find_peak_guesses(x, y, xbin, peak_number)
            # a Voigt splits the width between its Gaussian and Lorentzian parts
            widths = widths if params_per_peak == 3 else [w / 2 for w in widths]
        else:
            # clicked position; any 2nd peak is started 1.5 x-units below it
            positions = [guess_peak - 1.5 * i for i in range(peak_number)]
            widths = [0.5 if params_per_peak == 3 else 0.2] * peak_number

        pinit = [y[0]]
        for position, width in zip(positions, widths):
            if params_per_peak == 4:
                amplitude = self._voigt_amplitude(x, y, position, width, offset=y[0])
            else:
                amplitude = 0.5
            pinit += [amplitude, position] + [width] * (params_per_peak - 2)
        return pinit

    @staticmethod
    def _voigt_amplitude(x, y, position, width, offset):
        ''' The Voigt amplitude is the peak area: start from the one giving the
            measured peak height, whatever the units and peak width (a fixed 0.5
            gave a starting peak 36x too low for the ~10 cm-1 wide H2 vibron). '''
        height = y[np.argmin(np.abs(x - position))] - offset
        height = max(height, 0.1 * np.ptp(y))      # keep a positive, sensible start
        return height / voigt(0, width, width)

    @staticmethod
    def _find_peak_guesses(x, y, xbin, peak_number):
        ''' Positions and widths (x units) of the peak_number tallest peaks,
            tallest first. Missing peaks are guessed next to the tallest one. '''
        pk, prop = find_peaks(y - np.min(y), height = np.ptp(y)/2, width=0.1/abs(xbin))
        order = np.argsort(prop['peak_heights'])[::-1]
        positions = list(x[pk[order]])
        widths = list(prop['widths'][order] * abs(xbin))

        if not positions:
            positions = [x[np.argmax(y)]]
            widths = [10 * abs(xbin)]
        while len(positions) < peak_number:
            # e.g. unresolved doublet: start the extra peak just beside the main one
            positions.append(positions[0] - widths[0])
            widths.append(widths[0])
        return positions[:peak_number], widths[:peak_number]


    def __repr__(self):
        return 'GaugeFitModel : ' + str( self.__dict__ )



def Single_Gaussian(x, c, a1, x1, sigma1):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2))

def Single_Voigt(x, c, a1, x1, sigma1, gamma1):
    return c + a1 * voigt(x-x1, sigma1, gamma1)

def Single_Lorentzian(x, c, a1, x1, gamma1):
    return c + a1 * (2/(np.pi*gamma1)) / (1 + ((x - x1)/(gamma1/2))**2)

def Double_Gaussian(x, c, a1, x1, sigma1, a2, x2, sigma2):
    return Single_Gaussian(x, c, a1, x1, sigma1) + \
           Single_Gaussian(x, 0, a2, x2, sigma2)

def Double_Voigt(x, c, a1, x1, sigma1, gamma1, a2, x2, sigma2, gamma2):
    return Single_Voigt(x, c, a1, x1, sigma1, gamma1) + \
           Single_Voigt(x, 0, a2, x2, sigma2, gamma2)

def Double_Lorentzian(x, c, a1, x1, gamma1, a2, x2, gamma2):
    return Single_Lorentzian(x, c, a1, x1, gamma1) + \
           Single_Lorentzian(x, 0, a2, x2, gamma2)    


DoubleVoigt = GaugeFitModel(name = 'Double Voigt',
                                 func = Double_Voigt,
                                 type = 'peak',
                                 color = 'firebrick')

DoubleGaussian = GaugeFitModel(name = 'Double Gaussian',
                                 func = Double_Gaussian,
                                 type = 'peak',
                                 color = 'firebrick')

DoubleLorentzian = GaugeFitModel(name = 'Double Lorentzian',
                                 func = Double_Lorentzian,
                                 type = 'peak',
                                 color = 'firebrick')

SingleLorentzian = GaugeFitModel(name = 'Single Lorentzian',
                                 func = Single_Lorentzian,
                                 type = 'peak',
                                 color = 'mediumseagreen')

SingleVoigt= GaugeFitModel(name = 'Single Voigt',
                                    func = Single_Voigt,
                                    type = 'peak',
                                    color = 'mediumseagreen')
                
SingleGaussian = GaugeFitModel(name = 'Single Gaussian',
                                    func = Single_Gaussian,
                                    type = 'peak',
                                    color = 'mediumseagreen')

RamanEdge = GaugeFitModel(name = 'Raman Edge',
                                    func = None,
                                    type = 'edge',
                                    color = 'darkgrey')        
        
model_list = [DoubleVoigt,
              DoubleLorentzian,
              DoubleGaussian,
              SingleVoigt,
              SingleLorentzian,
              SingleGaussian,
              RamanEdge
              ]
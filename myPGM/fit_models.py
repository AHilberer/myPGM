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
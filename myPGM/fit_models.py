import numpy as np
from scipy.special import voigt_profile as voigt

import helpers

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


DoubleVoigt = helpers.GaugeFitModel(name = 'Double Voigt',
                                 func = Double_Voigt,
                                 type = 'peak',
                                 color = 'firebrick')

DoubleGaussian = helpers.GaugeFitModel(name = 'Double Gaussian',
                                 func = Double_Gaussian,
                                 type = 'peak',
                                 color = 'firebrick')

DoubleLorentzian = helpers.GaugeFitModel(name = 'Double Lorentzian',
                                 func = Double_Lorentzian,
                                 type = 'peak',
                                 color = 'firebrick')

SingleLorentzian = helpers.GaugeFitModel(name = 'Single Lorentzian',
                                 func = Single_Lorentzian,
                                 type = 'peak',
                                 color = 'mediumseagreen')

SingleVoigt= helpers.GaugeFitModel(name = 'Single Voigt',
                                    func = Single_Voigt,
                                    type = 'peak',
                                    color = 'mediumseagreen')
                
SingleGaussian = helpers.GaugeFitModel(name = 'Single Gaussian',
                                    func = Single_Gaussian,
                                    type = 'peak',
                                    color = 'mediumseagreen')

RamanEdge = helpers.GaugeFitModel(name = 'Raman Edge',
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
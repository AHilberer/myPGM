import numpy as np
from scipy.special import voigt_profile as voigt

import helpers


def Single_Gaussian(x, c, a1, x1, sigma1):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2))

def Single_Voigt(x, c, a1, x1, sigma1, gamma1):
    return c + a1 * voigt(x-x1, sigma1, gamma1)

def Double_Gaussian(x, c, a1, x1, sigma1, a2, x2, sigma2):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2)) + a2*np.exp(-(x-x2)**2/(2*sigma2**2))

def Double_Voigt(x, c, a1, x1, sigma1, gamma1, a2, x2, sigma2, gamma2):
    return c + a1 * voigt(x-x1, sigma1, gamma1) + a2 * voigt(x-x2, sigma2, gamma2)


DoubleVoigt = helpers.GaugeFitModel(name = 'Double Voigt',
							     func = Double_Voigt,
                                 type = 'peak',
                                 color = 'lightcoral')

DoubleGaussian = helpers.GaugeFitModel(name = 'Double Gaussian',
							     func = Double_Gaussian,
                                 type = 'peak',
							     color = 'lightcoral')
                
SingleVoigt= helpers.GaugeFitModel(name = 'Single Voigt',
							     	func = Single_Voigt,
                                    type = 'peak',
							     	color = 'royalblue')
                
SingleGaussian = helpers.GaugeFitModel(name = 'Single Gaussian',
							     	func = Single_Gaussian,
                                    type = 'peak',
							     	color = 'royalblue')

RamanEdge = helpers.GaugeFitModel(name = 'Raman Edge',
							     	func = None,
                                    type = 'edge',
							     	color = 'darkgrey')        
        
model_list = [DoubleVoigt,
              DoubleGaussian,
              SingleVoigt,
              SingleGaussian,
              RamanEdge
              ]
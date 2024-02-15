import numpy as np
from scipy.special import voigt_profile as voigt

import helpers


def Sm_model(x, c, a1, x1, sigma1):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2))

def Ruby_model_gauss(x, c, a1, x1, sigma1, a2, x2, sigma2):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2)) + a2*np.exp(-(x-x2)**2/(2*sigma2**2))

def Ruby_model_voigts(x, c, a1, x1, sigma1, gamma1, a2, x2, sigma2, gamma2):
    return c + a1 * voigt(x-x1, sigma1, gamma1) + a2 * voigt(x-x2, sigma2, gamma2)


RubyVoigt = helpers.GaugeFitModel(name = 'Ruby Voigt',
							     func = Ruby_model_gauss,
                                 type = 'fit',
                                 color = 'red')

RubyGauss = helpers.GaugeFitModel(name = 'Ruby Gaussian',
							     func = Ruby_model_gauss,
                                 type = 'fit',
							     color = 'lightcoral')
                
SamariumGauss = helpers.GaugeFitModel(name = 'Samarium Gaussian',
							     	func = Sm_model,
                                    type = 'fit',
							     	color = 'royalblue')
        

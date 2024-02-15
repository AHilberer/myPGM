import numpy as np
from scipy.special import voigt_profile as voigt

def Sm_model(x, c, a1, x1, sigma1):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2))

def SmPressure(lambda_Sm, lambda_Sm_0=685.41):
    # Datchi 1997
    delta_lambda = abs(lambda_Sm-lambda_Sm_0)
    P = 4.032*delta_lambda*(1 + 9.29e-3*delta_lambda)/(1 + 2.32e-2*delta_lambda)
    return P

def Ruby_model(x, c, a1, x1, sigma1, a2, x2, sigma2):
    return c + a1*np.exp(-(x-x1)**2/(2*sigma1**2)) + a2*np.exp(-(x-x2)**2/(2*sigma2**2))

def Ruby_model_voigts(x, c, a1, x1, sigma1, gamma1, a2, x2, sigma2, gamma2):
    return c + a1 * voigt(x-x1, sigma1, gamma1) + a2 * voigt(x-x2, sigma2, gamma2)

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
import numpy as np


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


        
# Shen G., Wang Y., Dewaele A. et al. (2020) High Pres. Res. doi: 10.1080/08957959.2020.1791107
def Pruby2020(l, T, l0, T0):
    dT = T - T0
    dlcorr = 0.00746 * dT - 3.01e-6 * dT**2 + 8.76e-9 * dT**3  # Datchi HPR 2007
    dl = (l - dlcorr) - l0
    P = 1870 * dl/l0 * (1 + 5.63 * dl/l0)

    return P

#  F. Datchi, High Pressure Research, 27:4, 447-463, DOI: 10.1080/08957950701659593 
def PsamDatchi1997(l, T, l0, T0):
    dT = T - T0
    dlcorr = -8.7e-5 * dT + 4.62e-6 * dT**2 -2.38e-9 * dT**3    # problem here !? (Datchi HPR 2007)
    if T >= 500:
        dlcorr = 1.06e-4 * (T-500) + 1.5e-7 * (T-500)**2    # these Queyroux p. 68
    else:
        dlcorr = 0
    #dlcorr=0
    dl = (l-dlcorr) - l0
    P = 4.032 * dl * (1 + 9.29e-3 * dl) / (1 + 2.32e-2 * dl)
    return P

#  F. Datchi, High Pressure Research, 27:4, 447-463, DOI: 10.1080/08957950701659593 
def PcBN(nu, T, nu0, T0):
    # find nu(p = 0 GPa, T = 0 K)
    nu00 = nu0 + 0.0091 * T0 + 1.54e-5 * T0**2

    nu0_T = nu00 - 0.0091 * T - 1.54e-5 * T**2
    B0_T = 396.5 - 0.0288 * (T - 300) - 6.84e-6 * (T - 300)**2
    B0p = 3.62
    P = (B0_T/B0p) * ( (nu/nu0_T)**2.876 - 1 )
    return P

# AKAHAMA, KAWAMURA, JOURNAL OF APPLIED PHYSICS 100, 043516 2006
def PAkahama2006(nu, T, nu0, T0):
    K0  = 547 # GPa
    K0p = 3.75
    dnu = nu - nu0 
    p = K0 * (dnu/nu0) * (1 + 0.5 * (K0p -1)*dnu/nu0)
    return p 


# Eremets et al., Nat Commun 14, 907 (2023). https://doi.org/10.1038/s41467-023-36429-9
def PEremets2023(nu, T, nu0, T0):
    A  = 517 # GPa
    B = 764 # GPa
    dnu = nu - nu0 
    p = A * (dnu/nu0) + B * (dnu/nu0)**2
    return p 


def PHilberer2025(nu, T, nu0, T0):
    K0  = 576.521119539528 # GPa
    K0p = 3.2571168198326683
    dnu = nu - nu0 
    p = K0 * (dnu/nu0) * (1 + 0.5 * (K0p -1)*dnu/nu0)
    return p

# Homemade:
def H2_Vibron(nu, T=0, nu0=0, T0=0):
    f = np.polynomial.polynomial.Polynomial(
        (-14536565712.17933,
         +17309734.53397923,
         -8244.669967044751,
         +1.963452944114722,
         -0.0002337933432834734,
          1.113520628648027e-08))
    return f(nu)


Ruby2020 = HPCalibration(name = 'Ruby2020',
                                 func = Pruby2020,
                                 Tcor_name='Datchi 2007',
                                 xname = 'lambda',
                                 xunit = 'nm',
                                 x0default = 694.28,
                                 xstep = .01,
                                 color = 'firebrick')
        
SamariumDatchi = HPCalibration(name = 'Samarium SrB4O7 Datchi 1997',
                                       func = PsamDatchi1997,
                                       Tcor_name='Datchi 2007 (?)',
                                       xname = 'lambda',
                                       xunit = 'nm',
                                       x0default = 685.41,
                                       xstep = .01,
                                       color = 'mediumseagreen')

Hilberer2025 = HPCalibration(name = 'Diamond Raman Edge Hilberer 2025',
                                    func = PHilberer2025,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1334,
                                    xstep = .1,
                                    color = 'orangered')

Akahama2006 = HPCalibration(name = 'Diamond Raman Edge Akahama 2006',
                                    func = PAkahama2006,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1334,
                                    xstep = .1,
                                    color = 'darkgrey')

Eremets2023 = HPCalibration(name = 'Diamond Raman Edge Eremets 2023',
                                    func = PEremets2023,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1332.5,
                                    xstep = .1,
                                    color = 'steelblue')
        
cBNDatchi = HPCalibration(name = 'cBN Raman Datchi 2007',
                                  func = PcBN,
                                  Tcor_name='Datchi 2007',
                                  xname = 'nu',
                                  xunit = 'cm-1',
                                  x0default = 1054,
                                  xstep = .1,
                                  color = 'lightblue')

H2Vibron = HPCalibration(name = 'H2 Vibron <30GPa',
                                  func = H2_Vibron,
                                  Tcor_name='NA',
                                  xname = 'nu',
                                  xunit = 'cm-1',
                                  x0default = 4200,
                                  xstep = .1,
                                  color = 'plum')


calib_list = [Ruby2020, 
                      SamariumDatchi,
                      Hilberer2025,
                      Akahama2006,
                      Eremets2023,
                      H2Vibron,
                      cBNDatchi,
                      ]


if __name__ == '__main__': 
    import matplotlib.pyplot as plt
    import numpy as np

    print(H2Vibron)
    x = np.linspace(4000, 4260, 100)
    y = H2_Vibron(x, 0, 4150, 0)

    print( H2Vibron.invfunc(10) )

    plt.plot(y,x)
    plt.show()
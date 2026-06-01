import numpy as np
from scipy.optimize import minimize


class HPCalibration():
    ''' A general HP calibration object '''
    def __init__(self, name, func, Tcor_name, 
                    xname, xunit, x0default, T0default, xstep, color,
                    default_fit_model=None):
        self.name = name
        self.func = func
        self.Tcor_name = Tcor_name
        self.xname = xname
        self.xunit = xunit
        self.x0default = x0default
        self.T0default = T0default
        self.xstep = xstep  # x step in spinboxes using mousewheel
        self.color = color  # color printed in calibration combobox
        self.default_fit_model = default_fit_model

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

# H. Mao, J. Xu, and P. Bell, J. Geophys. Res. 91, 4673 1986
def PrubyMao1986(l, T, l0, T0):
    A = 1904 # GPa
    B = 7.665 
    dT = T - T0
    dlcorr = 0.00746 * dT - 3.01e-6 * dT**2 + 8.76e-9 * dT**3  # Datchi HPR 2007
    dl = (l - dlcorr) - l0
    P = (A/B) * ( (1 + dl/l0)**B - 1 )

    return P

# F. Datchi, R. LeToullec, and P. Loubeyre Journal of Applied Physics 81, 3333 (1997)
# https://doi.org/10.1063/1.365025
def PrubyMao1986_DatchiF(l, T, l0, T0):
    dT = T - T0
    dlcorr = 0.00746 * dT - 3.01e-6 * dT**2 + 8.76e-9 * dT**3  # Datchi HPR 2007
    lcorr = l - dlcorr
    # there is a *10 error in eq. 1 of the paper 
    P = ( 2.74 *  l0 / 7.665 ) * ((lcorr/l0)**7.665 - 1)
    return P

# W.B. Holzapfel, High Press. Res. 25 87 (2005)
def PrubyHolzapfel2005(l, T, l0, T0):
    dT = T - T0
    A = 1845 # GPa
    B = 14.7
    C = 7.5
    dlcorr = 0.00746 * dT - 3.01e-6 * dT**2 + 8.76e-9 * dT**3  # Datchi HPR 2007
    lcorr = l - dlcorr
    P = (A/(B+C)) * ( np.exp( ((B+C)/C)*(1-(l0/lcorr)**C) ) - 1 ) 
    return P

# I. Dorogokupets and A.R. Oganov, Phys. Rev. B 75 024115 (2007)
def PrubyDO2007(l, T, l0, T0):
    dT = T - T0
    dlcorr = 0.00746 * dT - 3.01e-6 * dT**2 + 8.76e-9 * dT**3  # Datchi HPR 2007
    dl = (l - dlcorr) - l0
    P = 1884 * (dl/l0) * (1 + 5.5 *(dl/l0))
    return P

#  F. Datchi, High Pressure Research, 27:4, 447-463, DOI: 10.1080/08957950701659593 
def PsamDatchi1997(l, T, l0, T0):
    dT = T - T0
    #dlcorr = -8.7e-5 * dT + 4.62e-6 * dT**2 -2.38e-9 * dT**3    # Datchi HPR 2007 : error here.
    if T >= 500:
        dlcorr = 1.06e-4 * (T-500) + 1.5e-7 * (T-500)**2    #   J. Appl. Phys. 81, 3333 (1997); doi: 10.1063/1.365025 
    else:
        dlcorr = 0
    #dlcorr=0
    dl = (l-dlcorr) - l0
    P = 4.032 * dl * (1 + 9.29e-3 * dl) / (1 + 2.32e-2 * dl)
    return P

# Rashchenko et al. JOURNAL OF APPLIED PHYSICS 117, 145902 (2015)
def PsamRashchenko2015(l, T, l0, T0):
    dl = l - l0
    P = 4.20 * dl * (1 + 0.020 * dl) / (1 + 0.036 * dl)
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


def PHilberer2026(nu, T, nu0, T0):
    K0  = 576.521119539528 # GPa
    K0p = 3.2571168198326683
    dnu = nu - nu0 
    p = K0 * (dnu/nu0) * (1 + 0.5 * (K0p -1)*dnu/nu0)
    return p

# Homemade:
def H2_Vibron(nu, T, nu0, T0):
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
                                 T0default = 298,
                                 xstep = .01,
                                 color = 'firebrick',
                                 default_fit_model='Double Voigt')

RubyMao1986 = HPCalibration(name = 'Ruby Mao 1986',
                                 func = PrubyMao1986,
                                 Tcor_name='Datchi 2007',
                                 xname = 'lambda',
                                 xunit = 'nm',
                                 x0default = 694.28,
                                 T0default = 298,
                                 xstep = .01,
                                 color = 'crimson',
                                 default_fit_model='Double Voigt')

RubyMao1986_DatchiF = HPCalibration(name = 'Ruby Mao 1986 (Datchi form)',
                                    func = PrubyMao1986_DatchiF,
                                    Tcor_name='Datchi 2007',
                                    xname = 'lambda',
                                    xunit = 'nm',
                                    x0default = 694.28,
                                    T0default = 298,
                                    xstep = .01,
                                    color = 'deeppink',
                                    default_fit_model='Double Voigt')

RubyHolzapfel2005 = HPCalibration(name = 'Ruby Holzapfel 2005',
                                  func = PrubyHolzapfel2005,
                                  Tcor_name='Datchi 2007',
                                  xname = 'lambda',
                                  xunit = 'nm',
                                  x0default = 694.28,
                                  T0default = 298,
                                  xstep = .01,
                                  color = 'tomato',
                                  default_fit_model='Double Voigt')

RubyDO2007 = HPCalibration(name = 'Ruby Dorogokupets-Oganov 2007',
                                  func = PrubyDO2007,
                                  Tcor_name='Datchi 2007',
                                  xname = 'lambda',
                                  xunit = 'nm',
                                  x0default = 694.28,
                                  T0default = 298,
                                  xstep = .01,
                                  color = 'orangered',
                                  default_fit_model='Double Voigt')

SamariumDatchi = HPCalibration(name = 'Samarium SrB4O7 Datchi 1997',
                                       func = PsamDatchi1997,
                                       Tcor_name='Datchi J.Appl.Phys. 1997',
                                       xname = 'lambda',
                                       xunit = 'nm',
                                       x0default = 685.41,
                                       T0default = 298,
                                       xstep = .01,
                                       color = 'mediumseagreen',
                                       default_fit_model='Single Voigt')

SamRashchenko2015 = HPCalibration(name = 'Samarium SrB4O7 Rashchenko 2015',
                                  func = PsamRashchenko2015,
                                  Tcor_name='NA',
                                  xname = 'lambda',
                                  xunit = 'nm',
                                  x0default = 685.51,
                                  T0default = 298,
                                  xstep = .01,
                                  color = 'springgreen',
                                  default_fit_model='Single Voigt')

Hilberer2026 = HPCalibration(name = 'Diamond Raman Edge Hilberer 2026',
                                    func = PHilberer2026,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1334,
                                    T0default = 298,
                                    xstep = .1,
                                    color = 'deepskyblue',
                                    default_fit_model='Raman Edge')

Akahama2006 = HPCalibration(name = 'Diamond Raman Edge Akahama 2006',
                                    func = PAkahama2006,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1334,
                                    T0default = 298,
                                    xstep = .1,
                                    color = 'royalblue',
                                    default_fit_model='Raman Edge')

Eremets2023 = HPCalibration(name = 'Diamond Raman Edge Eremets 2023',
                                    func = PEremets2023,
                                    Tcor_name='NA',
                                    xname = 'nu',
                                    xunit = 'cm-1',
                                    x0default = 1332.5,
                                    T0default = 298,
                                    xstep = .1,
                                    color = 'steelblue',
                                    default_fit_model='Raman Edge')
        
cBNDatchi = HPCalibration(name = 'cBN Raman Datchi 2007',
                                  func = PcBN,
                                  Tcor_name='Datchi 2007',
                                  xname = 'nu',
                                  xunit = 'cm-1',
                                  x0default = 1054,
                                  T0default = 298,
                                  xstep = .1,
                                  color = 'violet',
                                  default_fit_model='Single Voigt')

H2Vibron = HPCalibration(name = 'H2 Vibron <30GPa',
                                  func = H2_Vibron,
                                  Tcor_name='NA',
                                  xname = 'nu',
                                  xunit = 'cm-1',
                                  x0default = -1,
                                  T0default = 298,
                                  xstep = .1,
                                  color = 'tan',
                                  default_fit_model='Single Voigt')


calib_list = [Ruby2020, 
              RubyMao1986,
              RubyMao1986_DatchiF,
              RubyHolzapfel2005,
              RubyDO2007,
              SamariumDatchi,
              SamRashchenko2015,
              Hilberer2026,
              Eremets2023,
              Akahama2006,
              H2Vibron,
              cBNDatchi,
                      ]


if __name__ == '__main__': 
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(2, figsize=(7,9), sharex=True)
    ax[0].set_xlabel('wavelength (nm)')
    ax[0].set_ylabel('P (GPa)')

    ax[1].set_xlabel('wavelength (nm)')
    ax[1].set_ylabel('P - Pruby2020 (GPa)')

    ll = np.linspace(694.28, 720, 100)
    l0 = 694.28

    T1 = 298
    T0 = 298

    ruby2020 = Pruby2020(ll, T1, l0, T0)

    ax[0].plot(ll, ruby2020, c='k', label='ruby 2020')
    ax[0].plot(ll, PrubyMao1986(ll, T1, l0, T0), c='r', label='Mao 1986')
    ax[0].plot(ll, PrubyMao1986_DatchiF(ll, T1, l0, T0), c='pink', linestyle='dashed', label='Mao 1986 Datchi Form')
    ax[0].plot(ll, PrubyHolzapfel2005(ll, T1, l0, T0), c='green', label='Holzapfel 2005')
    ax[0].plot(ll, PrubyDO2007(ll, T1, l0, T0), c='gold', label='Dorogokupets-Oganov 2005')


    # differences
    ax[1].plot(ll, ruby2020-ruby2020, c='k')
    ax[1].plot(ll, PrubyMao1986(ll, T1, l0, T0) - ruby2020, c='r')
    ax[1].plot(ll, PrubyMao1986_DatchiF(ll, T1, l0, T0) - ruby2020, c='pink', linestyle='dashed')
    ax[1].plot(ll, PrubyHolzapfel2005(ll, T1, l0, T0) - ruby2020, c='green')
    ax[1].plot(ll, PrubyDO2007(ll, T1, l0, T0) - ruby2020, c='gold')



    ax[0].legend()

    plt.show()

    fig, ax = plt.subplots()
    ax.set_title('Samarium Borate')
    ax.set_xlabel('wavelength (nm)')
    ax.set_ylabel('P (GPa)')

    ll = np.linspace(685.41, 700, 100)
    l0 = 685.41

    T1 = 298
    T0 = 298



    ax.plot(ll, PsamDatchi1997(ll, T1, l0, T0), c='k', label='Datchi 1997')
    ax.plot(ll, PsamRashchenko2015(ll, T1, l0, T0), c='r', label='Rashchenko 2015')


    ax.legend()

    plt.show()
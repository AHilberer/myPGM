import helpers
import numpy as np

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
#    dlcorr = -8.7e-5 * dT + 4.62e-6 * dT**2 -2.38e-9 * dT**3    # problem here !? (Datchi HPR 2007)
#    if T >= 500:
#        dlcorr = 1.06e-4 * (T-500) + 1.5e-7 * (T-500)**2    # these Queyroux p. 68
#    else:
#        dlcorr = 0
    dlcorr=0
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

def H2_Vibron(nu, T=0, nu0=0, T0=0):
	poly = 1.113520628648027e-08*nu**5-0.0002337933432834734*nu**4+1.963452944114722*nu**3-8244.669967044751*nu**2+17309734.53397923*nu-14536565712.17933
	return poly


Ruby2020 = helpers.HPCalibration(name = 'Ruby2020',
							     func = Pruby2020,
							     Tcor_name='Datchi 2007',
							     xname = 'lambda',
							     xunit = 'nm',
							     x0default = 694.28,
							     xstep = .01,
							     color = 'lightcoral')
        
SamariumDatchi = helpers.HPCalibration(name = 'Samarium Borate Datchi 1997',
							     	   func = PsamDatchi1997,
							     	   Tcor_name='NA',
							     	   xname = 'lambda',
							     	   xunit = 'nm',
							     	   x0default = 685.41,
							     	   xstep = .01,
							     	   color = 'moccasin')
        
Akahama2006 = helpers.HPCalibration(name = 'Diamond Raman Edge Akahama 2006',
							     	func = PAkahama2006,
							     	Tcor_name='NA',
							     	xname = 'nu',
							     	xunit = 'cm-1',
							     	x0default = 1333,
							     	xstep = .1,
							     	color = 'darkgrey')
        
cBNDatchi = helpers.HPCalibration(name = 'cBN Raman Datchi 2007',
							      func = PcBN,
							      Tcor_name='Datchi 2007',
							      xname = 'nu',
							      xunit = 'cm-1',
							      x0default = 1054,
							      xstep = .1,
							      color = 'lightblue')

H2Vibron = helpers.HPCalibration(name = 'H2 Vibron <30GPa',
							      func = H2_Vibron,
							      Tcor_name='NA',
							      xname = 'nu',
							      xunit = 'cm-1',
							      x0default = 4200,
							      xstep = .1,
							      color = 'royalblue')


calib_list = [Ruby2020, 
                      SamariumDatchi, 
                      Akahama2006, 
                      cBNDatchi,
					  H2Vibron]


if __name__ == '__main__': 
	import matplotlib.pyplot as plt
	import numpy as np

	print(H2Vibron)
	x = np.linspace(4000, 4260, 100)
	y = H2_Vibron(x, 0, 4150, 0)

	print( H2Vibron.invfunc(10) )

	plt.plot(y,x)
	plt.show()
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


if __name__ == '__main__':
	pass
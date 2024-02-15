import helpers
import calibfuncs
Ruby2020 = helpers.HPCalibration(name = 'Ruby2020',
							     func = calibfuncs.Pruby2020,
							     Tcor_name='Datchi 2007',
							     xname = 'lambda',
							     xunit = 'nm',
							     x0default = 694.28,
							     xstep = .01,
							     color = 'lightcoral')
        
SamariumDatchi = helpers.HPCalibration(name = 'Samarium Borate Datchi 1997',
							     	   func = calibfuncs.PsamDatchi1997,
							     	   Tcor_name='NA',
							     	   xname = 'lambda',
							     	   xunit = 'nm',
							     	   x0default = 685.41,
							     	   xstep = .01,
							     	   color = 'moccasin')
        
Akahama2006 = helpers.HPCalibration(name = 'Diamond Raman Edge Akahama 2006',
							     	func = calibfuncs.PAkahama2006,
							     	Tcor_name='NA',
							     	xname = 'nu',
							     	xunit = 'cm-1',
							     	x0default = 1333,
							     	xstep = .1,
							     	color = 'darkgrey')
        
cBNDatchi = helpers.HPCalibration(name = 'cBN Raman Datchi 2007',
							      func = calibfuncs.PcBN,
							      Tcor_name='Datchi 2007',
							      xname = 'nu',
							      xunit = 'cm-1',
							      x0default = 1054,
							      xstep = .1,
							      color = 'lightblue')
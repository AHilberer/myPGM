import numpy as np
import pandas as pd
from copy import deepcopy
from scipy.optimize import minimize
from PyQt5.QtCore import QObject, pyqtSignal

import Calibfuncs

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
									x0=self.x0default, tol=1e-6)
		return res.x[0]
	


class HPData():

	def __init__(self, Pm, P, x, T, x0, T0, calib, file):
		super().__init__()

		self.Pm = Pm
		self.P = P
		self.x = x
		self.T = T
		self.x0 = x0
		self.T0 = T0
		self.calib = calib
		self.file = file

	def __repr__(self):
		return str(self.df)

	def calcP(self):
		self.P = self.calib.func(self.x, self.T, self.x0, self.T0)

	def invcalcP(self):
		self.x = self.calib.invfunc(self.P, self.T, self.x0, self.T0)

	# SOMETHING TO RETRIEVE THE CALIB OBJECT BY ITS NAME ?

	@property
	def df(self):		
		_df = pd.DataFrame({'Pm': self.Pm,
							'P' : self.P, 
							'x' : self.x,
							'T' : self.T,
							'x0': self.x0,
							'T0': self.T0,
							'calib': self.calib.name,
							'file' : self.file}, index=[0])
		return _df



class HPDataTable(QObject):
	
	changed = pyqtSignal()

	def __init__(self, df=None, calibrations=None):
		super().__init__()	
	
		self.datalist = []

		if df is not None:
			self.reconstruct_from_df(df, calibrations)

	def __repr__(self):
		return str( self.df )

	def __getitem__(self, index):
		return self.datalist[index]

	def __setitem__(self, index, HPDataobj):
		self.datalist[index] = HPDataobj
		self.changed.emit()

	def __len__(self):
		return len(self.datalist)


	def recalc_item_P(self, index):
		# method implemented to emit change!
		self.datalist[index].calcP()
		self.changed.emit()

	def reinvcalc_item_P(self, index):
		self.datalist[index].invcalcP()
		self.changed.emit()

	def setitemval(self, item, attr, val):
		if val != getattr(self.datalist[item],attr): 
			setattr(self.datalist[item], attr, val)
			self.changed.emit()

	def add(self, buffer):
		# NB:  deepcopy fails if HPData inherits from QObject !
		# deepcopy absolutely necessary here
		# Here I work with the HPData object
		self.datalist.append( deepcopy(buffer) )
		self.changed.emit()

	def removelast(self):
		# Here I work with the HPData object
		self.datalist = self.datalist[:-1]
		self.changed.emit()

	def removespecific(self, index):
		del self.datalist[index]
		self.changed.emit()

	def reconstruct_from_df(self, df, calibrations):
		# erases the previous content!
		self.datalist = []
		for _, row in df.iterrows():
			HPdi = HPData(Pm = row['Pm'],
						  P  = row['P'], 
						  x  = row['x'], 
						  T  = row['T'], 
						  x0 = row['x0'], 
						  T0 = row['T0'],
						  calib = calibrations[row['calib']], # retrieve calib
						  file = row['file'])
			self.datalist.append(HPdi)
		self.changed.emit()

	@property
	def df(self):
		# should be used only as a REPRESENTATION of HPDataTable
		_df = pd.DataFrame(columns=['Pm','P','x','T','x0','T0','calib','file'])
		for xi in self.datalist:
			_df = pd.concat([_df, xi.df ], ignore_index=True)
		return _df
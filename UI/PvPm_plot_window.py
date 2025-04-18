import matplotlib.pyplot as plt
import pyqtgraph as pg

from PyQt5.QtWidgets import (QMainWindow,)

class PmPPlotWindow(QMainWindow):
	def __init__(self, HPDataTable_, calibrations_):
		super().__init__()
		
		self.setWindowTitle("PvPm Plot")
		self.setGeometry(1000, 550, 450, 350)

		self.plot_graph = pg.PlotWidget()
		self.setCentralWidget(self.plot_graph)
		self.pens = {}
		#self.plot_graph.setTitle("Temperature vs Time", color="b", size="20pt")
		self.plot_graph.setBackground("white")
		styles = {"color": "black", "font-size": "16px"}
		self.plot_graph.setLabel("left", "P (GPa)", **styles)
		self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
		self.plot_graph.addLegend()
		self.plot_graph.showGrid(x=True, y=True)

		self.data = HPDataTable_
		self.calibrations = calibrations_
		self.lines = {}

		self.updateplot()

	def updateplot(self): 
		gr = self.data.df.groupby('calib')
		groups = gr.groups.keys()
		
		for g in groups:
			subdf = gr.get_group(g)
			if g in list(self.lines.keys()):
				self.lines[g].setData(list(subdf['Pm']), list(subdf['P']))
				
			else :
				self.pens[g] = pg.mkPen(color=self.calibrations[g].color)
				self.lines[g] = self.plot_graph.plot(
					list(subdf['Pm']),
					list(subdf['P']),
					name=g,
					pen=self.pens[g],
					symbol="o",
					symbolSize=8,
					symbolBrush=self.calibrations[g].color,)


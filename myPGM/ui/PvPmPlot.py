import pyqtgraph as pg

from PyQt5.QtWidgets import (QMainWindow,)

class PvPmPlotWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.data_manager = None
		
		self.setWindowTitle("PvPm Plot")
		self.setGeometry(1000, 550, 450, 350)

		self.plot_graph = pg.PlotWidget()
		self.setCentralWidget(self.plot_graph)
		self.pens = {}
		self.calib_colors = None
		#self.plot_graph.setTitle("Temperature vs Time", color="b", size="20pt")
		self.plot_graph.setBackground("white")
		styles = {"color": "black", "font-size": "16px"}
		self.plot_graph.setLabel("left", "P (GPa)", **styles)
		self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
		self.plot_graph.addLegend()
		self.plot_graph.showGrid(x=True, y=True)

		# self.data = HPDataTable_
		# self.calibrations = calibrations_
		self.lines = {}

		self.updateplot()

	def set_data_manager(self, data_manager):
		self.data_manager = data_manager


	def set_dark_mode(self):
		styles = {"color": 'white', "font-size": "16px"}
		self.plot_graph.setBackground("#202020")
		self.plot_graph.setLabel("left", "P (GPa)", **styles)
		self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
   

	def set_light_mode(self):
		styles = {"color": 'black', "font-size": "16px"}
		self.plot_graph.setBackground("white")
		self.plot_graph.setLabel("left", "P (GPa)", **styles)
		self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)

	def updateplot(self, incoming_data=None): 
		if incoming_data is None:
			if self.data_manager is None:
				return
			incoming_data = []
			for obj in self.data_manager.values():
				if not getattr(obj, "include_in_table", False):
					continue
				if obj.Pm is None or obj.P is None:
					continue
				incoming_data.append(
					{
						"Pm": float(obj.Pm),
						"P": float(obj.P),
						"calib": obj.calib.name if obj.calib is not None else "unknown",
					}
				)
		
		# Group data by 'calib' key
		groups = {}
		for item in incoming_data:
			calib = item.get('calib')
			if calib not in groups:
				groups[calib] = []
			groups[calib].append(item)
		
		active_groups = set(groups.keys())
		for stale_group in list(self.lines.keys()):
			if stale_group not in active_groups:
				self.plot_graph.removeItem(self.lines[stale_group])
				del self.lines[stale_group]
				self.pens.pop(stale_group, None)

		for g, subdata in groups.items():
			pm_values = [float(item['Pm']) for item in subdata]
			p_values = [float(item['P']) for item in subdata]
			#print(f"Group: {g}, Pm: {pm_values}, P: {p_values}")

			if g in list(self.lines.keys()):
				self.lines[g].setData(pm_values, p_values)
			else:
				if self.calib_colors is None:
					color = pg.intColor(len(self.lines))
				else:
					color = self.calib_colors.get(g, pg.intColor(len(self.lines)))

				self.pens[g] = pg.mkPen(color=color)
				self.lines[g] = self.plot_graph.plot(
					pm_values,
					p_values,
					name=g,
					pen=self.pens[g],
					symbol="o",
					symbolSize=8,
					symbolBrush=color)


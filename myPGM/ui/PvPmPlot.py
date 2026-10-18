import numpy as np
import pyqtgraph as pg

from PyQt5.QtGui import QFont

from PyQt5.QtWidgets import (QMainWindow,
							 QWidget,
							 QVBoxLayout,
							 QCheckBox,)

class PvPmPlotWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.data_manager = None
		
		self.setWindowTitle("PvPm Plot")
		self.resize(700, 500)   # placed by MainWindow._arrange_windows

		self.plot_graph = pg.PlotWidget()
		self.lines_checkbox = QCheckBox('Display lines')
		self.lines_checkbox.setChecked(True)

		central_widget = QWidget()
		layout = QVBoxLayout(central_widget)
		layout.addWidget(self.plot_graph)
		layout.addWidget(self.lines_checkbox)

		self.setCentralWidget(central_widget)
		self.pens = {}
		self.calib_colors = None
		self.font_px = 18
		self.label_color = "black"
		self.plot_graph.setBackground("white")
		self._update_labels()
		self.legend = self.plot_graph.addLegend()
		self.plot_graph.showGrid(x=True, y=True)

		self.lines = {}
		self.error_bars = {}
		
		self.lines_checkbox.toggled.connect(self.toggle_lines)

		self.updateplot()

	def set_data_manager(self, data_manager):
		self.data_manager = data_manager

	def set_dark_mode(self):
		self.label_color = "white"
		self.plot_graph.setBackground("#202020")
		self._update_labels()

	def set_light_mode(self):
		self.label_color = "black"
		self.plot_graph.setBackground("white")
		self._update_labels()

	def set_font_size(self, size):
		self.font_px = size
		self._update_labels()
		self._update_legend_font()

	def _update_labels(self):
		styles = {"color": self.label_color, "font-size": f"{self.font_px}px"}
		self.plot_graph.setLabel("left", "P (GPa)", **styles)
		self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
		tick_font = QFont()
		tick_font.setPixelSize(self.font_px)
		for side in ("left", "bottom"):
			self.plot_graph.getAxis(side).setStyle(tickFont=tick_font)

	def _update_legend_font(self):
		for sample, label in self.legend.items:
			label.setText(label.text, size=f"{self.font_px}px")

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
						"P_err": getattr(obj, "P_err", None),
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
				if stale_group in self.error_bars:
					self.plot_graph.removeItem(self.error_bars.pop(stale_group))

		for g, subdata in groups.items():
			pm_values = [float(item['Pm']) for item in subdata]
			p_values = [float(item['P']) for item in subdata]

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
					symbolSize=14,
					symbolBrush=color)

			self._update_error_bars(g, subdata)

		self._update_legend_font()

	def _update_error_bars(self, group, subdata):
		# statistical fit uncertainty on P (0 for points without one, e.g. Raman edge)
		pm = np.array([float(item["Pm"]) for item in subdata])
		p = np.array([float(item["P"]) for item in subdata])
		err = np.array([item.get("P_err") or 0.0 for item in subdata], dtype=float)
		if group not in self.error_bars:
			# not given a name, so it stays out of the legend
			self.error_bars[group] = pg.ErrorBarItem(beam=0, pen=self.pens[group])
			self.plot_graph.addItem(self.error_bars[group])
		self.error_bars[group].setData(x=pm, y=p, top=err, bottom=err)

	def toggle_lines(self, checked):
	    for g in self.lines:
	        if checked:
	            self.lines[g].setPen(self.pens[g])
	        else:
	            self.lines[g].setPen(None)
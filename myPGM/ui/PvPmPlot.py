import numpy as np
import pyqtgraph as pg

from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QVBoxLayout,
                             QAction,)

from myPGM.ui import theme

LINE_OPACITY = 0.6      # line joining the points, DESIGN.md §6

class PvPmPlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data_manager = None
        
        self.setWindowTitle("PvPm Plot")
        self.resize(700, 500)   # placed by MainWindow._arrange_windows

        self.plot_graph = pg.PlotWidget()

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.plot_graph)

        self.setCentralWidget(central_widget)
        self.pens = {}
        self.calibs = {}            # calibration of each series: gives its colour
        self.font_px = 18
        self.legend = self.plot_graph.addLegend()

        self.lines = {}
        self.error_bars = {}
        self._restyle()
        
        # 'Display lines' in the plot's right-click menu
        self.lines_action = QAction('Display lines', self)
        self.lines_action.setCheckable(True)
        self.lines_action.setChecked(True)
        self.lines_action.toggled.connect(self.toggle_lines)
        menu = self.plot_graph.plotItem.vb.menu
        menu.addSeparator()
        menu.addAction(self.lines_action)

        self.updateplot()

    def set_data_manager(self, data_manager):
        self.data_manager = data_manager

    def set_dark_mode(self):
        self._restyle()

    def set_light_mode(self):
        self._restyle()

    def _restyle(self):
        """Colours of the current theme (theme.tokens()): plot, axes, legend and
        the series, drawn in their calibration's colour."""
        t = theme.tokens()
        self.label_color = t["mu"]
        theme.style_axes(self.plot_graph, t)
        self.legend.setLabelTextColor(theme.qcolor(t["tx"]))
        self._update_labels()
        for group in self.lines:
            self._style_series(group)
        self._update_legend_font()

    def _series_color(self, group):
        return theme.qcolor(theme.calib_color(self.calibs.get(group)))

    def _style_series(self, group):
        color = self._series_color(group)
        line_color = theme.qcolor(color.name())
        line_color.setAlphaF(LINE_OPACITY)
        self.pens[group] = pg.mkPen(color=line_color, width=1.5)
        line = self.lines[group]
        line.setPen(self.pens[group] if self.lines_action.isChecked() else None)
        line.setSymbolBrush(pg.mkBrush(color))
        line.setSymbolPen(None)
        line.setSymbolSize(10)
        if group in self.error_bars:
            self.error_bars[group].setData(pen=pg.mkPen(color=line_color, width=1))

    def set_font_size(self, size):
        self.font_px = size
        self._update_labels()
        self._update_legend_font()

    def _update_labels(self):
        styles = theme.label_styles(self.label_color, self.font_px)
        self.plot_graph.setLabel("left", "P (GPa)", **styles)
        self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
        tick_font = theme.mono_font(self.font_px)
        for side in ("left", "bottom"):
            self.plot_graph.getAxis(side).setStyle(tickFont=tick_font)

    def _update_legend_font(self):
        for sample, label in self.legend.items:
            label.setText(label.text, size=f"{self.font_px}px")

    def updateplot(self):
        if self.data_manager is None:
            return
        incoming_data = []
        # same order as the table '#': points are joined in the order they were added
        for obj in self.data_manager.table_entries():
            if obj.Pm is None or obj.P is None:
                continue
            incoming_data.append(
                {
                    "Pm": float(obj.Pm),
                    "P": float(obj.P),
                    "P_err": getattr(obj, "P_err", None),
                    "calib": obj.calib.name if obj.calib is not None else "unknown",
                    "calib_obj": obj.calib,
                    "label": obj.calib.short_name if obj.calib is not None else "unknown",
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
                self.calibs.pop(stale_group, None)
                if stale_group in self.error_bars:
                    self.plot_graph.removeItem(self.error_bars.pop(stale_group))

        for g, subdata in groups.items():
            pm_values = [float(item['Pm']) for item in subdata]
            p_values = [float(item['P']) for item in subdata]

            if g in list(self.lines.keys()):
                self.lines[g].setData(pm_values, p_values)
            else:
                self.calibs[g] = subdata[0]["calib_obj"]
                self.lines[g] = self.plot_graph.plot(
                    pm_values,
                    p_values,
                    name=subdata[0].get("label", g),   # short name, as in the table
                    symbol="o")
                # pen (none while lines are hidden), markers in the calibration colour
                self._style_series(g)

            self._update_error_bars(g, subdata)

        self._update_legend_font()

    def _update_error_bars(self, group, subdata):
        # statistical fit uncertainty on P (0 for points without one, e.g. Raman edge)
        pm = np.array([float(item["Pm"]) for item in subdata])
        p = np.array([float(item["P"]) for item in subdata])
        err = np.array([item.get("P_err") or 0.0 for item in subdata], dtype=float)
        if group not in self.error_bars:
            # not given a name, so it stays out of the legend
            self.error_bars[group] = pg.ErrorBarItem(beam=0, pen=pg.mkPen(self.pens[group].color(), width=1))
            self.plot_graph.addItem(self.error_bars[group])
        self.error_bars[group].setData(x=pm, y=p, top=err, bottom=err)

    def toggle_lines(self, checked):
        for g in self.lines:
            if checked:
                self.lines[g].setPen(self.pens[g])
            else:
                self.lines[g].setPen(None)
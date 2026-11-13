import numpy as np
import pyqtgraph as pg

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtWidgets import (QAction,
                             QLabel,
                             QVBoxLayout,
                             QWidget,)

from myPGM.ui import theme

LINE_OPACITY = 0.6      # line joining the points, DESIGN.md §6

class PvPmPlotWindow(QWidget):
    """P vs Pm plot, shown in the bottom dock. Its legend (a dot per calibration) is
    `legend_label`, placed in the dock header (DESIGN.md §1)."""

    def __init__(self):
        super().__init__()
        self.data_manager = None

        self.setWindowTitle("P vs Pm")

        self.plot_graph = pg.PlotWidget()
        # room around the points: the highest one sat on the top edge of the card
        self.plot_graph.getViewBox().setDefaultPadding(0.08)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_graph)

        self.pens = {}
        self.calibs = {}            # calibration of each series: gives its colour
        self.labels = {}            # legend text of each series (calibration short name)
        self.font_px = 18
        self.legend_label = QLabel()
        self.legend_label.setObjectName("PlotLegend")

        self.lines = {}
        self.error_bars = {}

        # the point of the spectrum shown gets a ring (DESIGN.md §1)
        self.current_id = None
        self.current_ring = pg.ScatterPlotItem(symbol="o", size=20, brush=None)
        self.current_ring.setZValue(10)
        self.plot_graph.addItem(self.current_ring, ignoreBounds=True)

        # no point yet: a centred line instead of an empty plot (DESIGN.md §4b)
        self.empty_label = QLabel("Logged points appear here, P against Pm.", self.plot_graph)
        self.empty_label.setObjectName("EmptyHint")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.plot_graph.installEventFilter(self)
        self._restyle()
        self._set_empty(True)
        
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

    def eventFilter(self, watched, event):
        if watched is self.plot_graph and event.type() == QEvent.Resize:
            self.empty_label.setGeometry(self.plot_graph.rect().adjusted(16, 0, -16, 0))
        return super().eventFilter(watched, event)

    def set_current_id(self, obj_id):
        self.current_id = obj_id
        self._update_ring()

    def _update_ring(self):
        obj = None
        if self.data_manager is not None and self.current_id is not None:
            obj = next((o for o in self.data_manager.table_entries()
                        if o.id == self.current_id and o.Pm is not None and o.P is not None),
                       None)
        if obj is None:
            self.current_ring.setData([], [])
            return
        self.current_ring.setData([float(obj.Pm)], [float(obj.P)])
        self.current_ring.setPen(pg.mkPen(theme.qcolor(theme.calib_color(obj.calib)), width=1.5))

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
        self._update_labels()
        for group in self.lines:
            self._style_series(group)
        self._update_legend()
        self._update_ring()

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

    def _update_labels(self):
        styles = theme.label_styles(self.label_color, self.font_px)
        self.plot_graph.setLabel("left", "P (GPa)", **styles)
        self.plot_graph.setLabel("bottom", "Pm (bar)", **styles)
        tick_font = theme.mono_font(self.font_px)
        for side in ("left", "bottom"):
            self.plot_graph.getAxis(side).setStyle(tickFont=tick_font)
        if getattr(self, "empty", False):
            self._set_empty(True)       # PlotItem.setLabel shows the axes again

    def legend_entries(self):
        """(text, colour) of each series, in the order they were first plotted."""
        return [(self.labels[group], self._series_color(group).name()) for group in self.lines]

    def _update_legend(self):
        self.legend_label.setText("&nbsp;&nbsp;&nbsp;".join(
            f'<span style="color:{color}">●</span>&nbsp;{text}'
            for text, color in self.legend_entries()))

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
                self.labels.pop(stale_group, None)
                if stale_group in self.error_bars:
                    self.plot_graph.removeItem(self.error_bars.pop(stale_group))

        for g, subdata in groups.items():
            pm_values = [float(item['Pm']) for item in subdata]
            p_values = [float(item['P']) for item in subdata]

            if g in list(self.lines.keys()):
                self.lines[g].setData(pm_values, p_values)
            else:
                self.calibs[g] = subdata[0]["calib_obj"]
                self.labels[g] = subdata[0].get("label", g)   # short name, as in the table
                self.lines[g] = self.plot_graph.plot(pm_values, p_values, symbol="o")
                # pen (none while lines are hidden), markers in the calibration colour
                self._style_series(g)

            self._update_error_bars(g, subdata)

        self._update_legend()
        self._update_ring()
        self._set_empty(not incoming_data)

    def _set_empty(self, empty):
        """No point: the message instead of the axes, no legend."""
        self.empty = empty
        self.empty_label.setVisible(empty)
        self.legend_label.setVisible(not empty)
        for axis in ("left", "bottom"):
            self.plot_graph.getPlotItem().showAxis(axis, not empty)

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
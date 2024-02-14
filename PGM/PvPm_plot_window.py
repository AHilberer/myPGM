import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QWidget,
                             QVBoxLayout)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar



#? Define PvPm plot class
class PvPmPlotWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PvPm Plot")
        self.setGeometry(900, 550, 450, 350)
        PmP_plot = MplCanvas(self)
        self.axes = PmP_plot.axes
        self.figure = PmP_plot.figure
        self.canvas = FigureCanvas(self.figure)
        self.axes.set_ylabel(r'$P$ (GPa)')
        self.axes.set_xlabel(r"$P_m$ (bar)")
        #self.axes.plot([0,1,2,3,4], [10,1,20,3,40])

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)

#? Define plot canvas class

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = plt.Figure(tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        plt.tight_layout()
        super(MplCanvas, self).__init__(fig)
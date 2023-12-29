import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#? Define plot canvas class

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = plt.Figure(tight_layout=True)
        self.fig = fig
        self.axes = fig.add_subplot(111)
        plt.tight_layout()
        super(MplCanvas, self).__init__(fig)
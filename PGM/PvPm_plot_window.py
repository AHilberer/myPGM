import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QWidget,
                             QVBoxLayout,)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar



#? Define plot canvas class

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = plt.figure(figsize=(width, height), dpi=dpi, constrained_layout=True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class PmPPlotWindow(QWidget):
	def __init__(self, HPDataTable_, calibrations_):
		super().__init__()

		self.setWindowTitle("PvPm Plot")
		self.setGeometry(1000, 550, 450, 350)

		#centerPoint = QDesktopWidget().availableGeometry().center()
		#thePosition = (centerPoint.x() + 300, centerPoint.y() - 400)
		#self.move(*thePosition)

		self.data = HPDataTable_
		self.calibrations = calibrations_

		self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
		self.toolbar = NavigationToolbar(self.canvas, self)		
		layout = QVBoxLayout()

		layout.addWidget(self.toolbar)
		layout.addWidget(self.canvas)

		self.setLayout(layout)

#		self.updateplot()

	def updateplot(self): 

		self.canvas.axes.cla()

		self.canvas.axes.set_xlabel('Pm (bar)')
		self.canvas.axes.set_ylabel('P (GPa)')

		gr = self.data.df.groupby('calib')
		groups = gr.groups.keys()

		for g in groups:
			subdf = gr.get_group(g)
			self.canvas.axes.plot(subdf['Pm'], 
								  subdf['P'], 
								  marker='o',
								  color=self.calibrations[g].color,
								  label=g)
		if len(groups) != 0:
			self.canvas.axes.legend()
		self.canvas.draw()


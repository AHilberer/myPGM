import sys
import os
from PyQt5.QtWidgets import QApplication

from myPGM.helpers import load_style
from myPGM.ui.main_ui import MainWindow
from myPGM.data_model import PressureGaugeDataManager
from myPGM.presenter import Presenter

def main():
#    os.chdir(os.path.abspath(__file__).replace(os.path.basename(__file__), ""))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        style = load_style('light-mode.qss')
        app.setStyleSheet(style)
    except:
        pass
    model = PressureGaugeDataManager()
    view = MainWindow()
    presenter = Presenter(model, view, test_mode=True)
    presenter.view.show()
    #presenter.initialize_example()

    sys.exit(app.exec_())


import sys
import os
from PyQt5.QtWidgets import QApplication
from main_ui import *
from data_model import PressureGaugeDataManager
from presenter import Presenter

# Run the application
if __name__ == "__main__":
    os.chdir(os.path.abspath(__file__).replace(os.path.basename(__file__), ""))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        with open("light-mode.qss", "r") as file:
            qss = file.read()
            app.setStyleSheet(qss)
    except:
        pass
    model = PressureGaugeDataManager()
    view = MainWindow(model)
    presenter = Presenter(model, view)
    presenter.view.show()
    presenter.initialize_example()

    sys.exit(app.exec_())


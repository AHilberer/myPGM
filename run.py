import sys
import os
from PyQt5.QtWidgets import QApplication
from UI.main_ui import MainWindow
from myPGM.data_model import PressureGaugeDataManager
from myPGM.presenter import Presenter

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
    presenter = Presenter(model, view, test_mode=True)
    presenter.view.show()
    #presenter.initialize_example()

    sys.exit(app.exec_())


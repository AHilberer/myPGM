import sys
import os
from PyQt5.QtWidgets import QApplication

from data_model import PressureGaugeDataObject, PressureGaugeDataManager, HPCalibration, GaugeFitModel
import calibrations
import fit_models
from main_ui import *

from FileListViewerWidget import *

class Presenter:
    def __init__(self, model: PressureGaugeDataManager, view: QWidget) -> None:
        self.model = model
        self.view = view
        #self.view.input_data_collected.connect(self.handle_input_data)
        self.example_files = [
                #"Example_diam_Raman.asc",
                "Example_Ruby_1.asc",
                "Example_Ruby_2.asc",
                "Example_Ruby_3.asc",
                #"Example_H2.txt",
            ]

    def initialize_example(self):
        for i, current_file in enumerate(self.example_files):
            current_file_path = os.path.dirname(__file__) + "/resources/" + current_file
            a = PressureGaugeDataObject()
            self.model.add_instance(a)
            a.load_spectral_data_file(current_file, current_file_path)
            a.set_calibration(calibrations.Ruby2020)
            a.set_fit_model(fit_models.DoubleVoigt)
            a.fit_data()
        print([k for k in self.model.values()])
        self.view.list_widget.populate_list()



if __name__ == '__main__':
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



    

 
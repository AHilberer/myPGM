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
        self.current_selected_file = None
        self.example_files = [
                #"Example_diam_Raman.asc",
                "Example_Ruby_1.asc",
                "Example_Ruby_2.asc",
                "Example_Ruby_3.asc",
                #"Example_H2.txt",
            ]
        self.view.file_list_widget.object_selected.connect(self.file_selected_from_file_list)

        self.view.smoothing_factor.valueChanged.connect(self.smoothen)

    def initialize_example(self):
        for i, current_file in enumerate(self.example_files):
            current_file_path = os.path.dirname(__file__) + "/resources/" + current_file
            a = PressureGaugeDataObject()
            self.model.add_instance(a)
            a.load_spectral_data_file(current_file, current_file_path)
            a.set_calibration(calibrations.Ruby2020)
            a.set_fit_model(fit_models.DoubleVoigt)
        
        for a in list(self.model.values())[:-1]:
            a.fit_data()
        print([k for k in self.model.values()])
        self.populate_file_list()

    def file_selected_from_file_list(self, obj_id):
        self.current_selected_file = obj_id
        self.update_data_plots(obj_id)

    
    def update_data_plots(self, obj_id):
        obj = self.model.get(obj_id, None)
        if obj.original_data is not None:
            x, y = obj.get_data_to_process()
            self.view.plot_data(x,y)
            if obj.fit_result is not None:
                self.view.plot_fit(obj.P, obj.fit_model, obj.fit_result, x, y)
            
        else:
            print('No data to be plotted.')

    def smoothen(self, smoothing_factor):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            obj.smoothen(int(smoothing_factor))
            self.update_data_plots(self.current_selected_file)
        else:
            return
    
    def populate_file_list(self):
        self.view.file_list_widget.list_widget.clear()
        for obj in self.model.values():
            if getattr(obj, "include_in_filelist", False):
                text = f"{obj.filename}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, obj.id)  # Store only object ID 
                self.view.file_list_widget.list_widget.addItem(item)

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



    

 
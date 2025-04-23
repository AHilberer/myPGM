import sys
import os
from PyQt5.QtWidgets import QApplication, QListWidgetItem
from PyQt5.QtCore import Qt
from myPGM.data_model import PressureGaugeDataObject, PressureGaugeDataManager
import myPGM.calibrations
import myPGM.fit_models

class Presenter:
    def __init__(self, model, view, test_mode=False):
        self.model = model
        self.view = view
        self.test_mode = test_mode
        self.current_selected_file = None
        self.example_files = [
                "Example_diam_Raman.asc",
                "Example_Ruby_1.asc",
                "Example_Ruby_2.asc",
                "Example_Ruby_3.asc",
                "Example_H2.txt",
            ]

        self.initialize_calibrations_menu()
        self.initialize_fit_models_menu()

        self.view.startup_buffer()
        #self.view.update_fit_model()



        #? Setup Signal-Slot interactions
        self.view.calibration_combo.currentIndexChanged.connect(self.view.update_calib)
        self.view.fit_model_combo.currentIndexChanged.connect(self.view.update_fit_model)

        self.view.file_list_widget.object_selected.connect(self.file_selected_from_file_list)

        self.view.smoothing_factor.valueChanged.connect(self.smoothen)

        self.view.start_auto_fit_signal.connect(self.fit_current_file)
        self.view.fit_from_click_signal.connect(self.fit_current_file)

        self.view.CHullBg_button.clicked.connect(self.subtract_auto_bg)
        self.view.ResetBg_button.clicked.connect(self.reset_bg)


        if self.test_mode:
            self.initialize_example()

    ##################################################################################""
        #? Methods 

    def initialize_calibrations_menu(self):
        self.view.load_calibrations({a.name: a for a in myPGM.calibrations.calib_list})
        self.view.populate_calib_combo()
        self.view.x0_spinbox.setValue(myPGM.calibrations.calib_list[0].x0default)


    def initialize_fit_models_menu(self):
        self.view.load_fit_models({a.name: a for a in myPGM.fit_models.model_list})
        self.view.populate_fit_models_combo()


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
    
    def subtract_auto_bg(self):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            obj.convexhull_bg()
            self.update_data_plots(self.current_selected_file)
        else:
            return

    def reset_bg(self):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            obj.reset_bg()
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


    def fit_current_file(self, guess=None): 
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            obj.set_calibration(self.view.buffer.calib)
            obj.set_fit_model(self.view.fit_mode)
            try:
                obj.fit_data(guess)
                self.view.x_spinbox.setValue(obj.x)
                self.update_data_plots(self.current_selected_file)
            except RuntimeError:
                self.fit_error_popup()


    def fit_error_popup(self):
        self.view.fit_error_popup_window()


    def initialize_example(self):
        for i, current_file in enumerate(self.example_files):
            current_file_path = os.path.dirname(__file__) + "/resources/" + current_file
            a = PressureGaugeDataObject()
            self.model.add_instance(a)
            a.load_spectral_data_file(current_file, current_file_path)
            a.set_calibration(myPGM.calibrations.Ruby2020)
            a.set_fit_model(myPGM.fit_models.DoubleVoigt)
        
        #for a in list(self.model.values())[:-1]:
        #    a.fit_data()
        #print([k for k in self.model.values()])
        self.populate_file_list()

 
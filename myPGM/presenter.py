import sys
import os
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, QFileInfo
from myPGM.data_model import PressureGaugeDataObject
import myPGM.calibrations
import myPGM.fit_models

class Presenter:
    def __init__(self, model, view, test_mode=False):
        self.model = model
        self.view = view
        self.test_mode = test_mode
        self.current_selected_file = None
        self.current_directory = None
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
        self.view.file_list_widget.add_button.clicked.connect(self.add_new_file)
        self.view.file_list_widget.delete_button.clicked.connect(self.delete_current_file)
        self.view.file_list_widget.selectdir_button.clicked.connect(self.set_current_directory)
        self.view.file_list_widget.loadlatest_button.clicked.connect(self.add_latest_file)

        self.view.smoothing_factor.valueChanged.connect(self.smoothen)

        self.view.start_auto_fit_signal.connect(self.fit_current_file)
        self.view.fit_from_click_signal.connect(self.fit_current_file)

        self.view.CHullBg_button.clicked.connect(self.subtract_auto_bg)
        self.view.ResetBg_button.clicked.connect(self.reset_bg)
        self.view.subtract_ManualBg_signal.connect(self.subtract_manual_bg)

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

        
    def add_instance_from_path(self, file_path):
        file_info = QFileInfo(file_path)
        file_name = file_info.fileName()    
        a = PressureGaugeDataObject()
        self.model.add_instance(a)
        a.load_spectral_data_file(file_name, file_path)
                # a.set_calibration(myPGM.calibrations.Ruby2020)
                # a.set_fit_model(myPGM.fit_models.DoubleVoigt)

    def add_new_file(self):
        try:
            selected_files = self.view.get_file_via_dialog()
        except:
            raise RuntimeError("File selection dialog failed.")
        if selected_files is not None:
            for file in selected_files:
                self.add_instance_from_path(file)
            self.populate_file_list()

    def set_current_directory(self):
        self.current_directory = self.view.select_directory_from_dialog()


    def add_latest_file(self):
        if self.current_directory is not None:
            file_names = [
                f
                for f in os.listdir(self.current_directory)
                if os.path.isfile(os.path.join(self.current_directory, f)) and ".asc" in f
            ]
            if file_names:
                file_names.sort(
                    key=lambda f: os.path.getmtime(os.path.join(self.current_directory, f))
                )
                latest_file_name = file_names[-1]
                file = os.path.join(self.current_directory, latest_file_name)
                self.add_instance_from_path(file)
                self.populate_file_list()
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("No files in selected directory.")
                msg.setWindowTitle("Error")
                msg.exec_()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No directory selected.")
            msg.setWindowTitle("Error")
            msg.exec_()



    def delete_current_file(self):
        if self.current_selected_file is not None:
            obj_id = self.current_selected_file
            self.model.delete_instance(obj_id)
            self.current_selected_file = None
            self.populate_file_list()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No file selected to delete.")
            msg.setWindowTitle("Error")
            msg.exec_()


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

    def subtract_manual_bg(self, bg):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            if bg is not None:
                obj.subtract_external_bg(bg)
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

        for obj_id in self.view.ordered_files_to_display:
            try:
                obj = self.model.get(obj_id)
                if not getattr(obj, "include_in_filelist"):
                    self.view.ordered_files_to_display.remove(obj_id)
            except:
                self.view.ordered_files_to_display.remove(obj_id)

        for obj in self.model.values():
            if getattr(obj, "include_in_filelist") and (obj.id not in self.view.ordered_files_to_display):
                self.view.ordered_files_to_display.append(obj.id)

        for obj_id in self.view.ordered_files_to_display:
            obj = self.model.get(obj_id)
            text = f"{obj.filename}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, obj.id)  # Store only object ID 
            self.view.file_list_widget.list_widget.addItem(item)

        # print('actual files', [obj.id for obj in self.model.values()])
        # print('files to display', self.view.ordered_files_to_display)
        

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
            self.add_instance_from_path(current_file_path)
        
        #for a in list(self.model.values())[:-1]:
        #    a.fit_data()
        #print([k for k in self.model.values()])
        self.populate_file_list()

 
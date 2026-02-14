import os
import json
import numpy as np
from copy import deepcopy
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, QFileInfo, QObject
from myPGM.data_model import PressureGaugeDataObject
import myPGM.calibrations
import myPGM.fit_models
from myPGM.helpers import pressure_valid, spectro_calibration_reader

class Presenter(QObject):
    def __init__(self, model, view, test_mode=False):
        super().__init__()
        self.model = model
        self.view = view
        self.test_mode = test_mode
        self.current_selected_file = None
        self.current_directory = None
        self.corrected_spectro_x = None
        self.example_files = [
                "Example_diam_Raman.asc",
                "Example_Ruby_1.asc",
                "Example_Ruby_2.asc",
                "Example_Ruby_3.asc",
                "Example_H2.txt",
            ]
        self.ordered_files_to_display = []
        self.buffer = PressureGaugeDataObject()
        self.additional_buffer = PressureGaugeDataObject()


        self.initialize_calibrations_menu()
        self.view.PvPmPlotWindow.calib_colors = {calib.name: calib.color for calib in myPGM.calibrations.calib_list}
        self.initialize_fit_models_menu()
        self.initialize_buffer()

        #? Setup Signal-Slot interactions
        self.view.fit_model_combo.currentIndexChanged.connect(self.update_fit_model)

        self.view.file_list_widget.object_selected.connect(self.file_selected_from_file_list)
        self.view.file_list_widget.add_button.clicked.connect(self.add_new_file)
        self.view.file_list_widget.delete_button.clicked.connect(self.delete_current_file)
        self.view.file_list_widget.selectdir_button.clicked.connect(self.set_current_directory)
        self.view.file_list_widget.loadlatest_button.clicked.connect(self.add_latest_file)

        self.view.file_list_widget.moveup_button.clicked.connect(self.move_up)
        self.view.file_list_widget.movedown_button.clicked.connect(self.move_down)

        self.view.smoothing_factor.valueChanged.connect(self.smoothen)

        self.view.start_auto_fit_signal.connect(self.fit_current_file)
        self.view.fit_from_click_signal.connect(self.fit_current_file)
        self.view.add_current_fit_signal.connect(self.add_current_fit_to_table)

        self.view.CHullBg_button.clicked.connect(self.subtract_auto_bg)
        self.view.ResetBg_button.clicked.connect(self.reset_bg)
        self.view.subtract_ManualBg_signal.connect(self.subtract_manual_bg)

        self.view.Spectro_use_button.toggled.connect(self.toggle_spectro_calib)
        self.view.LoadSpectro_button.clicked.connect(self.load_spectro_calibration)

        self.view.open_session_signal.connect(self.load_session)
        self.view.save_session_signal.connect(self.save_session)

        self.view.PToolbox_toTable_button.clicked.connect(self.add_current_PToolbox_to_table)

        if self.test_mode:
            self.initialize_example()

    ##################################################################################""
        #? Methods 

    def initialize_calibrations_menu(self):
        calib_dict = {a.name: a for a in myPGM.calibrations.calib_list}
        self.view.ptoolbox.initialize(calib_dict)
        self.view.additional_toolbox_window.initialize(calib_dict)

    def initialize_fit_models_menu(self):
        model_dict = {a.name: a for a in myPGM.fit_models.model_list}
        self.fit_models = model_dict
        self.view.populate_fit_models_combo(model_dict)
        self.fit_mode = model_dict[self.view.fit_model_combo.currentText()]


    def initialize_buffer(self):
        # Default state at opening 
        calib_dict = {a.name: a for a in myPGM.calibrations.calib_list}
        self.buffer.calib = calib_dict["Ruby2020"]
        self.buffer.Pm = 0
        self.buffer.T = 298
        self.buffer.x0 = 694.28
        self.buffer.T0 = 298
        self.buffer.set_x(694.28)

        self.additional_buffer = deepcopy(self.buffer)

        self.view.ptoolbox.set_state_from_buffer(self.buffer)
        self.view.additional_toolbox_window.set_state_from_buffer(self.additional_buffer)
    
        # Connects
        self.view.ptoolbox.calibChanged.connect(self.on_calib_changed)
        self.view.ptoolbox.PmChanged.connect(self.on_Pm_edited)
        self.view.ptoolbox.PChanged.connect(self.on_P_edited)
        self.view.ptoolbox.xChanged.connect(self.on_x_edited)
        self.view.ptoolbox.TChanged.connect(self.on_T_edited)
        self.view.ptoolbox.x0Changed.connect(self.on_x0_edited)
        self.view.ptoolbox.T0Changed.connect(self.on_T0_edited)

        self.view.additional_toolbox_window.calibChanged.connect(self.on_calib_changed)
        self.view.additional_toolbox_window.PmChanged.connect(self.on_Pm_edited)
        self.view.additional_toolbox_window.PChanged.connect(self.on_P_edited)
        self.view.additional_toolbox_window.xChanged.connect(self.on_x_edited)
        self.view.additional_toolbox_window.TChanged.connect(self.on_T_edited)
        self.view.additional_toolbox_window.x0Changed.connect(self.on_x0_edited)
        self.view.additional_toolbox_window.T0Changed.connect(self.on_T0_edited)

    
    def _get_toolbox_context(self, sender=None):
        src = sender or self.sender()
        if src == self.view.additional_toolbox_window:
            return self.view.additional_toolbox_window, self.additional_buffer
        return self.view.ptoolbox, self.buffer

    @pressure_valid
    def on_Pm_edited(self, Pm):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_Pm(Pm)
        toolbox.set_state_from_buffer(buffer)

    @pressure_valid
    def on_P_edited(self, p):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_P(p)
        toolbox.set_state_from_buffer(buffer)
    
    @pressure_valid
    def on_x_edited(self, x):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_x(x)        
        toolbox.set_state_from_buffer(buffer)

    @pressure_valid
    def on_T_edited(self, T):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_T(T)        
        toolbox.set_state_from_buffer(buffer)

    @pressure_valid
    def on_x0_edited(self, x0):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_x0(x0)

        # All those are the same, unique instance:
        #print(buffer.calib is toolbox.calibrations[buffer.calib.name])
        #print(buffer.calib is calib_dict[buffer.calib.name])

        # THE NEW x0 for this gauge is now x0 :
        buffer.calib.x0default = x0

        toolbox.set_state_from_buffer(buffer)

    @pressure_valid
    def on_T0_edited(self, T0):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_T0(T0)  

        # THE NEW T0 for this gauge is now T0 :
        buffer.calib.T0default = T0
        
        toolbox.set_state_from_buffer(buffer)

    @pressure_valid
    def on_calib_changed(self, newcalib):
        toolbox, buffer = self._get_toolbox_context()
        # data model method!
        buffer.set_calibration(newcalib)
        # view method
        toolbox.set_state_from_buffer(buffer)

    def file_selected_from_file_list(self, obj_id):
        self.current_selected_file = obj_id
        self.view.current_file_label.setText(f"{self.model.get(obj_id).filename}")
        if self.view.Spectro_use_button.isChecked():
            try:
                if self.corrected_spectro_x is not None:
                    if self.current_selected_file is not None:
                        obj = self.model.get(self.current_selected_file, None)
                        obj.spectro_recalib(self.corrected_spectro_x)
            except:
                pass
        else:
            if self.current_selected_file is not None:
                obj = self.model.get(self.current_selected_file, None)
                obj.reset_spectro_recalib()
        self.update_data_plots(obj_id)
        
        # toolbox is updated (is it what we want?)
        obj = self.model.get(obj_id, None)
        if obj.fit_result is not None:
            self.buffer = deepcopy(obj)
            self.view.ptoolbox.set_state_from_buffer(self.buffer)

    def add_instance_from_path(self, file_path):
        file_info = QFileInfo(file_path)
        file_name = file_info.fileName()
        a = PressureGaugeDataObject()
        self.model.add_instance(a)
        a.load_spectral_data_file(file_name, file_path)


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

            # on utilise buffer (juste pour afficher les unités des axes dans plot_data)
            self.view.plot_data(x, y, self.buffer)
            if obj.fit_result is not None:
                self.view.plot_fit(obj.P, obj.fit_model, obj.fit_result, x, y)

            if obj.fitting_range is not None:
                self.view.fit_range_selector.setRegion(obj.fitting_range)
            else:
                if not self.view.fit_range_selector_edited:
                    x_range = x[-1]-x[0]
                    x_mean = (x[0]+x[-1])/2
                    self.view.fit_range_selector.setRegion((x_mean - x_range*0.15, x_mean + x_range*0.15))
            

            self.view.fit_range_selector.setBounds((x[0], x[-1]))
            
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


    def load_spectro_calibration(self):
        try:
            selected_file = self.view.get_file_via_dialog()[0]
            file_info = QFileInfo(selected_file)
            file_name = file_info.fileName()
        except:
            raise RuntimeError("File selection dialog failed.")
        if selected_file is not None:
            try:
                self.corrected_spectro_x = spectro_calibration_reader(selected_file)
                self.view.Spectro_filename_label.setText(file_name)
            except:
                RuntimeError("Failed to load spectrometer calibration file.")
            #print(self.corrected_spectro_x)
        return 
    
    def toggle_spectro_calib(self, checked):
        if checked:
            if self.corrected_spectro_x is not None:
                if self.current_selected_file is not None:
                    obj = self.model.get(self.current_selected_file, None)
                    obj.spectro_recalib(self.corrected_spectro_x)
                    self.update_data_plots(self.current_selected_file)
        else:
            if self.current_selected_file is not None:
                obj = self.model.get(self.current_selected_file, None)
                obj.reset_spectro_recalib()
                self.update_data_plots(self.current_selected_file)

    def populate_file_list(self): 
        self.view.file_list_widget.list_widget.clear()

        self.ordered_files_to_display = [
            obj_id
            for obj_id in self.ordered_files_to_display
            if obj_id in self.model
            and getattr(self.model.get(obj_id), "include_in_filelist", False)
        ]

        for obj in self.model.values():
            if getattr(obj, "include_in_filelist", False) and obj.id not in self.ordered_files_to_display:
                self.ordered_files_to_display.append(obj.id)

        for obj_id in self.ordered_files_to_display:
            obj = self.model.get(obj_id)
            text = f"{obj.filename}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, obj.id)  # Store only object ID 
            self.view.file_list_widget.list_widget.addItem(item)

    def select_file_in_list(self, obj_id):
        list_widget = self.view.file_list_widget.list_widget
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == obj_id:
                list_widget.setCurrentItem(item)
                return


    def move_up(self):
        if self.current_selected_file is not None:
            index = self.ordered_files_to_display.index(self.current_selected_file)
            if index > 0:
                # Swap with the previous item
                self.ordered_files_to_display[index], self.ordered_files_to_display[index - 1] = (
                    self.ordered_files_to_display[index - 1],
                    self.ordered_files_to_display[index],
                )
                self.populate_file_list()

    def move_down(self):
        if self.current_selected_file is not None:
            index = self.ordered_files_to_display.index(self.current_selected_file)
            if index < len(self.ordered_files_to_display) - 1:
                # Swap with the next item
                self.ordered_files_to_display[index], self.ordered_files_to_display[index + 1] = (
                    self.ordered_files_to_display[index + 1],
                    self.ordered_files_to_display[index],
                )
                self.populate_file_list()


    def update_fit_model(self, newind):
        self.fit_mode = self.fit_models[self.view.fit_model_combo.currentText()]

        tmp_color = self.view.fit_model_combo.model().item(newind).background().color().getRgb()
        self.view.fit_model_combo.setStyleSheet(
            "background-color: rgba{};\
                    selection-background-color: k;".format(tmp_color)
        )

    def fit_current_file(self, guess=None): 
        if self.current_selected_file is not None:

            obj = self.model.get(self.current_selected_file, None)

            # Set parameters from buffer : 
            obj.set_Pm(self.buffer.Pm)
            obj.set_T(self.buffer.T)
            obj.set_x0(self.buffer.x0)
            obj.set_T0(self.buffer.T0)
            # deepcopy more safe here also:
            obj.set_calibration( deepcopy(self.buffer.calib) )

            obj.set_fit_model(self.fit_mode)

            try:
                if self.view.fit_range_enabled:
                    obj.fitting_range = self.view.fit_range_selector.getRegion()
                obj.fit_data(guess)

                # On récupère obj dans buffer après fit
                # deepcopy, autrement self.buffer est une ref au dernier 
                # obj fité et une modif de self.buffer via la GUI 
                # modifie ce dernier obj !
                # ici self.buffer.calib est également copié (deepcopy) 
                self.buffer = deepcopy(obj)
                # set ptoolbox state:
                self.view.ptoolbox.set_state_from_buffer(self.buffer)
                self.update_data_plots(self.current_selected_file)

            except RuntimeError:
                self.fit_error_popup()

    def fit_error_popup(self):
        self.view.fit_error_popup_window()

    def add_current_fit_to_table(self):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            if obj.fit_result is not None:
                obj.include_in_table = True
                self.update_PvPm_table()
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setText("No fit result to add to table.")
                msg.setWindowTitle("Error")
                msg.exec_()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("No file selected.")
            msg.setWindowTitle("Error")
            msg.exec_()


    def update_PvPm_table(self):
        table_data = []
        self.view.PvPmTableWindow.table_widget.clearContents()
        for obj in self.model.values():
            if getattr(obj, "include_in_table", False):
                table_data.append({
                    "Pm": f"{obj.Pm:.2f}",
                    "P": f"{obj.P:.2f}",
                    "calib": obj.calib.name,
                    "file": obj.filename,
                    "x": f"{obj.x:.3f}",
                    "T": f"{obj.T:.3f}",
                    "x0": f"{obj.x0:.3f}",
                    "T0": f"{obj.T0:.3f}"
                })
        self.view.PvPmTableWindow.table_widget.updatetable(table_data)
        self.view.PvPmPlotWindow.updateplot(table_data)

    def initialize_example(self):
        for i, current_file in enumerate(self.example_files):
            current_file_path = os.path.dirname(__file__) + "/resources/" + current_file
            self.add_instance_from_path(current_file_path)
        

        self.populate_file_list()


    def add_current_PToolbox_to_table(self):
        # create a new object from buffer and add it to the model, then update table and plot
        new_obj = deepcopy(self.buffer)
        new_obj.id = PressureGaugeDataObject.generate_id()
        new_obj.filename = None
        new_obj.full_path = None
        new_obj.include_in_filelist = False
        new_obj.include_in_table = True
        self.model.add_instance(new_obj)
        self.update_PvPm_table()

    def save_session(self):
        file_path = self.view.get_save_session_filename_dialog()
        if not file_path:
            return

        session = {
            "version": 1,
            "ordered_files": self.ordered_files_to_display,
            "current_selected_file": self.current_selected_file,
            "buffer": self.buffer.to_dict(),
            "corrected_spectro_x": self.corrected_spectro_x.tolist()
            if self.corrected_spectro_x is not None
            else None,
            "spectro_use_enabled": self.view.Spectro_use_button.isChecked(),
            "files": [obj.to_dict() for obj in self.model.values()],
        }

        try:
            with open(file_path, "w", encoding="utf-8") as file_handle:
                json.dump(session, file_handle, indent=2)
        except Exception as exc:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"Failed to save session: {exc}")
            msg.setWindowTitle("Save error")
            msg.exec_()

    def load_session(self):
        file_path = self.view.get_open_session_filename_dialog()
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file_handle:
                session = json.load(file_handle)
        except Exception as exc:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText(f"Failed to load session: {exc}")
            msg.setWindowTitle("Load error")
            msg.exec_()
            return

        self.model.clear()
        self.ordered_files_to_display = []
        self.current_selected_file = None
        self.corrected_spectro_x = None

        calib_dict = self.view.ptoolbox.calibrations
        model_dict = self.fit_models

        for payload in session.get("files", []):
            obj = PressureGaugeDataObject.from_dict(payload, calib_dict, model_dict)
            self.model.add_instance(obj)

        self.ordered_files_to_display = session.get(
            "ordered_files",
            [obj.id for obj in self.model.values()],
        )
        self.populate_file_list()

        buffer_payload = session.get("buffer")
        if buffer_payload:
            self.buffer = PressureGaugeDataObject.from_dict(
                buffer_payload, calib_dict, model_dict
            )
            if self.buffer.calib is None and calib_dict:
                self.buffer.calib = list(calib_dict.values())[0]
            self.view.ptoolbox.set_state_from_buffer(self.buffer)

        corrected_spectro_x = session.get("corrected_spectro_x")
        if corrected_spectro_x is not None:
            self.corrected_spectro_x = np.asarray(corrected_spectro_x)

        self.view.Spectro_use_button.setChecked(
            session.get("spectro_use_enabled", False)
        )

        selected_id = session.get("current_selected_file")
        if selected_id in self.model:
            self.current_selected_file = selected_id
            self.select_file_in_list(selected_id)
            self.file_selected_from_file_list(selected_id)

        self.update_PvPm_table()
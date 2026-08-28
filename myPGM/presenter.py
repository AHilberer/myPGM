import os
import json
import numpy as np
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt, QFileInfo, QObject
from myPGM.data_model import PressureGaugeDataObject
import myPGM.calibrations
import myPGM.fit_models
from myPGM.helpers import pressure_valid, spectro_calibration_reader


def get_app_version():
    try:
        return version("myPGM")
    except PackageNotFoundError:
        # Running from source tree without installed package metadata.
        return "dev"

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
        self.app_version = get_app_version()
        self.view.setWindowTitle(f"myPGM - Pressure Gauge Monitor v{self.app_version}")


        self.initialize_calibrations_menu()
        self.view.PvPmPlotWindow.calib_colors = {calib.name: calib.color for calib in myPGM.calibrations.calib_list}
        self.initialize_fit_models_menu()
        self.initialize_buffer()
        self.view.PvPmTableWindow.set_data_manager(self.model)
        self.view.PvPmPlotWindow.set_data_manager(self.model)
        self.view.PvPmTableWindow.table_widget.recall_requested.connect(self.recall_from_table)
        self.view.PvPmTableWindow.table_changed.connect(self.update_PvPm_table)

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
        self.view.theme_switched.connect(self.on_theme_switched)

        self.view.PToolbox_toTable_button.clicked.connect(self.add_current_PToolbox_to_table)

        if self.test_mode:
            self.initialize_example()

    ##################################################################################""
        #? Methods 

    def initialize_calibrations_menu(self):
        calib_dict = {a.name: a for a in myPGM.calibrations.calib_list}
        self.view.ptoolbox.initialize(calib_dict)
        self.view.additional_toolbox_window.initialize(calib_dict)

    def _show_error(self, text, title="Error"):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(text)
        msg.setWindowTitle(title)
        msg.exec_()

    def _get_spectro_reference_object(self):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            if obj is not None and obj.original_data is not None:
                return obj

        for obj in self.model.values():
            if obj.original_data is not None:
                return obj

        return None

    def _validate_spectro_calibration(self, corrected_spectro_x):
        if corrected_spectro_x is None or len(corrected_spectro_x) == 0:
            raise RuntimeError("Calibration file is empty or could not be parsed.")

        reference_obj = self._get_spectro_reference_object()
        if reference_obj is None:
            return

        reference_x, _ = reference_obj.get_data_to_process()
        if len(corrected_spectro_x) != len(reference_x):
            raise RuntimeError(
                "Calibration file length does not match the loaded spectra "
                f"({len(corrected_spectro_x)} vs {len(reference_x)} points)."
            )

    def _set_spectro_use_checked(self, checked):
        was_blocked = self.view.Spectro_use_button.blockSignals(True)
        self.view.Spectro_use_button.setChecked(checked)
        self.view.Spectro_use_button.blockSignals(was_blocked)

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
#        toolbox.set_state_from_buffer(buffer)
        
#       Nothing to do

    @pressure_valid
    def on_P_edited(self, p):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_P(p)
#        toolbox.set_state_from_buffer(buffer)
        toolbox.set_xval(buffer.x)
    
    @pressure_valid
    def on_x_edited(self, x):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_x(x)        
#        toolbox.set_state_from_buffer(buffer)
        toolbox.set_Pval(buffer.P)

    @pressure_valid
    def on_T_edited(self, T):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_T(T)        
#        toolbox.set_state_from_buffer(buffer)
        toolbox.set_Pval(buffer.P)

    @pressure_valid
    def on_x0_edited(self, x0):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_x0(x0)

        # THE NEW x0 for this gauge is now x0.
        # Update both the buffer's calib copy AND the shared instance in the toolbox
        # so that future files using this calibration start with the updated x0default.
        buffer.calib.x0default = x0
        if buffer.calib is not None and buffer.calib.name in toolbox.calibrations:
            toolbox.calibrations[buffer.calib.name].x0default = x0

#        toolbox.set_state_from_buffer(buffer)
        toolbox.set_Pval(buffer.P)

    @pressure_valid
    def on_T0_edited(self, T0):
        toolbox, buffer = self._get_toolbox_context()
        buffer.set_T0(T0)  

        # THE NEW T0 for this gauge is now T0.
        # Update both the buffer's calib copy AND the shared instance in the toolbox.
        buffer.calib.T0default = T0
        if buffer.calib is not None and buffer.calib.name in toolbox.calibrations:
            toolbox.calibrations[buffer.calib.name].T0default = T0
        
#        toolbox.set_state_from_buffer(buffer)
        toolbox.set_Pval(buffer.P)

    @pressure_valid
    def on_calib_changed(self, newcalib):
        toolbox, buffer = self._get_toolbox_context()
        # data model method!
        buffer.set_calibration(newcalib)

        default_fit_name = getattr(newcalib, "default_fit_model", None)
        if default_fit_name in self.fit_models:
            ind = self.view.fit_model_combo.findText(default_fit_name, Qt.MatchExactly)
            if ind >= 0 and ind != self.view.fit_model_combo.currentIndex():
                self.view.fit_model_combo.setCurrentIndex(ind)

        if toolbox == self.view.ptoolbox and buffer.calib is not None:
            xlabel = f"{buffer.calib.xname} ({buffer.calib.xunit})"
            self.view.data_widget.setLabel("bottom", xlabel)
            self.view.deriv_widget.setLabel("bottom", xlabel)

        # view method
        toolbox.set_state_from_buffer(buffer)

    def file_selected_from_file_list(self, obj_id):
        self.current_selected_file = obj_id
        self.view.current_file_label.setText(f"{self.model.get(obj_id).filename}")

        obj = self.model.get(self.current_selected_file, None)
        if obj is None:
            return

        if self.view.Spectro_use_button.isChecked():
            if self.corrected_spectro_x is not None:
                try:
                    obj.spectro_recalib(self.corrected_spectro_x)
                except Exception as exc:
                    obj.reset_spectro_recalib()
                    self._set_spectro_use_checked(False)
                    self._show_error(
                        f"Alternative spectrometer calibration disabled for this file: {exc}",
                        title="Calibration mismatch",
                    )
            else:
                self._set_spectro_use_checked(False)
        else:
            obj.reset_spectro_recalib()

        self.update_data_plots(obj_id)
        
        # toolbox is updated (is it what we want?)
        obj = self.model.get(obj_id, None)
        if obj.fit_result is not None:
            self.buffer = deepcopy(obj)
            self.view.ptoolbox.set_state_from_buffer(self.buffer)

        # fit model combo box is updated.
        if obj.fit_model is not None and obj.fit_model.name in self.fit_models:
            ind = self.view.fit_model_combo.findText(obj.fit_model.name, Qt.MatchExactly)
            if ind >= 0 and ind != self.view.fit_model_combo.currentIndex():
                self.view.fit_model_combo.setCurrentIndex(ind)


    def add_instance_from_path(self, file_path):
        file_info = QFileInfo(file_path)
        file_name = file_info.fileName()
        a = PressureGaugeDataObject()
        self.model.add_instance(a)
        a.load_spectral_data_file(file_name, file_path)


    def add_new_file(self):
        try:
            selected_files = self.view.get_file_via_dialog()
        except Exception as exc:
            raise RuntimeError(f"File selection dialog failed: {exc}") from exc
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
                self._show_error("No files in selected directory.")
        else:
            self._show_error("No directory selected.")

    def delete_current_file(self):
        if self.current_selected_file is not None:
            obj_id = self.current_selected_file
            self.model.delete_instance(obj_id)
            self.current_selected_file = None
            self.populate_file_list()
            self.update_PvPm_table()
            self.view.current_file_label.setText("No file selected")
        else:
            self._show_error("No file selected to delete.")

    def update_data_plots(self, obj_id, preserve_view=False):
        obj = self.model.get(obj_id, None)
        if obj.original_data is not None:
            data_view_range = None
            deriv_view_range = None
            data_autorange = None
            deriv_autorange = None
            if preserve_view:
                data_vb = self.view.data_widget.plotItem.vb
                deriv_vb = self.view.deriv_widget.plotItem.vb
                data_view_range = self.view.data_widget.plotItem.vb.viewRange()
                deriv_view_range = self.view.deriv_widget.plotItem.vb.viewRange()
                data_autorange = tuple(data_vb.autoRangeEnabled())
                deriv_autorange = tuple(deriv_vb.autoRangeEnabled())
                data_vb.enableAutoRange(x=False, y=False)
                deriv_vb.enableAutoRange(x=False, y=False)

            x, y = obj.get_data_to_process()
            x_min = float(np.min(x))
            x_max = float(np.max(x))

            # on utilise buffer (juste pour afficher les unités des axes dans plot_data)
            self.view.plot_data(x, y, self.buffer, preserve_view=preserve_view)
            if obj.fit_result is not None:
                self.view.plot_fit(obj.P, obj.fit_model, obj.fit_result, x, y)

            self.view.fit_range_selector.setBounds((x_min, x_max))

            if obj.fitting_range is not None:
                sanitized_range = self._sanitize_fitting_range(obj.fitting_range, x_min, x_max)
                obj.fitting_range = sanitized_range
                self.view.fit_range_selector.setRegion(sanitized_range)
            else:
                current_region = self.view.fit_range_selector.getRegion()
                if (not self.view.fit_range_selector_edited) or self._range_needs_reset(current_region, x_min, x_max):
                    self.view.fit_range_selector.setRegion(
                        self._centered_nonzero_range(x_min, x_max)
                    )

            if preserve_view and data_view_range is not None and deriv_view_range is not None:
                self.view.data_widget.plotItem.vb.setRange(
                    xRange=tuple(data_view_range[0]),
                    yRange=tuple(data_view_range[1]),
                    padding=0,
                )
                self.view.deriv_widget.plotItem.vb.setRange(
                    xRange=tuple(deriv_view_range[0]),
                    yRange=tuple(deriv_view_range[1]),
                    padding=0,
                )
                if data_autorange is not None and deriv_autorange is not None:
                    self.view.data_widget.plotItem.vb.enableAutoRange(
                        x=bool(data_autorange[0]),
                        y=bool(data_autorange[1]),
                    )
                    self.view.deriv_widget.plotItem.vb.enableAutoRange(
                        x=bool(deriv_autorange[0]),
                        y=bool(deriv_autorange[1]),
                    )
            
        else:
            print('No data to be plotted.')

    def on_theme_switched(self):
        if self.current_selected_file is not None:
            self.update_data_plots(self.current_selected_file, preserve_view=True)

    def _centered_nonzero_range(self, x_min, x_max):
        x_span = max(float(x_max) - float(x_min), 1e-9)
        x_mean = (float(x_min) + float(x_max)) / 2.0
        half_width = max(x_span * 0.15, 1e-6)
        return (x_mean - half_width, x_mean + half_width)

    def _sanitize_fitting_range(self, fit_range, x_min, x_max):
        centered = self._centered_nonzero_range(x_min, x_max)

        if fit_range is None or len(fit_range) != 2:
            return centered

        try:
            low = float(fit_range[0])
            high = float(fit_range[1])
        except (TypeError, ValueError):
            return centered

        if not (np.isfinite(low) and np.isfinite(high)):
            return centered

        if low > high:
            low, high = high, low

        low = max(low, float(x_min))
        high = min(high, float(x_max))

        x_span = max(float(x_max) - float(x_min), 1e-9)
        min_width = max(x_span * 0.02, 1e-6)

        # If the range collapses (typically clipped to one edge), recenter it.
        if (high - low) < min_width:
            return centered

        return (low, high)

    def _range_needs_reset(self, fit_range, x_min, x_max):
        sanitized = self._sanitize_fitting_range(fit_range, x_min, x_max)
        low, high = float(sanitized[0]), float(sanitized[1])
        cur_low = float(fit_range[0]) if fit_range is not None and len(fit_range) == 2 else np.nan
        cur_high = float(fit_range[1]) if fit_range is not None and len(fit_range) == 2 else np.nan

        if not (np.isfinite(cur_low) and np.isfinite(cur_high)):
            return True

        return (abs(cur_low - low) > 1e-12) or (abs(cur_high - high) > 1e-12)


    def smoothen(self, smoothing_factor):
        if self.current_selected_file is None:
            return

        obj = self.model.get(self.current_selected_file, None)
        obj.smoothen(int(smoothing_factor))
        self.update_data_plots(self.current_selected_file)
    
    def subtract_auto_bg(self):
        if self.current_selected_file is None:
            return

        obj = self.model.get(self.current_selected_file, None)
        obj.convexhull_bg()
        self.update_data_plots(self.current_selected_file)

    def subtract_manual_bg(self, bg):
        if self.current_selected_file is None or bg is None:
            return

        obj = self.model.get(self.current_selected_file, None)
        obj.subtract_external_bg(bg)
        self.update_data_plots(self.current_selected_file, preserve_view=True)
    
    def reset_bg(self):
        if self.current_selected_file is None:
            return

        obj = self.model.get(self.current_selected_file, None)
        obj.reset_bg()
        self.update_data_plots(self.current_selected_file)


    def load_spectro_calibration(self):
        selected_files = self.view.get_file_via_dialog()
        if not selected_files:
            return

        selected_file = selected_files[0]
        file_info = QFileInfo(selected_file)
        file_name = file_info.fileName()

        try:
            corrected_spectro_x = spectro_calibration_reader(selected_file)
            self._validate_spectro_calibration(corrected_spectro_x)
        except Exception as exc:
            self.corrected_spectro_x = None
            self.view.Spectro_filename_label.setText("None")
            self.view.Spectro_use_button.setChecked(False)
            self._show_error(
                f"Failed to load spectrometer calibration file: {exc}",
                title="Calibration load error",
            )
            return

        self.corrected_spectro_x = corrected_spectro_x
        self.view.Spectro_filename_label.setText(file_name)

        if self.view.Spectro_use_button.isChecked() and self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            if obj is not None:
                obj.spectro_recalib(self.corrected_spectro_x)
                self.update_data_plots(self.current_selected_file)

        return 
    
    def toggle_spectro_calib(self, checked):
        if self.current_selected_file is None:
            return

        obj = self.model.get(self.current_selected_file, None)
        if checked:
            if self.corrected_spectro_x is None:
                self._set_spectro_use_checked(False)
                return

            try:
                obj.spectro_recalib(self.corrected_spectro_x)
            except Exception as exc:
                obj.reset_spectro_recalib()
                self._set_spectro_use_checked(False)
                self._show_error(
                    f"Alternative spectrometer calibration disabled for this file: {exc}",
                    title="Calibration mismatch",
                )

            self.update_data_plots(self.current_selected_file)
            return

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

    def recall_from_table(self, obj_id):
        try:
            obj_id = int(obj_id)
        except (TypeError, ValueError):
            return

        obj = self.model.get(obj_id, None)
        if obj is None:
            return

        # If the entry is tied to a loaded file, reuse the normal file-selection flow.
        if getattr(obj, "include_in_filelist", False):
            self.select_file_in_list(obj_id)
            self.file_selected_from_file_list(obj_id)
            return

        # For table-only entries, restore toolbox state from the recalled object.
        self.current_selected_file = None
        self.view.current_file_label.setText("No file selected")
        self.buffer = deepcopy(obj)
        self.view.ptoolbox.set_state_from_buffer(self.buffer)

        if obj.fit_model is not None and obj.fit_model.name in self.fit_models:
            ind = self.view.fit_model_combo.findText(obj.fit_model.name, Qt.MatchExactly)
            if ind >= 0 and ind != self.view.fit_model_combo.currentIndex():
                self.view.fit_model_combo.setCurrentIndex(ind)


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
                self.update_data_plots(self.current_selected_file, preserve_view=True)

            except RuntimeError:
                self.fit_error_popup()

    def fit_error_popup(self):
        self.view.fit_error_popup_window()

    def add_current_fit_to_table(self, _=None):
        if self.current_selected_file is not None:
            obj = self.model.get(self.current_selected_file, None)
            if obj.fit_result is not None:
                pm_value = self.view.prompt_fit_pm(self.buffer.Pm)
                if pm_value is None:
                    return
                obj.set_Pm(pm_value)
                self.buffer.set_Pm(pm_value)
                self.view.ptoolbox.set_Pmval(pm_value)
                obj.include_in_table = True
                self.update_PvPm_table()
            else:
                self._show_error("No fit result to add to table.")
        else:
            self._show_error("No file selected.")


    def update_PvPm_table(self):
        self.view.PvPmTableWindow.table_widget.updatetable()
        self.view.PvPmPlotWindow.updateplot()

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
            "app_version": self.app_version,
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
            self._show_error(f"Failed to save session: {exc}", title="Save error")

    def load_session(self):
        file_path = self.view.get_open_session_filename_dialog()
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file_handle:
                session = json.load(file_handle)
        except Exception as exc:
            self._show_error(f"Failed to load session: {exc}", title="Load error")
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
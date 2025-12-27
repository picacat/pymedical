# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets

from libs import module_utils, system_utils, ui_utils


# 病患資料 2020.10.05
class Patient(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(Patient, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.call_from = args[3]
        self.ic_card = args[4]
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.tab_patient_data = module_utils.get_patient_data(
            self, self.database, self.system_settings, self.patient_key, self.call_from, self.ic_card
        )
        self.ui.tabWidget_patient.addTab(self.tab_patient_data, '病患資料')

        if self.patient_key is not None:  # 初診病患建檔時不能輸入初診照護資料 2025-08-07 陳立德青花瓷
            self.tab_patient_new_care = module_utils.get_patient_new_care(
                self, self.database, self.system_settings, self.patient_key,
            )
            self.ui.tabWidget_patient.addTab(self.tab_patient_new_care, '初診照護病歷')

            self.tab_patient_settings = module_utils.get_patient_settings(
                self, self.database, self.system_settings, self.patient_key,
            )
            self.ui.tabWidget_patient.addTab(self.tab_patient_settings, '病患設定')

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_patient)
        self.ui.action_save.triggered.connect(self._save_patient)
        self.ui.action_copy_remote_patient.triggered.connect(self._copy_remote_patient)
        self.ui.action_capture_image.triggered.connect(self._capture_image)
        self.ui.action_remove_image.triggered.connect(self._remove_photo)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_patient(self):
        self.close_all()
        self.close_tab()

    def _save_patient(self):
        patient_key = self.tab_patient_data.save_patient()
        if patient_key is None:
            return

        try:
            self.tab_patient_new_care.save_patient_new_care(patient_key)
            self.tab_patient_settings.save_patient_settings(patient_key)
        except Exception:
            pass
        
        self.close_patient()

    def _copy_remote_patient(self):
        self.tab_patient_data.copy_remote_patient()

    def _capture_image(self):
        self.tab_patient_data.capture_image()

    def _remove_photo(self):
        self.tab_patient_data.remove_photo()

# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from libs import patient_utils, system_utils, ui_utils


#  病患設定 2023.06.27 太初
class PatientSettings(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PatientSettings, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.patient_key is not None:
            self._read_patient_settings()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PATIENT_SETTINGS, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        pass

    def _read_patient_settings(self):
        medicine_bag_name_mask = patient_utils.get_patient_extension_settings(
            self.database, self.patient_key, '藥包姓名遮蔽')
        if medicine_bag_name_mask == '1':
            self.ui.checkBox_medicine_bag_name_mask.setChecked(True)
            
        medicine_bag_no_name = patient_utils.get_patient_extension_settings(
            self.database, self.patient_key, '藥包姓名不印')
        if medicine_bag_no_name == '1':
            self.ui.checkBox_medicine_bag_no_name.setChecked(True)

    def save_patient_settings(self, patient_key):
        patient_utils.set_patient_extension_settings(
            self.database, patient_key, '藥包姓名遮蔽', self.ui.checkBox_medicine_bag_name_mask.isChecked()
        )
        patient_utils.set_patient_extension_settings(
            self.database, patient_key, '藥包姓名不印', self.ui.checkBox_medicine_bag_no_name.isChecked()
        )

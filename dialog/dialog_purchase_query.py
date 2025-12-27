
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import patient_utils
from libs import personnel_utils


# 主視窗
class DialogPurchaseQuery(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPurchaseQuery, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PURCHASE_QUERY, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.dateEdit_start_date.setDate(datetime.datetime.now())
        self.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_patient.clicked.connect(self._select_patient)

    def _set_combo_box(self):
        ui_utils.set_combo_box(
            self.ui.comboBox_doctor,
            personnel_utils.get_person(self.database, '全部醫師'), None,
        )

        ui_utils.set_combo_box(
            self.ui.comboBox_massage_referrer,
            personnel_utils.get_person(self.database, '推拿師父'), None,
        )

        ui_utils.set_combo_box(
            self.ui.comboBox_nursing_assistant,
            personnel_utils.get_person(self.database, '職員'), None,
        )

    def accepted_button_clicked(self):
        pass

    def _select_patient(self):
        patient_key = patient_utils.select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', ''
        )
        self.ui.lineEdit_patient_key.setText(patient_key)

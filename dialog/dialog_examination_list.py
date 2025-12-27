
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import ui_utils
from libs import system_utils
from libs import patient_utils
from libs import dialog_utils


# 檢驗查詢查詢視窗
class DialogExaminationList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExaminationList, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXAMINATION_LIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.label_patient_key.setEnabled(False)
        self.ui.lineEdit_patient_key.setEnabled(False)
        self.ui.toolButton_select_patient.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_patient.clicked.connect(lambda: self._select_patient(None))

        self.ui.radioButton_range_date.clicked.connect(self._set_date)
        self.ui.radioButton_all_date.clicked.connect(self._set_date)

        self.ui.radioButton_all_patient.clicked.connect(self._set_patient)
        self.ui.radioButton_assigned_patient.clicked.connect(self._set_patient)

    def _set_patient(self):
        if self.ui.radioButton_all_patient.isChecked():
            self.ui.lineEdit_patient_key.setText('')
            enabled = False
        else:
            enabled = True

        self.ui.label_patient_key.setEnabled(enabled)
        self.ui.lineEdit_patient_key.setEnabled(enabled)
        self.ui.toolButton_select_patient.setEnabled(enabled)

        if self.ui.radioButton_assigned_patient.isChecked():
            self.ui.lineEdit_patient_key.setFocus()

    def _set_date(self):
        if self.ui.radioButton_all_date.isChecked():
            enabled = False
            self.ui.radioButton_assigned_patient.setChecked(True)
            self._set_patient()
            self.ui.lineEdit_patient_key.setFocus()
        else:
            enabled = True
            self.ui.radioButton_all_patient.setChecked(True)
            self._set_patient()

        self.ui.label_date.setEnabled(enabled)
        self.ui.label_between.setEnabled(enabled)
        self.ui.dateEdit_start_date.setEnabled(enabled)
        self.ui.dateEdit_end_date.setEnabled(enabled)

    # 設定 mysql script
    def get_sql(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd')

        condition = []
        script = '''
            SELECT * FROM examination
        '''

        if self.ui.radioButton_range_date.isChecked():
            condition.append(f'(ExaminationDate BETWEEN "{start_date}" AND "{end_date}")')

        keyword = self.ui.lineEdit_patient_key.text()
        if keyword != '':
            patient_key = patient_utils.get_patient_by_keyword(
                self, self.database, self.system_settings,
                'patient', 'PatientKey', keyword
            )
            if patient_key in ['', None]:
                self.ui.lineEdit_patient_key.setText('')
            else:
                condition.append(f'PatientKey = {patient_key}')

        if len(condition) > 0:
            condition = ' AND '.join(condition)
            script += f' WHERE {condition} '

        script += ' ORDER BY ExaminationDate'

        if self.ui.radioButton_all_date.isChecked() and self.ui.lineEdit_patient_key.text() == '':
            script = ''

        return script

    def accepted_button_clicked(self):
        pass

    def _select_patient(self, keyword=None):
        patient_key = ''

        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', keyword
        )
        if dialog.exec_():
            patient_key = dialog.get_primary_key()

        self.ui.lineEdit_patient_key.setText(patient_key)

        dialog.deleteLater()

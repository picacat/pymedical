
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime
from libs import ui_utils
from libs import system_utils
from libs import patient_utils
from libs import dialog_utils


# 醫療費用證明書查詢
class DialogCertificateQuery(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCertificateQuery, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.certificate_type = args[2]
        self.ui = None

        self.sql = None
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CERTIFICATE_QUERY, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.ui.label_year.setEnabled(False)
        self.ui.spinBox_year.setEnabled(False)

        current_year = datetime.datetime.now().year
        self.ui.spinBox_year.setMaximum(current_year)
        self.ui.spinBox_year.setValue(current_year)
        self.ui.lineEdit_keyword.setFocus()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.radioButton_patient.clicked.connect(self._set_patient)
        self.ui.radioButton_year.clicked.connect(self._set_patient)
        self.ui.toolButton_select_patient.clicked.connect(lambda: self._select_patient(None))

    def _set_patient(self):
        if self.ui.radioButton_patient.isChecked():
            enabled = True
        else:
            self.ui.lineEdit_keyword.setText('')
            enabled = False

        self.ui.label_keyword.setEnabled(enabled)
        self.ui.lineEdit_keyword.setEnabled(enabled)
        self.ui.toolButton_select_patient.setEnabled(enabled)

        self.ui.label_year.setEnabled(not enabled)
        self.ui.spinBox_year.setEnabled(not enabled)

    def accepted_button_clicked(self):
        self.sql = f'''
            SELECT certificate.*, cases.ChargeDone FROM certificate
                LEFT JOIN cases ON cases.CaseKey = certificate.CaseKey
            WHERE
                CertificateType = "{self.certificate_type}"
        '''

        if self.ui.radioButton_patient.isChecked():
            keyword = self.ui.lineEdit_keyword.text()
            if keyword == '':
                pass
            elif keyword.isdigit() and len(keyword) < 7:
                self.sql += f' AND certificate.PatientKey = {keyword}'
            else:
                patient_key = patient_utils.get_patient_by_keyword(
                    self, self.database, self.system_settings,
                    'patient', 'PatientKey', keyword
                )

                if patient_key != '':
                    self.sql += f''' AND certificate.PatientKey = {patient_key}'''
        else:
            year = self.ui.spinBox_year.value()
            start_date = f'{year}-01-01 00:00:00'
            end_date = f'{year}-12-31 23:59:59'
            self.sql += f' AND CertificateDate BETWEEN "{start_date}" AND "{end_date}"'

        self.sql += ' ORDER BY CertificateKey DESC'

    def _select_patient(self, keyword=None):
        patient_key = ''
        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings,
            'patient', 'PatientKey', keyword
        )
        if dialog.exec_():
            patient_key = dialog.get_primary_key()

        self.ui.lineEdit_keyword.setText(patient_key)

        dialog.deleteLater()

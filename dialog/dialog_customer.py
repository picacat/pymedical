
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import patient_utils
from libs import string_utils
from libs import nhi_utils
from libs import validator_utils
from libs import date_utils
from libs import dialog_utils


# 新增顧客資料
class DialogCustomer(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCustomer, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.customer_key = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        if self.customer_key is not None:
            self._set_customer_data()
        else:
            self._preset_customer_data()

        self.ui.lineEdit_name.setFocus()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CUSTOMER, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_patient_key.setInputMask('00000000')
        self._set_combobox()
        self._set_validator()

    def _set_validator(self):
        self.ui.lineEdit_birthday.setValidator(validator_utils.set_validator('日期格式'))
        self.ui.lineEdit_id.setValidator(validator_utils.set_validator('身分證格式'))

    def _set_combobox(self):
        ui_utils.set_combo_box(self.ui.comboBox_gender, nhi_utils.GENDER, None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_patient.clicked.connect(self._select_patient)
        self.ui.toolButton_address.clicked.connect(self._open_address_dict)
        self.ui.lineEdit_birthday.editingFinished.connect(self._validate_birthday)

    def _validate_birthday(self):
        west_date = date_utils.date_to_west_date(self.ui.lineEdit_birthday.text())
        self.ui.lineEdit_birthday.setText(west_date)

    def accepted_button_clicked(self):
        self._save_customer()

    def _save_customer(self):
        fields = [
            'PatientKey', 'Name', 'Birthday', 'ID', 'Gender',
            'Telephone', 'Cellphone', 'Email', 'Address', 'Remark'
        ]
        data = [
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_id.text(),
            self.ui.comboBox_gender.currentText(),
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_cellphone.text(),
            self.ui.lineEdit_email.text(),
            self.ui.lineEdit_address.text(),
            self.ui.lineEdit_remark.text(),
        ]
        if self.customer_key is not None:
            self.database.update_record('massage_customer', fields, 'MassageCustomerKey', self.customer_key, data)
        else:
            self.last_row_id = self.database.insert_record('massage_customer', fields, data)

    def _set_customer_data(self):
        sql = f'''
            SELECT * FROM massage_customer
            WHERE
                MassageCustomerKey = {self.customer_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        self.lineEdit_customer_key.setText(string_utils.xstr(self.customer_key))
        self._set_massage_customer_data(row)

    def _preset_customer_data(self):
        customer_key = self.database.get_last_auto_increment_key('massage_customer')

        self.ui.lineEdit_customer_key.setText(string_utils.xstr(customer_key))

    def _select_patient(self):
        patient_key = patient_utils.select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', ''
        )
        if patient_key == '':
            return

        self._set_line_edit_patient_data(patient_key)

    def _set_line_edit_patient_data(self, patient_key):
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self._set_massage_customer_data(row)

    def _set_massage_customer_data(self, row):
        self.lineEdit_patient_key.setText(string_utils.xstr(row['PatientKey']))
        self.lineEdit_name.setText(string_utils.xstr(row['Name']))
        self.lineEdit_birthday.setText(string_utils.xstr(row['Birthday']))
        self.lineEdit_id.setText(string_utils.xstr(row['ID']))
        self.comboBox_gender.setCurrentText(string_utils.xstr(row['Gender']))
        self.lineEdit_telephone.setText(string_utils.xstr(row['Telephone']))
        self.lineEdit_cellphone.setText(string_utils.xstr(row['Cellphone']))
        self.lineEdit_email.setText(string_utils.xstr(row['Email']))
        self.lineEdit_address.setText(string_utils.xstr(row['Address']))

    def _open_address_dict(self):
        dialog = dialog_utils.get_dialog_address(
            self, self.database, self.system_settings, self.ui.lineEdit_address,
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()


# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QDialogButtonBox

import re
import datetime

from libs import system_utils
from libs import ui_utils
from libs import validator_utils
from libs import patient_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import dialog_utils


# 新增物理治療預約
class DialogPhysiotherapyBooking(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPhysiotherapyBooking, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.physiotherapy_date = args[2]
        self.physiotherapy_time = args[3]
        self.physiotherapy = args[4]
        self.ui = None

        self._set_ui()
        self._set_validator()
        self._set_signal()

        self.default_treat_fee = 2500

        row = self._read_data()
        if row is None:
            self.update_type = 'insert'
        else:
            self.update_type = 'update'
            self._set_data(row)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PHYSIOTHERAPY_BOOKING, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('存檔')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.lineEdit_physiotherapy_date.setText(f'{self.physiotherapy_date} {self.physiotherapy_time}')
        self.ui.lineEdit_physiotherapy.setText(self.physiotherapy)
        try:
            hour = int(self.physiotherapy_time.split(':')[0])
            minute = int(self.physiotherapy_time.split(':')[1])
            self.ui.timeEdit_arrival_time.setTime(QtCore.QTime(hour, minute))
        except Exception:
            pass

        ui_utils.set_completer(
            self.database,
            'SELECT Name FROM patient GROUP BY Name ORDER BY Name',
            'Name',
            self.ui.lineEdit_query
        )
        self._clear_patient_data()
        # self._set_patient_read_only(True)

    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            return

    # 設定信號
    def _set_signal(self):
        # self.ui.buttonBox.accepted.connect(self._dialog_button_clicked)
        self.ui.buttonBox.clicked.connect(self._dialog_button_clicked)
        self.ui.pushButton_query.clicked.connect(self._query_patient)
        self.ui.lineEdit_query.returnPressed.connect(self._query_patient)
        self.ui.lineEdit_name.textChanged.connect(self.check_validation)
        self.ui.lineEdit_birthday.editingFinished.connect(self._validate_birthday)
        self.ui.spinBox_treat_fee.valueChanged.connect(self._check_fee)
        self.ui.spinBox_receipt_fee.valueChanged.connect(self._check_fee)

    def _check_fee(self):
        treat_fee = self.ui.spinBox_treat_fee.value()
        receipt_fee = self.ui.spinBox_receipt_fee.value()
        if receipt_fee > 0 and (receipt_fee != treat_fee):
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _cancel_button_clicked(self):
        self.close()

    def _validate_birthday(self):
        west_date = date_utils.date_to_west_date(self.ui.lineEdit_birthday.text())
        self.ui.lineEdit_birthday.setText(west_date)

    def _set_validator(self):
        self.ui.lineEdit_birthday.setValidator(validator_utils.set_validator('日期格式'))

    def check_validation(self):
        if self.ui.spinBox_treat_fee.value() == 0:
            self.ui.spinBox_treat_fee.setValue(self.default_treat_fee)

        if self.ui.lineEdit_patient_key.text() in ['', None] and \
                '(初診)' not in self.ui.lineEdit_remark.text():
            self.ui.lineEdit_remark.setText(self.ui.lineEdit_remark.text() + '(初診)')

        if self.ui.lineEdit_name.text().strip() != '':
            button_enabled = True
        else:
            button_enabled = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(button_enabled)

    def _clear_patient_data(self):
        self.ui.lineEdit_patient_key.setText(None)
        self.ui.lineEdit_name.setText(None)
        self.ui.lineEdit_birthday.setText(None)
        self.ui.lineEdit_id.setText(None)
        self.ui.lineEdit_telephone.setText(None)
        self.ui.lineEdit_cellphone.setText(None)
        self.ui.lineEdit_address.setText(None)

    def _set_patient_read_only(self, set_read_only):
        self.ui.lineEdit_query.setEnabled(set_read_only)
        self.ui.pushButton_query.setEnabled(set_read_only)

        self.ui.lineEdit_patient_key.setReadOnly(True)
        self.ui.lineEdit_name.setReadOnly(set_read_only)
        self.ui.lineEdit_birthday.setReadOnly(set_read_only)
        self.ui.lineEdit_id.setReadOnly(set_read_only)
        self.ui.lineEdit_telephone.setReadOnly(set_read_only)
        self.ui.lineEdit_cellphone.setReadOnly(set_read_only)
        self.ui.lineEdit_address.setReadOnly(set_read_only)

        if set_read_only:
            self.ui.lineEdit_query.setFocus()
        else:
            self.ui.lineEdit_name.setFocus()

    def _dialog_button_clicked(self, sender):
        if sender == self.ui.buttonBox.button(QDialogButtonBox.Cancel):
            self.close()
            return

        if self.lineEdit_name.isModified() or \
                self.lineEdit_id.isModified() or \
                self.lineEdit_birthday.isModified() or \
                self.lineEdit_telephone.isModified() or \
                self.lineEdit_cellphone.isModified() or \
                self.lineEdit_address.isModified():
            self._save_patient()

        if self.update_type == 'update':
            self._update_physiotherapy_record()
        else:
            self._insert_physiotherapy_record()

    def _update_physiotherapy_record(self):
        arrival_time = self.ui.timeEdit_arrival_time.time().toString("hh:mm")
        treat_fee = self.ui.spinBox_treat_fee.value()
        receipt_fee = self.ui.spinBox_receipt_fee.value()
        remark = self.ui.lineEdit_remark.text()
        if receipt_fee > 0 and '(已報到)' not in self.ui.lineEdit_remark.text():
            if '(初診)' in self.ui.lineEdit_remark.text():
                self._insert_patient()

            remark += '(已報到)'

        sql = f'''
            UPDATE physiotherapy_schedule
            SET
                ArrivalTime = "{arrival_time}",
                TreatFee = "{treat_fee}",
                ReceiptFee = "{receipt_fee}",
                Remark = "{remark}"
            WHERE
                PhysiotherapyDate = "{self.physiotherapy_date}" AND
                PhysiotherapyTime = "{self.physiotherapy_time}" AND
                Physiotherapy = "{self.physiotherapy}"
        '''
        self.database.exec_sql(sql)

    def _insert_patient(self):
        fields = ['Name', 'ID', 'Birthday', 'Telephone', 'Cellphone', 'Address']

        name = self.ui.lineEdit_name.text()
        sql = f'''
            SELECT * FROM patient
            WHERE
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            patient_key = rows[0]['PatientKey']
        else:
            data = [
                name,
                self.ui.lineEdit_id.text(),
                self.ui.lineEdit_birthday.text(),
                self.ui.lineEdit_telephone.text(),
                self.ui.lineEdit_cellphone.text(),
                self.ui.lineEdit_address.text(),
            ]
            patient_key = self.database.insert_record('patient', fields, data)

        sql = f'''
            UPDATE physiotherapy_schedule
            SET
                PatientKey = "{patient_key}"
            WHERE
                PhysiotherapyDate = "{self.physiotherapy_date}" AND
                PhysiotherapyTime = "{self.physiotherapy_time}" AND
                Physiotherapy = "{self.physiotherapy}"
        '''
        self.database.exec_sql(sql)

    def _insert_physiotherapy_record(self):
        fields = [
            'PhysiotherapyDate', 'PhysiotherapyTime', 'Physiotherapy',
            'PatientKey', 'ArrivalTime', 'TreatFee', 'ReceiptFee', 'Remark'
        ]
        physiotherapy_date = date_utils.str_to_date(self.physiotherapy_date)
        physiotherapy_time = self.physiotherapy_time
        physiotherapy = self.ui.lineEdit_physiotherapy.text()
        patient_key = self.ui.lineEdit_patient_key.text()
        arrival_time = self.ui.timeEdit_arrival_time.time().toString("hh:mm")
        treat_fee = self.ui.spinBox_treat_fee.value()
        receipt_fee = self.ui.spinBox_receipt_fee.value()
        remark = self.ui.lineEdit_remark.text()

        data = [
            physiotherapy_date, physiotherapy_time, physiotherapy,
            patient_key, arrival_time, treat_fee, receipt_fee, remark,
        ]

        self.database.insert_record('physiotherapy_schedule', fields, data)

    def _save_patient(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        remark = self.ui.lineEdit_remark.text()
        if patient_key in ['', None]:
            patient_key = self._insert_temp_patient()
            self.ui.lineEdit_patient_key.setText(str(patient_key))
            self.ui.lineEdit_remark.setText(remark)
        elif '(初診)' not in remark:  # 複診病人要更改修改的資料
            self._update_patient()

    def _insert_temp_patient(self):
        fields = ['Name', 'ID', 'Birthday', 'PhoneNo', 'Cellphone', 'Address']
        data = [
            self.ui.lineEdit_name.text(), self.ui.lineEdit_id.text(), self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_telephone.text(), self.ui.lineEdit_cellphone.text(), self.ui.lineEdit_address.text(),
        ]
        temp_patient_key = self.database.insert_record('temp_patient', fields, data)

        return temp_patient_key

    def _update_patient(self):
        patient_key = self.ui.lineEdit_patient_key.text()

        fields = ['Name', 'ID', 'Birthday', 'Telephone', 'Cellphone', 'Address']
        data = [
            self.ui.lineEdit_name.text(), self.ui.lineEdit_id.text(), self.ui.lineEdit_birthday.text(),
            self.ui.lineEdit_telephone.text(), self.ui.lineEdit_cellphone.text(), self.ui.lineEdit_address.text(),
        ]
        self.database.update_record('patient', fields, 'PatientKey', patient_key, data)

    # 開始查詢病患資料
    def _query_patient(self):
        keyword = string_utils.xstr(self.ui.lineEdit_query.text())
        if keyword == '':
            return

        pattern = re.compile(validator_utils.DATE_REGEXP)
        if pattern.match(keyword):
            keyword = date_utils.date_to_west_date(keyword)
        else:
            keyword = validator_utils.get_exp_date(keyword)

        self._get_patient(keyword)

    def _get_patient(self, keyword, ic_card=None):
        rows = patient_utils.search_patient(self.ui, self.database, self.system_settings, keyword)
        if rows is None:  # 找不到資料
            dialog = dialog_utils.get_dialog_select_patient(
                self, self.database, self.system_settings, 'patient', 'PatientKey', keyword
            )
            if dialog.table_widget_patient_list.row_count() <= 0:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    '查無資料',
                    '<font size="5" color="red"><b>找不到有關的病患資料, 請檢查關鍵字是否有誤.</b></font>',
                    '請確定輸入資料的正確性, 生日請輸入YYYY-MM-DD.'
                )
                self.ui.lineEdit_query.setFocus()
                return

            if dialog.exec_():
                patient_key = dialog.get_primary_key()
                rows = patient_utils.get_patient_row(self.database, patient_key)
                self._set_patient_data(rows)

            del dialog
        elif rows == -1:  # 取消查詢
            self.ui.lineEdit_query.setFocus()
        else:  # 已選取病患
            self._set_patient_data(rows)
            self.ui.spinBox_treat_fee.setValue(self.default_treat_fee)

        self.ui.lineEdit_query.clear()

    def _set_patient_data(self, rows):
        try:
            row = rows[0]
        except Exception:
            row = rows

        patient_key = row['PatientKey']
        name = string_utils.xstr(row['Name'])  # 病歷號可能會跟網路初診病歷號重複
        telephone = string_utils.xstr(row['Telephone'])
        cellphone = string_utils.xstr(row['Cellphone'])
        address = string_utils.xstr(row['Address'])

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))
        self.ui.lineEdit_name.setText(name)
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row['Birthday']))
        self.ui.lineEdit_id.setText(string_utils.xstr(row['ID']))
        self.ui.lineEdit_telephone.setText(telephone)
        self.ui.lineEdit_cellphone.setText(cellphone)
        self.ui.lineEdit_address.setText(address)

    def _read_data(self):
        sql = f'''
            SELECT * FROM physiotherapy_schedule
            WHERE
                PhysiotherapyDate = "{self.physiotherapy_date}" AND
                PhysiotherapyTime = "{self.physiotherapy_time}" AND
                Physiotherapy = "{self.physiotherapy}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]

        return row

    def _set_data(self, row):
        self.ui.pushButton_query.setEnabled(False)
        self.ui.lineEdit_query.setEnabled(False)

        arrival_time = string_utils.xstr(row['ArrivalTime'])
        arrival_time = datetime.datetime.strptime(arrival_time, '%H:%M').time()
        treat_fee = number_utils.get_integer(row['TreatFee'])
        receipt_fee = number_utils.get_integer(row['ReceiptFee'])
        remark = string_utils.xstr(row['Remark'])

        patient_key = string_utils.xstr(row['PatientKey'])
        patient_row = patient_utils.get_patient_row(self.database, patient_key)
        if '(初診)' in remark and '(已到到)' not in remark:
            temp_patient_row = patient_utils.get_temp_patient(self.database, patient_key, '*')
            if temp_patient_row is not None:
                patient_row = temp_patient_row
                patient_row['PatientKey'] = patient_row['TempPatientKey']
                patient_row['Telephone'] = patient_row['PhoneNo']

        self._set_patient_data(patient_row)

        self.ui.spinBox_treat_fee.setValue(treat_fee)
        self.ui.spinBox_receipt_fee.setValue(receipt_fee)
        self.ui.timeEdit_arrival_time.setTime(arrival_time)
        self.ui.lineEdit_remark.setText(remark)

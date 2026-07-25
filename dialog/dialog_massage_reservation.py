
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QInputDialog
from libs import class_utils

import datetime

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import personnel_utils
from libs import patient_utils
from libs import nhi_utils
from libs import number_utils
from libs import dialog_utils
from libs import massage_utils
from libs import db_utils


# 新增養生館預約 2019.11.13
class DialogMassageReservation(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMassageReservation, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.massager = args[2]
        self.reservation_date = args[3]
        self.period = args[4]
        self.start_time = args[5]
        self.end_time = args[6]
        self.massage_case_key = args[7]

        self.ui = None

        self._set_db()
        self._set_ui()
        self._set_signal()
        if self.massage_case_key is None:
            self._preset_reservation()
        else:
            self._read_reservation()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定資料庫來源
    def _set_db(self):
        try:
            massage_host_dict = db_utils.get_host_database_dict(self.database, '養生館')
            clinic_name = list(massage_host_dict)[0]
            self.massage_database = massage_host_dict[clinic_name]['database']
        except (KeyError, IndexError, AttributeError):
            self.massage_database = None

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MASSAGE_RESERVATION, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        button_ok = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        button_ok.setText('確定')
        button_ok.setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self._set_combo_box()

        self.table_widget_massage_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_massage_prescript, self.massage_database
        )
        self.table_widget_massage_prescript.set_column_hidden([0, 1, 2])
        self.table_widget_massage_payment = class_utils.get_table_widget(
            self.ui.tableWidget_massage_payment, self.massage_database
        )
        self.table_widget_massage_payment.set_column_hidden([0, 1])
        self._set_table_width()
        self._set_group_box(False)

    # 設定信號
    def _set_signal(self):
        self.ui.lineEdit_massage_customer_key.returnPressed.connect(self._get_massage_customer)
        self.ui.lineEdit_massage_customer_key.textChanged.connect(self._massage_customer_key_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_add_massage_customer.clicked.connect(self._add_massage_customer)
        self.ui.toolButton_add_prescript.clicked.connect(self._add_prescript)
        self.ui.toolButton_remove_prescript.clicked.connect(self._remove_prescript)
        self.ui.tableWidget_massage_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.toolButton_add_payment.clicked.connect(self._add_payment)
        self.ui.toolButton_remove_payment.clicked.connect(self._remove_payment)
        self.ui.tableWidget_massage_payment.itemChanged.connect(self._payment_item_changed)
        self.ui.keyPressEvent = self._key_pressed

    # override key press event
    def _key_pressed(self, event):
        key = event.key()

        if key in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Escape]:
            return

        return QtWidgets.QDialog.keyPressEvent(self.ui, event)

    def accepted_button_clicked(self):
        if self.massage_case_key is None:
            self._insert_records()
        else:
            self._update_records()

        self.close()

    def _set_combo_box(self):
        massager_list = personnel_utils.get_person(self.massage_database, '推拿師父')
        ui_utils.set_combo_box(self.ui.comboBox_massager, massager_list)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)

    def _set_table_width(self):
        width = [100, 100, 100, 260, 60, 60, 100, 100, 150]
        self.table_widget_massage_prescript.set_table_heading_width(width)
        width = [100, 100, 260, 100, 300]
        self.table_widget_massage_payment.set_table_heading_width(width)

    def _insert_records(self):
        massage_case_key = self._insert_massage_cases()
        self._insert_massage_prescript(massage_case_key)
        self._insert_massage_payment(massage_case_key)

    def _insert_massage_cases(self):
        fields = [
            'MassageCustomerKey', 'Name', 'CaseDate', 'FinishDate', 'Period',
            'InsType', 'TreatType',
            'Massager', 'Registrar', 'DesignatedMassager', 'Remark',
            'SelfTotalFee', 'TotalFee', 'ReceiptFee',
        ]

        date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd')
        start_time = self.ui.timeEdit_start_time.time().toString('hh:mm:ss')
        end_time = self.ui.timeEdit_end_time.time().toString('hh:mm:ss')

        start_date = f'{date} {start_time}'
        end_date = f'{date} {end_time}'

        if self.ui.checkBox_designated_massager.isChecked():
            designated_massager = 'True'
        else:
            designated_massager = 'False'

        total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee.text())
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())

        data = [
            self.ui.lineEdit_massage_customer_key.text(),
            self.ui.lineEdit_name.text(),
            start_date,
            end_date,
            self.ui.comboBox_period.currentText(),
            '自費',
            '養生館',
            self.ui.comboBox_massager.currentText(),
            self.system_settings.field('使用者'),
            designated_massager,
            self.ui.textEdit_remark.toPlainText(),
            total_fee,
            total_fee,
            receipt_fee,
        ]

        last_row_id = self.massage_database.insert_record('massage_cases', fields, data)

        return last_row_id

    def _insert_massage_prescript(self, massage_case_key):
        fields = [
            'MassageCaseKey', 'MedicineKey', 'MedicineName',
            'Quantity', 'Unit', 'Price', 'Amount', 'Remark',

        ]
        for row_no in range(self.ui.tableWidget_massage_prescript.rowCount()):
            data = [
                massage_case_key,
                self.ui.tableWidget_massage_prescript.item(row_no, 2).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 3).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 4).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 5).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 6).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 7).text(),
                self.ui.tableWidget_massage_prescript.item(row_no, 8).text(),
            ]
            self.massage_database.insert_record('massage_prescript', fields, data)

    def _insert_massage_payment(self, massage_case_key):
        fields = [
            'MassageCaseKey', 'PaymentType', 'Amount', 'Remark',
        ]
        for row_no in range(self.ui.tableWidget_massage_payment.rowCount()):
            data = [
                massage_case_key,
                self.ui.tableWidget_massage_payment.item(row_no, 2).text(),
                self.ui.tableWidget_massage_payment.item(row_no, 3).text(),
                self.ui.tableWidget_massage_payment.item(row_no, 4).text(),
            ]
            self.massage_database.insert_record('massage_payment', fields, data)

    def _preset_reservation(self):
        reservation_date = datetime.datetime.strptime(self.reservation_date, '%Y-%m-%d').date()
        self.ui.dateEdit_reservation_date.setDate(reservation_date)
        self.comboBox_period.setCurrentText(self.period)

        start_time = datetime.datetime.strptime(self.start_time, '%H:%M').time()
        self.ui.timeEdit_start_time.setTime(start_time)
        end_time = datetime.datetime.strptime(self.end_time, '%H:%M').time()
        self.ui.timeEdit_end_time.setTime(end_time)

        self.ui.comboBox_massager.setCurrentText(self.massager)

    def _set_group_box(self, enabled):
        self.ui.lineEdit_name.setEnabled(enabled)
        self.ui.lineEdit_id.setEnabled(enabled)
        self.ui.lineEdit_birthday.setEnabled(enabled)
        self.ui.lineEdit_gender.setEnabled(enabled)
        self.ui.lineEdit_telephone.setEnabled(enabled)
        self.ui.lineEdit_cellphone.setEnabled(enabled)
        self.ui.lineEdit_address.setEnabled(enabled)
        self.ui.lineEdit_remark.setEnabled(enabled)

        self.ui.label_name.setEnabled(enabled)
        self.ui.label_id.setEnabled(enabled)
        self.ui.label_birthday.setEnabled(enabled)
        self.ui.label_gender.setEnabled(enabled)
        self.ui.label_telephone.setEnabled(enabled)
        self.ui.label_cellphone.setEnabled(enabled)
        self.ui.label_address.setEnabled(enabled)
        self.ui.label_remark.setEnabled(enabled)

    def _clear_massage_customer_data(self):
        self.ui.lineEdit_name.setText('')
        self.ui.lineEdit_id.setText('')
        self.ui.lineEdit_birthday.setText('')
        self.ui.lineEdit_gender.setText('')
        self.ui.lineEdit_telephone.setText('')
        self.ui.lineEdit_cellphone.setText('')
        self.ui.lineEdit_address.setText('')
        self.ui.lineEdit_remark.setText('')

    def _get_massage_customer(self):
        keyword = self.ui.lineEdit_massage_customer_key.text()
        massage_customer_key = patient_utils.get_patient_by_keyword(
            self, self.massage_database, self.system_settings,
            'massage_customer', 'MassageCustomerKey', keyword
        )
        if massage_customer_key in ['', None]:
            return

        self._set_line_edit_massage_customer_data(massage_customer_key)

    def _massage_customer_key_changed(self):
        keyword = self.ui.lineEdit_massage_customer_key.text()
        button_ok = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)

        if keyword == '':
            self._clear_massage_customer_data()
            self._set_group_box(False)
            button_ok.setEnabled(False)
            return

        if keyword.isdigit() and len(keyword) <= 6:
            massage_customer_key = keyword
            self._set_line_edit_massage_customer_data(massage_customer_key)

        if self.ui.lineEdit_name.text() != '':
            button_ok.setEnabled(True)

    def _set_line_edit_massage_customer_data(self, massage_customer_key):
        self.ui.lineEdit_massage_customer_key.setText(string_utils.xstr(massage_customer_key))

        if self.ui.radioButton_massage_customer.isChecked():
            key_field = 'MassageCustomerKey'
            sql = f'''
                SELECT * FROM massage_customer
                WHERE
                    MassageCustomerKey = {massage_customer_key}
            '''
            rows = self.massage_database.select_record(sql)
        else:
            key_field = 'PatientKey'
            sql = f'''
                SELECT * FROM patient
                WHERE
                    PatientKey = {massage_customer_key}
            '''
            rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        self._set_massage_customer_data(row, key_field)
        self._set_group_box(True)

    def _set_massage_customer_data(self, row, key_field):
        self.ui.lineEdit_massage_customer_key.setText(string_utils.xstr(row[key_field]))
        self.ui.lineEdit_name.setText(string_utils.xstr(row['Name']))
        self.ui.lineEdit_id.setText(string_utils.xstr(row['ID']))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row['Birthday']))
        self.ui.lineEdit_gender.setText(string_utils.xstr(row['Gender']))
        self.ui.lineEdit_telephone.setText(string_utils.xstr(row['Telephone']))
        self.ui.lineEdit_cellphone.setText(string_utils.xstr(row['Cellphone']))
        self.ui.lineEdit_address.setText(string_utils.xstr(row['Address']))
        self.ui.lineEdit_remark.setText(string_utils.xstr(row['Remark']))

    def _add_massage_customer(self):
        dialog = dialog_utils.get_dialog_patient(
            self, self.massage_database, self.system_settings, None,
        )
        if dialog.exec_():
            massage_customer_key = dialog.last_row_id
        else:
            massage_customer_key = None

        dialog.close_all()
        dialog.deleteLater()

        if massage_customer_key is not None:
            self.ui.lineEdit_massage_customer_key.setText(string_utils.xstr(massage_customer_key))

    def _read_massage_customer(self, massage_customer_key):
        sql = f'''
            SELECT * FROM massage_customer
            WHERE
                MassageCustomerKey = {massage_customer_key}
        '''
        rows = self.massage_database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self._set_massage_customer_data(row)
        self._set_group_box(True)

    def _read_reservation(self):
        self._read_massage_cases()

        self._read_massage_prescript()
        self.calculate_total_fee()

        self._read_massage_payment()
        self._calculate_receipt_fee()

    def _read_massage_cases(self):
        sql = f'''
            SELECT * FROM massage_cases
            WHERE
                MassageCaseKey = {self.massage_case_key}
        '''
        rows = self.massage_database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self._read_massage_customer(row['MassageCustomerKey'])
        self._set_reservation(row)

    def _set_reservation(self, row):
        reservation_date = row['CaseDate'].date()
        start_time = row['CaseDate'].time()
        end_time = row['FinishDate'].time()
        period = string_utils.xstr(row['Period'])
        massager = string_utils.xstr(row['Massager'])
        remark = string_utils.get_str(row['Remark'], 'utf8')
        designated_massage = string_utils.xstr(row['DesignatedMassager'])

        if designated_massage == 'True':
            self.ui.checkBox_designated_massager.setChecked(True)

        self.ui.dateEdit_reservation_date.setDate(reservation_date)
        self.comboBox_period.setCurrentText(string_utils.xstr(period))
        self.ui.timeEdit_start_time.setTime(start_time)
        self.ui.timeEdit_end_time.setTime(end_time)

        self.ui.comboBox_massager.setCurrentText(massager)
        self.ui.textEdit_remark.setText(remark)

    def _read_massage_prescript(self):
        sql = f'''
            SELECT * FROM massage_prescript
            WHERE
                MassageCaseKey = {self.massage_case_key}
            ORDER BY MassagePrescriptKey
        '''
        self.table_widget_massage_prescript.set_db_data(sql, self._set_massage_prescript_table)

    def _set_massage_prescript_table(self, row_no, row):
        prescript_row = [
            string_utils.xstr(row['MassagePrescriptKey']),
            string_utils.xstr(row['MassageCaseKey']),
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineName']),
            number_utils.get_float(row['Quantity']),
            string_utils.xstr(row['Unit']),
            number_utils.get_float(row['Price']),
            number_utils.get_float(row['Amount']),
            string_utils.xstr(row['Remark']),
        ]

        for col_no in range(len(prescript_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, prescript_row[col_no])

            self.ui.tableWidget_massage_prescript.setItem(row_no, col_no, item)
            if col_no in [4, 6, 7]:
                self.ui.tableWidget_massage_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5]:
                self.ui.tableWidget_massage_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if col_no not in [4, 8]:
                self.ui.tableWidget_massage_prescript.item(row_no, col_no).setFlags(
                    QtCore.Qt.ItemIsEnabled
                )

    def _read_massage_payment(self):
        sql = f'''
            SELECT * FROM massage_payment
            WHERE
                MassageCaseKey = {self.massage_case_key}
            ORDER BY MassagePaymentKey
        '''
        self.table_widget_massage_payment.set_db_data(sql, self._set_massage_payment_table)

    def _set_massage_payment_table(self, row_no, row):
        massage_payment_row = [
            string_utils.xstr(row['MassagePaymentKey']),
            string_utils.xstr(row['MassageCaseKey']),
            string_utils.xstr(row['PaymentType']),
            number_utils.get_float(row['Amount']),
            string_utils.xstr(row['Remark']),
        ]
        self._set_massage_payment_row(massage_payment_row, row_no)

    def _set_massage_payment_row(self, massage_payment_row, row_no):
        for col_no in range(len(massage_payment_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, massage_payment_row[col_no])

            self.ui.tableWidget_massage_payment.setItem(row_no, col_no, item)
            if col_no in [3]:
                self.ui.tableWidget_massage_payment.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            if col_no not in [3, 4]:
                self.ui.tableWidget_massage_payment.item(row_no, col_no).setFlags(
                    QtCore.Qt.ItemIsEnabled
                )

        self._calculate_receipt_fee()

    def _update_records(self):
        self._update_massage_cases()

        self.massage_database.delete_record('massage_prescript', 'MassageCaseKey', self.massage_case_key)
        self.massage_database.delete_record('payment', 'MassageCaseKey', self.massage_case_key)
        self._insert_massage_prescript(self.massage_case_key)
        self._insert_massage_payment(self.massage_case_key)

    def _update_massage_cases(self):
        fields = [
            'MassageCustomerKey', 'Name', 'CaseDate', 'FinishDate', 'Period',
            'Massager', 'Registrar', 'DesignatedMassager', 'Remark',
            'SelfTotalFee', 'TotalFee', 'ReceiptFee'
        ]

        date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd')
        start_time = self.ui.timeEdit_start_time.time().toString('hh:mm:ss')
        end_time = self.ui.timeEdit_end_time.time().toString('hh:mm:ss')

        start_date = f'{date} {start_time}'
        end_date = f'{date} {end_time}'

        if self.ui.checkBox_designated_massager.isChecked():
            designated_massager = 'True'
        else:
            designated_massager = 'False'

        total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee.text())
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())

        data = [
            self.ui.lineEdit_massage_customer_key.text(),
            self.ui.lineEdit_name.text(),
            start_date,
            end_date,
            self.ui.comboBox_period.currentText(),
            self.ui.comboBox_massager.currentText(),
            self.system_settings.field('使用者'),
            designated_massager,
            self.ui.textEdit_remark.toPlainText(),
            total_fee,
            total_fee,
            receipt_fee,
        ]

        self.massage_database.update_record('massage_cases', fields, 'MassageCaseKey', self.massage_case_key, data)

    def _add_prescript(self):
        dialog = dialog_utils.get_dialog_medicine(
            self, self.massage_database, self.system_settings,
            self.ui.tableWidget_massage_prescript, None, '養生館',
        )
        dialog.exec_()
        dialog.deleteLater()

    def _remove_prescript(self):
        self.ui.tableWidget_massage_prescript.removeRow(self.ui.tableWidget_massage_prescript.currentRow())
        self.calculate_total_fee()

    def calculate_total_fee(self):
        total_fee = 0
        for row_no in range(self.ui.tableWidget_massage_prescript.rowCount()):
            item = self.ui.tableWidget_massage_prescript.item(row_no, 7)
            if item is None:
                continue

            total_fee += number_utils.get_float(item.text())

        total_fee = number_utils.round_up(total_fee)
        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))

    def _calculate_receipt_fee(self):
        receipt_fee = 0
        for row_no in range(self.ui.tableWidget_massage_payment.rowCount()):
            item = self.ui.tableWidget_massage_payment.item(row_no, 3)
            if item is None:
                continue

            receipt_fee += number_utils.get_float(item.text())

        receipt_fee = number_utils.round_up(receipt_fee)
        self.ui.lineEdit_receipt_fee.setText(string_utils.xstr(receipt_fee))

    def _prescript_item_changed(self, item):
        if item is None:
            return

        row_no = item.row()
        col_no = item.column()
        if col_no != 4:
            return

        price = self.ui.tableWidget_massage_prescript.item(row_no, 6)
        if price is None:
            return

        quantity = item.text()
        price = price.text()
        amount = number_utils.get_integer(quantity) * number_utils.get_integer(price)

        amount_col_no = 7
        self.ui.tableWidget_massage_prescript.setItem(
            row_no, amount_col_no,
            QtWidgets.QTableWidgetItem(string_utils.xstr(amount))
        )
        self.ui.tableWidget_massage_prescript.item(
            row_no, amount_col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        self.ui.tableWidget_massage_prescript.item(row_no, amount_col_no).setFlags(
            QtCore.Qt.ItemIsEnabled
        )

        if col_no not in [4, 8]:
            self.ui.tableWidget_massage_prescript.item(row_no, col_no).setFlags(
                QtCore.Qt.ItemIsEnabled
            )

        self.calculate_total_fee()

    def _add_payment(self):
        input_dialog = dialog_utils.get_dialog(
            '付款方式', '請選擇付款方式',
            None, QInputDialog.TextInput, 320, 200)
        input_dialog.setComboBoxItems(massage_utils.PAYMENT_ITEMS)
        ok = input_dialog.exec_()

        if not ok:
            return

        item = input_dialog.textValue()

        self.ui.tableWidget_massage_payment.setRowCount(
            self.ui.tableWidget_massage_payment.rowCount() + 1
        )
        massage_payment_row = [
            None,
            None,
            item,
            None,
            None,
        ]
        row_no = self.ui.tableWidget_massage_payment.rowCount() - 1
        self._set_massage_payment_row(massage_payment_row, row_no)

    def _remove_payment(self):
        self.ui.tableWidget_massage_payment.removeRow(self.ui.tableWidget_massage_payment.currentRow())
        self._calculate_receipt_fee()

    def _payment_item_changed(self):
        self._calculate_receipt_fee()

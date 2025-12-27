
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import personnel_utils
from libs import registration_utils
from libs import string_utils
from libs import patient_utils


# 新增盤點記錄
class DialogAddReturnGoods(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogAddReturnGoods, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.return_goods_key = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()

        if self.return_goods_key is not None:
            self._set_return_goods_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_ADD_RETURN_GOODS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        period = registration_utils.get_current_period(self.system_settings)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, period)
        ui_utils.set_combo_box(
            self.ui.comboBox_cashier,
            personnel_utils.get_person(self.database, '全部'),
        )
        self.ui.dateEdit_return_goods_date.setDate(datetime.datetime.today())

    def _check_return_goods_fee_completed(self):
        quantity = self.ui.lineEdit_quantity.text()
        amount = self.ui.lineEdit_amount.text()

        if (quantity != '' and amount != ''):
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def _set_return_goods_data(self):
        sql = f'''
            SELECT * FROM returngoods
            WHERE
                ReturnGoodsKey = {self.return_goods_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.dateEdit_return_goods_date.setDate(row['ReturnGoodsDate'])
        self.ui.comboBox_period.setCurrentText(string_utils.xstr(row['Period']))
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(row['PatientKey']))
        self.ui.lineEdit_name.setText(string_utils.xstr(row['Name']))
        self.ui.lineEdit_item_name.setText(string_utils.xstr(row['ItemName']))
        self.ui.lineEdit_quantity.setText(string_utils.xstr(row['Quantity']))
        self.ui.lineEdit_amount.setText(string_utils.xstr(row['Amount']))
        self.ui.lineEdit_reason.setText(string_utils.xstr(row['ReturnGoodsReason']))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.lineEdit_quantity.textChanged.connect(self._check_return_goods_fee_completed)
        self.ui.lineEdit_amount.textChanged.connect(self._check_return_goods_fee_completed)
        self.ui.lineEdit_patient_key.returnPressed.connect(self._get_patient)
        self.ui.lineEdit_patient_key.textChanged.connect(self._patient_key_changed)

    def accepted_button_clicked(self):
        if self.return_goods_key is None:
            self._insert_return_goods()
        else:
            self._update_return_goods()

    def _insert_return_goods(self):
        fields = [
            'ReturnGoodsDate', 'Period', 'PatientKey', 'Name', 'ItemName',
            'Quantity', 'Amount', 'ReturnGoodsReason', 'Cashier',
        ]
        data = [
            self.ui.dateEdit_return_goods_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_period.currentText(),
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            self.ui.lineEdit_item_name.text(),
            self.ui.lineEdit_quantity.text(),
            self.ui.lineEdit_amount.text(),
            self.ui.lineEdit_reason.text(),
            self.ui.comboBox_cashier.currentText(),
        ]
        self.return_goods_key = self.database.insert_record('returngoods', fields, data)

    def _update_return_goods(self):
        fields = [
            'ReturnGoodsDate', 'Period', 'PatientKey', 'Name', 'ItemName',
            'Quantity', 'Amount', 'ReturnGoodsReason', 'Cashier',
        ]
        data = [
            self.ui.dateEdit_return_goods_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_period.currentText(),
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            self.ui.lineEdit_item_name.text(),
            self.ui.lineEdit_quantity.text(),
            self.ui.lineEdit_amount.text(),
            self.ui.lineEdit_reason.text(),
            self.ui.comboBox_cashier.currentText(),
        ]
        self.database.update_record('returngoods', fields, 'ReturnGoodsKey', self.return_goods_key, data)

    def _get_patient(self):
        keyword = self.ui.lineEdit_patient_key.text().strip()

        patient_key = patient_utils.get_patient_by_keyword(
            self, self.database, self.system_settings,
            'patient', 'PatientKey', keyword
        )
        if patient_key in ['', None]:
            return

        self._set_line_edit_patient_data(patient_key)

    def _set_line_edit_patient_data(self, patient_key):
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))

        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.lineEdit_name.setText(string_utils.xstr(row['Name']))

    def _patient_key_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text().strip()

        if patient_key == '':
            self.ui.lineEdit_name.setText(None)
            return

        if patient_key.isdigit() and len(patient_key) <= 6:
            self._set_line_edit_patient_data(patient_key)
        else:
            self.ui.lineEdit_name.setText(None)

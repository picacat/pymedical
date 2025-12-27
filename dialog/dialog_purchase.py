
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import dialog_utils


# 自購藥
class DialogPurchase(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPurchase, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.medicine_key = None
        self.medicine_type = None
        self.set_medicine = True

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PURCHASE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_dict.clicked.connect(self._dict_medicine_clicked)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.spinBox_quantity.valueChanged.connect(self._calculate_fee)
        self.ui.spinBox_discount.valueChanged.connect(self._calculate_fee)

    def accepted_button_clicked(self):
        pass

    def rejected_button_clicked(self):
        self.set_medicine = False
        self.close()

    def _dict_medicine_clicked(self):
        self.medicine_key = None
        self.medicine_type = None

        dialog = dialog_utils.get_dialog_medicine(
            self, self.database, self.system_settings, None, 2, '藥品')
        dialog.exec()
        dialog.deleteLater()

        medicine_row = dialog.get_medicine()
        if medicine_row is None:
            return

        self.medicine_key = medicine_row['medicine_key']
        self.medicine_type = medicine_row['medicine_type']
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {self.medicine_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        if self.ui.spinBox_quantity.value() == 0:
            self.ui.spinBox_quantity.setValue(1)

        row = rows[0]
        price = number_utils.get_float(row['SalePrice'])

        self.ui.lineEdit_medicine_name.setText(string_utils.xstr(row['MedicineName']))
        self.ui.lineEdit_unit.setText(string_utils.xstr(row['Unit']))
        self.ui.lineEdit_price.setText(string_utils.get_formatted_str('單價', price))

        self._calculate_fee()

    def _calculate_fee(self):
        quantity = self.ui.spinBox_quantity.value()
        price = number_utils.get_float(self.ui.lineEdit_price.text())
        amount = quantity * price

        discount = self.ui.spinBox_discount.value()
        total_fee = amount - discount

        self.ui.lineEdit_amount.setText(string_utils.get_formatted_str('單價', amount))
        self.ui.lineEdit_total_fee.setText(string_utils.get_formatted_str('單價', total_fee))
        self.ui.lineEdit_receipt_fee.setText(string_utils.get_formatted_str('單價', total_fee))

    def get_medicine(self):
        if not self.set_medicine:
            medicine_row = None
        else:
            medicine_row = {
                'medicine_key': self.medicine_key,
                'medicine_type': self.medicine_type,
                'medicine_name': self.ui.lineEdit_medicine_name.text(),
                'unit': self.ui.lineEdit_unit.text(),
                'quantity': self.ui.spinBox_quantity.value(),
                'price': self.ui.lineEdit_price.text(),
                'amount': self.ui.lineEdit_amount.text(),
                'discount': self.ui.spinBox_discount.value(),
                'total_fee': self.ui.lineEdit_total_fee.text(),
                'receipt_fee': self.ui.lineEdit_receipt_fee.text(),
                'promotion': self.ui.checkBox_promotion.isChecked(),
            }

        return medicine_row


# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import personnel_utils
from libs import purchase_utils
from libs import dialog_utils
from libs import number_utils
from libs import string_utils
from libs import case_utils


# 換貨
class DialogExchangeGoods(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExchangeGoods, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_key = args[3]
        self.medicine_set = args[4]
        self.medicine_name = args[5]
        self.quantity = args[6]
        self.invoice_no = args[7]
        self.receipt_fee = args[8]
        self.ui = None

        self.receipt_fee = number_utils.get_integer(self.receipt_fee)

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.prescript_column = {
            'MedicineKey': 0,
            'MedicineType': 1,
            'Promotion': 2,
            'MedicineName': 3,
            'Unit': 4,
            'Quantity': 5,
            'Price': 6,
            'Amount': 7,
            'DiscountFee': 8,
            'Remove': 9,
        }

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXCHANGE_GOODS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_prescript = class_utils.get_table_widget(self.ui.tableWidget_prescript, self.database)
        self.ui.tableWidget_prescript.setAlternatingRowColors(True)

        if self.invoice_no in ['', None]:
            self.ui.toolButton_course.setEnabled(False)

        self.ui.lineEdit_medicine_name.setText(self.medicine_name)
        self.dateEdit_exchange_date.setDate(datetime.datetime.now())

        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)
        if pres_days <= 0:
            pres_days = 1

        if pres_days == 1:
            self.receipt_fee /= self.quantity
        else:
            self.receipt_fee /= pres_days

        self.ui.lineEdit_receipt_fee.setText(string_utils.xstr(self.receipt_fee))
        self._set_combo_box()
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_dict.clicked.connect(self._open_dictionary)
        self.ui.toolButton_course.clicked.connect(self._open_purchase_course_list)
        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.spinBox_quantity.valueChanged.connect(self._spin_box_quantity_changed)

    def _spin_box_quantity_changed(self):
        total_amount = self.ui.spinBox_quantity.value() * self.receipt_fee
        self.ui.lineEdit_receipt_fee.setText(string_utils.xstr(total_amount))

    def _check_prescript_count(self):
        if self.ui.tableWidget_prescript.rowCount() > 0:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def _calculate_exchange_amount(self):
        total_amount = 0

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(row_no, 7)
            if item is None:
                continue

            total_amount += number_utils.get_integer(item.text())

        self.ui.lineEdit_amount.setText(string_utils.xstr(total_amount))
        total_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
        if total_amount < total_fee:
            message = f'<font color="darkGreen">金額不足{total_fee}, 須退還{total_fee - total_amount}元</font>'
        elif total_amount > total_fee:
            message = f'<font color="red">金額超過{total_fee}, 須補差額{total_amount - total_fee}元</font>'
        else:
            message = '金額正確'

        self.ui.label_message.setText(message)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100, 100,
            50, 220, 50, 60, 70, 80, 70, 50
        ]
        self.table_widget_prescript.set_table_heading_width(width)
        self.table_widget_prescript.set_column_hidden([0, 1])

    def _set_combo_box(self):
        items = personnel_utils.get_person(self.database, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_dealer, items)
        self.ui.comboBox_dealer.setCurrentText(self.user_name)

    def accepted_button_clicked(self):
        if self.ui.label_message.text() != '金額正確':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '換貨金額不平衡', self.ui.label_message.text(),
                '請注意換貨金額不平衡'
            )

    def _open_dictionary(self):
        dialog = dialog_utils.get_dialog_medicine(
            self, self.database, self.system_settings, self.ui.tableWidget_prescript, 2, '藥品',
        )
        dialog.exec_()
        dialog.deleteLater()

    def insert_prescript_row(self, medicine_row):
        medicine_key = medicine_row['MedicineKey']

        extra_process = [self._check_prescript_count, self._calculate_exchange_amount]
        purchase_utils.insert_prescript_row(
            self.database, self.ui.tableWidget_prescript, medicine_key, extra_process, cancel_button=True)
        self._check_prescript_count()

    def _prescript_item_changed(self, item):
        self._calculate_exchange_amount()

        if item is None:
            return

        purchase_utils.prescript_item_changed(self.ui.tableWidget_prescript, item)

    def _open_purchase_course_list(self):
        dialog = dialog_utils.get_dialog_purchase_course_list(
            self, self.database, self.system_settings, self.case_key, self.medicine_key, self.invoice_no)
        dialog.exec_()
        dialog.deleteLater()

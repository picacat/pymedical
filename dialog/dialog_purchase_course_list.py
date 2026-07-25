
# 療程商品消費記錄 2021-10-24
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils


# 主視窗
class DialogPurchaseCourseList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPurchaseCourseList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_key = args[3]
        self.invoice_no = args[4]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_purchase_course()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PURCHASE_COURSE_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('關閉')
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database
        )
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [130, 250, 50, 100, 100]
        self.table_widget_prescript.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _read_purchase_course(self):
        sql = f'''
            SELECT prescript.*, cases.CaseDate AS PurchaseDate FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                MedicineKey = {self.medicine_key} AND
                cases.InvoiceNo = "{self.invoice_no}"
            ORDER BY cases.CaseDate
        '''
        self.table_widget_prescript.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        prescrpt_record = [
            string_utils.xstr(row['PurchaseDate'].date()),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['Dosage']),
            string_utils.xstr(row['Price']),
            string_utils.xstr(row['Amount']),
        ]

        for col_no in range(len(prescrpt_record)):
            self.ui.tableWidget_prescript.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(prescrpt_record[col_no])
            )
            if col_no in [2, 3, 4]:
                self.ui.tableWidget_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

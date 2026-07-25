
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import number_utils
from libs import string_utils


# 主視窗
class DialogCertificateItems(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCertificateItems, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.in_table_widget_certificate_items = args[2]
        self.correct_list = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._set_certificate_items()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CERTIFICATE_ITEMS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('更新自費金額')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_certificate_items = class_utils.get_table_widget(
            self.ui.tableWidget_certificate_items, self.database
        )
        self.table_widget_certificate_items.set_column_hidden([0, 1])
        width = [100, 100, 120, 60, 80, 80, 80, 80, 80, 80, 80, 80, 100]
        self.table_widget_certificate_items.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def _set_certificate_items(self):
        in_row_count = self.in_table_widget_certificate_items.rowCount() - 1

        self.ui.tableWidget_certificate_items.setRowCount(in_row_count)
        for row_no in range(in_row_count):
            case_key = self.in_table_widget_certificate_items.item(row_no, 1).text()
            total_fee = number_utils.get_integer(self.in_table_widget_certificate_items.item(row_no, 9).text())
            correct_fee = total_fee
            for item in self.correct_list:
                if item[1] == case_key:
                    correct_fee = item[2]

            certificate_items_row = [
                self.in_table_widget_certificate_items.item(row_no, 0).text(),
                case_key,
                self.in_table_widget_certificate_items.item(row_no, 2).text(),
                self.in_table_widget_certificate_items.item(row_no, 3).text(),
                self.in_table_widget_certificate_items.item(row_no, 4).text(),
                self.in_table_widget_certificate_items.item(row_no, 5).text(),
                self.in_table_widget_certificate_items.item(row_no, 6).text(),
                self.in_table_widget_certificate_items.item(row_no, 7).text(),
                self.in_table_widget_certificate_items.item(row_no, 8).text(),
                string_utils.xstr(total_fee),
                string_utils.xstr(correct_fee),
                self.in_table_widget_certificate_items.item(row_no, 10).text(),
                self.in_table_widget_certificate_items.item(row_no, 11).text(),
            ]
            for col_no in range(len(certificate_items_row)):
                self.ui.tableWidget_certificate_items.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(certificate_items_row[col_no])
                )
                if col_no in [4, 5, 6, 7, 8, 9, 10, 11]:
                    self.ui.tableWidget_certificate_items.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                elif col_no in [3]:
                    self.ui.tableWidget_certificate_items.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )
                if total_fee != correct_fee:
                    self.ui.tableWidget_certificate_items.item(row_no, col_no).setForeground(
                        QtGui.QColor('red')
                    )

    def accepted_button_clicked(self):
        self._correct_certificate_items()

    def _correct_certificate_items(self):
        for row_no in range(self.ui.tableWidget_certificate_items.rowCount()):
            total_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 9).text())
            correct_fee = number_utils.get_integer(self.ui.tableWidget_certificate_items.item(row_no, 10).text())
            if total_fee == correct_fee:
                continue

            certificate_items_key = self.ui.tableWidget_certificate_items.item(row_no, 0).text()
            sql = f'''
                SELECT * FROM certificate_items
                WHERE
                    CertificateItemsKey = {certificate_items_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            row = rows[0]
            discount_fee = number_utils.get_integer(row['DiscountFee'])
            fields = [
                'SelfTotalFee', 'TotalFee',
            ]
            data = [
                correct_fee + discount_fee,
                correct_fee,
            ]

            self.database.update_record(
                'certificate_items', fields, 'CertificateItemsKey', certificate_items_key, data,
            )

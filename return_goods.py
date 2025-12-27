
# 欠還款作業 2022.09.28
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog
import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import personnel_utils
from libs import dialog_utils
from libs import export_utils
from libs import date_utils


# 退貨 2024.05.01 同安
class ReturnGoods(QtWidgets.QMainWindow):
    program_name = '退貨'

    # 初始化
    def __init__(self, parent=None, *args):
        super(ReturnGoods, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()
        self.read_return_goods()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_RETURN_GOODS, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_return_goods = class_utils.get_table_widget(self.ui.tableWidget_return_goods, self.database)
        self.table_widget_return_goods.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_return_goods)
        self.ui.action_return_goods.triggered.connect(self.add_return_goods)
        self.ui.action_modify_return_goods.triggered.connect(self._modify_return_goods)
        self.ui.action_remove_return_goods.triggered.connect(self._remove_return_goods)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)
        self.ui.tableWidget_return_goods.doubleClicked.connect(self._modify_return_goods)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_to_excel.setEnabled(False)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 150, 80, 100, 120, 400, 100, 100, 480, 120]
        self.table_widget_return_goods.set_table_heading_width(width)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_return_goods(self):
        self.close_all()
        self.close_tab()

    def read_return_goods(self):
        sql = '''
            SELECT * FROM returngoods
            ORDER BY ReturnGoodsDate DESC
        '''
        self.table_widget_return_goods.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        quantity = number_utils.get_float(row['Quantity'])
        amount = number_utils.get_integer(row['Amount'])

        return_goods_row = [
            string_utils.xstr(row['ReturnGoodsKey']),
            string_utils.xstr(row['ReturnGoodsDate'].strftime('%Y-%m-%d')),
            string_utils.xstr(row['Period']),
            row['PatientKey'],
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['ItemName']),
            quantity,
            amount,
            string_utils.xstr(row['ReturnGoodsReason']),
            string_utils.xstr(row['Cashier']),
        ]

        for col_no in range(len(return_goods_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, return_goods_row[col_no])

            self.ui.tableWidget_return_goods.setItem(row_no, col_no, item)
            if col_no in [3, 6, 7]:
                self.ui.tableWidget_return_goods.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_return_goods.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def add_return_goods(self):
        dialog = dialog_utils.get_dialog_add_return_goods(
            self, self.database, self.system_settings, None
        )

        if dialog.exec_():
            self.read_return_goods()

        dialog.close_all()
        dialog.deleteLater()

    def _modify_return_goods(self):
        key = self.table_widget_return_goods.field_value(0)
        dialog = dialog_utils.get_dialog_add_return_goods(
            self, self.database, self.system_settings, key
        )

        if dialog.exec_():
            self.read_return_goods()

        dialog.close_all()
        dialog.deleteLater()

    def _remove_return_goods(self):
        msg_box = dialog_utils.get_message_box(
            '刪除退貨資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆退貨資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_return_goods.field_value(0)
        self.database.delete_record('returngoods', 'ReturnGoodsKey', key)
        self.ui.tableWidget_return_goods.removeRow(self.ui.tableWidget_return_goods.currentRow())

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel檔案", f'{self.system_settings.field("院所名稱")}退貨資料.xlsx',
            "excel檔案 (*.xlsx)",
            options=options
        )

        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_return_goods, [0], [3, 6, 7]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            'Excel資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Excel檔案格式.'
        )

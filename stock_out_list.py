
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox
import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils
from libs import stock_utils
from libs import number_utils


#  出貨-出貨資料  2023.04.05
class StockOutList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockOutList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.read_stock_out()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_OUT_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_stock_out_list = class_utils.get_table_widget(
            self.ui.tableWidget_stock_out_list, self.database
        )
        self._set_table_width()
        self.table_widget_stock_out_list.set_column_hidden([0])

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_stock.clicked.connect(self._add_stock)
        self.ui.toolButton_remove_stock.clicked.connect(self._remove_stock)
        self.ui.toolButton_edit_stock.clicked.connect(self._edit_stock)
        self.ui.tableWidget_stock_out_list.doubleClicked.connect(self._edit_stock)
        self.ui.tableWidget_stock_out_list.itemSelectionChanged.connect(self._stock_out_list_selection_changed)
        self.ui.lineEdit_query.textChanged.connect(self._query_stock)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 150, 200, 200, 250, 100, 120, 100, 120, 250, 130]
        self.table_widget_stock_out_list.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        current_tab.close_all()
        current_tab.deleteLater()

    def _calculate_total(self):
        total_fee = 0
        col_no = 5
        for row_no in range(self.ui.tableWidget_stock_out_list.rowCount()):
            if self.ui.tableWidget_stock_out_list.item(row_no, col_no) is None:
                continue

            total_fee += number_utils.get_integer(self.ui.tableWidget_stock_out_list.item(row_no, col_no).text())

        self.ui.tableWidget_stock_out_list.setRowCount(self.ui.tableWidget_stock_out_list.rowCount()+1)

        row_no = self.ui.tableWidget_stock_out_list.rowCount() - 1
        self.ui.tableWidget_stock_out_list.setItem(
            row_no, 4, QtWidgets.QTableWidgetItem('合計')
        )
        self.ui.tableWidget_stock_out_list.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(f'{total_fee:,}')
        )
        self.ui.tableWidget_stock_out_list.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def read_stock_out(self, sql=None):
        if sql is None:
            sql = '''
                SELECT * FROM stockout
                ORDER BY StockOutKey DESC
            '''

        self.table_widget_stock_out_list.set_db_data(sql, self._set_db_data)
        self._calculate_total()
        self._stock_out_list_selection_changed()

    def _set_db_data(self, row_no, row):
        amount = f'{number_utils.get_integer(row["Amount"]):,}'

        stock_row = [
            string_utils.xstr(row['StockOutKey']),
            string_utils.xstr(row['StockOutDate']),
            string_utils.xstr(row['OrderNo']),
            string_utils.xstr(row['InvoiceNo']),
            string_utils.xstr(row['Client']),
            amount,
            string_utils.xstr(row['PaymentType']),
            string_utils.xstr(row['Paid']),
            string_utils.xstr(row['Attn']),
            string_utils.xstr(row['Remark']),
            string_utils.xstr(row['AdjustDate']),
        ]

        for col_no in range(len(stock_row)):
            self.ui.tableWidget_stock_out_list.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(stock_row[col_no])
            )
            if col_no in [5]:
                self.ui.tableWidget_stock_out_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _query_stock(self):
        keywords = self.ui.lineEdit_query.text().split()
        if len(keywords) <= 0:
            self.read_stock_out()
            return

        condition = []
        for keyword in keywords:
            condition.append(f'''
                (OrderNo LIKE "{keyword}%" OR
                 InvoiceNo LIKE "%{keyword}%" OR
                 Client LIKE "%{keyword}%" OR
                 Attn LIKE "%{keyword}%" OR
                 Remark LIKE "%{keyword}%")
            ''')

        condition = ' AND '.join(condition)
        sql = f'''
            SELECT * FROM stockout
            WHERE
                {condition}
            ORDER BY StockOutKey DESC
        '''
        self.read_stock_out(sql)
        self.ui.lineEdit_query.setFocus(True)
        self.ui.lineEdit_query.setCursorPosition(len(self.ui.lineEdit_query.text()))

    # 新增出貨
    def _add_stock(self):
        self.parent.add_stock_out(None, None)

    # 刪除出貨
    def _remove_stock(self):
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆出貨單資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        stock_out_key = self.table_widget_stock_out_list.field_value(0)

        if self.system_settings.field('調整庫存量') == '即時調整':
            stock_utils.restore_stock_quantity(self.database, stock_out_key)

        self.database.delete_record('stockout', 'StockOutKey', stock_out_key)
        self.ui.tableWidget_stock_out_list.removeRow(self.ui.tableWidget_stock_out_list.currentRow())

    # 編輯出貨資料
    def _edit_stock(self):
        stock_out_key = self.table_widget_stock_out_list.field_value(0)
        order_no = self.table_widget_stock_out_list.field_value(2)
        self.parent.add_stock_out(order_no, stock_out_key)

    def update_stock(self):
        msg_box = QtWidgets.QMessageBox()
        msg_box.setIcon(QtWidgets.QMessageBox.Warning)
        msg_box.setWindowTitle('準備過帳')
        msg_box.setText("""
            <font size='4' color='red'>
                <b>確定開始調整處方庫存量?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料過帳後, 將無法回復!")
        msg_box.addButton(QtWidgets.QPushButton("取消"), QtWidgets.QMessageBox.NoRole)
        msg_box.addButton(QtWidgets.QPushButton("確定"), QtWidgets.QMessageBox.YesRole)
        update_record = msg_box.exec_()
        if not update_record:
            return

        stock_out_key = self.table_widget_stock_out_list.field_value(0)
        stock_utils.adjust_stock_out_quantity(self.database, stock_out_key)
        sql = f'''
            UPDATE stockout
            SET
                AdjustDate = "{datetime.datetime.now().strftime('%Y-%m-%d')}"
            WHERE
                StockOutKey = {stock_out_key}
        '''
        self.database.exec_sql(sql)
        row = self.database.select_record(f'SELECT * FROM stockout WHERE StockOutKey = {stock_out_key}')[0]
        self._set_db_data(self.ui.tableWidget_stock_out_list.currentRow(), row)
        self._stock_out_list_selection_changed()

        system_utils.show_message_box(
            QMessageBox.Information,
            '過帳完成',
            '<h3>出貨單資料過帳完成.</h3>',
            '庫存量已調整.'
        )

    def _stock_out_list_selection_changed(self):
        self.parent.action_update_stock.setEnabled(True)

        customer = self.table_widget_stock_out_list.field_value(4)
        adjust_date = self.table_widget_stock_out_list.field_value(10)

        if customer == '合計' or adjust_date not in ['', None]:
            self.parent.action_update_stock.setEnabled(False)
            return

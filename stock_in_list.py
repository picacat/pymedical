
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import datetime
import calendar

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils
from libs import stock_utils
from libs import export_utils
from libs import date_utils
from libs import number_utils


#  進貨-進貨資料  2022.11.19
class StockInList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockInList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.read_stock_in()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_IN_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_stock_in_list = class_utils.get_table_widget(
            self.ui.tableWidget_stock_in_list, self.database
        )
        self._set_table_width()
        self.table_widget_stock_in_list.set_column_hidden([0])

        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        last_day = calendar.monthrange(year, month)[1]

        start_date = date_utils.str_to_date(f'{year}-{month:0>2}-01')
        end_date = date_utils.str_to_date(f'{year}-{month:0>2}-{last_day:0>2}')
        self.ui.dateEdit_start_date.setDate(start_date)
        self.ui.dateEdit_end_date.setDate(end_date)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_stock.clicked.connect(self._add_stock)
        self.ui.toolButton_remove_stock.clicked.connect(self._remove_stock)
        self.ui.toolButton_edit_stock.clicked.connect(self._edit_stock)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_stock_in_list.doubleClicked.connect(self._edit_stock)
        self.ui.tableWidget_stock_in_list.itemSelectionChanged.connect(self._stock_in_list_selection_changed)
        self.ui.lineEdit_query.textChanged.connect(self._query_stock)
        self.ui.dateEdit_start_date.dateChanged.connect(lambda: self.read_stock_in())
        self.ui.dateEdit_end_date.dateChanged.connect(lambda: self.read_stock_in())

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 150, 200, 200, 250, 100, 120, 120, 350, 150]
        self.table_widget_stock_in_list.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        current_tab.close_all()
        current_tab.deleteLater()

    def _calculate_total(self):
        total_fee = 0
        col_no = 5
        for row_no in range(self.ui.tableWidget_stock_in_list.rowCount()):
            if self.ui.tableWidget_stock_in_list.item(row_no, col_no) is None:
                continue

            amount = self.ui.tableWidget_stock_in_list.item(row_no, col_no).text()
            amount = amount.replace(',', '')
            total_fee += number_utils.get_float(amount)

        self.ui.tableWidget_stock_in_list.setRowCount(self.ui.tableWidget_stock_in_list.rowCount()+1)

        row_no = self.ui.tableWidget_stock_in_list.rowCount() - 1
        self.ui.tableWidget_stock_in_list.setItem(
            row_no, 4, QtWidgets.QTableWidgetItem('合計')
        )
        self.ui.tableWidget_stock_in_list.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(f'{total_fee:,}')
        )
        self.ui.tableWidget_stock_in_list.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def read_stock_in(self, sql=None):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd')

        if sql is None:
            sql = f'''
                SELECT * FROM stockin
                WHERE
                    StockInDate BETWEEN "{start_date}" AND "{end_date}"
                ORDER BY StockInDate DESC
            '''

        self.table_widget_stock_in_list.set_db_data(sql, self._set_db_data)
        self._calculate_total()
        self._stock_in_list_selection_changed()

    def _set_db_data(self, row_no, row):
        amount = f'{number_utils.get_float(row["Amount"]):,.1f}'

        stock_row = [
            string_utils.xstr(row['StockInKey']),
            string_utils.xstr(row['StockInDate']),
            string_utils.xstr(row['OrderNo']),
            string_utils.xstr(row['InvoiceNo']),
            string_utils.xstr(row['Supplier']),
            amount,
            string_utils.xstr(row['PaymentType']),
            string_utils.xstr(row['Attn']),
            string_utils.xstr(row['Remark']),
            string_utils.xstr(row['StoreDate']),
        ]

        for col_no in range(len(stock_row)):
            self.ui.tableWidget_stock_in_list.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(stock_row[col_no])
            )
            if col_no in [5]:
                self.ui.tableWidget_stock_in_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _query_stock(self):
        keywords = self.ui.lineEdit_query.text().split()
        if len(keywords) <= 0:
            self.read_stock_in()
            return

        condition = []
        for keyword in keywords:
            condition.append(f'''
                (OrderNo LIKE "{keyword}%" OR
                 InvoiceNo LIKE "%{keyword}%" OR
                 Supplier LIKE "%{keyword}%" OR
                 Attn LIKE "%{keyword}%" OR
                 Remark LIKE "%{keyword}%")
            ''')

        condition = ' AND '.join(condition)
        sql = f'''
            SELECT * FROM stockin
            WHERE
                {condition}
            ORDER BY StockInKey DESC
        '''
        self.read_stock_in(sql)
        self.ui.lineEdit_query.setFocus(True)
        self.ui.lineEdit_query.setCursorPosition(len(self.ui.lineEdit_query.text()))

    # 新增廠商資料
    def _add_stock(self):
        self.parent.add_stock_in(None, None)

    # 移除通訊錄資料
    def _remove_stock(self):
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆進貨單資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        stock_in_key = self.table_widget_stock_in_list.field_value(0)

        if self.system_settings.field('調整庫存量') == '即時調整':
            stock_utils.restore_stock_quantity(self.database, stock_in_key)

        self.database.delete_record('stockinitems', 'StockInKey', stock_in_key)
        self.database.delete_record('stockin', 'StockInKey', stock_in_key)
        self.ui.tableWidget_stock_in_list.removeRow(self.ui.tableWidget_stock_in_list.currentRow())

    # 編輯院所資料
    def _edit_stock(self):
        stock_in_key = self.table_widget_stock_in_list.field_value(0)
        order_no = self.table_widget_stock_in_list.field_value(2)
        self.parent.add_stock_in(order_no, stock_in_key)

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel檔案", f'{self.system_settings.field("院所名稱")}進貨資料.xlsx',
            "excel檔案 (*.xlsx)",
            options=options
        )

        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_stock_in_list, [0], [5],
            column_width=[20, 20, 20, 30, 10, 20, 10, 40]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            'Excel資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Excel檔案格式.'
        )

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

        stock_in_key = self.table_widget_stock_in_list.field_value(0)
        stock_utils.adjust_stock_quantity(self.database, self.system_settings, stock_in_key)
        sql = f'''
            UPDATE stockin
            SET
                StoreDate = "{datetime.datetime.now().strftime('%Y-%m-%d')}"
            WHERE
                StockInKey = {stock_in_key}
        '''
        self.database.exec_sql(sql)
        row = self.database.select_record(f'SELECT * FROM stockin WHERE StockInKey = {stock_in_key}')[0]
        self._set_db_data(self.ui.tableWidget_stock_in_list.currentRow(), row)
        self._stock_in_list_selection_changed()

        system_utils.show_message_box(
            QMessageBox.Information,
            '過帳完成',
            '<h3>進貨單資料過帳完成.</h3>',
            '庫存量已調整.'
        )

    def _stock_in_list_selection_changed(self):
        self.parent.action_update_stock.setEnabled(True)

        supplier = self.table_widget_stock_in_list.field_value(4)
        archived_date = self.table_widget_stock_in_list.field_value(9)

        if supplier == '合計' or archived_date not in ['', None]:
            self.parent.action_update_stock.setEnabled(False)
            return

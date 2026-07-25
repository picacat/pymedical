# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (class_utils, dialog_utils, export_utils, number_utils,
                  system_utils, ui_utils)


# 補貨 2022.11.19 誠泰
class StockReplenishment(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockReplenishment, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._calculate_stock()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_REPLENISHMENT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self._set_table_width()
        self.table_widget_medicine.set_column_hidden([0])

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100,
            120, 280, 70, 100, 100, 100, 120, 150, 280, 120, 80, 100
        ]
        self.table_widget_medicine.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_medicine.doubleClicked.connect(self._edit_medicine)        

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    def _edit_medicine(self):
        medicine_key = self.table_widget_medicine.field_value(0)
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, None, medicine_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        self._calculate_stock()
        
    def _calculate_stock(self):
        sql = '''
            SELECT
                MedicineKey, MedicineType, MedicineName, Unit, Location, SafeQuantity, Quantity
            FROM medicine
            WHERE
                SafeQuantity > 0 AND
                Quantity IS NOT NULL AND Quantity < SafeQuantity
            ORDER BY MedicineType, MedicineKey
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_db_data)

    def _set_db_data(self, row_no, row):
        medicine_key = row['MedicineKey']
        stock_in_row = self._get_stock_in_row(medicine_key)
        try:
            stock_in_date = stock_in_row['stock_in_date'].strftime('%Y-%m-%d')
        except Exception:
            stock_in_date = None

        medicine_row = [
            medicine_key,
            row['MedicineType'],
            row['MedicineName'],
            row['Unit'],
            row['Location'],
            number_utils.get_integer(row['SafeQuantity']),
            number_utils.get_integer(row['Quantity']),
            stock_in_date,
            stock_in_row['supplier'],
            stock_in_row['product_name'],
            stock_in_row['unit'],
            number_utils.get_integer(stock_in_row['unit_price']),
            number_utils.get_integer(stock_in_row['quantity']),
        ]

        for col_no, field in enumerate(medicine_row):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_medicine.setItem(row_no, col_no, item)

            if item is None:
                continue

            if col_no in [3]:
                self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5, 6, 11, 12]:
                self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _get_stock_in_row(self, medicine_key):
        stock_in_row = {
            'stock_in_date': None,
            'supplier': None,
            'product_name': None,
            'unit': None,
            'unit_price': None,
            'quantity': None,
        }
        sql = f'''
            SELECT stockin.*, stockinitems.* FROM stockinitems
                LEFT JOIN stockin ON stockinitems.StockInKey = stockin.StockInKey
            WHERE
                MedicineKey = {medicine_key}
            ORDER BY StockInDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return stock_in_row

        row = rows[0]
        stock_in_row['stock_in_date'] = row['StockInDate']
        stock_in_row['supplier'] = row['Supplier']
        stock_in_row['product_name'] = row['ProductName']
        stock_in_row['unit'] = row['Unit']
        stock_in_row['unit_price'] = row['UnitPrice']
        stock_in_row['quantity'] = row['Quantity']

        return stock_in_row

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出診斷證明書",
            f'補貨清單.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medicine, [0], [5, 6, 11, 12]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

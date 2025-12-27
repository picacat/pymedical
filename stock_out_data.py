
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (class_utils, dialog_utils, number_utils, stock_utils,
                  string_utils, system_utils, ui_utils)


#  出貨-輸入出貨資料  2023.04.06
class StockOutData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockOutData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.stock_out_key = args[2]
        self.ui = None

        self.item_col_no = {
            'stock_out_key': 0,
            'medicine_key': 1,
            'medicine_type': 2,
            'medicine_name': 3,
            'medicine_unit': 4,
            'product_no': 5,
            'product_name': 6,
            'unit': 7,
            'unit_quantity': 8,
            'unit_price': 9,
            'quantity': 10,
            'amount': 11,
            'remark': 12,
        }

        self._set_ui()
        self._set_signal()

        if self.stock_out_key is not None:
            self._read_stock_out_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_OUT_DATA, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_stock_out_items = class_utils.get_table_widget(
            self.ui.tableWidget_stock_out_items, self.database
        )
        self._set_table_width()
        self.table_widget_stock_out_items.set_column_hidden([
            self.item_col_no['stock_out_key'], self.item_col_no['medicine_key']
        ])

        self.ui.dateEdit_stock_out_date.setDate(datetime.datetime.now())
        ui_utils.set_combo_box(self.ui.comboBox_payment_type, stock_utils.PAYMENT_TYPE_LIST, None)

    def _get_supplier_list(self):
        sql = '''
            SELECT Supplier FROM stockin
            WHERE
                Supplier IS NOT NULL AND LENGTH(Supplier) > 0
            GROUP BY Supplier
        '''
        rows = self.database.select_record(sql)

        supplier_list = []
        for row in rows:
            supplier_list.append(string_utils.xstr(row['Supplier']))

        return supplier_list

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_save.clicked.connect(self._save_stock_out_data)
        self.ui.pushButton_close.clicked.connect(self.close_tab)
        self.ui.toolButton_add_item.clicked.connect(self._add_stock_out_item)
        self.ui.toolButton_remove_item.clicked.connect(self._remove_stock_out_item)
        self.ui.toolButton_edit_medicine.clicked.connect(self._edit_medicine)                
        self.ui.tableWidget_stock_out_items.itemChanged.connect(self._item_changed)
        self.ui.tableWidget_stock_out_items.doubleClicked.connect(self._edit_medicine)
        
    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100, 100,
            100, 300, 80, 150, 300, 100, 80, 80, 80, 80, 300]
        self.table_widget_stock_out_items.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_stock.currentIndex()
        self.parent.close_stock_tab(current_tab)

    def _edit_medicine(self):
        medicine_key = self.table_widget_stock_out_items.field_value(1)
        if medicine_key is None:
            return
        
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, None, medicine_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _add_stock_out_item(self):
        dialog = dialog_utils.get_dialog_medicine(
            self, self.database, self.system_settings, '進貨單', None, '藥品'
        )
        dialog.exec_()
        dialog.deleteLater()

    def _remove_stock_out_item(self):
        msg_box = dialog_utils.get_message_box(
            '刪除資料', QMessageBox.Warning,
            '<font size="3" color="red"><b>確定刪除此筆進貨項目?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        current_row = self.ui.tableWidget_stock_out_items.currentRow()
        self.ui.tableWidget_stock_out_items.removeRow(current_row)

    def insert_prescript_row(self, row):
        row_no = self.ui.tableWidget_stock_out_items.rowCount()
        self.ui.tableWidget_stock_out_items.setRowCount(row_no+1)

        medicine_type = string_utils.xstr(row['MedicineType'])
        if medicine_type == '單方':
            unit_quantity = 100
            product_unit = '罐'
        elif medicine_type == '複方':
            unit_quantity = 200
            product_unit = '罐'
        else:
            unit_quantity = None
            product_unit = None

        medicine_row = [
            None, row['MedicineKey'], medicine_type, row['MedicineName'], row['Unit'],
            None, row['MedicineName'], product_unit, unit_quantity,
        ]

        for col_no, field in enumerate(medicine_row):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_out_items.setItem(row_no, col_no, item)

            if col_no in [
                self.item_col_no['medicine_type'],
                self.item_col_no['medicine_name'],
                self.item_col_no['medicine_unit'],
            ]:
                item.setFlags(QtCore.Qt.ItemIsEnabled)

            if col_no in [
                self.item_col_no['medicine_unit'],
                self.item_col_no['unit'],
            ]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [
                self.item_col_no['unit_quantity'],
            ]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        self.ui.tableWidget_stock_out_items.setCurrentCell(row_no, self.item_col_no['product_no'])
        self.ui.tableWidget_stock_out_items.resizeRowsToContents()

    def _item_changed(self, item):
        if item is None:
            return

        row_no = self.ui.tableWidget_stock_out_items.currentRow()
        col_no = item.column()

        if col_no == self.item_col_no['product_no']:
            try:
                product_no = item.text()
            except Exception:
                return

            self._auto_completion_product(product_no)
        elif col_no in [self.item_col_no['quantity'], self.item_col_no['unit_price']]:
            try:
                unit_price = number_utils.get_integer(
                    self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['unit_price']).text())
            except Exception:
                unit_price = 0

            try:
                quantity = number_utils.get_integer(
                    self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['quantity']).text())
            except Exception:
                quantity = 0

            amount = quantity * unit_price

            amount_item = QtWidgets.QTableWidgetItem()
            amount_item.setData(QtCore.Qt.EditRole, amount)
            self.ui.tableWidget_stock_out_items.setItem(row_no, self.item_col_no['amount'], amount_item)

            for col_no in [
                self.item_col_no['unit_quantity'],
                self.item_col_no['unit_price'],
                self.item_col_no['quantity'],
                self.item_col_no['amount'],
            ]:
                item = self.ui.tableWidget_stock_out_items.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

                if col_no in [self.item_col_no['amount']]:
                    item.setFlags(QtCore.Qt.ItemIsEnabled)

            self._calculate_total_amount()

    def _calculate_total_amount(self):
        row_count = self.ui.tableWidget_stock_out_items.rowCount()

        subtotal = 0
        for row_no in range(row_count):
            amount = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['amount'])
            if amount is None:
                continue

            subtotal += number_utils.get_integer(amount.text())

        self.ui.lineEdit_total_amount.setText(string_utils.xstr(subtotal))

    def _auto_completion_product(self, product_no):
        product_row = self._get_product_row(product_no)
        if product_row is None:
            return

        item_record = [
            None, None, None, None, None, None,
            product_row['ProductName'],
            product_row['Unit'],
            product_row['UnitQuantity'],
            product_row['UnitPrice'],
        ]

        row_no = self.ui.tableWidget_stock_out_items.currentRow()
        for col_no, field in enumerate(item_record):
            if field is None:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_out_items.setItem(row_no, col_no, item)
            if col_no in [self.item_col_no['unit']]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [
                self.item_col_no['unit_quantity'],
                self.item_col_no['unit_price'],
                self.item_col_no['quantity'],
            ]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        self.ui.tableWidget_stock_out_items.setCurrentCell(row_no, self.item_col_no['quantity'])

    def _get_product_row(self, product_no):
        sql = f'''
            SELECT * FROM stockinitems
            WHERE
                ProductNo = "{product_no}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _read_stock_out_data(self):
        self._read_stock_out()
        self._read_stock_out_items()

    def _read_stock_out(self):
        sql = f'''
            SELECT * FROM stockout
            WHERE
                StockOutKey = {self.stock_out_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.ui.dateEdit_stock_out_date.setDate(row['StockOutDate'])
        self.ui.comboBox_client.setCurrentText(string_utils.xstr(row['Client']))
        self.ui.comboBox_attn.setCurrentText(string_utils.xstr(row['Attn']))
        self.ui.lineEdit_order_no.setText(string_utils.xstr(row['OrderNo']))
        self.ui.lineEdit_remark.setText(string_utils.xstr(row['Remark']))
        self.ui.lineEdit_invoice_no.setText(string_utils.xstr(row['InvoiceNo']))
        self.ui.comboBox_payment_type.setCurrentText(string_utils.xstr(row['PaymentType']))
        self.ui.lineEdit_total_amount.setText(string_utils.xstr(row['Amount']))

    def _read_stock_out_items(self):
        self.ui.tableWidget_stock_out_items.itemChanged.disconnect()

        sql = f'''
            SELECT * from stockoutitems
            WHERE
                StockOutKey = {self.stock_out_key}
            ORDER BY StockOutItemsKey
        '''

        self.table_widget_stock_out_items.set_db_data(sql, self._set_table_data)
        self.ui.tableWidget_stock_out_items.itemChanged.connect(self._item_changed)

    def _set_table_data(self, row_no, row):
        medicine_key = row['MedicineKey']
        medicine_row = self._get_medicine_row(medicine_key)

        stock_in_items_record = [
            row['StockOutItemsKey'],
            row['MedicineKey'],
            medicine_row['MedicineType'],
            row['MedicineName'],
            medicine_row['Unit'],
            row['ProductNo'],
            row['ProductName'],
            row['Unit'],
            row['UnitQuantity'],
            row['UnitPrice'],
            row['Quantity'],
            row['Amount'],
            row['Remark'],
        ]

        for col_no, field in enumerate(stock_in_items_record):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_out_items.setItem(row_no, col_no, item)
            if col_no in [
                self.item_col_no['medicine_unit'],
                self.item_col_no['unit'],
            ]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [
                self.item_col_no['unit_quantity'],
                self.item_col_no['unit_price'],
                self.item_col_no['quantity'],
                self.item_col_no['amount'],
            ]:
                self.ui.tableWidget_stock_out_items.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            if col_no in [
                self.item_col_no['medicine_type'],
                self.item_col_no['medicine_name'],
                self.item_col_no['medicine_unit'],
                self.item_col_no['amount'],
            ]:
                item.setFlags(QtCore.Qt.ItemIsEnabled)

    def _get_medicine_row(self, medicine_key):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = "{medicine_key}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _save_stock_out_data(self):
        if self.stock_out_key is not None:
            stock_out_key = self.stock_out_key
            self._update_record()
        else:
            stock_out_key = self._insert_record()

        if self.system_settings.field('調整庫存量') == '即時調整':
            stock_utils.adjust_stock_out_quantity(self.database, stock_out_key)

        self.parent.tab_stock_out_list.read_stock_out()
        self.close_tab()

    def _update_record(self):
        self._update_stock_out()
        self._update_stock_out_items()

    def _update_stock_out(self):
        fields = [
            'StockOutDate', 'Client', 'Attn', 'OrderNo', 'Remark', 'InvoiceNo', 'PaymentType', 'Amount']
        data = [
            self.ui.dateEdit_stock_out_date.date().toString('yyyy-MM-dd'),
            self.ui.comboBox_client.currentText(),
            self.ui.comboBox_attn.currentText(),
            self.ui.lineEdit_order_no.text(),
            self.ui.lineEdit_remark.text(),
            self.ui.lineEdit_invoice_no.text(),
            self.ui.comboBox_payment_type.currentText(),
            self.ui.lineEdit_total_amount.text(),
        ]
        self.database.update_record('stockout', fields, 'StockOutKey', self.stock_out_key, data)

    def _update_stock_out_items(self):
        # if self.system_settings.field('調整庫存量') == '即時調整':
        #     stock_utils.restore_stock_quantity(self.database, self.stock_out_key)

        self.database.delete_record('stockoutitems', 'StockOutKey', self.stock_out_key)
        self._insert_stock_out_items(self.stock_out_key)

    def _insert_record(self):
        stock_out_key = self._insert_stock_out()
        self._insert_stock_out_items(stock_out_key)

        return stock_out_key

    def _insert_stock_out(self):
        fields = [
            'StockOutDate', 'OrderNo', 'Amount', 'InvoiceNo', 'PaymentType',
            'Client', 'Attn', 'Remark']
        data = [
            self.ui.dateEdit_stock_out_date.date().toString('yyyy-MM-dd'),
            self.ui.lineEdit_order_no.text(),
            self.ui.lineEdit_total_amount.text(),
            self.ui.lineEdit_invoice_no.text(),
            self.ui.comboBox_payment_type.currentText(),
            self.ui.comboBox_client.currentText(),
            self.ui.comboBox_attn.currentText(),
            self.ui.lineEdit_remark.text(),
        ]
        stock_in_key = self.database.insert_record('stockout', fields, data)

        return stock_in_key

    def _insert_stock_out_items(self, stock_out_key):
        fields = [
            'StockOutKey', 'MedicineKey', 'MedicineName', 'ProductNo',  'ProductName',
            'Unit', 'UnitQuantity', 'Quantity', 'UnitPrice', 'Amount', 'Remark',
        ]

        for row_no in range(self.ui.tableWidget_stock_out_items.rowCount()):
            medicine_key = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['medicine_key']).text()
            medicine_name = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['medicine_name']).text()
            try:
                product_no = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['product_no']).text()
            except Exception:
                product_no = None

            try:
                product_name = self.ui.tableWidget_stock_out_items.item(
                    row_no, self.item_col_no['product_name']).text()
            except Exception:
                product_name = None

            try:
                unit = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['unit']).text()
            except Exception:
                unit = None

            try:
                unit_quantity = self.ui.tableWidget_stock_out_items.item(
                    row_no, self.item_col_no['unit_quantity']).text()
            except Exception:
                unit_quantity = None

            try:
                unit_price = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['unit_price']).text()
            except Exception:
                unit_price = None

            try:
                quantity = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['quantity']).text()
            except Exception:
                quantity = None

            try:
                amount = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['amount']).text()
            except Exception:
                amount = None

            try:
                remark = self.ui.tableWidget_stock_out_items.item(row_no, self.item_col_no['remark']).text()
            except Exception:
                remark = None

            data = [
                stock_out_key, medicine_key, medicine_name, product_no, product_name,
                unit, unit_quantity, quantity, unit_price, amount, remark,
            ]

            self.database.insert_record('stockoutitems', fields, data)

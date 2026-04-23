# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    class_utils,
    dialog_utils,
    number_utils,
    stock_utils,
    string_utils,
    system_utils,
    ui_utils,
)


#  進貨-輸入進貨資料  2022.11.20
class StockInData(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockInData, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.stock_in_key = args[2]
        self.ui = None

        self.item_col_no = {
            "stock_in_key": 0,
            "medicine_key": 1,
            "medicine_type": 2,
            "medicine_name": 3,
            "medicine_unit": 4,
            "product_no": 5,
            "product_name": 6,
            "unit": 7,
            "unit_quantity": 8,
            "unit_price": 9,
            "quantity": 10,
            "amount": 11,
            "remark": 12,
        }

        self._set_ui()
        self._set_signal()

        if self.stock_in_key is not None:
            self._read_stock_in_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_IN_DATA, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_stock_in_items = class_utils.get_table_widget(
            self.ui.tableWidget_stock_in_items, self.database
        )
        self._set_table_width()
        self.table_widget_stock_in_items.set_column_hidden(
            [self.item_col_no["stock_in_key"], self.item_col_no["medicine_key"]]
        )

        self.ui.dateEdit_stock_in_date.setDate(datetime.datetime.now())
        supplier_list = self._get_supplier_list()
        ui_utils.set_combo_box(self.ui.comboBox_supplier, supplier_list, None)
        ui_utils.set_combo_box(
            self.ui.comboBox_payment_type, stock_utils.PAYMENT_TYPE_LIST, None
        )

    def _get_supplier_list(self):
        sql = """
            SELECT Supplier FROM stockin
            WHERE
                Supplier IS NOT NULL AND LENGTH(Supplier) > 0
            GROUP BY Supplier
        """
        rows = self.database.select_record(sql)

        supplier_list = []
        for row in rows:
            supplier_list.append(string_utils.xstr(row["Supplier"]))

        sql = """
            SELECT Name FROM supplier
            WHERE
                Name IS NOT NULL AND LENGTH(Name) > 0
            GROUP BY Name
        """
        rows = self.database.select_record(sql)
        for row in rows:
            supplier_list.append(string_utils.xstr(row["Name"]))

        return supplier_list

    # 設定信號
    def _set_signal(self):
        self.ui.pushButton_save.clicked.connect(self._save_stock_in_data)
        self.ui.pushButton_close.clicked.connect(self.close_tab)
        self.ui.toolButton_add_item.clicked.connect(self._add_stock_in_item)
        self.ui.toolButton_remove_item.clicked.connect(self._remove_stock_in_item)
        self.ui.toolButton_edit_medicine.clicked.connect(self._edit_medicine)
        self.ui.tableWidget_stock_in_items.itemChanged.connect(self._item_changed)
        self.ui.tableWidget_stock_in_items.doubleClicked.connect(self._edit_medicine)
        self.ui.comboBox_supplier.currentTextChanged.connect(self._supplier_changed)

    def _edit_medicine(self):
        medicine_key = self.table_widget_stock_in_items.field_value(1)
        if medicine_key is None:
            return

        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, None, medicine_key
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _supplier_changed(self):
        supplier = self.ui.comboBox_supplier.currentText()
        sql = f'''
            SELECT Attn FROM stockin
            WHERE
                Supplier = "{supplier}" AND
                Attn IS NOT NULL AND LENGTH(Attn) > 0
            GROUP BY Attn
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            ui_utils.set_combo_box(self.ui.comboBox_attn, [], None)
            return

        attn_list = []
        for row in rows:
            attn_list.append(string_utils.xstr(row["Attn"]))

        ui_utils.set_combo_box(self.ui.comboBox_attn, attn_list, None)

        if len(attn_list) > 0:
            self.ui.comboBox_attn.setCurrentText(attn_list[0])
            self.ui.lineEdit_order_no.setFocus()
        else:
            self.ui.comboBox_attn.setFocus()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 100, 300, 80, 150, 300, 100, 80, 80, 80, 80, 300]
        self.table_widget_stock_in_items.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_stock.currentIndex()
        self.parent.close_stock_tab(current_tab)

    def _add_stock_in_item(self):
        dialog = dialog_utils.get_dialog_medicine(
            self, self.database, self.system_settings, "進貨單", None, "藥品"
        )
        dialog.exec_()
        dialog.deleteLater()

    def _remove_stock_in_item(self):
        msg_box = dialog_utils.get_message_box(
            "刪除資料",
            QMessageBox.Warning,
            '<font size="3" color="red"><b>確定刪除此筆進貨項目?</b></font>',
            "注意！資料刪除後, 將無法回復!",
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        current_row = self.ui.tableWidget_stock_in_items.currentRow()
        self.ui.tableWidget_stock_in_items.removeRow(current_row)

    def insert_prescript_row(self, row):
        medicine_key = row["MedicineKey"]
        row = self._get_medicine_row(medicine_key)
        if row is None:
            return

        medicine_name = string_utils.xstr(row["MedicineName"])
        medicine_type = string_utils.xstr(row["MedicineType"])

        product_no = None
        product_name = medicine_name

        row_no = self.ui.tableWidget_stock_in_items.rowCount()
        self.ui.tableWidget_stock_in_items.setRowCount(row_no + 1)
        try:
            in_price = number_utils.get_float(row["InPrice"])
        except Exception:
            in_price = 0

        try:
            sale_price = number_utils.get_float(row["SalePrice"])
        except Exception:
            sale_price = 0

        if in_price > 0:
            unit_price = in_price
        elif sale_price > 0:
            unit_price = sale_price
        else:
            unit_price = None

        if medicine_type == "單方":
            unit_quantity = 100
            product_unit = "罐"
        elif medicine_type == "複方":
            unit_quantity = 200
            product_unit = "罐"
        else:
            unit_quantity = 1
            product_unit = row["Unit"]

        medicine_row = [
            None,
            medicine_key,
            medicine_type,
            medicine_name,
            row["Unit"],
            product_no,
            product_name,
            product_unit,
            unit_quantity,
            unit_price,
        ]

        for col_no, field in enumerate(medicine_row):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_in_items.setItem(row_no, col_no, item)

            if col_no in [
                self.item_col_no["medicine_type"],
                self.item_col_no["medicine_name"],
                self.item_col_no["medicine_unit"],
            ]:
                item.setFlags(QtCore.Qt.ItemIsEnabled)

            if col_no in [self.item_col_no["medicine_unit"], self.item_col_no["unit"]]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            elif col_no in [
                self.item_col_no["unit_quantity"],
                self.item_col_no["unit_price"],
            ]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_stock_in_items.setCurrentCell(
            row_no, self.item_col_no["quantity"]
        )
        self._auto_completion_product(row_no, medicine_key)

        self.ui.tableWidget_stock_in_items.resizeRowsToContents()
        self.ui.tableWidget_stock_in_items.setFocus()

    def _auto_completion_product(self, row_no, medicine_key):
        row = self._get_product_row(medicine_key)
        if row is None:
            return

        product_no = string_utils.xstr(row["ProductNo"])
        product_name = string_utils.xstr(row["ProductName"])
        product_unit = string_utils.xstr(row["Unit"])
        unit_quantity = row["UnitQuantity"]
        unit_price = row["UnitPrice"]

        item_record = [
            None,
            None,
            None,
            None,
            None,
            product_no,
            product_name,
            product_unit,
            unit_quantity,
            unit_price,
        ]

        for col_no, field in enumerate(item_record):
            if field is None:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_in_items.setItem(row_no, col_no, item)
            if col_no in [self.item_col_no["unit"]]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            elif col_no in [
                self.item_col_no["unit_quantity"],
                self.item_col_no["unit_price"],
                self.item_col_no["quantity"],
            ]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_stock_in_items.setCurrentCell(
            row_no, self.item_col_no["quantity"]
        )

    def _get_product_row(self, medicine_key):
        supplier = self.ui.comboBox_supplier.currentText()

        if supplier == "":
            return

        sql = f'''
            SELECT * FROM stockinitems
            LEFT JOIN stockin ON stockinitems.StockInKey = stockin.StockInKey
            WHERE
                stockin.Supplier = "{supplier}" AND
                MedicineKey = {medicine_key}
            ORDER BY StockInItemsKey DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _item_changed(self, item):
        if item is None:
            return

        row_no = self.ui.tableWidget_stock_in_items.currentRow()
        col_no = item.column()

        if col_no in [self.item_col_no["quantity"], self.item_col_no["unit_price"]]:
            try:
                unit_price = number_utils.get_float(
                    self.ui.tableWidget_stock_in_items.item(
                        row_no, self.item_col_no["unit_price"]
                    ).text()
                )
            except Exception:
                unit_price = 0
                return

            try:
                quantity = number_utils.get_float(
                    self.ui.tableWidget_stock_in_items.item(
                        row_no, self.item_col_no["quantity"]
                    ).text()
                )
            except Exception:
                quantity = 0

            amount = quantity * unit_price
            amount_item = QtWidgets.QTableWidgetItem()
            amount_item.setData(QtCore.Qt.EditRole, amount)
            self.ui.tableWidget_stock_in_items.setItem(
                row_no, self.item_col_no["amount"], amount_item
            )

            for col_no in [
                self.item_col_no["unit_quantity"],
                self.item_col_no["unit_price"],
                self.item_col_no["quantity"],
                self.item_col_no["amount"],
            ]:
                item = self.ui.tableWidget_stock_in_items.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

                if col_no in [self.item_col_no["amount"]]:
                    item.setFlags(QtCore.Qt.ItemIsEnabled)

            self._calculate_total_amount()

    def _calculate_total_amount(self):
        row_count = self.ui.tableWidget_stock_in_items.rowCount()

        subtotal = 0
        for row_no in range(row_count):
            amount = self.ui.tableWidget_stock_in_items.item(
                row_no, self.item_col_no["amount"]
            )
            if amount is None:
                continue

            subtotal += number_utils.get_float(amount.text())

        self.ui.lineEdit_total_amount.setText(f"{subtotal:.1f}")

    def _read_stock_in_data(self):
        self._read_stock_in()
        self._read_stock_in_items()

    def _read_stock_in(self):
        sql = f"""
            SELECT * FROM stockin
            WHERE
                StockInKey = {self.stock_in_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        amount = number_utils.get_float(row["Amount"])
        self.ui.dateEdit_stock_in_date.setDate(row["StockInDate"])
        self.ui.comboBox_supplier.setCurrentText(string_utils.xstr(row["Supplier"]))
        self.ui.lineEdit_order_no.setText(string_utils.xstr(row["OrderNo"]))
        self.ui.comboBox_attn.setCurrentText(string_utils.xstr(row["Attn"]))
        self.ui.lineEdit_remark.setText(string_utils.xstr(row["Remark"]))
        self.ui.lineEdit_invoice_no.setText(string_utils.xstr(row["InvoiceNo"]))
        self.ui.comboBox_payment_type.setCurrentText(
            string_utils.xstr(row["PaymentType"])
        )
        self.ui.lineEdit_total_amount.setText(f"{amount:.1f}")

    def _read_stock_in_items(self):
        self.ui.tableWidget_stock_in_items.itemChanged.disconnect()

        sql = f"""
            SELECT * from stockinitems
            WHERE
                StockInKey = {self.stock_in_key}
            ORDER BY StockInItemsKey
        """

        self.table_widget_stock_in_items.set_db_data(sql, self._set_table_data)
        self.ui.tableWidget_stock_in_items.itemChanged.connect(self._item_changed)

    def _set_table_data(self, row_no, row):
        medicine_key = row["MedicineKey"]
        medicine_row = self._get_medicine_row(medicine_key)

        if medicine_row is None:
            medicine_type = "已刪除"
            unit = "已刪除"
        else:
            medicine_type = medicine_row["MedicineType"]
            unit = medicine_row["Unit"]

        stock_in_items_record = [
            row["StockInItemsKey"],
            row["MedicineKey"],
            medicine_type,
            row["MedicineName"],
            unit,
            row["ProductNo"],
            row["ProductName"],
            row["Unit"],
            row["UnitQuantity"],
            number_utils.get_float(row["UnitPrice"]),
            number_utils.get_float(row["Quantity"]),
            number_utils.get_float(row["Amount"]),
            row["Remark"],
        ]

        for col_no, field in enumerate(stock_in_items_record):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_in_items.setItem(row_no, col_no, item)
            if col_no in [
                self.item_col_no["medicine_unit"],
                self.item_col_no["unit"],
            ]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            elif col_no in [
                self.item_col_no["unit_quantity"],
                self.item_col_no["unit_price"],
                self.item_col_no["quantity"],
                self.item_col_no["amount"],
            ]:
                self.ui.tableWidget_stock_in_items.item(
                    row_no, col_no
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            if col_no in [
                self.item_col_no["medicine_type"],
                self.item_col_no["medicine_name"],
                self.item_col_no["medicine_unit"],
                self.item_col_no["amount"],
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

    def _save_stock_in_data(self):
        if self.stock_in_key is not None:
            stock_in_key = self.stock_in_key
            self._update_record()
        else:
            stock_in_key = self._insert_record()

        if self.system_settings.field("調整庫存量") == "即時調整":
            stock_utils.adjust_stock_quantity(
                self.database, self.system_settings, stock_in_key
            )

        self.parent.tab_stock_in_list.read_stock_in()
        self.close_tab()

    def _update_record(self):
        self._update_stock_in()
        self._update_stock_in_items()

    def _update_stock_in(self):
        fields = [
            "StockInDate",
            "Supplier",
            "OrderNo",
            "Attn",
            "Remark",
            "InvoiceNo",
            "PaymentType",
            "Amount",
        ]
        data = [
            self.ui.dateEdit_stock_in_date.date().toString("yyyy-MM-dd"),
            self.ui.comboBox_supplier.currentText(),
            self.ui.lineEdit_order_no.text(),
            self.ui.comboBox_attn.currentText(),
            self.ui.lineEdit_remark.text(),
            self.ui.lineEdit_invoice_no.text(),
            self.ui.comboBox_payment_type.currentText(),
            self.ui.lineEdit_total_amount.text(),
        ]
        self.database.update_record(
            "stockin", fields, "StockInKey", self.stock_in_key, data
        )

    def _update_stock_in_items(self):
        if self.system_settings.field("調整庫存量") == "即時調整":
            stock_utils.restore_stock_quantity(self.database, self.stock_in_key)

        self.database.delete_record("stockinitems", "StockInKey", self.stock_in_key)
        self._insert_stock_in_items(self.stock_in_key)

    def _insert_record(self):
        stock_in_key = self._insert_stock_in()
        self._insert_stock_in_items(stock_in_key)

        return stock_in_key

    def _insert_stock_in(self):
        fields = [
            "StockInDate",
            "Supplier",
            "OrderNo",
            "Attn",
            "Remark",
            "InvoiceNo",
            "PaymentType",
            "Amount",
        ]
        data = [
            self.ui.dateEdit_stock_in_date.date().toString("yyyy-MM-dd"),
            self.ui.comboBox_supplier.currentText(),
            self.ui.lineEdit_order_no.text(),
            self.ui.comboBox_attn.currentText(),
            self.ui.lineEdit_remark.text(),
            self.ui.lineEdit_invoice_no.text(),
            self.ui.comboBox_payment_type.currentText(),
            self.ui.lineEdit_total_amount.text(),
        ]
        stock_in_key = self.database.insert_record("stockin", fields, data)

        return stock_in_key

    def _insert_stock_in_items(self, stock_in_key):
        fields = [
            "StockInKey",
            "MedicineKey",
            "MedicineName",
            "ProductNo",
            "ProductName",
            "Unit",
            "UnitQuantity",
            "Quantity",
            "UnitPrice",
            "Amount",
            "Remark",
        ]

        for row_no in range(self.ui.tableWidget_stock_in_items.rowCount()):
            medicine_key = self.ui.tableWidget_stock_in_items.item(
                row_no, self.item_col_no["medicine_key"]
            ).text()
            medicine_name = self.ui.tableWidget_stock_in_items.item(
                row_no, self.item_col_no["medicine_name"]
            ).text()
            try:
                product_no = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["product_no"]
                ).text()
            except Exception:
                product_no = None

            try:
                product_name = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["product_name"]
                ).text()
            except Exception:
                product_name = None

            try:
                unit = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["unit"]
                ).text()
            except Exception:
                unit = None

            try:
                unit_quantity = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["unit_quantity"]
                ).text()
            except Exception:
                unit_quantity = None

            try:
                unit_price = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["unit_price"]
                ).text()
            except Exception:
                unit_price = None

            try:
                quantity = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["quantity"]
                ).text()
            except Exception:
                quantity = None

            try:
                amount = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["amount"]
                ).text()
            except Exception:
                amount = None

            try:
                remark = self.ui.tableWidget_stock_in_items.item(
                    row_no, self.item_col_no["remark"]
                ).text()
            except Exception:
                remark = None

            data = [
                stock_in_key,
                medicine_key,
                medicine_name,
                product_no,
                product_name,
                unit,
                unit_quantity,
                quantity,
                unit_price,
                amount,
                remark,
            ]

            self.database.insert_record("stockinitems", fields, data)

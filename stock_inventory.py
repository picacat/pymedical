# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QFileDialog

from libs import system_utils
from libs import ui_utils
from libs import class_utils
from libs import dialog_utils
from libs import number_utils
from libs import string_utils
from libs import date_utils
from libs import export_utils


# 盤點 2022.11.19 誠泰
class StockInventory(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StockInventory, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self.read_stock_inventory()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STOCK_INVENTORY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_stock_inventory = class_utils.get_table_widget(
            self.ui.tableWidget_stock_inventory, self.database
        )
        self.table_widget_stock_inventory.set_column_hidden([0])
        self.table_widget_stock_inventory_item = class_utils.get_table_widget(
            self.ui.tableWidget_stock_inventory_item, self.database
        )
        self.table_widget_stock_inventory_item.set_column_hidden([0, 1])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 150, 100, 150, 250]
        self.table_widget_stock_inventory.set_table_heading_width(width)
        width = [100, 100, 100, 200, 70, 80, 80, 80, 80, 80]
        self.table_widget_stock_inventory_item.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_update_inventory.triggered.connect(self._update_inventory)
        self.ui.toolButton_add_inventory.clicked.connect(self._add_inventory)
        self.ui.toolButton_edit_inventory.clicked.connect(self._edit_inventory)
        self.ui.toolButton_remove_inventory.clicked.connect(self._remove_inventory)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_stock_inventory.doubleClicked.connect(self._edit_inventory)
        self.ui.tableWidget_stock_inventory.itemSelectionChanged.connect(self._inventory_changed)
        self.ui.tableWidget_stock_inventory_item.itemChanged.connect(self._inventory_item_changed)
        self.ui.toolButton_remove_item.clicked.connect(self._remove_inventory_items)
        self.ui.toolButton_add_item.clicked.connect(self._add_inventory_items)
        self.ui.toolButton_auto_add.clicked.connect(self._auto_add_inventory_items)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    def read_stock_inventory(self):
        sql = '''
            SELECT * FROM stockinventory
            ORDER BY StockInventoryKey DESC
        '''
        self.table_widget_stock_inventory.set_db_data(sql, self._set_inventory_table_data)
        self._inventory_item_changed()

    def _set_inventory_table_data(self, row_no, row):
        try:
            archived_date = row['ArchivedDate'].strftime('%Y-%m-%d')
        except Exception:
            archived_date = None

        stock_inventory_record = [
            row['StockInventoryKey'],
            row['StockInventoryDate'].strftime('%Y-%m-%d'),
            row['Inspector'],
            archived_date,
            row['Remark'],
        ]

        for col_no, field in enumerate(stock_inventory_record):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_inventory.setItem(row_no, col_no, item)

    def _add_inventory(self):
        stock_inventory_key = None
        dialog = dialog_utils.get_dialog_add_inventory(
            self, self.database, self.system_settings, None,
        )
        if dialog.exec_():
            stock_inventory_key = dialog.stock_inventory_key
            self._refresh_record()

        dialog.deleteLater()
        self._create_stock_inventory_items(stock_inventory_key)  # 自動加入有安全存量的藥品
        self._inventory_changed()

    # 自動加入有安全存量設定的藥品
    def _create_stock_inventory_items(self, stock_inventory_key):
        sql = '''
            SELECT MedicineKey, MedicineName, Location, Quantity FROM medicine
            WHERE
                SafeQuantity > 0
            ORDER BY MedicineType, MedicineKey
        '''
        rows = self.database.select_record(sql)

        fields = ['StockInventoryKey', 'MedicineKey', 'MedicineName', 'Location', 'Quantity']
        for row in rows:
            data = [
                stock_inventory_key,
                row['MedicineKey'],
                row['MedicineName'],
                row['Location'],
                number_utils.get_float(row['Quantity']),
            ]
            self.database.insert_record('stockinventory_items', fields, data)

    def _inventory_changed(self):
        self.ui.action_update_inventory.setEnabled(True)
        archived_date = self.table_widget_stock_inventory.field_value(3)
        if archived_date is not None and archived_date != '':
            self.ui.action_update_inventory.setEnabled(False)

        stock_inventory_key = self.table_widget_stock_inventory.field_value(0)
        if stock_inventory_key in ['', None]:
            self.ui.tableWidget_stock_inventory_item.setRowCount(0)
            return

        self.ui.tableWidget_stock_inventory_item.blockSignals(True)
        sql = f'''
            SELECT
                stockinventory_items.*,
                medicine.MedicineType, medicine.Unit, medicine.SafeQuantity
            FROM stockinventory_items
                LEFT JOIN medicine ON medicine.MedicineKey =stockinventory_items.MedicineKey
            WHERE
                StockInventoryKey = {stock_inventory_key}
            ORDER BY StockInventoryItemsKey
        '''
        self.table_widget_stock_inventory_item.set_db_data(sql, self._set_inventory_items_table_data)
        self.ui.tableWidget_stock_inventory_item.blockSignals(False)

    def _inventory_item_changed(self):
        row_no = self.ui.tableWidget_stock_inventory_item.currentRow()
        if self.ui.tableWidget_stock_inventory_item.item(row_no, 8) is None:
            return

        self.ui.tableWidget_stock_inventory_item.blockSignals(True)
        self._calculate_items_subtotal(row_no)
        self.ui.tableWidget_stock_inventory_item.blockSignals(False)

    def _calculate_items_subtotal(self, row_no):
        quantity = number_utils.get_float(self.ui.tableWidget_stock_inventory_item.item(row_no, 7).text())
        inventory_quantity = number_utils.get_float(self.ui.tableWidget_stock_inventory_item.item(row_no, 8).text())
        remain = inventory_quantity - quantity

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, remain)
        self.ui.tableWidget_stock_inventory_item.setItem(row_no, 9, item)

        for col_no in [6, 7, 8, 9]:
            self.ui.tableWidget_stock_inventory_item.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

        stock_inventory_items_key = self.ui.tableWidget_stock_inventory_item.item(row_no, 0)
        if stock_inventory_items_key is None:
            return

        stock_inventory_items_key = stock_inventory_items_key.text()
        if stock_inventory_items_key == '':
            return
        
        sql = f'''
            UPDATE stockinventory_items
            SET
                InventoryQuantity = {inventory_quantity}
            WHERE
                StockInventoryItemsKey = {stock_inventory_items_key}
        '''
        self.database.exec_sql(sql)

    def _set_inventory_items_table_data(self, row_no, row):
        safe_quantity = number_utils.get_float(row['SafeQuantity'])
        quantity = number_utils.get_float(row['Quantity'])
        inventory_quantity = number_utils.get_float(row['InventoryQuantity'])
        remain = inventory_quantity - quantity

        stock_inventory_items_record = [
            row['StockInventoryItemsKey'],
            row['MedicineKey'],
            string_utils.xstr(row['MedicineType']),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['Location']),
            string_utils.xstr(row['Unit']),
            safe_quantity,
            quantity,
            inventory_quantity,
            remain,
        ]

        for col_no, field in enumerate(stock_inventory_items_record):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_inventory_item.setItem(row_no, col_no, item)

            if col_no in [5]:
                self.ui.tableWidget_stock_inventory_item.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [6, 7, 8, 9]:
                self.ui.tableWidget_stock_inventory_item.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _edit_inventory(self):
        stock_inventory_key = self.table_widget_stock_inventory.field_value(0)
        dialog = dialog_utils.get_dialog_add_inventory(
            self, self.database, self.system_settings, stock_inventory_key,
        )
        if dialog.exec_():
            self._refresh_record(stock_inventory_key)

        dialog.deleteLater()

    def _update_inventory(self):
        msg_box = dialog_utils.get_message_box(
            '調整盤點資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定更新盤點量回處方資料?</b></font>',
            '注意！資料更新後, 將無法回復!'
        )
        update_record = msg_box.exec_()
        if not update_record:
            return

        stock_inventory_key = self.table_widget_stock_inventory.field_value(0)
        sql = f'''
            SELECT * FROM stockinventory_items
            WHERE
                StockInventoryKey = {stock_inventory_key}
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            medicine_key = row['MedicineKey']
            inventory_quantity = row['InventoryQuantity']
            if inventory_quantity is None:
                inventory_quantity = 'NULL'

            sql = f'''
                UPDATE medicine
                SET
                    Quantity = {inventory_quantity}
                WHERE
                    MedicineKey = {medicine_key}
            '''
            self.database.exec_sql(sql)

        sql = f'''
            UPDATE stockinventory
            SET
                ArchivedDate = "{date_utils.now_to_str()}"
            WHERE
                StockInventoryKey = {stock_inventory_key}
        '''
        self.database.exec_sql(sql)
        self._refresh_record(stock_inventory_key)

        system_utils.show_message_box(
            QMessageBox.Information,
            '過帳完成',
            '<font size="5" color="blue"><b>所有產品的庫存量皆已更新.</b></font>',
            '庫存量已更新.'
        )

    def _remove_inventory(self):
        stock_inventory_key = self.table_widget_stock_inventory.field_value(0)
        if stock_inventory_key in ['', None]:
            return

        msg_box = dialog_utils.get_message_box(
            '刪除盤點資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此盤點資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        sql = f'''
            DELETE FROM stockinventory_items
            WHERE
                StockInventoryKey = {stock_inventory_key}
        '''
        self.database.exec_sql(sql)
        sql = f'''
            DELETE FROM stockinventory
            WHERE
                StockInventoryKey = {stock_inventory_key}
        '''
        self.database.exec_sql(sql)

        current_row = self.ui.tableWidget_stock_inventory.currentRow()
        self.ui.tableWidget_stock_inventory.removeRow(current_row)
        self._inventory_changed()

    def _add_inventory_items(self):
        dialog = dialog_utils.get_dialog_medicine(
            self, self.database, self.system_settings, self.ui.tableWidget_stock_inventory_item, None, '盤點藥品',
        )
        dialog.exec_()
        dialog.deleteLater()

    def _auto_add_inventory_items(self):
        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "藥品類別"
            ORDER BY DictOrderNo, DictGroupsKey
        '''
        rows = self.database.select_record(sql)
        items = []
        for row in rows:
            items.append(row['DictGroupsName'])

        input_dialog = QInputDialog()
        input_dialog.setOkButtonText('確定')
        input_dialog.setCancelButtonText('取消')
        medicine_type, ok = input_dialog.getItem(
            self, '選擇處方類別', '請選擇處方類別', items, 0, False)
        if not ok or not medicine_type:
            return

        sql = f'''
            SELECT MedicineKey FROM medicine
            WHERE
                MedicineType = "{medicine_type}" AND
                LENGTH(MedicineName) > 0 AND
                MedicineName IS NOT NULL AND
                (LENGTH(Deactivate) = 0 OR Deactivate IS NULL)
            ORDER BY MedicineName
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            self.insert_inventory_item(row)

    # call by dialog_medicine
    def insert_inventory_item(self, medicine_row):
        medicine_key = medicine_row['MedicineKey']
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        medicine_row = rows[0]
        stock_inventory_key = self.table_widget_stock_inventory.field_value(0)
        fields = ['StockInventoryKey', 'MedicineKey', 'MedicineName', 'Location', 'Quantity']
        data = [
            number_utils.get_integer(stock_inventory_key),
            medicine_key,
            medicine_row['MedicineName'],
            medicine_row['Location'],
            number_utils.get_float(medicine_row['Quantity'])
        ]
        inventory_items_key = self.database.insert_record('stockinventory_items', fields, data)

        row_no = self.ui.tableWidget_stock_inventory_item.rowCount()
        self.ui.tableWidget_stock_inventory_item.setRowCount(row_no + 1)
        inventory_row = [
            inventory_items_key,
            medicine_key,
            medicine_row['MedicineType'],
            medicine_row['MedicineName'],
            medicine_row['Location'],
            medicine_row['Unit'],
            number_utils.get_float(medicine_row['SafeQuantity']),
            number_utils.get_float(medicine_row['Quantity']),
            0, 0,
        ]

        for col_no, field in enumerate(inventory_row):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_stock_inventory_item.setItem(row_no, col_no, item)
            if col_no in [5]:
                self.ui.tableWidget_stock_inventory_item.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [6, 7, 8, 9]:
                self.ui.tableWidget_stock_inventory_item.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _remove_inventory_items(self):
        msg_box = dialog_utils.get_message_box(
            '刪除盤點藥品', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此盤點藥品?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        stock_inventory_items_key = self.table_widget_stock_inventory_item.field_value(0)
        sql = f'''
            DELETE FROM stockinventory_items
            WHERE
                StockInventoryItemsKey = {stock_inventory_items_key}
        '''
        self.database.exec_sql(sql)

        current_row = self.ui.tableWidget_stock_inventory_item.currentRow()
        self.ui.tableWidget_stock_inventory_item.removeRow(current_row)

    def _refresh_record(self, stock_inventory_key=None):
        if stock_inventory_key is None:
            self.read_stock_inventory()
            return

        sql = f'''
            SELECT * FROM stockinventory
            WHERE
                StockInventoryKey = {stock_inventory_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        current_row = self.ui.tableWidget_stock_inventory.currentRow()
        self._set_inventory_table_data(current_row, row)

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出盤點清單",
            f'盤點清單.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_stock_inventory_item, [0, 1], [5, 6, 7, 8]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>盤點清單{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

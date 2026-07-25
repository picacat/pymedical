
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (class_utils, dialog_utils, export_utils, string_utils,
                  system_utils, ui_utils)


#  廠商資料-通訊錄 2022.09.08 安聲
class DictAddressBook(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictAddressBook, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_supplier()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_ADDRESS_BOOK, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_dict_address = class_utils.get_table_widget(
            self.ui.tableWidget_dict_address, self.database
        )
        self.table_widget_dict_address.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_address.clicked.connect(self._add_address_book)
        self.ui.toolButton_remove_address.clicked.connect(self._remove_address_book)
        self.ui.toolButton_edit_address.clicked.connect(self._edit_address_book)
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_dict_address.doubleClicked.connect(self._edit_address_book)
        self.ui.lineEdit_query.textChanged.connect(self._query_address)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 300, 150, 150, 500, 400]
        self.table_widget_dict_address.set_table_heading_width(width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def _read_supplier(self, sql=None):
        if sql is None:
            sql = '''
                SELECT * FROM supplier
                ORDER BY SupplierKey
            '''

        self.table_widget_dict_address.set_db_data(sql, self._set_dict_address_data)

    def _set_dict_address_data(self, row_no, row):
        dict_address_row = [
            string_utils.xstr(row['SupplierKey']),
            string_utils.xstr(row['Code']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Telephone']),
            string_utils.xstr(row['Cellphone']),
            string_utils.xstr(row['Address']),
            string_utils.xstr(row['Remark']),
        ]

        for column in range(len(dict_address_row)):
            self.ui.tableWidget_dict_address.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_address_row[column])
            )

    def _query_address(self):
        keywords = self.ui.lineEdit_query.text().split()
        if len(keywords) <= 0:
            self._read_supplier()
            return

        condition = []
        for keyword in keywords:
            condition.append(f'''
                (Code LIKE "{keyword}%" OR
                 Name LIKE "%{keyword}%" OR
                 Telephone LIKE "%{keyword}%" OR
                 Cellphone LIKE "%{keyword}%" OR
                 Address LIKE "%{keyword}%" OR
                 Remark LIKE "%{keyword}%")
            ''')

        condition = ' AND '.join(condition)
        sql = f'''
            SELECT * FROM supplier
            WHERE
                {condition}
            ORDER BY SupplierKey
        '''
        self._read_supplier(sql)
        self.ui.lineEdit_query.setFocus(True)
        self.ui.lineEdit_query.setCursorPosition(len(self.ui.lineEdit_query.text()))

    # 新增廠商資料
    def _add_address_book(self):
        dialog = dialog_utils.get_dialog_input_supplier(self, self.database, self.system_settings, None)
        result = dialog.exec_()
        if result != 0:
            self._read_supplier()
            self.ui.tableWidget_dict_address.setCurrentCell(self.ui.tableWidget_dict_address.rowCount()-1, 1)

        dialog.close_all()
        dialog.deleteLater()

    # 移除通訊錄資料
    def _remove_address_book(self):
        supplier_name = self.table_widget_dict_address.field_value(2)
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除通訊錄資料 "{supplier_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_address.field_value(0)
        self.database.delete_record('supplier', 'SupplierKey', key)
        self.ui.tableWidget_dict_address.removeRow(self.ui.tableWidget_dict_address.currentRow())

    # 編輯院所資料
    def _edit_address_book(self):
        supplier_key = self.table_widget_dict_address.field_value(0)
        dialog = dialog_utils.get_dialog_input_supplier(self, self.database, self.system_settings, supplier_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f'''
            SELECT * FROM supplier
            WHERE
                SupplierKey = {supplier_key}
        '''
        row = self.database.select_record(sql)[0]
        self._set_dict_address_data(self.ui.tableWidget_dict_address.currentRow(), row)

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            '廠商通訊錄.xlsx',
            "excel檔案 (*.xlsx)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_dict_address, [0]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )
        

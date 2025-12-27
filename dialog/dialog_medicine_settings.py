# 輸入公告資料 2024-09-11
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import system_utils
from libs import ui_utils
from libs import class_utils
from libs import string_utils
from libs import number_utils
from libs import dialog_utils


# 主視窗
class DialogMedicineSettings(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicineSettings, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

        self._read_medicine()

        self.ui.tableWidget_medicine.setCurrentCell(0, 3)
        self.ui.tableWidget_medicine.setFocus()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICINE_SETTINGS, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog

        self._set_font_size()
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self.table_widget_medicine.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 280, 160, 280, 50, 50, 130, 130, 100, 200]
        self.table_widget_medicine.set_table_heading_width(width)

    def _set_font_size(self):
        font_size = 20
        self.ui.setStyleSheet(
            f'font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold'
        )
        self.ui.tableWidget_medicine.setStyleSheet(
            f'font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold'
        )

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medicine.itemChanged.connect(self._medicine_item_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_search.clicked.connect(self._search_medicine)
        self.ui.radioButton_medicine1.clicked.connect(lambda: self._read_medicine())
        self.ui.radioButton_medicine2.clicked.connect(lambda: self._read_medicine())

    def accepted_button_clicked(self):
        pass

    def _read_medicine(self, sql=None):
        if sql is None:
            if self.ui.radioButton_medicine1.isChecked():
                medicine_type = '單方'
            else:
                medicine_type = '複方'

            sql = f'''
                SELECT * FROM medicine
                WHERE
                    MedicineType = '{medicine_type}' AND
                    (Deactivate IS NULL OR LENGTH(Deactivate) = 0)
                ORDER BY SUBSTRING(medicine.Location, 1, 1), CAST(SUBSTRING(medicine.Location, 2) AS UNSIGNED) DESC
            '''

        self.ui.tableWidget_medicine.itemChanged.disconnect()
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)
        self.ui.tableWidget_medicine.itemChanged.connect(self._medicine_item_changed)

    def _get_more_barcode(self, medicine_key):
        sql = f'''
            SELECT * FROM medextend
            WHERE
                MedicineKey = '{medicine_key}' AND
                ExtendType = '藥品條碼'
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            more_barcode = True
        else:
            more_barcode = None

        return more_barcode

    def _more_barcode_clicked(self):
        print('more barcode clicked')

    def _set_medicine_data(self, row_no, row):
        medicine_key = string_utils.xstr(row['MedicineKey'])
        quantity = round(number_utils.get_float(row['Quantity']), 1)
        safe_quantity = round(number_utils.get_float(row['SafeQuantity']), 1)
        in_price = round(number_utils.get_float(row['InPrice']), 1)

        medicine_row = [
            medicine_key,
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['Location']),
            string_utils.xstr(row['MedicineCode']),
            None,
            None,
            quantity,
            safe_quantity,
            in_price,
            None,
        ]

        for col_no in range(len(medicine_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, string_utils.xstr(medicine_row[col_no]))
            self.ui.tableWidget_medicine.setItem(row_no, col_no, item)
            if col_no in [6, 7, 8]:
                self.ui.tableWidget_medicine.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            # elif col_no in [3]:
            #     self.ui.tableWidget_prescript.item(
            #         row_no, col_no).setTextAlignment(
            #         QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            #     )
            more_barcode = self._get_more_barcode(medicine_key)
            if more_barcode:
                ui_utils.set_table_widget_field_icon(
                    self.ui.tableWidget_medicine, row_no, 4, './icons/edit-copy.svg',
                    'more_barcode', True, self._more_barcode_clicked)

            ui_utils.set_table_widget_field_icon(
                self.ui.tableWidget_medicine, row_no, 5, './icons/add.svg',
                'add_more_barcode', True, lambda: self._add_more_barcode_clicked(medicine_key))

    def _add_more_barcode_clicked(self, medicine_key):
        dialog = dialog_utils.get_dialog_medicine_code(
            self, self.database, self.system_settings, medicine_key)

        dialog.exec_()
        del dialog

    def _medicine_item_changed(self, item):
        col_no = self.ui.tableWidget_medicine.currentColumn()
        row_no = self.ui.tableWidget_medicine.currentRow()

        item = self.ui.tableWidget_medicine.item(row_no, 0)
        if item is None:
            return

        medicine_key = item.text()

        item = self.ui.tableWidget_medicine.item(row_no, col_no)
        if item is None:
            return

        field_name_list = [
            'MeidcineKey',
            'MedicineName', 'Location', 'MedicineCode', 'Quantity', 'SafeQuantity', 'InPrice'
        ]
        field_name = field_name_list[col_no]
        value = item.text()

        if col_no in [4, 5, 6]:  # Quantity, SafeQuantity, InPrice
            value = number_utils.get_float(value)
            sql = f'''
                UPDATE medicine
                SET
                    {field_name} = {value}
                WHERE
                    MedicineKey = {medicine_key}
            '''
        else:
            value = value[:15]
            sql = f'''
                UPDATE medicine
                SET
                    {field_name} = '{value}'
                WHERE
                    MedicineKey = {medicine_key}
            '''
        self.database.exec_sql(sql)
        # self.ui.tableWidget_medicine.setCurrentCell(row_no+1, col_no)

    def _query_medicine(self):
        keyword = self.ui.lineEdit_keyword.text()
        if keyword == '':
            self._read_medicine()
            return

    def _search_medicine(self):
        keyword = self.ui.lineEdit_keyword.text()
        if keyword == '':
            self._read_medicine()
            return

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineName LIKE "%{keyword}%" OR
                 MedicineCode = "{keyword}") AND
                (Deactivate IS NULL OR LENGTH(Deactivate) = 0)
        '''
        self._read_medicine(sql)

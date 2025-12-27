# 輸入公告資料 2024-09-11
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QInputDialog

from libs import system_utils
from libs import ui_utils
from libs import class_utils
from libs import string_utils
from libs import dialog_utils


# 主視窗
class DialogMedicineCode(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicineCode, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.medicine_key = args[2]

        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

        self._read_med_extend()

        self.ui.tableWidget_med_extend.setCurrentCell(0, 3)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICINE_CODE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog

        self._set_font_size()
        self.table_widget_med_extend = class_utils.get_table_widget(
            self.ui.tableWidget_med_extend, self.database
        )
        self.table_widget_med_extend.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 520]
        self.table_widget_med_extend.set_table_heading_width(width)

    def _set_font_size(self):
        font_size = 20
        self.ui.setStyleSheet(
            f'font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold'
        )
        self.ui.tableWidget_med_extend.setStyleSheet(
            f'font-size: {font_size}pt; font-family: Microsoft JhengHei; font-weight: bold'
        )

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add.clicked.connect(self._add_med_extend)
        self.ui.toolButton_remove.clicked.connect(self._remove_med_extend)

    def accepted_button_clicked(self):
        pass

    def _read_med_extend(self, sql=None):
        sql = f'''
            SELECT * FROM medextend
            WHERE
                MedicineKey = {self.medicine_key} AND
                ExtendType = '藥品條碼'
            ORDER BY MedExtendKey
        '''
        self.table_widget_med_extend.set_db_data(sql, self._set_med_extend_data)

    def _set_med_extend_data(self, row_no, row):
        med_extend_key = string_utils.xstr(row['MedExtendKey'])
        description = string_utils.xstr(row['Description'])

        med_extend_row = [
            med_extend_key,
            description,
        ]

        for col_no in range(len(med_extend_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, string_utils.xstr(med_extend_row[col_no]))
            self.ui.tableWidget_med_extend.setItem(row_no, col_no, item)

    def _add_med_extend(self):
        input_dialog = dialog_utils.get_dialog(
            f'輸入條碼',
            f'請輸入藥品條碼',
            None, QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        barcode = input_dialog.textValue()
        fields = ['MedicineKey', 'ExtendType', 'Description']
        data = [self.medicine_key, '藥品條碼', barcode]
        self.database.insert_record('medextend', fields, data)
        self._read_med_extend()

    def _remove_med_extend(self):
        row_no = self.ui.tableWidget_med_extend.currentRow()
        if row_no < 0:
            return

        med_extend_key = self.ui.tableWidget_med_extend.item(row_no, 0).text()
        self.database.delete_record('medextend', 'MedExtendKey', med_extend_key)
        self._read_med_extend()
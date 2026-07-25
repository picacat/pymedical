
# -*- coding: UTF-8 -*-

import datetime
import enum

from libs import (class_utils, number_utils, prescript_utils, string_utils,
                  system_utils, ui_utils)
from PyQt5 import QtCore, QtWidgets


# 新增成方資料 2025.03.12 天地精進
class DialogInsertCompound(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsertCompound, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._set_compound()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INSERT_COMPOUND, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.table_widget_compound = class_utils.get_table_widget(
            self.ui.tableWidget_compound, self.database
        )
        self.table_widget_compound.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [100, 350, 70, 60]
        self.table_widget_compound.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.lineEdit_compound_name.textChanged.connect(self._check_compound)

    def accepted_button_clicked(self):
        self._save_compound()

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '新增成方完成',
            f'<h3>成方資料已存檔完成.</h3>',
            '存檔成功.'
        )

    def _set_compound(self):
        self.ui.tableWidget_compound.setRowCount(0)
        for row_no in range(self.table_widget_prescript.rowCount()):
            medicine_key_item = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineKey'])
            if medicine_key_item is None:
                continue

            medicine_key = medicine_key_item.text()
            medicine_name = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']).text()
            unit = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Unit']).text()
            dosage = self.table_widget_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO['Dosage']).text()

            self._insert_compound(medicine_key, medicine_name, dosage, unit)

    def _insert_compound(self, medicine_key, medicine_name, dosage, unit):
        self.ui.tableWidget_compound.setRowCount(
            self.ui.tableWidget_compound.rowCount() + 1
        )
        row_no = self.ui.tableWidget_compound.rowCount() - 1
        row = [medicine_key, medicine_name, dosage, unit]
        for col_no, field in enumerate(row):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, field)
            self.ui.tableWidget_compound.setItem(
                row_no, col_no, item,
            )
            if col_no == 2:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no == 3:
                item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _check_compound(self):
        compound_name = self.ui.lineEdit_compound_name.text()
        row_count = self.ui.tableWidget_compound.rowCount()
        if compound_name == '' or row_count <= 0:
            self.ui.lineEdit_input_code.setText('')
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
            return

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

        input_code = string_utils.get_input_code(compound_name)
        self.ui.lineEdit_input_code.setText(input_code)

    def _save_compound(self):
        compound_name = self.ui.lineEdit_compound_name.text()
        input_code = self.ui.lineEdit_input_code.text()
        fields = ['MedicineType', 'MedicineName', 'InputCode', 'Unit']
        data = ['成方', compound_name, input_code, '克']
        compound_key = self.database.insert_record('medicine', fields, data)

        fields = ['CompoundKey', 'MedicineKey', 'Quantity', 'Unit']
        for row_no in range(self.ui.tableWidget_compound.rowCount()):
            medicine_key = self.ui.tableWidget_compound.item(
                row_no, 0).text()
            
            if medicine_key in ['', None]:
                continue
            
            dosage = self.ui.tableWidget_compound.item(
                row_no, 2).text()
            unit = self.ui.tableWidget_compound.item(
                row_no, 3).text()
            data = [compound_key, medicine_key, dosage, unit]
            self.database.insert_record('refcompound', fields, data)

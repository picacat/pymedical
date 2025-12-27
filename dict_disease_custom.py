
# -*- coding: UTF-8 -*-

import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils


# 自訂病名設定 2023.04.17
class DictDiseaseCustom(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictDiseaseCustom, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.dict_type = '自訂病名'

        self._set_ui()
        self._set_signal()
        self._read_disease()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_DISEASE_CUSTOM, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_dict_groups_name = class_utils.get_table_widget(
            self.ui.tableWidget_dict_groups_name, self.database
        )
        self.table_widget_dict_groups_name.set_column_hidden([0])
        self.table_widget_dict_disease = class_utils.get_table_widget(self.ui.tableWidget_dict_disease, self.database)
        self.table_widget_dict_disease.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups_name.itemSelectionChanged.connect(self.dict_groups_name_changed)
        self.ui.toolButton_add_groups_name.clicked.connect(self._add_groups_name)
        self.ui.toolButton_remove_groups_name.clicked.connect(self._remove_groups_name)
        self.ui.toolButton_edit_groups_name.clicked.connect(self._edit_groups_name)
        self.ui.tableWidget_dict_groups_name.doubleClicked.connect(self._edit_groups_name)
        self.ui.toolButton_add_disease.clicked.connect(self._add_disease)
        self.ui.toolButton_remove_disease.clicked.connect(self._remove_disease)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 400]
        dict_disease_width = [100, 120, 80, 70, 840]
        self.table_widget_dict_groups_name.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_disease.set_table_heading_width(dict_disease_width)

    def _read_disease(self):
        self._read_dict_groups_name()

    def _read_dict_groups_name(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}"
            ORDER BY DictGroupsTopLevel
        '''
        self.table_widget_dict_groups_name.set_db_data(sql, self._set_dict_groups_name_data)
        self.dict_groups_name_changed()

    def _set_dict_groups_name_data(self, row_no, row):
        dict_groups_name_row = [
            string_utils.xstr(row['DictGroupsKey']),
            string_utils.xstr(row['DictGroupsTopLevel']),
        ]

        for column in range(len(dict_groups_name_row)):
            self.ui.tableWidget_dict_groups_name.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_groups_name_row[column])
            )

    def dict_groups_name_changed(self):
        dict_groups_name = self.table_widget_dict_groups_name.field_value(1)
        self.ui.groupBox_dict_disease.setTitle(f'{self.dict_type}資料 - [{dict_groups_name}]')
        self.read_dict_disease(dict_groups_name)
        self.ui.tableWidget_dict_groups_name.setFocus(True)

    def read_dict_disease(self, dict_groups_name):
        sql = f'''
            SELECT CustomDiseaseKey, icd10.* FROM custom_disease
                LEFT JOIN icd10 ON icd10.ICDCode = custom_disease.ICDCode
            WHERE
                GroupsName = "{dict_groups_name}"
            ORDER BY icd10.ICDCode
        '''
        self.table_widget_dict_disease.set_db_data(sql, self._set_dict_disease_data)

    def _set_dict_disease_data(self, row_no, row):
        dict_disease_row = [
            string_utils.xstr(row['CustomDiseaseKey']),
            string_utils.xstr(row['ICDCode']),
            string_utils.xstr(row['InputCode']),
            string_utils.xstr(row['SpecialCode']),
            string_utils.xstr(row['ChineseName']),
        ]

        for column in range(len(dict_disease_row)):
            self.ui.tableWidget_dict_disease.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_disease_row[column])
            )

            if string_utils.xstr(row['SpecialCode']) != '':
                self.ui.tableWidget_dict_disease.item(
                    row_no, column
                ).setForeground(QtGui.QColor('red'))

    # 新增病名類別
    def _add_groups_name(self):
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}分類',
            f'請輸入{self.dict_type}分類名稱', None,
            QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        groups_name = input_dialog.textValue()
        field = ['DictGroupsType', 'DictGroupsTopLevel']
        data = [
            self.dict_type, groups_name
        ]
        self.database.insert_record('dict_groups', field, data)
        self._read_dict_groups_name()

    # 移除舌診類別
    def _remove_groups_name(self):
        groups_name = self.table_widget_dict_groups_name.field_value(1)
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}分類資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除 [{groups_name}] {self.dict_type}分類?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_groups_name.field_value(0)
        self.database.delete_record('dict_groups', 'DictGroupsKey', key)
        self.ui.tableWidget_dict_groups_name.removeRow(self.ui.tableWidget_dict_groups_name.currentRow())

    # 修改舌診類別
    def _edit_groups_name(self):
        old_groups_name = self.table_widget_dict_groups_name.field_value(1)
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}分類',
            f'請輸入{self.dict_type}分類',
            old_groups_name,
            QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        dict_groups_name = input_dialog.textValue()
        dict_groups_key = self.table_widget_dict_groups_name.field_value(0)

        sql = f'''
            UPDATE custom_disease
            SET
                GroupsName = "{dict_groups_name}"
            WHERE
                GroupsName = "{old_groups_name}"
        '''
        self.database.exec_sql(sql)

        sql = f'''
            UPDATE dict_groups
            SET
                DictGroupsTopLevel = "{dict_groups_name}"
            WHERE
                DictGroupsKey = {dict_groups_key}
        '''
        self.database.exec_sql(sql)
        self.ui.tableWidget_dict_groups_name.item(
            self.ui.tableWidget_dict_groups_name.currentRow(), 1).setText(dict_groups_name)

    # 新增舌診
    def _add_disease(self):
        groups_name = self.table_widget_dict_groups_name.field_value(1)
        dialog = dialog_utils.get_dialog_input_disease(
            self, self.database, self.system_settings, groups_name, '自訂病名')
        dialog.exec_()
        dialog.close_all()

    # 移除舌診
    def _remove_disease(self):
        disease_name = self.table_widget_dict_disease.field_value(4)
        msg_box = dialog_utils.get_message_box(
            f'移除{self.dict_type}資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定移除{self.dict_type}: "{disease_name}"?</b></font>',
            '注意！資料移除後, 還可新增回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        custom_disease_key = self.table_widget_dict_disease.field_value(0)
        sql = f'''
            DELETE FROM custom_disease
            WHERE
                CustomDiseaseKey = {custom_disease_key}
        '''
        self.database.exec_sql(sql)
        self.ui.tableWidget_dict_disease.removeRow(self.ui.tableWidget_dict_disease.currentRow())

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

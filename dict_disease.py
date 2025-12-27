
# -*- coding: UTF-8 -*-

import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils


# 病名設定 2018.04.14
class DictDisease(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictDisease, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.dict_type = '病名'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_DISEASE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_dict_groups = class_utils.get_table_widget(self.ui.tableWidget_dict_groups, self.database)
        self.table_widget_dict_groups.set_column_hidden([0])
        self.table_widget_dict_groups_name = class_utils.get_table_widget(
            self.ui.tableWidget_dict_groups_name, self.database
        )
        self.table_widget_dict_groups_name.set_column_hidden([0])
        self.table_widget_dict_disease = class_utils.get_table_widget(self.ui.tableWidget_dict_disease, self.database)
        self.table_widget_dict_disease.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups.itemSelectionChanged.connect(self.dict_groups_changed)
        self.ui.tableWidget_dict_groups_name.itemSelectionChanged.connect(self.dict_groups_name_changed)
        self.ui.toolButton_add_dict_groups.clicked.connect(self._add_dict_groups)
        self.ui.toolButton_remove_dict_groups.clicked.connect(self._remove_dict_groups)
        self.ui.toolButton_edit_dict_groups.clicked.connect(self._edit_dict_groups)
        self.ui.tableWidget_dict_groups.doubleClicked.connect(self._edit_dict_groups)
        self.ui.toolButton_add_groups_name.clicked.connect(self._add_groups_name)
        self.ui.toolButton_remove_groups_name.clicked.connect(self._remove_groups_name)
        self.ui.toolButton_edit_groups_name.clicked.connect(self._edit_groups_name)
        self.ui.tableWidget_dict_groups_name.doubleClicked.connect(self._edit_groups_name)
        self.ui.toolButton_add_disease.clicked.connect(self._add_disease)
        self.ui.toolButton_remove_disease.clicked.connect(self._remove_disease)
        self.ui.toolButton_edit_disease.clicked.connect(self._edit_disease)
        self.ui.tableWidget_dict_disease.doubleClicked.connect(self._edit_disease)
        self.ui.lineEdit_find_disease.textChanged.connect(self._find_disease)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 400]
        dict_disease_width = [100, 120, 80, 70, 540]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_groups_name.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_disease.set_table_heading_width(dict_disease_width)

    def _read_disease(self):
        self._read_dict_groups()

    def _read_dict_groups(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}類別"
            ORDER BY DictGroupsKey
        '''
        self.table_widget_dict_groups.set_db_data(sql, self._set_dict_groups_data)

    def _set_dict_groups_data(self, rec_no, rec):
        dict_groups_rec = [
            string_utils.xstr(rec['DictGroupsKey']),
            string_utils.xstr(rec['DictGroupsName']),
        ]

        for column in range(len(dict_groups_rec)):
            self.ui.tableWidget_dict_groups.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(dict_groups_rec[column])
            )

    def dict_groups_changed(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        self.ui.groupBox_dict_groups_name.setTitle(string_utils.xstr(dict_groups_type) + '類別')
        self._read_dict_groups_name(dict_groups_type)
        self.ui.tableWidget_dict_groups.setFocus(True)

    def _read_dict_groups_name(self, dict_groups_type):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}" AND
                DictGroupsTopLevel = "{dict_groups_type}"
            ORDER BY DictGroupsName
        '''
        self.table_widget_dict_groups_name.set_db_data(sql, self._set_dict_groups_name_data)
        self.dict_groups_name_changed()

    def _set_dict_groups_name_data(self, rec_no, rec):
        dict_groups_name_rec = [
            string_utils.xstr(rec['DictGroupsKey']),
            string_utils.xstr(rec['DictGroupsName']),
        ]

        for column in range(len(dict_groups_name_rec)):
            self.ui.tableWidget_dict_groups_name.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(dict_groups_name_rec[column])
            )

    def dict_groups_name_changed(self):
        dict_groups_name = self.table_widget_dict_groups_name.field_value(1)
        self.ui.groupBox_dict_disease.setTitle(f'{self.dict_type}資料 - [{dict_groups_name}]')
        self.read_dict_disease(dict_groups_name)
        self.ui.tableWidget_dict_groups_name.setFocus(True)

    def read_dict_disease(self, dict_groups_name):
        sql = f'''
            SELECT * FROM icd10
            WHERE
                Groups = "{dict_groups_name}"
            ORDER BY ICDCode
        '''
        self.table_widget_dict_disease.set_db_data(sql, self._set_dict_disease_data)

    def _set_dict_disease_data(self, rec_no, rec):
        dict_disease_rec = [
            string_utils.xstr(rec['ICD10Key']),
            string_utils.xstr(rec['ICDCode']),
            string_utils.xstr(rec['InputCode']),
            string_utils.xstr(rec['SpecialCode']),
            string_utils.xstr(rec['ChineseName']),
        ]

        for column in range(len(dict_disease_rec)):
            self.ui.tableWidget_dict_disease.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(dict_disease_rec[column])
            )

            if string_utils.xstr(rec['SpecialCode']) != '':
                self.ui.tableWidget_dict_disease.item(
                    rec_no, column
                ).setForeground(QtGui.QColor('red'))

    # 新增舌診類別
    def _add_dict_groups(self):
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入{self.dict_type}類別',
            None, QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        dict_groups = input_dialog.textValue()
        field = ['DictGroupsType', 'DictGroupsName']
        data = [
            f'{self.dict_type}類別', dict_groups,
        ]
        self.database.insert_record('dict_groups', field, data)
        self._read_dict_groups()

    # 移除舌診類別
    def _remove_dict_groups(self):
        dict_groups = self.table_widget_dict_groups.field_value(1)
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}類別資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除 [{dict_groups}] {self.dict_type}類別?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_groups.field_value(0)
        self.database.delete_record('dict_groups', 'DictGroupsKey', key)
        self.ui.tableWidget_dict_groups.removeRow(self.ui.tableWidget_dict_groups.currentRow())

    # 更改舌診類別
    def _edit_dict_groups(self):
        old_groups = self.table_widget_dict_groups.field_value(1)
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入{self.dict_type}類別',
            old_groups,
            QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        dict_groups_name = input_dialog.textValue()
        data = [
            dict_groups_name,
        ]

        sql = f'''
            UPDATE dict_groups
            SET
                DictGroupsTopLevel = "{dict_groups_name}"
            WHERE
                DictGroupsType = "{self.dict_type}" AND
                DictGroupsTopLevel = "{old_groups}"
        '''
        self.database.exec_sql(sql)

        fields = ['DictGroupsName']
        self.database.update_record(
            'dict_groups', fields, 'DictGroupsKey',
            self.table_widget_dict_groups.field_value(0), data
        )
        self.ui.tableWidget_dict_groups.item(
            self.ui.tableWidget_dict_groups.currentRow(), 1
        ).setText(dict_groups_name)

    # 新增病名類別
    def _add_groups_name(self):
        dict_groups = self.table_widget_dict_groups.field_value(1)
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}分類',
            f'請輸入{self.dict_type}分類名稱', None,
            QInputDialog.TextInput, 320, 200
        )
        ok = input_dialog.exec_()
        if not ok:
            return

        groups_name = input_dialog.textValue()
        field = ['DictGroupsType', 'DictGroupsTopLevel', 'DictGroupsName']
        data = [
            self.dict_type, dict_groups, groups_name
        ]
        self.database.insert_record('dict_groups', field, data)
        self._read_dict_groups_name(dict_groups)

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
        data = [
            dict_groups_name,
        ]

        sql = f'''
            UPDATE
                clinic set Groups = "{dict_groups_name}"
            WHERE
                ClinicType = "{self.dict_type}" AND
                Groups = "{old_groups_name}"
        '''
        self.database.exec_sql(sql)

        fields = ['DictGroupsName']
        self.database.update_record('dict_groups', fields, 'DictGroupsKey',
                                    self.table_widget_dict_groups_name.field_value(0), data)
        self.ui.tableWidget_dict_groups_name.item(
            self.ui.tableWidget_dict_groups_name.currentRow(), 1).setText(dict_groups_name)

    # 新增舌診
    def _add_disease(self):
        groups_name = self.table_widget_dict_groups_name.field_value(1)
        dialog = dialog_utils.get_dialog_input_disease(
            self, self.database, self.system_settings, groups_name, '病名詞庫')
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

        disease_key = self.table_widget_dict_disease.field_value(0)
        sql = f'''
            UPDATE icd10
            SET
                Groups = NULL
            WHERE
                ICD10Key = {disease_key}
        '''
        self.database.exec_sql(sql)
        self.ui.tableWidget_dict_disease.removeRow(self.ui.tableWidget_dict_disease.currentRow())

    # 更改舌診
    def _edit_disease(self):
        disease_key = self.table_widget_dict_disease.field_value(0)
        dialog = dialog_utils.get_dialog_edit_disease(self, self.database, self.system_settings, disease_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f'''
            SELECT * FROM icd10
            WHERE
                ICD10Key = {disease_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self._set_dict_disease_data(self.ui.tableWidget_dict_disease.currentRow(), row_data)

    def _find_disease(self):
        keyword = self.ui.lineEdit_find_disease.text()

        if keyword == '':
            self.dict_groups_name_changed()
        else:
            sql = f'''
                SELECT * FROM icd10 WHERE
                (
                    ICDCode LIKE "{keyword}%" OR
                    InputCode LIKE "{keyword}%" OR
                    ChineseName LIKE "%{keyword}%"
                )
            '''
            self.table_widget_dict_disease.set_db_data(sql, self._set_dict_disease_data)

        self.ui.lineEdit_find_disease.setFocus(True)
        self.ui.lineEdit_find_disease.setCursorPosition(len(keyword))

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()


# 主程式
def main():
    app = QtWidgets.QApplication(sys.argv)
    widget = DictDisease()
    widget.show()
    sys.exit(app.exec_())


# 程式開始
if __name__ == '__main__':
    main()

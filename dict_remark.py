# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils


# 備註詞庫 2018.04.14
class DictRemark(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictRemark, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.dict_type = '備註'

        self._set_ui()
        self._set_signal()
        self._read_remark()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_REMARK, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_dict_groups = class_utils.get_table_widget(self.ui.tableWidget_dict_groups, self.database)
        self.table_widget_dict_groups.set_column_hidden([0])
        self.table_widget_dict_groups_name = class_utils.get_table_widget(
            self.ui.tableWidget_dict_groups_name, self.database
        )
        self.table_widget_dict_groups_name.set_column_hidden([0])
        self.table_widget_dict_remark = class_utils.get_table_widget(self.ui.tableWidget_dict_remark, self.database)
        self.table_widget_dict_remark.set_column_hidden([0])
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
        self.ui.toolButton_add_remark.clicked.connect(self._add_remark)
        self.ui.toolButton_remove_remark.clicked.connect(self._remove_remark)
        self.ui.toolButton_edit_remark.clicked.connect(self._edit_remark)
        self.ui.tableWidget_dict_remark.doubleClicked.connect(self._edit_remark)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 180]
        dict_remark_width = [100, 180, 180, 750]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_groups_name.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_remark.set_table_heading_width(dict_remark_width)

    def _read_remark(self):
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
        self.ui.groupBox_dict_remark.setTitle(f'{self.dict_type}資料 - [{dict_groups_name}]')
        self._read_dict_remark(dict_groups_name)
        self.ui.tableWidget_dict_groups_name.setFocus(True)

    def _read_dict_remark(self, dict_groups_name):
        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{self.dict_type}" AND
                Groups = "{dict_groups_name}"
            ORDER BY ClinicCode, ClinicName
        '''
        self.table_widget_dict_remark.set_db_data(sql, self._set_dict_remark_data)

    def _set_dict_remark_data(self, rec_no, rec):
        dict_remark_rec = [
            string_utils.xstr(rec['ClinicKey']),
            string_utils.xstr(rec['ClinicCode']),
            string_utils.xstr(rec['InputCode']),
            string_utils.xstr(rec['ClinicName']),
        ]

        for column in range(len(dict_remark_rec)):
            self.ui.tableWidget_dict_remark.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(dict_remark_rec[column])
            )

    # 新增主訴類別
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

    # 移除主訴類別
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

    # 更改主訴類別
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
        self.database.update_record('dict_groups', fields, 'DictGroupsKey',
                                    self.table_widget_dict_groups.field_value(0), data)
        self.ui.tableWidget_dict_groups.item(self.ui.tableWidget_dict_groups.currentRow(), 1).setText(dict_groups_name)

    # 新增主訴類別
    def _add_groups_name(self):
        dict_groups = self.table_widget_dict_groups.field_value(1)
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}分類',
            f'請輸入{self.dict_type}分類名稱',
            None, QInputDialog.TextInput, 320, 200
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

    # 移除主訴類別
    def _remove_groups_name(self):
        dict_groups_name = self.table_widget_dict_groups_name.field_value(1)
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}分類資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除 [{dict_groups_name}] {self.dict_type}分類?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_groups_name.field_value(0)
        self.database.delete_record('dict_groups', 'DictGroupsKey', key)
        self.ui.tableWidget_dict_groups_name.removeRow(self.ui.tableWidget_dict_groups_name.currentRow())

    # 修改主訴類別
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
            UPDATE clinic
            SET
                Groups = "{dict_groups_name}"
            WHERE
                ClinicType = "{self.dict_type}" AND
                Groups = "{old_groups_name}"
        '''
        self.database.exec_sql(sql)

        fields = ['DictGroupsName']
        self.database.update_record(
            'dict_groups', fields, 'DictGroupsKey',
            self.table_widget_dict_groups_name.field_value(0), data
        )
        self.ui.tableWidget_dict_groups_name.item(
            self.ui.tableWidget_dict_groups_name.currentRow(), 1).setText(dict_groups_name)

    # 新增主訴
    def _add_remark(self):
        dialog = dialog_utils.get_dialog_input_diagnostic(self, self.database, self.system_settings, None)
        result = dialog.exec_()
        if result != 0:
            current_row = self.ui.tableWidget_dict_remark.rowCount()
            self.ui.tableWidget_dict_remark.insertRow(current_row)
            dict_groups_name = self.table_widget_dict_groups_name.field_value(1)
            fields = ['ClinicType', 'ClinicCode', 'InputCode', 'ClinicName', 'Groups']
            data = [
                self.dict_type,
                dialog.ui.lineEdit_diagnostic_code.text(),
                dialog.ui.lineEdit_input_code.text(),
                dialog.ui.lineEdit_diagnostic_name.text(),
                dict_groups_name,
            ]
            self.database.insert_record('clinic', fields, data)
            self._read_dict_remark(dict_groups_name)

        dialog.close_all()
        dialog.deleteLater()

    # 移l除備註
    def _remove_remark(self):
        remark_name = self.table_widget_dict_remark.field_value(3)
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除{self.dict_type}: "{remark_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_remark.field_value(0)
        self.database.delete_record('clinic', 'ClinicKey', key)
        self.ui.tableWidget_dict_remark.removeRow(self.ui.tableWidget_dict_remark.currentRow())

    # 更改主訴
    def _edit_remark(self):
        clinic_key = self.table_widget_dict_remark.field_value(0)
        dialog = dialog_utils.get_dialog_input_diagnostic(self, self.database, self.system_settings, clinic_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicKey = {clinic_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self._set_dict_remark_data(self.ui.tableWidget_dict_remark.currentRow(), row_data)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

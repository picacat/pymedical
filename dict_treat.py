# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QFileDialog
import json

from libs import class_utils

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import dialog_utils
from libs import number_utils
from libs import db_utils
from libs import personnel_utils


# 處置詞庫 2018.04.14
class DictTreat(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictTreat, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.dict_type = '處置'
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._read_treat()

        self.groups_col_no = {
            'dict_groups_key': 0,
            'dict_order_no': 1,
            'dict_groups_name': 2,
            'dict_groups_percent': 3,
            'dict_groups_field_name': 4,
        }

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_TREAT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_dict_groups = class_utils.get_table_widget(self.ui.tableWidget_dict_groups, self.database)
        self.table_widget_dict_groups.set_column_hidden([0, 1])
        self.table_widget_dict_treat = class_utils.get_table_widget(self.ui.tableWidget_dict_treat, self.database)
        self.table_widget_dict_treat.set_column_hidden([0])
        self._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups.itemSelectionChanged.connect(self.dict_groups_changed)
        self.ui.toolButton_add_dict_groups.clicked.connect(self._add_dict_groups)
        self.ui.toolButton_charge_field.clicked.connect(self._add_charge_field)
        self.ui.toolButton_remove_dict_groups.clicked.connect(self._remove_dict_groups)
        self.ui.toolButton_edit_dict_groups.clicked.connect(self._edit_dict_groups)
        self.ui.tableWidget_dict_groups.doubleClicked.connect(self._edit_dict_groups)
        self.ui.toolButton_add_treat.clicked.connect(self._add_treat)
        self.ui.toolButton_remove_treat.clicked.connect(self._remove_treat)
        self.ui.toolButton_edit_treat.clicked.connect(self._edit_treat)
        self.ui.tableWidget_dict_treat.doubleClicked.connect(self._edit_treat)
        self.ui.tableWidget_dict_treat.itemSelectionChanged.connect(self.dict_treat_changed)
        self.ui.lineEdit_search_treat.textChanged.connect(self._search_treat)

        self.ui.toolButton_cut_drug.clicked.connect(self._cut_treat)
        self.ui.toolButton_copy_drug.clicked.connect(self._copy_treat)
        self.ui.toolButton_export.clicked.connect(self._export_treat)
        self.ui.toolButton_import.clicked.connect(self._import_treat)

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 100, 115, 60, 110]
        dict_treat_width = [100, 100, 90, 300, 250, 100, 120, 150, 100, 100, 70, 120]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)
        self.table_widget_dict_treat.set_table_heading_width(dict_treat_width)

    def _read_treat(self):
        self._read_dict_groups()

    def _read_dict_groups(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}類別"
            ORDER BY DictGroupsKey
        '''
        self.table_widget_dict_groups.set_db_data(sql, self._set_dict_groups_data)

    # def _set_dict_groups_data(self, rec_no, rec):
    #     dict_groups_rec = [
    #         string_utils.xstr(rec['DictGroupsKey']),
    #         string_utils.xstr(rec['DictGroupsName']),
    #     ]

    #     for column in range(len(dict_groups_rec)):
    #         self.ui.tableWidget_dict_groups.setItem(
    #             rec_no, column,
    #             QtWidgets.QTableWidgetItem(dict_groups_rec[column])
    #         )

    def _set_dict_groups_data(self, row_no, row):
        if row['DictGroupsLevel2'] is None:
            percent = ''
        else:
            try:
                value = number_utils.get_integer(row['DictGroupsLevel2'])
                percent = f'{value}%'
            except ValueError:
                percent = string_utils.xstr(row['DictGroupsLevel2'])

        dict_groups_row = [
            string_utils.xstr(row['DictGroupsKey']),
            string_utils.xstr(row['DictOrderNo']),
            string_utils.xstr(row['DictGroupsName']),
            percent,
            string_utils.xstr(row['DictGroupsTopLevel']),
        ]

        for column in range(len(dict_groups_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, dict_groups_row[column])
            self.ui.tableWidget_dict_groups.setItem(
                row_no, column, item,
            )
            if column in [3]:
                self.ui.tableWidget_dict_groups.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def dict_groups_changed(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(2)
        self._read_dict_treat(dict_groups_type)
        self.ui.tableWidget_dict_groups.setFocus(True)

    def _read_dict_treat(self, dict_groups_type, keyword=None):
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineType = "{dict_groups_type}"
        '''
        if keyword is not None:
            sql += keyword

        sql += ' ORDER BY MedicineCode, MedicineName'
        self.table_widget_dict_treat.set_db_data(sql, self._set_dict_treat_data)
        medicine_key = self.table_widget_dict_treat.field_value(0)
        self._read_treat_description(medicine_key)

    def _set_dict_treat_data(self, row_no, row):
        deactivate = string_utils.xstr(row['Deactivate'])

        dict_treat_row = [
            string_utils.xstr(row['MedicineKey']),
            string_utils.xstr(row['MedicineCode']),
            string_utils.xstr(row['InputCode']),
            string_utils.xstr(row['MedicineName']),
            string_utils.xstr(row['MedicineAlias']),
            string_utils.xstr(row['InsCode']),
            string_utils.xstr(row['Unit']),
            string_utils.xstr(row['MedicineMode']),
            number_utils.get_float(row['InPrice']),
            number_utils.get_float(row['SalePrice']),
            string_utils.xstr(row['Commission']),
            deactivate,
        ]

        for col_no in range(len(dict_treat_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, dict_treat_row[col_no])
            self.ui.tableWidget_dict_treat.setItem(row_no, col_no, item)

            if col_no in [8, 9, 10]:
                self.ui.tableWidget_dict_treat.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            if deactivate != '':
                self.ui.tableWidget_dict_treat.item(row_no, col_no).setForeground(
                    QtGui.QColor('gray')
                )

    # 更改處方類別
    def _add_charge_field(self):
        items = ['自費藥費', '水藥費', '高貴藥費', '自費針灸費', '民俗調理費', '自費材料費', '自費診察費']

        dict_groups_key = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_key'])
        dict_groups = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_name'])
        charge_field = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_field_name'])

        try:
            index = items.index(charge_field)
        except ValueError:
            index = 0

        item, ok = QInputDialog.getItem(
            self,
            f'{self.dict_type}類別',
            f'請選擇「{dict_groups}類別」的自費批價欄位',
            items, index, False
        )

        if not ok:
            return

        sql = f'''
            UPDATE dict_groups
            SET
                DictGroupsTopLevel = "{item}"
            WHERE
                DictGroupsKey = {dict_groups_key}
        '''
        self.database.exec_sql(sql)
        self._read_dict_groups()


    # # 新增主訴類別
    # def _add_dict_groups(self):
    #     input_dialog = dialog_utils.get_dialog(
    #         f'{self.dict_type}類別',
    #         f'請輸入{self.dict_type}類別',
    #         None, QInputDialog.TextInput, 320, 200
    #     )
    #     ok = input_dialog.exec_()
    #     if not ok:
    #         return

    #     dict_groups = input_dialog.textValue()
    #     field = ['DictGroupsType', 'DictGroupsName']
    #     data = [
    #         f'{self.dict_type}類別', dict_groups,
    #     ]
    #     self.database.insert_record('dict_groups', field, data)
    #     self._read_dict_groups()

    # 新增處方類別
    def _add_dict_groups(self):
        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入{self.dict_type}類別',
            None, QInputDialog.TextInput, 320, 200
        )
        if not input_dialog.exec_():
            return

        dict_groups = input_dialog.textValue()
        if dict_groups == '':
            return

        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入「{dict_groups}類別」的抽成',
            None, QInputDialog.TextInput, 320, 200
        )
        if not input_dialog.exec_():
            return

        dict_groups_percent = input_dialog.textValue().strip('%')

        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.dict_type}類別"
            ORDER BY DictOrderNo DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        last_dict_order_no = number_utils.get_integer(rows[0]['DictOrderNo'])

        field = [
            'DictGroupsType', 'DictOrderNo', 'DictGroupsName', 'DictGroupsLevel2'
        ]

        data = [
            f'{self.dict_type}類別',
            last_dict_order_no+1,
            dict_groups,
            dict_groups_percent,
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

    # # 更改主訴類別
    # def _edit_dict_groups(self):
    #     old_groups = self.table_widget_dict_groups.field_value(1)
    #     input_dialog = dialog_utils.get_dialog(
    #         f'{self.dict_type}類別',
    #         f'請輸入{self.dict_type}類別',
    #         old_groups,
    #         QInputDialog.TextInput, 320, 200
    #     )
    #     ok = input_dialog.exec_()
    #     if not ok:
    #         return

    #     dict_groups_name = input_dialog.textValue()
    #     data = [
    #         dict_groups_name,
    #     ]

    #     sql = f'''
    #         UPDATE dict_groups
    #         SET
    #             DictGroupsTopLevel = "{dict_groups_name}"
    #         WHERE
    #             DictGroupsType = "{self.dict_type}" AND
    #             DictGroupsTopLevel = "{old_groups}"
    #     '''
    #     self.database.exec_sql(sql)

    #     fields = ['DictGroupsName']
    #     self.database.update_record('dict_groups', fields, 'DictGroupsKey',
    #                                 self.table_widget_dict_groups.field_value(0), data)
    #     self.ui.tableWidget_dict_groups.item(self.ui.tableWidget_dict_groups.currentRow(), 1).setText(dict_groups_name)

    # 更改處方類別
    def _edit_dict_groups(self):
        old_groups = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_name'])

        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入{self.dict_type}類別',
            old_groups,
            QInputDialog.TextInput, 320, 200
        )
        if not input_dialog.exec_():
            return

        dict_groups_name = input_dialog.textValue()
        if dict_groups_name == '':
            return

        old_percent = self.table_widget_dict_groups.field_value(
            self.groups_col_no['dict_groups_percent']).strip('%')

        input_dialog = dialog_utils.get_dialog(
            f'{self.dict_type}類別',
            f'請輸入「{dict_groups_name}類別」的抽成',
            old_percent,
            QInputDialog.TextInput, 320, 200
        )
        if not input_dialog.exec_():
            return

        dict_groups_percent = input_dialog.textValue().strip('%')

        data = [
            dict_groups_name,
            dict_groups_percent,
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

        fields = ['DictGroupsName', 'DictGroupsLevel2']
        self.database.update_record(
            'dict_groups', fields, 'DictGroupsKey',
            self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_key']), data
        )

        dict_groups_key = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_key'])
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsKey = {dict_groups_key}
        '''
        row = self.database.select_record(sql)[0]
        self._set_dict_groups_data(self.ui.tableWidget_dict_groups.currentRow(), row)

        sql = f'''
            UPDATE medicine
            SET
                MedicineType = "{dict_groups_name}"
            WHERE
                MedicineType = "{old_groups}"
        '''
        self.database.exec_sql(sql)

    # 新增主訴
    def _add_treat(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(2)

        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, dict_groups_type, None)
        result = dialog.exec_()
        if result != 0:
            self._read_dict_treat(dict_groups_type)

        dialog.close_all()
        dialog.deleteLater()

    # 移除主訴
    def _remove_treat(self):
        selected = self.ui.tableWidget_dict_treat.selectedRanges()
        treat_list = []
        for item in selected:
            for row_no in range(item.topRow(), item.bottomRow() + 1):
                treat_list.append(self.ui.tableWidget_dict_treat.item(row_no, 0).text())

        if len(treat_list) > 1:
            self._remove_multiple_treats(treat_list)
        else:
            self._remove_single_treat()

    def _remove_multiple_treats(self, treat_list):
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}資料',
            QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除選取的處置資料?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )

        remove_record = msg_box.exec_()
        if not remove_record:
            return

        treat_list = str(treat_list)[1:-1]
        sql = f'''
            DELETE FROM medicine
            WHERE
                MedicineKey IN ({treat_list})
        '''
        self.database.exec_sql(sql)
        dict_groups_type = self.table_widget_dict_groups.field_value(self.groups_col_no['dict_groups_name'])
        self._read_dict_treat(dict_groups_type)

    def _remove_single_treat(self):
        treat_name = self.table_widget_dict_treat.field_value(3)
        msg_box = dialog_utils.get_message_box(
            f'刪除{self.dict_type}資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除{self.dict_type}: "{treat_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_treat.field_value(0)
        self.database.delete_record('medicine', 'MedicineKey', key)
        self.ui.tableWidget_dict_treat.removeRow(self.ui.tableWidget_dict_treat.currentRow())

    # 更改主訴
    def _edit_treat(self):
        medicine_key = self.table_widget_dict_treat.field_value(0)
        dialog = dialog_utils.get_dialog_input_drug(
            self, self.database, self.system_settings, None, medicine_key)
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        '''
        row_data = self.database.select_record(sql)[0]
        self._set_dict_treat_data(self.ui.tableWidget_dict_treat.currentRow(), row_data)
        self.dict_treat_changed()

    def dict_treat_changed(self):
        medicine_key = self.table_widget_dict_treat.field_value(0)
        self._read_treat_description(medicine_key)

    def _read_treat_description(self, medicine_key):
        self.ui.textEdit_description.setText('')

        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = "{medicine_key}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        try:
            self.ui.textEdit_description.setText(string_utils.get_str(rows[0]['Description'], 'utf8'))
        except TypeError:
            pass

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

    def _search_treat(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        keyword = self.ui.lineEdit_search_treat.text()

        if keyword == '':
            self._read_dict_treat(dict_groups_type)
        else:
            script = f'''
                AND
                (InputCode LIKE "{keyword}%" OR MedicineName LIKE "%{keyword}%")
            '''
            self._read_dict_treat(dict_groups_type, script)

        self.ui.lineEdit_search_treat.setFocus(True)
        self.ui.lineEdit_search_treat.setCursorPosition(len(keyword))

    # 複製處置
    def _copy_treat(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)

        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType IN ("處置類別", "藥品類別")
            ORDER BY DictGroupsType, DictOrderNo
        '''

        rows = self.database.select_record(sql)
        items = ()
        for row in rows:
            dict_groups_name = string_utils.xstr(row['DictGroupsName'])
            if dict_groups_name == dict_groups_type:
                continue

            items += (dict_groups_name, )

        medicine_type, ok = QInputDialog.getItem(
            self, "拷貝處置詞庫", "請選擇拷貝到何處", items, 0, False
        )

        if not ok:
            return

        selected = self.ui.tableWidget_dict_treat.selectedRanges()
        treat_list = []
        for item in selected:
            for row_no in range(item.topRow(), item.bottomRow() + 1):
                treat_list.append(self.ui.tableWidget_dict_treat.item(row_no, 0).text())

        fields = [
            'MedicineType', 'MedicineMode', 'MedicineCode', 'InputCode', 'InsCode',
            'MedicineName', 'MedicineAlias', 'Unit', 'Dosage', 'Location',
            'SalePrice', 'InPrice', 'Charged', 'SafeQuantity', 'Description',
        ]
        for medicine_key in treat_list:
            sql = f'''
                SELECT * FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            row = rows[0]
            data = [
                medicine_type,
                string_utils.xstr(row['MedicineMode']),
                string_utils.xstr(row['MedicineCode']),
                string_utils.xstr(row['InputCode']),
                string_utils.xstr(row['InsCode']),
                string_utils.xstr(row['MedicineName']),
                string_utils.xstr(row['MedicineAlias']),
                string_utils.xstr(row['Unit']),
                string_utils.xstr(row['Dosage']),
                string_utils.xstr(row['Location']),
                string_utils.xstr(row['SalePrice']),
                string_utils.xstr(row['InPrice']),
                string_utils.xstr(row['Charged']),
                string_utils.xstr(row['SafeQuantity']),
                string_utils.get_str(row['Description'], 'utf8'),
            ]
            self.database.insert_record('medicine', fields, data)

        if dict_groups_type == medicine_type:
            self._read_dict_treat(dict_groups_type)

    # 剪下處置
    def _cut_treat(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        sql = '''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType IN ("處置類別", "藥品類別")
            ORDER BY DictGroupsType, DictOrderNo
        '''

        rows = self.database.select_record(sql)
        items = ()
        for row in rows:
            dict_groups_name = string_utils.xstr(row['DictGroupsName'])
            if dict_groups_name == dict_groups_type:
                continue

            items += (dict_groups_name, )

        medicine_type, ok = QInputDialog.getItem(
            self, "剪下處置詞庫", "請選擇貼到到何處", items, 0, False
        )

        if not ok:
            return

        selected = self.ui.tableWidget_dict_treat.selectedRanges()
        treat_list = []
        for item in selected:
            for row_no in range(item.topRow(), item.bottomRow() + 1):
                treat_list.append(self.ui.tableWidget_dict_treat.item(row_no, 0).text())

        for medicine_key in treat_list:
            sql = f'''
                UPDATE medicine
                SET MedicineType = "{medicine_type}"
                WHERE
                    MedicineKey = {medicine_key}
            '''
            self.database.exec_sql(sql)

        self._read_dict_treat(dict_groups_type)

    def _export_treat(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)

        options = QFileDialog.Options()
        json_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出處置JSON檔案",
            f'{dict_groups_type}資料.json',
            "json檔案 (*.json)",
            options=options
        )
        if not json_file_name:
            return

        selected = self.ui.tableWidget_dict_treat.selectedRanges()
        treat_list = []
        for item in selected:
            for row_no in range(item.topRow(), item.bottomRow() + 1):
                treat_list.append(self.ui.tableWidget_dict_treat.item(row_no, 0).text())

        drug_list = str(treat_list)[1:-1]
        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey IN ({drug_list})
        '''
        rows = self.database.select_record(sql)

        json_data = db_utils.mysql_to_json(rows)
        text_file = open(json_file_name, "w", encoding='utf8')
        text_file.write(str(json_data))
        text_file.close()

        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯出完成',
            f'<h3>處置匯出資料{json_file_name}匯出完成.</h3>',
            'JSON 檔案格式.'
        )

    def _import_treat(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "開啟處置JSON檔",
            '*.json', "json 檔 (*.json);;", options=options
        )
        if not file_name:
            return

        dict_groups_type = self.table_widget_dict_groups.field_value(2)
        fields = [
            'MedicineType', 'MedicineCode', 'InputCode', 'MedicineName', 'Unit', 'MedicineMode', 'InsCode',
            'Dosage', 'MedicineAlias', 'Location', 'InPrice', 'SalePrice', 'Commission',
            'Quantity', 'SafeQuantity',
            'Description',
        ]

        with open(file_name, encoding='utf8') as json_file:
            rows = json.load(json_file)
            for row in rows:
                data = [
                    dict_groups_type,
                    row['MedicineCode'],
                    row['InputCode'],
                    row['MedicineName'],
                    row['Unit'],
                    row['MedicineMode'],
                    row['InsCode'],
                    row['Dosage'],
                    row['MedicineAlias'],
                    row['Location'],
                    row['InPrice'],
                    row['SalePrice'],
                    row['Commission'],
                    row['Quantity'],
                    row['SafeQuantity'],
                    row['Description'],
                ]
                self.database.insert_record('medicine', fields, data)

        self._read_dict_treat(dict_groups_type)

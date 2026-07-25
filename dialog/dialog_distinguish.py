
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import class_utils
from libs import db_utils


# 主視窗
class DialogDistinguish(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDistinguish, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.groups = args[2]
        self.text_edit = args[3]
        self.text_edit_cure = args[4]

        self.ui = None
        self.diagnostic_type = '辨證'

        self._set_ui()
        self._set_signal()
        self._read_groups_name()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DISTINGUISH, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_groups = class_utils.get_table_widget(self.ui.tableWidget_groups, self.database)
        self.table_widget_distinguish = class_utils.get_table_widget(self.ui.tableWidget_distinguish, self.database)
        # self.table_widget_groups.set_column_hidden([0])
        self.table_widget_distinguish.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_name_changed)
        self.ui.tableWidget_distinguish.clicked.connect(self.add_dict)
        self.ui.tableWidget_groups.keyPressEvent = self._table_widget_key_press
        self.ui.tableWidget_distinguish.keyPressEvent = self._table_widget_key_press

    def _table_widget_key_press(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.parent.close()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_distinguish, event)

    # 設定欄位寬度
    def _set_table_width(self):
        distinguish_width = [100, 240, 240]
        self.table_widget_distinguish.set_table_heading_width(distinguish_width)

    def _read_groups_name(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.diagnostic_type}" AND
                DictGroupsTopLevel = "{self.groups}"
            ORDER BY DictGroupsName
        '''
        # self.table_widget_groups.set_db_data(sql, self._set_groups_name_data)
        self.table_widget_groups.set_db_data_without_heading(sql, 'DictGroupsName')

    def _set_groups_name_data(self, rec_no, rec):
        groups_name_rec = [
            string_utils.xstr(rec['DictGroupsKey']),
            string_utils.xstr(rec['DictGroupsName']),
        ]

        for column in range(len(groups_name_rec)):
            self.ui.tableWidget_groups.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(groups_name_rec[column])
            )

    def groups_name_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        groups_name = self.ui.tableWidget_groups.selectedItems()[0].text()
        self._read_distinguish(groups_name)
        self.ui.tableWidget_groups.setFocus(True)

    def _read_distinguish(self, groups_name):
        order_type = 'ORDER BY ClinicCode, ClinicName'
        if self.system_settings.field('診察詞庫排序') == '點擊率':
            order_type = 'ORDER BY HitRate DESC'
        elif self.system_settings.field('診察詞庫排序') == '最後點擊時戳':
            order_type = 'ORDER BY TimeStamp DESC'

        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{self.diagnostic_type}" AND
                Groups = "{groups_name}"
                {order_type}
        '''
        self.table_widget_distinguish.set_db_data(sql, self._set_distinguish_data)

    def _set_distinguish_data(self, rec_no, rec):
        distinguish_row = [
            string_utils.xstr(rec['ClinicKey']),
            string_utils.xstr(rec['ClinicName']),
            string_utils.xstr(rec['Position']),
        ]

        for column in range(len(distinguish_row)):
            self.ui.tableWidget_distinguish.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(distinguish_row[column])
            )

    def _get_clinic_key(self, groups_name, symptom_name):
        sql = f'''
            SELECT ClinicKey FROM clinic
            WHERE
                ClinicType = "{self.diagnostic_type}" AND
                Groups = "{groups_name}" AND
                ClinicName = "{symptom_name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        clinic_key = row['ClinicKey']

        return clinic_key

    def add_dict(self):
        groups_name = self.ui.tableWidget_groups.selectedItems()[0].text()
        selected_item = self.ui.tableWidget_distinguish.selectedItems()[0].text()
        clinic_key = self._get_clinic_key(groups_name, selected_item)

        selected_distinguish = self.table_widget_distinguish.field_value(1)
        selected_cure = self.table_widget_distinguish.field_value(2)

        self._add_dict_to_text_edit(self.text_edit, selected_distinguish)
        self._add_dict_to_text_edit(self.text_edit_cure, selected_cure)

        if clinic_key is not None:
            db_utils.increment_hit_rate(self.database, 'clinic', 'ClinicKey', clinic_key)

        # self.parent.close()

    def _add_dict_to_text_edit(self, text_edit, selected_text):
        text = text_edit.text()
        text += ', ' + selected_text \
            if str(text).strip() != '' and len(str(text).strip()) > 0 \
            else selected_text
        text_edit.setText(string_utils.get_str(text, 'utf8'))
        text_edit.setModified(True)

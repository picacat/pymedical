
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
class DialogCure(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCure, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.groups = args[2]
        self.text_edit = args[3]

        self.ui = None
        self.diagnostic_type = '治則'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CURE, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.table_widget_groups = class_utils.get_table_widget(self.ui.tableWidget_groups, self.database)
        self.table_widget_cure = class_utils.get_table_widget(self.ui.tableWidget_cure, self.database)
        self.table_widget_groups.set_column_hidden([0])
        self.table_widget_cure.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_name_changed)
        self.ui.tableWidget_cure.clicked.connect(self.add_cure)
        self.ui.tableWidget_groups.keyPressEvent = self._table_widget_key_press
        self.ui.tableWidget_cure.keyPressEvent = self._table_widget_key_press

    def _table_widget_key_press(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.parent.close()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_cure, event)

    # 設定欄位寬度
    def _set_table_width(self):
        groups_width = [100, 200]
        cure_width = [100, 800]
        self.table_widget_groups.set_table_heading_width(groups_width)
        self.table_widget_cure.set_table_heading_width(cure_width)

    def _read_groups_name(self):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType = "{self.diagnostic_type}" AND
                DictGroupsTopLevel = "{self.groups}"
            ORDER BY DictGroupsName
        '''
        self.table_widget_groups.set_db_data(sql, self._set_groups_name_data)

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
        groups_name = self.table_widget_groups.field_value(1)
        self._read_cure(groups_name)
        self.ui.tableWidget_groups.setFocus(True)

    def _read_cure(self, groups_name):
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
        self.table_widget_cure.set_db_data(sql, self._set_cure_data)

    def _set_cure_data(self, rec_no, rec):
        cure_rec = [
            string_utils.xstr(rec['ClinicKey']),
            string_utils.xstr(rec['ClinicName']),
        ]

        for column in range(len(cure_rec)):
            self.ui.tableWidget_cure.setItem(
                rec_no, column,
                QtWidgets.QTableWidgetItem(cure_rec[column])
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

    def add_cure(self):
        groups_name = self.ui.tableWidget_groups.selectedItems()[0].text()
        selected_item = self.ui.tableWidget_cure.selectedItems()[0].text()
        clinic_key = self._get_clinic_key(groups_name, selected_item)

        selected_cure = self.table_widget_cure.field_value(1)
        cure = self.text_edit.text()
        cure += '，' + selected_cure \
            if str(cure).strip()[-1:] not in ['，', ',', ':', '='] and len(str(cure).strip()) > 0 \
            else selected_cure
        self.text_edit.setText(string_utils.get_str(cure, 'utf8'))
        self.text_edit.setModified(True)

        if clinic_key is not None:
            db_utils.increment_hit_rate(self.database, 'clinic', 'ClinicKey', clinic_key)

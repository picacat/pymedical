
# 主訴舌診脈象詞庫
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from libs import ui_utils
from libs import system_utils
from libs import db_utils
from libs import class_utils


# 主訴舌診脈象詞庫
class DialogSymptom(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSymptom, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.groups = args[2]
        self.text_edit = args[3]

        self.ui = None
        self.diagnostic_type = '主訴'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SYMPTOM, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        self.table_widget_symptom = class_utils.get_table_widget(self.ui.tableWidget_symptom, self.database)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_groups.itemSelectionChanged.connect(self.groups_name_changed)
        self.ui.tableWidget_symptom.clicked.connect(self.add_symptom)
        self.ui.tableWidget_groups.keyPressEvent = self._table_widget_key_press
        self.ui.tableWidget_symptom.keyPressEvent = self._table_widget_key_press

    def _table_widget_key_press(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.parent.close()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_symptom, event)

    def _read_groups_name(self):
        sql = f'''
            SELECT DictGroupsName FROM dict_groups
            WHERE
                DictGroupsType = "{self.diagnostic_type}" AND
                DictGroupsTopLevel = "{self.groups}"
            ORDER BY DictGroupsName
        '''

        rows = self.database.select_record(sql)
        record_count = len(rows)
        row_count = self.ui.tableWidget_groups.rowCount()

        columns = int(record_count / row_count)
        if record_count % row_count > 0:
            columns += 1

        for col_no in range(columns):
            for row_no in range(row_count):
                index = col_no * row_count + row_no
                if index >= record_count:
                    break

                self.ui.tableWidget_groups.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(rows[index]['DictGroupsName'])
                )

        self.ui.tableWidget_groups.setCurrentCell(0, 0)

    def groups_name_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        groups_name = self.ui.tableWidget_groups.selectedItems()[0].text()
        self._read_symptom(groups_name)
        # self.ui.tableWidget_groups.setFocus(True)
        self.parent.lineEdit_query.setText('')
        self.parent.lineEdit_query.setFocus()

    def _read_symptom(self, groups_name):
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
        self.table_widget_symptom.set_db_data_without_heading(sql, 'ClinicName')

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

    def add_symptom(self):
        groups_name = self.ui.tableWidget_groups.selectedItems()[0].text()
        selected_symptom = self.ui.tableWidget_symptom.selectedItems()[0].text()
        clinic_key = self._get_clinic_key(groups_name, selected_symptom)

        if self.system_settings.field('主訴換行') == 'Y':
            self.parent.parent.insert_text(self.text_edit, selected_symptom+'\n', '', insert_comma=False)
        else:
            self.parent.parent.insert_text(self.text_edit, selected_symptom, '')

        if clinic_key is not None:
            db_utils.increment_hit_rate(self.database, 'clinic', 'ClinicKey', clinic_key)

        self.text_edit.document().setModified(True)
        self.parent.reset_query()

        if not self.ui.tableWidget_symptom.selectedItems():
            return

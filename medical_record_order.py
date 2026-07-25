# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from libs import (class_utils, dialog_utils, nhi_utils, string_utils,
                  system_utils, ui_utils)


# 病歷資料-醫囑 2020.08.28
class MedicalRecordOrder(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordOrder, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.call_from = args[3]

        self.treat_type = None
        self.doctor_done = False
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_medical_record()
        self._read_order()

        self.user_name = system_utils.get_user_name(self.system_settings)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_ORDER, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_order = class_utils.get_table_widget(self.ui.tableWidget_order, self.database)
        self._set_table_width()

    def _set_table_width(self):
        width = [480]
        self.table_widget_order.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_order.clicked.connect(self.append_null_order)
        self.ui.toolButton_remove_order.clicked.connect(self.remove_order)
        self.ui.toolButton_dictionary.clicked.connect(self.open_dict)
        self.ui.tableWidget_order.keyPressEvent = self._table_widget_order_key_press

    def _read_medical_record(self):
        sql = f'''
            SELECT TreatType, DoctorDone FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self.treat_type = string_utils.xstr(row['TreatType'])
        if row['DoctorDone'] == 'True':
            self.doctor_done = True

    def _table_widget_order_key_press(self, event):
        system_utils.set_keyboard_layout('英文')

        key = event.key()
        current_row = self.ui.tableWidget_order.currentRow()

        if key == QtCore.Qt.Key_Delete:
            self.remove_order()
        elif key == QtCore.Qt.Key_Up:
            if self.ui.tableWidget_order.item(current_row, 0) is None:
                self.ui.tableWidget_order.removeRow(current_row)
                return
        elif key == QtCore.Qt.Key_Down:
            if current_row == self.ui.tableWidget_order.rowCount() - 1 and \
                    self.ui.tableWidget_order.item(current_row, 0) is not None:
                self.append_null_order()

        return QtWidgets.QTableWidget.keyPressEvent(self.ui.tableWidget_order, event)

    def get_order_count(self):
        sql = f'''
            SELECT Content FROM caseextend
            WHERE
                CaseKey = {self.case_key} AND
                ExtendType = "醫囑"
            ORDER BY CaseExtendKey
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _read_order(self):
        sql = f'''
            SELECT Content FROM caseextend
            WHERE
                CaseKey = {self.case_key} AND
                ExtendType = "醫囑"
            ORDER BY CaseExtendKey
        '''
        self.table_widget_order.set_db_data(sql, self._set_table_data)
        self.ui.tableWidget_order.setCurrentCell(0, 0)

        if self.ui.tableWidget_order.rowCount() <= 0 and not self.doctor_done and \
           self.treat_type in nhi_utils.CARE_TREAT:
            self._set_default_order()

    def _set_default_order(self):
        if self.treat_type in nhi_utils.BRAIN_CARE_TREAT:
            self._set_brain_care_order()

    def _set_brain_care_order(self):
        order_list = [
            '診斷要件: 確診腦血管疾病',
            'ICD10: G450-G468, I60-I68',
            '門診必要項目:',
            '中醫醫療診察費',
            '針灸治療、經穴摩、推拿導引',
            '每季: 衛教、巴氏量表',
            '追蹤期: 診療醫師完成病歷記載',
            '四診診療、治療處置、療效評估',
            '健保VPN登錄個案',
            '結案條件:',
            '連兩季巴氏量表未改善者、自診斷日啟超過兩年之患者',

        ]

        for row_no, order in enumerate(order_list):
            self.ui.tableWidget_order.setRowCount(self.ui.tableWidget_order.rowCount()+1)
            self.ui.tableWidget_order.setItem(row_no, 0, QtWidgets.QTableWidgetItem(order))

    def _set_table_data(self, row_no, row):
        order_row = [
            string_utils.xstr(row['Content']),
        ]

        for col_no in range(len(order_row)):
            self.ui.tableWidget_order.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(order_row[col_no])
            )

    # 增加處方資料
    def append_null_order(self):
        row_count = self.table_widget_order.row_count()
        if row_count <= 0:
            self._insert_order_row(row_count)
            return

        item = self.ui.tableWidget_order.item(row_count-1, 0)
        if item is None or item.text().strip() == '':
            return

        self._insert_order_row(row_count)

    def _insert_order_row(self, index):
        self.ui.tableWidget_order.setFocus(True)
        self.ui.tableWidget_order.insertRow(index)
        self.ui.tableWidget_order.setCurrentCell(index, 0)
        self.ui.tableWidget_order.setItem(index, 0, QtWidgets.QTableWidgetItem(None))

    # 刪除處方
    def remove_order(self):
        index = self.ui.tableWidget_order.currentRow()
        self.ui.tableWidget_order.removeRow(index)
        if self.ui.tableWidget_order.rowCount() <= 0:
            self.append_null_order()

    def save_record(self):
        sql = f'''
            DELETE FROM caseextend
            WHERE
                CaseKey = {self.case_key} AND
                ExtendType = "醫囑"
        '''
        self.database.exec_sql(sql)

        fields = ['CaseKey', 'ExtendType', 'Content']
        self.ui.tableWidget_order.setCurrentCell(0, 0)
        for row_no in range(self.ui.tableWidget_order.rowCount()):
            item = self.ui.tableWidget_order.item(row_no, 0)
            if item is None:
                continue

            content = item.text()
            if content == '':
                continue

            data = [self.case_key, '醫囑', content]
            self.database.insert_record('caseextend', fields, data)

    def open_dict(self):
        dialog = dialog_utils.get_dialog_simple_dict(
            self, self.database, self.system_settings,
        )

        dialog.exec_()
        dialog.deleteLater()

    def add_order(self, order_name):
        self.append_null_order()
        self.ui.tableWidget_order.setItem(
            self.ui.tableWidget_order.rowCount()-1, 0, QtWidgets.QTableWidgetItem(order_name)
        )

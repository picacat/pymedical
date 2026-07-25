
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox
import json

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import dialog_utils
from libs import case_utils


# 病歷回復 2019.06.20
class RestoreMedicalRecords(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(RestoreMedicalRecords, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_RESTORE_MEDICAL_RECORDS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_records = class_utils.get_table_widget(
            self.ui.tableWidget_medical_records, self.database
        )
        self.table_widget_medical_records.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            170, 100,
            120, 70, 90, 60, 70,
            90, 90, 70, 50, 200, 90,
            70, 70, 70, 80, 70,
        ]
        self.table_widget_medical_records.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_records.itemSelectionChanged.connect(self._medical_record_item_selection_changed)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def _medical_record_item_selection_changed(self):
        restore_record = self.table_widget_medical_records.field_value(18)
        if restore_record == '是':
            enabled = False
        else:
            enabled = True

        self.parent.ui.action_restore_record.setEnabled(enabled)

    def read_data(self):
        sql = '''
            SELECT * FROM backup_records
            WHERE
                TableName = "cases" AND
                Deleter != "編輯備份"
            ORDER BY TimeStamp DESC
        '''

        self.table_widget_medical_records.set_db_data(sql, self._set_medical_record_data)

    def _set_medical_record_data(self, row_no, row):
        try:
            deleted_row = json.loads(row['JSON'])[0]
        except Exception:
            return

        deleted_date = row['DeleteDateTime'].strftime('%Y-%m-%d %H:%M')

        medical_record_row = [
            string_utils.xstr(row['BackupRecordsKey']),
            deleted_date,
            string_utils.xstr(row['Deleter']),
            string_utils.xstr(deleted_row['CaseDate']).split(' ')[0],
            string_utils.xstr(deleted_row['PatientKey']),
            string_utils.xstr(deleted_row['Name']),
            string_utils.xstr(deleted_row['InsType']),
            string_utils.xstr(deleted_row['Visit']),
            string_utils.xstr(deleted_row['RegistType']),
            string_utils.xstr(deleted_row['TreatType']),
            string_utils.xstr(deleted_row['Card']),
            string_utils.xstr(deleted_row['Continuance']),
            string_utils.xstr(deleted_row['DiseaseName1']),
            string_utils.xstr(deleted_row['Doctor']),
            number_utils.get_integer(deleted_row['RegistFee']),
            number_utils.get_integer(deleted_row['SDiagFee']),
            number_utils.get_integer(deleted_row['SDrugFee']),
            number_utils.get_integer(deleted_row['TotalFee']),
            string_utils.xstr(row['RecordRestored']),
        ]

        for col_no in range(len(medical_record_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record_row[col_no])
            self.ui.tableWidget_medical_records.setItem(
                row_no, col_no, item,
            )
            if col_no in [4, 14, 15, 16, 17]:
                self.ui.tableWidget_medical_records.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [6, 7, 11, 18]:
                self.ui.tableWidget_medical_records.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def restore_medical_record(self):
        case_date = self.table_widget_medical_records.field_value(3)
        name = self.table_widget_medical_records.field_value(5)
        msg_box = dialog_utils.get_message_box(
            '回復病歷資料', QMessageBox.Question,
            f'''
                <font size="5" color="red">
                    <b>確定回復{name} {case_date}的病歷?</b>
                </font>
            ''',
            '注意！資料回復後, 就無法再次回復, 以免造成資料庫鍵值重複!'
        )
        restore_record = msg_box.exec_()
        if not restore_record:
            return

        row_no = self.ui.tableWidget_medical_records.currentRow()
        backup_records_key = self.table_widget_medical_records.field_value(0)
        case_utils.restore_medical_record(self.database, backup_records_key)

        self.database.exec_sql(f'''
            UPDATE backup_records
            SET
                RecordRestored = "是"
            WHERE
                BackupRecordsKey = {backup_records_key}
        ''')

        self.ui.tableWidget_medical_records.setItem(
            row_no, 18,
            QtWidgets.QTableWidgetItem("是")
        )
        self.ui.tableWidget_medical_records.item(
            row_no, 18).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self._medical_record_item_selection_changed()

    def view_medical_record_json(self):
        backup_records_key = self.table_widget_medical_records.field_value(0)
        dialog = dialog_utils.get_dialog_view_medical_record_json(
            self, self.database, self.system_settings, backup_records_key
        )
        dialog.exec_()
        dialog.deleteLater()


# 病歷版本記錄 2022.01.09
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils


# 主視窗
class DialogMedicalRecordVersionHistory(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordVersionHistory, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self._read_medical_record_version_history()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_VERSION_HISTORY, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('還原')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self.table_widget_medical_record.set_table_heading_width([100, 600])
        self.ui.tableWidget_medical_record.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        pass

    def _read_medical_record_version_history(self):
        sql = f'''
            SELECT BackupRecordsKey FROM backup_records
            WHERE
                TableName = "cases" AND
                KeyField = "CaseKey" AND
                KeyValue = {self.case_key} AND
                Deleter = "編輯備份"
            ORDER BY DeleteDateTime
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)
        for i in range(0, self.ui.tableWidget_medical_record.rowCount()):
            self.ui.tableWidget_medical_record.setRowHeight(i, 800)

    def _set_table_data(self, row_no, row):
        backup_records_key = row['BackupRecordsKey']

        html = case_utils.get_medical_record_html_from_json(
            self.database, self.system_settings, backup_records_key)
        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html)
        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addWidget(text_edit)
        widget = QtWidgets.QWidget()
        widget.setLayout(v_layout)

        self.ui.tableWidget_medical_record.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row['BackupRecordsKey'])))
        self.ui.tableWidget_medical_record.setCellWidget(row_no, 1, widget)

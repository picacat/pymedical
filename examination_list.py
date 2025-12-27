# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import examination_util
from libs import dialog_utils


# 檢驗作業 2019.08.11
class ExaminationList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(ExaminationList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
        }
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_EXAMINATION_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_examination_list = class_utils.get_table_widget(
            self.ui.tableWidget_examination_list, self.database
        )
        self.table_widget_examination_list.set_column_hidden([0])

        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_delete_record.triggered.connect(self._delete_examination)
        self.ui.action_close.triggered.connect(self.close_examination_list)
        self.ui.action_open_record.triggered.connect(self.open_examination)
        self.ui.tableWidget_examination_list.doubleClicked.connect(self.open_examination)
        self.ui.tableWidget_examination_list.itemSelectionChanged.connect(self._examination_preview)

    def close_examination_list(self):
        self.close_all()
        self.close_tab()

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 120, 100, 100, 250, 100]
        self.table_widget_examination_list.set_table_heading_width(width)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_examination_list(self, self.database, self.system_settings)
        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])

        result = dialog.exec_()
        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()

        sql = dialog.get_sql()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        if sql == '':
            return

        try:
            self.table_widget_examination_list.set_db_data(sql, self._set_table_data)
        except Exception:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '資料查詢錯誤',
                '<font size="5" color="red"><b>檢驗資料查詢條件設定有誤, 請重新查詢.</b></font>',
                '請檢查查詢的內容是否有標點符號或其他字元.'
            )

        self._set_tool_button()

    def _set_tool_button(self):
        pass

    def _set_table_data(self, row_no, row):
        examination_row = [
            string_utils.xstr(row['ExaminationKey']),
            string_utils.xstr(row['ExaminationDate']),
            row['PatientKey'],
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Laboratory']),
            string_utils.xstr(row['MLS']),
        ]

        for column in range(len(examination_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, examination_row[column])
            self.ui.tableWidget_examination_list.setItem(
                row_no, column, item,
            )
            if column in [2]:
                self.ui.tableWidget_examination_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def open_examination(self):
        examination_key = self.table_widget_examination_list.field_value(0)
        self.parent.open_examination(examination_key)

    def _examination_preview(self):
        examination_key = self.table_widget_examination_list.field_value(0)
        if examination_key is None:
            self.ui.textEdit_examination.setHtml(None)
            return

        html = examination_util.get_examination_html(self.database, examination_key)
        self.ui.textEdit_examination.setHtml(html)

    def _delete_examination(self):
        msg_box = dialog_utils.get_message_box(
            '刪除檢驗資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此筆檢驗資料 ?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_examination_list.field_value(0)
        self.database.delete_record('examination', 'ExaminationKey', key)
        self.database.delete_record('examination_item', 'ExaminationKey', key)
        self.ui.tableWidget_examination_list.removeRow(self.ui.tableWidget_examination_list.currentRow())

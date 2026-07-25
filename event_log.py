# -*- coding: UTF-8 -*-
# 病歷查詢 2014.09.22

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import class_utils
from libs import export_utils
from libs import personnel_utils


# 系統日誌
class EventLog(QtWidgets.QMainWindow):
    program_name = '系統日誌'

    # 初始化
    def __init__(self, parent=None, *args):
        super(EventLog, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self._read_event_log()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_EVENT_LOG, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_event_log = class_utils.get_table_widget(self.ui.tableWidget_event_log, self.database)
        self.table_widget_event_log.set_column_hidden([0])
        self._set_table_width()

        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_excel.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_refresh.triggered.connect(self._read_event_log)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)
        self.ui.dateEdit_start_date.dateChanged.connect(self._read_event_log)
        self.ui.dateEdit_end_date.dateChanged.connect(self._read_event_log)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 50, 200, 110, 150, 120, 150, 880]
        self.table_widget_event_log.set_table_heading_width(width)

    def _read_event_log(self):
        if self.sender().objectName() == 'dateEdit_start_date':
            self.ui.dateEdit_end_date.setDate(self.ui.dateEdit_start_date.date())

        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        sql = f'''
            SELECT * FROM event_log
            WHERE
                TimeStamp BETWEEN "{start_date}" AND "{end_date}"
            ORDER BY TimeStamp DESC
        '''
        self.table_widget_event_log.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        log_type = string_utils.xstr(row['LogType'])
        user_name = string_utils.xstr(row['UserName'])
        log_row = [
            string_utils.xstr(row['LogKey']),
            None,
            string_utils.xstr(row['TimeStamp']),
            user_name,
            string_utils.xstr(row['IP']),
            log_type,
            string_utils.xstr(row['ProgramName']),
            string_utils.xstr(row['Log']),
        ]

        for col_no in range(len(log_row)):
            self.ui.tableWidget_event_log.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(log_row[col_no])
            )

        icon = None
        if log_type == '資料刪除':
            icon = './icons/software-update-urgent.png'
        elif log_type in ['掛號存檔', '病歷存檔']:
            icon = './icons/media-floppy.png'
        elif log_type in ['掛號修正', '病歷修正', '資料修正']:
            icon = './icons/software-update-available.png'
        elif log_type == '系統登入':
            if user_name == '超級使用者':
                icon = './icons/user-info.png'
            else:
                icon = './icons/emblem-default.png'

        ui_utils.set_table_widget_field_icon(
            self.ui.tableWidget_event_log, row_no, 1, icon,
            None, None, self._do_nothing)

    def _do_nothing(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    def _export_to_excel(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd')

        options = QtWidgets.QFileDialog.Options()
        excel_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "匯出系統日誌",
            f'{start_date}至{end_date}系統日誌.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_event_log,
            [0, 1], None, f'{start_date}至{end_date}系統日誌',
            [25, 15, 20, 20, 30, 150]
        )

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

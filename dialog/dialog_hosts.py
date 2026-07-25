
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
from libs import class_utils

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import dialog_utils


# 分院連線設定 2019.06.25
class DialogHosts(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogHosts, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_hosts()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_HOSTS, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText('關閉')

        self.table_widget_hosts = class_utils.get_table_widget(self.ui.tableWidget_hosts, self.database)
        self.table_widget_hosts.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_add.clicked.connect(self._add_hosts)
        self.ui.toolButton_edit.clicked.connect(self._edit_hosts)
        self.ui.toolButton_remove.clicked.connect(self._remove_hosts)
        self.ui.tableWidget_hosts.doubleClicked.connect(self._edit_hosts)

    def accepted_button_clicked(self):
        self.close()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 200, 180, 60, 100, 60, 120, 80, 100, 250, 200]
        self.table_widget_hosts.set_table_heading_width(width)

    def _read_hosts(self):
        sql = '''
            SELECT * FROM hosts
            ORDER BY HostsKey
        '''

        self.table_widget_hosts.set_db_data(sql, self._set_hosts_data)

    def _set_hosts_data(self, row_no, row):
        hosts_row = [
            string_utils.xstr(row['HostsKey']),
            string_utils.xstr(row['ClinicName']),
            string_utils.xstr(row['Host']),
            string_utils.xstr(row['UserName']),
            '********',
            string_utils.xstr(row['Charset']),
            string_utils.xstr(row['DatabaseName']),
            string_utils.xstr(row['Vendor']),
            string_utils.xstr(row['HISVersion']),
            string_utils.xstr(row['Function']),
            string_utils.xstr(row['ImageDir']),
        ]

        for col_no in range(len(hosts_row)):
            self.ui.tableWidget_hosts.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(hosts_row[col_no])
            )

    def _add_hosts(self):
        dialog = dialog_utils.get_dialog_input_host(self, self.database, self.system_settings, None)
        result = dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self._read_hosts()
        self.ui.tableWidget_hosts.setCurrentCell(
            self.ui.tableWidget_hosts.rowCount(), 1
        )

    def _edit_hosts(self):
        hosts_key = self.table_widget_hosts.field_value(0)
        current_row = self.ui.tableWidget_hosts.currentRow()

        dialog = dialog_utils.get_dialog_input_host(
            self, self.database, self.system_settings, hosts_key,
        )
        result = dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self._read_hosts()
        self.ui.tableWidget_hosts.setCurrentCell(current_row, 1)

    def _remove_hosts(self):
        msg_box = dialog_utils.get_message_box(
            '刪除連線資料', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除此連線設定資料 ?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_hosts.field_value(0)
        self.database.delete_record('hosts', 'HostsKey', key)
        self.ui.tableWidget_hosts.removeRow(self.ui.tableWidget_hosts.currentRow())

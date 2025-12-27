
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import personnel_utils


# 功能表設定 2024.01.19
class DialogMenuSetting(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMenuSetting, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MENU_SETTING, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_menu_list = class_utils.get_table_widget(self.ui.tableWidget_menu_list, self.database)
        self._set_table_width()
        self.ui.tableWidget_menu_list.setFocus(True)

        self._set_menu_list_table()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_all.clicked.connect(self._set_selection_tool_button)
        self.ui.toolButton_diselect_all.clicked.connect(self._set_selection_tool_button)

    def _set_menu_list_table(self):
        top_menu = [
            '掛號作業', '診療作業', '醫務行政', '自費管理', '申報作業', '統計表', '分院統計', '進銷存管理',
            '設定', '系統作業'
        ]
        menu_list = []
        for action in self.parent.findChildren(QtWidgets.QAction):
            if not action.isVisible():
                continue

            menu = action.text()
            if menu in top_menu:
                continue

            if len(menu) == 0:
                continue

            menu_list.append(menu)

        self.ui.tableWidget_menu_list.setRowCount(len(menu_list))

        for row_no, menu in enumerate(menu_list):
            if menu in ['', ' ', None]:
                continue

            self.ui.tableWidget_menu_list.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(menu)
            )

            check_box = QtWidgets.QCheckBox(self.ui.tableWidget_menu_list)
            check_box.setChecked(False)
            check_box.setStyleSheet('margin:auto')
            self.ui.tableWidget_menu_list.setCellWidget(row_no, 1, check_box)

    def accepted_button_clicked(self):
        self._save_menu_list()

    def _save_menu_list(self):
        self.database.exec_sql('''
            DELETE FROM system_settings
            WHERE
                StationNo = 0 AND
                Field = "功能表醒目設定"
        ''')

        selected_menu = []
        for row_no in range(self.ui.tableWidget_menu_list.rowCount()):
            check_box = self.ui.tableWidget_menu_list.cellWidget(row_no, 1)
            if check_box.isChecked():
                menu = self.ui.tableWidget_menu_list.item(row_no, 0).text()
                selected_menu.append(menu)

        if len(selected_menu) == 0:
            return

        field = ['StationNo', 'Field', 'Value']
        for menu in selected_menu:
            data = [0, '功能表醒目設定', menu]
            self.database.insert_record('system_settings', field, data)

    def _set_table_width(self):
        width = [450, 100]
        self.table_widget_menu_list.set_table_heading_width(width)

    # 讀取資料
    def _read_data(self):
        menu_list = []
        sql = '''
            SELECT Value FROM system_settings
            WHERE
                StationNo = 0 AND
                Field = "功能表醒目設定"
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            menu_list.append(row['Value'])

        if len(menu_list) <= 0:
            return

        for row_no in range(self.ui.tableWidget_menu_list.rowCount()):
            menu = self.ui.tableWidget_menu_list.item(row_no, 0).text()
            if menu in menu_list:
                check_box = self.ui.tableWidget_menu_list.cellWidget(row_no, 1)
                check_box.setChecked(True)

    def _set_selection_tool_button(self):
        sender_name = self.sender().objectName()
        if sender_name == 'toolButton_select_all':
            checked = True
        else:
            checked = False

        for row_no in range(self.ui.tableWidget_menu_list.rowCount()):
            check_box = self.ui.tableWidget_menu_list.cellWidget(row_no, 1)
            check_box.setChecked(checked)

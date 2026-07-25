
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils


# 主視窗
class DialogCourseList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCourseList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key_list = args[2]

        self.selected_case_key = 0
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_medical_record()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_COURSE_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_case_list = class_utils.get_table_widget(self.ui.tableWidget_case_list, self.database)
        self.table_widget_case_list.set_column_hidden([0])
        width = [60, 130, 80, 50, 50, 220, 120, 100]
        self.table_widget_case_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_case_list.doubleClicked.connect(self._click_accept_button)

    def _read_medical_record(self):
        case_key_list = tuple(x for x in self.case_key_list if x is not None)

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey In {case_key_list}
            ORDER BY CaseDate
        '''
        self.table_widget_case_list.set_db_data(sql, self._set_db_data)

    def _set_db_data(self, row_no, row):
        pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])

        medical_rec = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            pres_days,
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(row['Treatment']),
            string_utils.xstr(row['Doctor']),
        ]

        for column in range(len(medical_rec)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_rec[column])
            self.ui.tableWidget_case_list.setItem(
                row_no, column, item,
            )

            if column in [4]:
                self.ui.tableWidget_case_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [3]:
                self.ui.tableWidget_case_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    # 雙擊滑鼠左鍵選擇病歷
    def _click_accept_button(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def accepted_button_clicked(self):
        self.selected_case_key = self.table_widget_case_list.field_value(0)

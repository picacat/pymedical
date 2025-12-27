# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QLineEdit

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils


#  用藥指示 2019.07.11
class DictInstruction(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DictInstruction, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_instruction()
        self._read_comment()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DICT_INSTRUCTION, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_dict_instruction = class_utils.get_table_widget(
            self.ui.tableWidget_dict_instruction, self.database
        )
        self.table_widget_dict_instruction.set_column_hidden([0])
        self.table_widget_dict_comment = class_utils.get_table_widget(
            self.ui.tableWidget_dict_comment, self.database
        )
        self.table_widget_dict_comment.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_instruction.clicked.connect(self._add_instruction)
        self.ui.toolButton_remove_instruction.clicked.connect(self._remove_instruction)
        self.ui.toolButton_edit_instruction.clicked.connect(self._edit_instruction)
        self.ui.tableWidget_dict_instruction.doubleClicked.connect(self._edit_instruction)
        self.ui.toolButton_add_comment.clicked.connect(self._add_comment)
        self.ui.toolButton_remove_comment.clicked.connect(self._remove_comment)
        self.ui.toolButton_edit_comment.clicked.connect(self._edit_comment)
        self.ui.tableWidget_dict_comment.doubleClicked.connect(self._edit_comment)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 250]
        self.table_widget_dict_instruction.set_table_heading_width(width)
        self.table_widget_dict_comment.set_table_heading_width(width)

    def _read_instruction(self):
        clinic_type = '指示'
        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{clinic_type}"
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        self.table_widget_dict_instruction.set_db_data(sql, self._set_dict_instruction_data)

    def _set_dict_instruction_data(self, row_no, row):
        dict_instruction_row = [
            string_utils.xstr(row['ClinicKey']),
            string_utils.xstr(row['ClinicName']),
        ]

        for column in range(len(dict_instruction_row)):
            self.ui.tableWidget_dict_instruction.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_instruction_row[column])
            )

    # 新增用藥指示
    def _add_instruction(self):
        input_dialog = dialog_utils.get_dialog(
            '用藥指示', '請輸入用藥指示',
            None, QInputDialog.TextInput, 320, 200)
        ok = input_dialog.exec_()
        if not ok:
            return

        instruction = input_dialog.textValue()

        field = ['ClinicType', 'ClinicName']
        data = ['指示', instruction]

        self.database.insert_record('clinic', field, data)
        self._read_instruction()

    # 移除用藥指示
    def _remove_instruction(self):
        instruction_name = self.table_widget_dict_instruction.field_value(1)
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除用藥指示 "{instruction_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_instruction.field_value(0)
        self.database.delete_record('clinic', 'ClinicKey', key)
        self.ui.tableWidget_dict_instruction.removeRow(self.ui.tableWidget_dict_instruction.currentRow())

    # 修改用藥指示
    def _edit_instruction(self):
        key = self.table_widget_dict_instruction.field_value(0)
        if key is None:
            return

        instruction_name = self.table_widget_dict_instruction.field_value(1)
        text, ok = QInputDialog.getText(
            self, "編輯用藥指示", "請輸入用藥指示:", QLineEdit.Normal, instruction_name)
        if not ok or text == '':
            return

        sql = f'''
            UPDATE clinic
            SET
                ClinicName = "{text}"
            WHERE
                ClinicKey = {key}
        '''
        self.database.exec_sql(sql)
        self._read_instruction()

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def _read_comment(self):
        clinic_type = '醫囑'
        sql = f'''
            SELECT * FROM clinic
            WHERE
                ClinicType = "{clinic_type}"
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        self.table_widget_dict_comment.set_db_data(sql, self._set_dict_comment_data)
        if self.ui.tableWidget_dict_comment.rowCount() <= 0:
            self._init_dict_comment()

    def _set_dict_comment_data(self, row_no, row):
        dict_instruction_row = [
            string_utils.xstr(row['ClinicKey']),
            string_utils.xstr(row['ClinicName']),
        ]

        for column in range(len(dict_instruction_row)):
            self.ui.tableWidget_dict_comment.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(dict_instruction_row[column])
            )

    # 新增用藥指示
    def _add_comment(self):
        input_dialog = dialog_utils.get_dialog(
            '醫師囑言', '請輸入醫師囑言',
            None, QInputDialog.TextInput, 320, 200)
        ok = input_dialog.exec_()
        if not ok:
            return

        comment = input_dialog.textValue()

        field = ['ClinicType', 'ClinicName']
        data = ['醫囑', comment]

        self.database.insert_record('clinic', field, data)
        self._read_comment()

    # 移除用藥指示
    def _remove_comment(self):
        comment_name = self.table_widget_dict_comment.field_value(1)
        msg_box = dialog_utils.get_message_box(
            '刪除資料',
            QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定刪除醫師囑言 "{comment_name}"?</b></font>',
            '注意！資料刪除後, 將無法回復!'
        )
        remove_record = msg_box.exec_()
        if not remove_record:
            return

        key = self.table_widget_dict_comment.field_value(0)
        self.database.delete_record('clinic', 'ClinicKey', key)
        self.ui.tableWidget_dict_comment.removeRow(self.ui.tableWidget_dict_comment.currentRow())

    # 修改醫囑
    def _edit_comment(self):
        key = self.table_widget_dict_comment.field_value(0)
        if key is None:
            return

        comment_name = self.table_widget_dict_comment.field_value(1)
        text, ok = QInputDialog.getText(
            self, "編輯醫囑", "請輸入醫囑:", QLineEdit.Normal, comment_name)
        if not ok or text == '':
            return

        sql = f'''
            UPDATE clinic
            SET
                ClinicName = "{text}"
            WHERE
                ClinicKey = {key}
        '''
        self.database.exec_sql(sql)
        self._read_comment()

    def _init_dict_comment(self):
        field = ['ClinicType', 'ClinicName']

        items = (
            "宜休息  日",
            "患者因上述情形，宜多休養",
            "患者因上述情形，宜在家休養，並持續回診治療",
            "患者因上述情形，宜門診持續追蹤治療",
        )
        for item in items:
            data = ['醫囑', item]
            self.database.insert_record('clinic', field, data)

        self._read_comment()

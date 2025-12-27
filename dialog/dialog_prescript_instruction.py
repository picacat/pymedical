
# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QSettings, QSize, QPoint
from libs import ui_utils
from libs import system_utils
from libs import prescript_utils
from libs import string_utils


# 處方服法詞庫
class DialogPrescriptInstruction(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPrescriptInstruction, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]
        self.ins_type = args[3]

        self.settings = QSettings('__settings.ini', QSettings.IniFormat)
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.button_list = [
            self.ui.toolButton_1,
            self.ui.toolButton_2,
            self.ui.toolButton_3,
            self.ui.toolButton_4,
            self.ui.toolButton_5,
            self.ui.toolButton_6,
            self.ui.toolButton_7,
            self.ui.toolButton_8,
            self.ui.toolButton_9,
            self.ui.toolButton_10,
            self.ui.toolButton_11,
            self.ui.toolButton_12,
            self.ui.toolButton_13,
            self.ui.toolButton_14,
            self.ui.toolButton_15,
            self.ui.toolButton_16,
            self.ui.toolButton_17,
            self.ui.toolButton_18,
            self.ui.toolButton_19,
            self.ui.toolButton_20,
            self.ui.toolButton_21,
            self.ui.toolButton_22,
            self.ui.toolButton_23,
            self.ui.toolButton_24,
            self.ui.toolButton_25,
            self.ui.toolButton_26,
            self.ui.toolButton_27,
            self.ui.toolButton_28,
            self.ui.toolButton_29,
            self.ui.toolButton_30,
        ]

        self._set_button_list()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def closeEvent(self, a0: QtGui.QCloseEvent):
        self.settings.setValue("dialog_prescript_instruction_size", self.size())
        self.settings.setValue("dialog_prescript_instruction_pos", self.pos())

    def show_prescript_instruction(self):
        self.show()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PRESCRIPT_INSTRUCTION, self)
        system_utils.set_css(self, self.system_settings)

        self.ui.resize(self.settings.value("dialog_prescript_instruction_size", QSize(460, 270)))
        screen_width = QtWidgets.QDesktopWidget().screenGeometry().width()
        width = self.settings.value("dialog_prescript_instruction_pos")
        if width is not None and width.x() < screen_width:
            self.ui.move(self.settings.value("dialog_prescript_instruction_pos", QPoint(226, 147)))

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            tool_button.clicked.connect(self._dosage_button_clicked)

    def accepted_button_clicked(self):
        self.close()

    def rejected_button_clicked(self):
        self.close()

    def reject(self):
        self.close()

    def _dosage_button_clicked(self):
        row_no = self.table_widget_prescript.currentRow()
        if self.ins_type == '健保':
            col_no = prescript_utils.INS_PRESCRIPT_COL_NO['Instruction']
            medicine_name_col_no = prescript_utils.INS_PRESCRIPT_COL_NO['MedicineName']
        else:
            col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction']
            medicine_name_col_no = prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']

        medicine_name_item = self.table_widget_prescript.item(row_no, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            return

        instruction = self.sender().text()
        self.table_widget_prescript.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(instruction)
        )
        self.table_widget_prescript.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.table_widget_prescript.setCurrentCell(row_no+1, col_no)
        medicine_name_item = self.table_widget_prescript.item(row_no+1, medicine_name_col_no)
        if medicine_name_item is None or medicine_name_item.text() == '':
            self.table_widget_prescript.setCurrentCell(row_no+1, medicine_name_col_no)
            # prescript_utils.append_null_medicine(self.parent.parent)
            self.close()

    def _set_button_list(self):
        instruction_list = ['混合']
        sql = '''
            SELECT ClinicName FROM clinic
            WHERE
                ClinicType = "指示"
            ORDER BY LENGTH(ClinicName), CAST(CONVERT(`ClinicName` using big5) AS BINARY)
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            instruction = string_utils.xstr(row['ClinicName'])
            if instruction == '':
                continue

            instruction_list.append(instruction)

        for tool_button in self.button_list:
            tool_button.setEnabled(False)

        for i, instruction in enumerate(instruction_list):
            self.button_list[i].setEnabled(True)
            self.button_list[i].setText(instruction)

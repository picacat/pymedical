# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import system_utils


# 中醫體質量表
class PhysiqueTable(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PhysiqueTable, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHYSIQUE_TABLE, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_anxiety = class_utils.get_table_widget(
            self.ui.tableWidget_anxiety, self.database
        )
        self._set_anxiety_table()
        self.check_box_list = [
            self.ui.checkBox_constitution1,
            self.ui.checkBox_constitution2,
            self.ui.checkBox_constitution3,
            self.ui.checkBox_constitution4,
            self.ui.checkBox_constitution5,
            self.ui.checkBox_constitution6,
            self.ui.checkBox_constitution7,
            self.ui.checkBox_constitution8,
            self.ui.checkBox_constitution9,
        ]

    def _set_anxiety_table(self):
        width = [500, 400]
        self.table_widget_anxiety.set_table_heading_width(width)
        self._set_radio_button_box()
        self.ui.tableWidget_anxiety.resizeRowsToContents()

    def _set_radio_button_box(self):
        self.radio_button_list = []
        radio_button_label = ['全不同意', '不同意', '同意', '完全同意']

        for i in range(10):
            radio_button_line = []
            h_layout = QtWidgets.QHBoxLayout()
            for j in range(4):
                radio_button = QtWidgets.QRadioButton()
                radio_button.setText(radio_button_label[j])
                radio_button.clicked.connect(self._set_anxiety_grade)

                radio_button_line.append(radio_button)
                h_layout.addWidget(radio_button)

            self.radio_button_list.append(radio_button_line)

            widget = QtWidgets.QWidget()
            widget.setLayout(h_layout)
            self._set_radio_button_item(i, 1, widget)

    def _set_radio_button_item(self, row_no, col_no, widget):
        self.ui.tableWidget_anxiety.setCellWidget(row_no, col_no, widget)

    def _clear_radio_button(self):
        for radio_button_line in self.radio_button_list:
            radio_button_line[0].setChecked(True)

    # 設定信號
    def _set_signal(self):
        for check_box in self.check_box_list:
            check_box.clicked.connect(self._set_check_box_color)

    def _set_check_box_color(self):
        sender = self.sender()
        if sender.isChecked():
            sender.setStyleSheet('color:darkred; font-weight:bold')
        else:
            sender.setStyleSheet(None)

    def set_row(self, row):
        self._set_physique_line(row)
        self._set_anxiety_line(row)

    def get_physique_line(self):
        physique_line = ''
        for check_box in self.check_box_list:
            if check_box.isChecked():
                physique_line += 'Y'
            else:
                physique_line += 'N'

        return physique_line

    def get_anxiety_line(self):
        anxiety_line = []
        for i in range(10):
            for j in range(4):
                if self.radio_button_list[i][j].isChecked():
                    anxiety_line.append(string_utils.xstr(j))
                    break

        return ''.join(anxiety_line)

    def get_anxiety_grade(self):
        total_grade = 0
        for i in range(10):
            for j in range(4):
                if self.radio_button_list[i][j].isChecked():
                    self.radio_button_list[i][j].setStyleSheet('color:darkred; font-weight:bold')
                    total_grade += j
                else:
                    self.radio_button_list[i][j].setStyleSheet(None)

        return total_grade

    def _set_physique_line(self, row):
        physique_line = string_utils.xstr(row['PhysiqueLine'])

        for i, check_box in enumerate(self.check_box_list):
            if physique_line[i] == 'Y':
                check_box.setChecked(True)
                check_box.setStyleSheet('color:darkred; font-weight:bold')
            else:
                check_box.setChecked(False)
                check_box.setStyleSheet(None)

    def _set_anxiety_line(self, row):
        anxiety_line = string_utils.xstr(row['AnxietyLine'])

        self._clear_radio_button()
        for i, anxiety in enumerate(anxiety_line):
            try:
                self.radio_button_list[i][int(anxiety)].setChecked(True)
            except IndexError:
                continue

        self._set_anxiety_grade()

    def _set_anxiety_grade(self):
        anxiety_grade = self.get_anxiety_grade()
        self.ui.lineEdit_anxiety_grade.setText(string_utils.xstr(anxiety_grade))
        if anxiety_grade <= 12:
            self.ui.label_anxiety_warning.hide()
        else:
            self.ui.label_anxiety_warning.show()

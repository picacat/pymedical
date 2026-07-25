
# 處置部位選取視窗 2022.07.12
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import prescript_utils


# 主視窗
class DialogTreatAuxiliary(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTreatAuxiliary, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.treatment = args[2]
        self.table_widget_treat = args[3]

        self.ui = None
        self.treat_time_list = None
        self.keyword = '輔助治療:'

        self._set_ui()
        self._set_signal()
        self._set_selected_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TREAT_AUXILIARY, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(f'{self.treatment} - 設定輔助治療')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.treatment in ['中度複雜性針灸', '高度複雜性針灸']:
            self.ui.checkBox_8.setEnabled(False)
            self.ui.checkBox_9.setEnabled(False)
            self.ui.checkBox_10.setEnabled(False)
        elif self.treatment in ['中度複雜性傷科', '高度複雜性傷科']:
            self.ui.checkBox_5.setEnabled(False)
            self.ui.checkBox_6.setEnabled(False)
            self.ui.checkBox_7.setEnabled(False)

        self.treat_auxiliary_list = [
            self.ui.checkBox_1,
            self.ui.checkBox_2,
            self.ui.checkBox_3,
            self.ui.checkBox_4,
            self.ui.checkBox_5,
            self.ui.checkBox_6,
            self.ui.checkBox_7,
            self.ui.checkBox_8,
            self.ui.checkBox_9,
            self.ui.checkBox_10,
        ]

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.checkBox_1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_6.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_7.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_8.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_9.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_10.clicked.connect(self._set_check_box_color)

    def _set_check_box_color(self):
        for check_box in self.treat_auxiliary_list:
            if check_box.isChecked():
                check_box.setStyleSheet('color:blue; font-weight:bold')
            else:
                check_box.setStyleSheet(None)

    def _set_selected_data(self):
        for row_no in range(self.table_widget_treat.rowCount()):
            item = self.table_widget_treat.item(row_no, prescript_utils.INS_TREAT_COL_NO['MedicineName'])
            if item is None:
                continue

            medicine_name = item.text()
            if self.keyword not in medicine_name:
                continue

            auxiliary_treat = medicine_name.replace(self.keyword, '').strip()
            for check_box in self.treat_auxiliary_list:
                if check_box.text() == auxiliary_treat:
                    check_box.setChecked(True)

        self._set_check_box_color()

    def accepted_button_clicked(self):
        pass

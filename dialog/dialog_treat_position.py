
# 處置部位選取視窗 2022.07.12
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import system_utils
from libs import ui_utils
from libs import nhi_utils
from libs import prescript_utils


# 主視窗
class DialogTreatPosition(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogTreatPosition, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.treatment = args[2]
        self.table_widget_treat = args[3]

        self.ui = None
        self.treat_time_list = None
        self.keyword = '治療部位:'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_TREAT_POSITION, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.setWindowTitle(f'{self.treatment} - 設定處置部位')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.treatment in nhi_utils.COMPLICATED_MASSAGE_TREAT:
            self.ui.label_acupuncture_hint.setVisible(False)

        self.treat_position_list = [
            self.ui.checkBox_c1,
            self.ui.checkBox_c2,
            self.ui.checkBox_c3,
            self.ui.checkBox_c4,
            self.ui.checkBox_c5,
            self.ui.checkBox_c6,
            self.ui.checkBox_c7,

            self.ui.checkBox_lu1,
            self.ui.checkBox_lu2,
            self.ui.checkBox_lu3,
            self.ui.checkBox_lu4,
            self.ui.checkBox_lu5,
            self.ui.checkBox_lu6,
            self.ui.checkBox_lu7,

            self.ui.checkBox_ru1,
            self.ui.checkBox_ru2,
            self.ui.checkBox_ru3,
            self.ui.checkBox_ru4,
            self.ui.checkBox_ru5,
            self.ui.checkBox_ru6,
            self.ui.checkBox_ru7,

            self.ui.checkBox_lb1,
            self.ui.checkBox_lb2,
            self.ui.checkBox_lb3,
            self.ui.checkBox_lb4,
            self.ui.checkBox_lb5,
            self.ui.checkBox_lb6,

            self.ui.checkBox_rb1,
            self.ui.checkBox_rb2,
            self.ui.checkBox_rb3,
            self.ui.checkBox_rb4,
            self.ui.checkBox_rb5,
            self.ui.checkBox_rb6,
        ]

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

        self.ui.checkBox_c1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c6.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_c6.clicked.connect(self._set_check_box_color)

        self.ui.checkBox_lu1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu6.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lu7.clicked.connect(self._set_check_box_color)

        self.ui.checkBox_lb1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lb2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lb3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lb4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lb5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_lb6.clicked.connect(self._set_check_box_color)

        self.ui.checkBox_ru1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru6.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_ru7.clicked.connect(self._set_check_box_color)

        self.ui.checkBox_rb1.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_rb2.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_rb3.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_rb4.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_rb5.clicked.connect(self._set_check_box_color)
        self.ui.checkBox_rb6.clicked.connect(self._set_check_box_color)

    def _set_check_box_color(self):
        for check_box in self.treat_position_list:
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

            position = medicine_name.replace(self.keyword, '').strip()
            for check_box in self.treat_position_list:
                if check_box.text() == position:
                    check_box.setChecked(True)

        self._set_check_box_color()

    def accepted_button_clicked(self):
        pass

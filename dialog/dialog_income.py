
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
import datetime

from libs import system_utils
from libs import ui_utils
from libs import personnel_utils
from libs import nhi_utils
from libs import date_utils


# 主視窗
class DialogIncome(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogIncome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
        self.ui = None

        self.start_date, self.end_date = None, None
        self.cashier, self.therapist = None, None
        self.period = '全部'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        script = 'select * from person where Position IN("醫師", "支援醫師") '
        if self.call_from == '養生館櫃台結帳':
            self.ui.label_therapist.setText('推拿師父')
            script = 'select * from person where Position IN("推拿師父") '

        rows = self.database.select_record(script)
        therapist_list = []
        for row in rows:
            therapist_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_room, ['1', '2', '3', '5', '6', '7', '8', '9', '10'], '全部')
        ui_utils.set_combo_box(self.ui.comboBox_therapist, therapist_list, '全部')
        ui_utils.set_combo_box(
            self.ui.comboBox_cashier,
            personnel_utils.get_person(self.database, '全部'), '全部',
        )
        ui_utils.set_combo_box(self.ui.comboBox_regist_type, nhi_utils.OUTPATIENT_TYPE + nhi_utils.REG_TYPE, '全部')

        default_date = date_utils.get_default_date(self.system_settings)
        self.ui.dateEdit_case_date.setDate(default_date)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)

    def button_accepted(self):
        self.start_date = self.ui.dateEdit_case_date.date().toString('yyyy-MM-dd 00:00:00')
        self.end_date = self.ui.dateEdit_case_date.date().toString('yyyy-MM-dd 23:59:59')

        self.period = '全部'
        if self.ui.radioButton_period1.isChecked():
            self.period = '早班'
        elif self.ui.radioButton_period2.isChecked():
            self.period = '午班'
        elif self.ui.radioButton_period3.isChecked():
            self.period = '晚班'

        self.therapist = self.ui.comboBox_therapist.currentText()
        self.cashier = self.ui.comboBox_cashier.currentText()
        self.regist_type = self.ui.comboBox_regist_type.currentText()
        self.room = self.ui.comboBox_room.currentText()

    def button_rejected(self):
        pass

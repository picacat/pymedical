
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import datetime
import calendar

from libs import ui_utils
from libs import system_utils
from libs import personnel_utils
from libs import string_utils


# 統計日期及醫師
class DialogInsDateDoctor(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInsDateDoctor, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]

        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INS_DATE_DOCTOR, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.ui.checkBox_regist_fee_discount.setVisible(False)
        self.ui.checkBox_basic_regist_fee_discount.setVisible(False)
        self.ui.checkBox_first_course.setVisible(False)
        self.ui.checkBox_from_medical_record.setVisible(False)
        self.ui.checkBox_exclude_c5.setVisible(False)

        if self.call_from == '健保門診優惠統計':
            self.ui.checkBox_regist_fee_discount.setVisible(True)
            self.ui.checkBox_basic_regist_fee_discount.setVisible(True)
            self.ui.checkBox_first_course.setVisible(True)
        elif self.call_from == '健保申報業績':
            self.ui.checkBox_from_medical_record.setVisible(True)
            self.ui.checkBox_exclude_c5.setVisible(True)

        self._set_date_edit()

    def _set_date_edit(self):
        start_date = datetime.datetime.today().replace(day=1)
        self.ui.dateEdit_start_date.setDate(start_date)
        self.ui.dateEdit_end_date.setDate(datetime.datetime.today())

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_start_date.dateChanged.connect(self._start_date_changed)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        self._set_calculate_doctor_permission()

    def _set_calculate_doctor_permission(self):
        if personnel_utils.get_permission(self.database, self.call_from, '統計全部醫師', self.user_name) == 'Y':
            return

        for i in range(self.ui.comboBox_doctor.count()-1, -1, -1):
            doctor_name = self.ui.comboBox_doctor.itemText(i)
            doctor_name = string_utils.replace_ascii_char([','], doctor_name)
            if doctor_name == '全部':
                self.ui.comboBox_doctor.removeItem(i)
                continue

            if self.user_name != doctor_name:
                self.ui.comboBox_doctor.removeItem(i)

    def _start_date_changed(self):
        year = self.ui.dateEdit_start_date.date().year()
        month = self.ui.dateEdit_start_date.date().month()
        last_day = calendar.monthrange(year, month)[1]

        self.ui.dateEdit_end_date.setDate(QtCore.QDate(year, month, last_day))

    # 設定comboBox
    def _set_combo_box(self):
        script = 'select * from person where Position IN("醫師", "支援醫師") AND ID IS NOT NULL'
        rows = self.database.select_record(script)
        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list, '全部')

    def start_date(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')

        return start_date

    def end_date(self):
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        return end_date

    def doctor(self):
        doctor = self.ui.comboBox_doctor.currentText()

        return doctor

    def accepted_button_clicked(self):
        pass

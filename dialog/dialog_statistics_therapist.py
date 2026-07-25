
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import datetime
import calendar

from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import personnel_utils
from libs import string_utils


# 病歷查詢視窗
class DialogStatisticsTherapist(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogStatisticsTherapist, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
        self.dialog_type = args[3]

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_STATISTICS_THERAPIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self._set_date_edit()

        self.ui.groupBox_exclude_cases.setVisible(False)
        self.ui.checkBox_only_traditional_massage.setVisible(False)
        self.ui.checkBox_under_250.setVisible(False)

        if self.dialog_type in ['推拿師父', '推拿師']:
            self.label_therapist.setText(self.dialog_type)
            self.groupBox_ins_type.setVisible(False)
            self.ui.checkBox_only_traditional_massage.setVisible(True)

        if self.call_from in ['自費印花稅統計']:
            self.ui.checkBox_under_250.setVisible(True)

        if self.dialog_type in ['自費抽成統計', '全部']:
            self.label_therapist.setText('銷售人員')
        elif self.call_from in ['醫師統計', '病歷統計']:
            self.ui.groupBox_exclude_cases.setVisible(True)
            if self.call_from in ['病歷統計']:
                self.ui.groupBox_exclude_cases.setTitle('統計以下病歷')

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if self.dialog_type in ['醫師']:
            self._set_calculate_doctor_permission()

    def _set_calculate_doctor_permission(self):
        if personnel_utils.get_permission(self.database, self.call_from, '統計全部醫師', self.user_name) == 'Y':
            return

        for i in range(self.ui.comboBox_therapist.count()-1, -1, -1):
            doctor_name = self.ui.comboBox_therapist.itemText(i)
            doctor_name = string_utils.replace_ascii_char([','], doctor_name)
            if doctor_name == '全部':
                self.ui.comboBox_therapist.removeItem(i)
                continue

            if self.user_name != doctor_name:
                self.ui.comboBox_therapist.removeItem(i)

    def _set_date_edit(self):
        start_date = datetime.datetime.today().replace(day=1)
        self.ui.dateEdit_start_date.setDate(start_date)
        self.ui.dateEdit_end_date.setDate(datetime.datetime.today())

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_start_date.dateChanged.connect(self._start_date_changed)

    def _start_date_changed(self):
        year = self.ui.dateEdit_start_date.date().year()
        month = self.ui.dateEdit_start_date.date().month()
        last_day = calendar.monthrange(year, month)[1]

        self.ui.dateEdit_end_date.setDate(QtCore.QDate(year, month, last_day))

    # 設定comboBox
    def _set_combo_box(self):
        script = 'select * from person where Position IN ("醫師", "支援醫師")'

        if self.dialog_type in ['推拿師父', '推拿師']:
            script = 'select * from person where Position IN ("推拿師父")'
        elif self.dialog_type in ['自費抽成統計', '全部']:
            script = 'select * from person'

        rows = self.database.select_record(script)
        therapist_list = []
        for row in rows:
            therapist_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_therapist, therapist_list, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '全部')

    def start_date(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')

        return start_date

    def end_date(self):
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        return end_date

    def period(self):
        period = self.ui.comboBox_period.currentText()

        return period

    def therapist(self):
        therapist = self.ui.comboBox_therapist.currentText()

        return therapist

    def ins_type(self):
        ins_type = '全部'

        if self.ui.radioButton_ins.isChecked():
            ins_type = '健保'
        elif self.ui.radioButton_self.isChecked():
            ins_type = '自費'

        return ins_type

    def weekday_list(self):
        weekday_list = []
        if self.checkBox_mon.isChecked():
            weekday_list.append('0')
        if self.checkBox_tue.isChecked():
            weekday_list.append('1')
        if self.checkBox_wed.isChecked():
            weekday_list.append('2')
        if self.checkBox_thu.isChecked():
            weekday_list.append('3')
        if self.checkBox_fri.isChecked():
            weekday_list.append('4')
        if self.checkBox_sat.isChecked():
            weekday_list.append('5')
        if self.checkBox_sun.isChecked():
            weekday_list.append('6')

        return weekday_list

    def only_traditional_massage(self):
        only_traditional_massage = self.ui.checkBox_only_traditional_massage.isChecked()

        return only_traditional_massage

    def under_250(self):
        under_250 = self.ui.checkBox_under_250.isChecked()

        return under_250

    def accepted_button_clicked(self):
        pass

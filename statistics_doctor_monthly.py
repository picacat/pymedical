# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 醫師月報表 2022.05.12
class StatisticsDoctorMonthly(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorMonthly, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "period": None,
            "ins_type": None,
            "therapist": None,
        }

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, '醫師月報表')

        if self.dialog_setting['dialog_executed']:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting['year'])
            dialog.ui.comboBox_month.setCurrentText(self.dialog_setting['month'])
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting['therapist'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = dialog.ui.comboBox_year.currentText()
        month = dialog.ui.comboBox_month.currentText()
        therapist = dialog.ui.comboBox_doctor.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['year'] = year
        self.dialog_setting['month'] = month
        self.dialog_setting['therapist'] = therapist

        dialog.deleteLater()
        self._set_tab_widget(year, month, therapist)

    def _set_tab_widget(self, year, month, doctor):
        self.ui.tabWidget_statistics_doctor.clear()

        self.ui.statusbar.showMessage(
            f' 統計期間: {year} 年 {month} 月 醫師: {doctor}'
        )

        self._add_statistic_doctor_monthly_count(year, month, doctor)
        self._add_statistic_doctor_monthly_income(year, month, doctor)
        self._add_statistic_doctor_monthly_person_count(year, month, doctor)

    # 醫師門診人數統計
    def _add_statistic_doctor_monthly_count(self, year, month, doctor):
        self.tab_statistics_doctor_monthly_count = module_utils.get_statistics_doctor_monthly_count(
            self, self.database, self.system_settings, year, month, doctor)
        self.tab_statistics_doctor_monthly_count.start_calculate()
        self.ui.tabWidget_statistics_doctor.addTab(self.tab_statistics_doctor_monthly_count, '月報表')

    # 醫師門診人數統計-收入統計
    def _add_statistic_doctor_monthly_income(self, year, month, doctor):
        self.tab_statistics_doctor_monthly_income = module_utils.get_statistics_doctor_monthly_income(
            self, self.database, self.system_settings, year, month, doctor)
        self.tab_statistics_doctor_monthly_income.start_calculate()
        self.ui.tabWidget_statistics_doctor.addTab(self.tab_statistics_doctor_monthly_income, '掛號收費統計')

    # 醫師門診人數月報表統計 - 耀康 2025-01-18
    def _add_statistic_doctor_monthly_person_count(self, year, month, doctor):
        self.tab_statistics_doctor_monthly_person_count = module_utils.get_statistics_doctor_monthly_person_count(
            self, self.database, self.system_settings, year, month, doctor)
        self.tab_statistics_doctor_monthly_person_count.start_calculate()
        self.ui.tabWidget_statistics_doctor.addTab(self.tab_statistics_doctor_monthly_person_count, '人數月報表')

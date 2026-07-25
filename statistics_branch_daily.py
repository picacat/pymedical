# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import db_utils
from libs import dialog_utils
from libs import module_utils


# 分院統計日報表 2022.01.19
class StatisticsBranchDaily(QtWidgets.QMainWindow):
    program_name = '分院日報表'

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsBranchDaily, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "current_date": None,
        }

        self.database_list = db_utils.get_host_database_dict(self.database, '分院統計')
        clinic_name = self.system_settings.field('院所名稱')
        self.database_list[clinic_name] = {'database': self.database}

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_BRANCH_DAILY, self)
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
        dialog = dialog_utils.get_dialog_calendar(self, self.database, self.system_settings, self.program_name)

        if self.dialog_setting['dialog_executed']:
            dialog.ui.calendarWidget.setSelectedDate(self.dialog_setting['current_date'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['current_date'] = dialog.ui.calendarWidget.selectedDate()

        dialog.deleteLater()
        year = self.dialog_setting['current_date'].year()
        month = self.dialog_setting['current_date'].month()
        day = self.dialog_setting['current_date'].day()

        self._set_tab_widget(year, month, day)

    def _set_tab_widget(self, year, month, day):
        self.ui.tabWidget_statistics_daily.clear()

        self.ui.statusbar.showMessage(
            f' 統計日期: {year} 年 {month:0>2} 月 {day:0>2}  日'
        )

        self._add_statistic_daily_person(year, month, day)
        self._add_statistic_daily_income(year, month, day)

    # 分院日報表人數統計
    def _add_statistic_daily_person(self, year, month, day):
        self.tab_statistics_daily_person = module_utils.get_statistics_branch_daily_person(
            self, self.database, self.system_settings, self.database_list, year, month, day
        )
        self.tab_statistics_daily_person.start_calculate()
        self.ui.tabWidget_statistics_daily.addTab(self.tab_statistics_daily_person, '門診人數統計')

    # 分院日報表金額統計
    def _add_statistic_daily_income(self, year, month, day):
        self.tab_statistics_daily_income = module_utils.get_statistics_branch_daily_income(
            self, self.database, self.system_settings, self.database_list, year, month, day,
        )
        self.tab_statistics_daily_income.start_calculate()
        self.ui.tabWidget_statistics_daily.addTab(self.tab_statistics_daily_income, '門診金額統計')

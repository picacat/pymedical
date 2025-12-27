# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import export_utils
from libs import dialog_utils
from libs import module_utils
from libs import personnel_utils


# 綜合業績報表 2020.03.27
class StatisticsDaily(QtWidgets.QMainWindow):
    program_name = '日報表'

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDaily, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self.dialog_setting = {
            "dialog_executed": False,
            "current_date": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DAILY, self)
        system_utils.set_css(self, self.system_settings)
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_excel.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, self.program_name)

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

        self.ui.statusbar.showMessage(f' 統計期間: {year}年 {month}月 {day}日')
        self._add_statistic_week_person(year, month, day)

    # 人數統計
    def _add_statistic_week_person(self, year, month, day):
        self.tab_statistics_daily_person = module_utils.get_statistics_daily_person(
                self, self.database, self.system_settings, year, month, day)
        self.tab_statistics_daily_person.start_calculate()
        self.ui.tabWidget_statistics_daily.addTab(self.tab_statistics_daily_person, '人數日報表')

    def _export_to_excel(self):
        self.tab_statistics_daily_person.export_to_excel()

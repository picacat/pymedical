
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 照護機構院民資料報表
class StatisticsNursingHome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsNursingHome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
            "month": None,
        }
        self.user_name = system_utils.get_user_name(self.system_settings)

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_NURSING_HOME, self)
        system_utils.set_css(self, self.system_settings)

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
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, None)

        if self.dialog_setting['dialog_executed']:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting['year'])
            dialog.ui.comboBox_month.setCurrentText(self.dialog_setting['month'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = dialog.ui.comboBox_year.currentText()
        month = dialog.ui.comboBox_month.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['year'] = year
        self.dialog_setting['month'] = month

        dialog.deleteLater()
        self._set_tab_widget(year, month)

    def _set_tab_widget(self, year, month):
        self.ui.tabWidget_statistics.clear()

        self.ui.statusbar.showMessage(f' 統計期間: {year}年 {month}月')

        self._add_statistic_nursing_home_data(year, month)
        self._add_statistic_nursing_home_daily_data(year, month)

    # 照護機構院民資料
    def _add_statistic_nursing_home_data(self, year, month):
        self.tab_statistics_nursing_home_data = module_utils.get_statistics_nursing_home_data(
                self, self.database, self.system_settings, year, month)
        self.tab_statistics_nursing_home_data.read_data()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_nursing_home_data, '院民資料')

    # 照護機構院民資料日報表
    def _add_statistic_nursing_home_daily_data(self, year, month):
        self.tab_statistics_nursing_home_daily_data = module_utils.get_statistics_nursing_home_daily_data(
                self, self.database, self.system_settings, year, month)
        self.tab_statistics_nursing_home_daily_data.read_data()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_nursing_home_daily_data, '日報表')

    def refresh_patient_record(self):
        self.tab_statistics_nursing_home_data.refresh_patient_record()


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 孕產照護報表 2021.09.13
class StatisticsInsPregnant(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsPregnant, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_PREGNANT, self)
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
        dialog = dialog_utils.get_dialog_date_duration(self, self.database, self.system_settings)
        dialog.set_title('請選擇起訖日期')

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.ui.dateEdit_start_date.date()
        end_date = dialog.ui.dateEdit_end_date.date()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = start_date
        self.dialog_setting['end_date'] = end_date

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date)

    def _set_tab_widget(self, start_date, end_date):
        self.ui.tabWidget_statistics.clear()

        start_date = start_date.toString('yyyy-MM-dd')
        end_date = end_date.toString('yyyy-MM-dd')
        self.ui.statusbar.showMessage(f' 統計期間: {start_date} 至 {end_date}')

        self._add_statistic_ins_pregnant_female(start_date, end_date)
        self._add_statistic_ins_pregnant_male(start_date, end_date)
        self._add_statistic_ins_pregnant_keep_baby(start_date, end_date)

    # 助孕照護 - 女
    def _add_statistic_ins_pregnant_female(self, start_date, end_date):
        self.tab_statistics_ins_pregnant_female = module_utils.get_statistics_ins_pregnant_female(
                self, self.database, self.system_settings, start_date, end_date)
        self.tab_statistics_ins_pregnant_female.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_ins_pregnant_female, '助孕照護(女)')

    # 助孕照護 - 男
    def _add_statistic_ins_pregnant_male(self, start_date, end_date):
        self.tab_statistics_ins_pregnant_male = module_utils.get_statistics_ins_pregnant_male(
                self, self.database, self.system_settings, start_date, end_date)
        self.tab_statistics_ins_pregnant_male.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_ins_pregnant_male, '助孕照護(男)')

    # 保胎照護
    def _add_statistic_ins_pregnant_keep_baby(self, start_date, end_date):
        self.tab_statistics_ins_pregnant_keep_baby = module_utils.get_statistics_ins_pregnant_keep_baby(
                self, self.database, self.system_settings, start_date, end_date)
        self.tab_statistics_ins_pregnant_keep_baby.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_ins_pregnant_keep_baby, '保胎照護')

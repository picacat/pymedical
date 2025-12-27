
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog

from libs import ui_utils
from libs import system_utils
from libs import export_utils
from libs import dialog_utils
from libs import module_utils


# 業績成長統計 2023.04.22
class StatisticsGrowthRate(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsGrowthRate, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
            "month": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_GROWTH_RATE, self)
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

        self._add_statistic_growth_month(year, month)
        self._add_statistic_growth_year(year, month)
        self._add_statistic_growth_income(year, month)

    # 歷年同月人數統計
    def _add_statistic_growth_month(self, year, month):
        self.tab_statistics_growth_year = module_utils.get_statistics_growth_month(
                self, self.database, self.system_settings, year, month)
        self.tab_statistics_growth_year.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_growth_year, f'{month}月份同期成長統計')

    # 當年人數統計
    def _add_statistic_growth_year(self, year, month):
        self.tab_statistics_growth_year = module_utils.get_statistics_growth_year(
                self, self.database, self.system_settings, year, month)
        self.tab_statistics_growth_year.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_growth_year, f'{year}年度成長統計')

    # 當年收入統計
    def _add_statistic_growth_income(self, year, month):
        self.tab_statistics_growth_income = module_utils.get_statistics_growth_income(
                self, self.database, self.system_settings, year, month)
        self.tab_statistics_growth_income.start_calculate()
        self.ui.tabWidget_statistics.addTab(self.tab_statistics_growth_income, f'{year}年度收入統計')

    def _export_to_excel(self):
        if self.ui.tabWidget_statistics.count() <= 0:
            return

        year = self.dialog_setting['year']
        month = self.dialog_setting['month']
        clinic_name = self.system_settings.field('院所名稱')
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出綜合業績報表",
            f'{year}年{month}月{clinic_name}綜合業績報表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_multiple_performance_to_excel(
            self.system_settings.field('院所名稱'),
            self.dialog_setting['year'],
            self.dialog_setting['month'],
            excel_file_name, self.ui.tabWidget_statistics
        )

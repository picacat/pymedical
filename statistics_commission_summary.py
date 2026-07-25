
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils
from libs import personnel_utils


# 自費銷售抽成總表 2021.06.03
class StatisticsCommissionSummary(QtWidgets.QMainWindow):
    program_name = '自費銷售抽成總表'

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsCommissionSummary, self).__init__(parent)
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
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_COMMISSION_SUMMARY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)

    def _export_to_excel(self):
        pass

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(
                self.database, self.program_name, '匯出Excel', self.user_name) != 'Y':
            self.ui.action_export_excel.setEnabled(False)
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_excel.setEnabled(False)

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
        self.ui.tabWidget_statistics_summary.clear()

        self.ui.statusbar.showMessage(f' 統計期間: {year} 年 {month} 月')

        self._add_statistic_commission_amount(year, month)

    # 醫師自費銷售業績統計
    def _add_statistic_commission_amount(self, year, month):
        self.tab_statistics_commission_amount = module_utils.get_statistics_commission_amount(
            self, self.database, self.system_settings, year, month
        )
        self.tab_statistics_commission_amount.start_calculate()
        self.ui.tabWidget_statistics_summary.addTab(self.tab_statistics_commission_amount, '自費銷售抽成金額總表')

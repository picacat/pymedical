# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import (
    dialog_utils,
    module_utils,
    personnel_utils,
    system_utils,
    ui_utils,
)


# 門市收入統計 2026-11-24
class StatisticsStoreRevenue(QtWidgets.QMainWindow):
    program_name = "門市收入統計"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_STORE_REVENUE, self)
        system_utils.set_css(self, self.system_settings)
        if (
            personnel_utils.get_permission(
                self.database, "門市收入統計", "執行門市收入統計", self.user_name
            )
            == "Y"
        ):
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
        dialog = dialog_utils.get_dialog_date_duration(
            self, self.database, self.system_settings
        )
        dialog.set_title("請選擇起訖日期")

        if self.dialog_setting["dialog_executed"]:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting["start_date"])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting["end_date"])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.ui.dateEdit_start_date.date()
        end_date = dialog.ui.dateEdit_end_date.date()

        self.dialog_setting["dialog_executed"] = True
        self.dialog_setting["start_date"] = start_date
        self.dialog_setting["end_date"] = end_date

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date)

    def _set_tab_widget(self, start_date, end_date):
        self.ui.tabWidget_statistics_store_revenue.clear()
        start_date = start_date.toString("yyyy-MM-dd")
        end_date = end_date.toString("yyyy-MM-dd")
        self.ui.statusbar.showMessage(f" 統計期間: {start_date} 至 {end_date}")
        self._add_statistic_store_revenue_amount(start_date, end_date)

    # 人數統計
    def _add_statistic_store_revenue_amount(self, start_date, end_date):
        self.tab_statistics_store_revenue = (
            module_utils.get_statistics_store_revenue_amount(
                self, self.database, self.system_settings, start_date, end_date
            )
        )
        self.tab_statistics_store_revenue.start_calculate()
        self.ui.tabWidget_statistics_store_revenue.addTab(
            self.tab_statistics_store_revenue, "門市收入金額統計"
        )

    def _export_to_excel(self):
        self.tab_statistics_store_revenue.export_to_excel()

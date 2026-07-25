# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 推拿統計 2020.11.03
class StatisticsMassager(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMassager, self).__init__(parent)
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
            "only_traditional_massage": False,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MASSAGER, self)
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
        dialog = dialog_utils.get_dialog_statistics_therapist(
            self, self.database, self.system_settings, '推拿師統計', '推拿師',
        )

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])

            if self.dialog_setting['ins_type'] == '全部':
                dialog.ui.radioButton_all.setChecked(True)
            elif self.dialog_setting['ins_type'] == '健保':
                dialog.ui.radioButton_ins.setChecked(True)
            elif self.dialog_setting['ins_type'] == '自費':
                dialog.ui.radioButton_self.setChecked(True)

            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting['period'])
            dialog.ui.comboBox_therapist.setCurrentText(self.dialog_setting['therapist'])
            dialog.ui.checkBox_only_traditional_massage.setChecked(self.dialog_setting['only_traditional_massage'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        period = dialog.period()
        ins_type = dialog.ins_type()
        therapist = dialog.therapist()
        only_traditional_massage = dialog.only_traditional_massage()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['period'] = period
        self.dialog_setting['ins_type'] = ins_type
        self.dialog_setting['therapist'] = therapist
        self.dialog_setting['only_traditional_massage'] = only_traditional_massage

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, period, ins_type, therapist, only_traditional_massage)

    def _set_tab_widget(self, start_date, end_date, period, ins_type, massager, only_traditional_massage):
        self.ui.tabWidget_statistics_massager.clear()

        self.ui.statusbar.showMessage(
            f' 統計期間: 從 {start_date[:10]} 至 {end_date[:10]} {period} 保險: {ins_type} 推拿師: {massager}'
        )

        self._add_statistic_massager_count(start_date, end_date, period, ins_type, massager, only_traditional_massage)
        self._add_statistic_massager_summary(start_date, end_date, only_traditional_massage)
        self._add_statistic_massager_income(start_date, end_date, period, ins_type, massager, only_traditional_massage)
        self._add_statistic_massager_list(start_date, end_date, period, massager, only_traditional_massage)

    # 推拿師父人數人數統計
    def _add_statistic_massager_count(
            self, start_date, end_date, period, ins_type, massager, only_traditional_massage):
        self.tab_statistics_massager_count = module_utils.get_statistics_massager_count(
            self, self.database, self.system_settings,
            start_date, end_date, period, ins_type, massager, only_traditional_massage
        )
        self.tab_statistics_massager_count.start_calculate()
        self.ui.tabWidget_statistics_massager.addTab(self.tab_statistics_massager_count, '推拿人數統計')

    # 推拿師父人數人數統計 (總表)
    def _add_statistic_massager_summary(self, start_date, end_date, only_traditional_massage):
        self.tab_statistics_massager_summary = module_utils.get_statistics_massager_summary(
            self, self.database, self.system_settings, start_date, end_date, only_traditional_massage
        )
        self.tab_statistics_massager_summary.start_calculate()
        self.ui.tabWidget_statistics_massager.addTab(self.tab_statistics_massager_summary, '推拿人數統計總表')

    # 醫師門診收入統計
    def _add_statistic_massager_income(
            self, start_date, end_date, period, ins_type, massager, only_traditional_massage):
        self.tab_statistics_massager_income = module_utils.get_statistics_massager_income(
            self, self.database, self.system_settings,
            start_date, end_date, period, ins_type, massager, only_traditional_massage
        )
        self.tab_statistics_massager_income.start_calculate()
        self.ui.tabWidget_statistics_massager.addTab(self.tab_statistics_massager_income, '推拿收入統計')

    # 醫師自費銷售統計
    def _add_statistic_massager_list(self, start_date, end_date, period, massager, only_traditional_massage):
        self.tab_statistics_massager_list = module_utils.get_statistics_massager_list(
            self, self.database, self.system_settings,
            start_date, end_date, period, massager, only_traditional_massage
        )
        self.tab_statistics_massager_list.start_calculate()
        self.ui.tabWidget_statistics_massager.addTab(self.tab_statistics_massager_list, '推拿業績明細')

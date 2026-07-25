
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils
from libs import personnel_utils


# 醫師自費銷售金額總表 2022.02.23
class StatisticsSalesSummary(QtWidgets.QMainWindow):
    program_name = '醫師自費銷售金額總表'

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsSalesSummary, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "ins_type": None,
            "therapist": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_SALES_SUMMARY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_print_list.triggered.connect(self._print_doctor_sale_summary)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(
                self.database, self.program_name, '匯出Excel', self.user_name) != 'Y':
            self.ui.action_export_excel.setEnabled(False)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_statistics_therapist(
            self, self.database, self.system_settings, '醫師銷售業績統計', '醫師',
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

            dialog.ui.comboBox_therapist.setCurrentText(self.dialog_setting['therapist'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        ins_type = dialog.ins_type()
        therapist = dialog.ui.comboBox_therapist.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['ins_type'] = ins_type
        self.dialog_setting['therapist'] = therapist

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, ins_type, therapist)

    def _set_tab_widget(self, start_date, end_date, ins_type, doctor):
        self.ui.tabWidget_statistics_sales_summary.clear()
        self.ui.statusbar.showMessage(f' 統計期間: {start_date} 至 {end_date} {doctor}醫師')

        self._add_statistic_doctor_sale_summary(start_date, end_date, ins_type, doctor)

    # 醫師自費銷售金額總表
    def _add_statistic_doctor_sale_summary(self, start_date, end_date, ins_type, doctor):
        self.tab_statistics_doctor_sale_summary = module_utils.get_statistics_doctor_sale_summary(
            self, self.database, self.system_settings, start_date, end_date, ins_type, doctor,
        )
        self.tab_statistics_doctor_sale_summary.start_calculate()
        self.ui.tabWidget_statistics_sales_summary.addTab(self.tab_statistics_doctor_sale_summary, '醫師自費銷售金額總表')

    def _export_to_excel(self):
        if self.ui.tabWidget_statistics_sales_summary.currentIndex() == 0:
            self.tab_statistics_doctor_sale_summary.export_sales_volume()
        elif self.ui.tabWidget_statistics_sales_summary.currentIndex() == 1:
            self.tab_statistics_doctor_project_sale.export_to_excel()

    def _print_doctor_sale_summary(self):
        self.tab_statistics_doctor_sale_summary.print_sale_summary()

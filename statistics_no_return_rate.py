# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 未回診統計 2020.04.07
class StatisticsNoReturnRate(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsNoReturnRate, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "no_return_start_date": None,
            "no_return_end_date": None,
            "ins_type": None,
            "treat_type": None,
            "visit": None,
            "doctor": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_NO_RETURN_RATE, self)
        system_utils.set_css(self, self.system_settings)

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
        dialog = dialog_utils.get_dialog_statistics_no_return_rate(
            self, self.database, self.system_settings, '未回診統計',
        )

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.dateEdit_no_return_start_date.setDate(self.dialog_setting['no_return_start_date'])
            dialog.ui.dateEdit_no_return_end_date.setDate(self.dialog_setting['no_return_end_date'])
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting['doctor'])

            dialog.set_ins_type(self.dialog_setting['ins_type'])
            dialog.set_treat_type(self.dialog_setting['treat_type'])
            dialog.set_visit(self.dialog_setting['visit'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['no_return_start_date'] = dialog.ui.dateEdit_no_return_start_date.date()
        self.dialog_setting['no_return_end_date'] = dialog.ui.dateEdit_no_return_end_date.date()
        self.dialog_setting['ins_type'] = dialog.ins_type()
        self.dialog_setting['treat_type'] = dialog.treat_type()
        self.dialog_setting['visit'] = dialog.visit()
        self.dialog_setting['doctor'] = dialog.ui.comboBox_doctor.currentText()

        dialog.deleteLater()
        self._set_tab_widget(
            self.dialog_setting['start_date'].toString('yyyy-MM-dd 00:00:00'),
            self.dialog_setting['end_date'].toString('yyyy-MM-dd 00:00:00'),
            self.dialog_setting['no_return_start_date'].toString('yyyy-MM-dd 00:00:00'),
            self.dialog_setting['no_return_end_date'].toString('yyyy-MM-dd 00:00:00'),
            self.dialog_setting['ins_type'],
            self.dialog_setting['treat_type'],
            self.dialog_setting['visit'],
            self.dialog_setting['doctor'],
        )

    def _set_tab_widget(self, start_date, end_date, no_return_start_date, no_return_end_date,
                        ins_type, treat_type, visit, doctor):
        self.ui.tabWidget_statistics_return_rate.clear()

        self.ui.statusbar.showMessage(f'''
            統計期間: 門診日期: {start_date[:10]} 至 {end_date[:10]},
            未回診日期: {no_return_start_date[:10]} 至 {no_return_end_date[:10]},
            保險: {ins_type}, 類別: {treat_type} 醫師: {doctor}
        ''')

        self._add_statistic_doctor_count(
            start_date, end_date, no_return_start_date, no_return_end_date,
            ins_type, treat_type, visit, doctor,
        )

    # 醫師回診率統計
    def _add_statistic_doctor_count(self, start_date, end_date, no_return_start_date, no_return_end_date,
                                    ins_type, treat_type, visit, doctor):
        self.tab_statistics_no_return_rate_doctor = module_utils.get_statistics_no_return_rate_doctor(
            self, self.database, self.system_settings,
            start_date, end_date, no_return_start_date, no_return_end_date,
            ins_type, treat_type, visit, doctor,
        )
        self.tab_statistics_no_return_rate_doctor.start_calculate()
        self.ui.tabWidget_statistics_return_rate.addTab(self.tab_statistics_no_return_rate_doctor, '醫師未回診率')

    def _export_to_excel(self):
        if self.ui.tabWidget_statistics_return_rate.currentIndex() == 0:
            self.tab_statistics_no_return_rate_doctor.export_to_excel()

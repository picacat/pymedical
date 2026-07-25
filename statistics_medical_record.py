# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 病歷統計 2019.06.10
class StatisticsMedicalRecord(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMedicalRecord, self).__init__(parent)
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
            "option": [],
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MEDICAL_RECORD, self)
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
        dialog = dialog_utils.get_dialog_statistics_therapist(
            self, self.database, self.system_settings, '病歷統計', '醫師',
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

            if '資源不足' in self.dialog_setting['option']:
                dialog.ui.checkBox_lack_area.setChecked(True)
            if '巡迴醫療' in self.dialog_setting['option']:
                dialog.ui.checkBox_tour.setChecked(True)
            if '法定傳染病' in self.dialog_setting['option']:
                dialog.ui.checkBox_infectious.setChecked(True)
            if '視訊門診' in self.dialog_setting['option']:
                dialog.ui.checkBox_telecom.setChecked(True)
            if '照護機構' in self.dialog_setting['option']:
                dialog.ui.checkBox_care.setChecked(True)

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        period = dialog.period()
        ins_type = dialog.ins_type()
        therapist = dialog.therapist()
        weekday_list = dialog.weekday_list()

        option = []
        if dialog.checkBox_lack_area.isChecked():
            option.append('資源不足')
        if dialog.checkBox_tour.isChecked():
            option.append('巡迴醫療')
        if dialog.checkBox_infectious.isChecked():
            option.append('法定傳染病')
        if dialog.checkBox_telecom.isChecked():
            option.append('視訊門診')
        if dialog.checkBox_care.isChecked():
            option.append('照護機構')

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['period'] = period
        self.dialog_setting['ins_type'] = ins_type
        self.dialog_setting['therapist'] = therapist
        self.dialog_setting['option'] = option

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, ins_type, therapist, option, weekday_list)

    def _set_tab_widget(self, start_date, end_date, ins_type, doctor, option, weekday_list):
        self.ui.tabWidget_statistics_medical_record.clear()

        self.ui.statusbar.showMessage(
            f' 統計期間: 從 {start_date[:10]} 至 {end_date[:10]} 保險: {ins_type} 醫師: {doctor}'
        )

        self._add_statistic_medical_record_disease_rank(start_date, end_date, ins_type, doctor, option, weekday_list)
        self._add_statistic_medical_record_diag_time_length(start_date, end_date, ins_type, doctor, weekday_list)

    # 疾病排行
    def _add_statistic_medical_record_disease_rank(self, start_date, end_date, ins_type, doctor, option, weekday_list):
        self.tab_statistics_medical_record_disease_rank = module_utils.get_statistics_medical_record_disease_rank(
                self, self.database, self.system_settings, start_date, end_date, ins_type, doctor, option, weekday_list
            )
        self.tab_statistics_medical_record_disease_rank.start_calculate()
        self.ui.tabWidget_statistics_medical_record.addTab(
            self.tab_statistics_medical_record_disease_rank, '疾病排行'
        )

    # 看診時間統計
    def _add_statistic_medical_record_diag_time_length(self, start_date, end_date, ins_type, doctor, weekday_list):
        self.tab_statistics_medical_record_diag_time_length = \
            module_utils.get_statistics_medical_record_diag_time_length(
                self, self.database, self.system_settings, start_date, end_date, ins_type, doctor, weekday_list)
        self.tab_statistics_medical_record_diag_time_length.start_calculate()
        self.ui.tabWidget_statistics_medical_record.addTab(
            self.tab_statistics_medical_record_diag_time_length, '看診時間統計'
        )

    def _export_to_excel(self):
        if self.ui.tabWidget_statistics_medical_record.currentIndex() == 0:
            self.tab_statistics_medical_record_disease_rank.export_to_excel()
        elif self.ui.tabWidget_statistics_medical_record.currentIndex() == 1:
            self.tab_statistics_medical_record_diag_time_length.export_to_excel()

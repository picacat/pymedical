
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 健保申報業績 2019.12.02
class StatisticsInsPerformance(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsPerformance, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "therapist": None,
            "show_medical_records": False,
            "exclude_c5": False,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_PERFORMANCE, self)
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
        dialog = dialog_utils.get_dialog_ins_date_doctor(
            self, self.database, self.system_settings, '健保申報業績',
        )

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting['therapist'])
            dialog.ui.checkBox_from_medical_record.setChecked(self.dialog_setting['show_medical_records'])
            dialog.ui.checkBox_exclude_c5.setChecked(self.dialog_setting['exclude_c5'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        doctor = dialog.ui.comboBox_doctor.currentText()
        show_medical_records = dialog.ui.checkBox_from_medical_record.isChecked()
        exclude_c5 = dialog.ui.checkBox_exclude_c5.isChecked()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['therapist'] = doctor
        self.dialog_setting['show_medical_records'] = show_medical_records
        self.dialog_setting['exclude_c5'] = exclude_c5

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, doctor, exclude_c5)

    def _set_tab_widget(self, start_date, end_date, doctor, exclude_c5):
        self.ui.tabWidget_ins_performance.clear()

        self.ui.statusbar.showMessage(
            f' 統計期間: 從 {start_date[:10]} 至 {end_date[:10]} 醫師: {doctor}'
        )

        if self.dialog_setting['show_medical_records']:
            self._add_statistic_ins_performance_medical_record(start_date, end_date, doctor)

        self._add_statistic_ins_performance_ins_apply(start_date, end_date, exclude_c5)
        self._add_statistic_doctor_achievement(
            start_date, end_date, doctor, exclude_c5)

    # 健保業績-依病歷
    def _add_statistic_ins_performance_medical_record(self, start_date, end_date, doctor):
        self.tab_ins_performance_medical_record = module_utils.get_statistics_ins_performance_medical_record(
                self, self.database, self.system_settings,
                start_date, end_date, doctor,
            )
        self.tab_ins_performance_medical_record.start_calculate()
        self.ui.tabWidget_ins_performance.addTab(self.tab_ins_performance_medical_record, '健保業績-依病歷')

    def _add_statistic_ins_performance_ins_apply(self, start_date, end_date, exclude_c5):
        self.tab_ins_apply_fee_performance = module_utils.get_ins_apply_fee_performance(
            self, self.database, self.system_settings,
            self.dialog_setting['start_date'].year(),
            self.dialog_setting['start_date'].month(),
            self.dialog_setting['therapist'],
            start_date, end_date, '全月', '申報', exclude_c5
        )
        self.ui.tabWidget_ins_performance.addTab(self.tab_ins_apply_fee_performance, '健保業績-依申報')

    # 醫師業績
    def _add_statistic_doctor_achievement(self, apply_year, apply_month, doctor, exclude_c5):
        self.tab_statistics_ins_performance_doctor = \
            module_utils.get_statistics_ins_performance_doctor(
                self, self.database, self.system_settings,
                self.dialog_setting['start_date'].year(),
                self.dialog_setting['start_date'].month(),
                doctor, exclude_c5)
        self.tab_statistics_ins_performance_doctor.start_calculate()
        self.ui.tabWidget_ins_performance.addTab(
            self.tab_statistics_ins_performance_doctor, '醫師業績')


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import ui_utils
from libs import system_utils
from libs import dialog_utils
from libs import module_utils


# 健保門診優惠統計 2022.09.01 重改
class StatisticsInsDiscount(QtWidgets.QMainWindow):

    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsDiscount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.program_name = '健保門診優惠統計'
        self.user_name = system_utils.get_user_name(self.system_settings)

        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "first_course": None,
            "basic_regist_fee_discount": False,
            "only_discount": False,
            "therapist": None,
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_DISCOUNT, self)
        system_utils.set_css(self, self.system_settings)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_open_dialog.triggered.connect(self.open_dialog)
        self.ui.action_print_list.triggered.connect(self._print_list)
        self.ui.action_export_excel.triggered.connect(self._export_to_excel)
        self.ui.action_open_medical_record.triggered.connect(self._open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_ins_date_doctor(
            self, self.database, self.system_settings, '健保門診優惠統計',
        )

        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.comboBox_doctor.setCurrentText(self.dialog_setting['therapist'])
            dialog.ui.checkBox_basic_regist_fee_discount.setChecked(self.dialog_setting['basic_regist_fee_discount'])
            dialog.ui.checkBox_first_course.setChecked(self.dialog_setting['first_course'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_date = dialog.start_date()
        end_date = dialog.end_date()
        doctor = dialog.ui.comboBox_doctor.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['therapist'] = doctor
        if dialog.ui.checkBox_basic_regist_fee_discount.isChecked():
            self.dialog_setting['basic_regist_fee_discount'] = True
        else:
            self.dialog_setting['basic_regist_fee_discount'] = False

        if dialog.ui.checkBox_first_course.isChecked():
            self.dialog_setting['first_course'] = True
        else:
            self.dialog_setting['first_course'] = False

        if dialog.ui.checkBox_regist_fee_discount.isChecked():
            self.dialog_setting['only_discount'] = True
        else:
            self.dialog_setting['only_discount'] = False

        dialog.deleteLater()
        self._set_tab_widget(start_date, end_date, doctor)

    def _set_tab_widget(self, start_date, end_date, doctor):
        self.ui.tabWidget_statistics_ins_discount.clear()

        start_date = start_date[:10]
        end_date = end_date[:10]
        self.ui.statusbar.showMessage(
            f' 統計期間: 從 {start_date} 至 {end_date} 醫師: {doctor}'
        )

        self._add_statistic_ins_discount_regist_fee(start_date, end_date, doctor)
        self._add_statistic_ins_discount_diag_share_fee(start_date, end_date, doctor)
        self._add_statistic_ins_discount_drug_share_fee(start_date, end_date, doctor)

    # 掛號費優待統計
    def _add_statistic_ins_discount_regist_fee(self, start_date, end_date, doctor):
        self.tab_statistics_ins_discount_regist_fee = module_utils.get_statistics_ins_discount_regist_fee(
            self, self.database, self.system_settings, start_date, end_date, doctor,
            self.dialog_setting['first_course'],
            self.dialog_setting['only_discount'],
            self.dialog_setting['basic_regist_fee_discount'],
        )
        self.tab_statistics_ins_discount_regist_fee.start_calculate()
        self.ui.tabWidget_statistics_ins_discount.addTab(
            self.tab_statistics_ins_discount_regist_fee, '掛號費優待統計'
        )

    # 門診負擔優待統計
    def _add_statistic_ins_discount_diag_share_fee(self, start_date, end_date, doctor):
        self.tab_statistics_ins_discount_diag_share_fee = module_utils.get_statistics_ins_discount_diag_share_fee(
                self, self.database, self.system_settings,
                start_date, end_date, doctor, self.dialog_setting['first_course'],
            )
        self.tab_statistics_ins_discount_diag_share_fee.start_calculate()
        self.ui.tabWidget_statistics_ins_discount.addTab(
            self.tab_statistics_ins_discount_diag_share_fee, '免收門診負擔統計'
        )

    # 藥品負擔優待統計
    def _add_statistic_ins_discount_drug_share_fee(self, start_date, end_date, doctor):
        self.tab_statistics_ins_discount_drug_share_fee = module_utils.get_statistics_ins_discount_drug_share_fee(
                self, self.database, self.system_settings,
                start_date, end_date, doctor,
            )
        self.tab_statistics_ins_discount_drug_share_fee.start_calculate()
        self.ui.tabWidget_statistics_ins_discount.addTab(
            self.tab_statistics_ins_discount_drug_share_fee, '免收藥品負擔統計'
        )

    def _export_to_excel(self):
        if self.ui.tabWidget_statistics_ins_discount.currentIndex() == 0:
            self.tab_statistics_ins_discount_regist_fee.export_to_excel()
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 1:
            self.tab_statistics_ins_discount_diag_share_fee.export_to_excel()
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 2:
            self.tab_statistics_ins_discount_drug_share_fee.export_to_excel()

    def _print_list(self):
        if self.ui.tabWidget_statistics_ins_discount.currentIndex() == 0:
            self.tab_statistics_ins_discount_regist_fee.print_list()
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 1:
            self.tab_statistics_ins_discount_diag_share_fee.print_list()
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 2:
            self.tab_statistics_ins_discount_drug_share_fee.print_list()

    def _open_medical_record(self):
        if self.ui.tabWidget_statistics_ins_discount.currentIndex() == 0:
            tab_widget = self.tab_statistics_ins_discount_regist_fee
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 1:
            tab_widget = self.tab_statistics_ins_discount_diag_share_fee
        elif self.ui.tabWidget_statistics_ins_discount.currentIndex() == 2:
            tab_widget = self.tab_statistics_ins_discount_drug_share_fee
        else:
            return

        tab_widget.open_medical_record()

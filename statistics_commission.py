# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import dialog_utils, module_utils, system_utils, ui_utils


# 自費抽成統計 2026.08.29
class StatisticsCommission(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_COMMISSION, self)
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
            self,
            self.database,
            self.system_settings,
            "醫師統計",
            "全部",
        )

        if self.dialog_setting["dialog_executed"]:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting["start_date"])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting["end_date"])

            if self.dialog_setting["ins_type"] == "全部":
                dialog.ui.radioButton_all.setChecked(True)
            elif self.dialog_setting["ins_type"] == "健保":
                dialog.ui.radioButton_ins.setChecked(True)
            elif self.dialog_setting["ins_type"] == "自費":
                dialog.ui.radioButton_self.setChecked(True)

            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting["period"])
            dialog.ui.comboBox_therapist.setCurrentText(
                self.dialog_setting["therapist"]
            )

            if "資源不足" in self.dialog_setting["option"]:
                dialog.ui.checkBox_lack_area.setChecked(True)
            if "巡迴醫療" in self.dialog_setting["option"]:
                dialog.ui.checkBox_tour.setChecked(True)
            if "法定傳染病" in self.dialog_setting["option"]:
                dialog.ui.checkBox_infectious.setChecked(True)
            if "視訊門診" in self.dialog_setting["option"]:
                dialog.ui.checkBox_telecom.setChecked(True)
            if "照護機構" in self.dialog_setting["option"]:
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
            option.append("資源不足")
        if dialog.checkBox_tour.isChecked():
            option.append("巡迴醫療")
        if dialog.checkBox_infectious.isChecked():
            option.append("法定傳染病")
        if dialog.checkBox_telecom.isChecked():
            option.append("視訊門診")
        if dialog.checkBox_care.isChecked():
            option.append("照護機構")

        self.dialog_setting["dialog_executed"] = True
        self.dialog_setting["start_date"] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting["end_date"] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting["period"] = period
        self.dialog_setting["ins_type"] = ins_type
        self.dialog_setting["therapist"] = therapist
        self.dialog_setting["option"] = option

        dialog.deleteLater()
        self._set_tab_widget(
            start_date, end_date, period, ins_type, therapist, option, weekday_list
        )

    def _set_tab_widget(
        self, start_date, end_date, period, ins_type, doctor, option, weekday_list
    ):
        self.ui.tabWidget_statistics_doctor.clear()

        self.ui.statusbar.showMessage(
            f" 統計期間: 從 {start_date[:10]} 至 {end_date[:10]} {period} 保險: {ins_type} 醫師: {doctor}"
        )

        self._add_statistic_doctor_sale(
            start_date, end_date, period, doctor, option, weekday_list
        )

    # 醫師自費銷售統計
    def _add_statistic_doctor_sale(
        self, start_date, end_date, period, doctor, option, weekday_list
    ):
        self.tab_statistics_commission_sale = (
            module_utils.get_statistics_commission_sale(
                self,
                self.database,
                self.system_settings,
                start_date,
                end_date,
                period,
                doctor,
                option,
                weekday_list,
            )
        )
        self.tab_statistics_commission_sale.start_calculate()
        self.ui.tabWidget_statistics_doctor.addTab(
            self.tab_statistics_commission_sale, "自費銷售抽成統計"
        )

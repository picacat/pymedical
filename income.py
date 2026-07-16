# 掛號櫃台結帳 2018.11.15
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox

from libs import (
    dialog_utils,
    module_utils,
    personnel_utils,
    printer_utils,
    system_utils,
    ui_utils,
)


# 掛號櫃台結帳
class Income(QtWidgets.QMainWindow):
    program_name = "掛號櫃台結帳"

    # 初始化
    def __init__(self, parent=None, *args):
        super(Income, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.tab_income_cash_flow = None
        self.tab_income_list = None
        self.tab_income_self_prescript = None
        self.tab_income_project = None

        self.dialog_setting = {
            "dialog_executed": False,
            "case_date": None,
            "start_date": None,
            "end_date": None,
            "period": None,
            "therapist": None,
            "room": None,
            "cashier": None,
            "regist_type": None,
            "income_source": None,
            "calculate_by_cashier": False,
        }

        self.income_list_columns = {
            "case_key": 0,
            "remark": 1,
            "case_date": 2,
            "period": 3,
            "patient_key": 4,
            "name": 5,
            "ins_type": 6,
            "share_type": 7,
            "treat_type": 8,
            "discount_type": 9,
            "card": 10,
            "pres_days": 11,
            "regist_fee": 12,
            "diag_share_fee": 13,
            "drug_share_fee": 14,
            "deposit_fee": 15,
            "refund_fee": 16,
            "repayment": 17,
            "self_total_fee": 18,
            "debt": 19,
            "regist_debt": 20,
            "massage_fee": 21,
            "receipt_fee": 22,
            "registrar": 23,
            "cashier": 24,
            "regist_no": 25,
        }

        self.income_date = None
        self.period = None

        self._set_ui()
        self._set_signal()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def open_medical_record(self, case_key, call_from):
        self.parent.open_medical_record(case_key, call_from)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_income(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_income)
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_print_portrait.triggered.connect(
            lambda: self._print_income("portrait")
        )
        self.ui.action_print_portrait2.triggered.connect(
            lambda: self._print_income2("portrait")
        )
        self.ui.action_print_landscape.triggered.connect(
            lambda: self._print_income("landscape")
        )
        self.ui.action_print_portrait_pdf.triggered.connect(
            lambda: self._print_income("portrait", "pdf")
        )
        self.ui.action_print_landscape_pdf.triggered.connect(
            lambda: self._print_income("landscape", "pdf")
        )
        self.ui.action_export_daily_excel.triggered.connect(self._export_daily_excel)

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "列印日報表", self.user_name
            )
            != "Y"
        ):
            self.ui.action_print_portrait.setEnabled(False)
            self.ui.action_print_landscape.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "匯出日報表", self.user_name
            )
            != "Y"
        ):
            self.ui.action_print_portrait_pdf.setEnabled(False)
            self.ui.action_print_landscape_pdf.setEnabled(False)

        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_print_portrait_pdf.setEnabled(False)
            self.ui.action_print_landscape_pdf.setEnabled(False)
            self.ui.action_export_daily_excel.setEnabled(False)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_income(
            self, self.database, self.system_settings, "掛號櫃台結帳"
        )
        if self.dialog_setting["dialog_executed"]:
            dialog.ui.dateEdit_case_date.setDate(self.dialog_setting["case_date"])
            period = self.dialog_setting["period"]
            if period == "早班":
                dialog.ui.radioButton_period1.setChecked(True)
            elif period == "午班":
                dialog.ui.radioButton_period2.setChecked(True)
            elif period == "晚班":
                dialog.ui.radioButton_period3.setChecked(True)
            # elif period == '早午班':
            #     dialog.ui.radioButton_period4.setChecked(True)
            # elif period == '午晚班':
            #     dialog.ui.radioButton_period5.setChecked(True)
            else:
                dialog.ui.radioButton_all.setChecked(True)

            if self.dialog_setting["calculate_by_cashier"]:
                dialog.ui.checkBox_calculate_by_cashier.setChecked(True)

            dialog.ui.comboBox_therapist.setCurrentText(
                self.dialog_setting["therapist"]
            )
            dialog.ui.comboBox_room.setCurrentText(self.dialog_setting["room"])
            dialog.ui.comboBox_cashier.setCurrentText(self.dialog_setting["cashier"])
            dialog.ui.comboBox_regist_type.setCurrentText(
                self.dialog_setting["regist_type"]
            )

        if dialog.exec_():
            self.dialog_setting["dialog_executed"] = True
            self.dialog_setting["case_date"] = dialog.ui.dateEdit_case_date.date()
            self.dialog_setting["start_date"] = dialog.start_date
            self.dialog_setting["end_date"] = dialog.end_date

            if dialog.ui.radioButton_period1.isChecked():
                self.dialog_setting["period"] = "早班"
            elif dialog.ui.radioButton_period2.isChecked():
                self.dialog_setting["period"] = "午班"
            elif dialog.ui.radioButton_period3.isChecked():
                self.dialog_setting["period"] = "晚班"
            # elif dialog.ui.radioButton_period4.isChecked():
            #     self.dialog_setting['period'] = '早午班'
            # elif dialog.ui.radioButton_period5.isChecked():
            #     self.dialog_setting['period'] = '午晚班'
            else:
                self.dialog_setting["period"] = "全部"

            if dialog.ui.checkBox_calculate_by_cashier.isChecked():
                self.dialog_setting["calculate_by_cashier"] = True
            else:
                self.dialog_setting["calculate_by_cashier"] = False

            if dialog.ui.radioButton_income_all.isChecked():
                self.dialog_setting["income_source"] = "全部"
            elif dialog.ui.radioButton_income_cashier.isChecked():
                self.dialog_setting["income_source"] = "櫃台"
            elif dialog.ui.radioButton_income_cashier_machine.isChecked():
                self.dialog_setting["income_source"] = "掛號機"
            else:
                self.dialog_setting["income_source"] = "全部"

            self.dialog_setting["therapist"] = dialog.comboBox_therapist.currentText()
            self.dialog_setting["room"] = dialog.comboBox_room.currentText()
            self.dialog_setting["cashier"] = dialog.comboBox_cashier.currentText()
            self.dialog_setting["regist_type"] = (
                dialog.comboBox_regist_type.currentText()
            )
            self.start_calculate()
        else:
            self.income_date = None
            self.period = None

        dialog.close_all()
        dialog.deleteLater()

    def start_calculate(self):
        start_date = self.dialog_setting["start_date"]
        end_date = self.dialog_setting["end_date"]
        period = self.dialog_setting["period"]
        therapist = self.dialog_setting["therapist"]
        room = self.dialog_setting["room"]
        cashier = self.dialog_setting["cashier"]
        regist_type = self.dialog_setting["regist_type"]
        income_source = self.dialog_setting["income_source"]
        calculate_by_cashier = self.dialog_setting["calculate_by_cashier"]

        if self.system_settings.field("所有資料都已批價才能結帳") == "Y":
            if self._check_unpaid_cases(
                start_date, end_date, period, regist_type, therapist, room, cashier
            ):
                return

        self.tab_income_cash_flow = module_utils.get_income_cash_flow(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            regist_type,
            therapist,
            room,
            cashier,
            income_source,
            calculate_by_cashier,
        )
        self.tab_income_list = module_utils.get_income_list(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            regist_type,
            therapist,
            room,
            self.tab_income_cash_flow.ui.tableWidget_registration,
            self.tab_income_cash_flow.ui.tableWidget_charge,
            income_source,
            self.income_list_columns,
        )
        self.tab_income_self_prescript = module_utils.get_income_self_prescript(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            regist_type,
            therapist,
            room,
            cashier,
            income_source,
        )
        self.tab_income_project = module_utils.get_income_project(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            regist_type,
            therapist,
            room,
            cashier,
            income_source,
        )
        self.tab_income_ins_list = module_utils.get_income_ins_list(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            regist_type,
            therapist,
            room,
            cashier,
            income_source,
        )

        self._check_unpaid_record(
            start_date, end_date, period, therapist, room, cashier, regist_type
        )

        self.ui.tabWidget_income.clear()
        self.ui.tabWidget_income.addTab(self.tab_income_list, "交帳明細一覽")
        self.ui.tabWidget_income.addTab(self.tab_income_cash_flow, "現金收入分析")
        self.ui.tabWidget_income.addTab(self.tab_income_ins_list, "健保收費明細")
        self.ui.tabWidget_income.addTab(self.tab_income_self_prescript, "自費明細表")
        self.ui.tabWidget_income.addTab(self.tab_income_project, "專案銷售明細表")

        self.income_date = start_date[:10]
        self.period = period

        self.tab_income_cash_flow.label_income_date.setText(self.income_date)
        self.tab_income_cash_flow.label_income_period.setText(self.period)

    def _check_unpaid_cases(
        self, start_date, end_date, period, regist_type, doctor, room, cashier
    ):
        if self.system_settings.field("櫃台結帳班別") == "掛號班別":
            return False

        sql = f'''
            SELECT
                Name, Period
            FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                DoctorDone = "True" AND
                (ChargeDone = "False" OR
                 ChargeDate IS NULL OR ChargePeriod IS NULL)
        '''
        if period != "全部":
            sql += f' AND Period = "{period}"'
        if doctor != "全部":
            sql += f' AND Doctor = "{doctor}"'
        if room != "全部":
            sql += f" AND Room = {room}"
        if cashier != "全部":
            sql += f' AND Cashier = "{cashier}"'
        if regist_type != "全部":
            sql += f' AND RegistType = "{regist_type}"'

        rows = self.database.select_record(sql)
        if len(rows) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "尚有未批價名單",
                '<font color="red"><h3>尚有未批價名單, 請至病歷查詢檢視並批價!</h3></font>',
                "請確認所有病歷均已完成批價.",
            )
            return True

        return False

    def _check_unpaid_record(
        self, start_date, end_date, period, doctor, room, cashier, regist_type
    ):
        sql = """
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN %s AND %s AND
                DoctorDone = "True" AND
                ChargeDone = "False"
        """
        params = [start_date, end_date]

        filters = [
            ("Period", period),
            ("Doctor", doctor),
            ("Room", room),
            ("Cashier", cashier),
            ("RegistType", regist_type),
        ]
        for column, value in filters:
            if value != "全部":
                sql += f" AND {column} = %s"
                params.append(value)

        rows = self.database.select_record(sql, params)
        if len(rows) > 0:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "批價檢查",
                '<font size="5" color="red"><b>今日門診資料尚有未批價名單, 請檢查是否已經全部批價.</b></font>',
                "請確定所有病歷均已批價, 否則櫃台結帳會無法統計尚未批價的資料.",
            )

    def _print_income(self, orientation, print_type=None):
        printer_utils.print_income(
            self,
            self.database,
            self.system_settings,
            orientation,
            self.tab_income_cash_flow.label_income_date.text(),
            self.tab_income_cash_flow.label_income_period.text(),
            self.tab_income_list.ui.tableWidget_income,
            self.tab_income_cash_flow.ui.tableWidget_total,
            self.income_list_columns,
            print_type,
        )

    def _print_income2(self, orientation, print_type=None):
        printer_utils.print_income2(
            self,
            self.database,
            self.system_settings,
            orientation,
            self.tab_income_cash_flow,
            self.tab_income_list,
            self.income_list_columns,
            print_type,
        )

    def _export_daily_excel(self):
        if self.ui.tabWidget_income.currentIndex() == 0:
            self.tab_income_list.export_to_excel()
        elif self.ui.tabWidget_income.currentIndex() == 3:
            self.tab_income_self_prescript.export_to_excel()
        elif self.ui.tabWidget_income.currentIndex() == 4:
            self.tab_income_project.export_to_excel()

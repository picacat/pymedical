# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    export_utils,
    nhi_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 醫師統計 2019.05.02
class StatisticsDoctorCount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorCount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
        self.option = args[7]
        self.weekday_list = args[8]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.single_self_case = self.system_settings.field("同自費只算一筆")

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_COUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_count = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_count, self.database
        )
        self.table_widget_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_doctor, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            130,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            85,
            100,
        ]
        self.table_widget_doctor_count.set_table_heading_width(width)
        self.table_widget_doctor.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_date_excel.clicked.connect(self._export_to_date_excel)
        self.ui.toolButton_export_doctor_excel.clicked.connect(
            self._export_to_doctor_excel
        )
        self.ui.toolButton_export_doctor_care_excel.clicked.connect(
            self._export_to_doctor_care_excel
        )

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_count.setRowCount(0)
        self.ui.tableWidget_doctor.setRowCount(0)
        self._set_statistics_table_heading()
        self._set_statistics_doctor_table_heading()
        self._calculate_data()

    def _set_statistics_table_heading(self):
        start_date = datetime.datetime.strptime(
            self.start_date, "%Y-%m-%d %H:%M:%S"
        ).date()
        end_date = datetime.datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S").date()
        day_count = (end_date - start_date).days + 1

        calendar_list = []
        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            case_date = date.strftime("%Y-%m-%d")
            if case_date not in calendar_list:
                calendar_list.append(case_date)

        row_count = len(calendar_list)
        self.ui.tableWidget_doctor_count.setRowCount(row_count + 1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_doctor_count.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date)
            )

        self.ui.tableWidget_doctor_count.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )

    @staticmethod
    def _get_doctor(doctor, treat_type):
        if doctor in ["", None]:
            if treat_type == "自購":
                doctor = treat_type
            else:
                doctor = "空白"

        return doctor

    def _set_statistics_doctor_table_heading(self):
        doctor_list = []
        rows = self._read_data(group_by_doctor=True)

        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            if doctor not in doctor_list:
                doctor_list.append(doctor)

        row_count = len(doctor_list)
        self.ui.tableWidget_doctor.setRowCount(row_count + 1)
        self.ui.tableWidget_doctor_care.setRowCount(row_count + 1)

        for row_no, doctor in enumerate(doctor_list):
            self.ui.tableWidget_doctor.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(doctor)
            )
            self.ui.tableWidget_doctor_care.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(doctor)
            )

        self.ui.tableWidget_doctor.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )
        self.ui.tableWidget_doctor_care.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )

    def _calculate_data(self):
        self._reset_data(self.ui.tableWidget_doctor_count)
        self._reset_data(self.ui.tableWidget_doctor)
        self._reset_data(self.ui.tableWidget_doctor_care)

        rows = self._read_data()
        self._calculate_ins_count(rows)
        self._calculate_doctor_ins_count(rows)

        self._calculate_visit(rows)
        self._calculate_doctor_visit(rows)

        self._calculate_designated(rows)
        self._calculate_doctor_designated(rows)

        self._calculate_period(rows)
        self._calculate_doctor_period(rows)

        self._calculate_treat_count(rows)
        self._calculate_doctor_treat_count(rows)

        self._calculate_pres_days(rows)
        self._calculate_doctor_pres_days(rows)

        self._calculate_integrate_care(rows)
        self._calculate_doctor_integrate_care(rows)

        self._calculate_subtotal()
        self._calculate_doctor_subtotal()

        self._calculate_acupuncture_total(rows)
        self._calculate_doctor_acupuncture_total(rows)

        self._calculate_massage_total(rows)
        self._calculate_doctor_massage_total(rows)

        self._calculate_doctor_care(rows)

        self._calculate_total()
        self._calculate_doctor_total()

        self._plot_chart()

    def _reset_data(self, in_table_widget_doctor):
        for row_no in range(in_table_widget_doctor.rowCount()):
            for col_no in range(1, in_table_widget_doctor.columnCount()):
                in_table_widget_doctor.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("0")
                )
                in_table_widget_doctor.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self, group_by_doctor=False):
        period_condition = ""
        if self.period != "全部":
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ""
        if self.ins_type != "全部":
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = ' AND Doctor = "{0}"'.format(self.doctor)

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(CaseDate) IN({','.join(self.weekday_list)})"
            )

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        group_condition = ""
        if group_by_doctor:
            group_condition = " GROUP BY Doctor, TreatType"

        treat_type_condition = ""
        if self.single_self_case == "Y":
            treat_type_condition = ' AND TreatType NOT IN ("自購", "開立證明") '

        sql = f'''
            SELECT
                CaseKey, PatientKey, CaseDate, Visit, Period, InsType,
                TreatType, Treatment, Continuance, Doctor,
                DesignatedDoctor
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0
                {treat_type_condition}
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            {group_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            case_date_field = self.ui.tableWidget_doctor_count.item(row_no, 0)
            if case_date == case_date_field.text():
                return row_no

        return None

    def _get_doctor_row_no(self, doctor, in_table_widget):
        for row_no in range(in_table_widget.rowCount()):
            doctor_field = in_table_widget.item(row_no, 0)
            if doctor_field is None:
                continue

            if doctor == doctor_field.text():
                return row_no

        return None

    def _calculate_ins_count(self, rows):
        self_patient_list = {}

        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)
            ins_type = string_utils.xstr(row["InsType"])
            patient_key = row["PatientKey"]

            if ins_type == "健保":
                col_no = 1
            else:
                if self.single_self_case == "Y":
                    if case_utils.is_duplicate_ins_patient(self.database, row):
                        continue

                    try:
                        if patient_key in self_patient_list[case_date]:
                            continue
                    except Exception:
                        self_patient_list[case_date] = []

                    self_patient_list[case_date].append(patient_key)

                col_no = 2

            ins_count = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if ins_count is None:
                ins_count = 0
            else:
                ins_count = number_utils.get_integer(ins_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(ins_count + 1),
            )

    def _calculate_doctor_ins_count(self, rows):
        self_patient_list = {}

        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            ins_type = string_utils.xstr(row["InsType"])
            patient_key = row["PatientKey"]

            if ins_type == "健保":
                col_no = 1
            else:
                if self.single_self_case == "Y":
                    if case_utils.is_duplicate_ins_patient(self.database, row):
                        continue

                    try:
                        if patient_key in self_patient_list[case_date]:
                            continue
                    except Exception:
                        self_patient_list[case_date] = []

                    self_patient_list[case_date].append(patient_key)

                col_no = 2

            ins_count = self.ui.tableWidget_doctor.item(row_no, col_no)

            if ins_count is None:
                ins_count = 0
            else:
                ins_count = number_utils.get_integer(ins_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor,
                row_no,
                col_no,
                string_utils.xstr(ins_count + 1),
            )

    def _calculate_visit(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)
            ins_type = string_utils.xstr(row["InsType"])
            if ins_type != "健保":
                continue

            visit = string_utils.xstr(row["Visit"])
            if visit == "初診":
                col_no = 3
            else:
                col_no = 4

            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count + 1),
            )

    def _calculate_doctor_visit(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            ins_type = string_utils.xstr(row["InsType"])
            if ins_type != "健保":
                continue

            visit = string_utils.xstr(row["Visit"])
            if visit == "初診":
                col_no = 3
            else:
                col_no = 4

            item = self.ui.tableWidget_doctor.item(row_no, col_no)

            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count + 1)
            )

    def _calculate_designated(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)
            ins_type = string_utils.xstr(row["InsType"])
            visit = string_utils.xstr(row["Visit"])
            if ins_type != "健保" or visit != "初診":
                continue

            designated = string_utils.xstr(row["DesignatedDoctor"])
            if designated == "True":
                col_no = 5
            else:
                col_no = 6

            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count + 1),
            )

    def _calculate_doctor_designated(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            ins_type = string_utils.xstr(row["InsType"])
            visit = string_utils.xstr(row["Visit"])
            if ins_type != "健保" or visit != "初診":
                continue

            designated = string_utils.xstr(row["DesignatedDoctor"])
            if designated == "True":
                col_no = 5
            else:
                col_no = 6

            item = self.ui.tableWidget_doctor.item(row_no, col_no)

            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count + 1)
            )

    def _calculate_period(self, rows):
        self_patient_list = {}

        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            period = string_utils.xstr(row["Period"])
            ins_type = string_utils.xstr(row["InsType"])
            patient_key = row["PatientKey"]

            if ins_type == "自費" and self.single_self_case == "Y":
                if case_utils.is_duplicate_ins_patient(self.database, row):
                    continue

                try:
                    if patient_key in self_patient_list[case_date]:
                        continue
                except Exception:
                    self_patient_list[case_date] = []

                self_patient_list[case_date].append(patient_key)

            col_no = 7
            if period == "早班":
                col_no = 7
            elif period == "午班":
                col_no = 8
            elif period == "晚班":
                col_no = 9

            row_no = self._get_row_no(case_date)
            period_count = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if period_count is None:
                period_count = 0
            else:
                period_count = number_utils.get_integer(period_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(period_count + 1),
            )

    def _calculate_doctor_period(self, rows):
        self_patient_list = {}

        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            period = string_utils.xstr(row["Period"])
            ins_type = string_utils.xstr(row["InsType"])
            patient_key = row["PatientKey"]

            if ins_type == "自費" and self.single_self_case == "Y":
                if case_utils.is_duplicate_ins_patient(self.database, row):
                    continue

                try:
                    if patient_key in self_patient_list[case_date]:
                        continue
                except Exception:
                    self_patient_list[case_date] = []

                self_patient_list[case_date].append(patient_key)

            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            col_no = 7
            if period == "早班":
                col_no = 7
            elif period == "午班":
                col_no = 8
            elif period == "晚班":
                col_no = 9

            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            period_count = self.ui.tableWidget_doctor.item(row_no, col_no)
            if period_count is None:
                period_count = 0
            else:
                period_count = number_utils.get_integer(period_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor,
                row_no,
                col_no,
                string_utils.xstr(period_count + 1),
            )

    def _get_col_no(self, treatment, pres_days, course):
        col_no = 10  # 內科

        if treatment in nhi_utils.MERGE_TREAT_LIST:
            if pres_days <= 0:
                col_no = 31
            else:
                col_no = 32
        elif treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT:
            if pres_days <= 0:
                if course <= 1:
                    col_no = 11
                else:
                    col_no = 12
            else:
                col_no = 14
        elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
            if pres_days <= 0:
                if course <= 1:
                    col_no = 15
                else:
                    col_no = 16
            else:
                col_no = 18
        elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
            if pres_days <= 0:
                if course <= 1:
                    col_no = 19
                else:
                    col_no = 20
            else:
                col_no = 22
        elif treatment in nhi_utils.GENERAL_MASSAGE_TREAT:
            if pres_days <= 0:
                if course <= 1:
                    col_no = 23
                else:
                    col_no = 24
            else:
                col_no = 26
        elif treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
            if pres_days <= 0:
                col_no = 27
            else:
                col_no = 30
        elif (
            treatment
            in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT + nhi_utils.DISLOCATE_TREAT
        ):
            if pres_days <= 0:
                col_no = 29
            else:
                col_no = 30

        return col_no

    def _calculate_treat_count(self, rows):
        for row in rows:
            ins_type = string_utils.xstr(row["InsType"])
            if ins_type != "健保":
                continue

            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            treatment = string_utils.xstr(row["Treatment"])
            course = number_utils.get_integer(row["Continuance"])
            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])

            row_no = self._get_row_no(case_date)
            col_no = self._get_col_no(treatment, pres_days, course)

            treat_count = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if treat_count is None:
                treat_count = 0
            else:
                treat_count = number_utils.get_integer(treat_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(treat_count + 1),
            )

    def _calculate_doctor_treat_count(self, rows):
        for row in rows:
            ins_type = string_utils.xstr(row["InsType"])
            if ins_type != "健保":
                continue

            treat_type = string_utils.xstr(row["TreatType"])
            treatment = string_utils.xstr(row["Treatment"])
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                treat_type,
            )
            course = number_utils.get_integer(row["Continuance"])
            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])

            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            col_no = self._get_col_no(treatment, pres_days, course)

            treat_count = self.ui.tableWidget_doctor.item(row_no, col_no)
            if treat_count is None:
                treat_count = 0
            else:
                treat_count = number_utils.get_integer(treat_count.text())

            self._set_item_data(
                self.ui.tableWidget_doctor,
                row_no,
                col_no,
                string_utils.xstr(treat_count + 1),
            )

    def _calculate_pres_days(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)
            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])
            course = number_utils.get_integer(row["Continuance"])

            col_no = 33
            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            count += pres_days
            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

            col_no = 34
            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if pres_days >= 14:
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

            col_no = 35
            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if course >= 1 and pres_days >= 8:
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

    def _calculate_doctor_pres_days(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])
            course = number_utils.get_integer(row["Continuance"])

            col_no = 33
            item = self.ui.tableWidget_doctor.item(row_no, col_no)

            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            count += pres_days

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

            col_no = 34
            item = self.ui.tableWidget_doctor.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if pres_days >= 14:
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

            col_no = 35
            item = self.ui.tableWidget_doctor.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if course >= 1 and pres_days >= 8:
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

    def _calculate_integrate_care(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            case_key = row["CaseKey"]
            row_no = self._get_row_no(case_date)

            col_no = 36
            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if (
                case_utils.get_case_extend(self.database, case_key, "整合醫療照護")
                == "Y"
            ):
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

    def _calculate_doctor_integrate_care(self, rows):
        col_no = 36
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            case_key = row["CaseKey"]
            item = self.ui.tableWidget_doctor.item(row_no, col_no)
            if item is None:
                count = 0
            else:
                count = number_utils.get_integer(item.text())

            if (
                case_utils.get_case_extend(self.database, case_key, "整合醫療照護")
                == "Y"
            ):
                count += 1

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

    def _set_item_data(self, tableWidget, row_no, col_no, data):
        tableWidget.setItem(row_no, col_no, QtWidgets.QTableWidgetItem(data))
        item = tableWidget.item(row_no, col_no)
        item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _calculate_subtotal(self):
        self._calculate_table_widget_subtotal(self.tableWidget_doctor_count)

    def _calculate_doctor_subtotal(self):
        self._calculate_table_widget_subtotal(self.tableWidget_doctor)

    def _calculate_table_widget_subtotal(self, tableWidget):
        for row_no in range(tableWidget.rowCount()):
            acupuncture1 = number_utils.get_integer(tableWidget.item(row_no, 11).text())
            acupuncture2 = number_utils.get_integer(tableWidget.item(row_no, 12).text())
            self._set_item_data(
                tableWidget, row_no, 13, string_utils.xstr(acupuncture1 + acupuncture2)
            )

            m_acupuncture1 = number_utils.get_integer(
                tableWidget.item(row_no, 15).text()
            )
            m_acupuncture2 = number_utils.get_integer(
                tableWidget.item(row_no, 16).text()
            )
            self._set_item_data(
                tableWidget,
                row_no,
                17,
                string_utils.xstr(m_acupuncture1 + m_acupuncture2),
            )

            h_acupuncture1 = number_utils.get_integer(
                tableWidget.item(row_no, 19).text()
            )
            h_acupuncture2 = number_utils.get_integer(
                tableWidget.item(row_no, 20).text()
            )
            self._set_item_data(
                tableWidget,
                row_no,
                21,
                string_utils.xstr(h_acupuncture1 + h_acupuncture2),
            )

            massage1 = number_utils.get_integer(tableWidget.item(row_no, 23).text())
            massage2 = number_utils.get_integer(tableWidget.item(row_no, 24).text())
            self._set_item_data(
                tableWidget, row_no, 25, string_utils.xstr(massage1 + massage2)
            )

    def _calculate_total(self):
        self.ui._calculate_table_widget_total(self.ui.tableWidget_doctor_count)

    def _calculate_doctor_total(self):
        self.ui._calculate_table_widget_total(self.ui.tableWidget_doctor)

    def _calculate_table_widget_total(self, tableWidget):
        total_list = [0 for i in range(tableWidget.columnCount())]
        for row_no in range(tableWidget.rowCount()):
            for col_no in range(1, tableWidget.columnCount()):
                value = number_utils.get_integer(
                    tableWidget.item(row_no, col_no).text()
                )
                total_list[col_no] += value

        row_no = tableWidget.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_item_data(
                tableWidget, row_no, col_no, string_utils.xstr(total_list[col_no])
            )

    def _export_to_date_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}醫師門診人次統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_count,
            None,
            [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
            ],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>醫師人次統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}個別醫師門診人次統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor,
            None,
            [
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                21,
                22,
                23,
                24,
                25,
                26,
            ],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>個別醫師人次統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def _export_to_doctor_care_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}個別醫師門診人次居家醫療統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_care,
            None,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>個別醫師人次統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_outpatient_count_chart()
        self._plot_visit_chart()

    def _plot_outpatient_count_chart(self):
        series = QtChart.QBarSeries()

        treat_type = ["內科", "針灸", "中針", "高針", "傷科", "中傷", "高傷"]
        col_no_list = [10, 13, 17, 21, 25, 27, 29]

        set_list = []
        for i in range(len(treat_type)):
            set_list.append(QtChart.QBarSet(treat_type[i]))
            set_list[i] << number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(
                    self.ui.tableWidget_doctor_count.rowCount() - 1, col_no_list[i]
                ).text()
            )
            series.append(set_list[i])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("門診人數統計表")
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ["門診人數"]

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(500)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_visit_chart(self):
        series = QtChart.QPieSeries()

        row_no = self.ui.tableWidget_doctor_count.rowCount() - 1
        first_visit = number_utils.get_integer(
            self.ui.tableWidget_doctor_count.item(row_no, 3).text()
        )
        visit = number_utils.get_integer(
            self.ui.tableWidget_doctor_count.item(row_no, 4).text()
        )
        visit_list = [
            ["初診", first_visit],
            ["複診", visit],
        ]
        for row_no in range(len(visit_list)):
            series.append(visit_list[row_no][0], visit_list[row_no][1])

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("初複診統計表")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(500)
        chartView.setFixedHeight(350)
        self.ui.verticalLayout_chart.addWidget(chartView)

    def _calculate_acupuncture_total(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)

            col_no = 37
            g_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 13).text()
            )
            g_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 14).text()
            )
            m_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 17).text()
            )
            m_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 18).text()
            )
            h_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 21).text()
            )
            h_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 22).text()
            )
            mg_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 31).text()
            )
            mg_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 32).text()
            )

            count = (
                g_acupuncture
                + g_acupuncture_med
                + m_acupuncture
                + m_acupuncture_med
                + h_acupuncture
                + h_acupuncture_med
                + mg_acupuncture
                + mg_acupuncture_med
            )

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

    def _calculate_doctor_acupuncture_total(self, rows):
        col_no = 37
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            g_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 13).text()
            )
            g_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 14).text()
            )
            m_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 17).text()
            )
            m_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 18).text()
            )
            h_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 21).text()
            )
            h_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 22).text()
            )
            mg_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 31).text()
            )
            mg_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 32).text()
            )

            count = (
                g_acupuncture
                + g_acupuncture_med
                + m_acupuncture
                + m_acupuncture_med
                + h_acupuncture
                + h_acupuncture_med
                + mg_acupuncture
                + mg_acupuncture_med
            )

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

    def _calculate_massage_total(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)

            col_no = 38
            g_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 25).text()
            )
            g_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 26).text()
            )
            m_massage = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 27).text()
            )
            m_massage_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 28).text()
            )
            h_massage = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 29).text()
            )
            h_massage_med = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, 30).text()
            )

            count = (
                g_acupuncture
                + g_acupuncture_med
                + m_massage
                + m_massage_med
                + h_massage
                + h_massage_med
            )

            self._set_item_data(
                self.ui.tableWidget_doctor_count,
                row_no,
                col_no,
                string_utils.xstr(count),
            )

    def _calculate_doctor_massage_total(self, rows):
        col_no = 38
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor)
            if row_no is None:
                continue

            g_acupuncture = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 25).text()
            )
            g_acupuncture_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 26).text()
            )
            m_massage = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 27).text()
            )
            m_massage_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 28).text()
            )
            h_massage = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 29).text()
            )
            h_massage_med = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 30).text()
            )

            count = (
                g_acupuncture
                + g_acupuncture_med
                + m_massage
                + m_massage_med
                + h_massage
                + h_massage_med
            )

            self._set_item_data(
                self.ui.tableWidget_doctor, row_no, col_no, string_utils.xstr(count)
            )

    def _calculate_doctor_care(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )
            row_no = self._get_doctor_row_no(doctor, self.ui.tableWidget_doctor_care)
            if row_no is None:
                continue

            ins_type = string_utils.xstr(row["InsType"])
            if ins_type != "健保":
                continue

            treat_type = string_utils.xstr(row["TreatType"])
            treatment = string_utils.xstr(row["Treatment"])

            self._set_doctor_care_count(row_no, 1)  # 健保人數

            if treat_type == "居家醫療":
                if treatment in nhi_utils.MERGE_TREAT_LIST:
                    col_no = 17
                elif treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT:
                    col_no = 11
                elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                    col_no = 12
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                    col_no = 13
                elif treatment in nhi_utils.GENERAL_MASSAGE_TREAT:
                    col_no = 14
                elif treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                    col_no = 15
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                    col_no = 16
                else:
                    col_no = 10
            else:
                if treatment in nhi_utils.MERGE_TREAT_LIST:
                    col_no = 9
                elif treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT:
                    col_no = 3
                elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                    col_no = 4
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                    col_no = 5
                elif treatment in nhi_utils.GENERAL_MASSAGE_TREAT:
                    col_no = 6
                elif treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                    col_no = 7
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                    col_no = 8
                else:
                    col_no = 2

            self._set_doctor_care_count(row_no, col_no)

            case_key = string_utils.xstr(row["CaseKey"])
            if (
                case_utils.get_case_extend(self.database, case_key, "整合醫療照護")
                == "Y"
            ):
                self._set_doctor_care_count(row_no, 12)

        self.ui._calculate_table_widget_total(self.ui.tableWidget_doctor_care)

    def _set_doctor_care_count(self, row_no, col_no):
        count = self.ui.tableWidget_doctor_care.item(row_no, col_no)
        if count is None:
            count = 0
        else:
            count = number_utils.get_integer(count.text())

        self._set_item_data(
            self.ui.tableWidget_doctor_care,
            row_no,
            col_no,
            string_utils.xstr(count + 1),
        )

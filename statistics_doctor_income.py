# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    case_utils,
    class_utils,
    export_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 醫師門診收入統計 2019.05.10
class StatisticsDoctorIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorIncome, self).__init__(parent)
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

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_income = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_income, self.database
        )
        self.table_widget_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_doctor, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            130,
            80,
            80,
            80,
            80,
            80,
            80,
            80,
            90,
            90,
        ]
        self.table_widget_doctor_income.set_table_heading_width(width)
        self.table_widget_doctor.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_date_excel.clicked.connect(self._export_to_date_excel)
        self.ui.toolButton_export_doctor_excel.clicked.connect(
            self._export_to_doctor_excel
        )

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_income.setRowCount(0)
        self.ui.tableWidget_doctor.setRowCount(0)
        self._set_statistics_table_heading()
        self._set_statistics_doctor_table_heading()
        self._calculate_data()

    @staticmethod
    def _get_doctor(doctor, treat_type):
        if doctor in ["", None]:
            if treat_type == "自購":
                doctor = treat_type
            else:
                doctor = "空白"

        return doctor

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
        self.ui.tableWidget_doctor_income.setRowCount(row_count + 1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_doctor_income.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date)
            )

        self.ui.tableWidget_doctor_income.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )

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

        for row_no, doctor in enumerate(doctor_list):
            self.ui.tableWidget_doctor.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(doctor)
            )

        self.ui.tableWidget_doctor.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem("總計")
        )

    def _calculate_data(self):
        self._reset_data()
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            "門診收入統計中, 請稍後...", "取消", 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self._calculate_income(rows)
        self._calculate_doctor_income(rows)

        self._calculate_refund()
        self._calculate_doctor_refund()

        self._calculate_debt()
        self._calculate_doctor_debt()

        self._calculate_repayment()
        self._calculate_doctor_repayment()

        if self.doctor == "全部":
            self.return_goods_dict = (
                self._read_return_goods_dict()
            )  # 一次撈完, 兩張表共用
            self._calculate_return_goods()
            self._calculate_doctor_return_goods()  # 新增, 一定要在 doctor_subtotal 之前

        self._calculate_subtotal()
        self._calculate_doctor_subtotal()

        self._calculate_total()
        self._calculate_doctor_total()

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

        self._plot_chart()

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor_income.columnCount()):
                self.ui.tableWidget_doctor_income.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("0")
                )
                self.ui.tableWidget_doctor_income.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                self.ui.tableWidget_doctor.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("0")
                )
                self.ui.tableWidget_doctor.item(row_no, col_no).setTextAlignment(
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
            doctor_condition = (
                f' AND (cases.Doctor = "{self.doctor}" and cases.TreatType != "自購")'
            )

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(CaseDate) IN({','.join(self.weekday_list)})"
            )

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        group_condition = ""
        if group_by_doctor:
            group_condition = " GROUP BY Doctor, TreatType"

        sql = f"""
            SELECT
                CaseKey, Name, CaseDate, TreatType, Doctor,
                RegistFee, SDiagShareFee, SDrugShareFee, DepositFee, TotalFee
            FROM cases
            WHERE
                CaseDate BETWEEN %s AND %s
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            {group_condition}
            ORDER BY CaseDate
        """
        params = (self.start_date, self.end_date)
        rows = self.database.select_record(sql, params)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            case_date_field = self.ui.tableWidget_doctor_income.item(row_no, 0)

            if case_date == case_date_field.text():
                return row_no

        return None

    def _calculate_income(self, rows):
        for row in rows:
            case_date = row["CaseDate"].strftime("%Y-%m-%d")
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            self.progress_dialog.setValue(row_no)
            regist_fee = self._get_cell_fee(row_no, 1) + number_utils.get_integer(
                row["RegistFee"]
            )
            diag_share_fee = self._get_cell_fee(row_no, 2) + number_utils.get_integer(
                row["SDiagShareFee"]
            )
            drug_share_fee = self._get_cell_fee(row_no, 3) + number_utils.get_integer(
                row["SDrugShareFee"]
            )
            deposit_fee = self._get_cell_fee(row_no, 4) + number_utils.get_integer(
                row["DepositFee"]
            )
            total_fee = self._get_cell_fee(row_no, 8) + number_utils.get_integer(
                row["TotalFee"]
            )

            self._set_item_data(row_no, 1, string_utils.xstr(regist_fee))
            self._set_item_data(row_no, 2, string_utils.xstr(diag_share_fee))
            self._set_item_data(row_no, 3, string_utils.xstr(drug_share_fee))
            self._set_item_data(row_no, 4, string_utils.xstr(deposit_fee))
            self._set_item_data(row_no, 8, string_utils.xstr(total_fee))

    def _calculate_doctor_income(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row["Doctor"]),
                string_utils.xstr(row["TreatType"]),
            )

            row_no = self._get_doctor_row_no(doctor)

            regist_fee = self._get_doctor_cell_fee(
                row_no, 1
            ) + number_utils.get_integer(row["RegistFee"])
            diag_share_fee = self._get_doctor_cell_fee(
                row_no, 2
            ) + number_utils.get_integer(row["SDiagShareFee"])
            drug_share_fee = self._get_doctor_cell_fee(
                row_no, 3
            ) + number_utils.get_integer(row["SDrugShareFee"])
            deposit_fee = self._get_doctor_cell_fee(
                row_no, 4
            ) + number_utils.get_integer(row["DepositFee"])
            total_fee = self._get_doctor_cell_fee(row_no, 8) + number_utils.get_integer(
                row["TotalFee"]
            )

            self._set_doctor_item_data(row_no, 1, string_utils.xstr(regist_fee))
            self._set_doctor_item_data(row_no, 2, string_utils.xstr(diag_share_fee))
            self._set_doctor_item_data(row_no, 3, string_utils.xstr(drug_share_fee))
            self._set_doctor_item_data(row_no, 4, string_utils.xstr(deposit_fee))
            self._set_doctor_item_data(row_no, 8, string_utils.xstr(total_fee))

    def _get_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_doctor_income.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _get_doctor_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_doctor.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _set_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_doctor_income.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_doctor_income.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_doctor_income.item(row_no, col_no).setForeground(
                QtGui.QColor("red")
            )

    def _set_doctor_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_doctor.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_doctor.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_doctor.item(row_no, col_no).setForeground(
                QtGui.QColor("red")
            )

    def _calculate_refund(self):
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            self.progress_dialog.setValue(row_no)
            case_date = self.ui.tableWidget_doctor_income.item(row_no, 0)
            if case_date is None:
                refund = 0
            else:
                refund = self._get_refund(case_date.text())

            self._set_item_data(row_no, 5, string_utils.xstr(refund))

    def _calculate_doctor_refund(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                refund = 0
            else:
                refund = self._get_doctor_refund(doctor.text())

            self._set_doctor_item_data(row_no, 5, string_utils.xstr(refund))

    def _get_refund(self, return_date):
        start_date = "{0} 00:00:00".format(return_date)
        end_date = "{0} 23:59:59".format(return_date)

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = 'AND cases.Doctor = "{0}"'.format(self.doctor)

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnDate) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee FROM deposit
                LEFT JOIN cases ON deposit.CaseKey = cases.CaseKey
            WHERE
                ReturnDate BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition}
                {doctor_condition}
        '''.format(
            start_date=start_date,
            end_date=end_date,
            doctor_condition=doctor_condition,
        )

        rows = self.database.select_record(sql)

        return_fee = 0
        for row in rows:
            return_fee += number_utils.get_integer(row["Fee"])

        return -return_fee

    def _get_doctor_refund(self, doctor):
        start_date = f"{self.start_date} 00:00:00"
        end_date = f"{self.end_date} 23:59:59"

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnDate) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee FROM deposit
                LEFT JOIN cases ON deposit.CaseKey = cases.CaseKey
            WHERE
                ReturnDate BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition} AND
                cases.Doctor = "{doctor}"
        '''

        rows = self.database.select_record(sql)

        return_fee = 0
        for row in rows:
            return_fee += number_utils.get_integer(row["Fee"])

        return -return_fee

    def _calculate_debt(self):
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            self.progress_dialog.setValue(row_no)
            case_date = self.ui.tableWidget_doctor_income.item(row_no, 0)
            if case_date is None:
                debt = 0
            else:
                debt = self._get_debt(case_date.text())

            self._set_item_data(row_no, 6, string_utils.xstr(debt))

    def _calculate_doctor_debt(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                debt = 0
            else:
                debt = self._get_doctor_debt(doctor.text())

            self._set_doctor_item_data(row_no, 6, string_utils.xstr(debt))

    def _get_debt(self, case_date):
        start_date = "{0} 00:00:00".format(case_date)
        end_date = "{0} 23:59:59".format(case_date)

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(debt.CaseDate) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                debt.CaseDate BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition}
                {doctor_condition}
        '''.format(
            start_date=start_date,
            end_date=end_date,
            doctor_condition=doctor_condition,
        )

        rows = self.database.select_record(sql)

        debt = 0
        for row in rows:
            debt += number_utils.get_integer(row["Fee"])

        return -debt

    def _get_doctor_debt(self, doctor):
        start_date = f"{self.start_date} 00:00:00"
        end_date = f"{self.end_date} 23:59:59"

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(debt.CaseDate) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                debt.CaseDate BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition} AND
                cases.Doctor = "{doctor}"
        '''

        rows = self.database.select_record(sql)

        debt = 0
        for row in rows:
            debt += number_utils.get_integer(row["Fee"])

        return -debt

    def _calculate_repayment(self):
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            self.progress_dialog.setValue(row_no)
            case_date = self.ui.tableWidget_doctor_income.item(row_no, 0)
            if case_date is None:
                repayment = 0
            else:
                repayment = self._get_repayment(case_date.text())

            self._set_item_data(row_no, 7, string_utils.xstr(repayment))

    def _calculate_doctor_repayment(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                repayment = 0
            else:
                repayment = self._get_doctor_repayment(doctor.text())

            self._set_doctor_item_data(row_no, 7, string_utils.xstr(repayment))

    def _get_repayment(self, case_date):
        start_date = "{0} 00:00:00".format(case_date)
        end_date = "{0} 23:59:59".format(case_date)

        doctor_condition = ""
        if self.doctor != "全部":
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnDate1) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee1 FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                ReturnDate1 BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition}
                {doctor_condition}
        '''
        rows = self.database.select_record(sql)

        repayment = 0
        for row in rows:
            repayment += number_utils.get_integer(row["Fee1"])

        return repayment

    def _get_doctor_repayment(self, doctor):
        start_date = f"{self.start_date} 00:00:00"
        end_date = f"{self.end_date} 23:59:59"

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnDate1) IN({','.join(self.weekday_list)})"
            )

        sql = f'''
            SELECT Fee1 FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                ReturnDate1 BETWEEN "{start_date}" AND "{end_date}"
                {weekday_condition} AND
                cases.Doctor = "{doctor}"
        '''

        rows = self.database.select_record(sql)

        repayment = 0
        for row in rows:
            repayment += number_utils.get_integer(row["Fee1"])

        return repayment

    def _calculate_subtotal(self):
        subtotal_field_no = 9

        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            subtotal = 0
            for col_no in range(1, subtotal_field_no):
                subtotal += number_utils.get_integer(
                    self.ui.tableWidget_doctor_income.item(row_no, col_no).text()
                )

            self._set_item_data(row_no, subtotal_field_no, string_utils.xstr(subtotal))

    def _calculate_doctor_subtotal(self):
        subtotal_field_no = 9

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            subtotal = 0
            for col_no in range(1, subtotal_field_no):
                subtotal += number_utils.get_integer(
                    self.ui.tableWidget_doctor.item(row_no, col_no).text()
                )

            self._set_doctor_item_data(
                row_no, subtotal_field_no, string_utils.xstr(subtotal)
            )

    def _read_return_goods_dict(self):
        period_condition = ""
        if self.period != "全部":
            period_condition = f' AND Period = "{self.period}"'

        weekday_condition = ""
        if len(self.weekday_list) > 0:
            weekday_condition = (
                f" AND WEEKDAY(ReturnGoodsDate) IN({','.join(self.weekday_list)})"
            )

        sql = f"""
            SELECT DATE(ReturnGoodsDate) AS ReturnDate, SUM(AMOUNT) AS Fee
            FROM returngoods
            WHERE ReturnGoodsDate BETWEEN %s AND %s
            {period_condition}
            {weekday_condition}
            GROUP BY DATE(ReturnGoodsDate)
        """
        params = (self.start_date, self.end_date)
        rows = self.database.select_record(sql, params)

        return_goods_dict = {}
        for row in rows:
            fee = number_utils.get_integer(row["Fee"])
            if fee == 0:
                continue

            return_goods_dict[row["ReturnDate"].strftime("%Y-%m-%d")] = fee

        return return_goods_dict

    def _calculate_return_goods(self):
        col_no = self.ui.tableWidget_doctor_income.columnCount() - 2

        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            case_date = self.ui.tableWidget_doctor_income.item(row_no, 0).text()
            if case_date == "總計":
                break

            return_goods_fee = self.return_goods_dict.get(case_date, 0)
            if return_goods_fee == 0:
                continue

            total_fee = number_utils.get_integer(
                self.ui.tableWidget_doctor_income.item(row_no, col_no).text()
            )
            total_fee -= return_goods_fee
            self._set_item_data(row_no, col_no, string_utils.xstr(total_fee))

    def _calculate_doctor_return_goods(self):
        # returngoods 無醫師欄位, 退貨獨立一列, 不歸在任何醫師身上
        return_goods_fee = sum(self.return_goods_dict.values())
        if return_goods_fee == 0:
            return

        row_no = self.ui.tableWidget_doctor.rowCount() - 1  # 插在總計列之前
        self.ui.tableWidget_doctor.insertRow(row_no)

        self.ui.tableWidget_doctor.setItem(
            row_no, 0, QtWidgets.QTableWidgetItem("退貨")
        )
        for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
            self._set_doctor_item_data(row_no, col_no, "0")

        col_no = self.ui.tableWidget_doctor.columnCount() - 2
        self._set_doctor_item_data(row_no, col_no, string_utils.xstr(-return_goods_fee))

    def _calculate_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_doctor_income.columnCount())]
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor_income.columnCount()):
                value = number_utils.get_integer(
                    self.ui.tableWidget_doctor_income.item(row_no, col_no).text()
                )
                total_list[col_no] += value

        row_no = self.ui.tableWidget_doctor_income.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_item_data(row_no, col_no, string_utils.xstr(total_list[col_no]))

    def _calculate_doctor_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_doctor.columnCount())]
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                value = number_utils.get_integer(
                    self.ui.tableWidget_doctor.item(row_no, col_no).text()
                )
                total_list[col_no] += value

        row_no = self.ui.tableWidget_doctor.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_doctor_item_data(
                row_no, col_no, string_utils.xstr(total_list[col_no])
            )

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}醫師門診收入統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_income,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>醫師收入統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(1)
            if item is None:
                break

            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_income_chart()
        self._plot_doctor_income_chart()

    def _plot_income_chart(self):
        case_date_list = []
        for row_no in range(self.ui.tableWidget_doctor_income.rowCount()):
            case_date_field = self.ui.tableWidget_doctor_income.item(row_no, 0)
            if case_date_field is None:
                continue

            case_date = case_date_field.text()
            if case_date == "總計":
                continue

            case_date_list.append(case_date)

        series = QtChart.QBarSeries()
        bar_set = []
        for i in range(len(case_date_list)):
            case_date = case_date_list[i]
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            subtotal = number_utils.get_integer(
                self.ui.tableWidget_doctor_income.item(row_no, 9).text()
            )
            bar_set.append(QtChart.QBarSet(case_date_list[i][8:10]))
            bar_set[i].setColor(QtGui.QColor("green"))
            bar_set[i] << subtotal
            series.append([bar_set[i]])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("門診收入統計表")
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ["門診收入"]

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        # chart.legend().setVisible(True)
        # chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(750)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_doctor_income_chart(self):
        series = QtChart.QPieSeries()

        for row_no in range(self.ui.tableWidget_doctor.rowCount() - 1):
            doctor_item = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor_item is None:
                continue

            doctor_name = doctor_item.text()
            if doctor_name == "退貨":
                continue

            total_fee = number_utils.get_integer(
                self.ui.tableWidget_doctor.item(row_no, 9).text()
            )
            series.append(doctor_name, total_fee)

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle("醫師收入統計表")
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(750)
        chartView.setFixedHeight(450)
        self.ui.verticalLayout_chart.addWidget(chartView)

    def _get_doctor_row_no(self, doctor):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor_field = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor_field is None:
                doctor = "空白"

            if doctor == doctor_field.text():
                return row_no

        return None

    def _export_to_date_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}醫師門診收入統計表.xlsx".format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name,
            self.ui.tableWidget_doctor_income,
            None,
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>醫師收入統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "{0}至{1}{2}個別醫師門診收入統計表.xlsx".format(
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
            [1, 2, 3, 4, 5, 6, 7, 8, 9],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            "<h3>個別醫師收入統計檔{0}匯出完成.</h3>".format(excel_file_name),
            "Microsoft Excel 格式.",
        )

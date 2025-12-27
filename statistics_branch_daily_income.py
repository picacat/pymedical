
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils


# 分院日報表金額統計 2022.01.20
class StatisticsBranchDailyIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsBranchDailyIncome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.database_list = args[2]
        self.year = args[3]
        self.month = args[4]
        self.day = args[5]
        self.ui = None

        self.start_date = f'{self.year}-{self.month}-{self.day} 00:00:00'
        self.end_date = f'{self.year}-{self.month}-{self.day} 23:59:59'
        self.period_list = ['早班', '午班', '晚班']

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_BRANCH_DAILY_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_regist_fee = class_utils.get_table_widget(
            self.ui.tableWidget_regist_fee, self.database
        )
        self.table_widget_diag_share_fee = class_utils.get_table_widget(
            self.ui.tableWidget_diag_share_fee, self.database
        )
        self.table_widget_drug_share_fee = class_utils.get_table_widget(
            self.ui.tableWidget_drug_share_fee, self.database
        )
        self.table_widget_self_total_fee = class_utils.get_table_widget(
            self.ui.tableWidget_self_total_fee, self.database
        )
        self.table_widget_project = class_utils.get_table_widget(
            self.ui.tableWidget_project, self.database
        )
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [280, 90, 90, 90, 90]
        self.table_widget_project.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self._calculate_regist_fee()
        self._calculate_diag_share_fee()
        self._calculate_drug_share_fee()
        self._calculate_self_total_fee()
        self._calculate_project_fee()

        self._calculate_total_income()

    def _calculate_regist_fee(self):
        self.ui.tableWidget_regist_fee.clear()

        col_data_list = ['金額', '欠還卡', '自費掛號']
        col_data_length = len(col_data_list)

        clinic_count = len(self.database_list)

        self.ui.tableWidget_regist_fee.setColumnCount(clinic_count * col_data_length + 3)
        self.ui.tableWidget_regist_fee.setRowCount(6)

        self._set_table_item(self.ui.tableWidget_regist_fee, 0, 0, 'A.掛號收入')
        self.ui.tableWidget_regist_fee.setSpan(0, 0, 6, 1)

        self._set_table_item(self.ui.tableWidget_regist_fee, 0, 1, '班別/診所')
        self.ui.tableWidget_regist_fee.setSpan(0, 1, 2, 1)

        self._set_table_item(
            self.ui.tableWidget_regist_fee,
            0, self.ui.tableWidget_regist_fee.columnCount()-1, '總計')
        self.ui.tableWidget_regist_fee.setSpan(
            0, self.ui.tableWidget_regist_fee.columnCount()-1, 2, 1)

        for i, clinic_name in enumerate(self.database_list):
            database = self.database_list[clinic_name]['database']
            rows = self._get_rows(database)

            col_no = col_data_length * i + 2
            self._set_table_item(self.ui.tableWidget_regist_fee, 0, col_no, clinic_name)
            self.ui.tableWidget_regist_fee.setSpan(0, col_no, 1, col_data_length)

            for j, col_data in enumerate(col_data_list):
                self._set_table_item(self.ui.tableWidget_regist_fee, 1, col_no+j, col_data)

            total_regist_fee, total_deposit_fee, total_self_regist_fee = 0, 0, 0
            start_row_no = 2
            for row_no in range(start_row_no, start_row_no + len(self.period_list)):
                period = self.period_list[row_no - start_row_no]
                ins_regist_fee, self_regist_fee, deposit_fee = self._calculate_total_regist_fee(rows, period)
                return_fee = self._get_return_fee(database, period)
                deposit_fee -= return_fee

                total_regist_fee += ins_regist_fee
                total_self_regist_fee += self_regist_fee
                total_deposit_fee += deposit_fee

                self._set_table_item(self.ui.tableWidget_regist_fee, row_no, 1, period)
                self._set_table_item(self.ui.tableWidget_regist_fee, row_no, col_no, ins_regist_fee)
                self._set_table_item(self.ui.tableWidget_regist_fee, row_no, col_no+1, deposit_fee)
                self._set_table_item(self.ui.tableWidget_regist_fee, row_no, col_no+2, self_regist_fee)

            self._set_table_item(self.ui.tableWidget_regist_fee, start_row_no + len(self.period_list), 1, '小計')
            self._set_table_item(
                self.ui.tableWidget_regist_fee, start_row_no + len(self.period_list), col_no, total_regist_fee)
            self._set_table_item(
                self.ui.tableWidget_regist_fee, start_row_no + len(self.period_list), col_no+1, total_deposit_fee)
            self._set_table_item(
                self.ui.tableWidget_regist_fee, start_row_no + len(self.period_list), col_no+2, total_self_regist_fee)

        self._calculate_fee_total(self.ui.tableWidget_regist_fee)

    def _calculate_diag_share_fee(self):
        self.ui.tableWidget_diag_share_fee.clear()

        col_data_list = ['金額']
        col_data_length = len(col_data_list)

        clinic_count = len(self.database_list)

        self.ui.tableWidget_diag_share_fee.setColumnCount(clinic_count * col_data_length + 3)
        self.ui.tableWidget_diag_share_fee.setRowCount(6)
        self._set_table_item(self.ui.tableWidget_diag_share_fee, 0, 0, 'B.門診負擔')
        self.ui.tableWidget_diag_share_fee.setSpan(0, 0, 6, 1)

        self._set_table_item(self.ui.tableWidget_diag_share_fee, 0, 1, '班別/診所')
        self.ui.tableWidget_diag_share_fee.setSpan(0, 1, 2, 1)
        self._set_table_item(self.ui.tableWidget_diag_share_fee, 2, 1, '早班')
        self._set_table_item(self.ui.tableWidget_diag_share_fee, 3, 1, '午班')
        self._set_table_item(self.ui.tableWidget_diag_share_fee, 4, 1, '晚班')
        self._set_table_item(
            self.ui.tableWidget_diag_share_fee,
            0, self.ui.tableWidget_diag_share_fee.columnCount()-1, '總計')
        self.ui.tableWidget_diag_share_fee.setSpan(
            0, self.ui.tableWidget_diag_share_fee.columnCount()-1, 2, 1)

        for i, clinic_name in enumerate(self.database_list):
            database = self.database_list[clinic_name]['database']
            rows = self._get_rows(database)

            col_no = col_data_length * i + 2
            self._set_table_item(self.ui.tableWidget_diag_share_fee, 0, col_no, clinic_name)
            if col_data_length >= 2:
                self.ui.tableWidget_diag_share_fee.setSpan(0, col_no, 1, col_data_length)

            for j, col_data in enumerate(col_data_list):
                self._set_table_item(self.ui.tableWidget_diag_share_fee, 1, col_no+j, col_data)

            total_diag_share_fee = 0
            start_row_no = 2
            for row_no in range(start_row_no, start_row_no + len(self.period_list)):
                period = self.period_list[row_no - start_row_no]
                diag_share_fee = self._calculate_fee(rows, period, 'SDiagShareFee')
                total_diag_share_fee += diag_share_fee

                self._set_table_item(self.ui.tableWidget_diag_share_fee, row_no, 1, period)
                self._set_table_item(self.ui.tableWidget_diag_share_fee, row_no, col_no, diag_share_fee)

            self._set_table_item(self.ui.tableWidget_diag_share_fee, start_row_no + len(self.period_list), 1, '小計')
            self._set_table_item(
                self.ui.tableWidget_diag_share_fee, start_row_no + len(self.period_list), col_no, total_diag_share_fee)

        self._calculate_fee_total(self.ui.tableWidget_diag_share_fee)

    def _calculate_drug_share_fee(self):
        self.ui.tableWidget_drug_share_fee.clear()

        col_data_list = ['金額']
        col_data_length = len(col_data_list)

        clinic_count = len(self.database_list)

        self.ui.tableWidget_drug_share_fee.setColumnCount(clinic_count * col_data_length + 3)
        self.ui.tableWidget_drug_share_fee.setRowCount(6)
        self._set_table_item(self.ui.tableWidget_drug_share_fee, 0, 0, 'C.藥品負擔')
        self.ui.tableWidget_drug_share_fee.setSpan(0, 0, 6, 1)

        self._set_table_item(self.ui.tableWidget_drug_share_fee, 0, 1, '班別/診所')
        self.ui.tableWidget_drug_share_fee.setSpan(0, 1, 2, 1)
        self._set_table_item(self.ui.tableWidget_drug_share_fee, 2, 1, '早班')
        self._set_table_item(self.ui.tableWidget_drug_share_fee, 3, 1, '午班')
        self._set_table_item(self.ui.tableWidget_drug_share_fee, 4, 1, '晚班')
        self._set_table_item(
            self.ui.tableWidget_drug_share_fee,
            0, self.ui.tableWidget_drug_share_fee.columnCount()-1, '總計')
        self.ui.tableWidget_drug_share_fee.setSpan(
            0, self.ui.tableWidget_drug_share_fee.columnCount()-1, 2, 1)

        for i, clinic_name in enumerate(self.database_list):
            database = self.database_list[clinic_name]['database']
            rows = self._get_rows(database)

            col_no = col_data_length * i + 2
            self._set_table_item(self.ui.tableWidget_drug_share_fee, 0, col_no, clinic_name)
            if col_data_length >= 2:
                self.ui.tableWidget_drug_share_fee.setSpan(0, col_no, 1, col_data_length)

            for j, col_data in enumerate(col_data_list):
                self._set_table_item(self.ui.tableWidget_drug_share_fee, 1, col_no+j, col_data)

            total_drug_share_fee = 0
            start_row_no = 2
            for row_no in range(start_row_no, start_row_no + len(self.period_list)):
                period = self.period_list[row_no - start_row_no]
                drug_share_fee = self._calculate_fee(rows, period, 'SDrugShareFee')
                total_drug_share_fee += drug_share_fee

                self._set_table_item(self.ui.tableWidget_drug_share_fee, row_no, 1, period)
                self._set_table_item(self.ui.tableWidget_drug_share_fee, row_no, col_no, drug_share_fee)

            self._set_table_item(self.ui.tableWidget_drug_share_fee, start_row_no + len(self.period_list), 1, '小計')
            self._set_table_item(
                self.ui.tableWidget_drug_share_fee, start_row_no + len(self.period_list), col_no, total_drug_share_fee)

        self._calculate_fee_total(self.ui.tableWidget_drug_share_fee)

    def _calculate_self_total_fee(self):
        self.ui.tableWidget_self_total_fee.clear()

        col_data_list = ['金額']
        col_data_length = len(col_data_list)

        clinic_count = len(self.database_list)

        self.ui.tableWidget_self_total_fee.setColumnCount(clinic_count * col_data_length + 3)
        self.ui.tableWidget_self_total_fee.setRowCount(6)
        self._set_table_item(self.ui.tableWidget_self_total_fee, 0, 0, 'D.藥局收入')
        self.ui.tableWidget_self_total_fee.setSpan(0, 0, 6, 1)

        self._set_table_item(self.ui.tableWidget_self_total_fee, 0, 1, '班別/診所')
        self.ui.tableWidget_self_total_fee.setSpan(0, 1, 2, 1)
        self._set_table_item(self.ui.tableWidget_self_total_fee, 2, 1, '早班')
        self._set_table_item(self.ui.tableWidget_self_total_fee, 3, 1, '午班')
        self._set_table_item(self.ui.tableWidget_self_total_fee, 4, 1, '晚班')
        self._set_table_item(
            self.ui.tableWidget_self_total_fee,
            0, self.ui.tableWidget_self_total_fee.columnCount()-1, '總計')
        self.ui.tableWidget_self_total_fee.setSpan(
            0, self.ui.tableWidget_self_total_fee.columnCount()-1, 2, 1)

        for i, clinic_name in enumerate(self.database_list):
            database = self.database_list[clinic_name]['database']
            rows = self._get_rows(database)

            col_no = col_data_length * i + 2
            self._set_table_item(self.ui.tableWidget_self_total_fee, 0, col_no, clinic_name)
            if col_data_length >= 2:
                self.ui.tableWidget_self_total_fee.setSpan(0, col_no, 1, col_data_length)

            for j, col_data in enumerate(col_data_list):
                self._set_table_item(self.ui.tableWidget_self_total_fee, 1, col_no+j, col_data)

            total_self_total_fee = 0
            start_row_no = 2
            for row_no in range(start_row_no, start_row_no + len(self.period_list)):
                period = self.period_list[row_no - start_row_no]
                self_total_fee = self._calculate_fee(rows, period, 'TotalFee')
                project_fee = self._get_project_fee(database, period)
                self_total_fee -= project_fee
                total_self_total_fee += self_total_fee

                self._set_table_item(self.ui.tableWidget_self_total_fee, row_no, 1, period)
                self._set_table_item(self.ui.tableWidget_self_total_fee, row_no, col_no, self_total_fee)

            self._set_table_item(self.ui.tableWidget_self_total_fee, start_row_no + len(self.period_list), 1, '小計')
            self._set_table_item(
                self.ui.tableWidget_self_total_fee, start_row_no + len(self.period_list), col_no, total_self_total_fee)

        self._calculate_fee_total(self.ui.tableWidget_self_total_fee)

    def _calculate_project_fee(self):
        period_field = {
            '早班': 1, '午班': 2, '晚班': 3,
        }

        for clinic_name in self.database_list:
            database = self.database_list[clinic_name]['database']
            rows = self._get_project_rows(database)
            for row in rows:
                project_name = string_utils.xstr(row['Project'])
                period = string_utils.xstr(row['Period'])
                col_no = period_field[period]

                row_no = self._is_exists_project(project_name)
                if row_no is None:
                    row_no = self._append_table_item(self.ui.tableWidget_project, 0, project_name)
                    self._set_table_item(self.ui.tableWidget_project, row_no, col_no, 0)

                case_key = row['CaseKey']
                medicine_set = row['MedicineSet']
                amount = number_utils.get_integer(row['Amount'])
                discount_fee = number_utils.get_integer(
                    case_utils.get_discount_fee(self.database, case_key, medicine_set)
                )
                pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
                if pres_days <= 0:
                    pres_days = 1

                cell_value = self._get_cell_value(self.ui.tableWidget_project, row_no, col_no)
                project_fee = amount * pres_days - discount_fee
                cell_value += project_fee

                self._set_table_item(self.ui.tableWidget_project, row_no, col_no, cell_value)

        self._calculate_fee_subtotal(self.ui.tableWidget_project)
        self._calculate_project_total(self.ui.tableWidget_project)

    def _calculate_total_income(self):
        col_no = self.ui.tableWidget_regist_fee.columnCount() - 1
        for row_no in range(2, self.ui.tableWidget_regist_fee.rowCount()):
            regist_fee = number_utils.get_integer(
                self.ui.tableWidget_regist_fee.item(row_no, col_no).text())

            self._set_table_item(self.ui.tableWidget_total_income, row_no-2, 0, regist_fee)

        col_no = self.ui.tableWidget_diag_share_fee.columnCount() - 1
        for row_no in range(2, self.ui.tableWidget_diag_share_fee.rowCount()):
            diag_share_fee = number_utils.get_integer(
                self.ui.tableWidget_diag_share_fee.item(row_no, col_no).text())

            self._set_table_item(self.ui.tableWidget_total_income, row_no-2, 1, diag_share_fee)

        col_no = self.ui.tableWidget_drug_share_fee.columnCount() - 1
        for row_no in range(2, self.ui.tableWidget_drug_share_fee.rowCount()):
            drug_share_fee = number_utils.get_integer(
                self.ui.tableWidget_drug_share_fee.item(row_no, col_no).text())

            self._set_table_item(self.ui.tableWidget_total_income, row_no-2, 2, drug_share_fee)

        col_no = self.ui.tableWidget_self_total_fee.columnCount() - 1
        for row_no in range(2, self.ui.tableWidget_self_total_fee.rowCount()):
            self_total_fee = number_utils.get_integer(
                self.ui.tableWidget_self_total_fee.item(row_no, col_no).text())

            self._set_table_item(self.ui.tableWidget_total_income, row_no-2, 3, self_total_fee)

        row_no = self.ui.tableWidget_project.rowCount() - 1
        for col_no in range(1, self.ui.tableWidget_project.columnCount()):
            project_fee = number_utils.get_integer(
                self.ui.tableWidget_project.item(row_no, col_no).text())

            self._set_table_item(self.ui.tableWidget_total_income, col_no-1, 4, project_fee)

        self._calculate_income_subtotal(self.ui.tableWidget_total_income)

    def _get_cell_value(self, tableWidget, row_no, col_no):
        item = tableWidget.item(row_no, col_no)
        if item is None:
            return 0

        return number_utils.get_integer(item.text())

    def _is_exists_project(self, project_name):
        if self.ui.tableWidget_project.rowCount() <= 0:
            return None

        exists_row_no = None
        for row_no in range(self.ui.tableWidget_project.rowCount()):
            item = self.ui.tableWidget_project.item(row_no, 0)
            if item is None:
                continue

            if item.text() == project_name:
                exists_row_no = row_no
                break

        return exists_row_no

    def _get_rows(self, database):
        sql = f'''
            SELECT InsType, Period, RegistFee, DepositFee, SDiagShareFee, SDrugShareFee, TotalFee FROM cases
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}")
            ORDER BY CaseDate
        '''
        rows = database.select_record(sql)

        return rows

    def _calculate_total_regist_fee(self, rows, period):
        ins_regist_fee = 0
        self_regist_fee = 0
        deposit_fee = 0

        for row in rows:
            if string_utils.xstr(row['Period']) != period:
                continue

            regist_fee = number_utils.get_integer(row['RegistFee'])
            if string_utils.xstr(row['InsType']) == '健保':
                ins_regist_fee += regist_fee
            else:
                self_regist_fee += regist_fee

            deposit_fee += number_utils.get_integer(row['DepositFee'])

        return ins_regist_fee, self_regist_fee, deposit_fee

    def _get_return_fee(self, database, period):
        sql = f'''
            SELECT Fee FROM deposit
            WHERE
                ReturnDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Period = "{period}"
        '''
        rows = database.select_record(sql)

        return_fee = 0
        for row in rows:
            return_fee += number_utils.get_integer(row['Fee'])

        return return_fee

    def _get_project_rows(self, database):
        sql = f'''
            SELECT
                cases.Period, prescript.CaseKey, MedicineSet, prescript.MedicineName, Amount,
                medicine.Project
            FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                medicine.Project IS NOT NULL AND LENGTH(medicine.Project) > 0
        '''
        rows = database.select_record(sql)

        return rows

    def _get_project_fee(self, database, current_period):
        rows = self._get_project_rows(database)

        project_fee = 0
        for row in rows:
            period = string_utils.xstr(row['Period'])
            if period != current_period:
                continue

            case_key = row['CaseKey']
            medicine_set = row['MedicineSet']
            amount = number_utils.get_integer(row['Amount'])
            discount_fee = number_utils.get_integer(
                case_utils.get_discount_fee(self.database, case_key, medicine_set)
            )
            pres_days = case_utils.get_pres_days(database, case_key, medicine_set)
            if pres_days <= 0:
                pres_days = 1

            project_fee += amount * pres_days - discount_fee

        return project_fee

    def _calculate_fee(self, rows, period, field_name):
        total_share_fee = 0

        for row in rows:
            if string_utils.xstr(row['Period']) != period:
                continue

            share_fee = number_utils.get_integer(row[field_name])
            total_share_fee += share_fee

        return total_share_fee

    def _calculate_fee_total(self, tableWidget):
        col_count = tableWidget.columnCount()

        for row_no in range(2, 6):
            total_value = 0
            for col_no in range(2, col_count-1):
                item = tableWidget.item(row_no, col_no)
                if item is None:
                    continue

                total_value += number_utils.get_integer(item.text())

            self._set_table_item(tableWidget, row_no, col_count-1, total_value)

    def _calculate_fee_subtotal(self, tableWidget):
        col_count = tableWidget.columnCount()

        for row_no in range(tableWidget.rowCount()):
            total_value = 0
            for col_no in range(1, col_count-1):
                item = tableWidget.item(row_no, col_no)
                if item is None:
                    self._set_table_item(tableWidget, row_no, col_no, 0)
                    continue

                total_value += number_utils.get_integer(item.text())

            self._set_table_item(tableWidget, row_no, col_count-1, total_value)

    def _calculate_income_subtotal(self, tableWidget):
        col_count = tableWidget.columnCount()

        for row_no in range(tableWidget.rowCount()):
            total_value = 0
            for col_no in range(col_count-1):
                item = tableWidget.item(row_no, col_no)
                if item is None:
                    self._set_table_item(tableWidget, row_no, col_no, 0)
                    continue

                total_value += number_utils.get_integer(item.text())

            self._set_table_item(tableWidget, row_no, col_count-1, total_value)

    def _calculate_project_total(self, tableWidget):
        total_row_no = self._append_table_item(self.ui.tableWidget_project, 0, '合計')

        for col_no in range(1, tableWidget.columnCount()):
            total_value = 0
            for row_no in range(tableWidget.rowCount()):
                item = tableWidget.item(row_no, col_no)
                if item is None:
                    continue

                total_value += number_utils.get_integer(item.text())

            self._set_table_item(tableWidget, total_row_no, col_no, total_value)

    @staticmethod
    def _set_table_item(tableWidget, row_no, col_no, data):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, data)
        tableWidget.setItem(row_no, col_no, item)
        tableWidget.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    @staticmethod
    def _append_table_item(tableWidget, col_no, data):
        row_count = tableWidget.rowCount()
        tableWidget.setRowCount(row_count+1)

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, data)
        tableWidget.setItem(row_count, col_no, item)
        tableWidget.item(
            row_count, col_no).setTextAlignment(
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

        return row_count

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}掛號費優待統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0],
            [4, 5, 6, 8],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>掛號費優待統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

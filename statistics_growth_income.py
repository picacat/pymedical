# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import ui_utils
from libs import number_utils
from libs import system_utils
from libs import printer_utils


# 業績成長統計-年收入統計 2023.05.07
class StatisticsGrowthIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsGrowthIncome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_GROWTH_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            140, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print.clicked.connect(self._print_income)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self._calculate_data()
        self._calculate_total()

    def _calculate_data(self):
        max_month = 12

        self.ui.tableWidget_medical_record.setRowCount(0)

        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計資料中, 請稍後...', '取消', 0, max_month, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        i = 0
        for month in range(1, max_month+1):
            i += 1
            progress_dialog.setValue(i)

            month_name = f'{self.year}年{month:0>2}月'

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "健保"
            '''
            rows = self.database.select_record(sql)
            ins_count = rows[0]['Count']
            if ins_count == 0:
                continue

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "自費" AND
                    TreatType NOT IN ("自購", "民俗調理")
            '''
            rows = self.database.select_record(sql)
            self_count = rows[0]['Count']

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "自費" AND
                    TreatType IN ("自購")
            '''
            rows = self.database.select_record(sql)
            purchase_count = rows[0]['Count']

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "自費" AND
                    TreatType IN ("民俗調理")
            '''
            rows = self.database.select_record(sql)
            self_massage_count = rows[0]['Count']

            person_count = ins_count + self_count + purchase_count + self_massage_count

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "健保" AND
                    (RegistFee IS NULL OR RegistFee = 0)
            '''
            rows = self.database.select_record(sql)
            free_regist_fee = rows[0]['Count']

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "健保" AND
                    (SDiagShareFee IS NULL OR SDiagShareFee = 0)
            '''
            rows = self.database.select_record(sql)
            free_diag_share_fee = rows[0]['Count']

            sql = f'''
                SELECT COUNT(*) AS Count FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "健保" AND
                    (SDrugShareFee IS NULL OR SDrugShareFee = 0)
            '''
            rows = self.database.select_record(sql)
            free_drug_share_fee = rows[0]['Count']

            sql = f'''
                SELECT SUM(RegistFee) AS Fee FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month}
            '''
            rows = self.database.select_record(sql)
            regist_fee = number_utils.get_integer(rows[0]['Fee'])

            sql = f'''
                SELECT SUM(RegistFee) AS Fee FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month} AND
                    InsType = "健保" AND
                    (Continuance IS NULL OR Continuance <= 1)
            '''
            rows = self.database.select_record(sql)
            first_regist_fee = number_utils.get_integer(rows[0]['Fee'])

            sql = f'''
                SELECT SUM(SDiagShareFee) AS Fee FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month}
            '''
            rows = self.database.select_record(sql)
            diag_share_fee = number_utils.get_integer(rows[0]['Fee'])

            sql = f'''
                SELECT SUM(SDrugShareFee) AS Fee FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month}
            '''
            rows = self.database.select_record(sql)
            drug_share_fee = number_utils.get_integer(rows[0]['Fee'])

            sql = f'''
                SELECT SUM(TotalFee) AS Fee FROM cases
                WHERE
                    Year(CaseDate) = {self.year} AND
                    Month(CaseDate) = {month}
            '''
            rows = self.database.select_record(sql)
            total_fee = number_utils.get_integer(rows[0]['Fee'])

            total_amount = regist_fee + diag_share_fee + drug_share_fee + total_fee

            row_no = self.ui.tableWidget_medical_record.rowCount()
            self.ui.tableWidget_medical_record.setRowCount(row_no + 1)

            medical_record_count = [
                month_name, ins_count, self_count, purchase_count, self_massage_count, person_count,
                free_regist_fee, free_diag_share_fee, free_drug_share_fee,
                regist_fee, first_regist_fee, diag_share_fee, drug_share_fee, total_fee, total_amount,
            ]

            for col_no, data in enumerate(medical_record_count):
                item = QtWidgets.QTableWidgetItem()
                if col_no in [0]:
                    item.setData(QtCore.Qt.EditRole, data)
                else:
                    item.setData(QtCore.Qt.EditRole, f'{data:,}')

                self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)
                if col_no in [0]:
                    self.ui.tableWidget_medical_record.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )
                else:
                    self.ui.tableWidget_medical_record.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

        progress_dialog.setValue(max_month)
        progress_dialog.deleteLater()

    def _calculate_total(self):
        row_count = self.ui.tableWidget_medical_record.rowCount()
        ins_count, self_count, purchase_count, self_massage_count, person_count = 0, 0, 0, 0, 0
        free_regist_fee, free_diag_share_fee, free_drug_share_fee = 0, 0, 0
        regist_fee, first_regist_fee = 0, 0
        diag_share_fee, drug_share_fee = 0, 0
        total_fee, total_amount = 0, 0

        for row_no in range(row_count):
            ins_count += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 1).text())
            self_count += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 2).text())
            purchase_count += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 3).text())
            self_massage_count += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 4).text())
            person_count += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 5).text())

            free_regist_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 6).text())
            free_diag_share_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 7).text())
            free_drug_share_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 8).text())

            regist_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 9).text())
            first_regist_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 10).text())
            diag_share_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 11).text())
            drug_share_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 12).text())
            total_fee += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 13).text())
            total_amount += number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 14).text())

        total_row = [
            '合計', ins_count, self_count, purchase_count, self_massage_count, person_count,
            free_regist_fee, free_diag_share_fee, free_drug_share_fee,
            regist_fee, first_regist_fee, diag_share_fee, drug_share_fee, total_fee, total_amount
        ]

        self.ui.tableWidget_medical_record.setRowCount(row_count + 1)
        for col_no in range(len(total_row)):
            item = QtWidgets.QTableWidgetItem()
            data = total_row[col_no]
            if col_no in [0]:
                item.setData(QtCore.Qt.EditRole, data)
            else:
                item.setData(QtCore.Qt.EditRole, f'{data:,}')

            self.ui.tableWidget_medical_record.setItem(row_count, col_no, item)
            if col_no == 0:
                self.ui.tableWidget_medical_record.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            else:
                self.ui.tableWidget_medical_record.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _print_income(self):
        printer_utils.print_growth_income(
            self, self.database, self.system_settings, self.ui.tableWidget_medical_record,
        )

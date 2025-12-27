
# 掛號櫃台結帳 - 健保收費明細 2021.11.25
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import class_utils
from libs import ui_utils
from libs import personnel_utils
from libs import system_utils
from libs import export_utils
from libs import string_utils
from libs import number_utils
from libs import nhi_utils
from libs import case_utils
from libs import printer_utils


# 掛號櫃台結帳 - 健保收費明細
class IncomeInsList(QtWidgets.QMainWindow):
    program_name = '健保收費明細'

    # 初始化
    def __init__(self, parent=None, *args):
        super(IncomeInsList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.regist_type = args[5]
        self.doctor = args[6]
        self.room = args[7]
        self.cashier = args[8]
        self.income_source = args[9]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()
        self._start_calculate()
        self._read_medical_record()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_income(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INCOME_INS_LIST, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_income = class_utils.get_table_widget(
            self.ui.tableWidget_income, self.database
        )
        self.table_widget_free_count = class_utils.get_table_widget(
            self.ui.tableWidget_free_count, self.database
        )
        self._set_table_width()
        self._set_table_free_count_header()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_print.clicked.connect(self._print_income_ins_list)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100, 90,
            120, 120, 110,
            130, 130, 120, 120,
            110,
            90, 90, 90, 90
        ]
        self.table_widget_income.set_table_heading_width(width)

    def _set_table_free_count_header(self):
        self.free_regist_fee = ['員工', '眷屬', '親友', '殘障', '其他', '小計']
        self.free_diag_share = ['福保', '榮民', '職傷', '重大傷病', '針灸療程', '其他', '小計']
        self.ui.tableWidget_free_count.setColumnCount(
            len(self.free_regist_fee) + len(self.free_diag_share) + 1
        )
        self.ui.tableWidget_free_count.setRowCount(2)
        self.ui.tableWidget_free_count.setItem(0, 0, QtWidgets.QTableWidgetItem('經手人'))
        self.ui.tableWidget_free_count.setSpan(0, 0, 2, 1)
        self.ui.tableWidget_free_count.setItem(0, 1, QtWidgets.QTableWidgetItem('免收掛號費人數'))
        self.ui.tableWidget_free_count.setSpan(0, 1, 1, len(self.free_regist_fee))
        self.ui.tableWidget_free_count.setItem(
            0, len(self.free_regist_fee)+1, QtWidgets.QTableWidgetItem('免收部份負擔人數')
        )
        self.ui.tableWidget_free_count.setSpan(0, len(self.free_regist_fee)+1, 1, len(self.free_diag_share))

        col_no = 1
        for item in self.free_regist_fee:
            self.ui.tableWidget_free_count.setItem(1, col_no, QtWidgets.QTableWidgetItem(item))
            col_no += 1

        col_no = len(self.free_regist_fee) + 1
        for item in self.free_diag_share:
            self.ui.tableWidget_free_count.setItem(1, col_no, QtWidgets.QTableWidgetItem(item))
            col_no += 1

        self._center_cell()

    def _center_cell(self):
        for row_no in range(self.ui.tableWidget_free_count.rowCount()):
            for col_no in range(self.ui.tableWidget_free_count.columnCount()):
                item = self.ui.tableWidget_free_count.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, self.program_name, '進入病歷', self.user_name) != 'Y'):
            return

        case_key = self.table_widget_self_prescript.field_value(0)
        if case_key is None:
            return

        self.parent.open_medical_record(case_key, '掛號櫃台結帳')

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出專案銷售明細",
            f'{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}專案銷售明細表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript, [0], [10, 12, 13]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>專案銷售明細表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _start_calculate(self):
        rows = self._read_medical_record()
        self._calculate_income(rows)
        self._calculate_free_count(rows)
        self._calculate_summary()

    def _read_medical_record(self):
        sql = f'''
            SELECT cases.*, patient.DiscountType FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保" AND
                {case_utils.exclude_xx_card()}
        '''
        if self.period != '全部':
            if self.period == '早午班':
                sql += ' AND cases.ChargePeriod IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += ' AND cases.ChargePeriod IN("午班", "晚班") '
            else:
                sql += f' AND cases.ChargePeriod = "{self.period}"'

        if self.doctor != '全部':
            sql += f' AND cases.Doctor = "{self.doctor}"'
        if self.room != '全部':
            sql += f' AND Room = {self.room}'
        if self.cashier != '全部':
            sql += f' AND Register = "{self.cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Register = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        sql += ' ORDER BY cases.Register'

        try:
            rows = self.database.select_record(sql)
        except Exception:
            rows = []

        return rows

    def _calculate_income(self, rows):
        for row in rows:
            registrar = string_utils.xstr(row['Register'])
            if registrar == '':
                registrar = '不詳'

            row_no = self._get_row_no(self.ui.tableWidget_income, registrar)
            if row_no is None:
                row_no = self.ui.tableWidget_income.rowCount()
                self.ui.tableWidget_income.setRowCount(row_no + 1)

            self.ui.tableWidget_income.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(registrar)
            )

            ins_count = self._get_item_value(self.ui.tableWidget_income, row_no, 1) + 1
            self._set_item_data(self.ui.tableWidget_income, row_no, 1, ins_count)

            regist_fee = number_utils.get_integer(row['RegistFee'])
            if regist_fee > 0:
                fee_count = self._get_item_value(self.ui.tableWidget_income, row_no, 2) + 1
                self._set_item_data(self.ui.tableWidget_income, row_no, 2, fee_count)
            else:
                fee_count = self._get_item_value(self.ui.tableWidget_income, row_no, 3) + 1
                self._set_item_data(self.ui.tableWidget_income, row_no, 3, fee_count)

            regist_fee += self._get_item_value(self.ui.tableWidget_income, row_no, 4)
            self._set_item_data(self.ui.tableWidget_income, row_no, 4, regist_fee)

            diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
            if diag_share_fee > 0:
                diag_share_count = self._get_item_value(self.ui.tableWidget_income, row_no, 5) + 1
                self._set_item_data(self.ui.tableWidget_income, row_no, 5, diag_share_count)
            else:
                diag_share_count = self._get_item_value(self.ui.tableWidget_income, row_no, 6) + 1
                self._set_item_data(self.ui.tableWidget_income, row_no, 6, diag_share_count)

            diag_share_fee += self._get_item_value(self.ui.tableWidget_income, row_no, 7)
            self._set_item_data(self.ui.tableWidget_income, row_no, 7, diag_share_fee)

            drug_share_fee = self._get_item_value(
                self.ui.tableWidget_income, row_no, 8) + number_utils.get_integer(row['SDrugShareFee'])
            self._set_item_data(self.ui.tableWidget_income, row_no, 8, drug_share_fee)

            deposit_fee = number_utils.get_integer(row['DepositFee'])
            if deposit_fee > 0:
                deposit = self._get_item_value(self.ui.tableWidget_income, row_no, 10) + 1
                self._set_item_data(self.ui.tableWidget_income, row_no, 10, deposit)

            deposit_fee += self._get_item_value(self.ui.tableWidget_income, row_no, 11)
            self._set_item_data(self.ui.tableWidget_income, row_no, 11, deposit_fee)

        self._set_return_fee()
        self._fill_zero(self.ui.tableWidget_income, 1)
        self._calculate_income_subtotal()
        self._calculate_income_total()

    def _calculate_income_subtotal(self):
        for row_no in range(self.ui.tableWidget_income.rowCount()):
            subtotal = (
               self._get_item_value(self.ui.tableWidget_income, row_no, 4) +
               self._get_item_value(self.ui.tableWidget_income, row_no, 7) +
               self._get_item_value(self.ui.tableWidget_income, row_no, 8)
            )
            self._set_item_data(self.ui.tableWidget_income, row_no, 9, subtotal)

    def _calculate_income_total(self):
        total_row_no = self.ui.tableWidget_income.rowCount()

        self.ui.tableWidget_income.setRowCount(total_row_no + 1)
        self._set_item_data(self.ui.tableWidget_income, total_row_no, 0, '合計')

        for col_no in range(1, self.ui.tableWidget_income.columnCount()):
            subtotal = 0
            for row_no in range(self.ui.tableWidget_income.rowCount()-1):
                value = self._get_item_value(self.ui.tableWidget_income, row_no, col_no)
                subtotal += value

            self._set_item_data(self.ui.tableWidget_income, total_row_no, col_no, subtotal)

    def _set_return_fee(self):
        sql = f'''
            SELECT * FROM deposit
            WHERE
                ReturnDate BETWEEN "{self.start_date}" AND "{self.end_date}"
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            refunder = string_utils.xstr(row['Refunder'])
            return_fee = number_utils.get_integer(row['Fee'])
            row_no = self._get_row_no(self.ui.tableWidget_income, refunder)

            if row_no is None:
                row_no = self.ui.tableWidget_income.rowCount()
                self.ui.tableWidget_income.setRowCount(row_no + 1)
                self.ui.tableWidget_income.setItem(
                    row_no, 0, QtWidgets.QTableWidgetItem(refunder)
                )

            self._add_item_data(self.ui.tableWidget_income, row_no, 12, 1)
            self._add_item_data(self.ui.tableWidget_income, row_no, 13, return_fee)

    def _get_item_value(self, in_table_widget, row_no, col_no):
        item = in_table_widget.item(row_no, col_no)

        if item is None:
            value = 0
        else:
            value = number_utils.get_integer(item.text())

        return value

    def _set_item_data(self, in_table_widget, row_no, col_no, data):
        in_table_widget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(data))
        )

        if data != '合計':
            in_table_widget.item(row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _add_item_data(self, in_table_widget, row_no, col_no, data):
        item = in_table_widget.item(row_no, col_no)
        if item is None:
            origin_value = 0
        else:
            origin_value = number_utils.get_integer(item.text())

        in_table_widget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(origin_value + data))
        )
        in_table_widget.item(row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _get_row_no(self, in_table_widget, registrar):
        for row_no in range(in_table_widget.rowCount()):
            item = in_table_widget.item(row_no, 0)
            if item is None:
                continue

            if registrar == item.text():
                return row_no

        return None

    def _get_col_no(self, in_table_widget, fee_type, data):
        if '員工' in data:
            data = '員工'
        elif '低收入戶' in data:
            data = '福保'
        elif '職業' in data:
            data = '職傷'

        if fee_type == '掛號費':
            start_no = 1
            if data not in self.free_regist_fee[:-2]:
                data = '其他'
        elif fee_type == '部份負擔':
            start_no = len(self.free_regist_fee) + 1
            if data not in self.free_diag_share[:-2]:
                data = '其他'

        for col_no in range(start_no, in_table_widget.columnCount()):
            item = in_table_widget.item(1, col_no)
            if item is None:
                continue

            if data == item.text():
                return col_no

        return None

    def _calculate_free_count(self, rows):
        for row in rows:
            share_type = string_utils.xstr(row['Share'])
            discount_type = string_utils.xstr(row['DiscountType'])
            regist_fee = number_utils.get_integer(row['RegistFee'])
            diag_share_fee = number_utils.get_integer(row['DiagShareFee'])
            registrar = string_utils.xstr(row['Register'])
            treat_type = string_utils.xstr(row['TreatType'])
            course = number_utils.get_integer(row['Continuance'])
            if share_type == '基層醫療' and course >= 2 and treat_type in nhi_utils.ACUPUNCTURE_TREAT:
                share_type = '針灸療程'

            if registrar == '':
                registrar = '不詳'

            row_no = self._get_row_no(self.ui.tableWidget_free_count, registrar)
            if row_no is None:
                row_no = self.ui.tableWidget_free_count.rowCount()
                self.ui.tableWidget_free_count.setRowCount(row_no + 1)

            self.ui.tableWidget_free_count.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(registrar)
            )

            if regist_fee <= 0:
                col_no = self._get_col_no(self.ui.tableWidget_free_count, '掛號費', discount_type)
                free_regist_fee = self._get_item_value(self.ui.tableWidget_free_count, row_no, col_no) + 1
                self._set_item_data(self.ui.tableWidget_free_count, row_no, col_no, free_regist_fee)

            if diag_share_fee <= 0:
                col_no = self._get_col_no(self.ui.tableWidget_free_count, '部份負擔', share_type)
                free_share_fee = self._get_item_value(self.ui.tableWidget_free_count, row_no, col_no) + 1
                self._set_item_data(self.ui.tableWidget_free_count, row_no, col_no, free_share_fee)

        self._fill_zero(self.ui.tableWidget_free_count, 1)
        self._calculate_free_subtotal()
        self._calculate_free_total()

    def _calculate_free_subtotal(self):
        for row_no in range(2, self.ui.tableWidget_free_count.rowCount()):
            subtotal = 0
            for col_no in range(1, len(self.free_regist_fee)):
                subtotal += self._get_item_value(self.ui.tableWidget_free_count, row_no, col_no)

            self._set_item_data(
                self.ui.tableWidget_free_count, row_no, len(self.free_regist_fee), subtotal)

        for row_no in range(2, self.ui.tableWidget_free_count.rowCount()):
            subtotal = 0
            for col_no in range(len(self.free_regist_fee)+1, self.ui.tableWidget_free_count.columnCount()):
                subtotal += self._get_item_value(self.ui.tableWidget_free_count, row_no, col_no)

            self._set_item_data(
                self.ui.tableWidget_free_count, row_no, self.ui.tableWidget_free_count.columnCount()-1, subtotal)

    def _calculate_free_total(self):
        total_row_no = self.ui.tableWidget_free_count.rowCount()

        self.ui.tableWidget_free_count.setRowCount(total_row_no + 1)
        self._set_item_data(self.ui.tableWidget_free_count, total_row_no, 0, '合計')

        for col_no in range(1, self.ui.tableWidget_free_count.columnCount()):
            subtotal = 0
            for row_no in range(self.ui.tableWidget_free_count.rowCount()-1):
                value = self._get_item_value(self.ui.tableWidget_free_count, row_no, col_no)
                subtotal += value

            self._set_item_data(self.ui.tableWidget_free_count, total_row_no, col_no, subtotal)

    def _calculate_summary(self):
        if self.ui.tableWidget_income.rowCount() <= 0:
            return

        row_no = self.ui.tableWidget_income.rowCount() - 1
        total_fee = self._get_item_value(self.ui.tableWidget_income, row_no, 9)
        deposit_fee = self._get_item_value(self.ui.tableWidget_income, row_no, 11)
        return_fee = self._get_item_value(self.ui.tableWidget_income, row_no, 13)

        self._set_item_data(self.ui.tableWidget_summary, 0, 0, total_fee)
        self._set_item_data(self.ui.tableWidget_summary, 1, 0, deposit_fee)
        self._set_item_data(self.ui.tableWidget_summary, 2, 0, return_fee)
        self._set_item_data(self.ui.tableWidget_summary, 3, 0, total_fee + deposit_fee - return_fee)
        self._set_item_data(self.ui.tableWidget_summary, 4, 0, total_fee + deposit_fee - return_fee)
        self._set_item_data(self.ui.tableWidget_summary, 5, 0, 0)

    def _fill_zero(self, table_widget, start_no):
        for row_no in range(table_widget.rowCount()):
            for col_no in range(start_no, table_widget.columnCount()):
                item = table_widget.item(row_no, col_no)
                if item is None:
                    self._set_item_data(table_widget, row_no, col_no, 0)

    def _print_income_ins_list(self):
        printer_utils.print_income_ins_list(
            self, self.database, self.system_settings, self.start_date, self.period,
            self.ui.tableWidget_income, self.ui.tableWidget_free_count, self.ui.tableWidget_summary,
        )

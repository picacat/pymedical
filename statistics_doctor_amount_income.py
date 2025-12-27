# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils


# 醫師金額收入統計 2023.07.08
class StatisticsDoctorAmountIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorAmountIncome, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_AMOUNT_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor = class_utils.get_table_widget(self.ui.tableWidget_doctor, self.database)
        self._set_table_width()

    def _set_table_width(self):
        width = [
            120,
            80, 80, 80, 70, 70, 90, 90, 90, 90,
            90, 90, 90, 90, 80, 90, 90, 80, 80,
        ]
        self.table_widget_doctor.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_doctor_excel.clicked.connect(self._export_to_doctor_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor.setRowCount(0)
        self._set_statistics_doctor_table_heading()
        self._calculate_data()

    @staticmethod
    def _get_doctor(doctor, treat_type):
        if doctor in ['', None]:
            if treat_type == '自購':
                doctor = treat_type
            else:
                doctor = '空白'

        return doctor

    def _set_statistics_doctor_table_heading(self):
        doctor_list = []
        rows = self._read_data(group_by_doctor=True)

        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row['Doctor']),
                string_utils.xstr(row['TreatType']),
            )
            if doctor in ['自購', '空白']:
                continue

            if doctor not in doctor_list:
                doctor_list.append(doctor)

        row_count = len(doctor_list)
        self.ui.tableWidget_doctor.setRowCount(row_count + 1)

        for row_no, doctor in enumerate(doctor_list):
            self.ui.tableWidget_doctor.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(doctor)
            )

        self.ui.tableWidget_doctor.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem('總計')
        )

    def _calculate_data(self):
        self._reset_data()
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            '門診收入統計中, 請稍後...', '取消', 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self._calculate_doctor_income(rows)
        self._calculate_doctor_refund()
        self._calculate_doctor_ins_subtotal()
        self._calculate_doctor_debt()
        self._calculate_doctor_repayment()
        self._calculate_doctor_total()

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                self.ui.tableWidget_doctor.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_doctor.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self, group_by_doctor=False):
        period_condition = ''
        if self.period != '全部':
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = ' AND Doctor = "{0}"'.format(self.doctor)

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        group_condition = ''
        if group_by_doctor:
            group_condition = ' GROUP BY Doctor, TreatType'

        sql = f'''
            SELECT
                CaseKey, Name, CaseDate, TreatType, Doctor,
                RegistFee, SDiagShareFee, SDrugShareFee, DepositFee,
                SDiagFee, SDrugFee, SHerbFee, SExpensiveFee,
                SAcupunctureFee, SMassageFee, SDislocateFee,
                SMaterialFee, SelfTotalFee, DiscountFee, TotalFee, ReceiptFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
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

    def _calculate_doctor_income(self, rows):
        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row['Doctor']),
                string_utils.xstr(row['TreatType']),
            )
            if doctor in ['自購', '空白']:
                continue

            row_no = self._get_doctor_row_no(doctor)

            regist_fee = self._get_doctor_cell_fee(row_no, 1) + number_utils.get_integer(row['RegistFee'])
            diag_share_fee = self._get_doctor_cell_fee(row_no, 2) + number_utils.get_integer(row['SDiagShareFee'])
            drug_share_fee = self._get_doctor_cell_fee(row_no, 3) + number_utils.get_integer(row['SDrugShareFee'])
            deposit_fee = self._get_doctor_cell_fee(row_no, 4) + number_utils.get_integer(row['DepositFee'])
            self_diag_fee = self._get_doctor_cell_fee(row_no, 7) + number_utils.get_integer(row['SDiagFee'])
            self_drug_fee = self._get_doctor_cell_fee(row_no, 8) + number_utils.get_integer(row['SDrugFee'])
            herb_fee = self._get_doctor_cell_fee(row_no, 9) + number_utils.get_integer(row['SHerbFee'])
            expensive_fee = self._get_doctor_cell_fee(row_no, 10) + number_utils.get_integer(row['SExpensiveFee'])
            self_treat_fee = self._get_doctor_cell_fee(row_no, 11) + \
                number_utils.get_integer(row['SAcupunctureFee']) + \
                number_utils.get_integer(row['SMassageFee']) + \
                number_utils.get_integer(row['SDislocateFee'])
            material_fee = self._get_doctor_cell_fee(row_no, 12) + number_utils.get_integer(row['SMaterialFee'])
            self_total_fee = self._get_doctor_cell_fee(row_no, 13) + number_utils.get_integer(row['SelfTotalFee'])
            discount_fee = self._get_doctor_cell_fee(row_no, 14) + number_utils.get_integer(row['DiscountFee'])
            total_fee = self._get_doctor_cell_fee(row_no, 15) + number_utils.get_integer(row['TotalFee'])
            receipt_fee = self._get_doctor_cell_fee(row_no, 16) + number_utils.get_integer(row['ReceiptFee'])

            self._set_doctor_item_data(row_no, 1, string_utils.xstr(regist_fee))
            self._set_doctor_item_data(row_no, 2, string_utils.xstr(diag_share_fee))
            self._set_doctor_item_data(row_no, 3, string_utils.xstr(drug_share_fee))
            self._set_doctor_item_data(row_no, 4, string_utils.xstr(deposit_fee))
            self._set_doctor_item_data(row_no, 7, string_utils.xstr(self_diag_fee))
            self._set_doctor_item_data(row_no, 8, string_utils.xstr(self_drug_fee))
            self._set_doctor_item_data(row_no, 9, string_utils.xstr(herb_fee))
            self._set_doctor_item_data(row_no, 10, string_utils.xstr(expensive_fee))
            self._set_doctor_item_data(row_no, 11, string_utils.xstr(self_treat_fee))
            self._set_doctor_item_data(row_no, 12, string_utils.xstr(material_fee))
            self._set_doctor_item_data(row_no, 13, string_utils.xstr(self_total_fee))
            self._set_doctor_item_data(row_no, 14, string_utils.xstr(discount_fee))
            self._set_doctor_item_data(row_no, 15, string_utils.xstr(total_fee))
            self._set_doctor_item_data(row_no, 16, string_utils.xstr(receipt_fee))

    def _get_doctor_row_no(self, doctor):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor_field = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor_field is None:
                doctor = '空白'

            if doctor == doctor_field.text():
                return row_no

        return None

    def _get_doctor_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_doctor.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _set_doctor_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_doctor.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_doctor.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_doctor.item(row_no, col_no).setForeground(
                QtGui.QColor('red')
            )

    def _calculate_doctor_refund(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                refund = 0
            else:
                refund = self._get_doctor_refund(doctor.text())

            self._set_doctor_item_data(row_no, 5, string_utils.xstr(refund))

    def _get_doctor_refund(self, doctor):
        start_date = f'{self.start_date} 00:00:00'
        end_date = f'{self.end_date} 23:59:59'

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(ReturnDate) IN({",".join(self.weekday_list)})'

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
            return_fee += number_utils.get_integer(row['Fee'])

        return -return_fee

    def _calculate_doctor_debt(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                debt = 0
            else:
                debt = self._get_doctor_debt(doctor.text())

            self._set_doctor_item_data(row_no, 17, string_utils.xstr(debt))

    def _get_doctor_debt(self, doctor):
        start_date = f'{self.start_date} 00:00:00'
        end_date = f'{self.end_date} 23:59:59'

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(debt.CaseDate) IN({",".join(self.weekday_list)})'

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
            debt += number_utils.get_integer(row['Fee'])

        return -debt

    def _calculate_doctor_repayment(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                repayment = 0
            else:
                repayment = self._get_doctor_repayment(doctor.text())

            self._set_doctor_item_data(row_no, 18, string_utils.xstr(repayment))

    def _get_doctor_repayment(self, doctor):
        start_date = f'{self.start_date} 00:00:00'
        end_date = f'{self.end_date} 23:59:59'

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(ReturnDate1) IN({",".join(self.weekday_list)})'

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
            repayment += number_utils.get_integer(row['Fee1'])

        return repayment

    def _calculate_doctor_ins_subtotal(self):
        subtotal_field_no = 6

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            subtotal = 0
            for col_no in range(1, subtotal_field_no):
                subtotal += number_utils.get_integer(
                    self.ui.tableWidget_doctor.item(row_no, col_no).text()
                )

            self._set_doctor_item_data(row_no, subtotal_field_no, string_utils.xstr(subtotal))

    def _calculate_doctor_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_doctor.columnCount())]
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                value = number_utils.get_integer(self.ui.tableWidget_doctor.item(row_no, col_no).text())
                total_list[col_no] += value

        row_no = self.ui.tableWidget_doctor.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_doctor_item_data(
                row_no, col_no, string_utils.xstr(total_list[col_no])
            )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}醫師金額統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor,
            title=f'{self.system_settings.field("院所名稱")} 醫師金額統計表',
            numeric_cell=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            calc_total=False
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>個別醫師收入統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils
from libs import printer_utils


# 門診收入總覽 2021.07.15
class StatisticsDoctorSummary(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorSummary, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.doctor = args[5]
        self.option = args[6]
        self.weekday_list = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_SUMMARY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_summary = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_summary, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            130,
            100, 100, 100, 120, 100, 100, 100, 100, 100, 100,
            100, 100,
        ]
        self.table_widget_doctor_summary.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.toolButton_print.clicked.connect(lambda: self._print_doctor_summary(print_type=None))
        self.ui.toolButton_print_to_pdf.clicked.connect(lambda: self._print_doctor_summary(print_type='pdf'))

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_summary.setRowCount(0)
        self._set_statistics_table_heading()
        self._calculate_data()
        self._calculate_total()

    def _set_statistics_table_heading(self):
        start_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S').date()
        end_date = datetime.datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S').date()
        day_count = (end_date - start_date).days + 1

        calendar_list = []
        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            case_date = date.strftime("%Y-%m-%d")
            if case_date not in calendar_list:
                calendar_list.append(case_date)

        row_count = len(calendar_list)
        self.ui.tableWidget_doctor_summary.setRowCount(row_count + 1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_doctor_summary.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date)
            )

        self.ui.tableWidget_doctor_summary.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem('總計')
        )

        for row_no in range(self.ui.tableWidget_doctor_summary.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor_summary.columnCount()):
                self.ui.tableWidget_doctor_summary.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_doctor_summary.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self):
        period_condition = ''

        if self.period != '全部':
            period_condition = f' AND Period = "{self.period}"'

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                TreatType NOT IN ("自購", "開立證明")
                {period_condition}
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_doctor_summary.rowCount()):
            case_date_item = self.ui.tableWidget_doctor_summary.item(row_no, 0)
            if case_date_item is None:
                continue

            if case_date == case_date_item.text():
                return row_no

        return None

    def _calculate_data(self):
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '門診收入統計中, 請稍後...', '取消', 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for i, row in enumerate(rows):
            case_date = row['CaseDate'].strftime('%Y-%m-%d')
            ins_type = string_utils.xstr(row['InsType'])
            progress_dialog.setValue(i)
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            self._set_person_count(row, row_no)
            if ins_type == '健保':
                self._set_toll_free(row, row_no)

            self._set_income(row, row_no)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    def _is_duplicate_patient(self, row):
        duplicate_patient = False
        case_date = row['CaseDate'].strftime('%Y-%m-%d')
        patient_key = string_utils.xstr(row['PatientKey'])

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                DATE(CaseDate) = "{case_date}" AND
                PatientKey = {patient_key}
        '''
        case_rows = self.database.select_record(sql)
        if len(case_rows) >= 2:
            duplicate_patient = True

        return duplicate_patient

    def _set_person_count(self, row, row_no):
        person_count = 1

        if string_utils.xstr(row['InsType']) == '健保':
            col_no = 1
        else:
            if self._is_duplicate_patient(row):
                return

            col_no = 2

        self._set_item_data(row_no, col_no, person_count)

        subtotal_col_no = 3
        person_subtotal = number_utils.get_integer(
            self.ui.tableWidget_doctor_summary.item(row_no, subtotal_col_no).text()
        )
        person_subtotal += person_count
        self._set_item_data(row_no, subtotal_col_no, person_count)

    def _set_toll_free(self, row, row_no):
        free_regist_fee_col_no = 4
        free_regist_fee_count = 0

        free_diag_share_fee_col_no = 5
        free_diag_share_fee_count = 0

        free_drug_share_fee_col_no = 6
        free_drug_share_fee_count = 0

        if number_utils.get_integer(row['RegistFee']) <= 0:
            free_regist_fee_count = 1

        if number_utils.get_integer(row['SDiagShareFee']) <= 0:
            free_diag_share_fee_count = 1

        if number_utils.get_integer(row['SDrugShareFee']) <= 0:
            free_drug_share_fee_count = 1

        self._set_item_data(row_no, free_regist_fee_col_no, free_regist_fee_count)
        self._set_item_data(row_no, free_diag_share_fee_col_no, free_diag_share_fee_count)
        self._set_item_data(row_no, free_drug_share_fee_col_no, free_drug_share_fee_count)

    def _set_income(self, row, row_no):
        regist_fee_col_no = 7
        first_regist_fee_col_no = 8
        diag_share_fee_col_no = 9
        drug_share_fee_col_no = 10
        total_fee_col_no = 11
        subtotal_fee_col_no = 12

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        self._set_item_data(row_no, regist_fee_col_no, regist_fee)
        if number_utils.get_integer(row['Continuance']) <= 1:
            self._set_item_data(row_no, first_regist_fee_col_no, regist_fee)

        subtotal = regist_fee + diag_share_fee + drug_share_fee + total_fee
        self._set_item_data(row_no, diag_share_fee_col_no, diag_share_fee)
        self._set_item_data(row_no, drug_share_fee_col_no, drug_share_fee)
        self._set_item_data(row_no, total_fee_col_no, total_fee)
        self._set_item_data(row_no, subtotal_fee_col_no, subtotal)

    def _set_item_data(self, row_no, col_no, in_value):
        item = self.ui.tableWidget_doctor_summary.item(row_no, col_no)
        if item is None:
            value = 0
        else:
            value = number_utils.get_integer(item.text())

        value += in_value

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_doctor_summary.setItem(row_no, col_no, item)
        self.ui.tableWidget_doctor_summary.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            f'{start_date}至{end_date}{self.doctor}門診收入一覽表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor_summary, None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>門診收入一覽檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _calculate_total(self):
        total_field_row_no = self.ui.tableWidget_doctor_summary.rowCount() - 1

        row_count = self.ui.tableWidget_doctor_summary.rowCount()
        for row_no in range(row_count-1):
            for col_no in range(1, self.ui.tableWidget_doctor_summary.columnCount()):
                value = number_utils.get_integer(self.ui.tableWidget_doctor_summary.item(row_no, col_no).text())
                self._set_item_data(total_field_row_no, col_no, value)

    def _print_doctor_summary(self, print_type=None):
        printer_utils.print_doctor_summary(
            self, self.database, self.system_settings, self.start_date, self.end_date, self.doctor,
            self.ui.tableWidget_doctor_summary, print_type)

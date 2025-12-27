# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import datetime
import calendar

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import date_utils
from libs import nhi_utils
from libs import printer_utils


# 醫師月報表-收入統計 2023.07.13 同慶
class StatisticsDoctorMonthlyIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorMonthlyIncome, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.doctor = args[4]
        self.ui = None

        self.last_day = calendar.monthrange(int(self.year), int(self.month))[1]
        self.start_date = f'{self.year}-{self.month}-01 00:00:00'
        self.end_date = f'{self.year}-{self.month}-{self.last_day} 23:59:59'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_MONTHLY_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_monthly = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_monthly, self.database
        )

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)
        self.ui.toolButton_print.clicked.connect(lambda: self._print_doctor_monthly_income(print_type=None))

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor_monthly.setRowCount(0)
        self._set_statistics_table_heading()
        self._calculate_data()
        self._calculate_total()

    def _set_heading(self, title, submenu):
        start_col_no = self.ui.tableWidget_doctor_monthly.columnCount()

        self.ui.tableWidget_doctor_monthly.setColumnCount(
            self.ui.tableWidget_doctor_monthly.columnCount()+len(submenu))
        self.ui.tableWidget_doctor_monthly.setItem(0, start_col_no, QtWidgets.QTableWidgetItem(title))
        self.ui.tableWidget_doctor_monthly.setSpan(0, start_col_no, 1, len(submenu))
        self.ui.tableWidget_doctor_monthly.item(0, start_col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )
        for col_no, menu in enumerate(submenu):
            self.ui.tableWidget_doctor_monthly.setItem(
                1, col_no+start_col_no, QtWidgets.QTableWidgetItem(menu))
            self.ui.tableWidget_doctor_monthly.item(1, col_no+start_col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

    def _set_statistics_table_heading(self):
        v_heading_height = 2
        self.ui.tableWidget_doctor_monthly.setColumnCount(2)
        self.ui.tableWidget_doctor_monthly.setRowCount(v_heading_height)

        self.ui.tableWidget_doctor_monthly.setItem(0, 0, QtWidgets.QTableWidgetItem('項目'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 0, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 0).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(0, 1, QtWidgets.QTableWidgetItem('健保人數'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 1, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 1).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self._set_heading('掛號費', ['收費人數', '免收人數', '金額'])
        self._set_heading('門診負擔', ['收費人數', '免收人數', '金額'])
        self._set_heading('藥品負擔', ['收費人數', '免收人數', '金額'])

        self.ui.tableWidget_doctor_monthly.setColumnCount(self.ui.tableWidget_doctor_monthly.columnCount()+5)

        self.ui.tableWidget_doctor_monthly.setItem(0, 11, QtWidgets.QTableWidgetItem('合計金額'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 11, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 11).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(0, 12, QtWidgets.QTableWidgetItem('欠卡人數'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 12, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 12).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(0, 13, QtWidgets.QTableWidgetItem('欠卡金額'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 13, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 13).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(0, 14, QtWidgets.QTableWidgetItem('還卡人數'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 14, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 14).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self.ui.tableWidget_doctor_monthly.setItem(0, 15, QtWidgets.QTableWidgetItem('還卡金額'))
        self.ui.tableWidget_doctor_monthly.setSpan(0, 15, 2, 1)
        self.ui.tableWidget_doctor_monthly.item(0, 15).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

        self._set_calendar_heading(v_heading_height)

    def _set_calendar_heading(self, v_heading_height):
        start_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S').date()
        end_date = datetime.datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S').date()
        day_count = (end_date - start_date).days + 1

        calendar_list = []
        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                week_day_name = date_utils.get_weekday_name(date.weekday(), 'zh_TW')
                case_date = date.strftime(f'%m/%d ({week_day_name[2]})')
            except Exception:
                case_date = date.strftime('%m/%d')

            if case_date not in calendar_list:
                calendar_list.append(case_date)

        row_count = len(calendar_list)
        self.ui.tableWidget_doctor_monthly.setRowCount(row_count+1+v_heading_height)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_doctor_monthly.setItem(
                row_no+v_heading_height, 0, QtWidgets.QTableWidgetItem(case_date)
            )
            self.ui.tableWidget_doctor_monthly.item(
                row_no+v_heading_height, 0).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_doctor_monthly.setItem(
            row_count+v_heading_height, 0, QtWidgets.QTableWidgetItem('總計')
        )
        self.ui.tableWidget_doctor_monthly.item(
            row_count+v_heading_height, 0).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        for row_no in range(v_heading_height, self.ui.tableWidget_doctor_monthly.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor_monthly.columnCount()):
                self.ui.tableWidget_doctor_monthly.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_doctor_monthly.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self):
        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                InsType = "健保" AND
                (Injury NOT IN {tuple(nhi_utils.OCCUPATIONAL_INJURY_TYPE)}) AND
                (Share NOT IN ("山地離島")) AND
                (Card IS NOT NULL) AND (LENGTH(cases.Card) > 0) AND (cases.Card != "欠卡")
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_doctor_monthly.rowCount()):
            case_date_item = self.ui.tableWidget_doctor_monthly.item(row_no, 0)
            if case_date_item is None:
                continue

            if case_date in case_date_item.text():
                return row_no

        return None

    def _calculate_data(self):
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '門診資料統計中, 請稍後...', '取消', 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for i, row in enumerate(rows):
            case_date = row['CaseDate'].strftime('%m/%d')
            progress_dialog.setValue(i)
            row_no = self._get_row_no(case_date)
            if row_no is None:
                continue

            ins_type = string_utils.xstr(row['InsType'])
            regist_fee = number_utils.get_integer(row['RegistFee'])
            diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
            drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
            receipt_fee = regist_fee + diag_share_fee + drug_share_fee

            if ins_type == '健保':
                self._increment_field_value(row_no, 1, 1)

            if regist_fee > 0:
                self._increment_field_value(row_no, 2, 1)
            else:
                self._increment_field_value(row_no, 3, 1)

            self._increment_field_value(row_no, 4, regist_fee)

            if diag_share_fee > 0:
                self._increment_field_value(row_no, 5, 1)
            else:
                self._increment_field_value(row_no, 6, 1)

            self._increment_field_value(row_no, 7, diag_share_fee)

            if drug_share_fee > 0:
                self._increment_field_value(row_no, 8, 1)
            else:
                self._increment_field_value(row_no, 9, 1)

            self._increment_field_value(row_no, 10, drug_share_fee)
            self._increment_field_value(row_no, 11, receipt_fee)

        progress_dialog.setValue(row_count)

        for row_no in range(2, self.ui.tableWidget_doctor_monthly.rowCount()):
            item = self.ui.tableWidget_doctor_monthly.item(row_no, 0)
            if item is None:
                continue

            case_date = item.text()
            if case_date == '總計':
                continue

            case_date = f'{self.year}/{case_date[:5]}'

            deposit_count, deposit_fee = self._get_deposit_fee(case_date)
            return_count, return_fee = self._get_return_fee(case_date)
            self._increment_field_value(row_no, 12, deposit_count)
            self._increment_field_value(row_no, 13, deposit_fee)
            self._increment_field_value(row_no, 14, return_count)
            self._increment_field_value(row_no, 15, return_fee)

        progress_dialog.deleteLater()

    def _get_deposit_fee(self, case_date):
        sql = f'''
            SELECT Fee FROM deposit
            WHERE
                DATE(DepositDate) = "{case_date}"
        '''
        rows = self.database.select_record(sql)

        total_deposit_fee = 0
        for row in rows:
            total_deposit_fee += number_utils.get_integer(row['Fee'])

        return len(rows), total_deposit_fee

    def _get_return_fee(self, case_date):
        sql = f'''
            SELECT Fee FROM deposit
            WHERE
                DATE(ReturnDate) = "{case_date}"
        '''
        rows = self.database.select_record(sql)

        total_return_fee = 0
        for row in rows:
            total_return_fee += number_utils.get_integer(row['Fee'])

        return len(rows), total_return_fee

    def _increment_field_value(self, row_no, col_no, value):
        try:
            case_count = number_utils.get_integer(
                self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text()) + value
            self._set_item_data(row_no, col_no, case_count)
        except Exception:
            pass

    def _set_item_data(self, row_no, col_no, value):
        item = self.ui.tableWidget_doctor_monthly.item(row_no, col_no)
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_doctor_monthly.setItem(row_no, col_no, item)
        self.ui.tableWidget_doctor_monthly.item(
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
            f'{start_date}至{end_date}{self.doctor}掛號收費統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor_monthly, None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>掛號收費統計{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _calculate_total(self):
        row_count = self.ui.tableWidget_doctor_monthly.rowCount()
        total_field_row_no = row_count - 1

        for col_no in range(1, self.ui.tableWidget_doctor_monthly.columnCount()):
            total_fee = 0
            for row_no in range(2, row_count-1):
                value = number_utils.get_integer(self.ui.tableWidget_doctor_monthly.item(row_no, col_no).text())
                total_fee += value

            self._set_item_data(total_field_row_no, col_no, total_fee)

    def _print_doctor_monthly_income(self, print_type=None):
        printer_utils.print_doctor_monthly_income(
            self, self.database, self.system_settings, self.start_date, self.end_date, self.doctor,
            self.ui.tableWidget_doctor_monthly, print_type)

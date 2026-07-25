# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtChart
from PyQt5.QtWidgets import QMessageBox, QFileDialog

import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import chart_utils


# 綜合業績報表-週專案統計表 2020.02.22
class StatisticsMultiplePerformanceWeekDoctor(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMultiplePerformanceWeekDoctor, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_DOCTOR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100, 60, 70,
            100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self.open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        if case_key == '':
            return

        self.parent.parent.open_medical_record(case_key, '病歷查詢')

    def start_calculate(self):
        self._calculate_fee()
        # self._plot_chart()

    def _calculate_fee(self):
        self.week_list = date_utils.get_week_list(self.year, self.month)
        self._calculate_doctor(self.week_list)

    def _calculate_doctor(self, week_list):
        if len(self.week_list) <= 0:
            return

        start_date = f'{week_list[0][0]} 00:00:00'
        end_date = f'{week_list[-1][1]} 23:59:59'
        sql = f'''
            SELECT Doctor FROM cases
                LEFT JOIN person ON person.Name = cases.Doctor
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0 AND
                TreatType != "自購" AND
                person.Position IN("醫師", "支援醫師")
            GROUP BY Doctor
        '''
        rows = self.database.select_record(sql)

        doctor_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計醫師業績資料中, 請稍後...', '取消', 0, doctor_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for i, row in zip(range(doctor_count), rows):
            progress_dialog.setValue(i)
            if progress_dialog.wasCanceled():
                break

            doctor = string_utils.xstr(row['Doctor'])
            self._calculate_doctor_week(week_list, i, doctor)

        progress_dialog.setValue(doctor_count)
        progress_dialog.deleteLater()

    def _calculate_doctor_week(self, week_list, i, doctor):
        self.ui.tableWidget_medical_record.setRowCount(
            self.ui.tableWidget_medical_record.rowCount() + len(week_list)
        )
        for week, j in zip(week_list, range(len(week_list))):
            start_date = week[0]
            end_date = week[1]
            row_no = i * len(week_list) + j
            if j == 0:
                self._set_table_item(self.ui.tableWidget_medical_record, row_no, 0, doctor)

            self._set_table_item(self.ui.tableWidget_medical_record, row_no, 1, j+1)
            self._calculate_period(row_no, 2, doctor, start_date, end_date)
            self._calculate_person_count(row_no, 3, doctor, start_date, end_date, '健保')
            self._calculate_avg_period(row_no, 4)
            self._calculate_treat_count(row_no, 5, doctor, start_date, end_date, '內科')
            self._calculate_treat_return(row_no, 6, doctor, start_date, end_date, '內科')
            self._calculate_return_rate(row_no, 7)
            self._calculate_self_amount(row_no, 8, doctor, start_date, end_date)
            self._calculate_avg_amount(row_no, 9)
            self._calculate_visit(row_no, 10, doctor, start_date, end_date, '初診')
            self._calculate_visit(row_no, 11, doctor, start_date, end_date, '複診')
            self._calculate_reservation(row_no, 12, doctor, start_date, end_date)
            self._calculate_reservation_rate(row_no, 13)
            self._calculate_reservation_arrival(row_no, 14, doctor, start_date, end_date)
            self._calculate_reservation_arrival_rate(row_no, 15)

    def _calculate_period(self, row_no, col_no, doctor, start_date, end_date):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey, CaseDate, DATE(CaseDate) as case_date FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                Doctor = "{doctor}"
            GROUP BY case_date, Period, Doctor
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_person_count(self, row_no, col_no, doctor, start_date, end_date, ins_type):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                Doctor = "{doctor}" AND
                InsType = "{ins_type}" AND
                TreatType != "自購"
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_avg_period(self, row_no, col_no):
        total_period = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 2).text())
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 3).text())
        if total_count == 0 or total_period == 0:
            avg_count = 0
        else:
            avg_count = number_utils.round_up(total_count / total_period)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, avg_count)

    def _get_treat_row(self, doctor, start_date, end_date, treat_type):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT PatientKey, CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                Doctor = "{doctor}" AND
                TreatType = "{treat_type}" AND
                TreatType != "自購"
        '''
        rows = self.database.select_record(sql)

        return rows

    def _calculate_treat_count(self, row_no, col_no, doctor, start_date, end_date, treat_type):
        rows = self._get_treat_row(doctor, start_date, end_date, treat_type)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_treat_return(self, row_no, col_no, doctor, start_date, end_date, treat_type):
        rows = self._get_treat_row(doctor, start_date, end_date, treat_type)
        patient_return = 0
        for row in rows:
            case_date = row['CaseDate']
            patient_key = row['PatientKey']
            if case_date is None or patient_key is None:
                continue

            start_return_date = case_date.date() + datetime.timedelta(days=1)
            end_return_date = start_date + datetime.timedelta(days=29)
            sql = f'''
                SELECT CaseKey FROM cases
                WHERE
                    PatientKey = {patient_key} AND
                    CaseDate BETWEEN "{start_return_date}" and "{end_return_date}" AND
                    Doctor = "{doctor}" AND
                    TreatType = "{treat_type}"
            '''
            return_rows = self.database.select_record(sql)
            if len(return_rows) > 0:
                patient_return += 1

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, patient_return)

    def _calculate_return_rate(self, row_no, col_no):
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 5).text())
        total_return = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 6).text())

        if total_count == 0 or total_return == 0:
            return_rate = '0%'
        else:
            return_percent = number_utils.round_up(total_return / total_count * 100)
            return_rate = f'{return_percent}%'

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, return_rate)

    def _calculate_self_amount(self, row_no, col_no, doctor, start_date, end_date):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT Sum(TotalFee) AS TotalAmount FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                Doctor = "{doctor}"
        '''
        rows = self.database.select_record(sql)
        total_amount = number_utils.get_integer(rows[0]['TotalAmount'])

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, total_amount)

    def _calculate_avg_amount(self, row_no, col_no):
        total_period = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 2).text())
        total_amount = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 8).text())
        if total_amount == 0 or total_period == 0:
            avg_amount = 0
        else:
            avg_amount = number_utils.round_up(total_amount / total_period)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, avg_amount)

    def _calculate_visit(self, row_no, col_no, doctor, start_date, end_date, visit):
        start_date, end_date = self._get_datetime_period(start_date, end_date)

        if visit == '初診':
            visit_condition = f'AND Visit = "{visit}"'
        else:
            visit_condition = f'AND (Visit = "{visit}" OR Visit IS NULL)'

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                Doctor = "{doctor}" AND
                InsType IN("健保", "自費") AND
                TreatType != "自購"
                {visit_condition}
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _get_reservation_rows(self, doctor, start_date, end_date, arrival=None):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        arrival_condition = ''
        if arrival:
            arrival_condition = 'AND Arrival="True"'

        sql = f'''
            SELECT ReserveKey FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" and "{end_date}" AND
                Doctor = "{doctor}"
                {arrival_condition}
        '''
        rows = self.database.select_record(sql)

        return rows

    def _calculate_reservation(self, row_no, col_no, doctor, start_date, end_date):
        rows = self._get_reservation_rows(doctor, start_date, end_date)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_reservation_rate(self, row_no, col_no):
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 3).text())
        total_reservation = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 12).text())

        if total_count == 0 or total_reservation == 0:
            reservation_rate = '0%'
        else:
            reservation_percent = number_utils.round_up(total_reservation / total_count * 100)
            reservation_rate = f'{reservation_percent}%'

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, reservation_rate)

    def _calculate_reservation_arrival(self, row_no, col_no, doctor, start_date, end_date):
        rows = self._get_reservation_rows(doctor, start_date, end_date, arrival=True)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_reservation_arrival_rate(self, row_no, col_no):
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 12).text())
        total_arrival = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 14).text())

        if total_count == 0 or total_arrival == 0:
            arrival_rate = '0%'
        else:
            arrival_percent = number_utils.round_up(total_arrival / total_count * 100)
            arrival_rate = f'{arrival_percent}%'

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, arrival_rate)

    @staticmethod
    def _get_datetime_period(start_date, end_date):
        start_date = f'{start_date.year}-{start_date.month}-{start_date.day} 00:00:00'
        end_date = f'{end_date.year}-{end_date.month}-{end_date.day} 23:59:59'

        return start_date, end_date

    @staticmethod
    def _set_table_item(tableWidget, row_no, col_no, data):
        item = QtWidgets.QTableWidgetItem()

        item.setData(QtCore.Qt.EditRole, data)
        tableWidget.setItem(
            row_no, col_no, item
        )
        tableWidget.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    def _calculate_total(self):
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            total = 0
            for col_no in range(2, self.ui.tableWidget_medical_record.columnCount()-1):
                item = self.ui.tableWidget_medical_record.item(row_no, col_no)
                if item is None:
                    continue

                total += number_utils.get_integer(item.text())

            if total > 0:
                self._set_table_item(
                    self.ui.tableWidget_medical_record,
                    row_no, self.ui.tableWidget_medical_record.columnCount()-1, total
                )

        self._set_table_item(self.ui.tableWidget_medical_record, 5, 0, '小計')
        for col_no in range(2, self.ui.tableWidget_medical_record.columnCount()):
            total = 0
            for row_no in range(5):
                item = self.ui.tableWidget_medical_record.item(row_no, col_no)
                if item is None:
                    continue

                total += number_utils.get_integer(item.text())

            self._set_table_item(self.ui.tableWidget_medical_record, 5, col_no, total)

    def _plot_chart(self):
        while self.ui.horizontalLayout_chart.count():
            item = self.ui.horizontalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_project_chart()

    def _plot_project_chart(self):
        set0 = QtChart.QBarSet('金額')
        categories = []
        for col_no in range(2, self.ui.tableWidget_medical_record.columnCount()-1):
            header = self.ui.tableWidget_medical_record.horizontalHeaderItem(col_no).text()
            value = number_utils.get_integer(self.ui.tableWidget_medical_record.item(5, col_no).text())
            set0 << value
            categories.append(header)

        series = QtChart.QBarSeries()
        series.append(set0)

        chart_utils.plot_chart('專案收入統計表', series, categories, self.ui.horizontalLayout_chart)

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}醫師掛號費優待統計表.xlsx',
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

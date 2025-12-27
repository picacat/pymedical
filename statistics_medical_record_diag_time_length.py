
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart
from PyQt5.QtWidgets import QMessageBox, QFileDialog

import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils
from libs import date_utils


# 醫師統計 2019.05.02
class StatisticsMedicalRecordDiagTimeLength(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMedicalRecordDiagTimeLength, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.ins_type = args[4]
        self.doctor = args[5]
        self.weekday_list = args[6]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MEDICAL_RECORD_DIAG_TIME_LENGTH, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            130, 70, 90, 60, 90, 90, 90, 90, 90, 90, 90, 90, 90, 100]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self._open_medical_record)

    def _open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_medical_record.setRowCount(0)
        self._calculate_data()

    def _calculate_data(self):
        self._read_data()
        self._plot_chart()

    def _read_data(self):
        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = f' AND InsType = "{self.ins_type}"'

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        weekday_list_condition = case_utils.get_weekday_list_sql(self.weekday_list)

        sql = f'''
            SELECT
                CaseKey, CaseDate, PatientKey, Name, InsType, TreatType,
                Doctor, DoctorDate, ChargeDate, Register
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {weekday_list_condition}
                {ins_type_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row['CaseKey'])
        registration_time = string_utils.xstr(row['CaseDate'].strftime('%H:%M'))

        try:
            diag_start_date = case_utils.get_case_extend(self.database, case_key, '病歷登錄時間')
            if diag_start_date is not None:
                diag_start_date = date_utils.str_to_datetime(diag_start_date)
            else:
                diag_start_date = row['CaseDate']

            diag_start_time = diag_start_date.strftime('%H:%M')
            diag_start_time_delta = diag_start_date - row['CaseDate']
            wait_seconds = datetime.timedelta(seconds=diag_start_time_delta.total_seconds())
            wait_time_cost = f'{wait_seconds.seconds // 60}分鐘'
        except Exception:
            diag_start_time = ''
            wait_time_cost = ''

        try:
            diag_finish_time = string_utils.xstr(row['DoctorDate'].strftime('%H:%M'))
            diag_time_delta = row['DoctorDate'] - diag_start_date
            wait_seconds = datetime.timedelta(seconds=diag_time_delta.total_seconds())
            diag_time_cost = f'{wait_seconds.seconds // 60}分鐘'
        except Exception:
            diag_finish_time = ''
            diag_time_cost = ''

        try:
            charge_finish_time = string_utils.xstr(row['ChargeDate'].strftime('%H:%M'))
            charge_time_delta = row['ChargeDate'] - row['DoctorDate']
            wait_seconds = datetime.timedelta(seconds=charge_time_delta.total_seconds())
            charge_time_cost = f'{wait_seconds.seconds // 60}分鐘'
        except (AttributeError, TypeError):
            charge_finish_time = ''
            charge_time_cost = ''

        medical_record = [
            case_key,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Doctor']),
            registration_time,
            diag_start_time,
            diag_finish_time,
            charge_finish_time,
            wait_time_cost,
            diag_time_cost,
            charge_time_cost,
            string_utils.xstr(row['Register']),
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [2]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出醫師門診看診時間統計表",
            f'{start_date}至{end_date}{self.doctor}醫師門診看診時間統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0], [2],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>醫師人次統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_wait_time_cost_chart()
        self._plot_diag_time_cost_chart()
        self._show_summary()

    def _plot_wait_time_cost_chart(self):
        series = QtChart.QLineSeries()

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, 11)
            if item is None:
                continue

            diag_cost_time = item.text().strip('分鐘')
            series.append(row_no, number_utils.get_integer(diag_cost_time))

        chart = QtChart.QChart()
        chart.legend().hide()
        chart.addSeries(series)
        chart.createDefaultAxes()

        chart.setTitle('候診時間花費統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(480)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_diag_time_cost_chart(self):
        series = QtChart.QLineSeries()

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, 12)
            if item is None:
                continue

            charge_cost_time = item.text().strip('分鐘')
            series.append(row_no, number_utils.get_integer(charge_cost_time))

        chart = QtChart.QChart()
        chart.legend().hide()
        chart.addSeries(series)
        chart.createDefaultAxes()

        chart.setTitle('診療時間花費統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(480)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _get_total_times(self, field_no, treat_type=None):
        total_times = 0
        total_medical_records = 0
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, field_no)
            treat_type_item = self.ui.tableWidget_medical_record.item(row_no, 5)
            if item is None:
                continue

            if treat_type is not None:
                if treat_type_item is None:
                    continue
                elif treat_type_item.text() != treat_type:
                    continue

            cost_time = item.text().strip('分鐘')
            total_times += number_utils.get_integer(cost_time)
            total_medical_records += 1

        return total_times, total_medical_records

    def _show_summary(self):
        total_diag_times, total_medical_records = self._get_total_times(12)
        if total_medical_records <= 0:
            return

        total_avg_diag_times = total_diag_times / total_medical_records

        total_internal_times, total_internal_medical_records = self._get_total_times(12, '內科')
        try:
            total_avg_internal_times = total_internal_times / total_internal_medical_records
        except Exception:
            total_avg_internal_times = 0

        total_acupuncture_times, total_acupuncture_medical_records = self._get_total_times(12, '針灸治療')
        try:
            total_avg_acupuncture_times = total_acupuncture_times / total_acupuncture_medical_records
        except Exception:
            total_avg_acupuncture_times = 0

        total_massage_times, total_massage_medical_records = self._get_total_times(12, '傷科治療')
        try:
            total_avg_massage_times = total_massage_times / total_massage_medical_records
        except Exception:
            total_avg_massage_times = 0

        label_summary = QtWidgets.QLabel()
        label_summary.setText(
            f'''
                <center>
                {self.doctor}醫師<br>
                </center>
                平均看診時間 = ({total_diag_times} / {total_medical_records}) = <b>
                {total_avg_diag_times: .2f}分鐘</b><br>
                內科平均看診時間 = ({total_internal_times} / {total_internal_medical_records}) = <b>
                {total_avg_internal_times: .2f}分鐘</b><br>
                針灸平均看診時間 = ({total_acupuncture_times} / {total_acupuncture_medical_records}) = <b>
                {total_avg_acupuncture_times: .2f}分鐘</b><br>
                傷科平均看診時間 = ({total_massage_times} / {total_massage_medical_records}) = <b>
                {total_avg_massage_times: .2f}分鐘</b><br>
                <br>
            '''
        )

        self.ui.verticalLayout_chart.addWidget(label_summary)

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import export_utils
from libs import system_utils


# 醫師未回診率統計 2020.04.07
class StatisticsNoReturnRateDoctor(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsNoReturnRateDoctor, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.no_return_start_date = args[4]
        self.no_return_end_date = args[5]
        self.ins_type = args[6]
        self.treat_type = args[7]
        self.visit = args[8]
        self.doctor = args[9]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_NO_RETURN_RATE_DOCTOR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_return_rate_doctor = class_utils.get_table_widget(
            self.ui.tableWidget_return_rate_doctor, self.database)
        self._set_table_width()
        self.table_widget_return_rate_doctor.set_column_hidden([0])

    def _set_table_width(self):
        width = [
            100,
            130, 70, 90, 70, 90, 340, 90, 140, 140]
        self.table_widget_return_rate_doctor.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_return_rate_doctor.doubleClicked.connect(self._open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_return_rate_doctor.setRowCount(0)
        self._calculate_data()

    def _calculate_data(self):
        self._read_data()
        self._calculate_return_rate()
        self._plot_chart()
        self._show_no_return_rate()
        self._filter_row()

    def _read_data(self):
        self.ins_type_condition = ''
        if self.ins_type != '全部':
            self.ins_type_condition = f' AND cases.InsType = "{self.ins_type}"'

        self.treat_type_condition = ''
        if self.treat_type == '內科':
            self.treat_type_condition = '''
                AND TreatType IN ("內科")
            '''
        elif self.treat_type == '針灸治療':
            self.treat_type_condition = '''
                AND TreatType IN ("針灸治療", "電針治療", "一般針灸", "電針", "一般針灸合併一般傷科")
            '''
        elif self.treat_type == '複雜針灸':
            self.treat_type_condition = '''
                AND (TreatType LIKE "%中度%" OR TreatType LIKE "%高度%") AND TreatType LIKE "%針灸%"
            '''
        elif self.treat_type == '傷科治療':
            self.treat_type_condition = '''
                AND TreatType IN ("傷科治療", "一般傷科", "一般針灸合併一般傷科")
            '''
        elif self.treat_type == '複雜傷科':
            self.treat_type_condition = '''
                AND (TreatType LIKE "%中度%" OR TreatType LIKE "%高度%") AND TreatType LIKE "%傷科%"
            '''

        self.visit_condition = ''
        if self.visit != '全部':
            self.visit_condition = f' AND Visit = "{self.visit}"'

        self.doctor_condition = ''
        if self.doctor != '全部':
            self.doctor_condition = f' AND Doctor = "{self.doctor}"'

        sql = f'''
            SELECT
                CaseKey, CaseDate, cases.PatientKey, cases.Name, Visit, TreatType, DiseaseName1, Doctor,
                Telephone, Cellphone
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Doctor IS NOT NULL
                {self.ins_type_condition}
                {self.treat_type_condition}
                {self.visit_condition}
                {self.doctor_condition}
            GROUP BY cases.PatientKey
            ORDER BY CaseDate
        '''
        self.table_widget_return_rate_doctor.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        return_days_list = self._get_no_return_days_list(row)

        phone_list = []
        if string_utils.xstr(row['Telephone']) != '':
            phone_list.append(string_utils.xstr(row['Telephone']))
        if string_utils.xstr(row['Cellphone']) != '':
            phone_list.append(string_utils.xstr(row['Cellphone']))

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Visit']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(row['Doctor']),
            ', '.join(return_days_list),
            ', '.join(phone_list),
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_return_rate_doctor.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [2]:
                self.ui.tableWidget_return_rate_doctor.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [4]:
                self.ui.tableWidget_return_rate_doctor.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _get_no_return_days_list(self, medical_row):
        patient_key = medical_row['PatientKey']
        start_date = self.no_return_start_date
        end_date = self.no_return_end_date
        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key}
                {self.doctor_condition}
            GROUP BY DATE(CaseDate)
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return_days_list = []
        for row in rows:
            return_days_list.append(string_utils.xstr(row['CaseDate'].date()))

        return return_days_list

    def _filter_row(self):
        table_widget_no_return = self.ui.tableWidget_return_rate_doctor
        for row_no in range(table_widget_no_return.rowCount(), -1, -1):
            return_list = table_widget_no_return.item(row_no, 8)
            if return_list is not None and return_list.text() != '':
                table_widget_no_return.removeRow(row_no)

    def _calculate_return_rate(self):
        self.denominator = self.ui.tableWidget_return_rate_doctor.rowCount()

        self.numerator = 0
        for row_no in range(self.ui.tableWidget_return_rate_doctor.rowCount()):
            return_date = self.ui.tableWidget_return_rate_doctor.item(row_no, 8)
            if return_date is not None and return_date.text() != '':
                continue

            self.numerator += 1

    def _show_no_return_rate(self):
        label_return_rate = QtWidgets.QLabel()

        if self.denominator == 0:
            no_return_rate = 0
        else:
            no_return_rate = self.numerator / self.denominator * 100

        label_return_rate.setText(
            f'''
                <center>
                    {self.doctor}醫師未回診率 = 歸戶未回診人數 / 歸戶總人數 <br>
                    {self.numerator} / {self.denominator} = <b>{no_return_rate: .2f}%</b>
                </center>
            '''
        )

        self.ui.verticalLayout_chart.addWidget(label_return_rate)

    def _plot_chart(self):
        series = QtChart.QPieSeries()
        series.append('未回診', self.numerator)
        series.append('回診', self.denominator - self.numerator)

        slice = series.slices()[0]
        slice.setExploded()
        slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle(f'{self.doctor}醫師未回診率')
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(450)
        self.chartView.setFixedHeight(400)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}{self.doctor}醫師未回診率統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_return_rate_doctor, [0]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>醫師未回診率統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _open_medical_record(self):
        case_key = self.table_widget_return_rate_doctor.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)

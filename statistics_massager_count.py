
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


# 推拿師人數統計 2020.11.03
class StatisticsMassagerCount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMassagerCount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.massager = args[6]
        self.only_traditional_massage = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MASSAGER_COUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_massager_count = class_utils.get_table_widget(
            self.ui.tableWidget_massager_count, self.database
        )
        self.table_widget_massager = class_utils.get_table_widget(
            self.ui.tableWidget_massager, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            130,
            85, 85, 85, 85, 85, 85,
        ]
        self.table_widget_massager_count.set_table_heading_width(width)
        self.table_widget_massager.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_date_excel.clicked.connect(self._export_to_date_excel)
        self.ui.toolButton_export_massager_excel.clicked.connect(self._export_to_massager_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_massager_count.setRowCount(0)
        self.ui.tableWidget_massager.setRowCount(0)
        self._set_statistics_table_heading()
        self._set_statistics_massager_table_heading()
        self._calculate_data()

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
        self.ui.tableWidget_massager_count.setRowCount(row_count + 1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_massager_count.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date)
            )

        self.ui.tableWidget_massager_count.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem('總計')
        )

    def _set_statistics_massager_table_heading(self):
        massager_list = []
        rows = self._read_data(group_by_massager=True)
        for row in rows:
            massager = string_utils.xstr(row['Massager'])
            if massager not in massager_list:
                massager_list.append(massager)

        row_count = len(massager_list)
        self.ui.tableWidget_massager.setRowCount(row_count + 1)

        for row_no, massager in enumerate(massager_list):
            self.ui.tableWidget_massager.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(massager)
            )

        self.ui.tableWidget_massager.setItem(
            row_count, 0, QtWidgets.QTableWidgetItem('總計')
        )

    def _calculate_data(self):
        self._reset_data()
        rows = self._read_data()
        self._calculate_ins_count(rows)
        self._calculate_massager_ins_count(rows)

        self._calculate_period(rows)
        self._calculate_massager_period(rows)

        self._calculate_subtotal()
        self._calculate_massager_subtotal()

        self._calculate_total()
        self._calculate_massager_total()

        self._plot_chart()

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_massager_count.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager_count.columnCount()):
                self.ui.tableWidget_massager_count.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_massager_count.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

        for row_no in range(self.ui.tableWidget_massager.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager.columnCount()):
                self.ui.tableWidget_massager.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_massager.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self, group_by_massager=False):
        only_traditional_massage_condition = ''
        if self.only_traditional_massage:
            only_traditional_massage_condition = ' AND TreatType = "民俗調理"'

        period_condition = ''
        if self.period != '全部':
            period_condition = f' AND Period = "{self.period}"'

        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = f' AND InsType = "{self.ins_type}"'

        massager_condition = ''
        if self.massager != '全部':
            massager_condition = f' AND Massager = "{self.massager}"'

        group_condition = ''
        if group_by_massager:
            group_condition = ' GROUP BY Massager'

        massage_fee_condition = ''
        if self.system_settings.field('院所名稱') == '耀康中醫診所':
            massage_fee_condition = ' AND SMassageFee > 0'

        sql = f'''
            SELECT
                CaseKey, CaseDate, PatientKey, Period, InsType, TreatType, Continuance, Massager, SMassageFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Massager IS NOT NULL AND LENGTH(Massager) > 0
                {massage_fee_condition}
                {only_traditional_massage_condition}
                {period_condition}
                {ins_type_condition}
                {massager_condition}
            {group_condition}
            ORDER BY CaseDate, CaseKey
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_massager_count.rowCount()):
            case_date_field = self.ui.tableWidget_massager_count.item(row_no, 0)
            if case_date_field is None:
                continue

            if case_date == case_date_field.text():
                return row_no

        return None

    def _get_massager_row_no(self, massager):
        for row_no in range(self.ui.tableWidget_massager.rowCount()):
            massager_field = self.ui.tableWidget_massager.item(row_no, 0)
            if massager_field is None:
                continue

            if massager == massager_field.text():
                return row_no

        return None

    def _is_double_rows(self, case_date, patient_key):
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                DATE(CaseDate) = "{case_date}" AND
                PatientKey = {patient_key} AND
                InsType = "自費" AND
                TreatType = "民俗調理"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return True, rows[0]['CaseKey']
        else:
            return False, None

    def _get_col_no(self, row):
        case_key = row['CaseKey']
        case_date = row['CaseDate'].strftime('%Y-%m-%d')
        ins_type = string_utils.xstr(row['InsType'])
        massage_fee = number_utils.get_integer(row['SMassageFee'])
        patient_key = row['PatientKey']

        if self.system_settings.field('院所名稱') == '耀康中醫診所':
            if massage_fee == 50:
                col_no = 1
            else:
                col_no = 2
        elif ins_type == '健保':
            is_double_rows, self_case_key = self._is_double_rows(case_date, patient_key)
            if is_double_rows:
                col_no = 2
                self.counted_case_key.append(self_case_key)
            else:
                col_no = 1
        else:
            if case_key in self.counted_case_key:
                col_no = None
            else:
                col_no = 2

        return col_no

    def _calculate_ins_count(self, rows):
        self.counted_case_key = []
        for row in rows:
            case_date = row['CaseDate'].strftime('%Y-%m-%d')

            col_no = self._get_col_no(row)
            if col_no is None:
                continue

            row_no = self._get_row_no(case_date)
            ins_count = self.ui.tableWidget_massager_count.item(row_no, col_no)
            if ins_count is None:
                ins_count = 0
            else:
                ins_count = number_utils.get_integer(ins_count.text())

            self._set_item_data(row_no, col_no, string_utils.xstr(ins_count + 1))

    def _calculate_massager_ins_count(self, rows):
        self.counted_case_key = []

        for row in rows:
            massager = string_utils.xstr(row['Massager'])

            col_no = self._get_col_no(row)
            if col_no is None:
                continue

            row_no = self._get_massager_row_no(massager)
            ins_count = self.ui.tableWidget_massager.item(row_no, col_no)
            if ins_count is None:
                ins_count = 0
            else:
                ins_count = number_utils.get_integer(ins_count.text())

            self._set_massager_item_data(row_no, col_no, string_utils.xstr(ins_count + 1))

    def _calculate_period(self, rows):
        self.counted_case_key = []

        for row in rows:
            case_date = row['CaseDate'].strftime('%Y-%m-%d')
            period = string_utils.xstr(row['Period'])

            col_no = self._get_col_no(row)
            if col_no is None:
                continue

            col_no = 3
            if period == '早班':
                col_no = 3
            elif period == '午班':
                col_no = 4
            elif period == '晚班':
                col_no = 5

            row_no = self._get_row_no(case_date)
            period_count = self.ui.tableWidget_massager_count.item(row_no, col_no)
            if period_count is None:
                period_count = 0
            else:
                period_count = number_utils.get_integer(period_count.text())

            self._set_item_data(row_no, col_no, string_utils.xstr(period_count + 1))

    def _calculate_massager_period(self, rows):
        self.counted_case_key = []

        for row in rows:
            massager = string_utils.xstr(row['Massager'])
            period = string_utils.xstr(row['Period'])

            col_no = self._get_col_no(row)
            if col_no is None:
                continue

            col_no = 3
            if period == '早班':
                col_no = 3
            elif period == '午班':
                col_no = 4
            elif period == '晚班':
                col_no = 5

            row_no = self._get_massager_row_no(massager)
            period_count = self.ui.tableWidget_massager.item(row_no, col_no)
            if period_count is None:
                period_count = 0
            else:
                period_count = number_utils.get_integer(period_count.text())

            self._set_massager_item_data(row_no, col_no, string_utils.xstr(period_count + 1))

    def _set_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_massager_count.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_massager_count.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _set_massager_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_massager.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_massager.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _calculate_subtotal(self):
        for row_no in range(self.ui.tableWidget_massager_count.rowCount()):
            period1 = number_utils.get_integer(self.ui.tableWidget_massager_count.item(row_no, 3).text())
            period2 = number_utils.get_integer(self.ui.tableWidget_massager_count.item(row_no, 4).text())
            period3 = number_utils.get_integer(self.ui.tableWidget_massager_count.item(row_no, 5).text())
            self._set_item_data(row_no, 6, string_utils.xstr(period1 + period2 + period3))

    def _calculate_massager_subtotal(self):
        for row_no in range(self.ui.tableWidget_massager.rowCount()):
            period1 = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, 3).text())
            period2 = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, 4).text())
            period3 = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, 5).text())
            self._set_massager_item_data(row_no, 6, string_utils.xstr(period1 + period2 + period3))

    def _calculate_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_massager_count.columnCount())]
        for row_no in range(self.ui.tableWidget_massager_count.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager_count.columnCount()):
                value = number_utils.get_integer(self.ui.tableWidget_massager_count.item(row_no, col_no).text())
                total_list[col_no] += value

        row_no = self.ui.tableWidget_massager_count.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_item_data(
                row_no, col_no, string_utils.xstr(total_list[col_no])
            )

    def _calculate_massager_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_massager.columnCount())]
        for row_no in range(self.ui.tableWidget_massager.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager.columnCount()):
                value = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, col_no).text())
                total_list[col_no] += value

        row_no = self.ui.tableWidget_massager.rowCount() - 1
        for col_no in range(1, len(total_list)):
            self._set_massager_item_data(
                row_no, col_no, string_utils.xstr(total_list[col_no])
            )

    def _export_to_date_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            '{0}至{1}{2}推拿人次統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.massager
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager_count, None,
            [1, 2, 3, 4, 5, 6],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>推拿人次統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _export_to_massager_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            '{0}至{1}{2}推拿師父人次統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.massager
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager, None,
            [1, 2, 3, 4, 5, 6],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>推拿師父人次統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_massager_count_chart()
        self._plot_massager_chart()

    def _plot_massager_count_chart(self):
        series = QtChart.QBarSeries()

        treat_type = ['健保', '自費', '早班', '午班', '晚班']
        col_no_list = [1, 2, 3, 4, 5]

        set_list = []
        for i in range(len(treat_type)):
            set_list.append(QtChart.QBarSet(treat_type[i]))
            set_list[i] << number_utils.get_integer(
                self.ui.tableWidget_massager_count.item(
                    self.ui.tableWidget_massager_count.rowCount() - 1, col_no_list[i]).text()
            )
            series.append(set_list[i])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('推拿人數統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['推拿人數']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(600)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_massager_chart(self):
        series = QtChart.QPieSeries()
        for row_no in range(self.ui.tableWidget_massager.rowCount() - 1):
            massager_item = self.ui.tableWidget_massager.item(row_no, 0)
            if massager_item is None:
                massager_name = '空白'
                total_count = 0
            else:
                massager_name = massager_item.text()
                total_count = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, 6).text())

            series.append(massager_name, total_count)

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('推拿師父人數統計表')
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(600)
        chartView.setFixedHeight(450)
        self.ui.verticalLayout_chart.addWidget(chartView)

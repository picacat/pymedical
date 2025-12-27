
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


# 推拿師收入統計 2020.11.04
class StatisticsMassagerIncome(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMassagerIncome, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MASSAGER_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_massager_income = class_utils.get_table_widget(
            self.ui.tableWidget_massager_income, self.database
        )
        self.table_widget_massager = class_utils.get_table_widget(
            self.ui.tableWidget_massager, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            130,
            100, 100,
        ]
        self.table_widget_massager_income.set_table_heading_width(width)
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
        self.ui.tableWidget_massager_income.setRowCount(0)
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
        self.ui.tableWidget_massager_income.setRowCount(row_count + 1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_massager_income.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date)
            )

        self.ui.tableWidget_massager_income.setItem(
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
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            '門診收入統計中, 請稍後...', '取消', 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self._calculate_income(rows)
        self._calculate_massager_income(rows)

        self._calculate_subtotal()
        self._calculate_massager_subtotal()

        self._calculate_total()
        self._calculate_massager_total()
        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

        self._plot_chart()

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_massager_income.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager_income.columnCount()):
                self.ui.tableWidget_massager_income.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_massager_income.item(
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
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        massager_condition = ''
        if self.massager != '全部':
            massager_condition = f' AND Massager = "{self.massager}"'

        group_condition = ''
        if group_by_massager:
            group_condition = ' GROUP BY Massager'

        sql = f'''
            SELECT
                CaseKey, Name, CaseDate, SMassageFee, Massager
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Massager IS NOT NULL AND LENGTH(Massager) > 0
                {only_traditional_massage_condition}
                {period_condition}
                {ins_type_condition}
                {massager_condition}
            {group_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, case_date):
        for row_no in range(self.ui.tableWidget_massager_income.rowCount()):
            case_date_field = self.ui.tableWidget_massager_income.item(row_no, 0)
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

    def _calculate_income(self, rows):
        for row in rows:
            case_date = row['CaseDate'].strftime('%Y-%m-%d')
            row_no = self._get_row_no(case_date)
            self.progress_dialog.setValue(row_no)
            massage_fee = self._get_cell_fee(row_no, 1) + number_utils.get_integer(row['SMassageFee'])
            total_fee = massage_fee

            self._set_item_data(row_no, 1, string_utils.xstr(massage_fee))
            self._set_item_data(row_no, 2, string_utils.xstr(total_fee))

    def _calculate_massager_income(self, rows):
        for row in rows:
            massager = string_utils.xstr(row['Massager'])
            row_no = self._get_massager_row_no(massager)
            self.progress_dialog.setValue(row_no)
            massage_fee = self._get_massager_cell_fee(row_no, 1) + number_utils.get_integer(row['SMassageFee'])
            total_fee = massage_fee

            self._set_massager_item_data(row_no, 1, string_utils.xstr(massage_fee))
            self._set_massager_item_data(row_no, 2, string_utils.xstr(total_fee))

    def _get_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_massager_income.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _get_massager_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_massager.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _set_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_massager_income.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_massager_income.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_massager_income.item(row_no, col_no).setForeground(
                QtGui.QColor('red')
            )

    def _set_massager_item_data(self, row_no, col_no, data):
        self.ui.tableWidget_massager.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_massager.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_massager.item(row_no, col_no).setForeground(
                QtGui.QColor('red')
            )

    def _calculate_subtotal(self):
        subtotal_field_no = 2

        for row_no in range(self.ui.tableWidget_massager_income.rowCount()):
            subtotal = 0
            for col_no in range(1, subtotal_field_no):
                subtotal += number_utils.get_integer(
                    self.ui.tableWidget_massager_income.item(row_no, col_no).text()
                )

            self._set_item_data(row_no, subtotal_field_no, string_utils.xstr(subtotal))

    def _calculate_massager_subtotal(self):
        subtotal_field_no = 2

        for row_no in range(self.ui.tableWidget_massager.rowCount()):
            subtotal = 0
            for col_no in range(1, subtotal_field_no):
                subtotal += number_utils.get_integer(
                    self.ui.tableWidget_massager.item(row_no, col_no).text()
                )

            self._set_massager_item_data(row_no, subtotal_field_no, string_utils.xstr(subtotal))

    def _calculate_total(self):
        total_list = [0 for i in range(self.ui.tableWidget_massager_income.columnCount())]
        for row_no in range(self.ui.tableWidget_massager_income.rowCount()):
            for col_no in range(1, self.ui.tableWidget_massager_income.columnCount()):
                value = number_utils.get_integer(self.ui.tableWidget_massager_income.item(row_no, col_no).text())
                total_list[col_no] += value

        row_no = self.ui.tableWidget_massager_income.rowCount() - 1
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
            '{0}至{1}{2}推拿師收入統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.massager
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager_income,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>推拿師收入統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _export_to_massager_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            '{0}至{1}{2}推拿師個別收入統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.massager
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_massager,
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>推拿師個別收入統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(1)
            if item is None:
                break

            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_income_chart()
        self._plot_massager_income_chart()

    def _plot_income_chart(self):
        case_date_list = []
        for row_no in range(self.ui.tableWidget_massager_income.rowCount()):
            case_date_field = self.ui.tableWidget_massager_income.item(row_no, 0)
            if case_date_field is None:
                continue

            case_date = case_date_field.text()
            if case_date == '總計':
                continue

            case_date_list.append(case_date)

        series = QtChart.QBarSeries()
        bar_set = []
        for i in range(len(case_date_list)):
            case_date = case_date_list[i]
            row_no = self._get_row_no(case_date)
            subtotal = number_utils.get_integer(
                self.ui.tableWidget_massager_income.item(row_no, 2).text()
            )
            bar_set.append(QtChart.QBarSet(case_date_list[i][8:10]))
            bar_set[i].setColor(QtGui.QColor('green'))
            bar_set[i] << subtotal
            series.append([bar_set[i]])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('推拿收入統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['推拿收入']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        # chart.legend().setVisible(True)
        # chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(750)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_massager_income_chart(self):
        series = QtChart.QPieSeries()
        for row_no in range(self.ui.tableWidget_massager.rowCount() - 1):
            massager_item = self.ui.tableWidget_massager.item(row_no, 0)
            if massager_item is None:
                massager_name = '空白'
                total_income = 0
            else:
                massager_name = massager_item.text()
                total_income = number_utils.get_integer(self.ui.tableWidget_massager.item(row_no, 2).text())

            series.append(massager_name, total_income)

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('推拿師父收入統計表')
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(750)
        chartView.setFixedHeight(450)
        self.ui.verticalLayout_chart.addWidget(chartView)

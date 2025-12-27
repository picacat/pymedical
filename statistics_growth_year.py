# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtChart
import datetime

from libs import class_utils
from libs import ui_utils
from libs import number_utils
from libs import system_utils


# 業績成長統計-年統計 2023.04.25
class StatisticsGrowthYear(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsGrowthYear, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_GROWTH_YEAR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            150, 100, 100,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self._calculate_ins_data()
        self._plot_chart()

    def _calculate_ins_data(self):
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
                    TreatType NOT IN ("開立證明", "自購")
            '''
            rows = self.database.select_record(sql)
            self_count = rows[0]['Count']

            row_no = self.ui.tableWidget_medical_record.rowCount()
            self.ui.tableWidget_medical_record.setRowCount(row_no + 1)

            medical_record_count = [f'{self.year}年{month:0>2}月', ins_count, self_count]

            for col_no, data in enumerate(medical_record_count):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, data)
                self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)
                if col_no in [0]:
                    self.ui.tableWidget_medical_record.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )
                elif col_no in [1, 2]:
                    self.ui.tableWidget_medical_record.item(row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

        progress_dialog.setValue(max_month)
        progress_dialog.deleteLater()

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_ins_month_chart()
        self._plot_self_month_chart()

    def _plot_ins_month_chart(self):
        series = QtChart.QBarSeries()

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            bar_set = []
            month = self.ui.tableWidget_medical_record.item(row_no, 0).text()[5:8]
            ins_count = number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 1).text()
            )
            bar_set.append(QtChart.QBarSet(month))
            # bar_set[0].setColor(QtGui.QColor('green'))
            bar_set[0] << ins_count
            series.append([bar_set[0]])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('健保人數統計')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['健保人數']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(1200)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_self_month_chart(self):
        series = QtChart.QBarSeries()

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            bar_set = []
            month = self.ui.tableWidget_medical_record.item(row_no, 0).text()[5:8]
            self_count = number_utils.get_integer(
                self.ui.tableWidget_medical_record.item(row_no, 2).text()
            )
            bar_set.append(QtChart.QBarSet(month))
            # bar_set[0].setColor(QtGui.QColor('green'))
            bar_set[0] << self_count
            series.append([bar_set[0]])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('自費人數統計')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['自費人數']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(1200)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

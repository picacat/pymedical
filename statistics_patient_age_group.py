# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QPainter
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import system_utils


# 病患年齡分佈統計 2025-04-23
class StatisticsPatientAgeGroup(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsPatientAgeGroup, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.sql = None

        self._set_ui()
        self._set_signal()

        self._calculate_age_group()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_PATIENT_AGE_GROUP, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_age_group = class_utils.get_table_widget(
            self.ui.tableWidget_age_group, self.database)
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self._calculate_age_group)
        self.ui.action_close.triggered.connect(self.close_form)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [200, 100]
        self.table_widget_age_group.set_table_heading_width(width)

    def _calculate_age_group(self):
        sql = '''
        SELECT
            CASE
                WHEN age BETWEEN 0 AND 10 THEN '0-10'
                WHEN age BETWEEN 11 AND 20 THEN '11-20'
                WHEN age BETWEEN 21 AND 30 THEN '21-30'
                WHEN age BETWEEN 31 AND 40 THEN '31-40'
                WHEN age BETWEEN 41 AND 50 THEN '41-50'
                WHEN age BETWEEN 51 AND 60 THEN '51-60'
                WHEN age BETWEEN 61 AND 70 THEN '61-70'
                WHEN age BETWEEN 71 AND 80 THEN '71-80'
                WHEN age BETWEEN 81 AND 90 THEN '81-90'
                WHEN age BETWEEN 91 AND 100 THEN '91-100'
                ELSE '>100↑'
            END AS age_group,
            COUNT(*) AS total
            FROM (
            SELECT
                TIMESTAMPDIFF(YEAR, Birthday, CURDATE()) AS age
            FROM patient
            WHERE Birthday IS NOT NULL
            ) AS derived
            GROUP BY age_group
            ORDER BY MIN(age);
        '''

        rows = self.database.select_record(sql)
        self.ui.tableWidget_age_group.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            self.ui.tableWidget_age_group.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row['age_group'])))

            item = QtWidgets.QTableWidgetItem(str(row['total']))
            item.setTextAlignment(QtCore.Qt.AlignRight)
            self.ui.tableWidget_age_group.setItem(row_no, 1, item)

        self.create_bar_chart(rows)

    def create_bar_chart(self, data_rows):
        # 清除舊的 chart（若有）
            # 刪除舊圖表（如果已經有）
        for i in reversed(range(self.ui.horizontalLayout_age_group.count())):
            item = self.ui.horizontalLayout_age_group.itemAt(i)
            widget = item.widget()
            if widget and widget != self.ui.tableWidget_age_group:
                widget.setParent(None)

        # 統計總次數
        total = sum([row['total'] for row in data_rows])

        # 建立 QBarSet
        bar_set = QBarSet("人數")
        contents = []
        for row in data_rows:
            contents.append(row['age_group'])
            bar_set.append(row['total'])

        # 建立 QBarSeries 並加進 QBarSet
        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)  # 顯示數字
        series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)  # 顯示在條外側

        # 建立 Chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("病患年齡分佈圖")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        # 分類軸（Y軸）
        axis_y = QBarCategoryAxis()
        axis_y.append(contents)
        chart.setAxisX(axis_y, series)
        axis_y.setLabelsAngle(-30)  # 或 -45 看效果

        # 數值軸（X軸）
        axis_x = QValueAxis()
        axis_x.setRange(0, max(row['total'] for row in data_rows) + 1)
        axis_x.setTitleText("人數")
        chart.setAxisY(axis_x, series)

        # 建立 Chart View
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        # 加入 layout（在 tableWidget_age_group 右邊）
        self.ui.horizontalLayout_age_group.addWidget(chart_view)

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtChart

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import system_utils
from libs import chart_utils
from libs import case_utils


# 綜合業績報表-週專案統計表 2020.02.22
class StatisticsMultiplePerformanceWeekProject(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMultiplePerformanceWeekProject, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_PROJECT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )

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
        self._plot_chart()

    def _set_fee_data_row_header(self, project_list):
        column_header = ['週次', '日期'] + project_list + ['總計']

        self.ui.tableWidget_medical_record.setColumnCount(len(column_header))
        self.ui.tableWidget_medical_record.setHorizontalHeaderLabels(column_header)

        width = [55, 130] + [100 for _ in range(len(project_list))] + [100]
        self.table_widget_medical_record.set_table_heading_width(width)

    def _calculate_fee(self):
        self.ui.tableWidget_medical_record.setRowCount(6)

        self.week_list = date_utils.get_week_list(self.year, self.month)

        self._set_project_columns(self.week_list)
        self._calculate_week(self.week_list)
        self._calculate_total()
        self._calculate_month()

    def _set_project_columns(self, week_list):
        project_list = []
        for week, row_no in zip(week_list, range(len(week_list))):
            start_date = week[0]
            end_date = week[1]
            project_items = self._get_project_items(start_date, end_date)
            for item in project_items:
                if item not in project_list:
                    project_list.append(item)

        self._set_fee_data_row_header(project_list)

    def _get_project_items(self, start_date, end_date):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}"
        '''
        rows = self.database.select_record(sql)

        project_items = []
        for row in rows:
            case_key = row['CaseKey']
            sql = f'''
                SELECT prescript.Amount, medicine.Project FROM prescript
                    LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
                WHERE
                    CaseKey = {case_key} AND
                    medicine.Project IS NOT NULL AND LENGTH(medicine.Project) > 0
                ORDER BY medicine.MedicineKey
            '''
            prescript_rows = self.database.select_record(sql)
            for prescript in prescript_rows:
                project_name = string_utils.xstr(prescript['Project'])
                if project_name not in project_items:
                    project_items.append(project_name)

        return project_items

    def _calculate_week(self, week_list):
        for week, row_no in zip(week_list, range(len(week_list))):
            start_date = week[0]
            end_date = week[1]
            date_period = f'{start_date.month}/{start_date.day}~{end_date.month}/{end_date.day}'

            self._set_table_item(self.ui.tableWidget_medical_record, row_no, 0, row_no+1)
            self._set_table_item(self.ui.tableWidget_medical_record, row_no, 1, date_period)
            self._calculate_project_item(row_no, start_date, end_date)

    @staticmethod
    def _get_datetime_period(start_date, end_date):
        start_date = f'{start_date.year}-{start_date.month}-{start_date.day} 00:00:00'
        end_date = f'{end_date.year}-{end_date.month}-{end_date.day} 23:59:59'

        return start_date, end_date

    def _calculate_project_item(self, row_no, start_date, end_date):
        for col_no in range(2, self.ui.tableWidget_medical_record.columnCount()-1):
            self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, 0)

        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}"
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            case_key = row['CaseKey']
            sql = f'''
                SELECT prescript.MedicineSet, prescript.Amount, medicine.Project FROM prescript
                    LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
                WHERE
                    CaseKey = {case_key} AND
                    medicine.Project IS NOT NULL AND LENGTH(medicine.Project) > 0
                ORDER BY medicine.MedicineKey
            '''
            prescript_rows = self.database.select_record(sql)
            for prescript in prescript_rows:
                project_name = string_utils.xstr(prescript['Project'])
                col_no = self._get_project_item_col_no(project_name)
                if col_no is None:
                    continue

                item = self.ui.tableWidget_medical_record.item(row_no, col_no)
                pres_days = case_utils.get_pres_days(self.database, case_key, prescript['MedicineSet'])
                if pres_days <= 0:
                    pres_days = 1

                amount = number_utils.get_integer(prescript['Amount']) * pres_days

                total_amount = number_utils.get_integer(item.text()) + amount
                self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, total_amount)

    def _get_project_item_col_no(self, project_name):
        for col_no in range(self.ui.tableWidget_medical_record.columnCount()):
            header = self.ui.tableWidget_medical_record.horizontalHeaderItem(col_no).text()
            if project_name == header:
                return col_no

        return None

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

    def _calculate_month(self):
        start_date = date_utils.str_to_date(date_utils.get_start_date_by_year_month(self.year, self.month))
        end_date = date_utils.str_to_date(
            date_utils.get_end_date_by_year_month(int(self.year), int(self.month))
        )

        self.ui.tableWidget_medical_record.setRowCount(self.ui.tableWidget_medical_record.rowCount() + 1)
        row_no = self.ui.tableWidget_medical_record.rowCount() - 1
        period = f'{self.year}年{self.month}月'

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, 0, '當月')
        self._set_table_item(self.ui.tableWidget_medical_record, row_no, 1, period)
        self._calculate_project_item(row_no, start_date, end_date)

        total = 0
        for col_no in range(2, self.ui.tableWidget_medical_record.columnCount()-1):
            item = self.ui.tableWidget_medical_record.item(6, col_no)
            if item is None:
                continue

            total += number_utils.get_integer(item.text())

        self._set_table_item(
            self.ui.tableWidget_medical_record,
            6, self.ui.tableWidget_medical_record.columnCount()-1, total
        )

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

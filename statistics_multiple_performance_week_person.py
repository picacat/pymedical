# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtChart

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import system_utils
from libs import chart_utils


# 綜合業績報表-週統計表 2020.02.15
class StatisticsMultiplePerformanceWeekPerson(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMultiplePerformanceWeekPerson, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MULTIPLE_PERFORMANCE_WEEK_PERSON, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_week = class_utils.get_table_widget(
            self.ui.tableWidget_week, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            180, 140, 140, 140, 140, 140, 120, 120,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

        width = [
            70,
            45, 45, 45,
            45, 45, 45,
            45, 45, 45,
            45, 45, 45,
            45, 45, 45,
            45, 45, 45,
            45, 45, 45,
            70,
        ]
        self.table_widget_week.set_table_heading_width(width)

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
        self._calculate_week_count()
        self._plot_chart()

    def _set_ins_data_row_header(self):
        row_header = [
            '日期', '健保總人數', '健保總日數', '健保總診數', '平均健保人數/日', '平均健保人數/診',
            '自費', '初診', '複診', '內科', '針灸', '針灸給藥', '傷骨科',
        ]
        for row_no in range(len(row_header)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, row_header[row_no])
            self.ui.tableWidget_medical_record.setItem(
                row_no, 0, item
            )
            self.ui.tableWidget_medical_record.item(
                row_no, 0).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

    def week_of_month(self, dt):
        from math import ceil
        """ Returns the week of the month for the specified date.
        """

        first_day = dt.replace(day=1)

        dom = dt.day
        adjusted_dom = dom + first_day.weekday()

        return int(ceil(adjusted_dom / 7.0))

    def _calculate_ins_data(self):
        self.ui.tableWidget_medical_record.setRowCount(13)
        self._set_ins_data_row_header()

        header = ['項目', '', '', '', '', '', '總和', '平均']
        self.week_list = date_utils.get_week_list(self.year, self.month)
        for i, week in enumerate(self.week_list):
            header[i+1] = f'第{week[2]}週'

        self.ui.tableWidget_medical_record.setHorizontalHeaderLabels(header)
        self._calculate_week(self.week_list)

    def _calculate_week(self, week_list):
        for week, col_no in zip(week_list, range(1, len(week_list)+1)):
            start_date = week[0]
            end_date = week[1]
            date_period = f'{start_date.month}/{start_date.day}~{end_date.month}/{end_date.day}'
            self._set_table_item(self.ui.tableWidget_medical_record, 0, col_no, date_period)

            self._calculate_person_count(1, col_no, start_date, end_date, '健保')
            self._calculate_ins_days(2, col_no, start_date, end_date)
            self._calculate_ins_period(3, col_no, start_date, end_date)
            self._calculate_avg_days(4, col_no)
            self._calculate_avg_period(5, col_no)

            self._calculate_person_count(6, col_no, start_date, end_date, '自費')
            self._calculate_visit(7, col_no, start_date, end_date, '初診')
            self._calculate_visit(8, col_no, start_date, end_date, '複診')
            self._calculate_treat_type(9, col_no, start_date, end_date, '內科')
            self._calculate_treat_type(10, col_no, start_date, end_date, '針灸')
            self._calculate_treat_type(11, col_no, start_date, end_date, '針灸給藥')
            self._calculate_treat_type(12, col_no, start_date, end_date, '傷骨科')

        self._calculate_total()

    @staticmethod
    def _get_datetime_period(start_date, end_date):
        start_date = f'{start_date.year}-{start_date.month}-{start_date.day} 00:00:00'
        end_date = f'{end_date.year}-{end_date.month}-{end_date.day} 23:59:59'

        return start_date, end_date

    def _calculate_person_count(self, row_no, col_no, start_date, end_date, ins_type):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                InsType = "{ins_type}" AND
                TreatType != "自購"
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_ins_days(self, row_no, col_no, start_date, end_date):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                InsType = "健保"
            GROUP BY Date(CaseDate)
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_ins_period(self, row_no, col_no, start_date, end_date):
        start_date, end_date = self._get_datetime_period(start_date, end_date)
        sql = f'''
            SELECT CaseKey, CaseDate, DATE(CaseDate) as case_date FROM cases
                LEFT JOIN person ON cases.Doctor = person.Name
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保" AND
                Doctor IS NOT NULL AND
                LENGTH(Doctor) > 0 AND
                person.ID IS NOT NULL
            GROUP BY case_date, Period, Doctor
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_avg_days(self, row_no, col_no):
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(1, col_no).text())
        total_days = number_utils.get_integer(self.ui.tableWidget_medical_record.item(2, col_no).text())
        if total_count == 0 or total_days == 0:
            avg_days = 0
        else:
            avg_days = number_utils.round_up(total_count / total_days)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, avg_days)

    def _calculate_avg_period(self, row_no, col_no):
        total_count = number_utils.get_integer(self.ui.tableWidget_medical_record.item(1, col_no).text())
        total_period = number_utils.get_integer(self.ui.tableWidget_medical_record.item(3, col_no).text())
        if total_count == 0 or total_period == 0:
            avg_period = 0
        else:
            avg_period = number_utils.round_up(total_count / total_period)
            # avg_period = round(total_count / total_period)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, avg_period)

    def _calculate_visit(self, row_no, col_no, start_date, end_date, visit):
        start_date, end_date = self._get_datetime_period(start_date, end_date)

        if visit == '初診':
            visit_condition = f'AND Visit = "{visit}"'
        else:
            visit_condition = f'AND (Visit = "{visit}" OR Visit IS NULL)'

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                InsType IN("健保", "自費") AND
                TreatType != "自購"
                {visit_condition}
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

    def _calculate_treat_type(self, row_no, col_no, start_date, end_date, treat_type):
        start_date, end_date = self._get_datetime_period(start_date, end_date)

        treat_type_condition = ''
        if treat_type == '內科':
            treat_type_condition = f'AND TreatType = "{treat_type}"'
        elif treat_type == '針灸':
            treat_type_condition = '''
                AND
                (TreatType LIKE "%針灸%" OR TreatType LIKE "%電針%" OR
                 TreatType LIKE "%複雜針灸%" OR TreatType LIKE "%複雜性針灸") AND
                (InterDrugFee IS NULL OR InterDrugFee = 0)
            '''
        elif treat_type == '針灸給藥':
            treat_type_condition = '''
                AND
                (TreatType LIKE "%針灸%" OR TreatType LIKE "%電針%" OR
                 TreatType LIKE "%複雜針灸%" OR TreatType LIKE "%複雜性針灸") AND
                InterDrugFee > 0
            '''
        elif treat_type == '傷骨科':
            treat_type_condition = '''
                AND
                (TreatType LIKE "%傷科%" OR TreatType LIKE "%複雜傷科%" OR
                 TreatType LIKE "%複雜性傷科%" OR
                 TreatType = "%脫臼%" OR TreatType = "%骨折%") AND
                (TreatType NOT LIKE "%針灸%")
            '''

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                InsType = "健保"
                {treat_type_condition}
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)

        self._set_table_item(self.ui.tableWidget_medical_record, row_no, col_no, row_count)

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
        for row_no in range(1, self.ui.tableWidget_medical_record.rowCount() + 1):
            total = 0
            col_count = 0
            for col_no in range(1, 6):
                item = self.ui.tableWidget_medical_record.item(row_no, col_no)
                if item is None:
                    continue

                value = number_utils.get_integer(item.text())
                total += value
                col_count += 1

            if total > 0 and col_count > 0:
                self._set_table_item(self.ui.tableWidget_medical_record, row_no, 6, total)
                self._set_table_item(
                    self.ui.tableWidget_medical_record, row_no, 7, number_utils.round_up(total/col_count)
                )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_treat_type_chart()
        self._plot_visit_chart()
        self._plot_week_chart()

    def _calculate_week_count(self):
        self.ui.tableWidget_week.setRowCount(8)
        self._set_week_header()
        self._calculate_week_data()
        self._calculate_week_total()

    def _set_week_header(self):
        if len(self.week_list) <= 0:
            return

        start_year = self.week_list[0][0].year
        start_month = self.week_list[0][0].month
        start_day = self.week_list[0][0].day
        start_date = f'{start_year}-{start_month}-{start_day}'

        end_year = self.week_list[-1][1].year
        end_month = self.week_list[-1][1].month
        end_day = self.week_list[-1][1].day
        end_date = f'{end_year}-{end_month}-{end_day}'

        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}"
            GROUP BY Date(CaseDate)
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        week_list = [[], [], [], [], [], [], []]
        for row in rows:
            week_day = row['CaseDate'].weekday()
            week_list[week_day].append(string_utils.xstr(row['CaseDate'].day))

        col_list = [1, 4, 7, 10, 13, 16, 19]
        for col_no in col_list:
            self.ui.tableWidget_week.setSpan(0, col_no, 1, 3)

        self._set_table_item(self.ui.tableWidget_week, 0, 0, '日期')
        for col_no, i in zip(col_list, range(len(col_list))):
            self._set_table_item(
                self.ui.tableWidget_week, 0, col_no, ', '.join(week_list[i])
            )

        header = [
            '週別',
            '早', '午', '晚',
            '早', '午', '晚',
            '早', '午', '晚',
            '早', '午', '晚',
            '早', '午', '晚',
            '早', '午', '晚',
            '早', '午', '晚',
        ]
        row_no = 1
        for col_no in range(len(header)):
            self.ui.tableWidget_week.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(header[col_no])
            )
            self.ui.tableWidget_week.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

    def _calculate_week_data(self):
        week_list_count = len(self.week_list)
        if week_list_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計人數資料中, 請稍後...', '取消', 0, week_list_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for i, week_row in zip(range(week_list_count), self.week_list):
            progress_dialog.setValue(i)
            if progress_dialog.wasCanceled():
                break

            row_no = i + 2
            self._set_table_item(self.ui.tableWidget_week, row_no, 0, i+1)
            start_date, end_date = self._get_datetime_period(
                week_row[0], week_row[1],
            )
            sql = f'''
                SELECT CaseDate FROM cases
                WHERE
                    CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                    InsType IN('健保', '自費')
                GROUP BY Date(CaseDate)
                ORDER BY CaseDate
            '''
            rows = self.database.select_record(sql)
            self._calculate_week_period_count(row_no, rows)

        progress_dialog.setValue(week_list_count)
        progress_dialog.deleteLater()

    def _calculate_week_period_count(self, row_no, rows):
        col_no_list = [1, 4, 7, 10, 13, 16, 19]
        for row in rows:
            week_no = row['CaseDate'].weekday()
            col_no = col_no_list[week_no]
            count = self._get_period_count(row['CaseDate'], '早班')
            self._set_table_item(self.ui.tableWidget_week, row_no, col_no, count)
            count = self._get_period_count(row['CaseDate'], '午班')
            self._set_table_item(self.ui.tableWidget_week, row_no, col_no+1, count)
            count = self._get_period_count(row['CaseDate'], '晚班')
            self._set_table_item(self.ui.tableWidget_week, row_no, col_no+2, count)

    def _get_period_count(self, case_date, period):
        start_date = f'{case_date.year}-{case_date.month}-{case_date.day} 00:00:00'
        end_date = f'{case_date.year}-{case_date.month}-{case_date.day} 23:59:59'

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" and "{end_date}" AND
                Period = "{period}" AND
                InsType IN('健保', '自費') AND
                TreatType != "自購"
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _calculate_week_total(self):
        for row_no in range(2, self.ui.tableWidget_week.rowCount() + 1):
            total = 0
            col_count = 0
            for col_no in range(1, 22):
                item = self.ui.tableWidget_week.item(row_no, col_no)
                if item is None:
                    continue

                value = number_utils.get_integer(item.text())
                total += value
                col_count += 1

            if total > 0 and col_count > 0:
                self._set_table_item(self.ui.tableWidget_week, row_no, 22, total)

        self._set_table_item(self.ui.tableWidget_week, 7, 0, '總計')
        for col_no in range(1, self.ui.tableWidget_week.columnCount()):
            total = 0
            for row_no in range(2, 7):
                item = self.ui.tableWidget_week.item(row_no, col_no)
                if item is not None:
                    total += number_utils.get_integer(item.text())

                self._set_table_item(self.ui.tableWidget_week, 7, col_no, total)

    def _plot_treat_type_chart(self):
        set_list = list()
        set_list.append(QtChart.QBarSet('內科'))
        set_list.append(QtChart.QBarSet('針灸'))
        set_list.append(QtChart.QBarSet('針藥'))
        set_list.append(QtChart.QBarSet('傷科'))

        treat_type_list = []
        for i in range(len(set_list)):
            treat_type_list.append([])

        categories = []

        weeks = 5
        for col_no in range(1, weeks+1):
            item = self.ui.tableWidget_medical_record.item(0, col_no)
            if item is None:
                break

            categories.append(f'第{col_no}週')
            for j in range(len(set_list)):
                value = number_utils.get_integer(self.ui.tableWidget_medical_record.item(j+9, col_no).text())
                treat_type_list[j].append(value)

        series = QtChart.QStackedBarSeries()
        for i in range(len(set_list)):
            for value in treat_type_list[i]:
                set_list[i] << value

            series.append(set_list[i])

        chart_utils.plot_chart('健保人數統計表', series, categories, self.ui.verticalLayout_chart, 500)

    def _plot_visit_chart(self):
        set_list = list()
        set_list.append(QtChart.QBarSet('複診'))
        set_list.append(QtChart.QBarSet('初診'))

        visit_list = []
        for i in range(len(set_list)):
            visit_list.append([])

        categories = []

        weeks = 5
        for col_no in range(1, weeks+1):
            item = self.ui.tableWidget_medical_record.item(0, col_no)
            if item is None:
                break

            categories.append(f'第{col_no}週')
            for j in range(len(set_list)):
                value = number_utils.get_integer(self.ui.tableWidget_medical_record.item(8-j, col_no).text())
                visit_list[j].append(value)

        series = QtChart.QStackedBarSeries()
        for i in range(len(set_list)):
            for value in visit_list[i]:
                set_list[i] << value

            series.append(set_list[i])

        chart_utils.plot_chart('初複診統計表', series, categories, self.ui.verticalLayout_chart, 500)

    def _plot_week_chart(self):
        set_list = list()
        set_list.append(QtChart.QBarSet('早班'))
        set_list.append(QtChart.QBarSet('午班'))
        set_list.append(QtChart.QBarSet('晚班'))

        period_list = []
        for i in range(len(set_list)):
            period_list.append([])

        categories = []

        col_no_list = [1, 4, 7, 10, 13, 16, 19]
        for i, col_no in enumerate(col_no_list):
            week_name = date_utils.get_weekday_name(i)
            categories.append(week_name[2])
            for j in range(len(set_list)):
                value = number_utils.get_integer(self.ui.tableWidget_week.item(7, col_no+j).text())
                period_list[j].append(value)

        series = QtChart.QStackedBarSeries()
        for i in range(len(set_list)):
            for value in period_list[i]:
                set_list[i] << value

            series.append(set_list[i])

        chart_utils.plot_chart('週人數統計表', series, categories, self.ui.verticalLayout_chart, 500)


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtChart, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import copy

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import nhi_utils
from libs import chart_utils
from libs import case_utils


# 日報表人數統計 2020.03.27
class StatisticsDailyPerson(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDailyPerson, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.day = args[4]
        self.ui = None

        self.start_date = f'{self.year}-{self.month}-{self.day} 00:00:00'
        self.end_date = f'{self.year}-{self.month}-{self.day} 23:59:59'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DAILY_PERSON, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_period1 = class_utils.get_table_widget(
            self.ui.tableWidget_period1, self.database
        )
        self.table_widget_period2 = class_utils.get_table_widget(
            self.ui.tableWidget_period2, self.database
        )
        self.table_widget_period3 = class_utils.get_table_widget(
            self.ui.tableWidget_period3, self.database
        )
        self.table_widget_period_total = class_utils.get_table_widget(
            self.ui.tableWidget_period_total, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            60, 100,
            80, 80, 80, 80, 80, 80, 80, 80, 80, 80,
            80, 80, 80, 80, 80, 80, 80, 80, 80, 80,
        ]
        self.table_widget_period1.set_table_heading_width(width)
        self.table_widget_period2.set_table_heading_width(width)
        self.table_widget_period3.set_table_heading_width(width)
        self.table_widget_period_total.set_table_heading_width(width)

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
        self._calculate_data('早班', self.ui.tableWidget_period1)
        self._calculate_data('午班', self.ui.tableWidget_period2)
        self._calculate_data('晚班', self.ui.tableWidget_period3)
        self._calculate_period_total()
        # self._plot_chart()

    def _calculate_period_total(self):
        self.ui.tableWidget_period_total.setRowCount(1)
        self._set_table_item(self.ui.tableWidget_period_total, 0, 0, '全部')
        self._set_table_item(self.ui.tableWidget_period_total, 0, 1, '總計')

        for col_no in range(2, self.ui.tableWidget_period_total.columnCount()):
            self._set_table_item(
                self.ui.tableWidget_period_total, 0, col_no,
                number_utils.get_integer(
                    self.ui.tableWidget_period1.item(self.ui.tableWidget_period1.rowCount()-1, col_no).text()) +
                number_utils.get_integer(
                    self.ui.tableWidget_period2.item(self.ui.tableWidget_period2.rowCount()-1, col_no).text()) +
                number_utils.get_integer(
                    self.ui.tableWidget_period3.item(self.ui.tableWidget_period3.rowCount()-1, col_no).text())
            )

    def _calculate_data(self, period, table_widget_period):
        table_widget_period.setRowCount(0)

        sql = f'''
            SELECT Doctor FROM cases
                LEFT JOIN person ON person.Name = cases.Doctor
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (Period = "{period}") AND
                (Doctor IS NOT NULL AND LENGTH(Doctor) > 0) AND
                (person.Position IN ("醫師", "支援醫師")) AND
                (person.ID IS NOT NULL)
            GROUP BY Doctor
            ORDER BY cases.Room
        '''
        rows = self.database.select_record(sql)
        table_widget_period.setRowCount(len(rows))
        for row_no, row in enumerate(rows):
            doctor = string_utils.xstr(row['Doctor'])
            self._set_table_item(table_widget_period, row_no, 0, period)
            self._set_table_item(table_widget_period, row_no, 1, doctor)
            self._count_doctor(table_widget_period, row_no, doctor, period)

        self._calculate_total(table_widget_period)

    def _count_doctor(self, table_widget_period, row_no, doctor, period):
        sql = f'''
            SELECT CaseKey, PatientKey, CaseDate, InsType, Treatment FROM cases
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (Period = "{period}") AND
                (Doctor = "{doctor}")
        '''
        rows = self.database.select_record(sql)

        internal_medicine = 0
        general_acupuncture = 0
        moderate_acupuncture = 0
        highly_acupuncture = 0
        general_massage = 0
        moderate_massage = 0
        highly_massage = 0
        acupuncture_with_medicine = 0
        m_acupuncture_with_medicine = 0
        h_acupuncture_with_medicine = 0
        massage_with_medicine = 0
        merge_treat = 0
        merge_treat_with_medicine = 0

        own_expense = 0

        for row in rows:
            ins_type = string_utils.xstr(row['InsType'])
            treatment = string_utils.xstr(row['Treatment'])
            pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
            if ins_type == '健保':
                if treatment in nhi_utils.MERGE_TREAT_LIST:
                    if pres_days > 0:
                        merge_treat_with_medicine += 1
                    else:
                        merge_treat += 1
                elif treatment in nhi_utils.ACUPUNCTURE_TREAT:
                    if treatment in nhi_utils.ORDINARY_ACUPUNCTURE_TREAT:
                        if pres_days > 0:
                            acupuncture_with_medicine += 1
                        else:
                            general_acupuncture += 1
                    elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                        if pres_days > 0:
                            m_acupuncture_with_medicine += 1
                        else:
                            moderate_acupuncture += 1
                    elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                        if pres_days > 0:
                            h_acupuncture_with_medicine += 1
                        else:
                            highly_acupuncture += 1
                elif treatment in nhi_utils.MASSAGE_TREAT:
                    if pres_days > 0:
                        massage_with_medicine += 1
                    elif treatment in nhi_utils.ORDINARY_MASSAGE_TREAT:
                        general_massage += 1
                    elif treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                        moderate_massage += 1
                    elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                        highly_massage += 1
                else:
                    internal_medicine += 1
            elif ins_type == '自費':
                # if case_utils.is_duplicate_patient(self.database, row):
                #     continue

                own_expense += 1

        acupuncture_subtotal = (
            general_acupuncture + moderate_acupuncture + highly_acupuncture + acupuncture_with_medicine + \
                m_acupuncture_with_medicine + h_acupuncture_with_medicine
        )
        massage_subtotal = general_massage + moderate_massage + highly_massage + massage_with_medicine
        merge_subtotal = merge_treat + merge_treat_with_medicine

        treat_total = acupuncture_subtotal + massage_subtotal + merge_subtotal

        subtotal = internal_medicine + acupuncture_subtotal + massage_subtotal + merge_subtotal
        total = subtotal + own_expense

        self._set_table_item(table_widget_period, row_no, 2, internal_medicine)
        self._set_table_item(table_widget_period, row_no, 3, general_acupuncture)
        self._set_table_item(table_widget_period, row_no, 4, moderate_acupuncture)
        self._set_table_item(table_widget_period, row_no, 5, highly_acupuncture)
        self._set_table_item(table_widget_period, row_no, 6, acupuncture_with_medicine)
        self._set_table_item(table_widget_period, row_no, 7, m_acupuncture_with_medicine)
        self._set_table_item(table_widget_period, row_no, 8, h_acupuncture_with_medicine)
        self._set_table_item(table_widget_period, row_no, 9, acupuncture_subtotal)

        self._set_table_item(table_widget_period, row_no, 10, general_massage)
        self._set_table_item(table_widget_period, row_no, 11, moderate_massage)
        self._set_table_item(table_widget_period, row_no, 12, highly_massage)
        self._set_table_item(table_widget_period, row_no, 13, massage_with_medicine)
        self._set_table_item(table_widget_period, row_no, 14, massage_subtotal)

        self._set_table_item(table_widget_period, row_no, 15, merge_treat)
        self._set_table_item(table_widget_period, row_no, 16, merge_treat_with_medicine)
        self._set_table_item(table_widget_period, row_no, 17, merge_subtotal)

        self._set_table_item(table_widget_period, row_no, 18, treat_total)

        self._set_table_item(table_widget_period, row_no, 19, subtotal)
        self._set_table_item(table_widget_period, row_no, 20, own_expense)
        self._set_table_item(table_widget_period, row_no, 21, total)

    @staticmethod
    def _get_datetime_period(start_date, end_date):
        start_date = f'{start_date.year}-{start_date.month}-{start_date.day} 00:00:00'
        end_date = f'{end_date.year}-{end_date.month}-{end_date.day} 23:59:59'

        return start_date, end_date

    @staticmethod
    def _set_table_item(tableWidget, row_no, col_no, data):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, data)
        tableWidget.setItem(row_no, col_no, item)
        tableWidget.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    def _calculate_total(self, table_widget_period):
        row_count = table_widget_period.rowCount()
        table_widget_period.setRowCount(row_count + 1)

        total_list = [0 for _ in range(table_widget_period.columnCount())]
        for row_no in range(table_widget_period.rowCount()):
            for col_no in range(2, table_widget_period.columnCount()):
                item = table_widget_period.item(row_no, col_no)
                if item is None:
                    continue

                value = number_utils.get_integer(item.text())
                total_list[col_no] += value

        total_list[0] = ''
        total_list[1] = '合計'
        for col_no in range(len(total_list)):
            self._set_table_item(table_widget_period, row_count, col_no, total_list[col_no])

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_treat_type_chart()
        self._plot_visit_chart()
        self._plot_week_chart()

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

        col_no_list = [1, 4, 7, 10, 13, 16]
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

    def _get_export_table_widget(self):
        tableWidget_period = QtWidgets.QTableWidget()
        tableWidget_period.setColumnCount(self.ui.tableWidget_period1.columnCount())

        current_row_no = 0
        for i in range(0, self.ui.tableWidget_period1.rowCount()):
            current_row_no += 1
            tableWidget_period.setRowCount(current_row_no)
            for j in range(0, self.ui.tableWidget_period1.columnCount()):
                current_item = self.ui.tableWidget_period1.item(i, j)
                if current_item:
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, current_item.text())
                    tableWidget_period.setItem(current_row_no-1, j, item)

        for i in range(0, self.ui.tableWidget_period2.rowCount()):
            current_row_no += 1
            tableWidget_period.setRowCount(current_row_no)
            for j in range(0, self.ui.tableWidget_period2.columnCount()):
                current_item = self.ui.tableWidget_period2.item(i, j)
                if current_item:
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, current_item.text())
                    tableWidget_period.setItem(current_row_no-1, j, item)

        for i in range(0, self.ui.tableWidget_period3.rowCount()):
            current_row_no += 1
            tableWidget_period.setRowCount(current_row_no)
            for j in range(0, self.ui.tableWidget_period3.columnCount()):
                current_item = self.ui.tableWidget_period3.item(i, j)
                if current_item:
                    item = QtWidgets.QTableWidgetItem()
                    item.setData(QtCore.Qt.EditRole, current_item.text())
                    tableWidget_period.setItem(current_row_no-1, j, item)

        header = [
            '班別', '醫師姓名', '內科', '一般針灸', '中度針灸', '高度針灸', '一般針藥',
            '中度針藥', '高度針藥', '針灸合計',
            '一般傷科', '中度傷科', '高度傷科', '傷科給藥', '傷科合計',
            '針傷合併', '合併給藥', '合併合計', '針傷合計', '健保小計', '自費人數', '總計'
        ]
        tableWidget_period.setHorizontalHeaderLabels(header)

        return tableWidget_period

    def export_to_excel(self):
        options = QFileDialog.Options()
        clinic_name = self.system_settings.field('院所名稱')
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "日報表",
            f'{clinic_name}日報表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        tableWidget_period = self._get_export_table_widget()

        export_utils.export_table_widget_to_excel(
            excel_file_name, tableWidget_period, None,
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            'Excel資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Excel檔案格式.'
        )
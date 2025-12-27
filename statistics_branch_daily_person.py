
# -*- coding: UTF-8 -*-

from PyQt5 import QtChart, QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (case_utils, chart_utils, class_utils, date_utils,
                  export_utils, nhi_utils, number_utils, string_utils,
                  system_utils, ui_utils)


# 分院日報表人數統計 2022.01.19
class StatisticsBranchDailyPerson(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsBranchDailyPerson, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.database_list = args[2]
        self.year = args[3]
        self.month = args[4]
        self.day = args[5]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_BRANCH_DAILY_PERSON, self)
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
        self._set_table_width()

    def _set_table_width(self):
        width = [
            60, 150, 120, 100, 100, 100, 100, 100, 100, 100, 100, 100,
        ]
        self.table_widget_period1.set_table_heading_width(width)
        self.table_widget_period2.set_table_heading_width(width)
        self.table_widget_period3.set_table_heading_width(width)

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
        # self._plot_chart()

    def _get_rows(self, clinic_name, database, period):
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
        rows = database.select_record(sql)

        for row in rows:
            row['database'] = database
            row['clinic_name'] = clinic_name

        return rows

    def _calculate_data(self, period, table_widget_period):
        table_widget_period.setRowCount(0)

        total_rows = []
        for clinic_name in self.database_list:
            database = self.database_list[clinic_name]['database']
            rows = self._get_rows(clinic_name, database, period)
            total_rows += rows

        table_widget_period.setRowCount(len(total_rows))
        for row_no, row in enumerate(total_rows):
            doctor = string_utils.xstr(row['Doctor'])
            clinic_name = row['clinic_name']
            database = row['database']
            self._set_table_item(table_widget_period, row_no, 0, period)
            self._set_table_item(table_widget_period, row_no, 2, doctor)
            self._count_doctor(clinic_name, database, table_widget_period, row_no, doctor, period)

        self._calculate_total(table_widget_period)

    def _count_doctor(self, clinic_name, database, table_widget_period, row_no, doctor, period):
        sql = f'''
            SELECT CaseKey, Card, InsType, TreatType, TotalFee FROM cases
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (Period = "{period}") AND
                (Doctor = "{doctor}")
        '''
        rows = database.select_record(sql)

        general_treat = 0
        acupuncture_treat = 0
        acupuncture_with_medicine = 0
        massage_treat = 0
        massage_with_medicine = 0
        own_expense = 0
        subtotal, total = 0, 0
        self_total_fee = 0
        for row in rows:
            card = string_utils.xstr(row['Card'])
            if card in ['XX1', 'XX2', 'XX3', 'XX4', 'XX5']:
                continue
            
            ins_type = string_utils.xstr(row['InsType'])
            treat_type = string_utils.xstr(row['TreatType'])
            self_total_fee += number_utils.get_integer(row['TotalFee'])
            if ins_type == '健保':
                if treat_type == '內科':
                    general_treat += 1
                elif treat_type in nhi_utils.ACUPUNCTURE_TREAT:
                    pres_days = case_utils.get_pres_days(database, row['CaseKey'])
                    if pres_days > 0:
                        acupuncture_with_medicine += 1
                    else:
                        acupuncture_treat += 1
                elif treat_type in nhi_utils.MASSAGE_TREAT:
                    pres_days = case_utils.get_pres_days(database, row['CaseKey'])
                    if pres_days > 0:
                        massage_with_medicine += 1
                    else:
                        massage_treat += 1
                        
            elif ins_type == '自費':
                own_expense += 1

            subtotal = general_treat + acupuncture_treat + acupuncture_with_medicine + massage_treat + massage_with_medicine
            total = subtotal + own_expense

        self._set_table_item(table_widget_period, row_no, 1, clinic_name)
        self._set_table_item(table_widget_period, row_no, 3, general_treat)
        self._set_table_item(table_widget_period, row_no, 4, acupuncture_treat)
        self._set_table_item(table_widget_period, row_no, 5, acupuncture_with_medicine)
        self._set_table_item(table_widget_period, row_no, 6, massage_treat)
        self._set_table_item(table_widget_period, row_no, 7, massage_with_medicine)
        self._set_table_item(table_widget_period, row_no, 8, subtotal)
        self._set_table_item(table_widget_period, row_no, 9, own_expense)
        self._set_table_item(table_widget_period, row_no, 10, total)
        self._set_table_item(table_widget_period, row_no, 11, self_total_fee)

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
            for col_no in range(3, 10):
                item = table_widget_period.item(row_no, col_no)
                if item is None:
                    continue

                value = number_utils.get_integer(item.text())
                total_list[col_no] += value

        total_list[0] = ''
        total_list[1] = ''
        total_list[2] = '合計'
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

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{start_date}至{end_date}掛號費優待統計表.xlsx',
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

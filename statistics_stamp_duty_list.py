# -*- coding: utf-8 -*-

import datetime

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (case_utils, class_utils, export_utils, number_utils,
                  personnel_utils, string_utils, system_utils, ui_utils)


# 印花稅金額統計 2024.03.17
class StatisticsStampDutyList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsStampDutyList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
        self.option = args[7]
        self.weekday_list = args[8]
        self.ui = None
        self.program_name = '自費印花稅統計'

        self._set_ui()
        self._set_signal()

        self.user_name = system_utils.get_user_name(self.system_settings)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_STAMP_DUTY_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_case_amount = class_utils.get_table_widget(self.ui.tableWidget_case_amount, self.database)
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            130, 70, 90, 100, 100, 70, 100,
            90, 90, 90, 90, 90, 90, 90, 90, 90,
            90, 90, 90,
        ]
        self.table_widget_case_amount.set_table_heading_width(width)
        self.table_widget_case_amount.set_column_hidden([0])

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_excel.clicked.connect(self._export_to_excel)
        self.ui.tableWidget_case_amount.doubleClicked.connect(self.open_medical_record)

    def open_medical_record(self):
        if self.user_name == '超級使用者':
            pass
        elif personnel_utils.get_permission(self.database, '病歷查詢', '調閱病歷', self.user_name) != 'Y':
            system_utils.show_message_box(
                QMessageBox.Warning,
                '權限不足',
                f'<h3>{self.user_name}，您的權限[{self.program_name}:調閱病歷]未被授權，無法進入病歷.</h3>',
                '請確認是否獲得調閱病歷的權限'
            )
        else:
            pass

        case_key = self.table_widget_case_amount.field_value(0)
        self.parent.parent.open_medical_record(case_key, '病歷查詢')

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_case_amount.setRowCount(0)
        self._calculate_data()

    def _calculate_data(self):
        self._calculate_case_amount()
        self._calculate_table_widget_total(self.ui.tableWidget_case_amount)

    def _calculate_case_amount(self):
        period_condition = ''
        if self.period != '全部':
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = ' AND Doctor = "{0}"'.format(self.doctor)

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT
                CaseKey, PatientKey, CaseDate, InsType, Period, Name, Doctor,
                RegistFee, SDiagFee, SDrugFee, SHerbFee, SExpensiveFee,
                SAcupunctureFee, SMassageFee, SMaterialFee, SExamFee,
                DiscountFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                (RegistFee >= 250 OR TotalFee >= 250)
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        self.table_widget_case_amount.set_db_data(sql, self._set_case_amount)

    # 顯示資料
    def _set_case_amount(self, row_no, row):
        case_key = string_utils.xstr(row['CaseKey'])
        ins_type = string_utils.xstr(row['InsType'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_fee = number_utils.get_integer(row['SDiagFee'])
        drug_fee = number_utils.get_integer(row['SDrugFee'])
        herb_fee = number_utils.get_integer(row['SHerbFee'])
        expensive_fee = number_utils.get_integer(row['SExpensiveFee'])
        acupuncture_fee = number_utils.get_integer(row['SAcupunctureFee'])
        massage_fee = number_utils.get_integer(row['SMassageFee'])
        material_fee = number_utils.get_integer(row['SMaterialFee'])
        exam_fee = number_utils.get_integer(row['SExamFee'])
        self_total_fee = (
            diag_fee + drug_fee + herb_fee + expensive_fee + acupuncture_fee + massage_fee +
            material_fee + exam_fee
        )
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        total_fee = self_total_fee - discount_fee

        if ins_type == '自費' or regist_fee >= 250:
            total_fee += regist_fee

        stamp_duty_fee = number_utils.get_integer(total_fee * 4 / 1000)  # 印花稅千分之4

        case_row = [
            case_key,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Period']),
            row['PatientKey'],
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Doctor']),
            ins_type,
            regist_fee,
            diag_fee,
            drug_fee,
            herb_fee,
            expensive_fee,
            acupuncture_fee,
            massage_fee,
            material_fee,
            exam_fee,
            self_total_fee,
            discount_fee,
            total_fee,
            stamp_duty_fee,
        ]

        for col_no in range(len(case_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, case_row[col_no])
            self.ui.tableWidget_case_amount.setItem(
                row_no, col_no, item,
            )
            if col_no in [3] or col_no >= 7:
                self.ui.tableWidget_case_amount.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            else:
                self.ui.tableWidget_case_amount.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _calculate_table_widget_total(self, tableWidget):
        total_list = [0 for i in range(tableWidget.columnCount())]
        for row_no in range(tableWidget.rowCount()):
            for col_no in range(6, tableWidget.columnCount()):
                value = number_utils.get_integer(tableWidget.item(row_no, col_no).text())
                total_list[col_no] += value

        tableWidget.setRowCount(tableWidget.rowCount() + 1)
        row_no = tableWidget.rowCount() - 1
        for col_no in range(6, len(total_list)):
            self._set_item_data(
                tableWidget, row_no, col_no, string_utils.xstr(total_list[col_no])
            )

        tableWidget.setItem(
            row_no, 1, QtWidgets.QTableWidgetItem('合計')
        )
        tableWidget.item(row_no, 1).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _set_item_data(self, tableWidget, row_no, col_no, data):
        tableWidget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(data))
        )
        tableWidget.item(row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}自費印花稅統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_case_amount, [0],
            [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17], title=None,
            column_width=[15]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>自費印花稅{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            '{0}至{1}{2}個別醫師門診人次統計表.xlsx'.format(
                self.start_date[:10], self.end_date[:10], self.doctor
            ),
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor, None,
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>個別醫師人次統計檔{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_outpatient_count_chart()
        self._plot_visit_chart()

    def _plot_outpatient_count_chart(self):
        series = QtChart.QBarSeries()

        treat_type = ['內科', '針灸', '中針', '高針', '傷科', '中傷', '高傷']
        col_no_list = [10, 13, 17, 21, 25, 27, 29]

        set_list = []
        for i in range(len(treat_type)):
            set_list.append(QtChart.QBarSet(treat_type[i]))
            set_list[i] << number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(
                    self.ui.tableWidget_doctor_count.rowCount() - 1, col_no_list[i]).text()
            )
            series.append(set_list[i])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('門診人數統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['門診人數']

        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.setAxisX(axis, series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(500)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_visit_chart(self):
        series = QtChart.QPieSeries()

        row_no = self.ui.tableWidget_doctor_count.rowCount() - 1
        first_visit = number_utils.get_integer(self.ui.tableWidget_doctor_count.item(row_no, 3).text())
        visit = number_utils.get_integer(self.ui.tableWidget_doctor_count.item(row_no, 4).text())
        visit_list = [
            ['初診', first_visit],
            ['複診', visit],
        ]
        for row_no in range(len(visit_list)):
            series.append(visit_list[row_no][0], visit_list[row_no][1])

            try:
                slice = series.slices()[row_no]
            except IndexError:
                return

            slice.setExploded()
            slice.setLabelVisible()

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('初複診統計表')
        chart.legend().hide()
        chart.setAnimationOptions(QtChart.QChart.AllAnimations)

        chartView = QtChart.QChartView(chart)
        chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        chartView.setFixedWidth(500)
        chartView.setFixedHeight(350)
        self.ui.verticalLayout_chart.addWidget(chartView)

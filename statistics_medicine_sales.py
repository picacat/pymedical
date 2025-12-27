# -*- coding: utf-8 -*-

import re

from PyQt5 import QtChart, QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (class_utils, export_utils, number_utils, personnel_utils,
                  string_utils, system_utils, ui_utils)


# 用藥統計內容 2019.08.02
class StatisticsMedicineSales(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMedicineSales, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.ins_type = args[4]
        self.doctor = args[5]
        self.medicine_type = args[6]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.program_name = '用藥統計'

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MEDICINE_SALES, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medicine_sales = class_utils.get_table_widget(
            self.ui.tableWidget_medicine_sales, self.database
        )
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            270, 80,
            80, 50, 90, 90,
        ]
        self.table_widget_medicine_sales.set_table_heading_width(width)
        self.table_widget_medical_record.set_table_heading_width([100, 130, 80, 100, 70, 70])

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medicine_sales.itemSelectionChanged.connect(self._item_selection_changed)
        self.ui.tableWidget_medical_record.doubleClicked.connect(self._open_medical_record)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def _open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, '病歷查詢', '調閱病歷', self.user_name) != 'Y'):
            return

        case_key = self.table_widget_medical_record.field_value(0)
        self.parent.parent.open_medical_record(case_key, '用藥統計')

    def _item_selection_changed(self):
        medicine_name = self.table_widget_medicine_sales.field_value(0)
        sql = self._get_sql(assign_medicine=medicine_name)
        self.table_widget_medical_record.set_db_data(sql, self._set_medical_data)
        self.ui.tableWidget_medicine_sales.setFocus()

    def _set_medical_data(self, row_no, row):
        total_dosage = number_utils.get_float(row['TotalDosage'])
        total_amount = round(number_utils.get_float(row['Price']) * total_dosage, 2)

        case_key = row['CaseKey']
        patient_key = row['PatientKey']
        medicine_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(patient_key),
            string_utils.xstr(row['Name']),
            total_dosage,
            total_amount,
        ]

        for col_no in range(len(medicine_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medicine_record[col_no])
            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no, item,
            )

            if col_no in [2, 4, 5]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def start_calculate(self):
        self.ui.tableWidget_medicine_sales.itemSelectionChanged.disconnect()
        self._read_prescript()
        self._calculate_total()
        # self._plot_chart()
        self._item_selection_changed()
        self.ui.tableWidget_medicine_sales.itemSelectionChanged.connect(self._item_selection_changed)

    def _get_sql(self, assign_medicine=None, group_by_medicine=False, return_goods=False):
        # ins_type_condition = ''
        # if self.ins_type != '全部':
        #     ins_type_condition = f'cases.InsType = "{self.ins_type}" AND'

        if self.ins_type == '健保':
            ins_type_condition = 'AND prescript.MedicineSet = 1'
        elif self.ins_type == '自費':
            ins_type_condition = 'AND prescript.MedicineSet >= 2'
        else:
            ins_type_condition = ''

        medicine_name_condition = ''
        if assign_medicine is not None:
            medicine_name_condition = f'AND prescript.MedicineName = "{assign_medicine}" '

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f'AND cases.Doctor = "{self.doctor}"'

        if assign_medicine is not None:
            dosage_condition = ''
        elif return_goods:
            dosage_condition = 'AND prescript.Dosage < 0'
        else:
            dosage_condition = 'AND prescript.Dosage > 0'

        sql = f'''
            SELECT
                cases.CaseKey, cases.CaseDate, cases.PatientKey, cases.Name,
                prescript.MedicineName, prescript.Unit, prescript.Price, prescript.Amount,
                IFNULL(SUM(prescript.Dosage * IF(dosage.Days, dosage.Days, 1)), 0) AS TotalDosage,
                IFNULL(SUM(prescript.Dosage * prescript.Price * IF(dosage.Days, dosage.Days, 1)), 0) AS TotalAmount,
                medicine.InPrice, medicine.SalePrice, medicine.Location
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
                LEFT JOIN dosage ON prescript.CaseKey = dosage.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                prescript.MedicineType = "{self.medicine_type}" AND
                (dosage.MedicineSet = prescript.MedicineSet)
                {ins_type_condition}
                {medicine_name_condition}
                {doctor_condition}
                {dosage_condition}
        '''

        if group_by_medicine:
            sql += 'GROUP BY prescript.MedicineName'
        else:
            sql += 'GROUP BY cases.CaseKey ORDER BY DATE(cases.CaseDate), cases.PatientKey'

        return sql

    def _read_prescript(self):
        self.ui.tableWidget_medicine_sales.setRowCount(0)

        sql = self._get_sql(group_by_medicine=True)
        self.table_widget_medicine_sales.set_db_data(sql, self._set_table_data)
        self.ui.tableWidget_medicine_sales.sortItems(1, QtCore.Qt.DescendingOrder)
        self.ui.tableWidget_medicine_sales.setCurrentCell(0, 0)
        self._set_return_goods()

    def _calculate_total(self):
        row_count = self.ui.tableWidget_medicine_sales.rowCount()
        total_quantity, in_price_total, sale_price_total, profit_total = 0, 0, 0, 0

        for row_no in range(row_count):
            try:
                total_quantity += number_utils.get_integer(
                    self.ui.tableWidget_medicine_sales.item(row_no, 2).text())
            except Exception:
                pass

            try:
                in_price_total += number_utils.get_integer(
                    self.ui.tableWidget_medicine_sales.item(row_no, 4).text())
            except Exception:
                pass

            try:
                sale_price_total += number_utils.get_integer(
                    self.ui.tableWidget_medicine_sales.item(row_no, 5).text())
            except Exception:
                pass

            try:
                profit_total += number_utils.get_integer(
                    self.ui.tableWidget_medicine_sales.item(row_no, 6).text())
            except Exception:
                pass

        total_record = [
            '合計',
            None,
            string_utils.xstr(total_quantity),
            None,
            string_utils.xstr(in_price_total),
            string_utils.xstr(sale_price_total),
            string_utils.xstr(profit_total),
        ]

        self.ui.tableWidget_medicine_sales.setRowCount(row_count+1)

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_medicine_sales.setItem(
                row_count, col_no,
                QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [2, 4, 5, 6]:
                self.ui.tableWidget_medicine_sales.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_medicine_sales.item(row_count, col_no).setFont(font)

    def _set_table_data(self, row_no, row):
        total_dosage = number_utils.get_float(row['TotalDosage'])
        in_price = number_utils.get_float(row['InPrice']) * total_dosage
        sale_price = number_utils.get_float(row['TotalAmount'])
        if sale_price > 0:
            profit = sale_price - in_price
        else:
            profit = 0

        medicine_name = string_utils.xstr(row['MedicineName'])
        location = string_utils.xstr(row['Location'])

        medicine_record = [
            medicine_name,
            location,
            total_dosage,
            string_utils.xstr(row['Unit']),
            in_price,
            sale_price,
            profit,
        ]

        for col_no in range(len(medicine_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medicine_record[col_no])
            self.ui.tableWidget_medicine_sales.setItem(
                row_no, col_no, item,
            )

            if col_no in [2, 4, 5, 6]:
                self.ui.tableWidget_medicine_sales.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3]:
                self.ui.tableWidget_medicine_sales.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出用藥統計",
            f'{start_date}至{end_date}{self.medicine_type}{self.doctor}用藥統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medicine_sales, None, [2, 3, 4, 5, 6]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>用藥統計統計檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def export_detail_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出用藥病歷",
            f'{start_date}至{end_date}{self.medicine_type}用藥病歷.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0], [4]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>用藥病歷明細檔{excel_file_name}匯出完成.</h3>',
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

        self._plot_medicine_chart()

    def _plot_medicine_chart(self):
        medicine_list = []
        for row_no in range(10):
            medicine = [
                self.ui.tableWidget_medicine_sales.item(row_no, 0),
                self.ui.tableWidget_medicine_sales.item(row_no, 1),
            ]
            if medicine[0] is None:
                continue

            medicine_list.append(medicine)

        series = QtChart.QBarSeries()
        bar_set = []
        for i in range(len(medicine_list)):
            bar_set.append(QtChart.QBarSet(medicine_list[i][0].text()))
            bar_set[i] << number_utils.get_float(medicine_list[i][1].text())
            series.append([bar_set[i]])

        chart = QtChart.QChart()
        chart.addSeries(series)
        chart.setTitle('用藥統計表')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['用藥統計']
        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.addAxis(axis, QtCore.Qt.AlignBottom)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(450)
        self.ui.horizontalLayout_income.addWidget(self.chartView)

    def _set_return_goods(self):
        sql = self._get_sql(group_by_medicine=True, return_goods=True)
        rows = self.database.select_record(sql)
        for row in rows:
            medicine_name = string_utils.xstr(row['MedicineName'])
            real_medicine_name = re.sub(r'[（(](退貨|換貨)[）)]', '', medicine_name).strip()            
            
            for row_no in range(self.ui.tableWidget_medicine_sales.rowCount()):
                medicine_name_item = self.ui.tableWidget_medicine_sales.item(row_no, 0)
                if medicine_name_item is None:
                    continue

                current_medicine_name = medicine_name_item.text()
                if '退貨' in current_medicine_name or '換貨' in current_medicine_name:
                    continue
                
                if real_medicine_name == self.ui.tableWidget_medicine_sales.item(row_no, 0).text():
                    total_dosage = number_utils.get_float(row['TotalDosage'])
                    in_price = number_utils.get_float(row['InPrice'])
                    sale_price = number_utils.get_float(row['Price'])
                    total_in_price = round(total_dosage * in_price, 2)
                    total_sale_price = round(total_dosage * sale_price, 2)

                    self.ui.tableWidget_medicine_sales.insertRow(row_no+1)
                    self._set_cell(row_no+1, 0, medicine_name, align=QtCore.Qt.AlignLeft)
                    self._set_cell(row_no+1, 1, self.ui.tableWidget_medicine_sales.item(row_no, 1).text())
                    self._set_cell(row_no+1, 2, total_dosage)
                    self._set_cell(
                        row_no+1, 3, self.ui.tableWidget_medicine_sales.item(row_no, 3).text(),
                        align=QtCore.Qt.AlignCenter)
                    self._set_cell(row_no+1, 4, self.ui.tableWidget_medicine_sales.item(row_no, 4).text())
                    self._set_cell(row_no+1, 5, sale_price * total_dosage)                    
                    
    def _set_cell(self, row_no, col_no, value, align=QtCore.Qt.AlignRight):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, value)
        self.ui.tableWidget_medicine_sales.setItem(row_no, col_no, item)
        self.ui.tableWidget_medicine_sales.item(
            row_no, col_no).setTextAlignment(align | QtCore.Qt.AlignVCenter)
        self.ui.tableWidget_medicine_sales.item(row_no, col_no).setForeground(QtGui.QColor('red'))
        

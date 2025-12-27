# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils


# 分院專案統計內容 2021.02.09
class StatisticsBranchProjectSales(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsBranchProjectSales, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.database_list = args[1]
        self.system_settings = args[2]
        self.start_date = args[3]
        self.end_date = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
        self.project_name = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_BRANCH_PROJECT_SALES, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_branch_project_sales = class_utils.get_table_widget(
            self.ui.tableWidget_branch_project_sales, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            150, 120, 90, 100, 250, 60, 60, 70, 90, 70, 100, 80,
        ]
        self.table_widget_branch_project_sales.set_table_heading_width(width)
        self.table_widget_branch_project_sales.set_column_hidden([0])

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_branch_project_sales.doubleClicked.connect(self.open_medical_record)
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_medical_record(self):
        clinic_name = self.table_widget_branch_project_sales.field_value(1)
        if self.system_settings.field('院所名稱') != clinic_name:
            system_utils.show_message_box(
                QMessageBox.Warning,
                '無法開啟病歷',
                '<h3>此病歷非本院病患所有, 無法開啟.</h3>',
                f'請使用{clinic_name}系統讀取.'
            )
            return

        case_key = self.table_widget_branch_project_sales.field_value(0)
        self.parent.parent.open_medical_record(case_key, '病歷查詢')

    def start_calculate(self):
        self.ui.tableWidget_branch_project_sales.setRowCount(0)

        for clinic_name in self.database_list:
            database = self.database_list[clinic_name]['database']
            self._calculate_project_sales(database, clinic_name)

        self.ui.tableWidget_branch_project_sales.sortItems(1, QtCore.Qt.AscendingOrder)
        self._calculate_total()
        self._plot_chart()

    def _calculate_project_sales(self, database, clinic_name):
        ins_type_condition = f' AND InsType = "{self.ins_type}"' if self.ins_type != '全部' else ''
        doctor_type_condition = f' AND Doctor = "{self.doctor}"' if self.doctor != '全部' else ''

        sql = f'''
            SELECT
                cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
                prescript.MedicineName, prescript.Dosage, prescript.Unit, prescript.MedicineSet,
                prescript.Price, prescript.Amount, prescript.DiscountFee,
                medicine.InPrice, medicine.SalePrice, medicine.Project, medicine.Commission
            FROM prescript
                LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                prescript.MedicineSet >= 2 AND
                medicine.Project IS NOT NULL AND
                medicine.Project= "{self.project_name}"
                {ins_type_condition}
                {doctor_type_condition}
        '''
        rows = database.select_record(sql)
        for row in rows:
            self._add_record_to_table(database, row, clinic_name)

    def _add_record_to_table(self, database, row, clinic_name):
        row_no = self.ui.tableWidget_branch_project_sales.rowCount()
        self.ui.tableWidget_branch_project_sales.setRowCount(row_no+1)

        case_key = row['CaseKey']
        medicine_set = number_utils.get_integer(row['MedicineSet'])
        dosage = number_utils.get_float(row['Dosage'])
        price = number_utils.get_float(row['Price'])
        amount = number_utils.get_float(row['Amount'])
        in_price = number_utils.get_float(row['InPrice'])
        sale_price = number_utils.get_float(row['SalePrice'])
        commission = string_utils.xstr(row['Commission'])

        if commission == '':
            percent = 0
        elif '%' in commission:
            percent = number_utils.get_integer(commission.replace('%', ''))
        else:
            percent = number_utils.get_integer(commission)

        try:
            # discount_rate = number_utils.round_up((receipt_fee / amount) * 100)
            discount_rate = case_utils.get_discount_rate(database, case_key, medicine_set)
        except Exception:
            discount_rate = 100

        receipt_fee = amount * discount_rate / 100
        cost = number_utils.round_up((in_price * dosage) + (sale_price * percent / 100))

        medicine_record = [
            case_key,
            clinic_name,
            row['CaseDate'].date().strftime("%Y-%m-%d"),
            row['PatientKey'],
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['MedicineName']),
            dosage,
            string_utils.xstr(row['Unit']),
            price,
            receipt_fee,
            f'{discount_rate}%',
            string_utils.xstr(row['Doctor']),
            cost,
        ]

        for col_no in range(len(medicine_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medicine_record[col_no])
            self.ui.tableWidget_branch_project_sales.setItem(
                row_no, col_no, item,
            )

            if col_no in [3, 6, 8, 9, 10, 12]:
                self.ui.tableWidget_branch_project_sales.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [7]:
                self.ui.tableWidget_branch_project_sales.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _calculate_total(self):
        row_count = self.ui.tableWidget_branch_project_sales.rowCount()

        subtotal, total_cost = 0, 0
        for row_no in range(row_count):
            total_fee_item = self.ui.tableWidget_branch_project_sales.item(row_no, 9)
            total_cost_item = self.ui.tableWidget_branch_project_sales.item(row_no, 12)

            total_fee = total_fee_item if total_fee_item is not None else '0'
            cost = total_cost_item if total_cost_item is not None else '0'

            subtotal += number_utils.get_float(float(total_fee.text()))
            total_cost += number_utils.get_float(float(cost.text()))

        self.ui.tableWidget_branch_project_sales.setRowCount(row_count+1)

        items = [
            [8, '總計'],
            [9, subtotal],
            [12, total_cost]
        ]

        for cell in items:
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, cell[1])
            self.ui.tableWidget_branch_project_sales.setItem(row_count, cell[0], item)
            self.ui.tableWidget_branch_project_sales.item(
                row_count, cell[0]).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出用藥統計",
            f'{start_date}至{end_date}{self.project_name}用藥統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medicine_sales, None, [1, 3, 4, 5]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>用藥統計統計檔{excel_file_name}匯出完成.</h3>',
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

        # self._plot_medicine_chart()

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

        self.chartView.setFixedWidth(950)
        self.ui.horizontalLayout_income.addWidget(self.chartView)

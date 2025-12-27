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
from libs import case_utils
from libs import date_utils


# 醫師統計 2019.05.02
class StatisticsMedicalRecordDiseaseRank(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsMedicalRecordDiseaseRank, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.ins_type = args[4]
        self.doctor = args[5]
        self.option = args[6]
        self.weekday_list = args[7]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_MEDICAL_RECORD_DISEASE_RANK, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_disease_rank = class_utils.get_table_widget(
            self.ui.tableWidget_disease_rank, self.database
        )
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        self.table_widget_disease_rank.set_table_heading_width([100, 560, 100, 100, 100])
        self.table_widget_medical_record.set_table_heading_width(
            [100, 90, 100, 60, 150, 70, 120]
        )

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_disease_rank.itemSelectionChanged.connect(self._disease_changed)
        self.ui.tableWidget_medical_record.doubleClicked.connect(self._open_medical_record)

    def _open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        if case_key is None:
            return

        self.parent.parent.open_medical_record(case_key)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self._calculate_data()
        self.ui.tableWidget_disease_rank.setCurrentCell(0, 1)

    def _calculate_data(self):
        self._read_data()
        self._calculate_percent()
        self._plot_rank_chart()

    def _read_data(self):
        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = f' AND InsType = "{self.ins_type}"'

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option, exclude=False)

        weekday_condition = case_utils.get_weekday_list_sql(self.weekday_list)

        sql = f'''
            SELECT
                PatientKey, DiseaseCode1, DiseaseName1
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY DiseaseCode1
        '''
        rows = self.database.select_record(sql)
        self._set_table_data(rows)

    def _set_table_data(self, rows):
        disease_dict = {}

        max_progress = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在統計資料中, 請稍後...', '取消', 0, max_progress, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        i = 0
        for row in rows:
            i += 1
            progress_dialog.setValue(i)

            disease_code = string_utils.xstr(row['DiseaseCode1'])
            if disease_code == '':
                continue
            
            patient_key = row['PatientKey']
            if disease_code not in disease_dict:
                disease_dict[disease_code] = [string_utils.xstr(row['DiseaseName1']), 1, [patient_key], 1]
            else:
                disease_dict[disease_code][3] += 1

                if patient_key not in disease_dict[disease_code][2]:  # 只統計歸戶人數
                    disease_dict[disease_code][1] += 1
                    disease_dict[disease_code][2].append(patient_key)

        progress_dialog.setValue(max_progress)

        self.ui.tableWidget_disease_rank.setRowCount(0)
        for row_no, row in enumerate(disease_dict.items()):
            self.ui.tableWidget_disease_rank.insertRow(row_no)
            disease_row = [row[0], row[1][0], row[1][1], row[1][3]]
            for col_no in range(len(disease_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, disease_row[col_no])
                self.ui.tableWidget_disease_rank.setItem(
                    row_no, col_no, item,
                )
                if col_no in [2, 3]:
                    self.ui.tableWidget_disease_rank.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )

        self.ui.tableWidget_disease_rank.resizeRowsToContents()
        self.ui.tableWidget_disease_rank.sortItems(2, QtCore.Qt.DescendingOrder)
        self.ui.tableWidget_disease_rank.setRowCount(10)

    def _get_row_no(self, disease_code):
        for row_no in range(self.ui.tableWidget_disease_rank.rowCount()):
            item = self.ui.tableWidget_disease_rank.item(row_no, 0)
            if item is None:
                continue

            if disease_code == item.text():
                return row_no

        self.ui.tableWidget_disease_rank.setRowCount(
            self.ui.tableWidget_disease_rank.rowCount() + 1
        )

        return self.ui.tableWidget_disease_rank.rowCount()

    def export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出疾病排行",
            f'{start_date}至{end_date}{self.doctor}醫師門診門診疾病排行.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_disease_rank, None, [2],
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>疾病排行檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _calculate_percent(self):
        total_person = 0
        for row_no in range(self.ui.tableWidget_disease_rank.rowCount()):
            item = self.ui.tableWidget_disease_rank.item(row_no, 2)
            if item is None:
                continue

            total_person += number_utils.get_integer(item.text())

        for row_no in range(self.ui.tableWidget_disease_rank.rowCount()):
            item = self.ui.tableWidget_disease_rank.item(row_no, 2)
            if item is None:
                continue

            person_count = number_utils.get_integer(item.text())
            percent = f'{round(person_count / total_person * 100, 2)}%'
            self.ui.tableWidget_disease_rank.setItem(
                row_no, 4, QtWidgets.QTableWidgetItem(percent))
            self.ui.tableWidget_disease_rank.item(
                row_no, 4).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def _plot_rank_chart(self):
        self._plot_diseaes_rank_chart()
        self._plot_age_rank_chart()
        self._plot_gender_rank_chart()

    def _plot_diseaes_rank_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        disease_list = []

        for row_no in range(10):
            disease = [
                self.ui.tableWidget_disease_rank.item(row_no, 1),
                self.ui.tableWidget_disease_rank.item(row_no, 2),
            ]
            if disease[0] is None:
                continue

            disease_list.append(disease)

        # series = QtChart.QBarSeries()
        # bar_set = []
        # for i in range(len(disease_list)):
        #     bar_set.append(QtChart.QBarSet(disease_list[i][0].text()))
        #     bar_set[i] << number_utils.get_float(disease_list[i][1].text())
        #     series.append([bar_set[i]])

        series = QtChart.QPieSeries()
        for i in range(len(disease_list)):
            series.append(disease_list[i][0].text(), number_utils.get_integer(disease_list[i][1].text()))

        for slice in series.slices():
            slice.setLabel(f'{slice.label()[:5]}: {int(slice.value())}')

        chart = QtChart.QChart()
        chart.addSeries(series)
        # chart.setTitle('就醫疾病排行Top10')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['疾病排行']
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
        self.chartView.setFixedHeight(330)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _get_age_list(self):
        age_list = []
        for row_no in range(self.ui.tableWidget_disease_rank.rowCount()):
            self.ui.tableWidget_disease_rank.setCurrentCell(row_no, 1)
            age, _ = self._disease_changed()
            if age is None:
                continue

            age_list += age

        return age_list

    def _get_gender_list(self):
        gender_list = []
        for row_no in range(self.ui.tableWidget_disease_rank.rowCount()):
            self.ui.tableWidget_disease_rank.setCurrentCell(row_no, 1)
            _, gender = self._disease_changed()
            if gender is None:
                continue

            gender_list += gender

        return gender_list

    def _plot_age_rank_chart(self):
        while self.ui.verticalLayout_rank_age.count():
            item = self.ui.verticalLayout_rank_age.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        age_dict = {
            '0-10': 0,
            '11-20': 0,
            '21-30': 0,
            '31-40': 0,
            '41-50': 0,
            '51-60': 0,
            '61-70': 0,
            '71-80': 0,
            '81-90': 0,
            '91-100': 0,
            '>100': 0,
        }
        age_list = self._get_age_list()
        for age in age_list:
            if age is None:
                continue

            if 0 <= age <= 10:
                age_dict['0-10'] += 1
            elif 11 <= age <= 20:
                age_dict['11-20'] += 1
            elif 21 <= age <= 30:
                age_dict['21-30'] += 1
            elif 31 <= age <= 40:
                age_dict['31-40'] += 1
            elif 41 <= age <= 50:
                age_dict['41-50'] += 1
            elif 51 <= age <= 60:
                age_dict['51-60'] += 1
            elif 61 <= age <= 70:
                age_dict['61-70'] += 1
            elif 71 <= age <= 80:
                age_dict['71-80'] += 1
            elif 81 <= age <= 90:
                age_dict['81-90'] += 1
            elif 91 <= age <= 100:
                age_dict['91-100'] += 1
            elif age > 100:
                age_dict['>100'] += 1

        age_list = []
        for key in age_dict.keys():
            age_list.append([key, age_dict[key]])

        # series = QtChart.QBarSeries()
        # bar_set = []
        # for i in range(len(age_list)):
        #     bar_set.append(QtChart.QBarSet(age_list[i][0]))
        #     bar_set[i] << number_utils.get_float(age_list[i][1])
        #     series.append([bar_set[i]])

        series = QtChart.QPieSeries()
        for i in range(len(age_list)):
            series.append(age_list[i][0], number_utils.get_integer(age_list[i][1]))

        for slice in series.slices():
            slice.setLabel(f'{slice.label()}: {int(slice.value())}')

        chart = QtChart.QChart()
        chart.addSeries(series)
        # chart.setTitle('就醫疾病排行Top10')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['年齡']
        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.addAxis(axis, QtCore.Qt.AlignBottom)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(350)
        self.chartView.setFixedHeight(330)
        self.ui.verticalLayout_rank_age.addWidget(self.chartView)

    def _plot_gender_rank_chart(self):
        while self.ui.verticalLayout_rank_gender.count():
            item = self.ui.verticalLayout_rank_gender.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        gender_dict = {'男': 0, '女': 0}

        gender_list = self._get_gender_list()
        for gender in gender_list:
            if gender in ['男', '女']:
                gender_dict[gender] += 1

        gender_list = [['男', gender_dict['男']], ['女', gender_dict['女']]]

        # series = QtChart.QBarSeries()
        # bar_set = []
        # for i in range(len(gender_list)):
        #     bar_set.append(QtChart.QBarSet(gender_list[i][0]))
        #     bar_set[i] << number_utils.get_float(gender_list[i][1])
        #     series.append([bar_set[i]])

        series = QtChart.QPieSeries()
        for i in range(len(gender_list)):
            series.append(gender_list[i][0], number_utils.get_integer(gender_list[i][1]))

        for slice in series.slices():
            slice.setLabel(f'{slice.label()}: {int(slice.value())}')

        chart = QtChart.QChart()
        chart.addSeries(series)
        # chart.setTitle('就醫疾病排行Top10')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['性別']
        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.addAxis(axis, QtCore.Qt.AlignBottom)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(300)
        self.chartView.setFixedHeight(330)
        self.ui.verticalLayout_rank_gender.addWidget(self.chartView)

    def _disease_changed(self):
        disease_code = self.ui.tableWidget_disease_rank.item(
            self.ui.tableWidget_disease_rank.currentRow(), 0
        )

        if disease_code is None:
            return [None], [None]

        disease_code = disease_code.text()
        age_list, gender_list = self._read_medical_record(disease_code)

        return age_list, gender_list

    def _read_medical_record(self, disease_code):
        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = f' AND cases.InsType = "{self.ins_type}"'

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option, exclude=False)
        weekday_condition = case_utils.get_weekday_list_sql(self.weekday_list)

        sql = f'''
            SELECT cases.CaseKey, cases.PatientKey, cases.Name,
                   patient.Gender, patient.Birthday, patient.Address
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                DiseaseCode1 = "{disease_code}"
                {weekday_condition}
                {regist_condition}
                {ins_type_condition}
                {doctor_condition}
            GROUP BY PatientKey
            ORDER BY PatientKey
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_medical_record)

        age_list = []
        gender_list = []
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            gender = self.ui.tableWidget_medical_record.item(row_no, 3).text()
            age = number_utils.get_integer(self.ui.tableWidget_medical_record.item(row_no, 5).text())

            gender_list.append(gender)
            age_list.append(age)

        self._plot_chart_patient()

        return age_list, gender_list

    def _plot_chart_patient(self):
        self._plot_chart_gender()
        self._plot_chart_age()

    def _set_medical_record(self, row_no, row):
        age_year, _ = date_utils.get_age(row['Birthday'], datetime.datetime.now().date())
        if age_year is None:
            age_year = ''

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            # string_utils.xstr(row['CaseDate'].date()),
            # string_utils.xstr(row['InsType']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(age_year),
            string_utils.xstr(row['Address'])[:6],
        ]

        for col_no in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record[col_no])
            )

            if col_no in [3]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif col_no in [1, 5]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _plot_chart_gender(self):
        while self.ui.verticalLayout_gender.count():
            item = self.ui.verticalLayout_gender.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        gender_dict = {'男': 0, '女': 0}

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            gender_item = self.ui.tableWidget_medical_record.item(row_no, 3)
            if gender_item is None:
                continue

            gender = gender_item.text()
            if gender in ['男', '女']:
                gender_dict[gender] += 1

        gender_list = [['男', gender_dict['男']], ['女', gender_dict['女']]]

        series = QtChart.QPieSeries()
        for i in range(len(gender_list)):
            series.append(gender_list[i][0], number_utils.get_integer(gender_list[i][1]))

        for slice in series.slices():
            slice.setLabel(f'{slice.label()}: {int(slice.value())}')

        chart = QtChart.QChart()
        chart.addSeries(series)
        # chart.setTitle('就醫疾病排行Top10')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['性別']
        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.addAxis(axis, QtCore.Qt.AlignBottom)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedWidth(250)
        self.chartView.setFixedHeight(330)
        self.ui.verticalLayout_gender.addWidget(self.chartView)

    def _plot_chart_age(self):
        while self.ui.verticalLayout_age.count():
            item = self.ui.verticalLayout_age.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        age_dict = {
            '10以下': 0,
            '11-20': 0,
            '21-30': 0,
            '31-40': 0,
            '41-50': 0,
            '51-60': 0,
            '61-70': 0,
            '71-80': 0,
            '81-90': 0,
            '90以上': 0,
        }

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            age_item = self.ui.tableWidget_medical_record.item(row_no, 5)
            if age_item is None:
                continue

            age = number_utils.get_integer(age_item.text())
            if age <= 10:
                age_dict['10以下'] += 1
            elif 11 <= age <= 20:
                age_dict['11-20'] += 1
            elif 21 <= age <= 30:
                age_dict['21-30'] += 1
            elif 31 <= age <= 40:
                age_dict['31-40'] += 1
            elif 41 <= age <= 50:
                age_dict['41-50'] += 1
            elif 51 <= age <= 60:
                age_dict['51-60'] += 1
            elif 61 <= age <= 70:
                age_dict['61-70'] += 1
            elif 71 <= age <= 80:
                age_dict['71-80'] += 1
            elif 81 <= age <= 90:
                age_dict['81-90'] += 1
            elif age > 90:
                age_dict['90以上'] += 1

        age_list = []
        for key in age_dict.keys():
            age_list.append([key, age_dict[key]])

        # series = QtChart.QBarSeries()
        # bar_set = []
        # for i in range(len(age_list)):
        #     bar_set.append(QtChart.QBarSet(age_list[i][0]))
        #     bar_set[i] << number_utils.get_float(age_list[i][1])
        #     series.append([bar_set[i]])

        series = QtChart.QPieSeries()
        for i in range(len(age_list)):
            series.append(age_list[i][0], number_utils.get_integer(age_list[i][1]))

        for slice in series.slices():
            slice.setLabel(f'{slice.label()}: {int(slice.value())}')

        chart = QtChart.QChart()
        chart.addSeries(series)
        # chart.setTitle('就醫疾病排行Top10')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        categories = ['年齡統計']
        axis = QtChart.QBarCategoryAxis()
        axis.append(categories)
        chart.createDefaultAxes()
        chart.addAxis(axis, QtCore.Qt.AlignBottom)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(QtCore.Qt.AlignRight)
        # chart.legend().hide()

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        # self.chartView.setFixedWidth(500)
        self.chartView.setFixedHeight(330)
        self.ui.verticalLayout_age.addWidget(self.chartView)

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import personnel_utils
from libs import system_utils
from libs import number_utils
from libs import pregnant_utils
from libs import module_utils


# 病歷資料 2018.01.31
class PregnantMale(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PregnantMale, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.call_from = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()

        self.user_name = system_utils.get_user_name(self.system_settings)
        self._set_permission()
        self._read_current_data()
        self._read_past_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PREGNANT_MALE, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_past_pregnant = class_utils.get_table_widget(
            self.ui.tableWidget_past_pregnant, self.database
        )
        self.table_widget_past_pregnant.set_column_hidden([0, 1])
        self.ui.dateEdit_exam_date.setDate(self.parent.medical_record['CaseDate'].date())
        self._set_physique_table()
        self.ui.tableWidget_past_pregnant.setStyleSheet('''
            QTableWidget:!active {
                selection-background-color: palette(Highlight);
                selection-color: palette(HighlightedText)
            }
        ''')

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_copy.clicked.connect(self.copy_pregnant_data)
        self.ui.toolButton_save.clicked.connect(self.save_pregnant_data)
        self.ui.tableWidget_past_pregnant.itemSelectionChanged.connect(self._past_pregnant_changed)

    def _set_physique_table(self):
        self.tab_physique = module_utils.get_physique_table(
            self, self.database, self.system_settings, self.case_key, self.call_from
        )
        self.ui.verticalLayout_physique.addWidget(self.tab_physique)

    def _set_permission(self):
        if self.call_from == '醫師看診作業':
            return

        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

    def _read_current_data(self, case_key=None, display_case_date_label=True):
        if case_key is None:
            case_key = self.case_key

        sql = f'''
            SELECT pregnant.*, cases.CaseDate, cases.Name, cases.Doctor FROM pregnant
                LEFT JOIN cases ON pregnant.CaseKey = cases.CaseKey
            WHERE
                pregnant.CaseKey = {case_key}
            ORDER BY cases.CaseDate DESC
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._insert_pregnant_data()
            rows = self.database.select_record(sql)

        row = rows[0]
        if display_case_date_label:
            pregnant_utils.set_case_label(row, self.ui.label_case_date)

        self._set_pregnant_data(row)
        self.tab_physique.set_row(row)

    def _set_pregnant_data(self, row):
        exam_date = row['OvulateDate']
        fertilization = string_utils.xstr(row['Fertilization'])

        self.ui.lineEdit_sperm.setText(string_utils.xstr(row['Sperm']))
        self.ui.lineEdit_yield.setText(string_utils.xstr(row['Yield']))
        self.ui.lineEdit_liquefaction.setText(string_utils.xstr(row['Liquefaction']))
        self.ui.lineEdit_impurity.setText(string_utils.xstr(row['Impurity']))
        self.ui.lineEdit_activity.setText(string_utils.xstr(row['Activity']))
        self.ui.lineEdit_spouse.setText(string_utils.xstr(row['Spouse']))
        self.ui.lineEdit_second_disease.setText(string_utils.xstr(row['DiseaseName']))
        self.ui.lineEdit_misc.setText(string_utils.xstr(row['Remark']))
        if exam_date is not None:
            self.ui.dateEdit_exam_date.setDate(exam_date)

        if fertilization == 'Y':
            self.ui.checkBox_fertilization.setChecked(True)
        else:
            self.ui.checkBox_fertilization.setChecked(False)

    def _insert_pregnant_data(self):
        fields = [
            'CaseKey', 'PatientKey', 'PhysiqueLine',
            'AnxietyLine', 'Fertilization',
        ]
        data = [
            self.case_key, self.parent.patient_record['PatientKey'],
            'NNNNNNNNN', '0000000000', 'N'
        ]
        self.database.insert_record('pregnant', fields, data)

    def _read_past_data(self):
        sql = f'''
            SELECT pregnant.*, cases.CaseDate FROM pregnant
                LEFT JOIN cases ON pregnant.CaseKey = cases.CaseKey
            WHERE
                pregnant.PatientKey = {self.parent.patient_record['PatientKey']}
            ORDER BY cases.CaseDate DESC
        '''

        self.table_widget_past_pregnant.set_db_data(sql, self._set_table_data)
        self._set_current_date_position()
        self._plot_chart()

    def _set_current_date_position(self):
        case_date = string_utils.xstr(self.parent.medical_record['CaseDate'].date())
        for row_no in range(self.ui.tableWidget_past_pregnant.rowCount()):
            if self.ui.tableWidget_past_pregnant.item(row_no, 2).text() == case_date:
                self.ui.tableWidget_past_pregnant.setCurrentCell(row_no, 2)
                break

    def _set_table_data(self, row_no, row):
        fertilization = string_utils.xstr(row['Fertilization'])
        if fertilization == 'Y':
            fertilization = '是'
        elif fertilization == 'N':
            fertilization = '否'
        else:
            fertilization = ''

        case_date = row['CaseDate']
        if case_date is not None:
            case_date = case_date.date()

        pregnant_row = [
            string_utils.xstr(row['PregnantKey']),
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(case_date),
            string_utils.xstr(row['OvulateTemperature']),
            string_utils.xstr(row['Sperm']),
            string_utils.xstr(row['Yield']),
            string_utils.xstr(row['Liquefaction']),
            string_utils.xstr(row['Activity']),
            fertilization,
        ]

        for col_no in range(len(pregnant_row)):
            self.ui.tableWidget_past_pregnant.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(pregnant_row[col_no])
            )
            # if col_no in [3, 4, 5, 6, 8]:
            #     self.ui.tableWidget_past_pregnant.item(
            #         row_no, col_no).setTextAlignment(
            #         QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            #     )
            if col_no in [8]:
                self.ui.tableWidget_past_pregnant.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def copy_pregnant_data(self):
        pregnant_utils.copy_pregnant_data(self, self.ui.tableWidget_past_pregnant, self._read_current_data)

    def save_pregnant_data(self):
        pregnant_key = self.table_widget_past_pregnant.field_value(0)
        physique_line = self.tab_physique.get_physique_line()
        anxiety_line = self.tab_physique.get_anxiety_line()
        anxiety_grade = self.tab_physique.get_anxiety_grade()

        if self.ui.checkBox_fertilization.isChecked():
            fertilization = 'Y'
        else:
            fertilization = 'N'

        fields = [
            'Sperm', 'Yield',
            'Liquefaction', 'Impurity',
            'Activity', 'Spouse',
            'DiseaseName', 'Remark',
            'OvulateDate', 'Fertilization',
            'PhysiqueLine', 'AnxietyLine', 'AnxietyGrade'
        ]
        data = [
            self.ui.lineEdit_sperm.text(),
            self.ui.lineEdit_yield.text(),
            self.ui.lineEdit_liquefaction.text(),
            self.ui.lineEdit_impurity.text(),
            self.ui.lineEdit_activity.text(),
            self.ui.lineEdit_spouse.text(),
            self.ui.lineEdit_second_disease.text(),
            self.ui.lineEdit_misc.text(),
            self.ui.dateEdit_exam_date.date().toString('yyyy-MM-dd'),
            fertilization,
            physique_line, anxiety_line,
            anxiety_grade,
        ]
        self.database.update_record('pregnant', fields, 'PregnantKey', pregnant_key, data)
        self._refresh_pregnant_row()

    def _refresh_pregnant_row(self):
        pregnant_key = self.table_widget_past_pregnant.field_value(0)
        if pregnant_key is None:
            return

        sql = f'''
            SELECT pregnant.*, cases.CaseDate FROM pregnant
                LEFT JOIN cases ON pregnant.CaseKey = cases.CaseKey
            WHERE
                PregnantKey = {pregnant_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        current_row = self.ui.tableWidget_past_pregnant.currentRow()
        self._set_table_data(current_row, row)

    def _past_pregnant_changed(self):
        case_key = self.table_widget_past_pregnant.field_value(1)
        if case_key is None:
            return

        self._read_current_data(case_key)

    def _plot_chart(self):
        while self.ui.verticalLayout_chart.count():
            item = self.ui.verticalLayout_chart.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._plot_chart_sperm()

    def _plot_chart_sperm(self):
        series_sperm = QtChart.QLineSeries(name='精蟲數')

        row_count = self.ui.tableWidget_past_pregnant.rowCount()
        for i, row_no in enumerate(range(row_count-1, -1, -1)):
            sperm = self.ui.tableWidget_past_pregnant.item(row_no, 4)
            if sperm is None:
                continue

            sperm = number_utils.get_integer(sperm.text())
            series_sperm.append(i, sperm)

        chart = QtChart.QChart()
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        chart.addSeries(series_sperm)
        chart.createDefaultAxes()

        chart.setTitle('精蟲數')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(300)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

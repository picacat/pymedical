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
class PregnantFemale(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PregnantFemale, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PREGNANT_FEMALE, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_past_pregnant = class_utils.get_table_widget(
            self.ui.tableWidget_past_pregnant, self.database
        )
        self.table_widget_past_pregnant.set_column_hidden([0, 1])
        self.ui.dateEdit_ovulation_date.setDate(self.parent.medical_record['CaseDate'].date())
        self._set_combo_box()
        self._set_physique_table()
        self.ui.tableWidget_past_pregnant.setStyleSheet('''
            QTableWidget:!active {
                selection-background-color: palette(Highlight);
                selection-color: palette(HighlightedText)
            }
        ''')

    def _set_combo_box(self):
        ui_utils.set_combo_box(
            self.ui.comboBox_low_temperature,
            [
                '1-少於10天',
                '2-11至20天',
                '3-21天以上',
                '4-高低溫紊亂無規律',
             ]
        )
        self.ui.comboBox_low_temperature.setCurrentIndex(1)
        ui_utils.set_combo_box(
            self.ui.comboBox_high_temperature,
            [
                '1-少於10天',
                '2-11至20天',
                '3-21天以上',
                '4-高低溫紊亂無規律',
             ]
        )
        self.ui.comboBox_high_temperature.setCurrentIndex(1)
        ui_utils.set_combo_box(
            self.ui.comboBox_western_cure,
            [
                '0-沒有',
                '1-西醫藥物治療',
                '2-人工受孕',
                '3-試管嬰兒',
             ]
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_ovulation_low_temperature_times,
            [
                '1->=2次',
                '2-1次',
                '3-無',
             ]
        )

    def _set_physique_table(self):
        self.tab_physique = module_utils.get_physique_table(
            self, self.database, self.system_settings, self.case_key, self.call_from
        )
        self.ui.verticalLayout_physique.addWidget(self.tab_physique)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_save.clicked.connect(self.save_pregnant_data)
        self.ui.toolButton_copy.clicked.connect(self.copy_pregnant_data)
        self.ui.tableWidget_past_pregnant.itemSelectionChanged.connect(self._past_pregnant_changed)

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
        low_temperature = row['LowTemperature']
        high_temperature = row['HighTemperature']
        ovulation_low_temperature_times = row['SymptomLine']
        ovulation_date = row['OvulateDate']
        western_cure = row['WesternCure']
        fertilization = string_utils.xstr(row['Fertilization'])
        birth_foetus = number_utils.get_integer(row['BirthFoetus'])
        stillbirth_foetus = number_utils.get_integer(row['StillFoetus'])

        if low_temperature is not None:
            try:
                self.ui.comboBox_low_temperature.setCurrentIndex(int(low_temperature)-1)
            except Exception:
                pass
        if high_temperature is not None:
            try:
                self.ui.comboBox_high_temperature.setCurrentIndex(int(high_temperature)-1)
            except Exception:
                pass
        if ovulation_low_temperature_times is not None:
            try:
                self.ui.comboBox_ovulation_low_temperature_times.setCurrentIndex(
                    int(ovulation_low_temperature_times)-1)
            except Exception:
                pass

        self.ui.lineEdit_follicle_days.setText(string_utils.xstr(row['FollDays']))
        self.ui.lineEdit_follicle_temperature.setText(string_utils.xstr(row['FollTemperature']))
        self.ui.lineEdit_luteal_days.setText(string_utils.xstr(row['LuteumDays']))
        self.ui.lineEdit_luteal_temperature.setText(string_utils.xstr(row['LuteumTemperature']))
        if ovulation_date is not None:
            self.ui.dateEdit_ovulation_date.setDate(ovulation_date)

        self.ui.lineEdit_ovulation_temperature.setText(string_utils.xstr(row['OvulateTemperature']))
        self.ui.lineEdit_second_disease.setText(string_utils.xstr(row['DiseaseName']))
        self.ui.lineEdit_misc.setText(string_utils.xstr(row['Remark']))
        self.ui.spinBox_birth_foetus.setValue(birth_foetus)
        self.ui.spinBox_stillbirth_foetus.setValue(stillbirth_foetus)

        if western_cure is not None:
            self.ui.comboBox_western_cure.setCurrentIndex(int(western_cure))

        if fertilization == 'Y':
            self.ui.checkBox_fertilization.setChecked(True)
        else:
            self.ui.checkBox_fertilization.setChecked(False)

    def _insert_pregnant_data(self):
        fields = [
            'CaseKey', 'PatientKey', 'LowTemperature', 'HighTemperature', 'PhysiqueLine',
            'AnxietyLine', 'Fertilization', 'WesternCure'
        ]
        data = [
            self.case_key, self.parent.patient_record['PatientKey'],
            '2', '2', 'NNNNNNNNN', '0000000000', 'N', '0'
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
            string_utils.xstr(row['FollDays']),
            string_utils.xstr(row['FollTemperature']),
            string_utils.xstr(row['LuteumDays']),
            string_utils.xstr(row['LuteumTemperature']),
            string_utils.xstr(row['OvulateDate']),
            string_utils.xstr(row['OvulateTemperature']),
            fertilization,
        ]

        for col_no in range(len(pregnant_row)):
            self.ui.tableWidget_past_pregnant.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(pregnant_row[col_no])
            )
            if col_no in [3, 4, 5, 6, 8]:
                self.ui.tableWidget_past_pregnant.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [9]:
                self.ui.tableWidget_past_pregnant.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def copy_pregnant_data(self):
        pregnant_utils.copy_pregnant_data(
            self, self.ui.tableWidget_past_pregnant, self._read_current_data)

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
            'LowTemperature', 'HighTemperature',
            'SymptomLine',
            'FollDays', 'FollTemperature',
            'LuteumDays', 'LuteumTemperature',
            'OvulateDate', 'OvulateTemperature',
            'DiseaseName', 'Remark',
            'BirthFoetus', 'StillFoetus',
            'WesternCure', 'Fertilization',
            'PhysiqueLine', 'AnxietyLine', 'AnxietyGrade'
        ]
        data = [
            self.ui.comboBox_low_temperature.currentIndex()+1,
            self.ui.comboBox_high_temperature.currentIndex()+1,
            self.ui.comboBox_ovulation_low_temperature_times.currentIndex()+1,
            self.ui.lineEdit_follicle_days.text(),
            self.ui.lineEdit_follicle_temperature.text(),
            self.ui.lineEdit_luteal_days.text(),
            self.ui.lineEdit_luteal_temperature.text(),
            self.ui.dateEdit_ovulation_date.date().toString('yyyy-MM-dd'),
            self.ui.lineEdit_ovulation_temperature.text(),
            self.ui.lineEdit_second_disease.text(),
            self.ui.lineEdit_misc.text(),
            self.ui.spinBox_birth_foetus.value(),
            self.ui.spinBox_stillbirth_foetus.value(),
            self.ui.comboBox_western_cure.currentIndex(),
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

        self._plot_chart_days()
        self._plot_chart_temperature()

    def _plot_chart_days(self):
        series_follicle = QtChart.QLineSeries(name='濾泡期天數')
        series_luteum = QtChart.QLineSeries(name='黃體期天數')

        row_count = self.ui.tableWidget_past_pregnant.rowCount()
        for i, row_no in enumerate(range(row_count-1, -1, -1)):
            follicle = self.ui.tableWidget_past_pregnant.item(row_no, 3)
            luteum = self.ui.tableWidget_past_pregnant.item(row_no, 5)
            if follicle is None:
                continue

            if luteum is None:
                continue

            follicle = number_utils.get_integer(follicle.text())
            luteum = number_utils.get_integer(luteum.text())

            series_follicle.append(i, follicle)
            series_luteum.append(i, luteum)

        chart = QtChart.QChart()
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        chart.addSeries(series_follicle)
        chart.addSeries(series_luteum)
        chart.createDefaultAxes()

        chart.setTitle('濾泡及黃體期天數')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(220)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_chart_temperature(self):
        series_follicle = QtChart.QLineSeries(name='濾泡期溫度')
        series_luteum = QtChart.QLineSeries(name='黃體期溫度')
        series_ovulate = QtChart.QLineSeries(name='排卵期溫度')

        row_count = self.ui.tableWidget_past_pregnant.rowCount()
        for i, row_no in enumerate(range(row_count-1, -1, -1)):
            follicle = self.ui.tableWidget_past_pregnant.item(row_no, 4)
            luteum = self.ui.tableWidget_past_pregnant.item(row_no, 6)
            ovulate = self.ui.tableWidget_past_pregnant.item(row_no, 8)
            if follicle is None:
                continue

            if luteum is None:
                continue

            if ovulate is None:
                continue

            follicle = number_utils.get_float(follicle.text())
            luteum = number_utils.get_float(luteum.text())
            ovulate = number_utils.get_float(ovulate.text())

            series_follicle.append(i, follicle)
            series_luteum.append(i, luteum)
            series_ovulate.append(i, ovulate)

        chart = QtChart.QChart()
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        chart.addSeries(series_follicle)
        chart.addSeries(series_luteum)
        chart.addSeries(series_ovulate)

        chart.createDefaultAxes()
        chart.axisY().setRange(36, 38)

        chart.setTitle('濾泡、黃體及排卵期溫度')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(220)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

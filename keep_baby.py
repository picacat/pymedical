# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import personnel_utils
from libs import system_utils
from libs import number_utils
from libs import case_utils
from libs import pregnant_utils
from libs import module_utils


# 保胎照護 2021.09.03
class KeepBaby(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(KeepBaby, self).__init__(parent)
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_KEEP_BABY, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_past_pregnant = class_utils.get_table_widget(
            self.ui.tableWidget_past_pregnant, self.database
        )
        self.table_widget_past_pregnant.set_column_hidden([0, 1])
        self.ui.dateEdit_first_date.setDate(self.parent.medical_record['CaseDate'].date())
        self._set_physique_table()
        self.ui.tableWidget_past_pregnant.setStyleSheet('''
            QTableWidget:!active {
                selection-background-color: palette(Highlight);
                selection-color: palette(HighlightedText)
            }
        ''')

    def _set_physique_table(self):
        self.tab_physique = module_utils.get_physique_table(
            self, self.database, self.system_settings, self.case_key, self.call_from
        )
        self.ui.verticalLayout_physique.addWidget(self.tab_physique)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_copy.clicked.connect(self.copy_pregnant_data)
        self.ui.toolButton_save.clicked.connect(self.save_pregnant_data)
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
            SELECT pregnant.*, cases.CaseDate, cases.PatientKey, cases.Name, cases.Doctor FROM pregnant
                LEFT JOIN cases ON pregnant.CaseKey = cases.CaseKey
            WHERE
                pregnant.CaseKey = {case_key}
            ORDER BY cases.CaseDate DESC
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._insert_keep_baby_data()
            rows = self.database.select_record(sql)

        row = rows[0]
        if display_case_date_label:
            pregnant_utils.set_case_label(row, self.ui.label_case_date)
            
        try:
            self._set_keep_baby_data(row)
        except Exception:
            pass

        try:
            self._set_symptom_line(row)
        except Exception:
            pass

        self.tab_physique.set_row(row)

    def _set_keep_baby_data(self, row):
        first_date = case_utils.get_first_treat_date(self.database, row['CaseDate'], row['PatientKey'], '保胎照護')

        self.ui.lineEdit_heartbeat.setText(string_utils.xstr(row['HeartBeat']))
        self.ui.lineEdit_bp_high.setText(string_utils.xstr(row['BPHigh']))
        self.ui.lineEdit_bp_low.setText(string_utils.xstr(row['BPLow']))
        self.ui.lineEdit_vomit.setText(string_utils.xstr(row['Vomit']))
        self.ui.lineEdit_bleed.setText(string_utils.xstr(row['Bleed']))
        self.ui.lineEdit_second_disease.setText(string_utils.xstr(row['DiseaseName']))
        self.ui.lineEdit_misc.setText(string_utils.xstr(row['Remark']))
        if first_date is not None:
            self.ui.dateEdit_first_date.setDate(first_date)

    def _insert_keep_baby_data(self):
        fields = [
            'CaseKey', 'PatientKey',
            'SymptomLine', 'PhysiqueLine', 'AnxietyLine'
        ]
        data = [
            self.case_key, self.parent.patient_record['PatientKey'],
            'NNNNNN', 'NNNNNNNNN', '0000000000'
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
        case_date = row['CaseDate']
        if case_date is not None:
            case_date = case_date.date()

        bp_high = string_utils.xstr(row['BPHigh'])
        bp_low = string_utils.xstr(row['BPLow'])
        blood_pressure = f'{bp_high} / {bp_low}'

        case_date = row['CaseDate']
        if case_date is not None:
            case_date = case_date.date()

        pregnant_row = [
            string_utils.xstr(row['PregnantKey']),
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(case_date),
            string_utils.xstr(row['HeartBeat']),
            string_utils.xstr(blood_pressure),
            string_utils.xstr(row['Vomit']),
            string_utils.xstr(row['Bleed']),
        ]

        for col_no in range(len(pregnant_row)):
            self.ui.tableWidget_past_pregnant.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(pregnant_row[col_no])
            )
            if col_no in [3, 4, 5, 6]:
                self.ui.tableWidget_past_pregnant.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _set_symptom_line(self, row):
        symptom_line = string_utils.xstr(row['SymptomLine'])

        check_box_list = [
            self.ui.checkBox_1,
            self.ui.checkBox_2,
            self.ui.checkBox_3,
            self.ui.checkBox_4,
            self.ui.checkBox_5,
            self.ui.checkBox_6,
        ]

        for i, check_box in enumerate(check_box_list):
            if symptom_line[i] == 'Y':
                check_box.setChecked(True)
            else:
                check_box.setChecked(False)

    def _get_symptom_line(self):
        symptom_line = ''
        check_box_list = [
            self.ui.checkBox_1,
            self.ui.checkBox_2,
            self.ui.checkBox_3,
            self.ui.checkBox_4,
            self.ui.checkBox_5,
            self.ui.checkBox_6,
        ]
        for check_box in check_box_list:
            if check_box.isChecked():
                symptom_line += 'Y'
            else:
                symptom_line += 'N'

        return symptom_line

    def copy_pregnant_data(self):
        pregnant_utils.copy_pregnant_data(self, self.ui.tableWidget_past_pregnant, self._read_current_data)

    def save_pregnant_data(self):
        pregnant_key = self.table_widget_past_pregnant.field_value(0)
        symptom_line = self._get_symptom_line()
        physique_line = self.tab_physique.get_physique_line()
        anxiety_line = self.tab_physique.get_anxiety_line()
        anxiety_grade = self.tab_physique.get_anxiety_grade()

        fields = [
            'HeartBeat',
            'BPHigh', 'BPLow',
            'Vomit', 'Bleed',
            'DiseaseName', 'Remark',
            'SymptomLine',
            'PhysiqueLine', 'AnxietyLine', 'AnxietyGrade'
        ]
        data = [
            self.ui.lineEdit_heartbeat.text(),
            self.ui.lineEdit_bp_high.text(),
            self.ui.lineEdit_bp_low.text(),
            self.ui.lineEdit_vomit.text(),
            self.ui.lineEdit_bleed.text(),
            self.ui.lineEdit_second_disease.text(),
            self.ui.lineEdit_misc.text(),
            symptom_line,
            physique_line, anxiety_line, anxiety_grade
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

        self._plot_chart_bpl()
        self._plot_chart_symptom()

    def _plot_chart_bpl(self):
        series_heartbeat = QtChart.QLineSeries(name='心跳數')
        series_bph = QtChart.QLineSeries(name='收縮壓')
        series_bpl = QtChart.QLineSeries(name='舒張壓')

        row_count = self.ui.tableWidget_past_pregnant.rowCount()
        for i, row_no in zip(range(row_count), range(row_count-1, -1, -1)):
            heartbeat = self.ui.tableWidget_past_pregnant.item(row_no, 3)
            bp = self.ui.tableWidget_past_pregnant.item(row_no, 4)
            if heartbeat is None:
                continue

            if bp is None:
                continue

            heartbeat = number_utils.get_integer(heartbeat.text())
            bp = bp.text().split(' / ')
            bph = number_utils.get_integer(bp[0])
            bpl = number_utils.get_integer(bp[1])

            series_heartbeat.append(i, heartbeat)
            series_bph.append(i, bph)
            series_bpl.append(i, bpl)

        chart = QtChart.QChart()
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        chart.addSeries(series_heartbeat)
        chart.addSeries(series_bph)
        chart.addSeries(series_bpl)

        chart.createDefaultAxes()

        chart.setTitle('心跳及血壓')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(220)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

    def _plot_chart_symptom(self):
        series_vomit = QtChart.QLineSeries(name='噁心嘔吐')
        series_bleed = QtChart.QLineSeries(name='出血')

        row_count = self.ui.tableWidget_past_pregnant.rowCount()
        for i, row_no in zip(range(row_count), range(row_count-1, -1, -1)):
            vomit = self.ui.tableWidget_past_pregnant.item(row_no, 5)
            bleed = self.ui.tableWidget_past_pregnant.item(row_no, 6)
            if vomit is None:
                continue

            if bleed is None:
                continue

            vomit = number_utils.get_integer(vomit.text())
            bleed = number_utils.get_integer(bleed.text())

            series_vomit.append(i, vomit)
            series_bleed.append(i, bleed)

        chart = QtChart.QChart()
        chart.legend().setAlignment(QtCore.Qt.AlignBottom)

        chart.addSeries(series_vomit)
        chart.addSeries(series_bleed)

        chart.createDefaultAxes()

        chart.setTitle('噁心嘔吐及出血')
        chart.setAnimationOptions(QtChart.QChart.SeriesAnimations)

        self.chartView = QtChart.QChartView(chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        self.chartView.setFixedHeight(220)
        self.ui.verticalLayout_chart.addWidget(self.chartView)

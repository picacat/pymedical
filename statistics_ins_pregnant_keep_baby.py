
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import export_utils
from libs import system_utils
from libs import personnel_utils
from libs import case_utils


# 保胎照護 - 2021-09-14
class StatisticsInsPregnantKeepBaby(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsInsPregnantKeepBaby, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_INS_PREGNANT_KEEP_BABY, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    def _set_table_width(self):
        width = [
            100,
            100, 120, 120, 120,
            90, 90, 90, 90, 90,
            60, 60, 60, 60, 60, 60,
            250,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self.open_medical_record)
        self.ui.pushButton_export_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def open_medical_record(self):
        if (self.parent.user_name != '超級使用者' and
                personnel_utils.get_permission(
                    self.database, '病歷資料', '病歷修正', self.parent.user_name) != 'Y'):
            return

        case_key = self.table_widget_medical_record.field_value(0)
        if case_key == '':
            return

        self.parent.parent.open_medical_record(case_key, '病歷查詢')

    def start_calculate(self):
        self._calculate_data()

    def _calculate_data(self):
        self._read_data()

    def _read_data(self):
        sql = f'''
            SELECT
                cases.CaseKey, cases.CaseDate, cases.Name, cases.PatientKey,
                patient.Birthday,
                pregnant.*
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                LEFT JOIN pregnant ON pregnant.CaseKey = cases.CaseKey
            WHERE
                DATE(CaseDate) BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                cases.InsType = "健保" AND
                cases.TreatType = "保胎照護"
            ORDER BY CaseDate
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        first_date = case_utils.get_first_treat_date(self.database, row['CaseDate'], row['PatientKey'], '保胎照護')
        symptom_line = string_utils.xstr(row['SymptomLine'])
        if symptom_line == '' or len(symptom_line) != 6:
            symptom_line = 'NNNNNN'

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(first_date.date()),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['HeartBeat']),
            string_utils.xstr(row['BPHigh']),
            string_utils.xstr(row['BPLow']),
            string_utils.xstr(row['Vomit']),
            string_utils.xstr(row['Bleed']),
            string_utils.get_yes_no_string(symptom_line[0], 'digit'),
            string_utils.get_yes_no_string(symptom_line[1], 'digit'),
            string_utils.get_yes_no_string(symptom_line[2], 'digit'),
            string_utils.get_yes_no_string(symptom_line[3], 'digit'),
            string_utils.get_yes_no_string(symptom_line[4], 'digit'),
            string_utils.get_yes_no_string(symptom_line[5], 'digit'),
            string_utils.xstr(row['DiseaseName']),
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)

            if col_no in [5, 6, 7, 8]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [9, 10, 11, 12, 13, 14]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _export_to_excel(self):
        filename = f'{self.start_date}至{self.end_date}懷孕初期症狀及心理估量表'

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel",
            f'{filename}.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        title = f"{self.system_settings.field('院所名稱')} {filename}"
        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record, [0],
            [], title, [10, 14, 14, 14, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 30]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

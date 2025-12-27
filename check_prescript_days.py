# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
import datetime

from libs import class_utils
from libs import ui_utils
from libs import date_utils
from libs import number_utils
from libs import string_utils
from libs import system_utils
from libs import nhi_utils


# 用藥天數檢查 2018.01.31
class CheckPrescriptDays(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(CheckPrescriptDays, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = int(args[2])
        self.apply_month = int(args[3])
        self.apply_type = args[4]
        self.duplicated_days = args[5]
        self.check_two_months = args[6]

        self.ui = None

        self.start_date = date_utils.get_start_date_by_year_month(
            self.apply_year, self.apply_month)

        end_year, end_month = self.apply_year, self.apply_month
        if self.check_two_months:
            if self.apply_month == 12:
                end_year, end_month = self.apply_year + 1, 1
            else:
                end_month += 1

        self.end_date = date_utils.get_end_date_by_year_month(end_year, end_month)

        self.errors = 0
        self.total_pres_days = 0
        self.total_duplicated_days = 0
        self.rows = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHECK_PRESCRIPT_DAYS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_table_widget()

    def _set_table_widget(self):
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database)
        self.table_widget_medical_record.set_column_hidden([0])
        width = [
            100, 
            130, 60, 90, 90, 100, 80, 50,
            100, 50, 100, 300, 90,
            70, 70, 230,
        ]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_medical_record.doubleClicked.connect(self.open_medical_record)
        self.ui.toolButton_find_error.clicked.connect(self._find_error)

    def _find_error(self):
        self.table_widget_medical_record.find_error(15)

    def open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        self.parent.open_medical_record(case_key)

    def read_data(self):
        apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)

        sql = f'''
            SELECT
                cases.*, dosage.*
            FROM cases
                LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
            WHERE
                (CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                (dosage.MedicineSet = 1) AND
                (dosage.Days > 0) AND
                ({apply_type_sql})
            ORDER BY PatientKey, CaseDate
        '''
        self.rows = self.database.select_record(sql)

    def row_count(self):
        return len(self.rows)

    def start_check(self):
        self.read_data()
        if self.row_count() <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在執行用藥天數檢查中, 請稍後...', '取消', 0, self.row_count(), self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.ui.tableWidget_medical_record.setRowCount(0)

        self.total_pres_days = 0
        self.total_duplicated_days = 0
        for row_no, row in enumerate(self.rows):
            error_messages = []
            error_messages += self._check_duplicated_days(row_no, row)
            self._insert_record(row, error_messages)

            progress_dialog.setValue(row_no)

        progress_dialog.setValue(self.row_count())
        progress_dialog.deleteLater()

        self._remove_useless_rows()
        self._recalculate_errors()
        self._calculate_duplicated_rate()

        self.ui.tableWidget_medical_record.setAlternatingRowColors(True)
        if self.errors <= 0:
            self.ui.toolButton_find_error.setEnabled(False)
        else:
            self.ui.toolButton_find_error.setEnabled(True)

        self.ui.tableWidget_medical_record.resizeRowsToContents()
        self._set_not_this_month_color()

        self.ui.label_message.adjustSize()

    def _calculate_duplicated_rate(self):
        self.total_duplicated_days = 0
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, 15)
            if item is None:
                continue

            error_message = item.text()
            if '給藥重複' in error_message:
                duplicated_days = number_utils.get_integer(error_message.split('給藥重複')[1].split('日')[0])
                self.total_duplicated_days += duplicated_days

        if self.total_pres_days <= 0:
            self.ui.label_message.setText('用藥重複率: 0%')
        else:
            percent = self.total_duplicated_days / self.total_pres_days * 100
            self.ui.label_message.setText(f'''
                用藥重複率 = 重複給藥日份 / 總給藥日份<br>
                <b>{self.total_duplicated_days} / {self.total_pres_days} = {percent:.2f}%</b>
            ''')

    def _check_duplicated_days(self, row_no, row):
        error_message = []

        patient_key = string_utils.xstr(row['PatientKey'])
        try:
            last_case_date = datetime.datetime.strptime(
                self.ui.tableWidget_medical_record.item(row_no-1, 1).text(), '%Y-%m-%d').date()
            last_patient_key = self.ui.tableWidget_medical_record.item(row_no-1, 3).text()
            last_prescript_days = int(self.ui.tableWidget_medical_record.item(row_no-1, 9).text())
            self.total_pres_days += number_utils.get_integer(last_prescript_days)
        except AttributeError:
            last_case_date = None
            last_patient_key = None
            last_prescript_days = 0

        duplicated_days = self.duplicated_days

        if patient_key == last_patient_key:
            duplicated_days = (last_case_date +
                               datetime.timedelta(
                                   days=last_prescript_days + duplicated_days) -
                               row['CaseDate'].date()).days - 1
            # if self.system_settings.field('當日用藥重複檢查次日起算') == 'Y':
            #     duplicated_days += 1

            if duplicated_days > 0:
                error_message.append(f'給藥重複{duplicated_days}日')
                self.total_duplicated_days += duplicated_days
                self.errors += 1

        return error_message

    def _recalculate_errors(self):
        self.errors = 0
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, 15)
            if item is None:
                continue

            error_message = item.text()
            if '給藥重複' in error_message:
                self.errors += 1

    def error_count(self):
        return self.errors

    def _insert_record(self, row, error_messages):
        row_no = self.ui.tableWidget_medical_record.rowCount()
        self.ui.tableWidget_medical_record.setRowCount(row_no + 1)

        year = row['CaseDate'].year
        month = row['CaseDate'].month
        day = row['CaseDate'].day
        medical_record = [
            string_utils.xstr(row['CaseKey']),
            f'{year}-{month:0>2}-{day:0>2}',
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Days']),
            string_utils.xstr(row['DiseaseCode1']),
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['InterDrugFee']),
            string_utils.xstr(row['PharmacyFee']),
            ', '.join(error_messages),
        ]
        for column_no in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column_no,
                QtWidgets.QTableWidgetItem(medical_record[column_no])
            )
            if column_no in [7]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            elif column_no in [3, 9, 13, 14]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

            if len(error_messages) > 0:
                color = QtGui.QColor('red')
                self.ui.tableWidget_medical_record.item(row_no, column_no).setForeground(color)

    def _set_not_this_month_color(self):
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            case_date = self.ui.tableWidget_medical_record.item(row_no, 1).text()
            if date_utils.str_to_date(case_date).month != self.apply_month:
                for col_no in range(self.ui.tableWidget_medical_record.columnCount()):
                    self.ui.tableWidget_medical_record.item(row_no, col_no).setForeground(QtGui.QColor('darkGray'))

    def _remove_useless_rows(self):
        for row_no in reversed(range(self.ui.tableWidget_medical_record.rowCount())):
            current_case_date = self.ui.tableWidget_medical_record.item(row_no, 1).text()
            current_patient_key = self.ui.tableWidget_medical_record.item(row_no, 3).text()
            if date_utils.str_to_date(current_case_date).month == self.apply_month:
                continue

            if row_no == 0:
                if date_utils.str_to_date(current_case_date).month != self.apply_month:
                    self._set_row_error_message(row_no, 15, '!')
                    break

            last_case_date = self.ui.tableWidget_medical_record.item(row_no-1, 1).text()
            last_patient_key = self.ui.tableWidget_medical_record.item(row_no-1, 3).text()

            if date_utils.str_to_date(last_case_date).month != self.apply_month and \
                    current_patient_key == last_patient_key:
                self._set_row_error_message(row_no, 15, '!')
            else:
                if current_patient_key != last_patient_key:
                    self._set_row_error_message(row_no, 15, '!')

        for row_no in reversed(range(self.ui.tableWidget_medical_record.rowCount())):
            remove_flag = self.ui.tableWidget_medical_record.item(row_no, 15)
            if remove_flag is not None and remove_flag.text() == '!':
                self.ui.tableWidget_medical_record.removeRow(row_no)

    def _set_row_error_message(self, row_no, col_no, error_message):
        self.ui.tableWidget_medical_record.setItem(row_no, col_no, QtWidgets.QTableWidgetItem(error_message))

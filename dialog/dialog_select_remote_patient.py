
# -*- coding: UTF-8 -*-


from PyQt5 import QtWidgets, QtCore
import re
import calendar

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils
from libs import validator_utils
from libs import number_utils


# 選擇分院病患  2019.07.22
class DialogSelectRemotePatient(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSelectRemotePatient, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.patient_key = None
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SELECT_REMOTE_PATIENT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_patient_list = class_utils.get_table_widget(self.ui.tableWidget_patient_list, self.database)
        self._set_table_width()

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)
        self.ui.tableWidget_patient_list.doubleClicked.connect(self.table_double_clicked)
        self.ui.pushButton_search.clicked.connect(self._read_remote_patient)

    def _set_table_width(self):
        width = [200, 80, 80, 40, 120, 120, 80, 120, 120, 400]
        self.table_widget_patient_list.set_table_heading_width(width)

    def button_accepted(self):
        self.patient_key = self.table_widget_patient_list.field_value(0)

    def button_rejected(self):
        self.patient_key = None

    def table_double_clicked(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def get_patient_key(self):
        return self.patient_key

    def _get_patient_sql(self):
        query_str = string_utils.xstr(self.ui.lineEdit_query.text()).strip()
        if query_str == '':
            return

        if query_str.isdigit():
            sql = f'''
                SELECT * FROM patient
                WHERE
                    PatientKey = "{query_str}"
                ORDER BY PatientKey
            '''
        elif re.compile(validator_utils.DATE_REGEXP).match(query_str):
            query_str = date_utils.date_to_west_date(query_str)
            sql = f'''
                SELECT * FROM patient
                WHERE
                    Birthday = "{query_str}"
                ORDER BY PatientKey
            '''
        elif re.compile('^[0-9]{1,4}[-/.][0-9]{1,2}').match(query_str):
            date_separator = date_utils.get_date_separator(query_str)
            if date_separator == '':
                return

            try:
                year, month = query_str.split(date_separator)
            except ValueError:
                return

            year = number_utils.get_integer(year)
            if year < 1000:
                year += 1911

            month = number_utils.get_integer(month)
            if month <= 0:
                return

            last_day = calendar.monthrange(year, month)[1]

            start_date = f'{year}{date_separator}{month}{date_separator}01'
            end_date = f'{year}{date_separator}{month}{date_separator}{last_day}'

            sql = f'''
                SELECT * FROM patient
                WHERE
                    Birthday BETWEEN "{start_date}" AND "{end_date}"
                ORDER BY Birthday
            '''
        elif re.compile('^[0-9]{1,4}[-/.]').match(query_str):
            if '-' in query_str:
                separator = '-'
            elif '/' in query_str:
                separator = '/'
            elif '.' in query_str:
                separator = '.'
            else:
                return

            year, _ = query_str.split(separator)
            year = number_utils.get_integer(year)
            if year < 1000:
                year += 1911

            start_date = f'{year}{separator}01{separator}01'
            end_date = f'{year}{separator}12{separator}31'

            sql = f'''
                SELECT * FROM patient
                WHERE
                    Birthday BETWEEN "{start_date}" AND "{end_date}"
                ORDER BY Birthday
            '''
        else:
            sql = f'''
                SELECT * FROM patient
                WHERE
                    (Name LIKE "%{query_str}%") OR
                    (ID LIKE "{query_str}%") OR
                    (Birthday = "{query_str}") OR
                    (Telephone LIKE "%{query_str}%") OR
                    (Cellphone LIKE "{query_str}%") OR
                    (Address LIKE "%{query_str}%")
                ORDER BY PatientKey
            '''

        return sql

    def _read_remote_patient(self):
        patient_records = []

        sql = '''
            SELECT * FROM hosts
            ORDER BY HostsKey
        '''
        rows = self.database.select_record(sql)
        self.database_list = {}
        for row in rows:
            clinic_name = string_utils.xstr(row['ClinicName'])
            HIS_version = string_utils.xstr(row['HISVersion'])
            database_hosts = class_utils.get_db(
                host=row['Host'],
                user=row['UserName'],
                password=row['Password'],
                database=row['DatabaseName'],
                charset=row['Charset'],
            )
            self.database_list[clinic_name] = database_hosts
            patient_records += self._get_patient_records(
                database_hosts, clinic_name, HIS_version
            )

        if len(patient_records) <= 0:
            self.ui.tableWidget_patient_list.setRowCount(0)
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
            return

        self._set_table_data(patient_records)
        self.ui.tableWidget_patient_list.sortItems(4, QtCore.Qt.AscendingOrder)
        self.ui.tableWidget_patient_list.setFocus(True)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    def _get_patient_records(self, database_hosts, clinic_name, HIS_version):
        if HIS_version == 'Medical':
            gender = 'Sex'
        else:
            gender = 'Gender'

        patient_records = []
        sql = self._get_patient_sql()
        try:
            rows = database_hosts.select_record(sql)
        except Exception:
            return patient_records

        if rows is None or len(rows) <= 0:
            return patient_records

        for row in rows:
            ins_type = row['InsType']
            if ins_type == '健保':
                ins_type = '基層醫療'

            patient_records.append(
                {
                    'ClinicName': clinic_name,
                    'PatientKey': row['PatientKey'],
                    'Name': row['Name'],
                    'Gender': row[gender],
                    'Birthday': row['Birthday'],
                    'ID': row['ID'],
                    'InsType': ins_type,
                    'Telephone': row['Telephone'],
                    'Cellphone': row['Cellphone'],
                    'Address': row['Address'],
                    'DisountType': row['DiscountType'],
                    'HISVersion': HIS_version,
                }
            )

        return patient_records

    def get_remote_patient(self):
        current_row = self.ui.tableWidget_patient_list.currentRow()
        remote_patient = {
            'Name': self.ui.tableWidget_patient_list.item(current_row, 2).text(),
            'Gender': self.ui.tableWidget_patient_list.item(current_row, 3).text(),
            'Birthday': self.ui.tableWidget_patient_list.item(current_row, 4).text(),
            'ID': self.ui.tableWidget_patient_list.item(current_row, 5).text(),
            'InsType': self.ui.tableWidget_patient_list.item(current_row, 6).text(),
            'Telephone': self.ui.tableWidget_patient_list.item(current_row, 7).text(),
            'Cellphone': self.ui.tableWidget_patient_list.item(current_row, 8).text(),
            'Address': self.ui.tableWidget_patient_list.item(current_row, 9).text(),
        }

        return remote_patient

    def _set_table_data(self, patient_records):
        patient_record_count = len(patient_records)
        self.ui.tableWidget_patient_list.setRowCount(patient_record_count)

        for row_no, row in zip(range(patient_record_count), patient_records):
            patient_row = [
                string_utils.xstr(row['ClinicName']),
                string_utils.xstr(row['PatientKey']),
                string_utils.xstr(row['Name']),
                string_utils.xstr(row['Gender']),
                string_utils.xstr(row['Birthday']),
                string_utils.xstr(row['ID']),
                string_utils.xstr(row['InsType']),
                string_utils.xstr(row['Telephone']),
                string_utils.xstr(row['Cellphone']),
                string_utils.xstr(row['Address'])
            ]

            for column in range(len(patient_row)):
                self.ui.tableWidget_patient_list.setItem(
                    row_no, column,
                    QtWidgets.QTableWidgetItem(patient_row[column])
                )
                if column in [3]:
                    self.ui.tableWidget_patient_list.item(
                        row_no, column).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )

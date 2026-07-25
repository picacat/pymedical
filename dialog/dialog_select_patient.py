
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
from libs import personnel_utils


# 選擇病患  2018.12.25
class DialogSelectPatient(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogSelectPatient, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_name = args[2]
        self.primary_key_field = args[3]
        self.keyword = args[4]

        self.primary_key = None
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

        if self.keyword != '':
            self.ui.lineEdit_query.setText(self.keyword)
            self.ui.tableWidget_patient_list.setFocus()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_SELECT_PATIENT, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_patient_list = class_utils.get_table_widget(
            self.ui.tableWidget_patient_list, self.database
        )
        # database._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)
        self.ui.tableWidget_patient_list.doubleClicked.connect(self.table_double_clicked)
        self.ui.lineEdit_query.textChanged.connect(self._query_patient)

    def _set_table_width(self):
        width = [80, 80, 40, 120, 120, 80, 120, 120, 500]
        self.table_widget_patient_list.set_table_heading_width(width)

    def button_accepted(self):
        self.primary_key = self.table_widget_patient_list.field_value(0)

    def button_rejected(self):
        self.primary_key = None

    def table_double_clicked(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def get_primary_key(self):
        return self.primary_key

    def get_name(self):
        name = self.table_widget_patient_list.field_value(1)
        return name

    def _query_patient(self):
        query_str = string_utils.xstr(self.ui.lineEdit_query.text()).strip()
        if query_str == '':
            self.ui.tableWidget_patient_list.setRowCount(0)
            return

        try:
            self._read_table(query_str)
        except Exception:
            return

        self.ui.lineEdit_query.setFocus(True)
        self.ui.lineEdit_query.setCursorPosition(len(query_str))

    def _read_table(self, query_str):
        keyword = validator_utils.get_exp_date(query_str)
        if keyword != query_str:
            sql = f'''
                SELECT * FROM {self.table_name}
                WHERE
                    (Birthday = "{keyword}" OR PatientKey = {self.keyword})
                ORDER BY {self.primary_key_field}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                sql = f'''
                    SELECT * FROM {self.table_name}
                    WHERE
                        PatientKey = "{query_str}"
                    ORDER BY {self.primary_key_field}
                '''
        elif query_str.isdigit():
            sql = f'''
                SELECT * FROM {self.table_name}
                WHERE
                    {self.primary_key_field} = {query_str}
                ORDER BY PatientKey
            '''
        elif re.compile(validator_utils.DATE_REGEXP).match(query_str):
            query_str = date_utils.date_to_west_date(query_str)
            sql = f'''
                SELECT * FROM {self.table_name}
                WHERE
                    Birthday = "{query_str}"
                ORDER BY {self.primary_key_field}
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
                SELECT * FROM {self.table_name}
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
                SELECT * FROM {self.table_name}
                WHERE
                    Birthday BETWEEN "{start_date}" AND "{end_date}"
                ORDER BY Birthday
            '''
        else:
            address_condition = ''
            if len(query_str) >= 2:
                address_condition = f'OR (Address LIKE "%{query_str}%")'

            sql = f'''
                SELECT * FROM {self.table_name}
                WHERE
                    (Name LIKE "%{query_str}%") OR
                    (ID LIKE "{query_str}%") OR
                    (Birthday = "{query_str}") OR
                    (Telephone LIKE "%{query_str}%") OR
                    (Cellphone LIKE "{query_str}%")
                    {address_condition}
                ORDER BY {self.primary_key_field}
            '''
        self.table_widget_patient_list.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        try:
            ins_type = string_utils.xstr(row['InsType'])
        except KeyError:
            ins_type = None

        address = string_utils.xstr(row['Address'])
        telephone = string_utils.xstr(row['Telephone'])
        cellphone = string_utils.xstr(row['Cellphone'])

        if personnel_utils.get_permission(self.database, '病患查詢', '調閱病歷', self.user_name) != 'Y':
            address = None
            telephone = None
            cellphone = None

        patient_row = [
            string_utils.xstr(row[self.primary_key_field]),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['ID']),
            ins_type,
            telephone,
            cellphone,
            address,
        ]

        for column in range(len(patient_row)):
            self.ui.tableWidget_patient_list.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(patient_row[column])
            )
            if column in [2]:
                self.ui.tableWidget_patient_list.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

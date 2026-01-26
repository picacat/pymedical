# coding: utf-8

import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import (class_utils, date_utils, nhi_utils, prescript_utils,
                  string_utils, system_utils, ui_utils)


# 健保碼檢查 2018.01.31
class CheckInsDrug(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(CheckInsDrug, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = int(args[2])
        self.apply_month = int(args[3])
        self.apply_type = args[4]
        self.ui = None

        self.start_date = date_utils.get_start_date_by_year_month(
            self.apply_year, self.apply_month)
        self.end_date = date_utils.get_end_date_by_year_month(
            self.apply_year, self.apply_month)
        self.errors = 0
        self.rows = None

        self.column = {
            'CaseKey': 0,
            'PrescriptKey': 1,
            'MedicineKey': 2,
            'CaseDate': 3,
            'PatientKey': 4,
            'Name': 5,
            'Doctor': 6,
            'MedicineType': 7,
            'MedicineName': 8,
            'InsCode': 9,
            'Factory': 10,
            'InsMedicineName': 11,
            'Signature': 12,
            'ValidDate': 13,
            'ErrorMessage': 14,
        }
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHECK_INS_DRUG, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_table_widget()

    def _set_table_widget(self):
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database)
        self.table_widget_prescript.set_column_hidden([0, 1, 2])
        width = [
            100, 100, 100,
            130, 90, 90, 90, 50, 200,
            120, 150, 180, 130, 150, 230,
        ]
        self.table_widget_prescript.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_prescript.doubleClicked.connect(self.open_medical_record)
        self.ui.toolButton_find_error.clicked.connect(self._find_error)
        self.ui.toolButton_update_ins_code.clicked.connect(self._update_ins_code)

    def _find_error(self):
        self.table_widget_prescript.find_error(14)

    def open_medical_record(self):
        case_key = self.table_widget_prescript.field_value(self.column['CaseKey'])
        self.parent.open_medical_record(case_key)

    def read_data(self):
        apply_type_sql = nhi_utils.get_apply_type_sql(self.apply_type)

        sql = f'''
            SELECT
                prescript.PrescriptKey, prescript.MedicineName, prescript.MedicineKey, prescript.MedicineType,
                prescript.Dosage, prescript.InsCode,
                cases.CaseKey, cases.CaseDate, cases.PatientKey, cases.Name,
                cases.Doctor
            FROM prescript
                LEFT JOIN cases ON cases.CaseKey = prescript.CaseKey
            WHERE
                (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (cases.InsType = "健保") AND
                ({apply_type_sql}) AND
                (prescript.MedicineSet = 1) AND
                (prescript.MedicineType IN ("單方", "複方"))
            ORDER BY cases.CaseDate, cases.CaseKey, prescript.PrescriptKey
        '''
        self.rows = self.database.select_record(sql)

    def row_count(self):
        return len(self.rows)

    def start_check(self):
        self.read_data()
        if self.row_count() <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '正在執行健保碼檢查中, 請稍後...', '取消', 0, self.row_count(), self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self.ui.tableWidget_prescript.setRowCount(0)
        for row_no, row in enumerate(self.rows):
            progress_dialog.setValue(row_no)
            medicine_name = string_utils.xstr(row['MedicineName'])

            error_messages = []
            ins_code = string_utils.xstr(row['InsCode'])
            if ins_code == '':
                self._insert_error_record(row_no, row, [], error_messages)
                continue

            sql = f'''
                SELECT Supplier, DrugName, ValidDate FROM drug
                WHERE
                    InsCode = "{ins_code}"
            '''
            drug_rows = self.database.select_record(sql)

            if '清冠一號' in medicine_name:
                pass
            elif len(drug_rows) <= 0:
                error_messages.append('查無健保藥品資料')
                self._insert_error_record(row_no, row, drug_rows, error_messages)
                self.errors += 1
                continue
            else:
                error_messages += self._check_valid_date(row, drug_rows)
                error_messages += self._check_invalid_ins_code(row)                

            self._insert_error_record(row_no, row, drug_rows, error_messages)

        progress_dialog.setValue(self.row_count())
        progress_dialog.deleteLater()

        self.ui.tableWidget_prescript.setAlternatingRowColors(True)
        if self.errors <= 0:
            self.ui.toolButton_find_error.setEnabled(False)
        else:
            self.ui.toolButton_find_error.setEnabled(True)

        self.ui.tableWidget_prescript.resizeRowsToContents()

    def _check_valid_date(self, row, drug_rows):
        error_message = []

        valid_date = drug_rows[0]['ValidDate']
        if type(valid_date) is str:
            try:
                if '-' in valid_date:
                    valid_date = datetime.datetime.strptime(valid_date, "%Y-%m-%d").date()
                else:
                    valid_date = datetime.datetime.strptime(valid_date, "%Y%m%d").date()
            except ValueError:
                valid_date = None

        if valid_date is None:
            error_message.append('健保藥碼無效')
        elif row['CaseDate'].date() > valid_date:
            error_message.append('有效期限過期')

        if len(error_message) > 0:
            self.errors += 1

        return error_message

    def _check_invalid_ins_code(self, row):
        error_message = []

        ins_code = string_utils.xstr(row['InsCode'])
        if ins_code in nhi_utils.INVALID_INS_CODE_LIST:
            error_message.append('港香蘭無效藥品, 請重新輸入其他藥廠藥品')
        elif ins_code in nhi_utils.INVALID_WKP_INS_CODE_LIST:
            error_message.append('萬國信宏無效藥品, 請重新輸入其他藥廠藥品')

        if len(error_message) > 0:
            self.errors += 1

        return error_message

    def _check_drug_name(self, row, drug_rows):
        error_message = []

        if string_utils.xstr(drug_rows[0]['DrugName']) not in string_utils.xstr(row['MedicineName']):
            error_message.append('健保藥名不一致')

        return error_message

    def error_count(self):
        return self.errors

    def _insert_error_record(self, row_no, row, drug_rows, error_messages):
        if len(drug_rows) <= 0:
            supplier = None
            drug_name = None
            valid_date = None
        else:
            supplier = drug_rows[0]['Supplier']
            drug_name = drug_rows[0]['DrugName']
            valid_date = drug_rows[0]['ValidDate']
            if type(valid_date) is str:
                if '-' in valid_date:
                    year = valid_date[:4]
                    month = valid_date[5:7]
                    day = valid_date[8:10]
                    valid_date = f'{year}-{month}-{day}'
                else:
                    year = valid_date[:4]
                    month = valid_date[4:6]
                    day = valid_date[6:8]
                    valid_date = f'{year}-{month}-{day}'

        prescript_key = string_utils.xstr(row['PrescriptKey'])
        sql = f'''
            SELECT Content FROM presextend
            WHERE
                ExtendType = "處方簽章" AND
                presextend.PrescriptKey = {prescript_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            prescript_sign = None
        else:
            prescript_sign = rows[0]['Content']

        self.ui.tableWidget_prescript.setRowCount(row_no + 1)

        case_key = string_utils.xstr(row['CaseKey'])
        prescript_key = string_utils.xstr(row['PrescriptKey'])
        medicine_key = string_utils.xstr(row['MedicineKey'])
        try:
            last_case_key = self.ui.tableWidget_prescript.item(row_no - 1, 0).text()
        except AttributeError:
            last_case_key = 0

        year = row['CaseDate'].year
        month = row['CaseDate'].month
        day = row['CaseDate'].day
        case_date = f'{year}-{month:0>2}-{day:0>2}'
        patient_key = row['PatientKey']
        name = row['Name']
        doctor = row['Doctor']
        medicine_name = string_utils.xstr(row['MedicineName'])
        if case_key == last_case_key:
            case_date = ''
            patient_key = ''
            name = ''
            doctor = ''

        medical_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(prescript_key),
            string_utils.xstr(medicine_key),
            string_utils.xstr(case_date),
            string_utils.xstr(patient_key),
            string_utils.xstr(name),
            string_utils.xstr(doctor),
            string_utils.xstr(row['MedicineType']),
            medicine_name,
            string_utils.xstr(row['InsCode']),
            string_utils.xstr(supplier),
            string_utils.xstr(drug_name),
            string_utils.xstr(valid_date),
            string_utils.xstr(prescript_sign),
            ', '.join(error_messages),
        ]
        for column_no in range(len(medical_record)):
            self.ui.tableWidget_prescript.setItem(
                row_no, column_no,
                QtWidgets.QTableWidgetItem(medical_record[column_no])
            )
            if column_no in [self.column['PatientKey']]:
                self.ui.tableWidget_prescript.item(
                    row_no, column_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            if '清冠一號' in medicine_name:
                color = QtGui.QColor('magenta')
            elif len(error_messages) > 0:
                if '健保藥名不一致' in error_messages:
                    color = QtGui.QColor('green')
                else:
                    color = QtGui.QColor('red')
            else:
                color = None

            if color is not None:
                self.ui.tableWidget_prescript.item(row_no, column_no).setForeground(color)

    def _update_ins_code(self):
        record_count = self.ui.tableWidget_prescript.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            '自動更新健保碼中, 請稍後...', '取消', 0, record_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(record_count):
            progress_dialog.setValue(row_no)
            error_message = self.ui.tableWidget_prescript.item(row_no, self.column['ErrorMessage'])
            if error_message is None:
                continue

            prescript_key = self.ui.tableWidget_prescript.item(row_no, self.column['PrescriptKey']).text()
            medicine_key = self.ui.tableWidget_prescript.item(row_no, self.column['MedicineKey'])
            medicine_type = self.ui.tableWidget_prescript.item(row_no, self.column['MedicineType']).text()
            medicine_name = self.ui.tableWidget_prescript.item(row_no, self.column['MedicineName']).text()
            ins_code = self.ui.tableWidget_prescript.item(row_no, self.column['InsCode']).text()
            if medicine_key in [None, ''] or ins_code in [None, '']:
                self._update_ins_code_by_name(prescript_key, medicine_type, medicine_name)
                continue

            medicine_key = medicine_key.text()
            ins_code = prescript_utils.get_medicine_field(self.database, medicine_key, 'InsCode')
            if ins_code is None:
                ins_code = 'NULL'
            else:
                ins_code = f'"{ins_code}"'

            sql = f'''
                UPDATE prescript
                    SET InsCode = {ins_code}
                WHERE
                    PrescriptKey = {prescript_key}
            '''
            self.database.exec_sql(sql)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()
        self.start_check()

    def _update_ins_code_by_name(self, prescript_key, medicine_type, medicine_name):
        medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
        if len(medicine_rows) <= 0:
            medicine_name = medicine_name.split('(')[0]  # 去掉()
            if string_utils.xstr(medicine_name) == '':
                return

            medicine_rows = self._get_medicine_row(medicine_type, medicine_name)
            if len(medicine_rows) <= 0:
                return

        ins_code = string_utils.xstr(medicine_rows[0]['InsCode'])
        self.database.exec_sql(f'''
            UPDATE prescript
            SET
                InsCode = "{ins_code}"
            WHERE
                PrescriptKey = {prescript_key}
        ''')

    def _get_medicine_row(self, medicine_type, medicine_name):
        sql = f'''
            SELECT InsCode FROM medicine
            WHERE
                MedicineType = "{medicine_type}" AND
                MedicineName LIKE "{medicine_name}%" AND
                InsCode IS NOT NULL AND
                LENGTH(InsCode) > 0
        '''
        rows = self.database.select_record(sql)

        return rows

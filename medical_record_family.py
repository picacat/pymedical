# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import personnel_utils
from libs import case_utils
from libs import system_utils
from libs import date_utils


# 病歷資料 2018.01.31
class MedicalRecordFamily(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(MedicalRecordFamily, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.call_from = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_family()

        self.user_name = system_utils.get_user_name(self.system_settings)
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MEDICAL_RECORD_FAMILY, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_patient = class_utils.get_table_widget(self.ui.tableWidget_patient, self.database)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_patient.itemSelectionChanged.connect(self._patient_changed)
        self.ui.tableWidget_medical_record.itemSelectionChanged.connect(self._medical_record_changed)
        self.ui.pushButton_copy.clicked.connect(self._copy_medical_record)

    def _set_permission(self):
        if self.call_from == '醫師看診作業':
            return

        if self.user_name == '超級使用者':
            return

        if personnel_utils.get_permission(self.database, '病歷資料', '病歷修正', self.user_name) == 'Y':
            return

        self.ui.groupBox_copy_option.setEnabled(False)
        self.ui.pushButton_copy.setEnabled(False)

    def _set_table_width(self):
        width = [90, 90, 50, 110, 50, 120]
        self.table_widget_patient.set_table_heading_width(width)

        width = [90, 125, 50, 200, 50, 90]
        self.table_widget_medical_record.set_table_heading_width(width)

    def _read_family(self):
        self._read_cases()
        self._read_patient()
        self._read_family_members()

    def _read_cases(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        self.medical_record_row = self.database.select_record(sql)[0]

    def _read_patient(self):
        patient_key = self.medical_record_row['PatientKey']
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            self.patient_row = rows[0]
        else:
            self.patient_row = None

    def _read_family_members(self):
        if self.patient_row is None:
            return

        patient_key = self.patient_row['PatientKey']
        patient_name = self.patient_row['Name']
        script = f'''
            FamilyPatientKey = {patient_key} OR
            FamilyPatientKey = "{patient_name}"
        '''
        condition = [script]

        family_patient_key = string_utils.xstr(self.patient_row['FamilyPatientKey'])
        if family_patient_key != '':
            if family_patient_key.isdigit():
                script = f'''
                    PatientKey = {family_patient_key} OR
                    FamilyPatientKey IN ({patient_key}, {family_patient_key})
                '''
            else:
                script = f'''
                    Name = "{family_patient_key}" OR
                    FamilyPatientKey = "{family_patient_key}"
                '''
            condition.append(script)

        telephone = string_utils.xstr(self.patient_row['Telephone'])
        if telephone != '' and len(telephone) >= 7:
            condition.append(f'(Telephone LIKE "%{telephone}%" OR Cellphone LIKE "%{telephone}%")')
        cellphone = string_utils.xstr(self.patient_row['Cellphone'])
        if cellphone != '' and len(cellphone) >= 10:
            condition.append(f'(Cellphone LIKE "%{cellphone}%" OR Telephone LIKE "%{cellphone}%")')
        address = string_utils.xstr(self.patient_row['Address'])
        address = string_utils.remove_illegal_characters(address)

        if address != '' and len(address) > 6:
            condition.append(f'(Address = "{address}")')

        if len(condition) <= 0:
            return

        patient_key = self.patient_row['PatientKey']
        condition = ' OR '.join(condition)
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey != {patient_key} AND
                ({condition})
            ORDER BY PatientKey
        '''
        self.table_widget_patient.set_db_data(sql, self._set_patient_data)
        self._patient_changed()

    def _set_patient_data(self, row_no, row):
        birthday = row['Birthday']
        if birthday is not None:
            age_year, _ = date_utils.get_age(birthday, datetime.datetime.now())
        else:
            age_year = None

        init_date = row['InitDate']
        if init_date is not None:
            init_date = init_date.date()

        patient_row = [
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(birthday),
            string_utils.xstr(age_year),
            string_utils.xstr(init_date),
        ]

        for col_no in range(len(patient_row)):
            self.ui.tableWidget_patient.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(patient_row[col_no])
            )
            if col_no in [0, 4]:
                self.ui.tableWidget_patient.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_patient.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _patient_changed(self):
        patient_key = self.table_widget_patient.field_value(0)
        if patient_key is None:
            self.ui.groupBox_copy_option.setEnabled(False)
            self.ui.pushButton_copy.setEnabled(False)
            return

        sql = f'''
            SELECT * FROM cases
            WHERE
                PatientKey = {patient_key}
            ORDER BY CaseDate DESC
        '''
        self.table_widget_medical_record.set_db_data(sql, self._set_medical_record_data)
        self._medical_record_changed()
        self.ui.tableWidget_patient.setFocus()

    def _set_medical_record_data(self, row_no, row):
        case_key = row['CaseKey']
        ins_type = string_utils.xstr(row['InsType'])

        medicine_set = 1
        if ins_type == '自費':
            medicine_set = 2

        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
        if pres_days <= 0:
            pres_days = None

        medical_record_row = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].date()),
            ins_type,
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(pres_days),
            string_utils.xstr(row['Doctor']),
        ]

        for col_no in range(len(medical_record_row)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record_row[col_no])
            )
            if col_no in [4]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _medical_record_changed(self):
        case_key = self.table_widget_medical_record.field_value(0)
        if case_key is None:
            return

        html = case_utils.get_medical_record_html(self.database, self.system_settings, case_key)
        self.ui.textEdit_medical_record.setHtml(html)
        self._set_copy_prescript_check_box()

    def _set_copy_prescript_check_box(self):
        case_key = self.table_widget_medical_record.field_value(0)
        ins_type = self.table_widget_medical_record.field_value(2)

        self.ui.checkBox_ins_prescript.setChecked(False)  # 健保療程2-6次預設不拷貝藥品
        self.ui.checkBox_ins_prescript.setEnabled(False)  # 健保療程2-6次預設不拷貝藥品

        self.ui.radioButton_ins_prescript.setEnabled(False)
        self.ui.radioButton_self_prescript.setEnabled(False)

        self.ui.checkBox_ins_treat.setChecked(False)
        self.ui.checkBox_ins_treat.setEnabled(False)

        if ins_type == '健保':
            sql = f'''
                SELECT Treatment FROM cases
                WHERE
                    CaseKey = {case_key}
            '''
            rows = self.database.select_record(sql)
            treatment = string_utils.xstr(rows[0]['Treatment'])

            if treatment != '':
                self.ui.checkBox_ins_treat.setEnabled(True)
                self.ui.checkBox_ins_treat.setChecked(True)

            sql = f'''
                SELECT PrescriptKey FROM prescript
                WHERE
                    CaseKey = {case_key} AND
                    MedicineSet = 1 AND
                    MedicineType IN ("單方", "複方")
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_ins_prescript.setEnabled(True)
                self.ui.radioButton_ins_prescript.setEnabled(True)
                self.ui.radioButton_self_prescript.setEnabled(True)
                if treatment == '':
                    self.ui.checkBox_ins_prescript.setChecked(True)  # 預設非療程才拷貝藥品

        sql = f'''SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            copy_self_prescript = True
        else:
            copy_self_prescript = False

        self.ui.checkBox_self_prescript.setEnabled(copy_self_prescript)
        self.ui.checkBox_self_prescript.setChecked(copy_self_prescript)
        if copy_self_prescript:
            self.ui.checkBox_self_prescript.setChecked(False)  # 預設不要拷貝

        if self.parent.ins_type == '自費':
            self.ui.radioButton_self_prescript.setChecked(True)

    def _copy_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)

        if self.ui.radioButton_ins_prescript.isChecked():
            copy_ins_prescript_to = '健保處方'
        else:
            copy_ins_prescript_to = '自費處方'

        case_utils.copy_past_medical_record(
            self.database, self.system_settings, self.parent, case_key,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_remark.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_ins_prescript.isChecked(),
            copy_ins_prescript_to,
            self.ui.checkBox_ins_treat.isChecked(),
            self.ui.checkBox_self_prescript.isChecked(),
            False,
            self.ui.checkBox_not_overwrite.isChecked(),
        )
        self.parent.tabWidget_medical.setCurrentIndex(0)

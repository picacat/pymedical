
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox

import datetime

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import nhi_utils
from libs import string_utils
from libs import number_utils
from libs import registration_utils
from libs import patient_utils
from libs import dialog_utils
from libs import charge_utils


# 診斷證明
class DialogCertificateDiagnosis(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogCertificateDiagnosis, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.certificate_key = args[2]
        self.ui = None
        self.dialog_past_history = None

        self._set_ui()
        self._set_signal()

        if self.certificate_key is not None:
            self._read_certificate()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        if self.dialog_past_history is not None:
            self.dialog_past_history.deleteLater()
            self.dialog_past_history = None

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_CERTIFICATE_DIAGNOSIS, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.dateEdit_start_date.setDate(datetime.datetime.now())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.now())
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self._set_group_box(False)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

        certificate_Fee = charge_utils.get_charge_settings_fee(self.database, '證明書費', '自費', '診斷證明書費')
        if certificate_Fee in [None, 0]:
            certificate_Fee = 100

        self.ui.spinBox_certificate_fee.setValue(certificate_Fee)

    # *設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.lineEdit_patient_key.returnPressed.connect(self._get_patient)
        self.ui.lineEdit_patient_key.textChanged.connect(self._patient_key_changed)
        self.ui.toolButton_select_patient.clicked.connect(self._select_patient)
        self.ui.toolButton_modify_patient.clicked.connect(self._modify_patient)

        self.ui.dateEdit_start_date.dateChanged.connect(self._start_date_changed)
        self.ui.dateEdit_end_date.dateChanged.connect(self._end_date_changed)
        self.ui.comboBox_ins_type.currentTextChanged.connect(self._read_medical_record)
        self.ui.comboBox_treat_type.currentTextChanged.connect(self._read_medical_record)
        self.ui.toolButton_import_diagnosis.clicked.connect(self._import_diagnosis)
        self.ui.toolButton_doctor_comment.clicked.connect(self._import_doctor_comment)
        self.ui.textEdit_diagnosis.textChanged.connect(self._check_diagnosis_completed)
        self.ui.textEdit_doctor_comment.textChanged.connect(self._check_diagnosis_completed)
        self.ui.toolButton_open_past_history.clicked.connect(self._open_past_history)

    def _set_table_width(self):
        width = [100, 10, 130, 50, 100, 300, 90]
        self.table_widget_medical_record.set_table_heading_width(width)

    def _set_group_box(self, enabled):
        self.ui.lineEdit_name.setEnabled(enabled)
        self.ui.lineEdit_id.setEnabled(enabled)
        self.ui.lineEdit_birthday.setEnabled(enabled)
        self.ui.lineEdit_gender.setEnabled(enabled)
        self.ui.lineEdit_telephone.setEnabled(enabled)
        self.ui.lineEdit_address.setEnabled(enabled)

        self.ui.label_name.setEnabled(enabled)
        self.ui.label_id.setEnabled(enabled)
        self.ui.label_birthday.setEnabled(enabled)
        self.ui.label_gender.setEnabled(enabled)
        self.ui.label_telephone.setEnabled(enabled)
        self.ui.label_address.setEnabled(enabled)

        self.ui.groupBox_medical_record.setEnabled(enabled)
        self.ui.groupBox_diagnosis.setEnabled(enabled)

        self.ui.toolButton_modify_patient.setEnabled(enabled)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_ins_type, nhi_utils.INS_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_treat_type, ['針傷科', '針灸科', '傷骨科', '內科'], '全部')
        self._set_doctor()

    def _set_doctor(self):
        script = 'select * from person where Position IN ("醫師", "支援醫師") '
        rows = self.database.select_record(script)
        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)

    def accepted_button_clicked(self):
        if self.certificate_key is None:
            self._insert_certificate()
        else:
            self._modify_certificate()

    def _insert_certificate(self):
        if self.ui.checkBox_create_medical_record.isChecked():
            case_key = self._write_medical_record()
            self._write_prescript(case_key)
            self._write_wait(case_key)
        else:
            case_key = 0

        certificate_key = self._write_certificate(case_key)
        self._write_certificate_items(certificate_key)

    def _clear_patient_data(self):
        self.ui.lineEdit_name.setText('')
        self.ui.lineEdit_id.setText('')
        self.ui.lineEdit_birthday.setText('')
        self.ui.lineEdit_gender.setText('')
        self.ui.lineEdit_telephone.setText('')
        self.ui.lineEdit_address.setText('')

    def _set_patient_data(self, row):
        telephone = string_utils.xstr(row['Telephone'])
        if telephone == '':
            telephone = string_utils.xstr(row['Cellphone'])

        self.ui.lineEdit_name.setText(string_utils.xstr(row['Name']))
        self.ui.lineEdit_id.setText(string_utils.xstr(row['ID']))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row['Birthday']))
        self.ui.lineEdit_gender.setText(string_utils.xstr(row['Gender']))
        self.ui.lineEdit_telephone.setText(telephone)
        self.ui.lineEdit_address.setText(string_utils.xstr(row['Address']))

    def _set_date_edit_index(self, date_edit):
        if self.table_widget_medical_record.row_count() <= 0:
            return

        index = date_edit.currentSectionIndex()
        if index <= 1:
            date_edit.setFocus()
            date_edit.setCurrentSectionIndex(index+1)
        else:
            self.ui.dateEdit_end_date.setCurrentSectionIndex(0)
            self.ui.dateEdit_end_date.setFocus()

    def _start_date_changed(self):
        self._read_medical_record()
        self._set_date_edit_index(self.ui.dateEdit_start_date)

    def _end_date_changed(self):
        self._read_medical_record()
        self._set_date_edit_index(self.ui.dateEdit_end_date)

    def _read_medical_record(self):
        patient_key = self.ui.lineEdit_patient_key.text().strip()
        if patient_key in ['', None]:
            return

        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        treat_type_dict = {
            '針傷科': nhi_utils.INS_TREAT,
            '針灸科': nhi_utils.ACUPUNCTURE_TREAT,
            '傷骨科': nhi_utils.MASSAGE_TREAT,
        }

        condition = ''
        ins_type = self.ui.comboBox_ins_type.currentText()
        if ins_type in ['健保', '自費']:
            condition = f' AND InsType = "{ins_type}" '

        treat_type = self.ui.comboBox_treat_type.currentText()
        if treat_type == '內科':
            condition += ' AND TreatType IN ("內科", "一般") '
        elif treat_type != '全部':
            condition += f' AND TreatType IN {tuple(treat_type_dict[treat_type])} '

        purchase_condition = ' AND TreatType NOT IN ("自購", "開立證明")'
        if self.ui.checkBox_include_purchase.isChecked():
            purchase_condition = ''

        sql = f'''
            SELECT
                CaseKey, CaseDate, InsType, TreatType, Doctor, DiseaseName1, DiseaseName2, DiseaseName3
            FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key} AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0
                {purchase_condition}
                {condition}
            GROUP BY DATE(CaseDate)
            ORDER BY CaseDate
        '''
        self.ui.tableWidget_medical_record.setRowCount(0)
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data, set_focus=False)
        record_count = self.ui.tableWidget_medical_record.rowCount()
        self.ui.label_record_count.setText(f'門診次數: {record_count}次')
        self.ui.label_checked_count.setText(f'選取次數: {record_count}次')
        self._check_diagnosis_completed()
        self._set_doctor_field()

        if self.ui.tableWidget_medical_record.rowCount() <= 0:
            self.ui.tableWidget_medical_record.setRowCount(1)
            self.ui.tableWidget_medical_record.setItem(0, 4, QtWidgets.QTableWidgetItem('查無病歷'))

    def _set_table_data(self, row_no, row):
        disease_list = []
        disease_name1 = string_utils.xstr(row['DiseaseName1'])
        disease_name2 = string_utils.xstr(row['DiseaseName2'])
        disease_name3 = string_utils.xstr(row['DiseaseName3'])
        if disease_name1 != '':
            disease_list.append(disease_name1)
        if disease_name2 != '':
            disease_list.append(disease_name2)
        if disease_name3 != '':
            disease_list.append(disease_name3)

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            None,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            ', '.join(disease_list),
            string_utils.xstr(row['Doctor']),
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )

            if column in [3]:
                self.ui.tableWidget_medical_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        check_box = QtWidgets.QCheckBox(self.ui.tableWidget_medical_record)
        check_box.setChecked(True)
        check_box.clicked.connect(self._check_box_medical_record_clicked)
        self.ui.tableWidget_medical_record.setCellWidget(row_no, 1, check_box)

    def _check_box_medical_record_clicked(self):
        checked_count = 0
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is not None and check_box.isChecked():
                checked_count += 1

        self.ui.label_checked_count.setText(f'選取次數: {checked_count}次')

    # def _import_diagnosis(self):
    #     case_key = self.table_widget_medical_record.field_value(0)
    #     sql = f'''
    #         SELECT
    #             cases.Symptom,
    #             cases.DiseaseCode1, cases.DiseaseName1, icd10.EnglishName,
    #             cases.DiseaseCode2, cases.DiseaseName2,
    #             cases.DiseaseCode3, cases.DiseaseName3
    #         FROM cases
    #             LEFT JOIN icd10 ON cases.DiseaseCode1 = icd10.ICDCode
    #         WHERE
    #             CaseKey = "{case_key}"
    #     '''
    #     rows = self.database.select_record(sql)
    #     if len(rows) <= 0:
    #         return

    #     row = rows[0]
    #     disease_code1 = string_utils.xstr(row['DiseaseCode1'])
    #     disease_name1 = string_utils.xstr(row['DiseaseName1'])
    #     disease_code2 = string_utils.xstr(row['DiseaseCode2'])
    #     disease_name2 = string_utils.xstr(row['DiseaseName2'])
    #     disease_code3 = string_utils.xstr(row['DiseaseCode3'])
    #     disease_name3 = string_utils.xstr(row['DiseaseName3'])
    #     english_name = row['EnglishName']

    #     diagnosis = f'{disease_code1} {disease_name1} {english_name}'
    #     if disease_code2 != '':
    #         diagnosis += f'<br>{disease_code2} {disease_name2}'
    #     if disease_code3 != '':
    #         diagnosis += f'<br>{disease_code3} {disease_name3}'

    #     if self.ui.checkBox_import_symptom.isChecked():
    #         symptom = string_utils.get_str(row['Symptom'], 'utf8')
    #         diagnosis += f'<br>{symptom}'

    #     diagnosis += '(以下空白)'

    #     self.ui.textEdit_diagnosis.setText(diagnosis)

    def _import_diagnosis(self):
        disease_code_list = []
        symptom = ''

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            item = self.ui.tableWidget_medical_record.item(row_no, 0)
            if item is None:
                continue

            case_key = item.text()
            sql = f'''
                SELECT
                    cases.DiseaseCode1, cases.DiseaseCode2, cases.DiseaseCode3,
                    cases.Symptom
                FROM cases
                WHERE
                    CaseKey = "{case_key}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return

            row = rows[0]
            if symptom == '':
                symptom = string_utils.get_str(row['Symptom'], 'utf8')

            for i in range(1, 4):
                disease_code = string_utils.xstr(row[f'DiseaseCode{i}'])
                if disease_code != '' and disease_code not in disease_code_list:
                    disease_code_list.append(disease_code)

        disease_name_list = []
        for disease_code in disease_code_list:
            sql = f'''
                SELECT ChineseName, EnglishName FROM icd10
                WHERE
                    ICDCode = "{disease_code}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue
            
            row = rows[0]
            disease_name = string_utils.xstr(row['ChineseName'])
            english_name = string_utils.xstr(row['EnglishName'])

            if self.ui.checkBox_no_english.isChecked():
                english_name = ''
                disease_code = ''

            diagnosis_name = f'{disease_code} {disease_name} {english_name}'
            disease_name_list.append(diagnosis_name)

        diagnosis = '<br>'.join(disease_name_list)

        if self.ui.checkBox_import_symptom.isChecked():
            diagnosis += f'<br>{symptom}'

        if self.ui.checkBox_no_english.isChecked():
            diagnosis += '<br>(以下空白)'
        else:
            diagnosis += '<br>(以下空白 This space intentionally left blank)'

        self.ui.textEdit_diagnosis.setText(diagnosis)

    def add_order(self, doctor_comment):
        comment_line = []
        comment = self.ui.textEdit_doctor_comment.toPlainText().replace('(以下空白 This space intentionally left blank)', '')
        if comment != '':
            comment_line = [comment]

        comment_line.append(doctor_comment)

        if self.ui.checkBox_no_english.isChecked():
            self.ui.textEdit_doctor_comment.setText('\n'.join(comment_line) + '(以下空白)')
        else:
            self.ui.textEdit_doctor_comment.setText('\n'.join(comment_line) + '(以下空白 This space intentionally left blank)')

    def _import_doctor_comment(self):
        dialog = dialog_utils.get_dialog_simple_dict(self, self.database, self.system_settings)
        dialog.exec_()
        dialog.deleteLater()

    def _check_diagnosis_completed(self):
        diagnosis = self.ui.textEdit_diagnosis.toPlainText()
        doctor_comment = self.ui.textEdit_doctor_comment.toPlainText()

        if (diagnosis != '' and doctor_comment != '' and
                self.ui.tableWidget_medical_record.rowCount() > 0):
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def _set_doctor_field(self):
        if self.ui.tableWidget_medical_record.rowCount() <= 0:
            return

        doctor_field = self.ui.tableWidget_medical_record.item(0, 6)
        if doctor_field is None:
            return

        doctor = doctor_field.text()
        self.ui.comboBox_doctor.setCurrentText(doctor)

    def _get_start_date(self):
        start_date = None
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is not None and check_box.isChecked():
                start_date = self.ui.tableWidget_medical_record.item(row_no, 2).text()
                break

        return start_date

    def _get_end_date(self):
        end_date = None
        for row_no in range(self.ui.tableWidget_medical_record.rowCount()-1, -1, -1):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is not None and check_box.isChecked():
                end_date = self.ui.tableWidget_medical_record.item(row_no, 2).text()
                break

        return end_date

    def _write_certificate(self, case_key, insert_date=None):
        if self.ui.checkBox_create_medical_record.isChecked():
            certificate_fee = self.ui.spinBox_certificate_fee.value()
        else:
            certificate_fee = None

        fields = [
            'CaseKey', 'PatientKey', 'Name', 'CertificateDate', 'CertificateType',
            'InsType', 'TreatType', 'StartDate', 'EndDate', 'Doctor',
            'Diagnosis', 'DoctorComment', 'CertificateFee',
        ]

        start_date = self._get_start_date()
        end_date = self._get_end_date()
        if insert_date is None:
            certificate_date = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            certificate_date = insert_date

        data = [
            case_key,
            self.ui.lineEdit_patient_key.text(),
            self.ui.lineEdit_name.text(),
            certificate_date,
            '診斷證明',
            self.ui.comboBox_ins_type.currentText(),
            self.ui.comboBox_treat_type.currentText(),
            start_date,
            end_date,
            self.ui.comboBox_doctor.currentText(),
            self.ui.textEdit_diagnosis.toPlainText(),
            self.ui.textEdit_doctor_comment.toPlainText(),
            certificate_fee,
        ]

        certificate_key = self.database.insert_record('certificate', fields, data)

        return certificate_key

    def _write_certificate_items(self, certificate_key):
        fields = [
            'CertificateKey', 'CaseKey', 'CaseDate', 'InsType',
        ]

        row_count = self.ui.tableWidget_medical_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is None:
                continue

            if not check_box.isChecked():
                continue

            case_key = self.ui.tableWidget_medical_record.item(row_no, 0).text()
            case_date = self.ui.tableWidget_medical_record.item(row_no, 2).text()
            ins_type = self.ui.tableWidget_medical_record.item(row_no, 3).text()
            data = [
                certificate_key,
                case_key,
                case_date,
                ins_type,
            ]

            self.database.insert_record('certificate_items', fields, data)

    def _write_medical_record(self):
        certificate_fee = self.ui.spinBox_certificate_fee.value()

        case_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        period = registration_utils.get_current_period(self.system_settings)
        charge_date = None
        charge_period = None
        charge_done = 'False'

        if self.system_settings.field('自動完成批價作業') == 'Y':
            charge_date = case_date
            charge_period = period
            charge_done = 'True'

        fields = [
            'PatientKey', 'Name', 'CaseDate', 'DoctorDate',
            'Period', 'InsType', 'TreatType', 'Register',
            'SMaterialFee', 'SelfTotalFee', 'TotalFee',
            'DoctorDone',
            'ChargeDate', 'ChargePeriod', 'ChargeDone',
        ]
        data = [
            self.ui.lineEdit_patient_key.text(), self.ui.lineEdit_name.text(), case_date, case_date,
            period, '自費', '開立證明', self.system_settings.field('使用者'),
            certificate_fee,
            certificate_fee,
            certificate_fee,
            'True',
            charge_date, charge_period, charge_done,
        ]

        if self.system_settings.field('自動完成批價作業') == 'Y':
            fields.append('ReceiptFee')
            data.append(certificate_fee)

        case_key = self.database.insert_record('cases', fields, data)

        return case_key

    def _write_prescript(self, case_key):
        certificate_fee = self.ui.spinBox_certificate_fee.value()

        fields = [
            'PrescriptNo', 'CaseKey', 'CaseDate',
            'MedicineSet', 'MedicineType', 'MedicineKey',
            'MedicineName', 'Dosage', 'Unit',
            'Price', 'Amount',
        ]

        data = [
            1,
            case_key,
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            2,
            '器材',
            0,
            '診斷證明書',
            1,
            '份',
            certificate_fee,
            certificate_fee,
        ]

        self.database.insert_record('prescript', fields, data)

    def _write_wait(self, case_key):
        case_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        period = registration_utils.get_current_period(self.system_settings)
        charge_done = 'False'

        if self.system_settings.field('自動完成批價作業') == 'Y':
            charge_done = 'True'

        fields = [
            'CaseKey', 'CaseDate', 'PatientKey', 'Name', 'Visit', 'RegistType',
            'TreatType', 'InsType', 'Period',
            'Room', 'RegistNo', 'DoctorDone',
            'ChargeDone',
        ]

        data = [
            case_key, case_date, self.ui.lineEdit_patient_key.text(), self.ui.lineEdit_name.text(), '複診', '一般門診',
            '開立證明', '自費', period,
            1, 0, 'True',
            charge_done,
        ]

        self.database.insert_record('wait', fields, data)

    def _open_past_history(self):
        patient_key = self.ui.lineEdit_patient_key.text()
        dialog = dialog_utils.get_dialog_medical_record_past_history(
            self, self.database, self.system_settings, None, patient_key, '診斷證明'
        )

        dialog.exec_()
        dialog.deleteLater()

    def _get_certificate_row(self, certificate_key):
        sql = f'''
            SELECT * FROM certificate
            WHERE
                CertificateKey = {certificate_key} AND
                CertificateType = "診斷證明"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]

        return row

    def _read_certificate(self):
        row = self._get_certificate_row(self.certificate_key)
        if row is None:
            return

        start_date = row['StartDate']
        end_date = row['EndDate']
        if start_date is not None:
            self.ui.dateEdit_start_date.setDate(start_date)
        if end_date is not None:
            self.ui.dateEdit_end_date.setDate(end_date)

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(row['PatientKey']))
        self.ui.comboBox_ins_type.setCurrentText(string_utils.xstr(row['InsType']))
        self.ui.comboBox_treat_type.setCurrentText(string_utils.xstr(row['TreatType']))
        self.ui.comboBox_doctor.setCurrentText(string_utils.xstr(row['Doctor']))
        self.ui.spinBox_certificate_fee.setValue(number_utils.get_integer(row['CertificateFee']))
        self.ui.textEdit_diagnosis.setText(string_utils.xstr(row['Diagnosis']))
        self.ui.textEdit_doctor_comment.setText(string_utils.xstr(row['DoctorComment']))

        if self.ui.spinBox_certificate_fee.value() > 0:
            self.ui.checkBox_create_medical_record.setChecked(True)

        self._set_medical_record_check_box(self.certificate_key)
        self._check_box_medical_record_clicked()

    def _set_medical_record_check_box(self, certificate_key):
        sql = f'''
            SELECT * FROM certificate_items
            WHERE
                CertificateKey = {certificate_key}
        '''
        rows = self.database.select_record(sql)

        case_key_list = []
        for row in rows:
            case_key_list.append(row['CaseKey'])

        for row_no in range(self.ui.tableWidget_medical_record.rowCount()):
            case_key_item = self.ui.tableWidget_medical_record.item(row_no, 0)
            if case_key_item is None:
                continue

            case_key = number_utils.get_integer(case_key_item.text())
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if check_box is not None and case_key not in case_key_list:
                check_box.setChecked(False)

    def _modify_certificate(self):
        row = self._get_certificate_row(self.certificate_key)
        if row is None:
            return

        case_key = row['CaseKey']
        certificate_date = row['CertificateDate']
        certificate_fee = number_utils.get_integer(row['CertificateFee'])

        certificate_key = self._write_certificate(case_key, certificate_date)
        self._write_certificate_items(certificate_key)

        self.database.exec_sql(f'''
            DELETE FROM certificate
            WHERE
                CertificateKey = {self.certificate_key}
        ''')
        self.database.exec_sql(f'''
            DELETE FROM certificate_items
            WHERE
                CertificateKey = {self.certificate_key}
        ''')

        if certificate_fee == 0 and self.ui.spinBox_certificate_fee.value() > 0:
            new_case_key = self._write_medical_record()
            self._write_prescript(new_case_key)
            self._write_wait(new_case_key)

    def _patient_key_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text().strip()

        if patient_key == '':
            self._clear_patient_data()
            self._set_group_box(False)
            return

        if patient_key.isdigit() and len(patient_key) <= 6:
            self._set_line_edit_patient_data(patient_key)
        else:
            self._clear_patient_data()

    def _modify_patient(self):
        patient_key = self.ui.lineEdit_patient_key.text().strip()
        fields = ['Telephone', 'Address']
        data = [
            self.ui.lineEdit_telephone.text(),
            self.ui.lineEdit_address.text(),
        ]
        self.database.update_record('patient', fields, 'PatientKey', patient_key, data)
        system_utils.show_message_box(
            QMessageBox.Information,
            '資料存檔完成',
            '<h3>病患電話及地址存檔完成.</h3>',
            '只開放修改電話及地址'
        )

    def _select_patient(self):
        patient_key = patient_utils.select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', ''
        )
        if patient_key in ['', None]:
            return

        self._set_line_edit_patient_data(patient_key)

    def _get_patient(self):
        keyword = self.ui.lineEdit_patient_key.text().strip()

        patient_key = patient_utils.get_patient_by_keyword(
            self, self.database, self.system_settings,
            'patient', 'PatientKey', keyword
        )
        if patient_key in ['', None]:
            return

        self._set_line_edit_patient_data(patient_key)

    def _set_line_edit_patient_data(self, patient_key):
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))

        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        self._set_patient_data(row)
        self._set_group_box(True)
        self._read_medical_record()

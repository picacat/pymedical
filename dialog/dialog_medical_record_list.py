
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime
import os
import re

from libs import (date_utils, dialog_utils, nhi_utils, patient_utils,
                  personnel_utils, system_utils, ui_utils)
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog


# 病歷查詢視窗
class DialogMedicalRecordList(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordList, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.ui.dateEdit_start_date.setFocus()
        self.ui.dateEdit_start_date.setCurrentSection(QtWidgets.QDateEdit.DaySection)
        
    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_LIST, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)

        default_date = date_utils.get_default_date(self.system_settings)
        self.ui.dateEdit_start_date.setDate(default_date)
        self.ui.dateEdit_end_date.setDate(default_date)
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.ui.label_patient_key.setEnabled(False)
        self.ui.lineEdit_patient_key.setEnabled(False)
        self.ui.toolButton_select_patient.setEnabled(False)
        self.ui.toolButton_select_patient_list.setEnabled(False)

        self.ui.checkBox_enable_end_date.setChecked(False)
        self.set_end_date()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_select_patient.clicked.connect(lambda: self._select_patient(None))
        self.ui.toolButton_select_patient_list.clicked.connect(self._select_patient_list)

        self.ui.radioButton_range_date.clicked.connect(self._set_date)
        self.ui.radioButton_all_date.clicked.connect(self._set_date)

        self.ui.radioButton_all_patient.clicked.connect(self._set_patient)
        self.ui.radioButton_assigned_patient.clicked.connect(self._set_patient)
        self.ui.groupBox_advance_search.toggled.connect(self._group_box_advance_search_clicked)
        self.ui.checkBox_enable_end_date.clicked.connect(self.set_end_date)
        self.ui.lineEdit_patient_key.textChanged.connect(self._set_ok_button)
        # self.ui.dateEdit_start_date.dateChanged.connect(self._set_end_date_value)

    def set_end_date(self):
        if self.ui.checkBox_enable_end_date.isChecked():
            self.ui.dateEdit_end_date.setEnabled(True)
        else:
            self.ui.dateEdit_end_date.setEnabled(False)

    def _set_end_date_value(self):
        self.ui.dateEdit_end_date.setDate(self.ui.dateEdit_start_date.date())

    def _group_box_advance_search_clicked(self):
        if self.ui.groupBox_advance_search.isChecked():
            self.ui.radioButton_all_patient.setEnabled(True)
        else:
            self.ui.radioButton_assigned_patient.setChecked(True)
            if self.ui.radioButton_all_date.isChecked():
                self.ui.radioButton_all_patient.setEnabled(False)
            else:
                self.ui.radioButton_all_patient.setEnabled(True)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_ins_type, nhi_utils.INS_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_regist_type, nhi_utils.REG_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_share_type, nhi_utils.SHARE_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_injury_type, nhi_utils.INJURY_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_apply_type, nhi_utils.APPLY_TYPE, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_room, nhi_utils.ROOM, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_visit, nhi_utils.VISIT, '全部')
        ui_utils.set_combo_box(
            self.ui.comboBox_doctor,
            personnel_utils.get_person(self.database, '全部醫師'), '全部',
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_registrar,
            personnel_utils.get_person(self.database, '全部'), '全部',
        )

        system_utils.set_combo_box_treat_type(self.ui.comboBox_treat_type)
        self.ui.comboBox_treat_type.insertItem(0, '全部')
        self.ui.comboBox_treat_type.setCurrentIndex(0)

    def _set_patient(self):
        if self.ui.radioButton_all_patient.isChecked():
            self.ui.lineEdit_patient_key.setText('')
            enabled = False
        else:
            enabled = True

        self.ui.label_patient_key.setEnabled(enabled)
        self.ui.lineEdit_patient_key.setEnabled(enabled)
        self.ui.toolButton_select_patient.setEnabled(enabled)
        self.ui.toolButton_select_patient_list.setEnabled(enabled)

        if self.ui.radioButton_assigned_patient.isChecked():
            self.ui.lineEdit_patient_key.setFocus()

    def _set_ok_button(self):
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        if not self.ui.radioButton_all_date.isChecked():
            return

        if self.ui.lineEdit_patient_key.text() == '':
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def _set_date(self):
        if self.ui.radioButton_all_date.isChecked():
            enabled = False
            self.ui.radioButton_assigned_patient.setChecked(True)
            self._set_patient()
            self.ui.lineEdit_patient_key.setFocus()
        else:
            enabled = True
            self.ui.radioButton_all_patient.setChecked(True)
            self._set_patient()

        self.ui.label_date.setEnabled(enabled)
        self.ui.label_period.setEnabled(enabled)
        self.ui.dateEdit_start_date.setEnabled(enabled)
        self.ui.dateEdit_end_date.setEnabled(enabled)
        self.ui.comboBox_period.setEnabled(enabled)

        if self.ui.groupBox_advance_search.isChecked():
            self.ui.radioButton_all_patient.setEnabled(True)
        else:
            self.ui.radioButton_all_patient.setEnabled(enabled)

        self._set_ok_button()

    # 設定 mysql script
    def get_sql(self, select_fields=None):
        if select_fields is None:
            select_fields = self.parent.get_select_fields()
            left_join_fields = '''
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                LEFT JOIN wait ON wait.CaseKey = cases.CaseKey
            '''
            order_by = True
        else:
            left_join_fields = ''
            order_by = False

        sql = f'''
            SELECT
                {select_fields}
            FROM cases
                {left_join_fields}
        '''
        sql += self._get_condition(order_by=order_by)

        return sql

    def _get_condition(self, order_by=False):
        order_method = 'default'
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        ins_type = self.ui.comboBox_ins_type.currentText()
        apply_type = self.ui.comboBox_apply_type.currentText()
        regist_type = self.ui.comboBox_regist_type.currentText()
        treat_type = self.ui.comboBox_treat_type.currentText()
        share_type = self.ui.comboBox_share_type.currentText()
        injury_type = self.ui.comboBox_injury_type.currentText()
        room = self.ui.comboBox_room.currentText()
        visit = self.ui.comboBox_visit.currentText()
        doctor = self.ui.comboBox_doctor.currentText()
        registrar = self.ui.comboBox_registrar.currentText()
        keyword = self.ui.lineEdit_patient_key.text()

        address = self.ui.lineEdit_address.text().strip()
        disease_list = self.ui.lineEdit_disease.text().split()
        symptom_list = self.ui.lineEdit_symptom.text().split()
        medicine_list = self.ui.lineEdit_medicine_name.text().split()
        remark_list = self.ui.lineEdit_remark.text().split()

        sql_condition = ''
        condition = []

        if self.ui.groupBox_advance_search.isChecked() and len(medicine_list) > 0:
            sql_condition += ' LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey '

        if self.ui.radioButton_range_date.isChecked():
            if self.ui.checkBox_enable_end_date.isChecked():
                condition.append(f'(cases.CaseDate BETWEEN "{start_date}" AND "{end_date}")')
            else:
                condition.append(f'(DATE(cases.CaseDate) = "{start_date}")')

            period = self.ui.comboBox_period.currentText()
            if period != '全部':
                condition.append(f'cases.Period = "{period}"')

            weekday_list = []
            if self.checkBox_mon.isChecked():
                weekday_list.append('0')
            if self.checkBox_tue.isChecked():
                weekday_list.append('1')
            if self.checkBox_wed.isChecked():
                weekday_list.append('2')
            if self.checkBox_thu.isChecked():
                weekday_list.append('3')
            if self.checkBox_fri.isChecked():
                weekday_list.append('4')
            if self.checkBox_sat.isChecked():
                weekday_list.append('5')
            if self.checkBox_sun.isChecked():
                weekday_list.append('6')

            if len(weekday_list) > 0:
                condition.append(f'WEEKDAY(cases.CaseDate) IN({",".join(weekday_list)})')

        if self.system_settings.field('病歷查詢預設健保') == 'Y':
            condition.append(f'cases.InsType = "健保"')
        elif ins_type != '全部':
            condition.append(f'cases.InsType = "{ins_type}"')

        if self.ui.checkBox_total_fee.isChecked():
            condition.append('cases.TotalFee > 0')

        if self.ui.checkBox_discount_fee.isChecked():
            condition.append('cases.DiscountFee > 0')

        if apply_type != '全部':
            condition.append(f'cases.ApplyType = "{apply_type}"')

        if regist_type != '全部':
            condition.append(f'cases.RegistType = "{regist_type}"')

        if treat_type != '全部':
            condition.append(f'cases.TreatType = "{treat_type}"')

        if not self.ui.checkBox_show_traditional_cure.isChecked():
            condition.append('''
                ((cases.InsType = "健保") OR
                 (cases.InsType = "自費" AND (Position1 IS NULL OR LENGTH(Position1) = 0))
                )
            ''')

        if share_type != '全部':
            condition.append(f'cases.Share = "{share_type}"')

        if injury_type != '全部':
            condition.append(f'cases.Injury = "{injury_type}"')

        if room != '全部':
            condition.append(f'cases.Room = {room}')

        if visit != '全部':
            condition.append(f'cases.Visit = "{visit}"')

        if doctor != '全部':
            condition.append(f'(cases.Doctor = "{doctor}" and cases.TreatType != "自購")')

        if registrar != '全部':
            condition.append(f'cases.Register = "{registrar}"')

        if address != '':
            condition.append(f'patient.Address LIKE "%{address}%"')

        if self.ui.groupBox_advance_search.isChecked() and len(disease_list) > 0:
            disease_condition = []
            for disease in disease_list:
                disease_condition.append(
                    f'(cases.DiseaseCode1 LIKE "%{disease}%" OR cases.DiseaseName1 LIKE "%{disease}%")')

            disease_condition = ' AND '.join(disease_condition)
            disease_condition = f'({disease_condition})'
            condition.append(disease_condition)

        if self.ui.groupBox_advance_search.isChecked() and len(symptom_list) > 0:
            symptom_condition = []
            for symptom in symptom_list:
                symptom_condition.append(f'cases.Symptom LIKE "%{symptom}%"')

            symptom_condition = ' AND '.join(symptom_condition)
            symptom_condition = f'({symptom_condition})'
            condition.append(symptom_condition)

        if self.ui.groupBox_advance_search.isChecked() and len(medicine_list) > 0:
            medicine_condition = []
            for medicine in medicine_list:
                medicine_condition.append(f'prescript.MedicineName LIKE "%{medicine}%"')

            medicine_condition = ' OR '.join(medicine_condition)
            medicine_condition = f'({medicine_condition})'
            condition.append(medicine_condition)

        if self.ui.groupBox_advance_search.isChecked() and len(remark_list) > 0:
            remark_condition = []
            for remark in remark_list:
                remark_condition.append(f'cases.Remark LIKE "%{remark}%"')

            remark_condition = ' AND '.join(remark_condition)
            remark_condition = f'({remark_condition})'
            condition.append(remark_condition)

        if keyword != '':
            if os.path.exists(keyword):
                patient_key_list = self._get_patient_key_list(keyword)
                if len(patient_key_list) >= 2:
                    condition.append(f'cases.PatientKey IN {tuple(patient_key_list)}')
                    order_method = 'patient_key'
            else:
                pattern = re.compile('^[0-9]*-[0-9]*$')
                if pattern.match(keyword):
                    patient_key_list = keyword.split('-')
                    condition.append(f'cases.PatientKey BETWEEN {patient_key_list[0]} AND {patient_key_list[1]}')
                    order_method = 'patient_key'
                else:
                    patient_key = patient_utils.get_patient_by_keyword(
                        self, self.database, self.system_settings,
                        'patient', 'PatientKey', keyword,
                    )

                    if patient_key in ['', None]:
                        return ''
                    else:
                        condition.append(f'cases.PatientKey = {patient_key}')
                        order_method = 'single_patient'

        if len(condition) > 0:
            condition = ' AND '.join(condition)
            sql_condition += f' WHERE {condition} '

        if self.ui.groupBox_advance_search.isChecked() and len(medicine_list) > 0:
            sql_condition += f' GROUP BY cases.CaseKey HAVING COUNT(cases.CaseKey) >= {len(medicine_list)} '

        if order_by:
            if order_method == 'patient_key':
                order_condition = 'ORDER BY PatientKey, DATE(cases.CaseDate)'
            elif order_method == 'single_patient':
                if self.system_settings.field('病歷查詢日期排序') == '降冪':
                    order_condition = 'ORDER BY PatientKey, DATE(cases.CaseDate) DESC'
                else:
                    order_condition = 'ORDER BY PatientKey, DATE(cases.CaseDate)'
            else:
                period_list = str(nhi_utils.PERIOD)[1:-1]
                order_condition = f'''
                    ORDER BY DATE(cases.CaseDate), FIELD(cases.Period, {period_list}), cases.RegistNo, cases.Room
                '''

            sql_condition += order_condition

        return sql_condition

    def _get_patient_key_list(self, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        patient_key_list = []
        for patient_key in lines:
            patient_key = patient_key.replace('\n', '')
            if patient_key != '':
                patient_key_list.append(patient_key)

        return patient_key_list

    def accepted_button_clicked(self):
        pass

    def _select_patient(self, keyword=None):
        patient_key = ''

        dialog = dialog_utils.get_dialog_select_patient(
            self, self.database, self.system_settings, 'patient', 'PatientKey', keyword
        )
        if dialog.exec_():
            patient_key = dialog.get_primary_key()

        self.ui.lineEdit_patient_key.setText(patient_key)

        dialog.deleteLater()

    def _select_patient_list(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        file_name, _ = QFileDialog.getOpenFileName(
            self, "選擇病患名單檔",
            '*.txt',
            "所有檔案 (*);;xml檔 (*.txt)", options=options
        )
        if not file_name:
            return

        self.ui.lineEdit_patient_key.setText(file_name)

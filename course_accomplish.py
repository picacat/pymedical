# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QMessageBox

import datetime

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import personnel_utils
from libs import registration_utils
from libs import medicine_utils


# 療程實現
class CourseAccomplish(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(CourseAccomplish, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_COURSE_ACCOMPLISH, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database)
        self.table_widget_prescript.set_column_hidden([0])
        width = [
            100,
            120, 70, 300, 100, 120,
        ]
        self.table_widget_prescript.set_table_heading_width(width)
        self._set_group_box_booking(True)

        doctor_list = personnel_utils.get_person(self.database, '醫師')
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list, None)
        massager_list = personnel_utils.get_person(self.database, '推拿師父')
        ui_utils.set_combo_box(self.ui.comboBox_massager, massager_list, None)
        nursing_assistant = personnel_utils.get_person(self.database, '職員')
        ui_utils.set_combo_box(self.ui.comboBox_nursing_assistant, nursing_assistant, None)
        ui_utils.set_combo_box(self.ui.comboBox_treat_type, ['療程實現', '療程實現贈送'], None)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_course_accomplish)
        self.ui.action_cancel.triggered.connect(self._cancel_booking)
        self.ui.action_save.triggered.connect(self._save_course)
        self.ui.toolButton_course_query.clicked.connect(self._query_course)
        self.ui.lineEdit_query.textChanged.connect(self._set_line_edit_query)
        self.ui.lineEdit_query.returnPressed.connect(self._query_course)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_course_accomplish(self):
        self.close_all()
        self.close_tab()

    def _set_group_box_booking(self, enabled):
        self._clear_data()

        self.ui.groupBox_booking.setEnabled(enabled)
        self.ui.groupBox_cases.setEnabled(not enabled)
        self.ui.groupBox_prescript.setEnabled(not enabled)
        self.ui.groupBox_course_accomplish.setEnabled(not enabled)
        self.ui.action_save.setEnabled(not enabled)
        self.ui.action_cancel.setEnabled(not enabled)

        self.ui.lineEdit_query.setText(None)
        self.ui.toolButton_course_query.setEnabled(False)

        self.ui.lineEdit_query.setFocus()

    def _clear_data(self):
        self.ui.lineEdit_patient_key.setText(None)
        self.ui.lineEdit_name.setText(None)
        self.ui.lineEdit_case_date.setText(None)
        self.ui.lineEdit_introducer.setText(None)
        self.ui.lineEdit_medicine_name.setText(None)
        self.ui.lineEdit_invoice_no.setText(None)
        self.ui.lineEdit_quantity.setText(None)
        self.ui.lineEdit_total_fee.setText(None)
        self.ui.lineEdit_usage.setText(None)
        self.ui.lineEdit_remain.setText(None)

        self.ui.tableWidget_prescript.setRowCount(0)

        self.ui.spinBox_quantity.setValue(1)
        self.ui.comboBox_doctor.setCurrentText(None)
        self.ui.comboBox_massager.setCurrentText(None)
        self.ui.comboBox_nursing_assistant.setCurrentText(None)

    def _set_line_edit_query(self):
        if self.ui.lineEdit_query.text() == '':
            self.ui.toolButton_course_query.setEnabled(False)
        else:
            self.ui.toolButton_course_query.setEnabled(True)

    def _cancel_booking(self):
        self._set_group_box_booking(True)

    def _query_course(self):
        invoice_no = self.ui.lineEdit_query.text()
        sql = f'''
            SELECT
                cases.*,
                prescript.MedicineKey, prescript.MedicineName, prescript.Dosage, prescript.Instruction
            FROM cases
                LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey
            WHERE
                InvoiceNo = "{invoice_no}" AND
                InsType = "自費" AND
                TreatType = "自購"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '查無資料',
                '<font color="red"><h3>查無療程實現購買資料, 請重新查詢!</h3></font>',
                '請確認療程卡編號是否正確.'
            )
            return

        row = rows[0]

        self._set_group_box_booking(False)
        self._set_prescript_data(row)
        self._set_case_data(row)

        if number_utils.get_integer(self.ui.lineEdit_remain.text()) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '療程次數用罄',
                '<font color="red"><h3>此人購買的療程次數已經用盡, 無法繼續療程實現!</h3></font>',
                '請確認療程是否使用完畢.'
            )
            self._set_group_box_booking(True)

    def _set_prescript_data(self, row):
        invoice_no = string_utils.xstr(row['InvoiceNo'])

        sql = f'''
            SELECT
                cases.CaseDate, cases.Period, cases.Doctor, cases.MassageReferrer, cases.NursingAssistant,
                prescript.PrescriptKey, prescript.MedicineName, prescript.Dosage
            FROM cases
                LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey
            WHERE
                InvoiceNo = "{invoice_no}" AND
                InsType = "自費" AND
                TreatType LIKE "療程實現%"
            GROUP BY prescript.CaseKey
            ORDER BY cases.CaseDate
        '''
        self.table_widget_prescript.set_db_data(sql, self._set_table_data)

    def _get_treat_type(self):
        bonus = number_utils.get_integer(self.ui.lineEdit_bonus.text())
        remain = number_utils.get_integer(self.ui.lineEdit_remain.text())
        if bonus > 0 and remain > 0 and remain <= bonus:
            treat_type = '療程實現贈送'
        else:
            treat_type = '療程實現'

        return treat_type

    def _set_table_data(self, row_no, row):
        operator = self._get_employee(row)

        medicine_name = string_utils.xstr(row['MedicineName'])
        dosage = number_utils.get_integer(row['Dosage'])
        if dosage < 0:
            dosage = 0

        prescript_row = [
            string_utils.xstr(row['PrescriptKey']),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Period']),
            medicine_name,
            string_utils.xstr(dosage),
            operator,
        ]

        for col_no in range(len(prescript_row)):
            self.ui.tableWidget_prescript.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(prescript_row[col_no])
            )
            if col_no in [2, 4]:
                self.ui.tableWidget_prescript.item(
                    row_no, col_no).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _get_employee(self, row):
        doctor = string_utils.xstr(row['Doctor'])
        massager = string_utils.xstr(row['MassageReferrer'])
        nursing_assistant = string_utils.xstr(row['NursingAssistant'])
        employee_list = []
        if doctor != '':
            employee_list.append(doctor)
        if massager != '':
            employee_list.append(massager)
        if nursing_assistant != '':
            employee_list.append(nursing_assistant)

        employee = ', '.join(employee_list)

        return employee

    def _get_medicine_row(self, medicine_key):
        if medicine_key in ['', None]:
            return None

        sql = f'''
            SELECT * FROM medicine
            WHERE
                MedicineKey = {medicine_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        return rows[0]

    def _set_case_data(self, row):
        medicine_row = self._get_medicine_row(row['MedicineKey'])
        if medicine_row is None:
            quantity = 0
            bonus = 0
        else:
            quantity = number_utils.get_integer(medicine_row['Dosage'])
            bonus = medicine_utils.get_medicine_extend(self.database, row['MedicineKey'], '療程實現贈送')

        patient_key = string_utils.xstr(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        case_date = string_utils.xstr(row['CaseDate'].date())
        invoice_no = string_utils.xstr(row['InvoiceNo'])
        introducer = self._get_employee(row)
        medicine_name = string_utils.xstr(row['MedicineName'])
        total_quantity = number_utils.get_integer(row['Instruction'])
        total_fee = number_utils.get_integer(row['TotalFee'])
        massage_referrer = string_utils.xstr(row['MassageReferrer'])
        total_usage = self._get_total_usage()
        remain = total_quantity - total_usage

        self.ui.lineEdit_patient_key.setText(patient_key)
        self.ui.lineEdit_name.setText(name)
        self.ui.lineEdit_case_date.setText(case_date)
        self.ui.lineEdit_introducer.setText(string_utils.xstr(introducer))
        self.ui.lineEdit_medicine_name.setText(medicine_name)
        self.ui.lineEdit_invoice_no.setText(invoice_no)
        self.ui.lineEdit_quantity.setText(string_utils.xstr(quantity))
        self.ui.lineEdit_bonus.setText(string_utils.xstr(bonus))
        self.ui.lineEdit_total_quantity.setText(string_utils.xstr(total_quantity))
        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))
        self.ui.lineEdit_usage.setText(string_utils.xstr(total_usage))
        self.ui.lineEdit_remain.setText(string_utils.xstr(remain))

        self.ui.spinBox_quantity.setMaximum(remain)

        self.ui.comboBox_massager.setCurrentText(massage_referrer)
        self.ui.comboBox_treat_type.setCurrentText(self._get_treat_type())

    def _get_total_usage(self):
        total_usage = 0
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(row_no, 4)
            if item is None:
                continue

            usage = number_utils.get_integer(item.text())
            if usage > 0:
                total_usage += number_utils.get_integer(item.text())

        return total_usage

    def _get_wait_data(self):
        period = registration_utils.get_current_period(self.system_settings)
        doctor = self.ui.comboBox_doctor.currentText()

        invoice_no = self.ui.lineEdit_invoice_no.text()
        total_quantity = number_utils.get_integer(self.ui.lineEdit_total_quantity.text())
        remain = number_utils.get_integer(self.ui.lineEdit_remain.text())
        course = total_quantity - remain + 1
        room = string_utils.xstr(registration_utils.get_room(self.database, period, doctor))
        reg_no = registration_utils.get_reg_no(
            self.database, self.system_settings, room, doctor, period, None,
        )

        return period, doctor, invoice_no, course, room, reg_no

    def _save_course(self):
        period, doctor, invoice_no, course, room, reg_no = self._get_wait_data()

        massager = self.ui.comboBox_massager.currentText()
        nursing_assistant = self.ui.comboBox_nursing_assistant.currentText()

        if doctor == '' and massager == '' and nursing_assistant == '':
            system_utils.show_message_box(
                QMessageBox.Critical,
                '操作人員空白',
                '<font color="red"><h3>請輸入操作人員, 以利資料完整!</h3></font>',
                '請選擇操作人員.'
            )
            return

        invoice_no = self.ui.lineEdit_invoice_no.text()
        patient_key = self.ui.lineEdit_patient_key.text()
        name = self.ui.lineEdit_name.text()
        case_date = datetime.datetime.now()
        ins_type = '自費'
        treat_type = self.ui.comboBox_treat_type.currentText()

        fields = [
            'PatientKey', 'Name', 'CaseDate', 'Period', 'InsType', 'InvoiceNo',
            'Card', 'Continuance', 'Room', 'RegistNo',
            'TreatType', 'Doctor', 'MassageReferrer', 'NursingAssistant'
        ]
        data = [
            patient_key, name, case_date, period, ins_type, invoice_no,
            invoice_no, course, room, reg_no,
            treat_type, doctor, massager, nursing_assistant,
        ]

        case_key = self.database.insert_record('cases', fields, data)
        self._insert_prescript(case_key, case_date, treat_type)

        if doctor != '':
            self._insert_wait(case_key)

        self._set_group_box_booking(True)
        self.ui.lineEdit_query.setFocus()

    def _insert_wait(self, case_key):
        period, doctor, invoice_no, course, room, reg_no = self._get_wait_data()

        doctor_done = 'False'
        case_date = datetime.datetime.now()
        patient_key = self.ui.lineEdit_patient_key.text()
        name = self.ui.lineEdit_name.text()
        regist_type = '一般門診'
        treat_type = self.ui.comboBox_treat_type.currentText()
        ins_type = '自費'
        treat_type = self.ui.comboBox_treat_type.currentText()

        fields = [
            'CaseKey', 'CaseDate', 'Period', 'PatientKey', 'Name', 'RegistType',
            'TreatType', 'InsType', 'Card', 'Continuance',
            'Room', 'RegistNo', 'Doctor', 'DoctorDone',
        ]
        data = [
            case_key,
            case_date,
            period,
            patient_key,
            name,
            regist_type,
            treat_type,
            ins_type,
            invoice_no,
            course,
            room,
            reg_no,
            doctor,
            doctor_done,
        ]
        self.database.insert_record('wait', fields, data)

    def _insert_prescript(self, case_key, case_date, treat_type):
        invoice_no = self.ui.lineEdit_invoice_no.text()

        sql = f'''
            SELECT
                prescript.*
            FROM cases
                LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey
            WHERE
                InvoiceNo = "{invoice_no}" AND
                InsType = "自費" AND
                TreatType = "自購"
            ORDER BY cases.CaseDate
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        medicine_key = row['MedicineKey']
        medicine_type = string_utils.xstr(row['MedicineType'])
        medicine_name = f"{row['MedicineName']} ({treat_type})"
        dosage = self.ui.spinBox_quantity.value()
        introducer = self.ui.lineEdit_introducer.text()
        remark = None

        if introducer != '':
            remark = f'(介紹人: {introducer})'
        else:
            remark = '(無介紹人)'

        fields = [
            'PrescriptNo', 'CaseKey', 'CaseDate', 'MedicineSet',
            'MedicineKey', 'MedicineType', 'MedicineName', 'DosageMode', 'Dosage',
            'Unit', 'Price', 'Amount', 'Remark'
        ]
        data = [
            1, case_key, case_date, 2,
            medicine_key, medicine_type, medicine_name, '日劑量', dosage,
            '次', 0, 0,
            remark,
        ]
        self.database.insert_record('prescript', fields, data)

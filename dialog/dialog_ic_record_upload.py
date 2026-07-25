
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime

from libs import date_utils, nhi_utils, system_utils, ui_utils
from PyQt5 import QtWidgets


# 主視窗
class DialogICRecordUpload(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogICRecordUpload, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_IC_RECORD_UPLOAD, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        default_date = date_utils.get_default_date(self.system_settings)
        self.ui.dateEdit_start_date.setDate(default_date)
        self.ui.dateEdit_end_date.setDate(default_date)

        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        if self.call_from in ['statistics_correction_reg']:
            self.ui.groupBox_upload_type.setVisible(False)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.dateEdit_start_date.dateChanged.connect(self._set_end_date)

    def _set_end_date(self):
        pass
        # self.ui.dateEdit_end_date.setDate(self.ui.dateEdit_start_date.date())

    # 設定comboBox
    def _set_combo_box(self):
        script = 'select * from person where Position IN ("醫師", "支援醫師")'
        rows = self.database.select_record(script)
        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, '全部')
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list, '全部')

    # 設定 mysql script
    def get_sql(self):
        if self.call_from == 'statistics_correction_reg':
            sql = self._get_correction_reg_sql()
        else:
            sql = self._get_upload_sql()

        return sql

    '''
            ExtractValue(Security, "//registered_date") AS RegisteredDate,
            ExtractValue(Security, "//sam_id") AS SAMID,
            ExtractValue(Security, "//clinic_id") AS ClinicID,
            ExtractValue(Security, "//upload_type") AS UploadType,
            ExtractValue(Security, "//treat_after_check") AS TreatAfterCheck,
            ExtractValue(Security, "//security_signature") AS SecuritySignature,
    '''
    def _get_upload_sql(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        patient_condition = ''
        patient_key = self.ui.lineEdit_patient_key.text()
        if patient_key != '':
            patient_condition = f'AND cases.PatientKey = {patient_key}'

        period_condition = ''
        period = self.ui.comboBox_period.currentText()
        if period != '全部':
            period_condition = f' AND Period = "{period}"'

        doctor_condition = ''
        doctor = self.ui.comboBox_doctor.currentText()
        if doctor != '全部':
            doctor_condition = f' AND Doctor = "{doctor}"'

        join_case_extend = ''
        case_extend_condition = ''

        if self.ui.radioButton_correct.isChecked():
            upload_condition = 'AND (ExtractValue(Security, "//upload_time") != "")'
            ins_type_condition = ''
        elif self.ui.radioButton_correct_updated.isChecked():
            upload_condition = 'AND (ExtractValue(Security, "//upload_time") != "")'

            join_case_extend = 'LEFT JOIN caseextend ON caseextend.CaseKey = cases.CaseKey'
            case_extend_condition = 'AND ExtendType = "IC已上傳資料修正"'
            ins_type_condition = ''
        else:
            upload_condition = 'AND (ExtractValue(Security, "//upload_time") = "")'
            ins_type_condition = '(cases.InsType = "健保") AND'

        script = f'''
            SELECT
                *, DATE_FORMAT(CaseDate, "%Y-%m-%d %H:%i") AS CaseDate,
                cases.InsType as CaseInsType,
                patient.Gender, patient.Birthday
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                {join_case_extend}
            WHERE
                ((CaseDate BETWEEN "{start_date}" AND "{end_date}") OR
                 (ExtractValue(Security, "//registered_date") BETWEEN "{start_date}" AND "{end_date}")) AND
                {ins_type_condition}
                (cases.ApplyType != '不申報') AND
                (Card NOT IN ("欠卡", "XX1") AND Card IS NOT NULL)
                {patient_condition}
                {period_condition}
                {doctor_condition}
                {upload_condition}
                {case_extend_condition}
                GROUP BY cases.CaseKey
                ORDER BY CaseDate, cases.Room, cases.RegistNo
        '''

        return script

    def _get_correction_reg_sql(self):
        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        period_condition = ''
        period = self.ui.comboBox_period.currentText()
        if period != '全部':
            period_condition = f' AND Period = "{period}"'

        doctor_condition = ''
        doctor = self.ui.comboBox_doctor.currentText()
        if doctor != '全部':
            doctor_condition = f' AND Doctor = "{doctor}"'

        script = f'''
            SELECT
                *, DATE_FORMAT(CaseDate, "%Y-%m-%d %H:%i") AS CaseDate,
                cases.InsType as CaseInsType,
                patient.Gender, patient.Birthday
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                ((CaseDate BETWEEN "{start_date}" AND "{end_date}") OR
                 (ExtractValue(Security, "//registered_date") BETWEEN "{start_date}" AND "{end_date}")) AND
                (cases.InsType = "健保") AND
                (RegistType = "矯正機關內門診") AND
                (cases.ApplyType != '不申報') AND
                (Card NOT IN ("欠卡") AND Card IS NOT NULL)
                {period_condition}
                {doctor_condition}
                ORDER BY CaseDate, cases.Room, cases.RegistNo
        '''

        return script

    def accepted_button_clicked(self):
        pass

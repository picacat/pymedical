
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import class_utils

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils


# 經驗方 2021.03.22
class DialogMedicalRecordExperience(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordExperience, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_date = args[2]
        self.medicine_set = args[3]

        self.ui = None

        self._set_ui()
        self._set_signal()
        try:
            self._read_experience()
        except Exception:
            pass

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_EXPERIENCE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_experience = class_utils.get_table_widget(
            self.ui.tableWidget_experience, self.database
        )
        self.table_widget_experience.set_column_hidden([0])
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 600]
        self.table_widget_experience.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_experience.itemSelectionChanged.connect(self._experience_changed)
        self.ui.pushButton_query.clicked.connect(self._query_experience)
        self.ui.pushButton_query_all.clicked.connect(self._query_experience_all)

    def accepted_button_clicked(self):
        case_utils.copy_experience(
            self.database, self.parent, self.case_date, self.row,
            self.medicine_set,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_disease.isChecked(),
            self.ui.checkBox_prescript.isChecked(),
        )

    def _query_experience(self):
        self._read_experience(self.ui.lineEdit_keyword.text())

    def _query_experience_all(self):
        self._read_experience()

        self.ui.lineEdit_keyword.setText(None)
        self.ui.lineEdit_keyword.setFocus()

    def _read_experience(self, keyword=None):
        condition = ''

        if keyword is not None:
            condition = f''' AND
                (ExpName LIKE "%{keyword}%" OR
                 ExpSymptom LIKE "%{keyword}%")
            '''

        sql = f'''
            SELECT * FROM experience
            WHERE
                (ExpName IS NOT NULL OR ExpSymptom IS NOT NULL)
                {condition}
            ORDER BY ExperienceKey
        '''
        self.table_widget_experience.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        exp_name = string_utils.xstr(row['ExpName'])
        if exp_name == '':
            exp_name = string_utils.xstr(row['ExpSymptom'])

        experience_record = [
            string_utils.xstr(row['ExperienceKey']),
            exp_name,
        ]

        for column in range(len(experience_record)):
            self.ui.tableWidget_experience.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(experience_record[column])
            )

    def _experience_changed(self):
        experience_key = self.table_widget_experience.field_value(0)
        if experience_key is None:
            return

        sql = f'''
            SELECT * FROM experience
            WHERE
                ExperienceKey = {experience_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.row = rows[0]
        self._set_experience_html(self.row)

    def _set_experience_html(self, row):
        medical_record = ''
        symptom = string_utils.get_str(row['ExpSymptom'], 'utf8')
        tongue = string_utils.get_str(row['ExpTongue'], 'utf8')
        pulse = string_utils.get_str(row['ExpPulse'], 'utf8')
        distincts = string_utils.xstr(row['ExpDistincts'])
        cure = string_utils.xstr(row['ExpCure'])

        if symptom != '':
            medical_record += f'<b>說明</b>: {symptom}<hr>'
        if tongue != '':
            medical_record += f'<b>舌診</b>: {tongue}<hr>'
        if pulse != '':
            medical_record += f'<b>脈象</b>: {pulse}<hr>'
        if distincts != '':
            medical_record += f'<b>辨證</b>: {distincts}<hr>'
        if cure != '':
            medical_record += f'<b>治則</b>: {cure}<hr>'

        icd_code = string_utils.xstr(row['ExpICDCode'])
        if icd_code != '':
            icd10_code, icd10_name = case_utils.convert_icd9_to_icd10(self.database, icd_code)
            if icd10_name is not None:
                medical_record += f'<b>主診斷</b>: {icd10_code} {icd10_name}<br>'

        medical_record = f'''
            <div style="width: 95%;">
                {medical_record}
            </div>
        '''

        prescript_record = self._get_prescript_record(row, row['ExperienceKey'])
        remark_record = self._get_remark_record(row['ExperienceKey'])

        html = f'''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {medical_record}
                    {prescript_record}
                    {remark_record}
                </body>
            </html>
        '''
        self.ui.textEdit_experience.setHtml(html)

    def _get_prescript_record(self, experience_row, experience_key):
        sql = f'''
            SELECT * FROM expprescript
            WHERE
                ExperienceKey = {experience_key}
            ORDER BY ExpPrescriptKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        prescript_data = ''
        sequence = 0
        for row in rows:
            if string_utils.xstr(row['MedicineName']) == '':
                continue

            sequence += 1
            medicine_name = string_utils.xstr(row['MedicineName'])
            dosage = number_utils.get_float(row['Dosage'])

            if dosage is None or dosage == 0.00:
                dosage_str = ''
            else:
                dosage_str = f'{dosage:.1f}'

            unit = string_utils.xstr(row['Unit'])
            instruction = string_utils.xstr(row['Instruction'])

            prescript_data += f'''
                <tr>
                    <td align="center" style="padding-right: 8px;">{sequence}</td>
                    <td style="padding-left: 8px">{medicine_name}</td>
                    <td align="right" style="padding-right: 8px">{dosage_str} {unit}</td>
                    <td style="padding-left: 8px">{instruction}</td>
                </tr>
            '''

        prescript_data += self._get_dosage_record(experience_row)
        prescript_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                        <th style="padding-left: 8px" width="50%" align="left">處方名稱</th>
                        <th style="padding-right: 8px" align="right" width="15%">劑量</th>
                        <th style="padding-left: 8px" align="left" width="25%">指示</th>
                    </tr>
                </thead>
                <tbody>
                    {prescript_data}
                </tbody>
            </table>
            <br>
        '''

        return prescript_html

    @staticmethod
    def _get_dosage_record(row):
        dosage_data = ''

        pres_days = number_utils.get_integer(row['ExpPresDays'])
        packages = number_utils.get_integer(row['ExpPackage'])

        if packages > 0 or pres_days > 0:
            instruction = string_utils.xstr(row['ExpInstruction'])
            dosage_data = f'''
                <tr>
                    <td style="text-align: left; padding-left: 30px;" colspan="4">
                        用法: {packages}包 {pres_days}日份 {instruction}服用
                    </td>
                </tr>
            '''

        return dosage_data

    def _get_remark_record(self, experience_key):
        sql = f'''
            SELECT * FROM expremark
            WHERE
                ExperienceKey = {experience_key}
            ORDER BY ExpRemarkKey
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        row = rows[0]
        remark = string_utils.get_str(row['Remark'], 'utf8')
        if remark != '':
            remark = f'<b>備註</b>: {remark}<hr>'

        remark_record = f'''
            <div style="width: 95%;">
                {remark}
            </div>
        '''
        return remark_record

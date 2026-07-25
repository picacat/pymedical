
# 參考病歷視窗 2020.11.13
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils


# 參考處方 2023-09-17 陳怡年
class DialogReferencePrescript(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReferencePrescript, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.icd_code = args[2]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_reference()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_REFERENCE_PRESCRIPT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('拷貝病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_reference_list = class_utils.get_table_widget(
            self.ui.tableWidget_reference_list, self.database
        )
        self.table_widget_reference_list.set_column_hidden([0])
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 100, 280, 100]
        self.table_widget_reference_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_reference_list.itemSelectionChanged.connect(self._reference_list_changed)

    def accepted_button_clicked(self):
        reference_key = self.table_widget_reference_list.field_value(0)

        case_utils.copy_reference_prescript(
            self.database, self.system_settings, self.parent, reference_key,
            self.ui.checkBox_diagnostic.isChecked(),
            self.ui.checkBox_prescript.isChecked(),
        )

    def _read_reference(self):
        icd_condition = ''
        if self.icd_code not in ['', None]:
            icd_condition = f' AND (ICD10Code LIKE "{self.icd_code[:3]}%") '

        sql = f'''
            SELECT * FROM reference
            WHERE
                RefSetName IS NOT NULL AND ICD10Code IS NOT NULL
                {icd_condition}
            ORDER BY ICD10Code, RefSet
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.table_widget_reference_list.set_db_data(sql, self._set_reference_list_data)
        self._read_reference_prescript()

    def _set_reference_list_data(self, row_no, row):
        reference_key = string_utils.xstr(row['ReferenceKey'])
        reference_set = string_utils.xstr(row['RefSet'])
        reference_set_name = string_utils.xstr(row['RefSetName'])
        disease_code = string_utils.xstr(row['ICD10Code'])

        reference_prescript_data = [
            reference_key,
            reference_set,
            reference_set_name,
            disease_code,
        ]

        for col_no in range(len(reference_prescript_data)):
            self.ui.tableWidget_reference_list.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(reference_prescript_data[col_no])
            )

    def _reference_list_changed(self):
        self._read_reference_prescript()

    def _read_reference_prescript(self):
        reference_key = self.table_widget_reference_list.field_value(0)
        sql = f'''
            SELECT * FROM reference
            WHERE
                ReferenceKey = {reference_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        symptom = string_utils.get_str(row['RefSymptom'], 'utf8')
        tongue = string_utils.get_str(row['RefTongue'], 'utf8')
        pulse = string_utils.get_str(row['RefPulse'], 'utf8')

        medical_record = ''
        if symptom != '':
            medical_record += f'<b>主訴</b>: {symptom}<hr>'
        if tongue != '':
            medical_record += f'<b>舌診</b>: {tongue}<hr>'
        if pulse != '':
            medical_record += f'<b>脈象</b>: {pulse}<hr>'

        medical_record = f'''
            <div style="width: 95%;">
                {medical_record}
            </div>
        '''

        prescript_record = self._get_prescript_record(reference_key)

        html = f'''
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {medical_record}
                    {prescript_record}
                </body>
            </html>
        '''

        self.ui.textEdit_medical_record.setHtml(html)

    def _get_prescript_record(self, reference_key):
        sql = f'''
            SELECT * FROM refprescript
            WHERE
                ReferenceKey = {reference_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return '<br><br><br><center>未設定處方</center><br>'

        prescript_data = ''
        sequence = 0
        for row in rows:
            medicine_key = row['MedicineKey']
            if medicine_key is None:
                continue

            sql = f'''
                SELECT * FROM medicine
                WHERE
                    MedicineKey = {medicine_key}
            '''
            medicine_rows = self.database.select_record(sql)
            if len(medicine_rows) <= 0:
                continue

            medicine_row = medicine_rows[0]

            sequence += 1
            dosage = number_utils.get_float(row['Quantity'])
            if dosage is None or dosage == 0.00:
                dosage_str = ''
            else:
                if self.system_settings.field('劑量模式') in ['日劑量', '總量']:
                    dosage_str = f'{dosage:.1f}'
                elif self.system_settings.field('劑量模式') in ['次劑量']:
                    dosage_str = f'{dosage:.2f}'
                else:
                    dosage_str = string_utils.xstr(dosage)

            unit = string_utils.xstr(medicine_row['Unit'])
            medicine_name = string_utils.xstr(medicine_row['MedicineName'])
            prescript_data += f'''
                <tr>
                    <td align="center" style="padding-right: 8px;">{sequence}</td>
                    <td style="padding-left: 8px;">{medicine_name}</td>
                    <td align="right" style="padding-right: 8px;">{dosage_str} {unit}</td>
                </tr>
            '''

        prescript_html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
            style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding-left: 8px" width="10%">序</th>
                        <th style="padding-left: 8px" align="left">處方名稱</th>
                        <th style="padding-right: 8px" align="right" width="25%">劑量</th>
                    </tr>
                </thead>
                <tbody>
                    {prescript_data}
                </tbody>
            </table>
            <br>
        '''

        return prescript_html

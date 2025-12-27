
# 參考病歷視窗 2020.11.13
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox
import json

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import dialog_utils
from libs import case_utils


# 參考病歷視窗
class DialogMedicalRecordReference(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordReference, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.copy_medical_record = True

        self._set_ui()
        self._set_signal()
        self._read_medical_record_reference()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_REFERENCE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.setFixedSize(self.size())  # non resizable dialog
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('拷貝病歷')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')
        self.table_widget_reference_list = class_utils.get_table_widget(
            self.ui.tableWidget_reference_list, self.database
        )
        self.table_widget_reference_symptom = class_utils.get_table_widget(
            self.ui.tableWidget_reference_symptom, self.database
        )
        self.table_widget_reference_symptom.set_column_hidden([0, 1, 2, 3, 4, 5])
        self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 220, 100]
        self.table_widget_reference_list.set_table_heading_width(width)
        width = [100, 100, 100, 100, 100, 100, 480]
        self.table_widget_reference_symptom.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_reference_list.itemSelectionChanged.connect(self._reference_list_changed)
        self.ui.tableWidget_reference_symptom.itemSelectionChanged.connect(self._reference_symptom_changed)
        self.ui.tableWidget_reference_symptom.doubleClicked.connect(self._copy_medical_record_reference)
        self.ui.toolButton_edit_reference.clicked.connect(self._edit_reference_medical_record)
        self.ui.lineEdit_disease_name.textChanged.connect(self._disease_name_changed)
        self.ui.toolButton_cancel_reference.clicked.connect(self._cancel_reference)
        self.ui.radioButton_medical_record.clicked.connect(lambda: self._read_medical_record_reference())
        self.ui.radioButton_custom.clicked.connect(self._read_custom_record_reference)

    def _copy_medical_record_reference(self):
        self.copy_medical_record = True
        self.accepted_button_clicked()
        self.close()

    def accepted_button_clicked(self):
        if not self.copy_medical_record:
            return

        if self.ui.radioButton_ins_prescript.isChecked():
            copy_ins_prescript_to = '健保處方'
        else:
            copy_ins_prescript_to = '自費處方'

        if self.ui.radioButton_medical_record.isChecked():
            case_key = self.table_widget_reference_symptom.field_value(0)
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
        else:
            extension_json_key = self.table_widget_reference_symptom.field_value(0)
            case_utils.copy_medical_record_json(
                self.database, self.system_settings, self.parent, extension_json_key,
                self.ui.checkBox_diagnostic.isChecked(),
                self.ui.checkBox_remark.isChecked(),
                self.ui.checkBox_disease.isChecked(),
                self.ui.checkBox_ins_prescript.isChecked(),
                copy_ins_prescript_to,
                self.ui.checkBox_ins_treat.isChecked(),
                self.ui.checkBox_self_prescript.isChecked(),
                self.ui.checkBox_not_overwrite.isChecked(),
            )

    def _disease_name_changed(self):
        disease_name = self.ui.lineEdit_disease_name.text()
        self._read_medical_record_reference(disease_name.strip())
        self.ui.lineEdit_disease_name.setFocus(True)
        self.ui.lineEdit_disease_name.setCursorPosition(len(disease_name))

    def _read_medical_record_reference(self, disease_name=''):
        if disease_name is None:
            return

        if disease_name != '':
            disease_name_script = f'''
                AND (
                    DiseaseCode1 LIKE "{disease_name}%" OR
                    DiseaseName1 LIKE "%{disease_name}%"
                )
            '''
        else:
            disease_name_script = ''

        # if self.case_key is not None:
        #     case_key_condition = f'CaseKey != {self.case_key} AND '
        # else:
        #     case_key_condition = ''

        sql = f'''
            SELECT
                DiseaseCode1, DiseaseName1, SpecialCode FROM cases
            WHERE
                DiseaseName1 IS NOT NULL AND
                cases.Reference = "True"
                {disease_name_script}
            GROUP BY DiseaseCode1
            ORDER BY DiseaseCode1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.table_widget_reference_list.set_db_data(sql, self._set_reference_list_data)
        self._read_symptom_by_medical_record()

    def _set_reference_list_data(self, row_no, row):
        disease_code = string_utils.xstr(row['DiseaseCode1'])

        color = None
        disease_type = None
        if disease_code in self.parent.parent.moderate_complicated_acupuncture_list:
            color = QtGui.QColor('darkGreen')
            disease_type = '中度複針'
        elif disease_code in self.parent.parent.highly_complicated_acupuncture_list:
            color = QtGui.QColor('darkMagenta')
            disease_type = '高度複針'
        elif disease_code in self.parent.parent.moderate_complicated_massage_list:
            color = QtGui.QColor('blue')
            disease_type = '中度複傷'
        elif disease_code in self.parent.parent.highly_complicated_massage_list:
            color = QtGui.QColor('magenta')
            disease_type = '高度複傷'
        elif string_utils.xstr(row['SpecialCode']).strip() != '':
            color = QtGui.QColor('red')
            disease_type = '慢性病'

        medical_record_data = [
            disease_code,
            string_utils.xstr(row['DiseaseName1']),
            disease_type,
        ]

        for col_no in range(len(medical_record_data)):
            self.ui.tableWidget_reference_list.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record_data[col_no])
            )
            if color is not None:
                self.ui.tableWidget_reference_list.item(row_no, col_no).setForeground(color)

    def _reference_list_changed(self):
        if self.ui.radioButton_medical_record.isChecked():
            self._read_symptom_by_medical_record()
        else:
            self._read_symptom_by_custom()

    def _read_symptom_by_medical_record(self):
        disease_code1 = self.table_widget_reference_list.field_value(0)

        sql = f'''
            SELECT
                cases.CaseKey, cases.CaseDate, cases.PatientKey,
                cases.Name, cases.InsType, cases.Symptom,
                patient.Gender, patient.Birthday
            FROM cases
            LEFT JOIN patient
                ON patient.PatientKey = cases.PatientKey
            WHERE
                DiseaseCode1 = "{disease_code1}" AND
                cases.Reference = "True"
            ORDER BY cases.PatientKey, CaseDate
        '''
        self.table_widget_reference_symptom.set_db_data(sql, self._set_reference_symptom_data)
        self._show_reference_medical_record()
        self.ui.tableWidget_reference_list.setFocus()

    def _read_symptom_by_custom(self):
        disease_code1 = self.table_widget_reference_list.field_value(0)

        sql = f'''
            SELECT * FROM extension_json
            WHERE
                TableName = "reference_medical_record" AND
                KeyField = "disease_code" AND
                KeyValue = "{disease_code1}"
            ORDER BY ExtensionJSONKey
        '''
        rows = self.database.select_record(sql)
        self._set_reference_symptom_custom_data(rows)

        self.ui.tableWidget_reference_symptom.setCurrentCell(0, 0)
        self._show_reference_custom_medical_record()
        self.ui.tableWidget_reference_list.setFocus()

    def _set_reference_symptom_custom_data(self, rows):
        self.ui.tableWidget_reference_symptom.setRowCount(0)

        for row_no, row in enumerate(rows):
            self._set_reference_symptom_custom_data_detail(row_no, row)

        self.ui.tableWidget_reference_symptom.resizeRowsToContents()

    def _set_reference_symptom_custom_data_detail(self, row_no, row):
        self.ui.tableWidget_reference_symptom.setRowCount(self.ui.tableWidget_reference_symptom.rowCount()+1)
        medical_record = json.loads(row['JSON'])['diagnostic']

        case_date = string_utils.xstr(row['TimeStamp'].date())
        patient_key = '0'
        name = '自訂參考病歷'
        symptom = string_utils.get_str(medical_record['symptom'], 'utf8')
        medical_record_summary = f'日期: {case_date} 病歷號: {patient_key} 姓名: {name}\n{symptom} '
        medical_record_symptom = [
            string_utils.xstr(row['ExtensionJSONKey']),
            None, None, None, None, None,
            medical_record_summary,
        ]

        for column in range(len(medical_record_symptom)):
            self.ui.tableWidget_reference_symptom.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record_symptom[column])
            )

    def _set_reference_symptom_data(self, row_no, row):
        case_date = string_utils.xstr(row['CaseDate'].date())
        patient_key = string_utils.xstr(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        symptom = string_utils.get_str(row['Symptom'], 'utf8')
        medical_record_summary = f'日期: {case_date} 病歷號: {patient_key} 姓名: {name}\n{symptom} '
        medical_record_symptom = [
            string_utils.xstr(row['CaseKey']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['InsType']),
            medical_record_summary,
        ]

        for column in range(len(medical_record_symptom)):
            self.ui.tableWidget_reference_symptom.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record_symptom[column])
            )

    def _reference_symptom_changed(self):
        if self.ui.radioButton_medical_record.isChecked():
            self._show_reference_medical_record()
        else:
            self._show_reference_custom_medical_record()

    def _show_reference_medical_record(self):
        case_key = self.table_widget_reference_symptom.field_value(0)
        if case_key in [None, '']:
            return

        patient_key = self.table_widget_reference_symptom.field_value(1)
        name = self.table_widget_reference_symptom.field_value(2)
        gender = self.table_widget_reference_symptom.field_value(3)
        birthday = self.table_widget_reference_symptom.field_value(4)

        self._set_copy_prescript_check_box()
        html = case_utils.get_medical_record_html(self.database, self.system_settings, case_key)
        self.ui.textEdit_medical_record.setHtml(html)

        self.ui.groupBox_medical_record.setTitle(
            f'病歷號: {patient_key} {name}({gender}) 出生日期: {birthday}  病歷內容'
        )

    def _show_reference_custom_medical_record(self):
        self.ui.groupBox_medical_record.setTitle('病歷號: 0 自訂參考病歷  病歷內容')

        extension_json_key = self.table_widget_reference_symptom.field_value(0)
        if extension_json_key in [None, '']:
            return

        html = case_utils.get_medical_record_json_html(self.database, self.system_settings, extension_json_key)

        self.ui.textEdit_medical_record.setHtml(html)

    def _set_copy_prescript_check_box(self):
        case_key = self.table_widget_reference_symptom.field_value(0)
        if case_key in [None, '']:
            return

        ins_type = self.table_widget_reference_symptom.field_value(5)

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
                    MedicineSet = 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                self.ui.checkBox_ins_prescript.setEnabled(True)
                self.ui.radioButton_ins_prescript.setEnabled(True)
                self.ui.radioButton_self_prescript.setEnabled(True)
                if treatment == '' or self.system_settings.field('預設拷貝健保針傷科處方用藥') == 'Y':
                    self.ui.checkBox_ins_prescript.setChecked(True)  # 預設非療程才拷貝藥品

        sql = f'''
            SELECT MedicineSet FROM prescript
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

    def _edit_reference_medical_record(self):
        if self.ui.radioButton_medical_record.isChecked():
            self._edit_past_history()
        else:
            self._edit_custom_reference_medical_record()

    def _edit_past_history(self):
        case_key = self.table_widget_reference_symptom.field_value(0)
        self.parent.parent.open_medical_record(case_key, '過去病歷')
        self.copy_medical_record = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def _edit_custom_reference_medical_record(self):
        extension_json_key = self.table_widget_reference_symptom.field_value(0)
        self.parent.parent.open_medical_record(extension_json_key, '自訂參考病歷')
        self.copy_medical_record = False

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).animateClick()

    def _cancel_reference(self):
        name = self.table_widget_reference_symptom.field_value(2)
        msg_box = dialog_utils.get_message_box(
            '解除參考病歷', QMessageBox.Warning,
            f'<font size="5" color="red"><b>確定解除{name}的參考病歷?</b></font>',
            '提示！參考病歷解除後, 病歷並不會被刪除!'
        )

        cancel_reference = msg_box.exec_()
        if not cancel_reference:
            return

        case_key = self.table_widget_reference_symptom.field_value(0)

        self.database.exec_sql(f'''
            UPDATE cases
            SET
                Reference = "False"
            WHERE
                CaseKey = {case_key}
        ''')

        row_no = self.ui.tableWidget_reference_symptom.currentRow()
        self.ui.tableWidget_reference_symptom.removeRow(row_no)

    def _read_custom_record_reference(self):
        self.ui.tableWidget_reference_list.setRowCount(0)

        sql = '''
            SELECT
                extension_json.KeyValue AS DiseaseCode1,
                icd10.ChineseName AS DiseaseName1, icd10.SpecialCode
            FROM extension_json
                LEFT JOIN icd10 ON icd10.ICDCode = extension_json.KeyValue
            WHERE
                TableName = "reference_medical_record" AND
                KeyField = "disease_code"
            GROUP BY KeyValue
            ORDER BY KeyValue
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self.table_widget_reference_list.set_db_data(sql, self._set_reference_list_data)


# -*- coding: UTF-8 -*-
import datetime

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import json

from libs import class_utils

from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import case_utils


# 匯入病歷資料 2019.09.29
class DialogImportMedicalRecord(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogImportMedicalRecord, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None

        self._set_ui()
        self._set_signal()
        self._open_file_dialog()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_IMPORT_MEDICAL_RECORD, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯入資料庫')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_medical_record.itemSelectionChanged.connect(self._item_selection_changed)
        self.ui.tableWidget_medical_record.horizontalHeader().sectionClicked.connect(self._header_clicked)

    def accepted_button_clicked(self):
        self._import_to_database()

        self.close()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 20, 180, 90, 50, 90, 70, 50, 200, 50, 90]
        self.table_widget_medical_record.set_table_heading_width(width)

    def _open_file_dialog(self):
        options = QFileDialog.Options()

        file_name, _ = QFileDialog.getOpenFileName(
            self, "開啟病歷JSON檔",
            '*.json', "json 檔 (*.json);;", options=options
        )
        if not file_name:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()
            return

        self._read_medical_record_json(file_name)

    def _read_medical_record_json(self, file_name):
        with open(file_name, encoding='utf8') as json_file:
            rows = json.load(json_file)
            for row_no, row in enumerate(rows):
                self._set_medical_record(row_no, row)

    def _set_medical_record(self, row_no, row):
        self.ui.tableWidget_medical_record.insertRow(row_no)

        medical_record_row = [
            string_utils.xstr(row),
            None,
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(row['DiseaseName1']),
            None,
            string_utils.xstr(row['Doctor']),
        ]

        for col_no in range(len(medical_record_row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record_row[col_no])

            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no, item
            )
            if col_no in [9]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [4, 7]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        check_box = QtWidgets.QCheckBox(self.ui.tableWidget_medical_record)
        check_box.setChecked(True)
        self.ui.tableWidget_medical_record.setCellWidget(row_no, 1, check_box)

    def _item_selection_changed(self):
        row_no = self.ui.tableWidget_medical_record.currentRow()
        item = self.ui.tableWidget_medical_record.item(row_no, 0)
        if item is None:
            return

        row = eval(item.text())
        html = case_utils.get_medical_record_row_html(row)
        self.ui.textEdit_medical_record.setHtml(html)

    def _delete_prescript(self, case_key):
        sql = f'''
            SELECT PrescriptKey FROM prescript
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            prescript_key = row['PrescriptKey']
            self.database.delete_record('prescript', 'PrescriptKey', prescript_key)
            self.database.delete_record('presextend', 'PrescriptKey', prescript_key)

    def _delete_record(self, case_date, patient_key):
        start_date = f'{case_date[:10]} 00:00:00'
        end_date = f'{case_date[:10]} 23:59:59'
        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key} AND
                InsType = "健保"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        case_key = rows[0]['CaseKey']

        # self.database.delete_record('cases', 'CaseKey', case_key)
        self.database.delete_record('dosage', 'CaseKey', case_key)
        self._delete_prescript(case_key)

    def _check_deposit(self, case_key, case_date, period, patient_key):
        start_date = f'{case_date[:10]} 00:00:00'
        end_date = f'{case_date[:10]} 23:59:59'
        sql = f'''
            SELECT * FROM deposit
            WHERE
                DepositDate BETWEEN "{start_date}" AND "{end_date}" AND
                ReturnDate IS NULL AND
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        deposit_key = row['DepositKey']
        return_date = datetime.datetime.now()
        sql = f'''
            UPDATE deposit
            SET
                CaseKey = {case_key},
                ReturnDate = "{return_date}",
                Period = "{period}",
                Fee = 0,
                Refunder = "{self.system_settings.field('使用者')}"
            WHERE
                DepositKey = {deposit_key}
        '''
        self.database.exec_sql(sql)

    def _import_to_database(self):
        row_count = self.ui.tableWidget_medical_record.rowCount()
        progress_dialog = QtWidgets.QProgressDialog(
            '正在匯入資料庫中, 請稍後...', '取消', 0, row_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no in range(row_count):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, 1)
            if not check_box.isChecked():
                continue

            item = self.ui.tableWidget_medical_record.item(row_no, 0)
            if item is None:
                return

            medical_row = eval(item.text())
            case_date = medical_row['CaseDate']
            period = medical_row['Period']
            ins_type = medical_row['InsType']
            card = string_utils.xstr(medical_row['Card'])

            patient_row = medical_row['PatientJSON']
            del medical_row['PatientJSON']
            patient_key = self._write_patient(patient_row)

            medical_row['PatientKey'] = patient_key

            if self.ui.checkBox_overwrite.isChecked() and patient_key is not None and ins_type == '健保':
                self._delete_record(case_date, patient_key)

            treat_row = medical_row['TreatJSON']
            dosage_row = medical_row['DosageJSON']
            prescript_row = medical_row['PrescriptJSON']

            self._remove_medical_row_field(medical_row)

            fields = list(medical_row.keys())
            data = list(medical_row.values())

            # case_key = self.database.insert_record('cases', fields, data)
            sql = f'''
                SELECT CaseKey FROM cases
                WHERE
                    CaseDate = "{case_date}" AND
                    InsType = "{ins_type}" AND
                    PatientKey = {patient_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                case_key = rows[0]['CaseKey']
                self.database.update_record('cases', fields, 'CaseKey', case_key, data)
            else:
                case_key = self.database.insert_record('cases', fields, data)

            self._write_pres_extend(treat_row, case_key)
            self._write_dosage(dosage_row, case_key)
            self._write_prescript(prescript_row, case_key)

            if card != '欠卡' and patient_key is not None:  # 檢查是否需要還卡
                self._check_deposit(case_key, case_date, period, patient_key)

        progress_dialog.setValue(row_count)
        system_utils.show_message_box(
            QMessageBox.Information,
            'JSON資料匯入完成',
            '<h3>病歷資料匯入完成.</h3>',
            '資料正確無誤'
        )

    @staticmethod
    def _remove_medical_row_field(medical_row):
        del medical_row['TreatJSON']
        del medical_row['DosageJSON']
        del medical_row['PrescriptJSON']

        del medical_row['CaseKey']
        del medical_row['TimeStamp']
        medical_row.pop('RegistTypex', None)
        medical_row.pop('Casher', None)
        medical_row.pop('Height', None)
        medical_row.pop('HeartBeat', None)
        for i in range(4, 7):
            medical_row.pop(f'Package{i}', None)
            medical_row.pop(f'PresDays{i}', None)
            medical_row.pop(f'Instruction{i}', None)

        medical_row.pop('SelfTreatment', None)
        medical_row.pop('Acupuncture1', None)
        medical_row.pop('Acupuncture2', None)
        medical_row.pop('EAcupuncture1', None)
        medical_row.pop('EAcupuncture2', None)
        medical_row.pop('Massage1', None)
        medical_row.pop('Massage2', None)
        medical_row.pop('Dislocate1', None)
        medical_row.pop('Dislocate2', None)
        medical_row.pop('ReceiptShare', None)
        medical_row.pop('SMiscFee', None)
        medical_row.pop('TreatShare', None)
        medical_row.pop('DrugShare', None)
        medical_row.pop('Refund', None)
        medical_row.pop('SMaterial', None)
        medical_row.pop('Debt', None)
        medical_row.pop('Cert', None)

    def _write_patient(self, patient_row):
        if len(patient_row) <= 0:
            return 0

        row = patient_row[0]
        name = string_utils.xstr(row['Name'])
        patient_id = string_utils.xstr(row['ID'])
        birthday = row['Birthday']
        if patient_id != '':
            sql = f'''
                SELECT PatientKey FROM patient
                WHERE
                    Name = "{name}" AND
                    ID = "{patient_id}"
            '''
        elif birthday != '':
            sql = f'''
                SELECT PatientKey FROM patient
                WHERE
                    Name = "{name}" AND
                    DATE(Birthday) = "{birthday}"
            '''
        else:
            sql = f'''
                SELECT PatientKey FROM patient
                WHERE
                    Name = "{name}"
            '''

        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return rows[0]['PatientKey']

        del row['PatientKey']
        row.pop('Sex', None)
        row.pop('Alergy', None)
        del row['TimeStamp']
        fields = list(row.keys())
        data = list(row.values())

        patient_key = self.database.insert_record('patient', fields, data)

        return patient_key

    def _write_pres_extend(self, treat_row, prescript_key):
        if treat_row is None or len(treat_row) <= 0:
            return

        row = treat_row[0]
        del row['PresExtendKey']
        row['PrescriptKey'] = prescript_key
        fields = list(row.keys())
        data = list(row.values())
        self.database.insert_record('presextend', fields, data)

    def _write_dosage(self, dosage_row, case_key):
        for row in dosage_row:
            del row['DosageKey']

            try:
                del row['SinglePriceMedicine']
                del row['SinglePrice']
            except Exception:
                pass

            del row['TimeStamp']
            row['CaseKey'] = case_key
            fields = list(row.keys())
            data = list(row.values())
            self.database.insert_record('dosage', fields, data)

    def _write_prescript(self, prescript_row, case_key):
        for row in prescript_row:
            pres_extend_row = row['PresExtendJSON']
            del row['PrescriptKey']
            del row['TimeStamp']
            del row['PresExtendJSON']
            row.pop('Charged', None)

            row['CaseKey'] = case_key
            fields = list(row.keys())
            data = list(row.values())
            prescript_key = self.database.insert_record('prescript', fields, data)
            self._write_pres_extend(pres_extend_row, prescript_key)

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_medical_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_medical_record.cellWidget(row_no, col_no)
            check_box.setChecked(not check_box.isChecked())

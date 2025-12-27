
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

from libs import class_utils
from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils
from libs import number_utils
from libs import export_utils


# 主視窗
class DialogPatientMedicalRecord(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogPatientMedicalRecord, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_patient_list = args[2]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_medical_record()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_PATIENT_MEDICAL_RECORD, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database)
        self.table_widget_medical_record.set_column_hidden([0])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('匯出Excel')
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText('取消')

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        options = QtWidgets.QFileDialog.Options()
        excel_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "匯出病歷資料",
            '病歷資料.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_medical_record,
            hidden_column=[0],
            numeric_cell=[2, 8, 11, 12, 13, 14, 15, 16, 17, 18],
        )

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '資料匯出完成',
            f'<h3>病歷資料{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _get_patient_key_list(self):
        patient_key_list = []

        for row_no in range(self.table_widget_patient_list.rowCount()):
            check_box = self.table_widget_patient_list.cellWidget(row_no, 0)
            if check_box is not None and not check_box.isChecked():
                continue

            item = self.table_widget_patient_list.item(row_no, 1)
            if item is None:
                continue

            patient_key_list.append(item.text())

        return patient_key_list

    def _read_medical_record(self):
        patient_key_list = self._get_patient_key_list()
        if len(patient_key_list) <= 0:
            return

        if len(patient_key_list) == 1:
            sql = f'''
                SELECT * FROM cases
                WHERE
                    PatientKey = {patient_key_list[0]}
                ORDER BY PatientKey, CaseDate
            '''
        else:
            sql = f'''
                SELECT * FROM cases
                WHERE
                    PatientKey IN {tuple(patient_key_list)}
                ORDER BY PatientKey, CaseDate
            '''

        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)
        # self.ui.tableWidget_medical_record.resizeColumnsToContents()
        # self.ui.tableWidget_medical_record.resizeRowsToContents()

    def _set_table_data(self, row_no, row):
        case_key = row['CaseKey']
        pres_days = case_utils.get_pres_days(self.database, case_key)
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['DiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['DrugShareFee'])
        diag_fee = number_utils.get_integer(row['DiagFee'])
        inter_drug_fee = number_utils.get_integer(row['InterDrugFee'])
        pharmacy_fee = number_utils.get_integer(row['PharmacyFee'])
        acupuncture_fee = number_utils.get_integer(row['AcupunctureFee'])
        massage_fee = number_utils.get_integer(row['MassageFee'])
        treat_fee = acupuncture_fee + massage_fee
        ins_apply_fee = number_utils.get_integer(row['InsApplyFee'])

        medical_record_row = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.xstr(row['Continuance']),
            string_utils.xstr(pres_days),
            string_utils.xstr(row['DiseaseName1']),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(diag_fee),
            string_utils.xstr(inter_drug_fee),
            string_utils.xstr(pharmacy_fee),
            string_utils.xstr(treat_fee),
            string_utils.xstr(ins_apply_fee),
        ]

        for col_no in range(len(medical_record_row)):
            self.ui.tableWidget_medical_record.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record_row[col_no])
            )
            if col_no in [2, 8, 11, 12, 13, 14, 15, 16, 17, 18]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [4, 7]:
                self.ui.tableWidget_medical_record.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

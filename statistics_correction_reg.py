# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QMessageBox

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import case_utils
from libs import personnel_utils
from libs import system_utils
from libs import dialog_utils


# 矯正機關內門診統計表
class StatisticsCorrectionReg(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsCorrectionReg, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.dialog_setting = {
            "dialog_executed": False,
            "start_date": None,
            "end_date": None,
            "period": None,
        }
        self.ui = None
        self.sql = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_medical_record_list(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_CORRECTION_REG, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_ic_record, self.database)
        self.table_widget_medical_record.set_column_hidden([0])

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_medical_record_list)
        self.ui.action_open_record.triggered.connect(self.open_medical_record)
        self.ui.action_generate_upload_file.triggered.connect(self.generate_upload_xml_file)

        self.ui.tableWidget_ic_record.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_ic_record.horizontalHeader().sectionClicked.connect(self._header_clicked)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 50, 160, 50, 80, 80, 40, 120, 50, 80, 80, 70, 40, 40, 100, 800]
        self.table_widget_medical_record.set_table_heading_width(width)

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_ic_record_upload(
            self, self.database, self.system_settings, 'statistics_correction_reg')
        if self.dialog_setting['dialog_executed']:
            dialog.ui.dateEdit_start_date.setDate(self.dialog_setting['start_date'])
            dialog.ui.dateEdit_end_date.setDate(self.dialog_setting['end_date'])
            dialog.ui.comboBox_period.setCurrentText(self.dialog_setting['period'])

        result = dialog.exec_()
        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['start_date'] = dialog.ui.dateEdit_start_date.date()
        self.dialog_setting['end_date'] = dialog.ui.dateEdit_end_date.date()
        self.dialog_setting['period'] = dialog.comboBox_period.currentText()

        self.sql = dialog.get_sql()
        dialog.close_all()
        dialog.deleteLater()

        if result == 0:
            return

        self.read_data(self.sql)

    def read_data(self, sql):
        self.table_widget_medical_record.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        case_key = row['CaseKey']
        sql = f'''
            SELECT * FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            pres_days = rows[0]['Days']
        else:
            pres_days = None

        security_row = case_utils.get_treat_data_xml_dict(string_utils.get_str(row['Security'], 'utf-8'))
        if security_row is None:
            return

        error_message = self._check_error(row, security_row)

        medical_record = [
            string_utils.xstr(row['CaseKey']),
            None,
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Gender']),
            string_utils.xstr(row['Birthday']),
            string_utils.xstr(row['CaseInsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            string_utils.xstr(row['Card']),
            string_utils.int_to_str(row['Continuance']).strip('0'),
            string_utils.int_to_str(pres_days),
            string_utils.xstr(row['Doctor']),
            error_message,
        ]

        for column in range(len(medical_record)):
            self.ui.tableWidget_ic_record.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(medical_record[column])
            )
            if column in [4]:
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [3, 6, 12, 13]:
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if error_message != '':
                self.ui.tableWidget_ic_record.item(
                    row_no, column).setForeground(
                    QtGui.QColor('red')
                )

        self._set_check_box(row_no, True)

    def _set_check_box(self, row_no, check):
        check_box = QtWidgets.QCheckBox()
        check_box.setStyleSheet('padding-left: 20px')
        check_box.setChecked(check)
        col_no = 1

        self.ui.tableWidget_ic_record.setCellWidget(
            row_no, col_no, check_box)
        self.ui.tableWidget_ic_record.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _check_error(self, row, security_row):
        if string_utils.xstr(row['DoctorDone']) == 'False':
            return '[尚未就診, 請登錄完成後再上傳]'
        patient_key = row['PatientKey']
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        patient_record = self.database.select_record(sql)[0]

        error_message = []
        if security_row['upload_type'] == '1':
            if security_row['registered_date'] == '':
                error_message.append('無IC卡掛號時間')
            if security_row['security_signature'] == '':
                error_message.append('無安全簽章')
            if security_row['sam_id'] == '':
                error_message.append('無安全模組代碼')
            if security_row['clinic_id'] == '':
                error_message.append('無院所代碼')
            if string_utils.xstr(patient_record['CardNo']) == '':
                error_message.append('病患資料無卡片號碼')

        if string_utils.xstr(patient_record['ID']) == '':
            error_message.append('病患資料無身份證號碼')
        if string_utils.xstr(patient_record['Birthday']) == '':
            error_message.append('病患資料無生日')
        if security_row['upload_type'] == '':
            error_message.append('無上傳格式')
        if security_row['treat_after_check'] == '':
            error_message.append('無補卡註記')
        if string_utils.xstr(row['Card']) == '':
            error_message.append('無卡序')
        if row['CardNo'] is not None and len(row['CardNo']) >= 1 and len(row['CardNo']) != 12:
            error_message.append('健保卡片號碼有誤')

        doctor_id = personnel_utils.get_person_field_value(
            self.database, string_utils.xstr(row['Doctor']), 'ID')
        position_list = personnel_utils.get_person(self.database, '醫師')

        if doctor_id == '':
            error_message.append('無醫師身份證號')
        elif string_utils.xstr(row['Doctor']) not in position_list:
            error_message.append('醫師欄位非醫師')
        if string_utils.xstr(row['DiseaseCode1']) == '':
            error_message.append('無主診斷碼')
        if string_utils.xstr(row['InsTotalFee']) == '':
            error_message.append('無申報費用')
        for i in range(1, 4):
            disease_code = string_utils.xstr(row[f'DiseaseCode{i}'])
            if disease_code == '':
                continue

            if not case_utils.is_disease_code_neat(self.database, disease_code):
                error_message.append(f'病名{i}非最細碼')

        return ', '.join(error_message)

    def open_medical_record(self):
        case_key = self.table_widget_medical_record.field_value(0)
        self.parent.open_medical_record(case_key, '病歷查詢')

    # 上傳資料
    def generate_upload_xml_file(self):
        upload_type = '1'

        try:
            current_date = self.ui.tableWidget_ic_record.item(0, 2).text()
            upload_filename = f'C{int(current_date[:4])-1911}{current_date[5:7]}{current_date[8:10]}.XML'
        except Exception:
            current_date = self.dialog_setting['start_date']
            upload_filename = f"C{current_date.year()-1911:0>3}{current_date.month():0>2}{current_date.day():0>2}.XML"

        ic_upload_xml = class_utils.get_ic_upload_xml1(
            self.parent, self.database, self.system_settings, self.ui.tableWidget_ic_record, upload_type)

        if ic_upload_xml.create_xml_file(assign_path=True, filename=upload_filename) is None:
            return

        if not ic_upload_xml.is_file_created():
            system_utils.show_message_box(
                QMessageBox.Critical,
                '上傳失敗',
                '''
                    <font color="red">
                        <h3>無法建立上傳XML檔案, 請檢查是否全部註記或資料路徑是否正確!</h3>
                    </font>
                ''',
                '請檢查是否設定正確',
            )
            return

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>矯正機關內門診上傳檔{upload_filename}匯出完成.</h3>',
            'XML 格式.'
        )

    def _header_clicked(self, col_no):
        if col_no != 1:
            return

        row_count = self.ui.tableWidget_ic_record.rowCount()
        for row_no in range(row_count):
            check_box = self.ui.tableWidget_ic_record.cellWidget(row_no, col_no)
            if check_box is None:
                continue

            check_box.setChecked(not check_box.isChecked())

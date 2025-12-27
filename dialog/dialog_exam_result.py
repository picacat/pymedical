
# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
import lxml
from lxml import etree

from libs import class_utils

from libs import system_utils
from libs import ui_utils
from libs import string_utils
from libs import nhi_utils
from libs import date_utils
from libs import patient_utils
from libs import dialog_utils

try:
    import requests
    import_requests = True
except ImportError:
    import_requests = False


# 檢驗結果 2020.03.28
class DialogExamResult(QtWidgets.QDialog):
    program_name = '檢驗結果報告'

    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogExamResult, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.patient_id = None

        if self.patient_key is not None:
            self.patient_id = patient_utils.get_patient_id(self.database, self.patient_key)

        self.ui = None

        self._set_ui()
        self._set_signal()

        if not import_requests:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '模組未安裝',
                '<font size="5" color="red"><b>找不到requests模組, 無法取得檢驗資料.</b></font>',
                '請聯絡軟體工程師安裝requests模組.'
            )
            return

        self.clinic_id = self.system_settings.field('院所代號')
        self.url = self.system_settings.field('檢驗所伺服器')
        self.hosp_id = self.system_settings.field('檢驗所用戶代碼')
        self.login_pws = self.system_settings.field('檢驗所密碼')

        if self.url is None or self.hosp_id is None or self.login_pws is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                '參數未設定',
                '<font size="5" color="red"><b>系統設定內沒有醫事檢驗所連線資訊, 無法取得檢驗資料.</b></font>',
                '請至系統設定將醫師檢驗所連線設定完成.'
            )
            return

        if self.patient_key is None:
            self._read_clinical_medical_record()
        else:
            self._read_personal_medical_record()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_EXAM_RESULT, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText('確定')
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_exam_items = class_utils.get_table_widget(
            self.ui.tableWidget_exam_items, self.database
        )
        self.table_widget_medical_record.set_table_heading_width(
            [110, 120, 100, 100]
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [90, 90, 300, 280, 130, 150, 120, 90]
        self.table_widget_exam_items.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.tableWidget_medical_record.itemSelectionChanged.connect(self._medical_record_changed)

    def accepted_button_clicked(self):
        self.close()

    def _read_clinical_medical_record(self):
        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, self.program_name)
        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_date = dialog.ui.calendarWidget.selectedDate()
        dialog.deleteLater()

        year = current_date.year()
        month = current_date.month()
        day = current_date.day()
        case_date = f'{year}-{month:0>2}-{day:0>2}'
        self._set_exam_date_by_date(case_date)
        self.ui.tableWidget_medical_record.setCurrentCell(0, 0)

    def _read_personal_medical_record(self):
        ins_type_list = string_utils.xstr(nhi_utils.INS_TYPE)[1:-1]
        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                cases.PatientKey = {self.patient_key}
            ORDER BY CaseDate DESC, FIELD(cases.InsType, {ins_type_list})
        '''
        rows = self.database.select_record(sql)

        max_progress = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            '正在讀取檢驗資料中, 請稍後...', '取消', 0, max_progress, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for i, row in zip(range(max_progress), rows):
            year = row['CaseDate'].year
            month = row['CaseDate'].month
            day = row['CaseDate'].day
            case_date = f'{year}-{month:0>2}-{day:0>2}'
            try:
                self._set_exam_date_by_patient(case_date)
            except Exception:
                pass
            
            progress_dialog.setValue(i)

        progress_dialog.setValue(max_progress)
        self.ui.tableWidget_medical_record.setCurrentCell(0, 0)

    def _set_exam_date_by_date(self, exam_date):
        xml = self._get_exam_xml_from_url(exam_date)
        try:
            root = etree.fromstring(xml)
        except lxml.etree.XMLSyntaxError:
            return

        rows = root.xpath('//LabExam/PatientNewCare')

        for row in rows:
            row_no = self.ui.tableWidget_medical_record.rowCount()
            self.ui.tableWidget_medical_record.setRowCount(row_no + 1)
            exam_row = [
                string_utils.xstr(exam_date),
                row.attrib['ExamNo'],
                row.attrib['HISno'],
                row.attrib['Name'],
            ]
            for col_no in range(len(exam_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, exam_row[col_no])
                self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)

    def _set_exam_date_by_patient(self, exam_date):
        xml = self._get_exam_xml_from_url(exam_date)
        root = etree.fromstring(xml)
        rows = root.xpath('//LabExam/PatientNewCare')

        for row in rows:
            patient_key = row.attrib['HISno']
            patient_id = row.attrib['Idno']
            if patient_key != string_utils.xstr(self.patient_key) and patient_id != self.patient_id:
                continue

            row_no = self.ui.tableWidget_medical_record.rowCount()
            self.ui.tableWidget_medical_record.setRowCount(row_no + 1)
            exam_row = [
                string_utils.xstr(exam_date),
                row.attrib['ExamNo'],
                row.attrib['HISno'],
                row.attrib['Name'],
            ]
            for col_no in range(len(exam_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, exam_row[col_no])
                self.ui.tableWidget_medical_record.setItem(row_no, col_no, item)

    def _get_exam_xml(self, exam_date, exam_no):
        exam_xml = None

        xml = self._get_exam_xml_from_url(exam_date)
        root = etree.fromstring(xml)
        rows = root.xpath('//LabExam/PatientNewCare')

        for row in rows:
            xml_exam_no = row.attrib['ExamNo']
            if string_utils.xstr(exam_no) == string_utils.xstr(xml_exam_no):
                exam_xml = row
                break

        return exam_xml

    def _get_exam_xml_from_url(self, exam_date):
        his_date = date_utils.west_date_to_nhi_date(exam_date)
        xml = f'''
            <?xml version="1.0" encoding="UTF-8"?>
            <LabExam
                LoginId="{self.clinic_id}"
                LoginPWS="{self.login_pws}"
                HospId="{self.hosp_id}"
                HisDateB="{his_date}"
                HisDateE="{his_date}"
                SendDateB=""
                SendDateE="">
            </LabExam>
        '''
        param_data = {'data': xml}

        result = requests.post(url=self.url, data=param_data)
        xml_content = str(result.content, encoding='utf-8')

        return xml_content

    def _medical_record_changed(self):
        exam_date = self.ui.tableWidget_medical_record.item(
            self.ui.tableWidget_medical_record.currentRow(), 0
        ).text()
        exam_no = self.ui.tableWidget_medical_record.item(
            self.ui.tableWidget_medical_record.currentRow(), 1
        ).text()
        exam_xml = self._get_exam_xml(exam_date, exam_no)
        if exam_xml is None:
            return

        self._parse_exam_xml(exam_xml)

    def _parse_exam_xml(self, exam_xml):
        self.ui.lineEdit_exam_no.setText(exam_xml.attrib['ExamNo'])
        self.ui.lineEdit_req_no.setText(exam_xml.attrib['ReqNo'])
        self.ui.lineEdit_send_date.setText(exam_xml.attrib['SendDate'])
        self.ui.lineEdit_exam_date.setText(exam_xml.attrib['ExamDate'])
        self.ui.lineEdit_name.setText(exam_xml.attrib['Name'])
        self.ui.lineEdit_gender.setText(exam_xml.attrib['Gender'])
        self.ui.lineEdit_birthday.setText(exam_xml.attrib['BirthDay'])
        self.ui.lineEdit_id_no.setText(exam_xml.attrib['Idno'])
        self.ui.lineEdit_reg_date.setText(exam_xml.attrib['RegDate'])
        self.ui.lineEdit_rep_date.setText(exam_xml.attrib['RepDate'])
        self.ui.lineEdit_rep_time.setText(exam_xml.attrib['RepTime'])

        row_count = len(exam_xml)
        self.ui.tableWidget_exam_items.setRowCount(row_count)
        for row_no, item in enumerate(exam_xml):
            item_row = [
                item.attrib['ItemCode'],
                item.attrib['NhiID'],
                item.attrib['ItemName'],
                item.attrib['ItemCName'],
                item.attrib['Value'],
                item.attrib['Referance'],
                item.attrib['Units'],
                item.attrib['Operator'],
            ]
            flag = item.attrib['Flag']

            for col_no in range(len(item_row)):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, item_row[col_no])
                self.ui.tableWidget_exam_items.setItem(row_no, col_no, item)
                if flag != 'N':
                    self.ui.tableWidget_exam_items.item(
                        row_no, col_no
                    ).setForeground(QtGui.QColor('red'))

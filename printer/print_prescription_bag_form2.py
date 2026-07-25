
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils
from libs import case_utils
from libs import number_utils


# 藥袋格式2 10"
# 2023.08.12 青蓮
class PrintPrescriptionBagForm2:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '藥袋印表機')

        self.current_print = None
        self.additional = None

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
        self.font_name = system_utils.get_font()
        self.font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def _check_printing(self):
        printing = True

        if self.additional == '健保另包':
            if printer_utils.is_additional_prescript(self.database, self.case_key):
                printing = True
            else:
                printing = False

        return printing

    def print(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        self.print_painter()

    def preview(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        preview_dialog.paintRequested.connect(self.print_painter)
        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(7, 10), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_1(self.database, self.case_key, '健保')
        symptom_record = printer_utils.get_symptom_html(self.database, self.system_settings, self.case_key, colspan=5)
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '處方箋', blocks=3, instruction=self.additional)
        instruction = printer_utils.get_instruction_html(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        additional_label = printer_utils.get_additional_label(self.additional)

        html = f'''
            <html>
              <body>
                <table width="98%" cellspacing="0">
                  <tbody>
                    {case_record}
                    {symptom_record}
                  </tbody>
                </table>
                {disease_record}
                <hr style="line-height:0.5">
                <table width="98%" cellspacing="0">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                {instruction}
                {additional_label}
              </body>
            </html>
        '''

        return html

    def print_painter(self):
        medical_record = self._get_medical_record()
        if medical_record is None:
            return

        self.printer.setPaperSize(QtCore.QSizeF(7, 10), QPrinter.Inch)
        painter = QtGui.QPainter()

        painter.begin(self.printer)

        self._print_patient(painter, medical_record)
        self._print_dosage(painter, medical_record)
        self._print_prescript(painter, medical_record)
        self._print_fee(painter, medical_record)
        self._print_caution(painter, medical_record)

        painter.end()

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [165, 195, 215]
        else:
            lines = [165, 195, 215]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(165, lines[1], medical_record['patient_name'])

        painter.drawText(460, lines[0], medical_record['patient_key'])
        painter.drawText(460, lines[2], medical_record['doctor'])

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [260, 300]
        else:
            lines = [260, 300]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(225, lines[0], f"{medical_record['packages']}")
        painter.drawText(400, lines[0], medical_record['pres_days'])
        painter.drawText(230, lines[1], medical_record['instruction'])
        painter.drawText(460, lines[1], '1')

    def _print_prescript(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [360]
            character_height = 16
        else:
            lines = [360]
            character_height = 16

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set} AND
                MedicineType NOT IN ("穴道", "處置", "檢驗")
            ORDER BY PrescriptKey
        '''
        rows = self.database.select_record(sql)

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)

        top = 0
        left = [70, 200, 275, 310, 385]
        self.total_dosage = 0
        pres_days = number_utils.get_integer(medical_record['pres_days'])
        for row in rows:
            painter.drawText(left[0], lines[0]+top, string_utils.xstr(row['MedicineName']))
            dosage = number_utils.get_float(row['Dosage'])
            if dosage > 0:
                this_total_doage = dosage * pres_days
                self.total_dosage += this_total_doage
                painter.drawText(
                    QtCore.QRect(left[1], lines[0]+top-character_height, 70, character_height),
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                    f"{row['Dosage']:.1f}")
                painter.drawText(left[2], lines[0]+top, string_utils.xstr(row['Unit']))

                painter.drawText(
                    QtCore.QRect(left[3], lines[0]+top-character_height, 70, character_height),
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                    f"{this_total_doage:.1f}")
                painter.drawText(left[4], lines[0]+top, string_utils.xstr(row['Unit']))

            top += character_height

    def _print_fee(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [520, 540]
        else:
            lines = [520, 540]

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(70, lines[0], f"掛號費: {medical_record['regist_fee']}")
        painter.drawText(190, lines[0], f"門診負擔: {medical_record['diag_share_fee']}")
        painter.drawText(310, lines[0], f"藥品負擔: {medical_record['drug_share_fee']}")

        total_fee = (number_utils.get_integer(medical_record['regist_fee']) +
                     number_utils.get_integer(medical_record['diag_share_fee']) +
                     number_utils.get_integer(medical_record['drug_share_fee']))

        painter.drawText(70, lines[1], f"收費合計: {total_fee}")
        painter.drawText(190, lines[1], f"總量: {self.total_dosage}")

    def _print_caution(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [580, 600, 640, 680]
        else:
            lines = [580, 600, 640, 680]

        font = QtGui.QFont(self.font_name, 14, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(150, lines[0], medical_record['case_date'])
        painter.drawText(460, lines[0], medical_record['doctor'])
        painter.drawText(150, lines[1], '請勿與其他藥品混合服用')
        painter.drawText(150, lines[2], medical_record['disease_name'])
        painter.drawText(150, lines[3], '無')

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
            DiseaseName1, DiseaseName2, DiseaseName3,
            RegistFee, SDiagShareFee, SDrugShareFee,
            patient.Gender, patient.Birthday
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            cases.CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]

        case_date = string_utils.xstr(row['CaseDate'].date())
        case_date = date_utils.west_date_to_nhi_date(case_date)
        case_date = f'{case_date[:3]}-{case_date[3:5]}-{case_date[5:]}'
        case_time = string_utils.xstr(row['CaseDate'].time())[:5]
        case_datetime = f'{case_date} {case_time}'
        disease_list = []
        if string_utils.xstr(row['DiseaseName1']) != '':
            disease_list.append(string_utils.xstr(row['DiseaseName1']))
        if string_utils.xstr(row['DiseaseName2']) != '':
            disease_list.append(string_utils.xstr(row['DiseaseName2']))
        if string_utils.xstr(row['DiseaseName3']) != '':
            disease_list.append(string_utils.xstr(row['DiseaseName3']))

        medical_record = dict()
        medical_record['patient_key'] = string_utils.xstr(row['PatientKey'])
        medical_record['patient_name'] = string_utils.xstr(row['Name'])
        medical_record['gender'] = string_utils.xstr(row['Gender'])
        medical_record['age'], _ = date_utils.get_age(row['Birthday'], row['CaseDate'].date())

        medical_record['case_date'] = case_date
        medical_record['case_time'] = case_time
        medical_record['case_datetime'] = case_datetime

        packages = case_utils.get_packages(self.database, self.case_key)
        pres_days = case_utils.get_pres_days(self.database, self.case_key)
        instruction = case_utils.get_instruction(self.database, self.case_key)
        medical_record['pres_days'] = string_utils.xstr(pres_days)
        medical_record['packages'] = string_utils.xstr(packages)
        medical_record['instruction'] = instruction

        medical_record['doctor'] = string_utils.xstr(row['Doctor'])
        medical_record['disease_name'] = ','.join(disease_list)

        medical_record['regist_fee'] = string_utils.xstr(row['RegistFee'])
        medical_record['diag_share_fee'] = string_utils.xstr(row['SDiagShareFee'])
        medical_record['drug_share_fee'] = string_utils.xstr(row['SDrugShareFee'])

        return medical_record

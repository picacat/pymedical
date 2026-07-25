
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


# 藥袋格式1 241mm x 93mm
# 2023.02.19 澄美
class PrintPrescriptionBagForm1:
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
        self._print_prescript(painter)
        self._print_caution(painter, medical_record)
        self._print_doctor(painter, medical_record)

        painter.end()

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [205, 240]
        else:
            lines = [205, 240]

        font = QtGui.QFont(self.font_name, 14, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[0], medical_record['case_datetime'])
        painter.drawText(355, lines[0], medical_record['patient_key'])

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[1], medical_record['patient_name'])
        painter.drawText(355, lines[1], f"{medical_record['gender']} / {medical_record['age']}")

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [280, 355]
        else:
            lines = [280, 355]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[0], f"每日{medical_record['packages']}次，{medical_record['instruction']}服用")
        painter.drawText(580, lines[1], medical_record['pres_days'])

    def _print_prescript(self, painter):
        if sys.platform == 'win32':
            lines = [390]
            character_height = 22
        else:
            lines = [390]
            character_height = 22

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = {self.medicine_set} AND
                MedicineType NOT IN ("穴道", "處置", "檢驗")
            ORDER BY PrescriptKey
        '''
        rows = self.database.select_record(sql)

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)

        top = 0
        for row in rows:
            painter.drawText(125, lines[0]+top, string_utils.xstr(row['MedicineName']))
            if number_utils.get_float(row['Dosage']) > 0:
                painter.drawText(
                    QtCore.QRect(520, lines[0]+top-20, 70, character_height),
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                    f"{row['Dosage']:.1f}")
                painter.drawText(595, lines[0]+top, string_utils.xstr(row['Unit']))

            top += character_height

    def _print_caution(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [705]
        else:
            lines = [705]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[0], '請勿與其他藥品混合服用')

    def _print_doctor(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [803, 828]
        else:
            lines = [803, 828]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[0], medical_record['doctor'])
        painter.drawText(345, lines[0], medical_record['doctor'])

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(125, lines[1], '中醫科')

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
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

        return medical_record

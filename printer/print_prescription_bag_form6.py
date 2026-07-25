
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys
import win32print
import win32ui

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils
from libs import case_utils
from libs import number_utils


# 藥包標籤, 女監使用 格式6 40mm x 20mm
# 2024.10.29 龍潭安聲
class PrintPrescriptionBagForm6:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '藥袋印表機')
        self.printer_name = self.system_settings.field('藥袋印表機')

        self.current_print = None
        self.additional = None

        self._set_ui()
        self._set_signal()

        self.medical_record = self._get_medical_record()
        pres_days = number_utils.get_integer(self.medical_record['pres_days'])
        packages = number_utils.get_integer(self.medical_record['packages'])

        self.total_packages = pres_days * packages


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

        for _ in range(self.total_packages):
            self.print_tsc()

    def print_tsc(self):
        chart_no = self.medical_record['chart_no']
        instruction = self.medical_record['instruction']
        tspl_commands = f"""
            SIZE 40 mm, 20 mm
            GAP 3 mm, 0 mm
            DIRECTION 1
            CLS
            TEXT 10,30,"TSS24.BF2",0,2,2,"{chart_no}"
            TEXT 10,80,"TSS24.BF2",0,2,2,"{instruction}"
            PRINT 1
        """

        # 打開印表機
        handle = win32print.OpenPrinter(self.printer_name)
        try:
            # 開始列印作業
            job = win32print.StartDocPrinter(handle, 1, ("Label Print Job", None, "RAW"))
            win32print.StartPagePrinter(handle)

            # 將 TSPL 指令發送到印表機
            win32print.WritePrinter(handle, tspl_commands.encode('big5'))

            # 結束列印作業
            win32print.EndPagePrinter(handle)
            win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)

    def preview(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        preview_dialog.paintRequested.connect(self.print_painter)
        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        for _ in range(self.total_packages):
            preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(40, 20), QPrinter.Millimeter)

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
        self.printer.setPaperSize(QtCore.QSizeF(60, 60), QPrinter.Millimeter)
        painter = QtGui.QPainter()

        painter.begin(self.printer)

        self._print_patient(painter, self.medical_record)
        self._print_dosage(painter, self.medical_record)
        self._print_spaces(painter, self.medical_record)

        painter.end()

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [25]
        else:
            lines = [25]

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(45, lines[0], medical_record['patient_key'])

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [45]
        else:
            lines = [45]

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(45, lines[0], f"{medical_record['instruction']}")

    def _print_spaces(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [65]
        else:
            lines = [45]

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(45, lines[0], '')

        painter.drawText(45, 81, '')

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
            patient.ChartNo, patient.Gender, patient.Birthday
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
        case_datetime = f'{case_date}'

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
        medical_record['chart_no'] = string_utils.xstr(row['ChartNo'])

        return medical_record

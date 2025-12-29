
# -*- coding: UTF-8 -*-

import sys

from libs import (case_utils, date_utils, number_utils, printer_utils,
                  string_utils, system_utils)
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter


# 藥袋格式8 8x10"
# 2025.07.14 脈蘊-公版藥袋
class PrintPrescriptionBagForm8:
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
        self.printer.setPaperSize(QtCore.QSizeF(8, 10), QPrinter.Inch)

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

        self._print_title(painter, medical_record)
        self._print_patient(painter, medical_record)
        self._print_dosage(painter, medical_record)
        self._print_prescript(painter)
        # self._print_caution(painter, medical_record)
        self._print_doctor(painter, medical_record)

        painter.end()

    def _print_title(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [70, 100]
        else:
            lines = [70, 100]

        clinic_fullname = self.system_settings.field('院所名稱')
        clinic_address = self.system_settings.field('院所地址')
        level_list = ['中醫診所', '中醫聯合診所']
        clinic_name = None
        clinic_level = '中醫診所'
        for level in level_list:
            if level in clinic_fullname:
                clinic_name = clinic_fullname.split(level)[0]
                clinic_level = level
                break

        font = QtGui.QFont(self.font_name, 48, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(120, lines[0], clinic_name)

        font = QtGui.QFont(self.font_name, 24, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(400, lines[0]-24, clinic_level)

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(400, lines[0], 'Chinese Medicine Clinic')

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(120, lines[1], clinic_address)

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [140, 170, 200]
        else:
            lines = [140, 170, 200]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(90, lines[0], medical_record['patient_key'])
        painter.drawText(300, lines[0], medical_record['patient_name'])
        painter.drawText(500, lines[0], medical_record['gender'])

        painter.drawText(90, lines[1], medical_record['case_date'])
        painter.drawText(300, lines[1], medical_record['share_type'])
        painter.drawText(500, lines[1], '中醫科')

        painter.drawText(90, lines[2], '1')
        painter.drawText(300, lines[2], '1')
        painter.drawText(500, lines[2], medical_record['doctor'])

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [260]
        else:
            lines = [260]

        font = QtGui.QFont(self.font_name, 20, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(60, lines[0], '用法用量:')

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(60, lines[0]+24, 'Usage and Dosage')

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(250, lines[0]+10,
            f"每日{medical_record['packages']}次，{medical_record['instruction']}服用，共{medical_record['pres_days']}日份")

        # 畫一條線：從 (60, y) 到 (550, y)
        line_y = lines[0] + 32 
        painter.drawLine(60, line_y, 600, line_y)

    def _print_prescript(self, painter):
        if sys.platform == 'win32':
            lines = [320, 350]
            character_height = 18
        else:
            lines = [320, 350]
            character_height = 18

        font = QtGui.QFont(self.font_name, 20, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(60, lines[0], '藥名 Medication Name:')

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
        medicine_name_position = 60
        dosage_position = 190
        unit_position = 270
        for row_no, row in enumerate(rows):
            if row_no == 12:
                top = 0
                medicine_name_position += 280
                dosage_position += 280
                unit_position += 280

            painter.drawText(medicine_name_position, lines[1]+top, string_utils.xstr(row['MedicineName']))
            if number_utils.get_float(row['Dosage']) > 0:
                painter.drawText(
                    QtCore.QRect(dosage_position, lines[1]+top-16, 70, character_height),
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                    f"{row['Dosage']:.1f}")
                painter.drawText(unit_position, lines[1]+top-1, string_utils.xstr(row['Unit']))

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

        # 畫一條線：從 (60, y) 到 (550, y)
        line_y = lines[0] + - 32 
        painter.drawLine(60, line_y, 600, line_y)

        font = QtGui.QFont(self.font_name, 20, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(60, lines[0], '處方醫師 Physican:')
        painter.drawText(320, lines[0], medical_record['doctor'])

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
            cases.Share,
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
        medical_record['share_type'] = string_utils.xstr(row['Share'])
        medical_record['age'], _ = date_utils.get_age(row['Birthday'], row['CaseDate'].date())

        medical_record['case_date'] = case_date
        medical_record['case_time'] = case_time
        medical_record['case_datetime'] = case_datetime

        packages = case_utils.get_packages(self.database, self.case_key, medicine_set=self.medicine_set)
        pres_days = case_utils.get_pres_days(self.database, self.case_key, medicine_set=self.medicine_set)
        instruction = case_utils.get_instruction(self.database, self.case_key, medicine_set=self.medicine_set)
        medical_record['pres_days'] = string_utils.xstr(pres_days)
        medical_record['packages'] = string_utils.xstr(packages)
        medical_record['instruction'] = instruction

        medical_record['doctor'] = string_utils.xstr(row['Doctor'])

        return medical_record

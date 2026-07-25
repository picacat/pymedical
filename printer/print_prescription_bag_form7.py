
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
# 2025.01.09 仙岩
class PrintPrescriptionBagForm7:
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

        ins_pres_days = case_utils.get_pres_days(self.database, self.case_key, medicine_set=1)
        if ins_pres_days > 0:
            self._print_ins_prescript(painter, medical_record)
        else:
            self._print_self_prescript(painter, medical_record)

        self._print_doctor(painter, medical_record)
        self._print_caution(painter, medical_record)

        painter.end()

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [140, 180]
        else:
            lines = [140, 180]

        font = QtGui.QFont(self.font_name, 32, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(60, lines[0]+30, medical_record['patient_name'])

        font = QtGui.QFont(self.font_name, 18, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(460, lines[0], medical_record['patient_key'])
        painter.drawText(460, lines[1], medical_record['doctor'])

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [230, 270]
        else:
            lines = [230, 270]

        font = QtGui.QFont(self.font_name, 18, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(250, lines[0], string_utils.xstr(medical_record['packages']))
        painter.drawText(450, lines[0], string_utils.xstr(medical_record['pres_days']))
        painter.drawText(120, lines[1], medical_record['instruction'])
        painter.drawText(480, lines[1], '1')

    def _get_ins_prescript(self):
        sql = f'''
            SELECT
                prescript.MedicineName, prescript.Dosage, prescript.Unit,
                medicine.Location
            FROM prescript
                LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = 1 AND
                prescript.MedicineType NOT IN ("穴道", "處置", "檢驗")
            ORDER BY PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        ins_prescript = []
        for row in rows:
            location = string_utils.xstr(row['Location'])
            medicine_name = string_utils.xstr(row['MedicineName'][:8])
            dosage = number_utils.get_float(row['Dosage'])
            unit = string_utils.xstr(row['Unit'])
            ins_prescript.append([location, medicine_name, dosage, unit])

        return ins_prescript

    def _get_self_prescript(self):
        sql = f'''
            SELECT
                prescript.MedicineName, prescript.Dosage, prescript.Unit,
                medicine.Location
            FROM prescript
                LEFT JOIN medicine ON medicine.MedicineKey = prescript.MedicineKey
            WHERE
                CaseKey = {self.case_key} AND
                MedicineSet = 2 AND
                prescript.MedicineType IN ("單方", "複方", "自費科中")
            ORDER BY PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        self_prescript = []
        for row in rows:
            location = string_utils.xstr(row['Location'])
            medicine_name = string_utils.xstr(row['MedicineName'][:8])
            dosage = number_utils.get_float(row['Dosage'])
            unit = string_utils.xstr(row['Unit'])
            self_prescript.append([location, medicine_name, dosage, unit])

        return self_prescript

    def _print_ins_prescript(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [335]
            character_height = 18 
        else:
            lines = [335]
            character_height = 20

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        
        ins_pres_days = number_utils.get_integer(medical_record['pres_days'])
        self_pres_days = case_utils.get_pres_days(self.database, self.case_key, medicine_set=2)
        if self_pres_days == 0:
            self_pres_days = 1

        top = 0
        ins_prescript = self._get_ins_prescript()
        self_prescript = self._get_self_prescript()

        max_length = len(ins_prescript)
        if len(self_prescript) > max_length:
            max_length = len(self_prescript)

        for index in range(max_length):
            if index < len(ins_prescript):
                ins_location = string_utils.xstr(ins_prescript[index][0])
                ins_medicine_name = ins_location + string_utils.xstr(ins_prescript[index][1][:8])
                ins_unit = string_utils.xstr(ins_prescript[index][3])

                painter.drawText(50, lines[0]+top, ins_medicine_name)

                ins_dosage = ins_prescript[index][2]
                if ins_dosage > 0:
                    ins_total_dosage = ins_dosage * ins_pres_days
                    painter.drawText(
                        QtCore.QRect(190, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{ins_dosage:.1f}")
                    painter.drawText(260, lines[0]+top, ins_unit)

                    painter.drawText(
                        QtCore.QRect(250, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{ins_total_dosage:.1f}")
                    painter.drawText(320, lines[0]+top, ins_unit)

            if len(self_prescript) > 0 and index < len(self_prescript):
                self_location = string_utils.xstr(self_prescript[index][0])
                self_medicine_name = self_location + string_utils.xstr(self_prescript[index][1][:7])
                self_unit = string_utils.xstr(self_prescript[index][3])
                painter.drawText(350, lines[0]+top, self_medicine_name)
                self_dosage = self_prescript[index][2]
                if self_dosage > 0:
                    self_total_dosage = self_dosage * self_pres_days
                    painter.drawText(
                        QtCore.QRect(450, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{self_dosage:.1f}")
                    painter.drawText(520, lines[0]+top, self_unit)

                    painter.drawText(
                        QtCore.QRect(510, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{self_total_dosage:.1f}")
                    painter.drawText(580, lines[0]+top, self_unit)

            top += character_height

    def _print_self_prescript(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [335]
            character_height = 18 
        else:
            lines = [335]
            character_height = 20

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        
        self_pres_days = case_utils.get_pres_days(self.database, self.case_key, medicine_set=2)
        if self_pres_days == 0:
            self_pres_days = 1

        top = 0
        self_prescript = self._get_self_prescript()

        max_length = len(self_prescript)
        for index in range(max_length):
            if index < len(self_prescript):
                self_location = string_utils.xstr(self_prescript[index][0])
                self_medicine_name = self_location + string_utils.xstr(self_prescript[index][1][:8])
                self_unit = string_utils.xstr(self_prescript[index][3])

                painter.drawText(50, lines[0]+top, self_medicine_name)

                self_dosage = self_prescript[index][2]
                if self_dosage > 0:
                    ins_total_dosage = self_dosage * self_pres_days
                    painter.drawText(
                        QtCore.QRect(190, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{self_dosage:.1f}")
                    painter.drawText(260, lines[0]+top, self_unit)

                    painter.drawText(
                        QtCore.QRect(250, lines[0]+top-15, 70, character_height),
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        f"{ins_total_dosage:.1f}")
                    painter.drawText(320, lines[0]+top, self_unit)

            top += character_height

    def _print_doctor(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [550]
        else:
            lines = [550]

        font = QtGui.QFont(self.font_name, 18, QtGui.QFont.PreferQuality)
        painter.setFont(font)

        painter.drawText(150, lines[0], medical_record['case_date'])
        painter.drawText(460, lines[0], medical_record['doctor'])

    def _print_caution(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [580, 610, 640]
        else:
            lines = [580, 610, 640]

        font = QtGui.QFont(self.font_name, 16, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(150, lines[0], '請勿與其它藥品混合服用')
        painter.drawText(150, lines[1], medical_record['disease_name'][:20])
        painter.drawText(150, lines[2], '本處方於醫學文獻中尚無副作用之記載')

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor,
            cases.DiseaseName1,
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
        case_datetime = f'{case_date}'

        medical_record = dict()
        medical_record['patient_key'] = string_utils.xstr(row['PatientKey'])
        medical_record['patient_name'] = string_utils.xstr(row['Name'])
        medical_record['disease_name'] = string_utils.xstr(row['DiseaseName1'])
        medical_record['gender'] = string_utils.xstr(row['Gender'])
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

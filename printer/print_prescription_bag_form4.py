
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


# 藥袋格式4 A4
# 2024.02.16 森奕閣
class PrintPrescriptionBagForm4:
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

    def print_painter(self):
        medical_record = self._get_medical_record()
        if medical_record is None:
            return

        self.printer.setPaperSize(QtCore.QSizeF(7, 10), QPrinter.Inch)
        painter = QtGui.QPainter()

        painter.begin(self.printer)

        self._print_patient(painter, medical_record)
        self._print_dosage(painter, medical_record)
        self._print_usage(painter, medical_record)

        painter.end()

    def _print_patient(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [165, 300]
        else:
            lines = [165, 300]

        font = QtGui.QFont(self.font_name, 24, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        case_year = medical_record['CaseDate'].year - 1911
        case_month = medical_record['CaseDate'].month
        case_day = medical_record['CaseDate'].day
        painter.drawText(340, lines[0], string_utils.xstr(case_year))
        painter.drawText(460, lines[0], f'{case_month:0>2}')
        painter.drawText(580, lines[0], f'{case_day:0>2}')

        font = QtGui.QFont(self.font_name, 36, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(340, lines[1], medical_record['patient_name'])

    def _print_dosage(self, painter, medical_record):
        if sys.platform == 'win32':
            lines = [390, 460]
        else:
            lines = [390, 460]

        font = QtGui.QFont(self.font_name, 24, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(270, lines[0], medical_record['packages'])
        painter.drawText(500, lines[0], medical_record['pres_days'])

    def _print_usage(self, painter, medical_record):
        usage1, usage2, usage3, usage4, usage5 = '', '', '', '', ''

        # if '早晚' in medical_record['instruction']:
        if number_utils.get_integer(medical_record['packages']) == 2:
            usage1 = 'V'
        elif number_utils.get_integer(medical_record['packages']) == 3:
            usage2 = 'V'

        # if '三餐' in medical_record['instruction']:
        #     usage2 = 'V'

        # usage2 = 'V'

        if '睡前' in medical_record['instruction']:
            usage3 = 'V'

        if '飯前' in medical_record['instruction']:
            usage4 = 'V'

        if '飯後' in medical_record['instruction']:
            usage5 = 'V'

        if sys.platform == 'win32':
            lines = [450, 500]
        else:
            lines = [450, 500]

        font = QtGui.QFont(self.font_name, 24, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(160, lines[0], usage1)
        painter.drawText(295, lines[0], usage2)
        painter.drawText(430, lines[0], usage3)

        painter.drawText(160, lines[1], usage4)
        painter.drawText(295, lines[1], usage5)

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
        medical_record['CaseDate'] = row['CaseDate']
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

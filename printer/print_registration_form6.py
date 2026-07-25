
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import sys
import datetime

from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils
from libs import date_utils
from libs import case_utils


# 掛號收據格式6 3"套表掛號單 (龍潭懷恩堂)
# 2020.01.09
class PrintRegistrationForm6:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '門診掛號單印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None
        self.return_card = None

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

    def print(self, return_card=None):
        self.return_card = return_card
        self.print_painter()

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_painter)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        medical_record = self._get_medical_record()
        if medical_record is None:
            return

        self.current_print = self.print_painter
        height = 3
        if self.system_settings.field('院所名稱') == '板橋聖昌中醫診所':
            height = 3.66

        self.printer.setPaperSize(QtCore.QSizeF(5, height), QPrinter.Inch)

        if sys.platform == 'win32':
            lines = [20, 110, 170, 230]
        else:
            lines = [0, 95, 155, 215]

        painter = QtGui.QPainter()
        painter.begin(self.printer)

        font = QtGui.QFont(self.font_name, 14, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(20, 50, medical_record['clinic_name'])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(40, lines[1], medical_record['patient_key'])
        painter.drawText(120, lines[1], medical_record['patient_name'])
        painter.drawText(250, lines[1], medical_record['room'])
        painter.drawText(350, lines[1], medical_record['registration_no'])

        painter.drawText(35, lines[2], medical_record['ins_type'])
        painter.drawText(120, lines[2], medical_record['visit'])
        painter.drawText(190, lines[2], medical_record['card'])
        painter.drawText(340, lines[2], medical_record['registrar'])

        font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(30, lines[3], medical_record['case_date'])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(110, lines[3], medical_record['case_time'])
        painter.drawText(210, lines[3], string_utils.xstr(medical_record['regist_fee']))
        painter.drawText(290, lines[3], string_utils.xstr(medical_record['diag_share_fee']))
        painter.drawText(360, lines[3], string_utils.xstr(medical_record['deposit_fee']))

        painter.end()

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.RegistNo, cases.Room,
            cases.InsType, cases.Share, cases.RegistFee, cases.SDiagShareFee,
            cases.DepositFee, cases.Card, cases.Continuance, cases.Visit, cases.Register,
            patient.DiscountType
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
        WHERE
            CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]
        if self.system_settings.field('列印院所名稱') == 'Y':
            clinic_name = self.system_settings.field('院所名稱')
        else:
            clinic_name = ''

        case_date = string_utils.xstr(row['CaseDate'].date())
        case_date = date_utils.west_date_to_nhi_date(case_date)
        case_date = f'{case_date[:3]}.{case_date[3:5]}.{case_date[5:]}'
        case_time = string_utils.xstr(row['CaseDate'].time())[:5]

        card = string_utils.xstr(row['Card'])
        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        return_card_note = ''

        if self.return_card == '還卡收據':
            return_date = case_utils.get_return_date(self.database, row['CaseKey'])
            if return_date is None:
                case_date = datetime.datetime.today()
                case_time = datetime.datetime.now().time().strftime('%H:%M')
            else:
                case_date = string_utils.xstr(return_date.date())
                case_time = string_utils.xstr(return_date.time())[:5]

            case_date = date_utils.west_date_to_nhi_date(case_date)
            case_date = f'{case_date[:3]}.{case_date[3:5]}.{case_date[5:]}'

            regist_fee = 0
            diag_share_fee = 0
            deposit_fee = -number_utils.get_integer(row['DepositFee'])
            return_card_note = '還卡'

        total_fee = string_utils.xstr(regist_fee + diag_share_fee + deposit_fee),

        medical_record = dict()
        medical_record['patient_key'] = string_utils.xstr(row['PatientKey'])
        medical_record['patient_name'] = string_utils.xstr(row['Name'])
        medical_record['registration_no'] = string_utils.xstr(row['RegistNo'])
        medical_record['share'] = string_utils.xstr(row['Share'])
        medical_record['room'] = string_utils.xstr(row['Room'])
        medical_record['visit'] = string_utils.xstr(row['Visit'])
        medical_record['ins_type'] = string_utils.xstr(row['InsType'])
        medical_record['discount_type'] = string_utils.xstr(row['DiscountType'])
        medical_record['registrar'] = string_utils.xstr(row['Register'])

        medical_record['clinic_name'] = clinic_name
        medical_record['case_date'] = case_date
        medical_record['case_time'] = case_time
        medical_record['card'] = card
        medical_record['regist_fee'] = regist_fee
        medical_record['diag_share_fee'] = diag_share_fee
        medical_record['deposit_fee'] = deposit_fee
        medical_record['total_fee'] = total_fee
        medical_record['return_card_note'] = return_card_note

        return medical_record

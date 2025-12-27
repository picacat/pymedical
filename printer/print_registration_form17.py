
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
from libs import charge_utils


# 掛號收據格式17 5.5"套表掛號單 (春暉)
# 2023.06.19
class PrintRegistrationForm17:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '門診掛號單印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
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

    def _get_medical_record(self):
        sql = f'''
        SELECT
            cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.RegistNo, cases.Room,
            cases.InsType, cases.Share, cases.RegistFee, cases.SDiagShareFee,
            cases.DepositFee, cases.RefundFee, cases.Card, cases.Continuance, cases.Visit, cases.Register,
            cases.Doctor as CaseDoctor, wait.Doctor, cases.Massager, cases.RegistType,
            patient.Birthday, patient.DiscountType
        FROM cases
            LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            LEFT JOIN wait ON wait.CasEKey = cases.CaseKey
        WHERE
            cases.CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return None

        row = rows[0]
        if self.system_settings.field('列印院所名稱') == 'Y':
            clinic_name = self.system_settings.field('院所名稱')
        else:
            clinic_name = ''

        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        case_date = string_utils.xstr(row['CaseDate'].date())
        case_date = date_utils.west_date_to_nhi_date(case_date)
        case_date = f'{case_date[:3]}.{case_date[3:5]}.{case_date[5:]}'
        case_time = string_utils.xstr(row['CaseDate'].time())[:5]

        card = string_utils.xstr(row['Card'])
        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])

        ins_type = string_utils.xstr(row['InsType'])
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        return_fee = number_utils.get_integer(row['RefundFee'])
        massage_fee = charge_utils.get_traditional_health_care_fee_from_case(
            self.database, self.case_key, ins_type=ins_type)
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

        total_fee = string_utils.xstr(regist_fee + diag_share_fee + deposit_fee - return_fee + massage_fee)

        medical_record = dict()
        medical_record['patient_key'] = string_utils.xstr(row['PatientKey'])
        medical_record['patient_name'] = string_utils.xstr(row['Name'])
        medical_record['birthday'] = string_utils.xstr(row['Birthday'])
        medical_record['registration_no'] = string_utils.xstr(row['RegistNo'])
        medical_record['share'] = string_utils.xstr(row['Share'])
        medical_record['regist_type'] = string_utils.xstr(row['RegistType'])
        medical_record['room'] = string_utils.xstr(row['Room'])
        medical_record['massager'] = string_utils.xstr(row['Massager'])
        medical_record['visit'] = string_utils.xstr(row['Visit'])
        medical_record['ins_type'] = ins_type
        medical_record['discount_type'] = string_utils.xstr(row['DiscountType'])
        medical_record['registrar'] = string_utils.xstr(row['Register'])

        medical_record['clinic_name'] = clinic_name
        medical_record['clinic_telephone'] = clinic_telephone
        medical_record['clinic_address'] = clinic_address
        medical_record['case_date'] = case_date
        medical_record['case_time'] = case_time
        medical_record['card'] = card
        medical_record['regist_fee'] = regist_fee
        medical_record['diag_share_fee'] = diag_share_fee
        medical_record['deposit_fee'] = deposit_fee
        medical_record['return_fee'] = return_fee
        medical_record['total_fee'] = total_fee
        medical_record['return_card_note'] = return_card_note
        medical_record['massage_fee'] = massage_fee

        return medical_record

    def print_painter(self):
        medical_record = self._get_medical_record()
        if medical_record is None:
            return

        self.printer.setPaperSize(QtCore.QSizeF(5, 5.5), QPrinter.Inch)

        if sys.platform == 'win32':
            row_no = [80, 174, 206, 238, 270, 302, 334, 360, 396, 420, 440, 460]
            col_no = [126, 340]
        else:
            row_no = [80, 174, 206, 238, 270, 302, 334, 360, 396, 420, 440, 460]
            col_no = [126, 340]

        diag_share_fee = number_utils.get_integer(medical_record['diag_share_fee'])
        regist_fee = number_utils.get_integer(medical_record['regist_fee'])

        painter = QtGui.QPainter()
        painter.begin(self.printer)

        font = QtGui.QFont(self.font_name, 15, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[0]+30, row_no[0], medical_record['clinic_name'])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[0], row_no[1], medical_record['patient_key'])
        painter.drawText(col_no[1], row_no[1], medical_record['case_date'])

        painter.drawText(col_no[0], row_no[2], medical_record['patient_name'])
        painter.drawText(col_no[1], row_no[2], medical_record['case_time'])

        painter.drawText(col_no[0], row_no[3], medical_record['visit'])
        painter.drawText(col_no[1], row_no[3], '中醫科')

        painter.drawText(col_no[0], row_no[4], medical_record['ins_type'])

        font = QtGui.QFont(self.font_name, 18, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[1]+20, row_no[4], medical_record['room'])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[0], row_no[5], medical_record['card'])

        font = QtGui.QFont(self.font_name, 18, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[1]+20, row_no[5], medical_record['registration_no'])

        font = QtGui.QFont(self.font_name, 12, QtGui.QFont.PreferQuality)
        painter.setFont(font)
        painter.drawText(col_no[0], row_no[6], medical_record['registrar'])
        painter.drawText(col_no[1], row_no[6], string_utils.xstr(regist_fee))

        painter.drawText(col_no[1]-77, row_no[7], f"門診負擔: {diag_share_fee} 元")
        painter.drawText(
            col_no[0]-77, row_no[7], f"病患生日: {date_utils.date_to_zh_tw_date(medical_record['birthday'])}")

        deposit_fee = medical_record['deposit_fee']
        if deposit_fee > 0:
            painter.drawText(col_no[0]-48, row_no[8], f"欠卡費: {deposit_fee}")

        painter.drawText(col_no[0]-48, row_no[9], f"電話: {medical_record['clinic_telephone']}")
        painter.drawText(col_no[0]-48, row_no[10], f"院址: {medical_record['clinic_address']}")

        if medical_record['card'] == '欠卡':
            painter.drawText(col_no[0]-48, row_no[11], "欠卡請於十日內還卡，謝謝")

        # return_fee = medical_record['return_fee']
        # painter.drawText(270, lines[2], string_utils.xstr(deposit_fee - return_fee))

        # font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        # painter.setFont(font)
        # painter.drawText(330, lines[2], medical_record['case_date'])

        # font = QtGui.QFont(self.font_name, 10, QtGui.QFont.PreferQuality)
        # painter.setFont(font)
        # painter.drawText(100, lines[3], f"卡序:{medical_record['card']}")
        # painter.drawText(200, lines[3], f"門診負擔:{medical_record['diag_share_fee']}")
        # painter.drawText(300, lines[3], f"自費:{medical_record['massage_fee']}")

        # painter.drawText(30, lines[4], f"經手人:{medical_record['registrar']}")
        # painter.drawText(200, lines[4], f"合計金額:{medical_record['total_fee']}")

        # massager = medical_record['massager']
        # if massager not in ['', None]:
        #     painter.drawText(300, lines[4], f"推拿師:{medical_record['massager']}")

        painter.end()

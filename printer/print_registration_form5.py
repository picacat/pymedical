
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import datetime

from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils
from libs import date_utils
from libs import case_utils


# 掛號收據格式5 3"套表掛號單 (明醫)
# 2019.07.04
class PrintRegistrationForm5:
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
        font = system_utils.get_font(self.system_settings)
        self.font = QtGui.QFont(font, 30, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def print(self, return_card=None):
        self.return_card = return_card
        self.print_html(True)
        # database.print_painter()

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(5, 3), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing, return_card=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(3.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT
                cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.RegistNo, cases.Room,
                wait.Doctor, cases.InsType, cases.Share, cases.Card, cases.Continuance,
                cases.RegistFee, cases.SDiagShareFee, cases.DepositFee,
                patient.DiscountType
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
                LEFT JOIN wait ON wait.CaseKey = cases.CaseKey
            WHERE
                cases.CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        if self.system_settings.field('列印院所名稱') == 'Y':
            clinic_name = self.system_settings.field('院所名稱').split('中醫')[0]
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
        font_size = 13

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

        patient_key = string_utils.xstr(row['PatientKey'])
        patient_name = string_utils.xstr(row['Name'])
        registration_no = string_utils.xstr(row['RegistNo'])
        # room = string_utils.xstr(row['Room'])
        doctor = string_utils.xstr(row['Doctor'])
        discount_type = string_utils.xstr(row['DiscountType'])
        ins_type = string_utils.xstr(row['InsType'])
        total_fee = string_utils.xstr(regist_fee + diag_share_fee + deposit_fee)
        share = string_utils.xstr(row['Share'])

        html = f'''
            <html>
            <body>
                <p style="font-size:18px">
                    &nbsp; &nbsp;
                    <b>{clinic_name}</b>
                </p>
                <table cellspacing=0 cellpadding=6>
                    <tr>
                        <td width="18%" style="font-size: {font_size}px; text-align: left">
                        </td>
                        <td width="30%" style="font-size: 15px; text-align: left">
                            {patient_name}
                        </td>
                        <td width="30%" style="font-size: 18px; text-align: left">
                            <b>{registration_no}</b>
                        </td>
                        <td width="30%" style="font-size: 14px; text-align: left">
                            {doctor}
                        </td>
                    </tr>
                    <tr>
                        <td width="20%" style="font-size: {font_size}px; text-align: left">
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {patient_key}
                        </td>
                        <td width="30%" style="font-size: 11px; text-align: left">
                            {case_date}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {case_time}
                        </td>
                    </tr>
                    <tr>
                        <td width="20%" style="font-size: {font_size}px; text-align: left">
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {share}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {discount_type}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {card}
                        </td>
                    </tr>
                    <tr>
                        <td width="20%" style="font-size: {font_size}px; text-align: left">
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {regist_fee}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {diag_share_fee}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {deposit_fee}
                        </td>
                    </tr>
                    <tr>
                        <td width="20%" style="font-size: {font_size}px; text-align: left">
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {total_fee}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {ins_type}
                        </td>
                        <td width="30%" style="font-size: {font_size}px; text-align: left">
                            {return_card_note}
                        </td>
                    </tr>
                </table>
                <br>
            </body>
            </html>
        '''

        return html

# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils
from libs import registration_utils


# 掛號收據格式12 2.5"套表掛號單
# 使用診所: 佳禾系列
# 2021.11.03
class PrintRegistrationForm12:
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
        self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)

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
        self.printer.setPaperSize(QtCore.QSizeF(5, 2.5), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing, return_card=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(5, 2.5), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        row = self.database.select_record(sql)[0]

        card = string_utils.xstr(row['Card'])
        deposit_hint = ''
        if card == '欠卡':
            return_card_days = registration_utils.get_return_card_days(self.system_settings)
            deposit_hint = f'請於{return_card_days}日內還卡'

        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])

        if self.system_settings.field('列印院所名稱') == 'Y':
            clinic_name = self.system_settings.field('院所名稱')
        else:
            clinic_name = ''

        # clinic_telephone = self.system_settings.field('院所電話')
        patient_key = string_utils.xstr(row['PatientKey'])
        patient_name = string_utils.xstr(row['Name'])
        registration_no = string_utils.xstr(row['RegistNo'])
        room = string_utils.xstr(row['Room'])
        doctor = string_utils.xstr(row['Doctor'])
        ins_type = string_utils.xstr(row['InsType'])
        case_date = string_utils.xstr(row['CaseDate'].date())
        case_time = string_utils.xstr(row['CaseDate'].time())[:5]
        # share = string_utils.xstr(row['Share'])
        # period = string_utils.xstr(row['Period'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])

        html = f'''
            <html>
                <body>
                    <p style="font-size:16px"><b>{clinic_name}</b></p>
                    <table style="margin-left:28px" cellspacing=16 cellpadding=0>
                        <tr>
                            <td width="30%" style="font-size: 16px; text-align: center">
                                {patient_name}
                            </td>
                            <td width="50%" style="font-size: 16px; text-align: center">
                            </td>
                            <td width="30%" style="font-size: 16px; text-align: left">
                                <b>{room}</br>
                            </td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">{patient_key}</td>
                            <td width="40%" style="text-align:center">{regist_fee}</td>
                            <td width="30%" style="text-align:left">{registration_no}</td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align:center">{case_date}</td>
                            <td width="40%" style="text-align:center">{diag_share_fee}</td>
                            <td width="30%" style="text-align:left">{doctor}</td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">{case_time}</td>
                            <td width="40%" style="text-align:center">{deposit_fee}</td>
                            <td width="30%" style="text-align:left">{card}</td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">{ins_type}</td>
                            <td width="40%" style="text-align:center">
                                {regist_fee + diag_share_fee + deposit_fee}
                            </td>
                            <td width="30%" style="text-align:left">{deposit_hint}</td>
                        </tr>
                    </table>
                </body>
            </html>
        '''

        return html

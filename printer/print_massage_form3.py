
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號收據格式1 80mm * 80mm 熱感紙
# 2018.07.09
class PrintMassageForm3:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        try:
            self.printer = args[3]
        except Exception:
            self.printer = printer_utils.get_printer(self.system_settings, '民俗調理單印表機')

        self.ui = None

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

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _get_case_row(self, case_key):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        row = self.database.select_record(sql)[0]

        if string_utils.xstr(row['TreatType']) != '民俗調理':
            sql = f'''
                SELECT * FROM cases
                WHERE
                    Position1 = {case_key}
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return

            row = rows[0]

        return row

    def _html(self):
        row = self._get_case_row(self.case_key)

        card = string_utils.xstr(row['Card'])
        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate']
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        room = number_utils.get_integer(row['Room'])
        regist_no = number_utils.get_integer(row['RegistNo'])

        massager = string_utils.xstr(row['Massager'])
        massage_fee = number_utils.get_integer(row['SMassageFee'])

        html = f'''
            <html>
            <body>
                <center style="font-size:18px"><b>民俗調理單</b></center>
                <div style="margin-left:20px; font-size: 18px">
                掛號日期: {case_date.date()}<br>
                掛號時間: {case_date.strftime('%H:%M')}<br>
                病患姓名: {patient_key:0>6} - {name}<br>
                推拿師父: {massager}<br>
                民俗調理費: {massage_fee}<br>
                </div>
                <center style="font-size:48px">{regist_no:0>3}號</b></center>
            </body>
            </html>
        '''

        return html

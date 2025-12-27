
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號收據格式2 11"中二刀空白掛號單
# 2018.07.09
class PrintRegistrationForm2:
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
        self.printer.setPaperSize(QtCore.QSizeF(241, 93), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(241, 93), QPrinter.Millimeter)

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
        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])
        total_amount = (number_utils.get_integer(row['RegistFee']) +
                        number_utils.get_integer(row['SDiagShareFee']) +
                        number_utils.get_integer(row['DepositFee']))

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate']
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        ins_type = string_utils.xstr(row['InsType'])
        share = string_utils.xstr(row['Share'])
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        registrar = string_utils.xstr(row['Register'])
        room = number_utils.get_integer(row['Room'])
        regist_no = number_utils.get_integer(row['RegistNo'])

        html = f'''
            <html>
            <body>
                <p style="font-size:24px"><b>{clinic_name} 門診掛號單</b></p>
                <table cellspacing=0 cellpadding=8
                 style="border-width:1px; border-style: solid; border-color: darkgrey">
                    <tr>
                        <td>掛號時間</td><td>{case_date}</td>
                        <td>病患姓名</td><td>{patient_key:0>6}-{name}</td>
                        <td>保險類別</td><td>{ins_type}-{share}</td>
                    </tr>
                    <tr>
                        <td>健保卡序</td><td>{card}</td>
                        <td>掛號費</td><td style="text-align:right">{regist_fee}元</td>
                        <td>門診負擔</td><td style="text-align:right">{diag_share_fee}元</td>
                    </tr>
                    <tr>
                     <td>欠卡費</td><td style="text-align:right">{deposit_fee}元</td>
                     <td>實收金額</td><td style="text-align:right">{total_amount}元</td>
                     <td>經手人</td><td>{registrar}</td>
                    </tr>
                    <tr>
                        <td>診療室</td><td><center style="font-size:28px"><b>{room}診</b></center></td>
                        <td>就診號碼</td><td><center style="font-size:28px"><b>{regist_no:0>3}號</b></center></td>
                        <td>蓋章</td>
                    </tr>
                </table>
                本單據僅供看診叫號使用，不作報稅證明用途<br>
            </body>
            </html>
        '''

        return html

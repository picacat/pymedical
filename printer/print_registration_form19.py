
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號收據格式19 80mm 熱感紙 人形圖
# 2023.11.24
class PrintRegistrationForm19:
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

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(2.5, 3), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(2.5, 5.8), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
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

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate']
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        total_fee = regist_fee + diag_share_fee + deposit_fee

        room = string_utils.xstr(row['Room'])
        doctor = string_utils.xstr(row['Doctor'])
        regist_no = string_utils.xstr(row['RegistNo'])

        if card == '欠卡':
            total_label = f'<br>欠卡費: {str(deposit_fee)}元 實收金額: {str(total_fee)}元'
        else:
            total_label = f'<br>實收金額: {str(total_fee)}元'

        html = f'''
            <html>
                <body>
                    <center style="font-size:16px"><b>{clinic_name}</b></center>
                    <center style="font-size:16px"><b>門診掛號單</b></center>
                    病患姓名: {name}<br>
                    掛號時間: {case_date}<br>
                    保險類別: {ins_type} - {treat_type}<br>
                    掛號費: {str(regist_fee)}元 門診負擔: {str(diag_share_fee)}元
                    {total_label}
                    <center style="font-size:20px">{room}診 {doctor}醫師</b></center>
                    <center style="font-size:20px">{regist_no:0>3}號</b></center>
                    <center>本單據僅供叫號，不作報稅證明</center>
                    <br><br>
                    <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="1">
                        <tr>
                            <td>熏蒸</td>
                            <td>傷科</td>
                            <td>針灸</td>
                            <td>電針</td>
                            <td>滑罐</td>
                            <td>電療</td>
                            <td>藥膏</td>
                        </tr>
                        <tr>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                        </tr>
                    </table>
                    <img src="{'./images/physical.jpg'}" height="200" width="200">
                </body>
            </html>
        '''

        return html

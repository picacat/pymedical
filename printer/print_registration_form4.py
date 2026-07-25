
# -*- coding: UTF-8 -*-

from libs import (charge_utils, number_utils, printer_utils, string_utils,
                  system_utils)
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter


# 掛號收據格式4 80mm 熱感紙 誠泰
# 2019.05.06
class PrintRegistrationForm4:
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
        self.printer.setPaperSize(QtCore.QSizeF(2.5, 3), QPrinter.Inch)

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
        massager = string_utils.xstr(row['Massager'])
        regist_no = string_utils.xstr(row['RegistNo'])
        massage_fee = charge_utils.get_traditional_health_care_fee_from_case(
            self.database, self.case_key, ins_type=ins_type)

        if massage_fee > 0:
            total_label = f'''
                <br>民俗調理: {str(massage_fee)}元 推拿師父: {massager}<br>
                實收金額: {str(total_fee + massage_fee)}元
            '''
        elif card == '欠卡':
            total_label = f'<br>欠卡費: {str(deposit_fee)}元 實收金額: {str(total_fee)}元'
        else:
            total_label = f'<br>實收金額: {str(total_fee)}元'

        html = f'''
            <html>
                <body>
                    <center style="font-size:20px"><b>{clinic_name}</b></center>
                    <center style="font-size:18px"><b>門診掛號單</b></center>
                    <div style="font-weight:900"><b>
                    姓名: <b style="font-size: 18px">{patient_key:0>6}-{name}</b><br>
                    日期: {case_date}<br>
                    保險: {ins_type} - {treat_type}<br>
                    掛號費: {str(regist_fee)}元 門診負擔: {str(diag_share_fee)}元
                    {total_label}
                    <center style="font-size:24px">{room}診 {doctor}醫師</b></center>
                    <center style="font-size:36px">{regist_no:0>3}號</b></center>
                    </b></div>        
                </body>
            </html>
        '''

        return html

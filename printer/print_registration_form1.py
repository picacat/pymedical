
# -*- coding: utf-8 -*-

from libs import number_utils, printer_utils, string_utils, system_utils
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter


# 掛號收據格式1 80mm * 80mm 熱感紙
# 2018.07.09
class PrintRegistrationForm1:
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
            if self.system_settings.field('加印一張掛號單') == 'Y':
                document.print(self.printer)
                
    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        row = self.database.select_record(sql)[0]

        card = string_utils.xstr(row['Card'])
        course = number_utils.get_integer(row['Continuance'])
        if course >= 1:
            card += '-' + string_utils.xstr(course)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
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
        
        sequence_html = f'''
            <center style="font-size:48px"><b>{room}診 {regist_no:0>3}號</b></center>
            <center style="font-size:12px">本收據可為報稅憑證<br>請妥善保存，遺失恕不補發。</center>
        '''
        
        if clinic_name == '祐康中醫診所':
            sequence_html = f'''
            <br><br>
            電話: {clinic_telephone}<br>
            地址: {clinic_address}<br>
            本收據可為報稅憑證，請妥善保存，遺失恕不補發。<br>            
            '''
            if treat_type not in ['內科'] and course >= 2:
                treat_type = '傷科'


        html = f'''
            <html>
            <body>
                <center style="font-size:20px"><b>{clinic_name}</b></center>
                <center style="font-size:20px"><b>門診掛號收據</b></center>
                <div style="margin-left:22px; font-weight:900">
                <b>
                掛號時間: {case_date}<br>
                病患姓名: {patient_key:0>6} - {name}<br>
                保險類別: {ins_type} - {treat_type}<br>
                健保卡序: {card}<br>
                掛號費: {regist_fee} 門診負擔: {diag_share_fee} 欠卡費: {deposit_fee}
                </b>
                {sequence_html}        
                </div>
            </body>
            </html>
        '''

        return html

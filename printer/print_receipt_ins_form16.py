
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import datetime

from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號機批價收據格式16 80mm * 80mm 熱感紙 板橋新生堂
# 2022.11.30
class PrintReceiptInsForm16:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '健保醫療收據印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

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
        self.font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 95)

    def _set_signal(self):
        pass

    def print(self, print_additional=None):
        if print_additional is not None:  # 排除printer_utils 的健保另包選項
            return

        self.print_html(True)

    def preview(self, print_additional=None):
        if print_additional is not None:
            return

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        self.current_print = self.print_painter
        # self.printer.setPaperSize(QtCore.QSizeF(57, 80), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 57, 80, QPrinter.Millimeter, '健保醫療收據')

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(56, 80), QPrinter.Millimeter)

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

        clinic_name = self.system_settings.field('院所名稱')
        clinic_telephone = self.system_settings.field('院所電話')
        name = string_utils.xstr(row['Name'])
        doctor = string_utils.xstr(row['Doctor'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        self_total_fee = number_utils.get_integer(row['TotalFee'])
        self_treat_fee = (
            number_utils.get_integer(row['SAcupunctureFee']) +
            number_utils.get_integer(row['SMassageFee']) +
            number_utils.get_integer(row['SDislocateFee'])
        )
        self_drug_fee = self_total_fee - self_treat_fee
        total_fee = drug_share_fee + self_total_fee

        date = datetime.datetime.now().strftime("%Y-%m-%d")
        time = datetime.datetime.now().strftime("%H:%M:%S")
        drug_no = number_utils.get_integer(row['DrugNo'])
        if drug_no > 0:
            drug_no_str = f'領藥號碼: <font size="12">{drug_no:0>3}</font><br>'
        else:
            drug_no_str = ''

        html = f'''
            <html>
            <body>
                <center style="font-size:14px"><b>繳費證明單</b></center>
                <div style="margin-left:0">
                {drug_no_str}
                病患姓名: <font size="12">{name}</font><br>
                健保藥費: {drug_share_fee}<br>
                自費藥費: {self_drug_fee}<br>
                自費處置: {self_treat_fee}<br>
                總收款額: {total_fee}<br>
                主治醫師: {doctor}<br>
                列印日期: {date}<br>
                列印時間: {time}<br>
                {clinic_name}<br>
                {clinic_telephone}<br>
                </div>
                領藥時請將此單交付櫃台<br>
                如需針灸請持單至針灸區
            </body>
            </html>
        '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號機批價收據格式13 80mm * 80mm 熱感紙
# 2021.12.27
class PrintReceiptInsForm13:
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
        # self.printer.setPaperSize(QtCore.QSizeF(80, 60), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 80, 60, QPrinter.Millimeter, '健保醫療收據')

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

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        row = self.database.select_record(sql)[0]

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate'].date()
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        self_total_fee = number_utils.get_integer(row['TotalFee'])
        total_fee = drug_share_fee + self_total_fee

        html = f'''
            <html>
            <body>
                <center style="font-size:20px"><b>{clinic_name}</b></center>
                <center style="font-size:18px"><b>批價證明單</b></center>
                <div style="margin-left:20px">
                門診日期: {case_date}<br>
                病患姓名: {patient_key:0>6} - {name}<br>
                藥品負擔: {drug_share_fee} 自費金額: {self_total_fee}<br>
                合計金額: {total_fee}
                </div>
                <center style="font-size:12px">本單據僅供繳費證明，不作報稅用途</center>
            </body>
            </html>
        '''

        return html

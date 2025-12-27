
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

import datetime

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import charge_utils


# 領藥單 80mm 熱感紙
# 2025.07.11 仁聿
class PrintMiscForm30:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.printer = args[3]
        self.ui = None

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

    def print(self):
        self.print_html(True)

    def preview(self):
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(4.4, 4.0), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 90, QPrinter.Millimeter, '健保醫療收據')

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

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate'].date()
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        name = string_utils.remove_not_chinese_character(name)
        drug_no = string_utils.xstr(row['DrugNo'])

        html = f'''
            <html>
                <body>
                    <b>
                    <center style="font-size:20px">{clinic_name}</center>
                    <center style="font-size:32px">領藥單</center>
                    <div style="font-size: 20px; margin-left: 20;">
                        姓名: {patient_key:0>6}-{name}<br>
                        日期: {case_date}
                    </div>
                    <br>
                    <div align="center">
                    <center style="font-size:32px">領藥號</center>
                    <center style="font-size:64px; font-weight:900;"><b>{drug_no:0>3}</b></center>
                    </div>
                    </b>
                </body>
            </html>
        '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import date_utils


# 就醫證明 80mm * 80mm 熱感紙
# 2025.07.16 林胤骨
class PrintMedicalFees:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
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
        self.font = QtGui.QFont(font, 12, QtGui.QFont.PreferQuality)

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
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 148, QPrinter.Millimeter)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT Name, PatientKey, CaseDate, Doctor FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        name = string_utils.xstr(row['Name'])
        patient_key = string_utils.xstr(row['PatientKey'])

        case_date = string_utils.xstr(row['CaseDate'].date())
        case_date = date_utils.date_to_zh_tw_date(case_date)
        case_year = string_utils.xstr(row['CaseDate'].date().year-1911)
        case_month = string_utils.xstr(row['CaseDate'].date().month)
        case_day = string_utils.xstr(row['CaseDate'].date().day)

        doctor = string_utils.xstr(row['Doctor'])

        html = f'''
            <html>
              <body style="margin-left: 20; margin-right: 20;">
                <center>
                    <font size="4"><b>{clinic_name}</b></font><br>
                    <font size="1">代號:{clinic_id}<br>
                    電話:{clinic_telephone}<br>
                    {clinic_address}<br></font>
                    <br>
                    <b><u>就醫證明書</u></b>
                </center>
                <p><b>
                    茲證明 {name} 病歷號碼{patient_key:0>6}，於{case_year}年{case_month}月{case_day}日，在{clinic_name}就醫。
                </b></p>
                <p style="margin-right: 10; text-align: right"><b>診治醫師 {doctor}</b></p>
                <center><b>中華民國{case_year}年{case_month}月{case_day}日</b></center>
              </body>
            </html>
        '''

        return html

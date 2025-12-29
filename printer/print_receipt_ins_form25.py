
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys
import datetime

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils


# 健保收據格式25 60mm 掛號機熱感紙 悅兒掛號機
# 2024.10.13
class PrintReceiptInsForm25:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.medicine_set = 1

        self.printer = printer_utils.get_printer(self.system_settings, '健保醫療收據印表機')

        self.current_print = None
        self.additional = None

        if sys.platform == 'darwin':
            dash_count = 34
        else:
            dash_count = 37

        self.dash_line = '-' * dash_count

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

    def _check_printing(self):
        printing = True

        if self.additional == '健保另包':
            if printer_utils.is_additional_prescript(self.database, self.case_key):
                printing = True
            else:
                printing = False

        return printing

    def print(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        self.print_html(True)

    def preview(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        preview_dialog.paintRequested.connect(self.print_html)
        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(74, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 60, 90, QPrinter.Millimeter, '健保醫療收據')

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
        now = datetime.datetime.now()
        case_date = now.strftime('%Y-%m-%d')
        case_time = now.strftime('%H:%M')
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        room = number_utils.get_integer(row['Room'])
        regist_no = number_utils.get_integer(row['RegistNo'])
        receipt_fee = regist_fee + diag_share_fee + drug_share_fee + total_fee
        prescript_sign = case_utils.extract_security_xml(row['Security'], '醫令時間')

        drug_no = number_utils.get_integer(row['DrugNo'])

        if drug_no > 0:
            drug_no_str = f'領藥號:{drug_no}<br>'
        else:
            drug_no_str = ''

        if prescript_sign is not None:
            ic_wrote = '是'
        else:
            ic_wrote = '否'

        html = f'''
            <html>
            <body>
                <b style="font-size:20px">{clinic_name}</b><br>
                <b style="font-size:18px">繳費完成憑證</b>
                <br>
                <div style="margin-left:0px; font-size: 15px">
                病歷號碼:{patient_key}<br>
                病患姓名:{name}<br>
                繳費日期:{case_date}<br>
                繳費時間:{case_time}<br>
                繳費金額:{receipt_fee}<br>
                寫卡狀態:{ic_wrote}<br>
                {drug_no_str}
                </div>
                <br>
                繳費完成請等候櫃台通知領藥<br>請將此憑證交給櫃台人員
            </body>
            </html>
        '''

        return html

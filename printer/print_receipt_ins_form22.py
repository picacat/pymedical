
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils
from libs import string_utils


# 健保收據格式6 A6: 105x148mm 天地精進
# 2023.12.29
class PrintReceiptInsForm22:
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
        # self.printer.setPaperSize(QtCore.QSizeF(105, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 105, 148, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(10)
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        ins_type = string_utils.xstr(row['InsType'])
        case_record = printer_utils.get_case_html_10(
            self.database, self.case_key, '健保', medicine_set=1, tw_date=True
        )
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html7(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=1, instruction=self.additional,
            print_total_dosage='Y')
        instruction = printer_utils.get_instruction_html4(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fee_html = printer_utils.get_ins_fees_html_22(self.database, self.case_key)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        html = f'''
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left" colspan="4" padding="2">
                        {clinic_name}({clinic_id}) 醫療費用收據
                      </th>
                    </tr>
                    <tr>
                      <th style="text-align: left; font-size: 12px" colspan="4">
                        電話:{clinic_telephone} 院址:{clinic_address}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                  </tbody>
                </table>
                <table width="100%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <br>
                <table width="100%" style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="2" border="1">
                  <thead>
                    <tr>
                      <th align="left" width="20%">位置</th>
                      <th align="left">處方名稱</th>
                      <th align="right" width="15%">劑量</th>
                      <th align="right" width="15%">總量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                {instruction}
                {additional_label}
                <hr>
                {fee_html}
                <br><br>
                收款人: {string_utils.xstr(row["Doctor"])}<br>
                適應症: {disease_name} 警語: 請勿與其它藥品混合服用<br>
                副作用: 本處方於醫學文獻中尚無副作用之記載<br>
                * 請妥善保存，遺失恕不補發<br>
                * 健保申報點數非一點一元給付
              </body>
            </html>
        '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys
import datetime

from libs import printer_utils
from libs import system_utils
from libs import case_utils


# 自費處方箋格式9 熱感80mm
# 2025.06.02
class PrintPrescriptionSelfForm9:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '自費處方箋印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)

        self.current_print = None

        if sys.platform == 'darwin':
            dash_count = 34
        else:
            dash_count = 42

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
        # self.printer.setPaperSize(QtCore.QSizeF(72, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 72, 148, QPrinter.Millimeter, '自費醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _get_fees_html(self):
        fees_record = printer_utils.get_self_fees_html_2(self.database, self.case_key, width=5)

        html = f'''
          <table width="100%" cellspacing="0">
            <tbody>
              {fees_record}
            </tbody>
          </table>
        '''

        if self.medicine_set is None or self.medicine_set >= 3:
            html = f'{self.dash_line}<br>'

        return html

    def _html(self):
        case_record = printer_utils.get_case_html_2_1(self.database, self.case_key, '自費')
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=1, print_total_dosage='Y')
        fees_record = self._get_fees_html()
        instruction = printer_utils.get_instruction_html_0(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)
        time = datetime.datetime.now().strftime('%H:%M:%S')

        if self.system_settings.field('處方箋不印費用明細') == 'Y':
            fees_record = ''

        prescript_html = f'''
            <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="2" border="1">
              <thead>
                <tr>
                  <th align="left">處方名稱</th>
                  <th align="right">劑量</th>
                  <th align="right">總量</th>
                </tr>
              </thead>
              <tbody>
                {prescript_record}
              </tbody>
            </table>
            <table width="100%">
              <tr>
                <td align="left">{instruction}</td>
                <td align="right">[{time}]</td>
              </tr>
            </table>
            {fees_record}
        '''

        if self.medicine_set is None:
            prescript_html = '無處方'

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')


        html = f'''
            <html>
              <body>
                <b>
                <table width="98%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: center" colspan="2">
                        <center>{clinic_name}<center>
                        <center>藥品處方箋<center>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                {prescript_html}
                </b>
              </body>
            </html>
        '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys

from libs import printer_utils
from libs import system_utils
from libs import case_utils


# 健保收據格式26 60mm 熱感紙(有框)
# 2025.01.20
class PrintReceiptInsForm26:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.medicine_set = 1

        self.printer = printer_utils.get_printer(self.system_settings, '健保醫療收據印表機')
        self.note_printer = printer_utils.get_printer(self.system_settings, '健保醫療收據印表機')
        self.second_printer = printer_utils.get_printer(self.system_settings, '門診掛號單印表機')

        self.current_print = None
        self.additional = None

        if sys.platform == 'darwin':
            dash_count = 34
        else:
            dash_count = 39

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
        self.font = QtGui.QFont(font, 9, QtGui.QFont.PreferQuality)

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
        if self.additional == '補退掛號費用':
            self.print_note_html()
            return

        if not self._check_printing():
            return

        self.print_html(True)

    def preview(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        if self.additional == '補退掛號費用':
            print_event = self.print_note_html
        else:
            print_event = self.print_html

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        preview_dialog.paintRequested.connect(print_event)
        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(74, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 58, 168, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)
            if self.system_settings.field('健保費用收據同時輸出至掛號印表機') == 'Y':
                self.print_second_html()

    def print_note_html(self):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(74, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 58, 40, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._note_html())
        printer_utils.set_document_line_height(document, 14)
        document.print(self.printer)

    def print_second_html(self):
        printer_utils.set_paper_size(self.second_printer, self.system_settings, 58, 168, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.second_printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        document.print(self.second_printer)

    def _html(self):
        case_record = printer_utils.get_case_html_23(
            self.database, self.case_key, '健保', tw_date=True
        )
        prescript_record = printer_utils.get_prescript_html23(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=1,
            instruction=self.additional, print_total_dosage='Y', print_treat_item=False)
        instruction = printer_utils.get_instruction_html_0(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fees_record = printer_utils.get_ins_fees_html_23(self.database, self.case_key)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)
        if pres_days > 0:
            warning = '<br>警語:本藥品無其他副作用'
        else:
            warning = '<br>'

        tax_hint = '本收據可為報稅憑證, 遺失恕不補發'
        if self.system_settings.field('不印報稅提示') == 'Y':
          tax_hint = ''

        if self.system_settings.field('列印條碼') == 'Y':
            barcode_string = f'case{self.case_key:0>8}{self.medicine_set:0>8}'
            barcode = printer_utils.get_barcode(barcode_string)
            qrcode = system_utils.get_qrcode_b64png(barcode_string)
            qrcode_html = f'''
              <br><br><br><br><br><br>
              <img src="data:;base64,{qrcode}" alt="" height="80" width="80">
            '''
            title_html = f'''
              <table>
                <tr>
                  <td width="20%">{qrcode_html}</td>
                  <td width="78%">
                  <br><br>
                  <center>{clinic_name}</center>
                  <center>醫療費用收據</center>
                  </td>
                </tr>
              </table>
            '''
        else:
            qrcode_html = ''
            title_html = f'''
              <table>
                <tr>
                <td width="30%"></td>
                <td>
                  <center>{clinic_name}</center>
                  <center>醫療費用收據</center>
                </td>
                </tr>
              </table>
              <br>
            '''

        html = f'''
            <html>
              <body>
                <b>
                {title_html}
                <table width="97%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                適應症:{disease_name}
                <table width="94%" style="border-collapse: collapse; border:1px #cccccc solid;" 
                  cellspacing="0" cellpadding="0" border="1">
                  <thead>
                    <tr>
                      <th align="center">序</th>
                      <th align="left">處方名稱</th>
                      <th align="right">劑量</th>
                      <th align="right">總量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <br><br>{instruction}
                {additional_label}
                {warning}
                {self.dash_line}
                <table width="94%" cellspacing="0" cellpadding="0" style="font-size: 11px">
                  <tbody>
                    {fees_record}
                  </tbody>
                </table>
                {tax_hint}
                {self.dash_line}<br>
                代號:{clinic_id}<br>
                {clinic_address}<br>
                {clinic_telephone}
              </b>
              </body>
            </html>
        '''

        return html

    def _note_html(self):
        note = case_utils.get_case_extend(self.database, self.case_key, '掛號費用')
        note = note.replace('\n', '<br>')

        html = f'''
            <html>
              <br>
              <center><b>掛號費補退提醒</b></center>
              <body style="font-size: 12px">
                <br>
                {note}
              </body>
            </html>
        '''

        return html

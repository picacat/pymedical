
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys

from libs import printer_utils
from libs import system_utils
from libs import case_utils


# 健保收據格式24 80mm 熱感紙(橫印) 專嘉
# 2025.07.04
class PrintReceiptInsForm28:
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
        self.font = QtGui.QFont(font, 11, QtGui.QFont.PreferQuality)

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
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 188, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 15)
        if printing:
            printer_utils.rotate_document(self.printer, document, 80, 500)
            # document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_24(
            self.database, self.system_settings, self.case_key, '健保', tw_date=True
        )
        prescript_html, _ = printer_utils.get_prescript_html24(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=1,
            instruction=self.additional, print_total_dosage='Y', print_treat_item=False, td_width=250)
        instruction = printer_utils.get_instruction_html_0(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fees_record = printer_utils.get_ins_fees_html_24(self.database, self.case_key)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)
        if pres_days > 0:
            warning = '''
                警語:請置於兒童不易取得處<br>
                副作用: 本處方用藥在醫學文獻上尚無副作用之記載<br>
                保存方式: 置於乾燥陰涼處<br>
                保存期限: 三個月
            '''
        else:
            warning = ''

        receipt_title_image = printer_utils.get_title_image(
            clinic_name, clinic_id, clinic_telephone, clinic_address)

        if self.system_settings.field('不印報稅提示') == 'Y':
            tax_hint = ''
        else:
            tax_hint = self.system_settings.field('醫療費用收據自訂報稅備註')
            if tax_hint in ['', None]:
              tax_hint = '本收據可為報稅憑證, 遺失恕不補發'

        if self.system_settings.field('費用收據不印處方') == 'Y':
            prescript_html = ''

        html = f'''
            <html>
              <body>
                <b>
                <br>
                <table width="100%" cellspacing="10">
                  <tbody>
                    <tr>
                        <td width="350">
                            {case_record}{instruction}{additional_label}
                            <br>適應症:{disease_name}<br>{warning}
                        </td>
                        {prescript_html}
                        <td width="350">
                            {fees_record}
                            {tax_hint}<br><br>
                            院所電話: {clinic_telephone}<br>
                            院所地址: {clinic_address}
                        </td>
                    </tr>
                  </tbody>
                </table>
              </b>
              </body>
            </html>
        '''

        return html

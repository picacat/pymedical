
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys
from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils


# 自費收據格式14 4.5 x 3 inches 友杏格式 字體可變
# 2018.10.09
class PrintReceiptSelfForm14:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '自費醫療收據印表機')
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

        self.font = QtGui.QFont(font, 8, QtGui.QFont.PreferQuality)

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
        # self.printer.setPaperSize(QtCore.QSizeF(4.0, 3), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 4.0, 3, QPrinter.Inch, '自費醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _get_prescript_html(self, row):
        self.prescript_font_size = number_utils.get_integer(self.system_settings.field('費用收據處方欄字體大小'))

        case_record = printer_utils.get_case_html_6(
            self.database, self.case_key, '自費', self.medicine_set,
        )
        # disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html2(
            self.database, self.system_settings,
            self.case_key, self.medicine_set,
            '費用收據', blocks=2, max_line=8)
        instruction = printer_utils.get_instruction_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name1 = string_utils.xstr(row['DiseaseName1'])

        prescript_html = f'''
            <table cellspacing="0">
              <thead>
                <tr>
                  <th style="text-align: center" colspan="3">
                    <u>處方暨費用收據</u>
                  </th>
                </tr>
              </thead>
              <tbody>
                {case_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table cellspacing="0" style="font-size: {self.prescript_font_size}px">
              <tbody>
                {prescript_record}
              </tbody>
            </table>
            {instruction}
            適應症: {disease_name1}<br>
            副作用: 本處方於醫學文獻中尚無副作用之記載<br>
            院所:{clinic_id} {clinic_name}<br>
            * 本收據可為報稅之憑證, 請妥善保存, 遺失恕不補發
        '''

        return prescript_html

    @staticmethod
    def _get_self_fees_html(row):
        if string_utils.xstr(row['InsType']) == '健保':
            regist_fee = 0
        else:
            regist_fee = number_utils.get_integer(row['RegistFee'])

        diag_fee = number_utils.get_integer(row['SDiagFee'])
        drug_fee = number_utils.get_integer(row['SDrugFee'])
        herb_fee = number_utils.get_integer(row['SHerbFee'])
        expensive_fee = number_utils.get_integer(row['SExpensiveFee'])
        acupuncture_fee = number_utils.get_integer(row['SAcupunctureFee'])
        massage_fee = number_utils.get_integer(row['SMassageFee'])
        dislocate_fee = number_utils.get_integer(row['SDislocateFee'])
        material_fee = number_utils.get_integer(row['SMaterialFee'])
        exam_fee = number_utils.get_integer(row['SExamFee'])
        self_total_fee = number_utils.get_integer(row['SelfTotalFee']) + regist_fee
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        total_fee = number_utils.get_integer(row['TotalFee']) + regist_fee
        receipt_fee = number_utils.get_integer(row['ReceiptFee']) + regist_fee

        fees_html = f'''
            <table width="98%" cellspacing="0">
              <tbody>
                <tr>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td></td>
                  <td></td>
                </tr>
                <tr>
                  <td>一般藥</td>
                  <td align="right">{drug_fee}</td>
                </tr>
                <tr>
                  <td>水藥費</td>
                  <td align="right">{herb_fee}</td>
                </tr>
                <tr>
                  <td>針灸費</td>
                  <td align="right">{acupuncture_fee}</td>
                </tr>
                <tr>
                  <td>傷科費</td>
                  <td align="right">{massage_fee}</td>
                </tr>
                <tr>
                  <td>脫臼費</td>
                  <td align="right">{dislocate_fee}</td>
                </tr>
                <tr>
                  <td>材料費</td>
                  <td align="right">{material_fee}</td>
                </tr>
                <tr>
                  <td>自費額</td>
                  <td align="right">{self_total_fee}</td>
                </tr>
                <tr>
                  <td><hr></td>
                  <td align="right"><hr></td>
                </tr>
                <tr>
                  <td>應收額</td>
                  <td align="right">{total_fee}</td>
                </tr>
                <tr>
                  <td>實收額</td>
                  <td align="right">{receipt_fee}</td>
                </tr>
              </tbody>
            </table>
        '''

        return fees_html

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

        prescript_html = self._get_prescript_html(row)
        if self.medicine_set == 2:
            fees_html = self._get_self_fees_html(row)
        else:
            fees_html = ''

        html = f'''
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td width="80%">
                        {prescript_html}
                      </td>
                      <td width="20%">
                        {fees_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
        '''

        return html

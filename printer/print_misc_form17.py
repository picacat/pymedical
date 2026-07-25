
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils
from libs import number_utils
from libs import string_utils


# 健保及自費印花稅總繳收據 4.5 x 3 inches
# 2025.02.09
class PrintMiscForm17:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.printer = args[3]

        self.medicine_set = None
        self.ui = None


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

        self.font = QtGui.QFont(font, 9, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def _read_fees(self):
        ins_type, regist_fee, total_fee = None, 0, 0
        sql = f'''
            SELECT InsType, RegistFee, TotalFee FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            row = rows[0]
            ins_type = string_utils.xstr(row['InsType'])
            regist_fee = number_utils.get_integer(row['RegistFee'])
            total_fee = number_utils.get_integer(row['TotalFee'])

        return ins_type, regist_fee, total_fee

    def print(self):
        ins_type, regist_fee, total_fee = self._read_fees()
        if ins_type == '健保' and regist_fee >= 250:
            self.print_ins_html(True)

        if total_fee >= 250:
            self.print_self_html(True)

    def preview(self):
        ins_type, regist_fee, total_fee = self._read_fees()

        if ins_type == '健保' and regist_fee >= 250:
            self.preview_form(ins_type='健保')

        if total_fee >= 250:
            self.preview_form(ins_type='自費')

    def preview_form(self, ins_type='自費'):
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        if ins_type == '健保':
            preview_dialog.paintRequested.connect(self.print_ins_html)
        else:
            preview_dialog.paintRequested.connect(self.print_self_html)

        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        preview_dialog.exec_()

    def print_ins_html(self, printing=None):
        self.current_print = self.print_ins_html
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html(ins_type='健保'))
        printer_utils.set_document_line_height(document, 13)
        if printing:
            document.print(self.printer)

    def print_self_html(self, printing=None):
        self.current_print = self.print_self_html
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html(ins_type='自費'))
        printer_utils.set_document_line_height(document, 13)
        if printing:
            document.print(self.printer)

    def _get_ins_prescript_html(self, row):
        case_record = printer_utils.get_case_html_6(
            self.database, self.case_key, '健保', 1,
        )

        prescript_record = '''
            <tr>
                <td align="left" width="29%">健保掛號費</td>
                <td align="right" width="11%">1次</td>
            </tr>
        '''

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        regist_fee = number_utils.get_integer(row['RegistFee'])
        owner = self.system_settings.field('負責醫師')

        prescript_html = f'''
            <table cellspacing="0">
              <thead>
                <tr>
                  <th style="text-align: center" colspan="3">
                    <u>收據</u><br>
                  </th>
                </tr>
              </thead>
              <tbody>
                {case_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table cellspacing="0">
              <tbody>
                {prescript_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table>
              <tbody>
                <tr>
                  <td width="55%">
                    應收金額: {regist_fee} 實收金額: {regist_fee}<br>
                    院所: {clinic_name}<br>
                    電話: {clinic_telephone}<br>
                    院址: {clinic_address}<br>
                    請妥善保存此收據, 遺失恕不補發
                  </td>
                  <td width="45%">
                    <table cellpadding="3" cellspacing="0" style="font-size:11px;
                     border-width:1px; border-style: solid; border-color: black;">
                      <tr>
                        <td align="center" colspan="2">{clinic_name}</td>
                      </tr>
                      <tr>
                        <td colspan="2" style="vertical-align: middle; padding: 15px 0;">
                            <center>本醫療收據</center>
                            <center>印花稅總繳</center>
                        </td>
                      </tr>
                      <tr>
                        <td>{clinic_address[:3]}</td>
                        <td>負責總繳人:{owner}</td>
                      </tr=>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>
        '''

        return prescript_html

    def _get_self_prescript_html(self, row):
        case_record = printer_utils.get_case_html_6(
            self.database, self.case_key, '自費', self.medicine_set,
        )

        prescript_record = printer_utils.get_prescript_html2(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=2, max_line=5)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        total_fee = number_utils.get_integer(row['TotalFee'])
        receipt_fee = number_utils.get_integer(row['ReceiptFee'])
        owner = self.system_settings.field('負責醫師')

        ins_type, regist_fee, total_fee = self._read_fees()
        if ins_type == '自費' and regist_fee >= 250:
            total_fee += regist_fee
            receipt_fee += regist_fee
            prescript_record = '''
                <tr>
                    <td align="left" width="29%">自費掛號費</td>
                    <td align="right" width="11%">1次</td>
                </tr>
            ''' + prescript_record

        prescript_html = f'''
            <table cellspacing="0">
              <thead>
                <tr>
                  <th style="text-align: center" colspan="3">
                    <u>收據</u>
                  </th>
                </tr>
              </thead>
              <tbody>
                {case_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table cellspacing="0">
              <tbody>
                {prescript_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table>
              <tbody>
                <tr>
                  <td width="55%">
                    應收金額: {total_fee} 實收金額: {receipt_fee}<br>
                    院所: {clinic_name}<br>
                    電話: {clinic_telephone}<br>
                    院址: {clinic_address}<br>
                    請妥善保存此收據, 遺失恕不補發
                  </td>
                  <td width="45%">
                    <table cellpadding="3" cellspacing="0" style="font-size:11px;
                     border-width:1px; border-style: solid; border-color: black;">
                      <tr>
                        <td align="center" colspan="2">{clinic_name}</td>
                      </tr>
                      <tr>
                        <td colspan="2" style="vertical-align: middle; padding: 15px 0;">
                            <center>本醫療收據</center>
                            <center>印花稅總繳</center>
                        </td>
                      </tr>
                      <tr>
                        <td>{clinic_address[:3]}</td>
                        <td>負責總繳人:{owner}</td>
                      </tr=>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>
        '''

        return prescript_html

    def _html(self, ins_type='自費'):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        if ins_type == '健保':
            prescript_html = self._get_ins_prescript_html(row)
        else:
            prescript_html = self._get_self_prescript_html(row)

        html = f'''
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td width="98%">
                        {prescript_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
        '''

        return html

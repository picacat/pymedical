
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import number_utils


# 健保收據格式20 友杏格式 4.5 x 5.5 inches
# 2018.10.09
class PrintReceiptInsForm20:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]

        try:
            self.print_dosage = args[3]
        except Exception:
            self.print_dosage = True

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
        self.font = QtGui.QFont(font, 9, QtGui.QFont.PreferQuality)
        self.font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 90)

    def _set_signal(self):
        pass

    def _check_printing(self):
        printing = True

        if self.additional == '健保另包':
            if printer_utils.is_additional_prescript(self.database, self.case_key):
                printing = True
            else:
                printing = False

        if self.additional == '健保檢驗':
            if printer_utils.is_ins_examination(self.database, self.case_key):
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

        # self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 4.7, 5.5, QPrinter.Inch, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 13)
        if printing:
            document.print(self.printer)

    def _get_prescript_html(self, row):
        title = '醫療費用收據'

        ins_exam = False
        additional_label = printer_utils.get_additional_label(self.additional)
        if self.additional == '健保檢驗':
            title = '檢驗單'
            additional_label = ''
            ins_exam = True

        if title == '檢驗單':
            case_record = printer_utils.get_case_html_6(
                self.database, self.case_key, '健保', self.medicine_set,
                birthday_mask=False, id_mask=False,
            )
        else:
            case_record = printer_utils.get_case_html_6(
                self.database, self.case_key, '健保', self.medicine_set,
            )

        disease_record = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)
        prescript_record = printer_utils.get_prescript_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set,
            '費用收據', blocks=2, instruction=self.additional, max_line=20, is_print_dosage=self.print_dosage)
        instruction = printer_utils.get_instruction_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set, additional_label,
            ins_exam=ins_exam,
        )

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        # dash_line = '<b>------------------------------------------------------------------------</b>'

        prescript_html = f'''
            <table cellspacing="0" cellpadding="0">
              <thead>
                <tr>
                  <th style="text-align: center" colspan="3">
                    {title}
                  </th>
                </tr>
              </thead>
              <tbody>
                {case_record}
              </tbody>
            </table>
            <hr style="line-height:0.5">
            <table cellspacing="0" cellpadding="0">
              <tbody>
                {prescript_record}
              </tbody>
            </table>
            <br>
            <hr style="line-height:0.5">
            {instruction}
            適應症: {disease_record}<br>
            副作用: 本處方於醫學文獻中尚無副作用之記載<br>
            警語: 請勿與其他藥品混合服用<br>
            院所:{clinic_id} {clinic_name}<br>
            院址:{clinic_address} {clinic_telephone}<br>
            * 本收據可為報稅之憑證, 請妥善保存, 遺失恕不補發
        '''

        return prescript_html

    @staticmethod
    def _get_ins_fees_html(row):
        regist_no = number_utils.get_integer(row['RegistNo'])
        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        diag_fee = number_utils.get_integer(row['DiagFee'])
        drug_fee = number_utils.get_integer(row['InterDrugFee'])
        pharmacy_fee = number_utils.get_integer(row['PharmacyFee'])
        acupuncture_fee = number_utils.get_integer(row['AcupunctureFee'])
        massage_fee = number_utils.get_integer(row['MassageFee'])
        ins_total_fee = number_utils.get_integer(row['InsTotalFee'])
        ins_apply_fee = number_utils.get_integer(row['InsApplyFee'])

        total_share_fee = diag_share_fee + drug_share_fee
        total_fee = regist_fee + diag_share_fee + drug_share_fee + deposit_fee
        treat_fee = acupuncture_fee + massage_fee

        fees_html = f'''
            <table width="100%" cellspacing="0">
              <tbody>
                <tr>
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
                  <td>掛號費</td>
                  <td align="right">{regist_fee}</td>
                </tr>
                <tr>
                  <td>診負擔</td>
                  <td align="right">{diag_share_fee}</td>
                </tr>
                <tr>
                  <td>品負擔</td>
                  <td align="right">{drug_share_fee}</td>
                </tr>
                <tr>
                  <td>總負擔</td>
                  <td align="right">{total_share_fee}</td>
                </tr>
                <tr>
                  <td>欠卡費</td>
                  <td align="right">{deposit_fee}</td>
                </tr>
                <tr>
                  <td>實收額</td>
                  <td align="right">{total_fee}</td>
                </tr>
                <tr>
                  <td>診察費</td>
                  <td align="right">{diag_fee}</td>
                </tr>
                <tr>
                  <td>內服藥</td>
                  <td align="right">{drug_fee}</td>
                </tr>
                <tr>
                  <td>調劑費</td>
                  <td align="right">{pharmacy_fee}</td>
                </tr>
                <tr>
                  <td>處置費</td>
                  <td align="right">{treat_fee}</td>
                </tr>
                <tr>
                  <td>健保額</td>
                  <td align="right">{ins_total_fee}</td>
                </tr>
                <tr>
                  <td>申請額</td>
                  <td align="right">{ins_apply_fee}</td>
                </tr>
              </tbody>
            </table>
            申報非1點1元給付
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
        fees_html = self._get_ins_fees_html(row)
        if self.additional is not None:
            fees_html = ''

        html = f'''
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td width="81%">
                        {prescript_html}
                      </td>
                      <td width="17%">
                        {fees_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
        '''

        return html

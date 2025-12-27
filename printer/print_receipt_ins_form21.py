
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils
from libs import number_utils


# 健保處方箋格式21 8.5 x 2.0 inches
# 2018.10.09 佳禾
class PrintReceiptInsForm21:
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
        # self.printer.setPaperSize(QtCore.QSizeF(7.8, 2.5), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 7.2, 2.0, QPrinter.Inch, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
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

        case_record = printer_utils.get_case_html_21(self.database, self.case_key, '健保', self.medicine_set)
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set,
            '費用收據', blocks=2, instruction=self.additional)
        instruction = printer_utils.get_instruction_html1(
            self.database, self.system_settings, self.case_key,
            self.medicine_set, print_total_fee=False, print_pharmacy_date=True
        )
        fees_record = printer_utils.get_ins_fees_html(self.database, self.case_key)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        symptom_html = self._get_symptom_html()
        prescript_html = self._get_prescript_html()
        fees_html = self._get_ins_fees_html(row)
        if self.additional is not None:
            fees_html = ''

        left_html = f'''
            <html>
              <body>
                <h4 align="center">{clinic_name} 處方暨費用收據</h4>
                <table style="font-size: 12px" width="95%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <br>
                <table style="font-size: 12px" width="95%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td>
                        {prescript_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
                警語: 請遵照醫師指示服藥,西藥隔開一小時, 適應症: 體質調理, 副作用: 無<br>
                {instruction}<br>
                本收據可為報稅之憑證, 請妥善保存, 遺失恕不補發
              </body>
            </html>
        '''

        html = f'''
            <html>
              <body>
                <table style="font-size: 12px" width="100%" cellspacing="0">
                  <tbody>
                    <tr>
                      <td width="77%">
                        {left_html}
                      </td>
                      <td width="23%">
                        {fees_html}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
        '''

        return html

    def _get_symptom_html(self):
        symptom_record = printer_utils.get_symptom_html(
            self.database, self.system_settings, self.case_key,
        )
        symptom_html = f'''
            <table cellspacing="0" cellpadding="0">
              <tbody>
                {symptom_record}
              </tbody>
            </table>
        '''

        return symptom_html

    def _get_prescript_html(self):
        prescript_record = printer_utils.get_prescript_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set,
            '費用收據', blocks=2, instruction=self.additional, max_line=4)
        prescript_html = f'''
            <table cellspacing="0" cellpadding="0">
              <tbody>
                {prescript_record}
              </tbody>
            </table>
        '''

        return prescript_html

    def _get_ins_fees_html(self, row):
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

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')

        fees_html = f'''
            <table width="100%" cellspacing="0">
              <tbody>
                <tr>
                  <td>掛號費</td>
                  <td align="right">{regist_fee}</td>
                </tr>
                <tr>
                  <td>門診負擔</td>
                  <td align="right">{diag_share_fee}</td>
                </tr>
                <tr>
                  <td>藥品負擔</td>
                  <td align="right">{drug_share_fee}</td>
                </tr>
                <tr>
                  <td>欠卡金額</td>
                  <td align="right">{deposit_fee}</td>
                </tr>
                <tr>
                  <td>實收金額</td>
                  <td align="right">{total_fee}</td>
                </tr>
                <tr>
                  <td>診察費</td>
                  <td align="right">{diag_fee}點</td>
                </tr>
                <tr>
                  <td>內服藥費</td>
                  <td align="right">{drug_fee}點</td>
                </tr>
                <tr>
                  <td>調劑費</td>
                  <td align="right">{pharmacy_fee}點</td>
                </tr>
                <tr>
                  <td>處置費</td>
                  <td align="right">{treat_fee}</td>
                </tr>
                <tr>
                  <td>健保合計</td>
                  <td align="right">{ins_total_fee}點</td>
                </tr>
                <tr>
                  <td>健保申請</td>
                  <td align="right">{ins_apply_fee}點</td>
                </tr>
              </tbody>
            </table>
        '''

        return fees_html

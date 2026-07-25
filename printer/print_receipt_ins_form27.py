
# -*- coding: UTF-8 -*-

from logging import warn
from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
import sys

from libs import printer_utils
from libs import system_utils
from libs import case_utils
from libs import string_utils
from libs import number_utils


# 健保收據格式27 A5 林胤谷
# 2025.04.11
class PrintReceiptInsForm27:
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
        # self.dash_line = f'<span style="color: #999999;">{'-' * 104}</span>'
        self.dash_line = '-' * 104

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
        # font = 'PMingLiU'
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
        # self.printer.setOrientation(QPrinter.Landscape)

        # printer_utils.set_paper_size(self.printer, self.system_settings, 148, 210, QPrinter.Millimeter, '健保醫療收據')
        printer_utils.set_paper_size(self.printer, self.system_settings, QPrinter.A4, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        # document.setDocumentMargin(printer_utils.get_document_margin())
        document.setDocumentMargin(20)
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 15)
        if printing:
            document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_27(
            self.database, self.case_key, self.medicine_set, '健保', tw_date=True
        )
        prescript_record = printer_utils.get_prescript_html27(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=2, max_length=6, instruction=self.additional)

        instruction = printer_utils.get_instruction_html_one_line(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fees_record = self.get_fees_html2(self.case_key)
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
            warning = ''

        receipt_title_image = printer_utils.get_title_image(
            clinic_name, clinic_id, clinic_telephone, clinic_address)

        tax_hint = '<br>本收據可為報稅憑證, 遺失恕不補發'
        if self.system_settings.field('不印報稅提示') == 'Y':
          tax_hint = ''

        html_str = f'''
            <html>
              <body>
              <br>
                <div style="text-align: center; padding-top: 6pt;">
                    <h3 style="margin: 0;">{clinic_name} 門診醫療費用收據</h3>
                </div>
                <br>
                <table width="100%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                {self.dash_line}
                <table width="100%" cellspacing="0" cellpadding="0" style="vertical-align: bottom; border-width: 0px; border-style: solid;">
                    <thead>
                        <tr>
                            <th align="center">序</th>
                            <th align="left">處方名稱</th>
                            <th align="right">劑量</th>
                            <th align="right">總量</th>
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
                {self.dash_line}
                {instruction}<br>適應症:{disease_name}{warning}
                {self.dash_line}
                <table width="100%" cellspacing="0" cellpadding="0" style="vertical-align: bottom; border-width: 0px; border-style: solid;">
                    <tbody>
                        {fees_record}
                    </tbody>
                </table>
                {self.dash_line}
                <table width="100%" cellspacing="0" cellpadding="0" style="vertical-align: bottom; border-width: 0px; border-style: solid;">
                    <tbody>
                            <td colspan="8">
                                院所代號: {clinic_id} 電話: {clinic_telephone} 地址: {clinic_address}
                                {tax_hint}
                            </td>
                        </tr>
                    </tbody>
                </table>
              </body>
            </html>
        '''

        return html_str

    # 健保局費用格式
    def get_fees_html2(self, case_key, ins_type='健保'):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {case_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return ''

        row = rows[0]
        registrar = string_utils.xstr(row['Register'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        total_share_fee = diag_share_fee + drug_share_fee

        diag_fee = number_utils.get_integer(row['DiagFee'])
        drug_fee = number_utils.get_integer(row['InterDrugFee'])
        pharmacy_fee = number_utils.get_integer(row['PharmacyFee'])
        exam_fee = number_utils.get_integer(row['ExamFee'])
        treat_fee = (
                number_utils.get_integer(row['AcupunctureFee']) +
                number_utils.get_integer(row['MassageFee']) +
                number_utils.get_integer(row['DislocateFee'])
        )
        ins_total_fee = number_utils.get_integer(row['InsTotalFee'])
        s_drug_fee = number_utils.get_integer(row['SDrugFee'])
        herb_fee = number_utils.get_integer(row['SHerbFee'])
        expensive_fee = number_utils.get_integer(row['SExpensiveFee'])
        s_exam_fee = number_utils.get_integer(row['SExamFee'])
        material_fee = number_utils.get_integer(row['SMaterialFee'])

        s_acupuncture_fee = number_utils.get_integer(row['SAcupunctureFee'])
        s_massage_fee = number_utils.get_integer(row['SMassageFee'])
        discount_fee = number_utils.get_integer(row['DiscountFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        if ins_type == '健保':
            s_drug_fee = 0
            herb_fee = 0
            expensive_fee = 0
            s_exam_fee = 0
            material_fee = 0
            s_acupuncture_fee = 0
            s_massage_fee = 0
            total_fee = 0

        s_treat_fee = s_acupuncture_fee + s_massage_fee
        self_drug_fee = s_drug_fee + herb_fee + expensive_fee - discount_fee
        self_treat_fee = s_exam_fee + s_treat_fee

        total_cash = regist_fee + total_share_fee + total_fee

        html = f'''
            <tr>
                <td colspan="2" style="padding-left: 5px">診察費</td>
                <td colspan="2" align=right style="padding-right: 40%">{diag_fee}</td>
                <td colspan="2" style="padding-left: 5px">掛號費</td>
                <td colspan="2" align=right style="padding-right: 40%">{regist_fee}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-left: 5px">藥費</td>
                <td colspan="2" align=right style="padding-right: 40%">{drug_fee}</td>
                <td colspan="2" style="padding-left: 5px">基本部分負擔</td>
                <td colspan="2" align=right style="padding-right: 40%">{diag_share_fee}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-left: 5px">藥事服務費</td>
                <td colspan="2" align=right style="padding-right: 40%">{pharmacy_fee}</td>
                <td colspan="2" style="padding-left: 5px">藥品部分負擔</td>
                <td colspan="2" align=right style="padding-right: 40%">{drug_share_fee}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-left: 5px">檢驗費</td>
                <td colspan="2" align=right style="padding-right: 40%">{exam_fee}</td>
                <td colspan="2" style="padding-left: 5px">檢驗處置費</td>
                <td colspan="2" align=right style="padding-right: 40%">{self_treat_fee}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-left: 5px">處置手術費</td>
                <td colspan="2" align=right style="padding-right: 40%">{treat_fee}</td>
                <td colspan="2" style="padding-left: 5px">藥品(自費)</td>
                <td colspan="2" align=right style="padding-right: 40%">{self_drug_fee}</td>
            </tr>
            <tr>
                <td colspan="2" style="padding-left: 5px">材料費</td>
                <td colspan="2" align=right style="padding-right: 40%">0</td>
                <td colspan="2" style="padding-left: 5px">衛材(自費)</td>
                <td colspan="2" align=right style="padding-right: 40%">{material_fee}</td>
            </tr>
            <tr>
                <td colspan="8">{self.dash_line}</td>
            <tr>
                <td align=left colspan=4>小計: 健保申報 {ins_total_fee}點<br>(健保申報點數非一點一元給付)</td>
                <td align=left colspan=4>小計: 部份負擔金額 {total_share_fee}元<br>其他自費金額: {total_fee}</td>
            </tr>
            <tr>
                <td align=left colspan=4>應繳金額: {total_cash}元</td>
                <td align=left colspan=4>經手人:</td>
            </tr>
        '''

        return html

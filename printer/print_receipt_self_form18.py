
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import number_utils
from libs import string_utils
from libs import case_utils


# 自費收據格式18 左收據右處方 11"中二刀
# 2023.12.20
class PrintReceiptSelfForm18:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

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

        width = 8.0
        if self.system_settings.field('院所名稱') == '板橋聖昌中醫診所':
          width = 8.2

        printer_utils.set_paper_size(self.printer, self.system_settings, width, 3.66, QPrinter.Inch, '健保醫療收據')  # 寬度最多只能到8.0吋

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
                self.database, self.case_key, '自費', self.medicine_set,
                birthday_mask=False, id_mask=False,
            )
        else:
            case_record = printer_utils.get_case_html_6(
                self.database, self.case_key, '自費', self.medicine_set,
            )

        disease_record = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)
        prescript_record = printer_utils.get_prescript_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set,
            '費用收據', blocks=2, instruction=self.additional, max_line=5)
        instruction = printer_utils.get_instruction_html2(
            self.database, self.system_settings, self.case_key, self.medicine_set, additional_label,
            ins_exam=ins_exam,
        )

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

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
            院所:{clinic_id} {clinic_name}<br>
            院址:{clinic_address} {clinic_telephone}<br>
        '''

        return prescript_html

    def _get_total_medicine_set(self):
        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
              CaseKey = {self.case_key} AND
              MedicineSet >= 2
            GROUP BY MedicineSet
        '''
        rows = self.database.select_record(sql)

        return len(rows)

    def _get_self_fees_html(self, row):
        regist_no = number_utils.get_integer(row['RegistNo'])

        if string_utils.xstr(row['InsType']) == '健保':
            regist_fee = 0
        elif self.medicine_set == 2:
            regist_fee = number_utils.get_integer(row['RegistFee'])
        else:
            regist_fee = 0

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
        total_fee = number_utils.get_integer(row['TotalFee'])
        receipt_fee = number_utils.get_integer(row['ReceiptFee'])

        if self.system_settings.field('列印所有收費收據費用明細') == 'Y' and \
                self.system_settings.field('列印所有收費收據各自金額') == 'Y':
            total_fee = number_utils.get_integer(
              case_utils.get_total_fee(self.database, self.case_key, self.medicine_set))
            total_medicine_set = self._get_total_medicine_set()

            if total_fee == 0 and total_medicine_set == 1:  # 只開自費1沒有批價，列印自費總批價
                pass
            else:
                diag_fee = 0
                drug_fee = total_fee
                herb_fee = 0
                expensive_fee = 0
                acupuncture_fee = 0
                massage_fee = 0
                dislocate_fee = 0
                material_fee = 0
                exam_fee = 0
                self_total_fee = total_fee
                discount_fee = 0
                receipt_fee = total_fee

        if self.medicine_set == 2:
            total_fee += regist_fee
            receipt_fee += regist_fee

        fees_html = f'''
            <table width="100%" cellspacing="0">
              <tbody>
                <tr>
                  <td style="text-align: right" colspan="2">診號:{regist_no}</td>
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
                  <td>診察費</td>
                  <td align="right">{diag_fee}</td>
                </tr>
                <tr>
                  <td>藥費</td>
                  <td align="right">{drug_fee}</td>
                </tr>
                <tr>
                  <td>水藥費</td>
                  <td align="right">{herb_fee}</td>
                </tr>
                <tr>
                  <td>高貴藥</td>
                  <td align="right">{expensive_fee}</td>
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
                  <td>檢驗費</td>
                  <td align="right">{exam_fee}</td>
                </tr>
                <tr>
                  <td>自費額</td>
                  <td align="right">{self_total_fee}</td>
                </tr>
                <tr>
                  <td>折扣額</td>
                  <td align="right">{discount_fee}</td>
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
        fees_html = self._get_self_fees_html(row)
        if self.additional is not None:
            fees_html = ''

        prescript_form_html = self._get_prescript_form_html()

        receipt_width = 54
        prescript_width = 46 

        if self.system_settings.field('院所名稱') == '板橋聖昌中醫診所':
            receipt_width = 54
            prescript_width = 46 

        html = f'''
            <html>
              <body>
                <br>
                <table width="100%" cellspacing="0">
                    <tr>
                        <td width="{receipt_width}%">
                            <table width="100%" cellspacing="0">
                                <tr>
                                    <td width="78%">
                                        {prescript_html}
                                    </td>
                                    <td width="18%">
                                        {fees_html}
                                    </td>
                                </tr>
                            </table>
                        </td>
                        <td width="{prescript_width}%">
                            <table width="100%" cellspacing="0">
                                <tr>
                                    <td>
                                        {prescript_form_html}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
              </body>
            </html>
        '''

        return html

    def _get_prescript_form_html(self):
        case_record = printer_utils.get_case_html_2(
            self.database, self.case_key, '自費', tw_date=True, birthday_mask=False, id_mask=False)
        symptom_record = printer_utils.get_symptom_html(self.database, self.system_settings, self.case_key, colspan=4)
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '處方箋', blocks=2, instruction=self.additional, print_total_dosage='N')
        instruction = printer_utils.get_instruction_html1(
            self.database, self.system_settings, self.case_key, self.medicine_set, print_total_fee=False
        )

        html = f'''
                <table width="100%" cellspacing="0">
                  <tbody>
                    {case_record}
                    {symptom_record}
                  </tbody>
                </table>
                {disease_record}
                <hr style="line-height:0.5">
                <table width="100%" cellspacing="0">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <br>
                <hr style="line-height:0.5">
                {instruction}
        '''

        return html

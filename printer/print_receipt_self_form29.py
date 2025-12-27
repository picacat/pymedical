
# -*- coding: UTF-8 -*-

import sys
from re import I

from libs import (case_utils, date_utils, number_utils, printer_utils,
                  string_utils, system_utils)
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter


# 自費據格式29 80mm 熱感紙(橫印) 專嘉
# 2025.07.21
class PrintReceiptSelfForm29:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None
        self.block_len = 10

        self.printer = printer_utils.get_printer(self.system_settings, '自費醫療收據印表機')

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
        # self.printer.setPaperSize(QtCore.QSizeF(74, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 188, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            minimum_len = 20
            if self.prescript_count <= minimum_len:
                a = 0
            else:
                a = (self.prescript_count - (minimum_len + 1)) // self.block_len + 1

            paper_length = 200 + (a * 40)

            printer_utils.rotate_document(self.printer, document, 80, paper_length)
            # document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_24(
            self.database, self.system_settings, self.case_key, '健保', tw_date=True
        )
        prescript_html, self.prescript_count = printer_utils.get_prescript_html29(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '費用收據', blocks=1,
            instruction=self.additional, print_total_dosage='Y', print_treat_item=False,
            td_width=180, block_len=self.block_len, border=0, header=False, print_sequence=False)
        instruction = printer_utils.get_instruction_html_0(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fees_record = printer_utils.get_self_fees_html_dynamic29(
            self.database, self.system_settings, self.case_key, self.medicine_set,
            print_cash_fees=True, width=1)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        pres_days = case_utils.get_pres_days(self.database, self.case_key, self.medicine_set)

        receipt_title_image = printer_utils.get_title_image(
            clinic_name, clinic_id, clinic_telephone, clinic_address)

        if self.system_settings.field('不印報稅提示') == 'Y':
            tax_hint = ''
        else:
            tax_hint = self.system_settings.field('醫療費用收據自訂報稅備註')
            if tax_hint in ['', None]:
                tax_hint = '''
                    <table>
                        <tr><td>1.</td><td>本收據若經塗改，或未蓋本院收費章者無效</td></tr>
                        <tr><td>2.</td><td>本收據請妥善保存，遺失恕不補發</td></tr>
                    </table>
                '''

        if self.system_settings.field('費用收據不印處方') == 'Y':
            prescript_html = ''

        rows = printer_utils.get_case_row(self.database, self.case_key)
        if not rows:
            return ''

        row = rows[0]

        patient_key = f"{row['PatientKey']:0>6}"
        name = string_utils.xstr(row['Name'])
        case_date = row['CaseDate'].strftime('%Y-%m-%d')
        id = string_utils.xstr(row['ID'])
        if id not in ['', None]:
            id = id[:6] + '****'

        gender = string_utils.xstr(row['Gender'])
        age = ''
        birthday = row['Birthday']
        if birthday is not None:
            birthday = birthday.strftime('%Y****')
            age_year, age_month = date_utils.get_age(row['Birthday'], row['CaseDate'])
            if age_year is None:
                age = ''
            else:
                age = f'年齡:{age_year}歲'

        birthday_str = string_utils.xstr(birthday)
        share_type = string_utils.xstr(row['Share'])
        doctor = string_utils.xstr(row['Doctor'])
        pres_days = case_utils.get_pres_days(self.database, self.case_key, medicine_set=self.medicine_set)
        packages = case_utils.get_packages(self.database, self.case_key, medicine_set=self.medicine_set)
        instruction = case_utils.get_instruction(self.database, self.case_key, medicine_set=self.medicine_set)
        dosage_mode = case_utils.get_dosage_mode(self.database, self.case_key, medicine_set=self.medicine_set)

        total_fee = case_utils.get_total_fee(self.database, self.case_key, medicine_set=self.medicine_set)
        drug_share_fee = number_utils.get_integer(row['DrugShareFee'])

        if pres_days > 0 and self.additional is None:
            if packages is None or packages == 0:
                packages = 1

            _, total_dosage, _, single_day_dosage = case_utils.get_prescript_html_data(
                self.database, self.system_settings, self.case_key, medicine_set=self.medicine_set
            )

            total_dosage = f'{total_dosage:.1f}'

            case_date = row['CaseDate'].date()
            html = f'''
                  指示:一日{packages}包, {pres_days}日份, 共{packages * pres_days}包<br>
                  服法:{instruction}服用 總量:{total_dosage}<br>
                  醫師/調劑者:{doctor}<br>
                  調劑日:{case_date}
            '''
        tab = '&nbsp;' * 6

        order_html = ''
        prescript_order = case_utils.get_prescript_order(self.database, self.case_key, self.medicine_set)
        if prescript_order not in ['', None]:
            order_html = f'''
                <tr>
                    <td>
                        醫囑: {prescript_order}
                    </td>
                </tr>
            '''
        
        instruction_html = ''
        if pres_days > 0:
            warning = '''
            '''
            instruction_html = f'''
                <table width="100%" cellspacing="0" style="margin-left: 10px;">
                    <tr>
                        <td>
                            門診日/調劑日: {case_date}{tab}
                            醫師/調劑者:{doctor}{tab}
                            指示:一日{packages}包, {pres_days}日份, 共{packages * pres_days}包{tab}
                            服法:{instruction}服用 總量:{total_dosage}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            警語:請遵照醫師指示服用，並置於兒童不易取得處{tab}
                            副作用: 本處方用藥在醫學文獻上尚無副作用之記載{tab}
                        </td>
                    </tr>
                    {order_html}
                </table>
            '''

        html = f'''
            <html>
              <body>
                <b>
                <br>
                <table width="100%" cellspacing="0" style="margin-left: 10px;">
                    <tr>
                       <td>{clinic_name}{clinic_id}{tab}門診費用收據{tab}
                            電話: {clinic_telephone}{tab}地址: {clinic_address}
                        </td>
                    </tr>
                    <tr>
                       <td>
                            病歷號: {patient_key}{tab}姓名: {name} ({gender}){tab}身份證: {id}{tab}
                            生日: {birthday_str}{tab}保險: 自費({self.medicine_set-1})
                       </td>
                    </tr>
                </table>
                <hr style="line-height:0.5">
                <table width="100%" cellspacing="0" style="margin-left: 10px;">
                  <tbody>
                    <tr>
                        {prescript_html}
                        <td width="300">
                            {fees_record}
                            <br>
                            {tax_hint}
                        </td>
                    </tr>
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                {instruction_html}
              </b>
              </body>
            </html>
        '''

        return html

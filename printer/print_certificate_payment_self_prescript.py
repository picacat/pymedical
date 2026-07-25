
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import patient_utils
from libs import personnel_utils
from libs import number_utils


# 收費證明自費明細
# 2020.05.07
class PrintCertificatePaymentSelfPrescript:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.certificate_key = args[2]

        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

        if self.system_settings.field('列印報表雙色印刷') == 'Y':
            self.html_bg_color = ' bgcolor="LightGray"'
        else:
            self.html_bg_color = ''

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

    def save_to_pdf(self):
        export_dir = f'{self.ins_apply_path}/certificate'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/certificate_prescription{self.certificate_key}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        export_dir = f'{self.ins_apply_path}/certificate'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/certificate_prescription{self.certificate_key}.pdf'

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent, "匯出費用證明pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)", options=options
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QMessageBox.Information,
            '匯出完成',
            '<font size="5" color="red"><b>費用證明pdf檔案已匯出完成</b></font>',
            '',
        )

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        sql = f'''
            SELECT * FROM certificate
            WHERE
                CertificateKey = {self.certificate_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        html_title = self._get_html_title(row)
        html_patient = self._get_html_patient(row)
        html_payment = self._get_html_payment(row)
        html_summary = self._get_html_summary(row)
        html_remark = self._get_html_remark()

        html = f'''
            <html>
              <body>
                {html_title}
                {html_patient}
                {html_payment}
                {html_summary}
                {html_remark}
              </body>
            </html>
        '''

        return html

    def _get_html_title(self, row):
        clinic_name = self.system_settings.field('院所名稱')
        certificate_key = f'{row["CertificateKey"]:0>8}'

        html = f'''
            <h1 style="text-align: center">{clinic_name} 醫療費用證明書 自費明細</h1>
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td><h3>編號: {certificate_key}</h3></td>
                    </tr>
                </tbody>
            </table>
        '''
        return html

    def _get_html_patient(self, row):
        patient_row = patient_utils.get_patient_row(self.database, row['PatientKey'])
        case_date = string_utils.xstr(row['StartDate'])

        if row['EndDate'] != row['StartDate']:
            case_date += f' 至 {row["EndDate"]}'

        patient_key = f'{row["PatientKey"]:0>6}'
        name = string_utils.xstr(row['Name'])
        gender = string_utils.xstr(patient_row['Gender'])
        birthday = string_utils.xstr(patient_row['Birthday'])
        patient_id = string_utils.xstr(patient_row['ID'])
        telephone = string_utils.xstr(patient_row['Telephone'])
        address = string_utils.xstr(patient_row['Address'])

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
                style="font-size: 14px; border-width: 1px; border-style: solid; border-collapse: collapse;">
                <tbody>
                    <tr>
                        <th{self.html_bg_color}>姓名</th>
                        <td style="text-align: center; vertical-align: middle">{name}</td>
                        <th{self.html_bg_color}>性別</th>
                        <td style="text-align: center; vertical-align: middle">{gender}</td>
                        <th{self.html_bg_color}>出生日期</th>
                        <td style="text-align: center; vertical-align: middle">{birthday}</td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color}>病歷號碼</th>
                        <td style="text-align: center; vertical-align: middle">{patient_key}</td>
                        <th{self.html_bg_color}>身份證號</th>
                        <td style="text-align: center; vertical-align: middle">{patient_id}</td>
                        <th{self.html_bg_color}>電話</th>
                        <td style="text-align: center; vertical-align: middle">{telephone}</td>
                    <tr>
                        <th{self.html_bg_color}>地址</th>
                        <td colspan="5" style="text-align: left; vertical-align: middle">{address}</td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color} style="vertical-align: middle">科別</th>
                        <td style="text-align: center; vertical-align: middle">60 中醫科</td>
                        <th{self.html_bg_color}>診療日期</th>
                        <td colspan="3" style="text-align: center; vertical-align: middle">{case_date}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    def _get_html_payment(self, row):
        ins_type = string_utils.xstr(row['InsType'])
        fees_detail = self._get_fees_detail(ins_type)

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
                style="font-size: 14px; border-width: 1px; border-style: solid; border-collapse: collapse">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th>序號</th>
                        <th>門診日期</th>
                        <th>保險類別</th>
                        <th>掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負擔</th>
                        <th>自付金額</th>
                        <th>健保申報</th>
                        <th>自費金額</th>
                        <th>自付合計</th>
                    </tr>
                    {fees_detail}
                </tbody>
            </table>
        '''

        return html

    def _get_fees_detail(self, ins_type):
        sql = f'''
            SELECT * FROM certificate_items
            WHERE
                CertificateKey = {self.certificate_key}
            ORDER BY CaseDate
        '''

        rows = self.database.select_record(sql)

        total_regist_fee = 0
        total_diag_share_fee = 0
        total_drug_share_fee = 0
        total_cash_fee = 0
        total_ins_apply_fee = 0
        total_total_fee = 0
        total_cash_total = 0

        html = ''
        for row_no, row in zip(range(1, len(rows)+1), rows):
            total_fee = number_utils.get_integer(row['TotalFee'])
            if total_fee <= 0:
                continue

            regist_fee = number_utils.get_integer(row['RegistFee'])
            diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
            drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
            cash_fee = regist_fee + diag_share_fee + drug_share_fee
            ins_apply_fee = number_utils.get_integer(row['InsApplyFee'])
            cash_total = cash_fee + total_fee

            total_regist_fee += regist_fee
            total_diag_share_fee += diag_share_fee
            total_drug_share_fee += drug_share_fee
            total_cash_fee += cash_fee
            total_ins_apply_fee += ins_apply_fee
            total_total_fee += total_fee
            total_cash_total += cash_total

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and row_no % 2 > 0:
                bg_color = ' bgcolor="#E3E3E3"'

            prescript_html = self._get_prescript_html(row['CaseKey'])
            case_date = string_utils.xstr(row['CaseDate'].date())
            html += f'''
                <tr>
                    <td{bg_color} style="text-align: center">{row_no}</td>
                    <td{bg_color} style="text-align: center">{case_date}</td>
                    <td{bg_color} style="text-align: center">{row["InsType"]}</td>
                    <td{bg_color} style="text-align: right">{regist_fee}</td>
                    <td{bg_color} style="text-align: right">{diag_share_fee}</td>
                    <td{bg_color} style="text-align: right">{drug_share_fee}</td>
                    <td{bg_color} style="text-align: right">{cash_fee}</td>
                    <td{bg_color} style="text-align: right">{ins_apply_fee}</td>
                    <td{bg_color} style="text-align: right"><b>{total_fee}</b></td>
                    <td{bg_color} style="text-align: right">{cash_total}</td>
                </tr>
                <tr>
                    <td colspan="10">
                        <div align="left" style="margin-left: 30px; margin-right: 30px;
                             margin-top: 5px">
                            <table align=center cellpadding="2" cellspacing="0" width="98%"
                                style="font-size: 14px; border-width: 1px;
                                border-style: solid; border-collapse: collapse">
                                <tbody>
                                    <tr{self.html_bg_color}>
                                        <th width="5%">序</th>
                                        <th width="10%">自費組別</th>
                                        <th width="45%">處方名稱</th>
                                        <th width="10%">數量</th>
                                        <th width="5%">單位</th>
                                        <th width="10%">單價</th>
                                        <th width="10%">金額</th>
                                    </tr>
                                    {prescript_html}
                                </tbody>
                            </table>
                        </div>
                    </td>
                </tr>
            '''

        html += f'''
            <tr>
                <td{self.html_bg_color} style="text-align: center" colspan=3>合計</td>
                <td style="text-align: right">{total_regist_fee}</td>
                <td style="text-align: right">{total_diag_share_fee}</td>
                <td style="text-align: right">{total_drug_share_fee}</td>
                <td style="text-align: right">{total_cash_fee}</td>
                <td style="text-align: right">{total_ins_apply_fee}</td>
                <td style="text-align: right">{total_total_fee}</td>
                <td style="text-align: right">{total_cash_total}</td>
            </tr>
        '''

        return html

    def _get_prescript_html(self, case_key):
        html = ''

        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                Price > 0
            ORDER BY MedicineSet, PrescriptKey
        '''
        rows = self.database.select_record(sql)

        for row_no, row in enumerate(rows):
            medicine_set = row['MedicineSet']
            medicine_type = string_utils.xstr(row['MedicineType'])

            medicine_name = string_utils.xstr(row['MedicineName'])
            if medicine_name in ['', '優待']:
                continue

            medicine_unit = string_utils.xstr(row['Unit'])
            dosage = number_utils.get_float(row['Dosage'])
            if dosage <= 0:
                dosage = 1
            price = number_utils.get_integer(row['Price'])
            amount = number_utils.get_integer(row['Amount'])
            if amount <= 0:
                amount = number_utils.get_integer(dosage * price)

            if medicine_type == '水藥' and amount <= 0:
                continue

            html += f'''
                <tr>
                    <td style="text-align: center">{row_no+1}</td>
                    <td style="text-align: center">{medicine_set-1}</td>
                    <td>{medicine_name}</td>
                    <td style="text-align: right">{dosage}</td>
                    <td style="text-align: center">{medicine_unit}</td>
                    <td style="text-align: right">{price}</td>
                    <td style="text-align: right">{amount}</td>
                </tr>
            '''

        return html

    def _get_html_summary(self, row):
        physician = string_utils.xstr(row['Doctor'])
        physician_cert_no = personnel_utils.get_person_field_value(
            self.database, physician, 'Certificate')
        president = self.system_settings.field('負責醫師')
        license_no = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        year = row['CertificateDate'].year
        month = row['CertificateDate'].month
        day = row['CertificateDate'].day
        certificate_date = f'{year} 年 {month} 月 {day} 日'

        html = f'''
            <table align=center cellpadding="10" cellspacing="0" width="98%"
                style="font-size: 14px; border-width: 1px; border-style: solid; border-collapse: collapse">
                <tbody>
                    <tr>
                        <td>
                            <h2>本證明請妥善保存，遺失恕不補發。</h2>
                            <h3>
                                主治醫師: {physician}<br>
                                醫師證書號碼: {physician_cert_no}<br>
                                院長: {president}<br>
                                開業執照號碼: {license_no}
                            </h3>
                            <h3>
                                院所電話: {clinic_telephone}<br>
                                院所地址: {clinic_address}
                            </h3>
                            <h3>
                                開立醫療費用證明日期: {certificate_date}
                            </h3>
                        </td>
                    </tr>
                </tbody>
            </table>
        '''
        return html

    @staticmethod
    def _get_html_remark():
        html = '''
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td>本證明書經塗改或未加蓋本院印章者無效</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

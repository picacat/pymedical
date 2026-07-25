
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils


# 列印掛號費優待名單
# 2022.08.28
class PrintInsRegistFeeDiscount:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.tableWidget_medical_record = args[4]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None
        self.font_size = '14px'

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
        options = QFileDialog.Options()
        pdf_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date}-{self.end_date}{self.doctor}矯正機關內門診現金日報表.pdf',
            "pdf檔案 (*.pdf);;Text Files (*.txt)", options=options
        )
        if not pdf_file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setOrientation(QPrinter.Portrait)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        income_list, total_person, total_discount = self._get_discount_list_html()
        clinic_name = self.system_settings.field('院所名稱')
        try:
            case_date = self.tableWidget_medical_record.item(0, self.columns['CaseDate']).text()
            case_date = date_utils.date_to_zh_tw_date(case_date)
            case_date = case_date.split(' ')[0]
        except Exception:
            case_date = ''

        if total_person > 0:
            total_person -= 1

        html = f'''
            <html>
                <body>
                    <br>
                    <p align=center style="font-size: 28px; font-weight: 500">{clinic_name} 免掛號費優惠名單</p>
                    <div align="left" style="margin-left: 30; font-size: {self.font_size}">
                        列印日期: {date_utils.date_to_str()}<br>
                        統計日期: {self.start_date} 至 {self.end_date}<br>
                        優惠人數: {total_person}人, 優惠金額: {total_discount}元
                    </div>
                    {income_list}
                    <br><br>
                </body>
            </html>
        '''

        return html

    def _get_patient_data(self, patient_key):
        sql = f'''
            SELECT ChartNo FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        row = rows[0]
        chart_no = string_utils.xstr(row['ChartNo'])

        return chart_no

    def _get_discount_list_html(self):
        medical_record_rows = ''

        alternative_row_color = self.system_settings.field('列印報表雙色印刷')

        total_person, total_discount = 0, 0
        for row_no in range(self.tableWidget_medical_record.rowCount()):
            total_person += 1

            bgcolor = 'white'
            if alternative_row_color == 'Y' and row_no % 2 > 0:
                bgcolor = '#E3E3E3'

            case_date_item = self.tableWidget_medical_record.item(row_no, 1)
            if case_date_item is None:
                continue

            case_date = case_date_item.text()
            try:
                case_date = date_utils.date_to_zh_tw_date(case_date)
            except Exception:
                pass

            discount_type = self.tableWidget_medical_record.item(row_no, 3).text()
            discount_fee = number_utils.get_integer(self.tableWidget_medical_record.item(row_no, 9).text())
            patient_key = self.tableWidget_medical_record.item(row_no, 11).text()
            name = self.tableWidget_medical_record.item(row_no, 12).text()

            birthday = self.tableWidget_medical_record.item(row_no, 13).text()
            try:
                birthday = date_utils.date_to_zh_tw_date(birthday)
            except Exception:
                pass

            patient_id = self.tableWidget_medical_record.item(row_no, 14).text()
            telephone = self.tableWidget_medical_record.item(row_no, 15).text()
            if telephone == '':
                telephone = self.tableWidget_medical_record.item(row_no, 16).text()

            address = self.tableWidget_medical_record.item(row_no, 17).text()
            total_discount += discount_fee

            medical_record_rows += f'''
                <tr bgcolor={bgcolor}>
                    <td align=center>{case_date}</td>
                    <td align=center>{discount_type}</td>
                    <td align=center>{discount_fee}</td>
                    <td align=center>{patient_key}</td>
                    <td align=center>{name}</td>
                    <td align=center>{birthday}</td>
                    <td align=center>{patient_id}</td>
                    <td align=left>{telephone}</td>
                    <td align=left>{address}</td>
                </tr>
            '''

        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="font-size: {self.font_size}; border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th>門診日期</th>
                        <th>優待類別</th>
                        <th>優待金額</th>
                        <th>病歷號</th>
                        <th>病患姓名</th>
                        <th>出生日期</th>
                        <th>身分證號</th>
                        <th>聯絡電話</th>
                        <th>聯絡地址</th>
                    </tr>
                </thead>
                <tbody>
                    {medical_record_rows}
                </tbody>
            </table>
            <br><br>
        '''

        return html, total_person, total_discount


# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils


# 列印門診收入總覽
# 2023.04.04
class PrintDoctorSummary:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.doctor = args[4]
        self.tableWidget_doctor_summary = args[5]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
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
        self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)

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
            f'{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}醫師門診收入總覽.pdf',
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
        # self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')
        income_table = self._get_income_table()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 門診收入總覽</h2>
                    <div align="left" style="margin-left: 10px">
                        統計日期: {self.start_date[:10]} 至 {self.end_date[:10]} {self.doctor}醫師
                    </div>
                    {income_table}
                </body>
            </html>
        '''

        return html

    def _get_income_table(self):
        income_header = self._get_income_header()
        income_body = self._get_income_body()

        html = f'''
            <table cellpadding="0" cellspacing="0" width="100%">
                <thead>
                    {income_header}
                </thead>
                <tbody>
                    {income_body}
                </tbody>
            </table>
        '''

        return html

    def _get_income_header(self):
        th = ''
        for col_no in range(self.tableWidget_doctor_summary.columnCount()):
            header = self.tableWidget_doctor_summary.horizontalHeaderItem(col_no).text()
            th += f'<th style="text-align: center; vertical-align: middle; padding: 2px">{header}</th>'

        html = f'<tr bgcolor="LightGray">{th}</tr>'

        return html

    def _get_income_body(self):
        html = ''
        for row_no in range(self.tableWidget_doctor_summary.rowCount()):
            td = ''
            for col_no in range(self.tableWidget_doctor_summary.columnCount()):
                value = self.tableWidget_doctor_summary.item(row_no, col_no).text()

                if col_no == 0:
                    align = 'center'
                    value = self.tableWidget_doctor_summary.item(row_no, col_no).text()
                    if len(value) >= 10:
                        value = value[5:10]
                else:
                    align = 'right'

                if row_no % 2 == 1:
                    td += f'<td bgcolor="#F4F6F7" style="text-align: {align}; padding: 2px;">{value}</td>'
                else:
                    td += f'<td style="text-align: {align}; padding: 2px">{value}</td>'

            html += f'<tr>{td}</tr>'

        return html

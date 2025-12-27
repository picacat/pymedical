
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils


# 列印醫師自費銷售金額總表 2022.02.23
class PrintDoctorSaleSummary:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.tableWidget_prescript = args[4]
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
            f'{self.income_date}-{self.income_period}-門診現金收入報表.pdf',
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
        clinic_name = self.system_settings.field('院所名稱')
        table_prescript = self._get_table_prescript_html()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 醫師自費銷售金額總表</h2>
                    <div align="left" style="margin-left: 40px">
                        統計日期: {self.start_date[:10]} 至 {self.end_date[:10]}
                    </div>
                    <br>
                    {table_prescript}
                </body>
            </html>
        '''

        return html

    def _get_table_prescript_html(self):
        doctor_th = self._get_doctor_th()
        medicine_type_th = self._get_medicine_type_th()
        income_rows = self._get_income_rows()

        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th rowspan="2">日期</th>
                        {doctor_th}
                    </tr>
                    <tr>
                        {medicine_type_th}
                    </tr>
                </thead>
                <tbody>
                    {income_rows}
                </tbody>
            </table>
        '''

        return html

    def _get_income_rows(self):
        income_rows = ''

        for col_no in range(2, self.tableWidget_prescript.columnCount()):
            case_date = self.tableWidget_prescript.horizontalHeaderItem(col_no).text()
            td_value = self._get_td_value(col_no)

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and col_no % 2 > 0:
                bg_color = ' bgcolor="#E3E3E3"'

            income_rows += f'''
                <tr{bg_color}>
                    <td>{case_date}</td>
                    {td_value}
                </tr>
            '''
        return income_rows

    def _get_td_value(self, col_no):
        row_count = self.tableWidget_prescript.rowCount()

        td_value = ''
        for row_no in range(row_count):
            item = self.tableWidget_prescript.item(row_no, col_no)
            if item is None:
                td_value += '<td></td>'
            else:
                td_value += f'<td align="right">{item.text()}</td>'

        return td_value

    def _get_doctor_th(self):
        row_count = self.tableWidget_prescript.rowCount()
        doctor_th = ''

        doctor_count = 0
        for row_no in range(row_count):
            item = self.tableWidget_prescript.item(row_no, 0)
            if item is not None:
                doctor_count += 1

        colspan = row_count // doctor_count

        for row_no in range(row_count):
            item = self.tableWidget_prescript.item(row_no, 0)
            if item is None:
                continue

            doctor_th += f'<th colspan="{colspan}">{item.text()}</th>'

        return doctor_th

    def _get_medicine_type_th(self):
        row_count = self.tableWidget_prescript.rowCount()
        medicine_type_th = ''

        for row_no in range(row_count):
            item = self.tableWidget_prescript.item(row_no, 1)
            if item is None:
                continue

            medicine_type_th += f'<th>{item.text()}</th>'

        return medicine_type_th

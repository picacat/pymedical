
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils


# 列印結帳日報表
# 2019.03.38
class PrintGrowthIncome:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.tableWidget_income_list = args[2]
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

        self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')
        table_income = self._get_table_income_html()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 年度收入統計表</h2>
                    {table_income}
                </body>
            </html>
        '''

        return html

    def _get_income_rows(self):
        income_rows = ''

        for row_no in range(self.tableWidget_income_list.rowCount()):
            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and row_no % 2 > 0:
                bg_color = ' bgcolor="#E3E3E3"'

            income_rows += f'''
                <tr{bg_color}>
                    <td align=center>{self.tableWidget_income_list.item(row_no, 0).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 1).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 2).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 3).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 4).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 5).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 6).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 7).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 8).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 9).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 10).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 11).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 12).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 13).text()}</td>
                    <td align=right>{self.tableWidget_income_list.item(row_no, 14).text()}</td>
                </tr>
            '''
        return income_rows

    def _get_table_income_html(self):
        income_rows = self._get_income_rows()
        html = f'''
            <table align=center cellpadding="4" cellspacing="10" width="95%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>月份</th>
                        <th>健保人次</th>
                        <th>一般自費</th>
                        <th>自購</th>
                        <th>民俗</th>
                        <th>人次合計</th>
                        <th>免掛號費人次</th>
                        <th>免診負人次</th>
                        <th>免藥負人次</th>
                        <th>掛號費收入</th>
                        <th>內/首掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負擔</th>
                        <th>自費金額</th>
                        <th>總收入</th>
                    </tr>
                </thead>
                <tbody>
                    {income_rows}
                </tbody>
            </table>
        '''

        return html

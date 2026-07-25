
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils


# 列印結帳日報表
# 2019.03.38
class PrintIncomeInsList:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.income_date = args[2]
        self.income_period = args[3]
        self.tableWidget_income = args[4]
        self.tableWidget_free_count = args[5]
        self.tableWidget_summary = args[6]
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

        # self.printer.setOrientation(QPrinter.Portrait)
        self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')
        income_table = self._get_income_table()
        free_table = self._get_free_table()
        summary = self._get_summary()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 掛號收費統計表</h2>
                    <div align="left" style="margin-left: 10px">
                        統計日期: {self.income_date[:10]} {self.income_period}<br><br>
                        收費統計
                    </div>
                    {income_table}
                    <br>
                    <div align="left" style="margin-left: 10px">
                        免收費統計
                    </div>
                    {free_table}
                    <br>
                    <div align="left" style="margin-left: 10px">
                        合計
                    </div>
                    {summary}
                </body>
            </html>
        '''

        return html

    def _get_income_table(self):
        income_header = self._get_income_header()
        income_body = self._get_income_body()

        html = f'''
            <table cellpadding="0" cellspacing="0" width="100%"
                style="border-width: 1px; border-style: solid;">
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
        for col_no in range(self.tableWidget_income.columnCount()):
            header = self.tableWidget_income.horizontalHeaderItem(col_no).text()
            th += f'<th style="text-align: center; padding: 2px">{header}</th>'

        html = f'<tr bgcolor="LightGray">{th}</tr>'

        return html

    def _get_income_body(self):
        html = ''
        for row_no in range(self.tableWidget_income.rowCount()):
            td = ''
            for col_no in range(self.tableWidget_income.columnCount()):
                if col_no == 0:
                    align = 'left'
                else:
                    align = 'right'

                value = self.tableWidget_income.item(row_no, col_no).text()
                td += f'<td style="text-align: {align}; padding: 2px">{value}</td>'

            html += f'<tr>{td}</tr>'

        return html

    def _get_free_table(self):
        free_header = self._get_free_header()
        free_body = self._get_free_body()

        html = f'''
            <table cellpadding="0" cellspacing="0" width="100%"
                style="border-width: 1px; border-style: solid;">
                <thead>
                    {free_header}
                </thead>
                <tbody>
                    {free_body}
                </tbody>
            </table>
        '''

        return html

    def _get_free_header(self):
        html = ''
        header1 = []
        header2 = []
        for row_no in range(2):
            for col_no in range(self.tableWidget_free_count.columnCount()):
                item = self.tableWidget_free_count.item(row_no, col_no)
                if item is None:
                    continue

                if row_no == 0:
                    header1.append(item.text())
                else:
                    header2.append(item.text())

        th_list1 = []
        for cell_no, cell in enumerate(header1):
            if cell != '0':  # 第一個元素一定要確定不是 '0'
                col_span = 1
                header = cell
                if cell_no == 0:
                    th_list1.append(
                        f'''<th rowspan="2" style="text-align: center; vertical-align: middle; padding: 2px">
                                {header}
                            </th>
                        '''
                    )
                else:
                    th_list1.append(f'<th style="text-align: center; padding: 2px">{header}</th>')
            else:
                del th_list1[-1]
                col_span += 1
                th_list1.append(f'<th colspan="{col_span}" style="text-align: center; padding: 2px">{header}</th>')

        html = f'<tr bgcolor="LightGray">{"".join(th_list1)}</tr>'

        th_list2 = []
        for header in header2:
            th_list2.append(f'<th style="text-align: center; padding: 2px">{header}</th>')

        html += f'<tr bgcolor="LightGray">{"".join(th_list2)}</tr>'

        return html

    def _get_free_body(self):
        html = ''
        for row_no in range(2, self.tableWidget_free_count.rowCount()):
            td = ''
            for col_no in range(self.tableWidget_free_count.columnCount()):
                if col_no == 0:
                    align = 'left'
                else:
                    align = 'right'

                value = self.tableWidget_free_count.item(row_no, col_no).text()
                td += f'<td style="text-align: {align}; padding: 2px">{value}</td>'

            html += f'<tr>{td}</tr>'

        return html

    def _get_summary(self):
        summary_header = self._get_summary_header()
        summary_body = self._get_summary_body()

        html = f'''
            <table cellpadding="0" cellspacing="0" width="100%"
                style="border-width: 1px; border-style: solid;">
                <thead>
                    {summary_header}
                </thead>
                <tbody>
                    {summary_body}
                </tbody>
            </table>
        '''

        return html

    def _get_summary_header(self):
        th = ''
        for row_no in range(self.tableWidget_summary.rowCount()):
            header = self.tableWidget_summary.verticalHeaderItem(row_no).text().split(' ')
            header = '<br>'.join(header)
            th += f'<th style="text-align: center; vertical-align: middle; padding: 2px">{header}</th>'

        html = f'<tr bgcolor="LightGray">{th}</tr>'

        return html

    def _get_summary_body(self):
        html = ''
        td = ''
        for row_no in range(self.tableWidget_summary.rowCount()):
            value = self.tableWidget_summary.item(row_no, 0).text()
            td += f'<td style="text-align: right; padding: 2px">{value}</td>'

        html += f'<tr>{td}</tr>'

        return html

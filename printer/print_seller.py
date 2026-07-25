
# -*- coding: UTF-8 -*-

from libs import number_utils, printer_utils, purchase_utils, system_utils
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog


# 列印銷售總表
# 2025.11.13
class PrintSeller:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.tableWidget_seller = args[4]
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
            f'{self.income_date}-{self.income_period}-自費銷售明細.pdf',
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

        seller_list = self._get_seller_html()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 自費抽成總表</h2>
                    <div align="left" style="margin-left: 40px">
                      統計日期: 從 {self.start_date[:10]} 至 {self.end_date[:10]}
                    </div>
                    {seller_list}
                </body>
            </html>
        '''

        return html

    def _get_seller_html(self):
        tr = ''
        th = ''
        width = 60
        for col_no in range(2, self.tableWidget_seller.columnCount()):
            sell_date = self.tableWidget_seller.horizontalHeaderItem(col_no).text()

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and col_no % 2 > 0:
                bg_color = ' bgcolor="#e3e3e3"'

            td = f'<td align=center width="{width}">{sell_date}</td>'
            th = f'<th align=center width="{width}">日期</th>'            
            for row_no in range(self.tableWidget_seller.rowCount()):
                seller= self.tableWidget_seller.item(row_no, 0).text()
                amount= self.tableWidget_seller.item(row_no, col_no).text()
                th += f'<td align=center width="{width}">{seller}</td>'
                td += f'<td align=right width="{width}">{int(amount):,}</td>'
                
            tr += f'''
                <tr{bg_color}>
                    {td}
                </tr>
            '''

        html = f'''
            <table width="98%" style="table-layout: fixed">
             <thead >
              <tr bgcolor="lightgray">
               {th}
               </tr>
             </thead>
             <tbody>
              {tr}
             </tbody>
           </table>
        '''
            
        return html


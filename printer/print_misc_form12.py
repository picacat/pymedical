
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils


# 自費醫療收據
# 2023.06.28 陳立德
class PrintMiscForm12:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.printer = args[3]
        self.ui = None

        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)

        self.current_print = None

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

    def print_html(self, printing=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT Doctor, TotalFee FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return '查無此病歷'

        row = rows[0]
        doctor = string_utils.xstr(row['Doctor'])
        total_fee = number_utils.get_integer(row['TotalFee'])

        case_record = printer_utils.get_case_html_2(
            self.database, self.case_key, '自費', tw_date=True, birthday_mask=False)
        # fees_record = printer_utils.get_fees_html(self.database, self.case_key)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        html = f'''
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: center;" colspan="5">
                        自費費用收據
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                自費金額: {total_fee}
                <hr style="line-height:0.5">
                醫師: {doctor}<br>
                院所: {clinic_id} {clinic_name}<br>
                院址: {clinic_address}<br>
                電話: {clinic_telephone}<br><br>
                * 本收據請妥善保存, 遺失恕不補發
              </body>
            </html>
        '''

        return html

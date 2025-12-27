
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import string_utils


# 醫囑單 4.4 x 3.0 inches
# 2020.09.01 馥林
class PrintMiscForm3:
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
        self.printer.setPaperSize(QtCore.QSizeF(4.4, 3.0), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        case_record = printer_utils.get_case_html_2(
            self.database, self.case_key, '健保', birthday_mask=False, tw_date=True
        )

        order_record = self._get_order_record()

        clinic_name = self.system_settings.field('院所名稱')
        # clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        html = f'''
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr style="text-align: center;">
                      <th colspan="4" align="center">{clinic_name} 醫囑單</th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                <table cellspacing="0">
                  <thead>
                    <tr>
                      <th width="10%">項次</th>
                      <th align="left" width="80%">醫囑內容</th>
                    </tr>
                  </thead>
                  <tbody>
                    {order_record}
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                院址: {clinic_address} 電話: {clinic_telephone}
                <h4>{clinic_name} 關心您!</h4>
              </body>
            </html>
        '''

        return html

    def _get_order_record(self):
        sql = f'''
            SELECT Content FROM caseextend
            WHERE
                CaseKey = {self.case_key} AND
                ExtendType = "醫囑"
        '''
        rows = self.database.select_record(sql)

        html = ''
        for row_no, row in zip(range(1, len(rows)+1), rows):
            html += f'''
                <tr>
                  <td align="center">{row_no}</td>
                  <td>{string_utils.xstr(row['Content'])}</td>
                </tr>
            '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils


# 健保格式醫療費用收據 80mm 熱敢紙
# 2024.05.14
class PrintMiscForm14:
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
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 148, QPrinter.Millimeter, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_14(self.database, self.case_key, '全部')
        fees_record = printer_utils.get_fees_html14(self.database, self.case_key)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')

        html = f'''
            <html>
              <body>
                <b>
                <br>
                <font size="5">{clinic_name} 醫療費用收據</font>
                <br>
                院所機構代號: {clinic_id}
                <table cellspacing="0">
                  <tbody>
                    <tr><td></td><td></td></tr>
                    {case_record}
                  </tbody>
                </table>
                <br>
                <table cellspacing="0" style="border-width: 1px; border-style: solid">
                  <thead>
                    <tr>
                        <th>健保申報項目</th>
                        <th>點數</th>
                        <th>自付費用項目</th>
                        <th>金額</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fees_record}
                  </tbody>
                </table>
                <br><br>
                院址:{clinic_address}<br>
                電話:{clinic_telephone}
                </b>
              </body>
            </html>
        '''

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils


# 健保處方箋格式3 4.5 x 3 inches
# 2019.02.14
class PrintPrescriptionSelfForm3:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '自費處方箋印表機')
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
        self.font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 90)

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

        height = 3.00
        if self.system_settings.field('院所名稱') == '板橋聖昌中醫診所':
          height = 3.66

        self.printer.setPaperSize(QtCore.QSizeF(4.5, height), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 13)
        if printing:
            document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html(
          self.database, self.case_key, birthday_mask=False, tw_date=True, id_mask=True,
          ins_type='自費', medicine_set=self.medicine_set,
        )
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '處方箋', blocks=2)
        instruction = printer_utils.get_instruction_html1_1(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )

        html = f'''
            <html>
              <body>
                <table width="98%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <b>------------------------------------------------------------------------</b>
                <table width="98%" cellspacing="0">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <br>
                <b>------------------------------------------------------------------------</b><br>
                {instruction}
              </body>
            </html>
        '''

        return html

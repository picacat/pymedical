
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils


# 友杏健保處方箋格式3 4.5 x 3 inches
# 2023.08.17
class PrintPrescriptionInsForm8:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.medicine_set = 1

        self.printer = printer_utils.get_printer(self.system_settings, '健保處方箋印表機')

        self.current_print = None
        self.additional = None

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
        self.font = QtGui.QFont(font, 9, QtGui.QFont.PreferQuality)
        self.font.setLetterSpacing(QtGui.QFont.PercentageSpacing, 95)

    def _set_signal(self):
        pass

    def _check_printing(self):
        printing = True

        if self.additional == '健保另包':
            if printer_utils.is_additional_prescript(self.database, self.case_key):
                printing = True
            else:
                printing = False

        return printing

    def print(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        self.print_html(True)

    def preview(self, additional=None):
        self.additional = additional
        if not self._check_printing():
            return

        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        preview_dialog.paintRequested.connect(self.print_html)
        preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        preview_dialog.exec_()

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
        case_record = printer_utils.get_case_html_utec(
            self.database, self.case_key, '健保', tw_date=True, birthday_mask=False, id_mask=False,
            medicine_set=self.medicine_set)
        symptom_record = printer_utils.get_symptom_html(self.database, self.system_settings, self.case_key, colspan=3)
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set, '處方箋', blocks=2, instruction=self.additional)
        instruction = printer_utils.get_instruction_html_utec(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        additional_label = printer_utils.get_additional_label(self.additional)

        html = f'''
            <html>
              <body>
                <table width="98%" cellspacing="0">
                  <tbody>
                    {case_record}
                    <tr>
                      <td colspan="3">{disease_record}</td>
                    </tr>
                    {symptom_record}
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                <table width="98%" cellspacing="0">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <br><hr>
                {instruction}
                {additional_label}
              </body>
            </html>
        '''

        return html

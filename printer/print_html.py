
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils


# 列印 HTML
# 2019.10.21
class PrintHtml:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.html = args[2]
        self.orientation = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
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

    def save_to_pdf(self, filename):
        options = QFileDialog.Options()
        pdf_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "另存PDF檔案",
            filename,
            "pdf檔案 (*.pdf);;Text Files (*.txt)", options=options
        )
        if not pdf_filename:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_filename)
        self.print_html(True)

    def print_html(self, printing):
        self.current_print = self.print_html
        if self.orientation == 'landscape':
            self.printer.setOrientation(QPrinter.Landscape)
        else:
            self.printer.setOrientation(QPrinter.Portrait)

        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self.html)
        if printing:
            document.print(self.printer)

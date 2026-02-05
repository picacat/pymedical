# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils, system_utils


# 健保處方箋格式5 6.5 x 2.5 inches
# 2019.07.03 明醫
class PrintReceiptInsForm5:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.medicine_set = 1

        self.printer = printer_utils.get_printer(
            self.system_settings, "健保醫療收據印表機"
        )

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
        self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def _check_printing(self):
        printing = True

        if self.additional == "健保另包":
            if printer_utils.is_additional_prescript(self.database, self.case_key):
                printing = True
            else:
                printing = False

        if self.additional == "健保檢驗":
            if printer_utils.is_ins_examination(self.database, self.case_key):
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
        # self.printer.setPaperSize(QtCore.QSizeF(7.2, 2.5), QPrinter.Inch)
        printer_utils.set_paper_size(
            self.printer, self.system_settings, 7.2, 2.5, QPrinter.Inch, "健保醫療收據"
        )

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 13)
        if printing:
            document.print(self.printer)

    def _html(self):
        title = "醫療費用收據"

        case_record = printer_utils.get_case_html_1(
            self.database, self.case_key, "健保", print_time_label=True
        )
        disease_record = printer_utils.get_disease2(
            self.database, self.system_settings, self.case_key
        )
        prescript_record = printer_utils.get_prescript_html(
            self.database,
            self.system_settings,
            self.case_key,
            self.medicine_set,
            "費用收據",
            blocks=2,
            instruction=self.additional,
        )
        instruction = printer_utils.get_instruction_html(
            self.database,
            self.system_settings,
            self.case_key,
            self.medicine_set,
            self.additional,
            resize_instruction=True,
        )
        additional_label = printer_utils.get_additional_label(self.additional)
        if self.additional == "健保檢驗":
            title = "檢驗單"
            additional_label = ""

        clinic_name = self.system_settings.field("院所名稱")
        clinic_id = self.system_settings.field("院所代號")
        clinic_telephone = self.system_settings.field("院所電話")
        clinic_address = self.system_settings.field("院所地址")

        # case_key_barcode = printer_utils.get_case_key_barcode(self.case_key)

        html = f"""
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left;" colspan="5">
                        {clinic_name}({clinic_id}) {title}
                        <font style="font-size: 9px">
                          院址:{clinic_address} 電話:{clinic_telephone}
                        </font>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <hr style="line-height:0.5">
                <table cellspacing="0">
                  <tbody>
                      {prescript_record}
                  </tbody>
                  <hr width="0%" style="line-height: 0.0">
                </table>
                <hr style="line-height:0.5">
                {instruction}
                {additional_label}<br>
                適應症: {disease_record}<br>
                副作用: 本處方用藥在醫學文獻上尚無副作用之記載 / 保存方式: 置於乾燥陰涼處 / 保存期限: 三個月<br>
              </body>
            </html>
        """

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils


# 健保處方箋格式2 8.5 x 2 inches
# 2018.10.09
class PrintReceiptInsForm10:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None
        self.medicine_set = 1

        self.printer = printer_utils.get_printer(self.system_settings, '健保醫療收據印表機')

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
        # self.printer.setPaperSize(QtCore.QSizeF(7.8, 2.5), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 7.8, 2.5, QPrinter.Inch, '健保醫療收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 12)
        if printing:
            document.print(self.printer)

    def _html(self):
        case_record = printer_utils.get_case_html_1(self.database, self.case_key, '健保')
        # symptom_record = printer_utils.get_symptom_html(
        #     self.database, self.system_settings, self.case_key, colspan=5
        # )
        disease_record = printer_utils.get_disease(self.database, self.case_key)
        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings,
            self.case_key, self.medicine_set,
            '費用收據', blocks=3, instruction=self.additional)
        instruction = printer_utils.get_instruction_html(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        fees_record = printer_utils.get_ins_fees_html(self.database, self.case_key)
        additional_label = printer_utils.get_additional_label(self.additional)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        disease_name = printer_utils.get_disease_name(self.database, self.system_settings, self.case_key)

        html = f'''
            <html>
              <body>
                <table style="font-size: 10px" width="95%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left; font-size: 10px" colspan="5">
                        {clinic_name}({clinic_id}) 醫療費用收據 (電話:{clinic_telephone} 院址:{clinic_address})
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <font style="font-size: 10px">{disease_record}</font>
                <hr style="line-height:0.5">
                <table style="font-size: 10px" cellspacing="0">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <font style="font-size: 10px">{instruction}</font>
                {additional_label}
                <hr style="line-height:0.5">
                <table style="font-size: 10px" width="90%" cellspacing="0">
                  <tbody>
                    {fees_record}
                  </tbody>
                </table>
                <font style="font-size: 10px">
                    警語: 本藥品無其他副作用, 適應症: {disease_name}<br>
                    * 本收據可為報稅之憑證, 請妥善保存, 遺失恕不補發 (健保申報為健保總額支付點數, 非一點一元)
                </font>
              </body>
            </html>
        '''

        return html

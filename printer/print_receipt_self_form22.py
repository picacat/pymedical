# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils, string_utils, system_utils


# 自費收據格式7 105x148mm
# 2023.12.29 天地精進
class PrintReceiptSelfForm22:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "自費醫療收據印表機"
        )
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
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(105, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(
            self.printer,
            self.system_settings,
            105,
            148,
            QPrinter.Millimeter,
            "自費醫療收據",
        )

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(10)
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        case_record = printer_utils.get_case_html_10(
            self.database,
            self.case_key,
            "自費",
            tw_date=True,
            medicine_set=self.medicine_set,
        )
        prescript_record = printer_utils.get_prescript_html22(
            self.database,
            self.system_settings,
            self.case_key,
            self.medicine_set,
            "費用收據",
            blocks=1,
            print_total_dosage="Y",
        )
        fees_record = printer_utils.get_self_fees_html_2(self.database, self.case_key)
        instruction = printer_utils.get_instruction_html4(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )

        prescript_html = f"""
            <table width="100%" style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="2" border="1">
              <thead>
                <tr>
                  <th align="left" width="15%">位置</th>
                  <th align="left">處方名稱</th>
                  <th align="right" width="15%">劑量</th>
                  <th align="right" width="12%">總量</th>
                  <th align="left" width="15%">服法</th>
                </tr>
              </thead>
              <tbody>
                {prescript_record}
              </tbody>
            </table>
           {instruction}
        """

        if self.medicine_set is None:
            prescript_html = "無處方"

        if self.medicine_set is None or self.medicine_set >= 3:
            fees_record = ""
            remark = ""

        clinic_name = self.system_settings.field("院所名稱")
        clinic_id = self.system_settings.field("院所代號")
        clinic_telephone = self.system_settings.field("院所電話")
        clinic_address = self.system_settings.field("院所地址")

        html = f"""
            <html>
              <body>
                <table width="100%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left" colspan="4">
                        {clinic_name}({clinic_id}) 醫療費用收據
                      </th>
                    </tr>
                    <tr>
                      <th style="text-align: left; font-size: 12px" colspan="4">
                        電話:{clinic_telephone} 院址:{clinic_address}
                      </th>
                    </tr>
                  </thead>
                </table>
                <table width="100%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <br>
                {prescript_html}
                <hr style="line-height:0.5">
                <table width="100%" cellspacing="0">
                  <tbody>
                    {fees_record}
                  </tbody>
                </table>
                <br>
                <hr style="line-height:0.5">
                收款人: {string_utils.xstr(row["Doctor"])}<br>
                警語: 請勿與其它藥品混合服用<br>
                副作用: 本處方於醫學文獻中尚無副作用之記載<br>
                * 請妥善保存，遺失恕不補發<br>
              </body>
            </html>
        """

        return html

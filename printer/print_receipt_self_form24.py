# -*- coding: UTF-8 -*-

import sys

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import case_utils, printer_utils, system_utils


# 自費收據格式23 熱感80mm(客制) 日知堂
# 2024.04.03
class PrintReceiptSelfForm24:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.print_dosage = args[4]
        self.ui = None
        self.print_no_dosage = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "自費醫療收據印表機"
        )
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)

        self.current_print = None

        if sys.platform == "darwin":
            dash_count = 34
        else:
            dash_count = 36

        self.dash_line = "-" * dash_count

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
        self.font = QtGui.QFont(font, 11, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def print(self, print_no_dosage=None):
        self.print_no_dosage = print_no_dosage
        self.print_html(True)

    def preview(self):
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_to_pdf(self):
        sql = f"""
          SELECT CaseDate, Name FROM cases
          WHERE
            CaseKey = {self.case_key} 
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        medicine_set = self.medicine_set
        if self.medicine_set >= 2:
            medicine_set -= 1

        pdf_file_name = (
            f"{row['CaseDate'].date()}{row['Name']}自費費用收據-{medicine_set}.pdf"
        )

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent.parent,
            "匯出自費費用收據pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)",
            options=options,
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QMessageBox.Information,
            "匯出完成",
            '<font size="5" color="red"><b>自費費用收據已匯出完成</b></font>',
            "",
        )

    def print_html(self, printing=None):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(72, 148), QPrinter.Millimeter)
        printer_utils.set_paper_size(
            self.printer,
            self.system_settings,
            72,
            300,
            QPrinter.Millimeter,
            "自費醫療收據",
        )

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 15)
        if printing:
            document.print(self.printer)

    def _get_fees_html(self):
        fees_record = printer_utils.get_self_fees_html_dynamic(
            self.database,
            self.system_settings,
            self.case_key,
            self.medicine_set,
            width=1,
        )

        if self.system_settings.field("不印報稅提示") == "Y":
            remark = ""
        else:
            remark = self.system_settings.field("醫療費用收據自訂報稅備註")
            if remark in ["", None]:
                remark = "本收據可為報稅憑證, 遺失恕不補發"

        html = f"""
          {self.dash_line}
          <table width="100%" cellspacing="0">
            <tbody>
              {fees_record}
            </tbody>
          </table>
          {self.dash_line}<br>
          {remark}
        """

        if self.medicine_set is None:
            html = f"{self.dash_line}<br>"

        return html

    def _html(self):
        case_record = printer_utils.get_case_html_23(
            self.database, self.case_key, "自費", tw_date=True
        )
        prescript_record = printer_utils.get_prescript_html23(
            self.database,
            self.system_settings,
            self.case_key,
            self.medicine_set,
            "費用收據",
            blocks=1,
            print_total_dosage="Y",
            print_dosage=self.print_dosage,
        )

        if (
            self.system_settings.field("列印所有收費收據費用明細") == "Y"
            or self.medicine_set == 2
        ):
            fees_record = self._get_fees_html()
        else:
            fees_record = ""

        instruction = printer_utils.get_instruction_html_0(
            self.database, self.system_settings, self.case_key, self.medicine_set
        )
        pres_days = case_utils.get_pres_days(
            self.database, self.case_key, self.medicine_set
        )

        disease_name = printer_utils.get_disease_name(
            self.database, self.system_settings, self.case_key
        )
        if disease_name not in ["", None]:
            disease_name_html = f"<br>適應症:{disease_name}"
        else:
            disease_name_html = ""

        if pres_days > 0:
            warning = "<br>警語:本藥品無其他副作用<br>"
        else:
            warning = "<br>"

        prescript_header = """
          <th align="center">序</th>
          <th align="left">處方名稱</th>
          <th align="right">劑量</th>
          <th align="right">總量</th>
        """

        if not self.print_dosage:
            prescript_header = """
              <th align="center">序</th>
              <th align="left">處方名稱</th>
            """

        prescript_html = f"""
            <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="2" border="1">
              <thead>
                <tr>
                  {prescript_header}
                </tr>
              </thead>
              <tbody>
                {prescript_record}
              </tbody>
            </table>
           <br><br>{instruction}
           {disease_name_html}
           {warning}
        """

        if self.system_settings.field("費用收據不印處方") == "Y":
            prescript_html = ""
        elif self.medicine_set is None:
            prescript_html = "無處方"

        clinic_name = self.system_settings.field("院所名稱")
        clinic_id = self.system_settings.field("院所代號")
        clinic_telephone = self.system_settings.field("院所電話")
        clinic_address = self.system_settings.field("院所地址")
        receipt_title_image = printer_utils.get_title_image(
            clinic_name, clinic_id, clinic_telephone, clinic_address
        )

        html = f"""
            <html>
              <body>
                {receipt_title_image}
                <b>
                <table width="98%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                {prescript_html}
                {fees_record}
              </b>
              <br><br>
              </body>
            </html>
        """

        if self.system_settings.field("醫療費用收據不印粗體") == "Y":
            html = html.replace("<b>", "").replace("</b>", "")

        return html

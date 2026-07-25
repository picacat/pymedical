# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import class_utils, printer_utils, system_utils


# 其他收據格式21 二維條碼處方箋
# 2023.10.23
class PrintMiscForm21:
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
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
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
        case_record = printer_utils.get_case_html_8(
            self.database, self.case_key, "全部", mask_name=True
        )
        clinic_name = self.system_settings.field("院所名稱")
        clinic_id = self.system_settings.field("院所代號")
        clinic_telephone = self.system_settings.field("院所電話")
        clinic_address = self.system_settings.field("院所地址")

        hca_api = class_utils.get_hca_api(self.database, self.system_settings)
        doctor_cert, prescript_cert = hca_api.get_cert(self.case_key)

        del hca_api

        try:
            doctor_qr_code = system_utils.get_qrcode_b64png(doctor_cert)
        except Exception:
            doctor_qr_code = ""

        try:
            prescript_qr_code = system_utils.get_qrcode_b64png(prescript_cert)
        except Exception:
            prescript_qr_code = ""

        html = f"""
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left;" colspan="3">
                        {clinic_name}({clinic_id}) 二維條碼處方箋
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <br><br><br><br><br><br><br><br><br><br><br>
                <center>
                <img src="data:;base64,{doctor_qr_code}" alt="" height="150" width="150">
                <img src="data:;base64,{prescript_qr_code}" alt="" height="150" width="150">
                </center>
                <p>院址:{clinic_address} 電話:{clinic_telephone}</p>
              </body>
            </html>
        """

        return html

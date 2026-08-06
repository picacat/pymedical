# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import number_utils, printer_utils, string_utils, system_utils


# 民俗調理格式12 2.5"套表民俗調理單
# 使用診所: 佳禾系列
# 2021.12.20
class PrintMassageForm12:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "民俗調理單印表機"
        )
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None
        self.return_card = None

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

    def print(self, return_card=None):
        self.return_card = return_card
        self.print_html(True)
        # database.print_painter()

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(5, 2.5), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, "print test line1 中文測試")
        painter.drawText(0, 30, "print test line2 中文測試")
        painter.end()

    def print_html(self, printing, return_card=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(5, 2.5), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _get_case_row(self, case_key):
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {case_key}
        """
        row = self.database.select_record(sql)[0]

        if string_utils.xstr(row["TreatType"]) != "民俗調理":
            sql = f'''
                SELECT * FROM cases
                WHERE
                    Position1 = "{case_key}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return

            row = rows[0]

        return row

    def _html(self):
        row = self._get_case_row(self.case_key)

        clinic_telephone = self.system_settings.field("院所電話")
        patient_key = string_utils.xstr(row["PatientKey"])
        patient_name = string_utils.xstr(row["Name"])
        registration_no = string_utils.xstr(row["RegistNo"])
        room = string_utils.xstr(row["Room"])
        massager = string_utils.xstr(row["Massager"])
        case_date = string_utils.xstr(row["CaseDate"].date())
        case_time = string_utils.xstr(row["CaseDate"].time())[:5]

        regist_fee = number_utils.get_integer(row["RegistFee"])
        massage_fee = number_utils.get_integer(row["SMassageFee"])
        total_fee = regist_fee + massage_fee

        if regist_fee == 0:
            regist_fee = ""

        html = f"""
            <html>
                <body>
                    <p style="font-size:16px"><b>民俗調理 {clinic_telephone}</b></p>
                    <table style="margin-left:28px" cellspacing=16 cellpadding=0>
                        <tr>
                            <td width="30%" style="font-size: 16px; text-align: center">
                                {patient_name}
                            </td>
                            <td width="50%" style="font-size: 16px; text-align: center">
                            </td>
                            <td width="30%" style="font-size: 16px; text-align: left">
                                <b>{room}</br>
                            </td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">{patient_key}</td>
                            <td width="40%" style="text-align:center">{regist_fee}</td>
                            <td width="30%" style="text-align:left">{registration_no}</td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align:center">{case_date}</td>
                            <td width="40%" style="text-align:center">{massage_fee}</td>
                            <td width="30%" style="text-align:left"></td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">{case_time}</td>
                            <td width="40%" style="text-align:center"></td>
                            <td width="30%" style="text-align:left"></td>
                        </tr>
                        <tr>
                            <td width="30%" style="text-align: center">自費</td>
                            <td width="40%" style="text-align:center">{total_fee}</td>
                            <td width="30%" style="text-align:left">{massager}</td>
                        </tr>
                    </table>
                </body>
            </html>
        """

        return html

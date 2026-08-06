# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import date_utils, number_utils, printer_utils, string_utils, system_utils


# 掛號收據格式9 3"套表掛號單 (禾生堂簡易版)
# 2020.10.15
class PrintRegistrationForm9:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(
            self.system_settings, "門診掛號單印表機"
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
        self.font = QtGui.QFont(font, 12, QtGui.QFont.PreferQuality)

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
        self.printer.setPaperSize(QtCore.QSizeF(5, 3), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, "print test line1 中文測試")
        painter.drawText(0, 30, "print test line2 中文測試")
        painter.end()

    def print_html(self, printing, return_card=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _get_massager(self, case_row):
        massager = string_utils.xstr(case_row["Massager"])

        if massager == "":
            sql = f'''
                SELECT Massager FROM cases
                WHERE
                    Position1 = "{self.case_key}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) >= 1:
                row = rows[0]
                massager = string_utils.xstr(row["Massager"])

        return massager

    def _html(self):
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        row = self.database.select_record(sql)[0]

        card = string_utils.xstr(row["Card"])
        if number_utils.get_integer(row["Continuance"]) >= 1:
            card += "-" + string_utils.xstr(row["Continuance"])

        if self.system_settings.field("列印院所名稱") == "Y":
            clinic_name = self.system_settings.field("院所名稱")
            clinic_telephone = f"電話: {self.system_settings.field('院所電話')}"
        else:
            clinic_name = ""
            clinic_telephone = ""

        # patient_key = string_utils.xstr(row['PatientKey'])
        patient_name = string_utils.xstr(row["Name"])
        registration_no = string_utils.xstr(row["RegistNo"])
        # room = string_utils.xstr(row['Room'])
        # ins_type = string_utils.xstr(row['InsType'])
        # regist_fee = string_utils.xstr(row['RegistFee'])
        # deposit_fee = string_utils.xstr(row['DepositFee'])
        case_date = date_utils.west_date_to_nhi_date(row["CaseDate"].date(), "-")
        # share = string_utils.xstr(row['Share'])
        period = string_utils.xstr(row["Period"])
        # diag_share_fee = string_utils.xstr(row['SDiagShareFee'])
        massager = self._get_massager(row)

        html = f"""
            <html>
                <body>
                    <p style="font-size:22px; margin-left: 50px">
                        <b>{clinic_name}<br>
                        {clinic_telephone}</b>
                    </p>
                    <br>
                    <table cellspacing=16 cellpadding=8>
                        <tr>
                            <td width="30%" style="font-size: 24px; text-align: center">
                            </td>
                            <td width="40%" style="font-size: 24px; text-align: center" colspan="3">
                                {patient_name}
                            </td>
                            <td width="30%" style="font-size: 24px; text-align: center">
                                <b>{registration_no}</br>
                            </td>
                        </tr>
                    </table>
                    <br>
                    <table cellspacing=0 cellpadding=8>
                        <tr>
                            <td width="20%" style="text-align: center"></td>
                            <td width="15%"></td>
                            <td width="20%" style="text-align:center"></td>
                            <td width="15%" style="text-align:right"></td>
                            <td width="25%" style="text-align:center">{case_date}</td>
                        </tr>
                    </table>
                    <table cellspacing=0 cellpadding=8>
                        <tr>
                            <td width="20%"></td>
                            <td width="30%">({massager})</td>
                            <td width="30%">班別:{period}</td>
                            <td width="20%"></td>
                        </tr>
                    </table>
                </body>
            </html>
        """

        return html

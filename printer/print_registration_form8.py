# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter

from libs import (
    number_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
)


# 掛號收據格式8 3"空白掛號單
# 2020.04.14
class PrintRegistrationForm8:
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
        self.printer.setPaperSize(QtCore.QSizeF(5, 3), QPrinter.Inch)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, "print test line1 中文測試")
        painter.drawText(0, 30, "print test line2 中文測試")
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        try:
            row = self.database.select_record(sql)[0]
        except Exception:
            return ""

        card = string_utils.xstr(row["Card"])
        if number_utils.get_integer(row["Continuance"]) >= 1:
            card += "-" + string_utils.xstr(row["Continuance"])

        if self.system_settings.field("列印院所名稱") == "Y":
            clinic_name = self.system_settings.field("院所名稱")
        else:
            clinic_name = ""

        regist_fee = number_utils.get_integer(row["RegistFee"])
        diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
        deposit_fee = number_utils.get_integer(row["DepositFee"])

        clinic_telephone = self.system_settings.field("院所電話")
        patient_key = string_utils.xstr(row["PatientKey"])
        patient_name = string_utils.xstr(row["Name"])
        registration_no = string_utils.xstr(row["RegistNo"])
        room = string_utils.xstr(row["Room"])
        ins_type = string_utils.xstr(row["InsType"])
        case_date = string_utils.xstr(row["CaseDate"].date())
        case_time = string_utils.xstr(row["CaseDate"].time())[:5]
        period = string_utils.xstr(row["Period"])
        total_fee = regist_fee + diag_share_fee + deposit_fee
        deposit_hint = ""
        title = "掛號收據"
        if "欠卡" in card:
            return_card_days = registration_utils.get_return_card_days(
                self.system_settings
            )
            deposit_hint = f"<br>* 欠卡請於{return_card_days}日內持健保卡還卡退押金"

        deposit_label = "欠卡費"
        if self.return_card == "還卡收據":
            title = "還卡收據"
            deposit_label = "還卡費"
            regist_fee = 0
            diag_share_fee = 0
            total_fee = regist_fee + diag_share_fee + deposit_fee

        html = f"""
            <html>
                <body>
                    <p style="font-size:20px;">
                        <b>
                            {clinic_name} {title}<br>
                            電話:{clinic_telephone}
                        </b>
                    </p>
                    <table width="95%" style="font-size: 18px; border-collapse: collapse;
                     border-width: 1px; border-style: solid;" cellpadding="0" cellspacing="0">
                        <tr style="font-size: 12px">
                            <td style="text-align: center;" colspan=2>病歷號碼</td>
                            <td style="text-align: center;" colspan=2>姓名</td>
                            <td style="text-align: center;" colspan=>診間</td>
                            <td style="text-align: center;" colspan=>候診號碼</td>
                        </tr>
                        <tr>
                            <td style="text-align: center; vertical-align: middle" colspan=2>
                                {patient_key}
                            </td>
                            <td style="font-size: 18px; text-align: center; vertical-align: middle" colspan=2>
                                {patient_name}
                            </td>
                            <td style="font-size: 30px; text-align: center;">
                              <b>{room}</br>
                            </td>
                            <td style="font-size: 30px; text-align: center;">
                              <b>{registration_no}</br>
                            </td>
                        </tr>
                        <tr style="font-size: 12px">
                            <td style="text-align: center;" colspan=2>保險</td>
                            <td style="text-align: center;">掛號費</td>
                            <td style="text-align: center;">部份負擔</td>
                            <td style="text-align: center;" colspan=2>門診日期</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan=2>{ins_type}</td>
                            <td style="text-align: center;">{regist_fee}元</td>
                            <td style="text-align: center;">{diag_share_fee}元</td>
                            <td style="text-align: center;" colspan=2>{case_date}</td>
                        </tr>
                        <tr style="font-size: 12px">
                            <td style="text-align: center;" colspan=2>健保卡序</td>
                            <td style="text-align: center;">{deposit_label}</td>
                            <td style="text-align: center;">合計金額</td>
                            <td style="text-align: center;">班別</td>
                            <td style="text-align: center;">時間</td>
                        </tr>
                        <tr>
                            <td style="text-align: center;" colspan=2>{card}</td>
                            <td style="text-align: center;">{deposit_fee}元</td>
                            <td style="text-align: center;">{total_fee}元</td>
                            <td style="text-align: center;">{period}</td>
                            <td style="text-align: center;">{case_time}</td>
                        </tr>
                    </table>
                    * 本收據可為報稅憑證，遺失恕不補發
                    {deposit_hint}
                </body>
            </html>
        """

        return html

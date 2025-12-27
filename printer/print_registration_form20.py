
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import string_utils
from libs import number_utils
from libs import system_utils


# 掛號收據格式20 80mm 熱感紙 自訂含二維碼
# 2024.05.09
class PrintRegistrationForm20:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '門診掛號單印表機')
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
        self.font = QtGui.QFont(font, 11, QtGui.QFont.PreferQuality)

    def _set_signal(self):
        pass

    def print(self, return_card=None):
        self.return_card = return_card
        self.print_html(True)

    def preview(self, return_card=None):
        self.return_card = return_card
        geometry = QtWidgets.QApplication.desktop().screenGeometry()

        self.preview_dialog.paintRequested.connect(self.print_html)
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_html(self, printing):
        self.current_print = self.print_html
        # self.printer.setPaperSize(QtCore.QSizeF(2.5, 5.8), QPrinter.Inch)
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 180, QPrinter.Millimeter, '掛號收據')

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        row = self.database.select_record(sql)[0]

        card = string_utils.xstr(row['Card'])
        if number_utils.get_integer(row['Continuance']) >= 1:
            card += '-' + string_utils.xstr(row['Continuance'])

        clinic_name = self.system_settings.field('院所名稱')
        case_date = row['CaseDate']
        patient_key = number_utils.get_integer(row['PatientKey'])
        name = string_utils.xstr(row['Name'])
        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])
        total_fee = regist_fee + diag_share_fee + deposit_fee

        room = string_utils.xstr(row['Room'])
        doctor = string_utils.xstr(row['Doctor'])
        regist_no = string_utils.xstr(row['RegistNo'])

        if card == '欠卡':
            total_label = f'<br>欠卡費: {str(deposit_fee)}元 實收金額: {str(total_fee)}元'
        else:
            total_label = f'<br>實收金額: {str(total_fee)}元'

        url = 'https://www.mainpi.com/query?i=2120'
        line_url = 'https://liff.line.me/1645278921-kWRPP32q/?accountId=yus0352i'
        app_qrcode = system_utils.get_qrcode_b64png(url)
        line_qrcode = system_utils.get_qrcode_b64png(line_url)

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        receipt_title_image = printer_utils.get_title_image(
            clinic_name, clinic_id, clinic_telephone, clinic_address, title='門診掛號單')

        html = f'''
            <html>
                <body>
                    {receipt_title_image}
                    <b>
                    <div>
                        病患姓名: {name}<br>
                        掛號時間: {case_date}<br>
                        保險類別: {ins_type} - {treat_type}<br>
                        掛號費: {str(regist_fee)}元 門診負擔: {str(diag_share_fee)}元
                        {total_label}
                    </div>
                    <center style="font-size:20px">{room}診 {doctor}醫師</b></center>
                    <center style="font-size:20px">診號: {regist_no:0>3}</b></center>
                    <ol>
                        <li>看完診請至櫃台批價領取藥號單，再至針灸區做針灸、電療等治療。</li>
                        <li>掛完號後為避免久候，請掃QRCode使用看診進度APP，提前4-6個號碼報到。</li>
                    </ol>
                    <br>
                    <img src="data:;base64,{app_qrcode}" alt="" height="80" width="80">
                    &nbsp;&nbsp;&nbsp;&nbsp;
                    <img src="data:;base64,{line_qrcode}" alt="" height="80" width="80">
                    <br>
                    看診進度查詢&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;LINE<br>
                    <table width=95% style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="1">
                        <tr>
                            <td colspan="2" align=center>三伏(九)貼</td>
                            <td>
                            <td align=center>薰</td>
                            <td>
                            <td align=center>照</td>
                            <td>
                        </tr>
                    </table>
                    <table width=95% style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="1">
                        <tr>
                            <td align=center>躺</td>
                            <td>
                            <td align=center>趴</td>
                            <td>
                            <td align=center>坐</td>
                            <td>
                        </tr>
                    </table>
                    <table width=95% style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="1">
                        <tr>
                            <td align=center rowspan="4">治<br>療<br>部<br>位</td>
                            <td align=center>頭</td>
                            <td align=center>頸</td>
                            <td align=center>臉</td>
                            <td align=center>腰</td>
                            <td align=center>背</td>
                        </tr>
                        <tr>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                        </tr>
                        <tr>
                            <td align=center>肩</td>
                            <td align=center>肘</td>
                            <td align=center>腕</td>
                            <td align=center>膝</td>
                            <td align=center>踝</td>
                        </tr>
                        <tr>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                            <td></td>
                        </tr>
                    </table>
                    <table width=95% style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="0" border="1">
                        <tr>
                            <td colspan="2" align=center>美顏針</td>
                            <td>
                            <td colspan="2" align=center>埋線</td>
                            <td>
                        </tr>
                    </table>
                    </b>
                </body>
            </html>
        '''

        return html

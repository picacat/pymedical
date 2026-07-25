
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import patient_utils
from libs import date_utils


# 掛號收據格式1 80mm * 80mm 熱感紙
# 2018.07.09
class PrintSimpleMedicalChart:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
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

    def save_to_pdf(self):
        export_dir = f'{self.ins_apply_path}/emr{self.apply_date}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/chart_{self.patient_key}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, 'print test line1 中文測試')
        painter.drawText(0, 30, 'print test line2 中文測試')
        painter.end()

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(QPrinter.A5)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        patient_row = patient_utils.get_patient_row(self.database, self.patient_key)

        clinic_name = self.system_settings.field('院所名稱')
        patient_key = string_utils.xstr(patient_row['PatientKey'])
        name = string_utils.xstr(patient_row['Name'])
        gender = string_utils.xstr(patient_row['Gender'])
        if gender == '':
            gender = '☐男   ☐女'
        birthday = date_utils.west_date_to_nhi_date(patient_row['Birthday'])
        if birthday is not None:
            birthday = f'民國 {birthday[:3]} 年 {birthday[3:5]} 月 {birthday[5:]} 日'
        else:
            birthday = '民國________年________月________日'

        patient_id = string_utils.xstr(patient_row['ID'])
        telephone = string_utils.xstr(patient_row['Telephone'])
        cellphone = string_utils.xstr(patient_row['Cellphone'])
        address = string_utils.xstr(patient_row['Address'])
        if address == '':
            address = '''
                _____________市(縣)_____________區_____________村_____________里<br>
                _____________路(街)_____________段_____________巷_____________弄_____________號________樓之________
            '''
        occupation = string_utils.xstr(patient_row['Occupation'])
        # education = string_utils.xstr(patient_row['Education'])
        marriage = string_utils.xstr(patient_row['Marriage'])
        if marriage == '':
            marriage = '☐已婚 ☐未婚'
        history = string_utils.get_str(patient_row['History'], 'utf-8')
        if history == '':
            history = '☐糖尿病 ☐高血壓 ☐心血管疾病 ☐高血脂症 ☐中風 ☐其他:'

        allergy = string_utils.get_str(patient_row['Allergy'], 'utf-8')[:10]

        html = f'''
            <html>
              <body>
                <h2 style="text-align: center">{clinic_name}<br>初診基本資料 (RECORD)</h2>
                <table align=center width="98%" cellspacing="0">
                  <tbody>
                    <tr>
                        <td style="text-align: right">病歷號碼: {patient_key:0>6}</td>
                    </tr>
                  </tbody>
                </table>
                <table align=center cellpadding="2" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                  <tbody>
                    <tr>
                        <th>姓名<br>Name</th>
                        <td width="20%" style="text-align:center; vertical-align: middle">{name}</td>
                        <th>性別<br>Gender</th>
                        <td width="10%" style="text-align:center; vertical-align: middle">{gender}</td>
                        <th>藥物過敏史<br>Drug allergy history</th>
                        <td style="text-align:center; vertical-align: middle">{allergy}</td>
                    </tr>
                    <tr>
                        <th>出生日期<br>Birth date</th>
                        <td colspan="3" style="text-align:left; vertical-align: middle">{birthday}</td>
                        <th>血型<br>Blood type</th>
                        <td></td>
                    </tr>
                    <tr>
                        <th>身份證號<br>ID No.</th>
                        <td colspan="5" style="text-align:left; vertical-align: middle">{patient_id}</td>
                    </tr>
                    <tr>
                        <th>聯絡電話<br>Tel No.</th>
                        <td colspan="5" style="text-align:left; vertical-align: middle">
                            宅(H): {telephone}<br>手機(Mobile phone): {cellphone}
                        </td>
                    </tr>
                    <tr>
                        <th>聯絡地址<br>Address</th>
                        <td colspan="5" style="text-align:left; vertical-align: middle">
                            {address}
                        </td>
                    </tr>
                    <tr>
                        <th>家族史<br>Family history</th>
                        <td colspan="5" style="text-align:left; vertical-align: middle">
                            {history}
                        </td>
                    </tr>
                    <tr>
                        <th>婚姻狀況<br>Marriage</th>
                        <td style="text-align:center; vertical-align: middle">{marriage}</td>
                        <th>身高<br>Height</th>
                        <td style="text-align:center; vertical-align: middle"></td>
                        <th>體重<br>Weight</th>
                        <td style="text-align:center; vertical-align: middle"></td>
                    </tr>
                    <tr>
                        <th>職業<br>Occupation</th>
                        <td style="text-align:center; vertical-align: middle">{occupation}</td>
                        <th>旅遊史<br>Travel</th>
                        <td colspan="3" style="text-align:left; vertical-align: middle">
                            半年內 ☐有 ☐無出國, 至____________________旅遊
                        </td>
                    </tr>
                    <tr>
                        <th>緊急聯絡人<br>Notify to Whom</th>
                        <td colspan="3" style="text-align:center; vertical-align: middle"></td>
                        <th rowspan="2" style="text-align:center; vertical-align: middle">與病患關係<br>Relationship</th>
                        <td rowspan="2" style="text-align:left; vertical-align: middle"></td>
                    </tr>
                    <tr>
                        <th>聯絡人電話<br>Tel No.</th>
                        <td colspan="3" style="text-align:center; vertical-align: middle"></td>
                    </tr>
                  </tbody>
                </table>
              </body>
            </html>
        '''

        return html

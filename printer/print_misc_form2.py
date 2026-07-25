
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

import datetime

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import number_utils
from libs import charge_utils


# 自費同意書 4.4 x 4.0 inches
# 2020.08.26 新生堂
class PrintMiscForm2:
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
        self.preview_dialog.resize(geometry.width(), geometry.height())  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def print_html(self, printing=None):
        self.current_print = self.print_html
        self.printer.setPaperSize(QtCore.QSizeF(4.4, 4.0), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]

        clinic_name = self.system_settings.field('院所名稱')
        # clinic_id = self.system_settings.field('院所代號')
        # clinic_telephone = self.system_settings.field('院所電話')
        # clinic_address = self.system_settings.field('院所地址')

        case_date = row['CaseDate'].date()
        patient_key = string_utils.xstr(row['PatientKey'])
        patient_name = string_utils.xstr(row['Name'])

        if self.system_settings.field('自費同意書自費1金額') == 'Y':
            total_fee = charge_utils.get_medicine_set_fee(self.database, self.system_settings, self.case_key, 2)
        else:
            total_fee = number_utils.get_integer(row['TotalFee'])

        current_year = datetime.datetime.now().year - 1911
        current_month = datetime.datetime.now().month
        current_day = datetime.datetime.now().day

        space = '&nbsp;'

        html = f'''
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr>
                    <tr style="text-align: center; font-size: 14px">
                      <th align="center">保險對象使用自費項目同意書</th>
                    </tr>
                  </thead>
                  <tbody>
                  </tbody>
                </table>
                <p style="margin-left: 20px; margin-right: 20px">
                    {space}{space}{space}{space}患者 <u>{patient_name} (病歷號碼: {patient_key})</u> 係全民健康保險對象,
                    於本院就醫期間 <u>{case_date}</u> 因醫療需要,
                    經醫療人員詳細說明自費項目內容並已充分了解,
                    自願自費使用未納入全民健康保險給付範圍之自費項目共計<u>新台幣{total_fee}元整</u>,
                    並同意繳費無異議.
                </p>
                <br><br>
                此致
                <p style="margin-left: 50px">{clinic_name}</p>
                <br>
                <p style="margin-left: 20px">立同意書人: ________________________________ (簽章)</p>
                <p style="margin-left: 20px">中華民國 {current_year} 年 {current_month} 月 {current_day} 日</p>
              </body>
            </html>
        '''

        return html

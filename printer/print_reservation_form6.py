
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter

import datetime
from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils


# 預約單 3"
# 2022.04.01 文青堂中醫
class PrintReservationForm6:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.reservation_key = args[2]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '預約掛號單印表機')
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
        self.font = QtGui.QFont(font, 12, QtGui.QFont.PreferQuality)

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
        self.printer.setPaperSize(QtCore.QSizeF(4.5, 3), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        if printing:
            document.print(self.printer)

    def _html(self):
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveKey = {self.reservation_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        print_reservation_no = self.system_settings.field('列印預約號碼')

        name = string_utils.xstr(row['Name'])
        patient_key = string_utils.xstr(row['PatientKey'])
        reservation_date = string_utils.xstr(row['ReserveDate'].date())
        reservation_time = string_utils.xstr(row['ReserveDate'].time())
        reservation_no = string_utils.xstr(row['ReserveNo'])
        period = string_utils.xstr(row['Period'])
        reservation_time = string_utils.xstr(row['ReserveDate'].time())[:5]
        doctor = string_utils.xstr(row['Doctor'])

        reserve_date = row['ReserveDate']
        weekday = datetime.datetime(
            reserve_date.year, reserve_date.month, reserve_date.day
        ).weekday()
        weekday_name = date_utils.get_weekday_name(weekday)

        if print_reservation_no == 'Y':
            label_reservation_no = f'<td>預約號碼: <b>{reservation_no}</b></td>'
        else:
            label_reservation_no = ''

        html = f'''
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left" colspan="5">
                        {clinic_name}({clinic_id}) 門診預約單
                      </th>
                    </tr>
                    <tr>
                      <th align="left" colspan="5">{clinic_address} {clinic_telephone}</th>
                    </tr>
                  </thead>
                  <tbody>
                  </tbody>
                </table>
                <br>
                <table width="95%" cellspacing="0" style="font-size: 18px">
                  <tbody>
                    <tr>
                      <td>病患姓名: {name}</td>
                      <td>病歷號碼: {patient_key}</td>
                    </tr>
                    <tr>
                      <td>預約醫師: {doctor}</td>
                      <td>預約日期: <b>{reservation_date}</b></td>
                    </tr>
                    <tr>
                      <td>報到時間: <b>{weekday_name} {period}</b></td>
                      {label_reservation_no}
                    </tr>
                  </tbody>
                </table>
                <ul style="font-size: 12px; margin-top: -30px; margin-bottom: -60px; margin-left: -10px">
                  <li>預約未能報到, 請事先告知</li>
                  <li>更多訊息, 溝通傳真專線: {clinic_telephone}</li>
                </ul>
              </body>
            </html>
        '''

        return html

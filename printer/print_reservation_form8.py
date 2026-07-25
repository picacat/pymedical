
# -*- coding: UTF-8 -*-

import datetime

from libs import date_utils, printer_utils, string_utils, system_utils
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter


# 預約單 熱感 80mm
# 2024.04.08 日知堂
class PrintReservationForm8:
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
        printer_utils.set_paper_size(self.printer, self.system_settings, 74, 148, QPrinter.Millimeter, '預約單')

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
        reservation_date = date_utils.date_to_zh_tw_date(reservation_date)

        reservation_time = string_utils.xstr(row['ReserveDate'].time())
        reservation_no = string_utils.xstr(row['ReserveNo'])
        period = string_utils.xstr(row['Period'])
        period = period.replace('班', '診')
        
        doctor = string_utils.xstr(row['Doctor'])

        if self.system_settings.field('預約班表不顯示時間') == 'Y':
            reservation_time = ''
        else:
            reservation_time = ' - ' + string_utils.xstr(row['ReserveDate'].time())[:5]

        reserve_date = row['ReserveDate']
        weekday = datetime.datetime(
            reserve_date.year, reserve_date.month, reserve_date.day
        ).weekday()
        weekday_name = date_utils.get_weekday_name(weekday)

        if print_reservation_no == 'Y':
            label_reservation_no = f'<tr><td>預約號碼: <b>{reservation_no}</b></td></tr>'
            reservation_time = ''
        else:
            label_reservation_no = ''

        if string_utils.xstr(row['Remark']).strip() != '':
            remark = f'<tr><td>備註: {string_utils.xstr(row["Remark"])} </td></tr>'
        else:
            remark = ''

        html = f'''
            <html>
              <body>
                <center>
                    <font size="5"><b>{clinic_name}</b></font><br>
                    <font size="1">代號:{clinic_id}<br>
                    電話:{clinic_telephone}<br>
                    {clinic_address}<br></font>
                    <br>
                    <b><u>門診預約單</u></b>
                </center>
                <table width="95%" cellspacing="0" style="font-size: 18px">
                  <tbody>
                    <tr>
                      <td>病患姓名: {name}</td>
                    </tr>
                    <tr>
                      <td>預約醫師: {doctor}</td>
                    </tr>
                    <tr>
                      <td>預約日期: <b>{reservation_date} {weekday_name}</b></td>
                    </tr>
                    <tr>
                      <td>預約看診時間: <b>{period}{reservation_time}</b></td>
                    </tr>
                    {label_reservation_no}
                    {remark}
                  </tbody>
                </table>
                <ul style="font-size: 12px; margin-top: -30px; margin-bottom: -60px; margin-left: -10px">
                  <li>預約未能報到, 請事先告知</li>
                  <li>預約看診時間和實際看診時間不同，病情每人不一，看診長短不同，如有久候，敬請見諒。</li>
                  <li>更多訊息, 溝通專線: {clinic_telephone}</li>
                </ul>
              </body>
            </html>
        '''

        return html

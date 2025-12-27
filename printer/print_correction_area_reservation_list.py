
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils


# 列印矯正機關預約門診日報表
# 2022.08.28
class PrintCorrectionAreaReservationList:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.doctor = args[5]
        self.tableWidget_reservation_list = args[6]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
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
        self.font = QtGui.QFont(font, 8, QtGui.QFont.PreferQuality)

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
        options = QFileDialog.Options()
        pdf_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date}-{self.end_date}{self.doctor}矯正機關內預約名單.pdf',
            "pdf檔案 (*.pdf);;Text Files (*.txt)", options=options
        )
        if not pdf_file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setOrientation(QPrinter.Portrait)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        reservation_list = self._get_reservation_list_html()
        correction_area = self.system_settings.field('矯正機關')

        html = f'''
            <html>
                <body>
                    <br>
                    <p align=center style="font-size: 28px; font-weight: 700">掛號報表明細表</p>
                    <div align="left" style="margin-left: 30; font-size: 16px">
                        機關名稱: 法務部矯正署{correction_area}
                    </div>
                    {reservation_list}
                    <br><br>
                </body>
            </html>
        '''

        return html

    def _get_patient_data(self, patient_key):
        sql = f'''
            SELECT ID, ChartNo, Birthday FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        row = rows[0]
        patient_id = string_utils.xstr(row['ID'])
        chart_no = string_utils.xstr(row['ChartNo'])
        birthday = string_utils.xstr(row['Birthday'])

        return patient_id, chart_no, birthday,

    def _get_reservation_list_html(self):
        reservation_list_row = ''

        alternative_row_color = self.system_settings.field('列印報表雙色印刷')

        for row_no in range(self.tableWidget_reservation_list.rowCount()):
            sequence = row_no + 1

            bgcolor = 'white'
            if alternative_row_color == 'Y' and row_no % 2 > 0:
                bgcolor = '#E3E3E3'

            reservation_date = self.tableWidget_reservation_list.item(row_no, 1).text()
            try:
                reservation_date = date_utils.date_to_zh_tw_date(reservation_date)
                reservation_date = reservation_date.split(' ')[0]
            except Exception:
                pass

            period = self.tableWidget_reservation_list.item(row_no, 3).text()
            if period == '早班':
                period = '上午'
            elif period == '午班':
                period = '下午'
            elif period == '晚班':
                period = '夜間'

            patient_key = self.tableWidget_reservation_list.item(row_no, 4).text()
            patient_id, chart_no, birthday = self._get_patient_data(patient_key)
            try:
                birthday = date_utils.date_to_zh_tw_date(birthday)
            except Exception:
                birthday = ''

            name = self.tableWidget_reservation_list.item(row_no, 5).text()

            reservation_list_row += f'''
                <tr bgcolor={bgcolor}>
                    <td align=center>{sequence}</td>
                    <td align=center>{reservation_date}</td>
                    <td align=center>{period}</td>
                    <td align=center>中醫科</td>
                    <td align=center>{chart_no:0>4}</td>
                    <td align=center>{name}</td>
                    <td align=center>{patient_id}</td>
                    <td align=center>{birthday}</td>
                </tr>
            '''

        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="font-size: 16px; border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th>序</th>
                        <th>看診日期</th>
                        <th>時段</th>
                        <th>科別</th>
                        <th>呼號</th>
                        <th>姓名</th>
                        <th>身分證號</th>
                        <th>出生日期</th>
                    </tr>
                </thead>
                <tbody>
                    {reservation_list_row}
                </tbody>
            </table>
        '''

        return html

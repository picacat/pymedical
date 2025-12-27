
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils


# 列印預約名單
# 2019.03.38
class PrintReservationList:
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
        self.no_reservation_time = self.system_settings.field('預約班表不顯示時間')

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

    def save_to_pdf(self):
        options = QFileDialog.Options()
        pdf_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date}-{self.end_date}{self.doctor}預約名單.pdf',
            "pdf檔案 (*.pdf);;Text Files (*.txt)", options=options
        )
        if not pdf_file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def print_html(self, printing):
        self.current_print = self.print_html
        self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        reservation_list = self._get_reservation_list_html()
        clinic_name = self.system_settings.field('院所名稱')
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 預約名單</h2>
                    <div align="left" style="margin-left: 40px">
                        預約日期: {start_date} 至 {end_date} 班別: {self.period} 醫師: {self.doctor}醫師
                    </div>
                    {reservation_list}
                    <br><br>
                </body>
            </html>
        '''

        return html

    def _get_reservation_list_html(self):
        reservation_list_row = ''

        for row_no in range(self.tableWidget_reservation_list.rowCount()):
            sequence = row_no + 1

            if row_no % 2 > 0:
                bgcolor = '#E3E3E3'
            else:
                bgcolor = 'white'

            reservation_date = self.tableWidget_reservation_list.item(row_no, 1).text()
            reservation_time = self.tableWidget_reservation_list.item(row_no, 2).text()
            period = self.tableWidget_reservation_list.item(row_no, 3).text()
            patient_key = self.tableWidget_reservation_list.item(row_no, 4).text()
            name = self.tableWidget_reservation_list.item(row_no, 5).text()
            telephone = self.tableWidget_reservation_list.item(row_no, 13).text()
            cellphone = self.tableWidget_reservation_list.item(row_no, 14).text()
            doctor = self.tableWidget_reservation_list.item(row_no, 7).text()
            reservation_no = self.tableWidget_reservation_list.item(row_no, 9).text()
            source = self.tableWidget_reservation_list.item(row_no, 11).text()
            create_time = self.tableWidget_reservation_list.item(row_no, 15).text()

            if self.no_reservation_time == 'Y':
                reservation_list_row += f'''
                    <tr bgcolor={bgcolor}>
                        <td align=center>{sequence}</td>
                        <td align=center>{reservation_date}</td>
                        <td align=center>{period}</td>
                        <td align=center>{patient_key}</td>
                        <td align=center>{name}</td>
                        <td align=center>{telephone}</td>
                        <td align=center>{cellphone}</td>
                        <td align=center>{doctor}</td>
                        <td align=center>{reservation_no}</td>
                        <td align=center>{source}</td>
                        <td align=center>{create_time}</td>
                    </tr>
                '''
            else:
                reservation_list_row += f'''
                    <tr bgcolor={bgcolor}>
                        <td align=center>{sequence}</td>
                        <td align=center>{reservation_date}</td>
                        <td align=center>{reservation_time}</td>
                        <td align=center>{period}</td>
                        <td align=center>{patient_key}</td>
                        <td align=center>{name}</td>
                        <td align=center>{telephone}</td>
                        <td align=center>{cellphone}</td>
                        <td align=center>{doctor}</td>
                        <td align=center>{reservation_no}</td>
                        <td align=center>{source}</td>
                        <td align=center>{create_time}</td>
                    </tr>
                '''

        if self.no_reservation_time == 'Y':
            html = f'''
                <table align=center cellpadding="1" cellspacing="0" width="95%"
                    style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                    <thead>
                        <tr bgcolor="LightGray">
                            <th>序</th>
                            <th>預約日期</th>
                            <th>班別</th>
                            <th>病歷號</th>
                            <th>姓名</th>
                            <th>聯絡電話</th>
                            <th>行動電話</th>
                            <th>預約醫師</th>
                            <th>診號</th>
                            <th>預約來源</th>
                            <th>登錄時間</th>
                        </tr>
                    </thead>
                    <tbody>
                        {reservation_list_row}
                    </tbody>
                </table>
            '''
        else:
            html = f'''
                <table align=center cellpadding="1" cellspacing="0" width="95%"
                    style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                    <thead>
                        <tr bgcolor="LightGray">
                            <th>序</th>
                            <th>預約日期</th>
                            <th>時間</th>
                            <th>班別</th>
                            <th>病歷號</th>
                            <th>姓名</th>
                            <th>聯絡電話</th>
                            <th>行動電話</th>
                            <th>預約醫師</th>
                            <th>診號</th>
                            <th>預約來源</th>
                            <th>登錄時間</th>
                        </tr>
                    </thead>
                    <tbody>
                        {reservation_list_row}
                    </tbody>
                </table>
            '''

        return html

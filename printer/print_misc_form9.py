
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore, QtPrintSupport
from PyQt5.QtPrintSupport import QPrinter
from libs import printer_utils
from libs import system_utils
from libs import string_utils


# 其他收據格式9 藥袋標示
# 2020.10.19
class PrintMiscForm9:
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
        self.printer.setPaperSize(QtCore.QSizeF(4.4, 3.0), QPrinter.Inch)

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(printer_utils.get_document_margin())
        document.setHtml(self._html())
        printer_utils.set_document_line_height(document, 14)
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

        case_record = printer_utils.get_case_html_8(self.database, self.case_key, '全部')
        clinic_name = self.system_settings.field('院所名稱')
        clinic_id = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        doctor = string_utils.xstr(row['Doctor'])
        disease_name1 = string_utils.xstr(row['DiseaseName1'])

        html = f'''
            <html>
              <body>
                <table width="95%" cellspacing="0">
                  <thead>
                    <tr>
                      <th style="text-align: left;" colspan="3">
                        {clinic_name}({clinic_id}) 藥袋標示
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <ul>
                    <li>保存方式: 置於常溫乾燥處</li>
                    <li>有效期限: 三個月</li>
                    <li>適應症: {disease_name1}</li>
                    <li>副作用: 無</li>
                    <li>警語: 請依照服藥時間服用</li>
                    <li>調劑者: {doctor}</li>
                    <li>請核對姓名, 保留藥袋至藥品用完.</li>
                    <li>藥品應置乾燥陰涼避光處, 如發現變質切勿服用.</li>
                    <li>請遵照醫師或藥師指示服用藥品, 以確保安全與療效.</li>
                    <li>服用中藥時, 須與西藥間隔1~2小時.</li>
                </ul>
                院址:{clinic_address} 電話:{clinic_telephone}
              </body>
            </html>
        '''

        return html

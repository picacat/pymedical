
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtPrintSupport import QPrinter
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import patient_utils


# 掛號收據格式1 80mm * 80mm 熱感紙
# 2018.07.09
class PrintMedicalFees:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.sql = args[3]
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
        export_dir = f'{self.ins_apply_path}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/case_{self.patient_key}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        export_dir = f'{self.ins_apply_path}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        if self.patient_key is not None:
            pdf_file_name = f'{export_dir}/病歷號{self.patient_key}收費明細表.pdf'
        else:
            pdf_file_name = '收費明細.pdf'

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent, "匯出收費明細表",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)", options=options
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QMessageBox.Information,
            '匯出完成',
            '<font size="5" color="red"><b>收費明細pdf檔案已匯出完成</b></font>',
            '',
        )

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
        # database.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        patient_row = patient_utils.get_patient_row(self.database, self.patient_key)
        medical_record_html = self.get_medical_record_html()

        if patient_row is None:
            html = medical_record_html
        else:
            init_date = patient_utils.get_init_date(self.database, self.system_settings, self.patient_key)
            telepnone = string_utils.xstr(patient_row['Telephone'])
            if telepnone == '':
                telepnone = string_utils.xstr(patient_row['Cellphone'])

            clinic_name = self.system_settings.field('院所名稱')
            clinic_id = self.system_settings.field('院所代號')
            clinic_telephone = self.system_settings.field('院所電話')
            clinic_address = self.system_settings.field('院所地址')
            patient_key = string_utils.xstr(patient_row['PatientKey'])
            name = string_utils.xstr(patient_row['Name'])
            gender = string_utils.xstr(patient_row['Gender'])
            birthday = string_utils.xstr(patient_row['Birthday'])
            patient_id = string_utils.xstr(patient_row['ID'])
            telephone = telepnone
            address = string_utils.xstr(patient_row['Address'])

            html = f'''
                <html>
                  <body>
                    <h3 style="text-align: center">{clinic_name} 收費明細表</h3>
                    <table width="98%" cellspacing="0">
                      <tbody>
                        <tr>
                            <td>病歷號: {patient_key}</td>
                            <td>姓名: {name}</td>
                            <td>性別: {gender}</td>
                            <td>生日: {birthday}</td>
                            <td>身份證: {patient_id}</td>
                        </tr>
                        <tr>
                            <td>初診日: {init_date}</td>
                            <td>電話: {telephone}</td>
                            <td colspan="3">地址: {address}</td>
                        </tr>
                      </tbody>
                    </table>
                    <hr>
                    {medical_record_html}
                    <h4>院所名稱: ({clinic_id}) {clinic_name} 電話: {clinic_telephone} 院址: {clinic_address}</h4>
                  </body>
                </html>
            '''

        return html

    def get_medical_record_html(self):
        rows = self.database.select_record(self.sql)
        if len(rows) <= 0:
            return None

        medical_record_html = ''
        for row in rows:
            case_key = row['CaseKey']
            # medicine_set = 1

            case_record = printer_utils.get_case_html_1(
                self.database, case_key, '健保',
            )
            prescript_record = printer_utils.get_self_prescript_html(
                self.database, self.system_settings, case_key,
            )
            ins_fees_record = printer_utils.get_ins_fees_html(self.database, case_key)
            self_fees_record = printer_utils.get_self_fees_html(self.database, case_key)
            # instruction = printer_utils.get_instruction_html(
            #     self.database, self.system_settings, case_key, medicine_set
            # )

            doctor = string_utils.xstr(row['Doctor'])

            medical_record_html += f'''
                <font size="5">
                <table width="100%" cellspacing="0">
                  <tbody>
                    {case_record}
                  </tbody>
                </table>
                <table width="100%" cellspacing="0" style="font-weight: bold; background-color: lightgray">
                  <tbody>
                    {prescript_record}
                  </tbody>
                </table>
                <table width="100%" cellspacing="0">
                  <tbody>
                    {ins_fees_record}
                    {self_fees_record}
                  </tbody>
                </table>
                醫師: {doctor}
                </font>
                <hr>
            '''

        return medical_record_html

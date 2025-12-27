
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter
import html
import os

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import nhi_utils
from libs import patient_utils


# 列印病歷表
# 2018.07.09
class PrintMedicalChart:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.patient_key = args[2]
        self.apply_date = args[3]
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
        export_dir = f'{self.ins_apply_path}/emr{self.apply_date}'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/chart_{self.patient_key:0>6}.pdf'
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        pdf_file_name = f'病歷首頁_{self.patient_key:0>6}.pdf'

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self.parent, "匯出病歷首頁pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)", options=options
        )
        if not filename:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(filename)
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
        # database.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        patient_row = patient_utils.get_patient_row(self.database, self.patient_key)
        ins_judge_init_date = self.system_settings.field('電子化抽審初診日期')

        if ins_judge_init_date != '':
            end_date_script = f' AND CaseDate >= "{ins_judge_init_date}"'
        else:
            end_date_script = ''

        sql = f'''
            SELECT * FROM cases
            WHERE
                InsType = "健保" AND
                PatientKey = {self.patient_key}
                {end_date_script}
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        case_row = rows[0]

        if ins_judge_init_date != '':
            init_date = case_row['CaseDate'].date()
        else:
            init_date = patient_utils.get_init_date(self.database, self.system_settings, self.patient_key)

        prescript_record = printer_utils.get_prescript_html(
            self.database, self.system_settings, case_row['CaseKey'], 1, '病歷表', blocks=2)
        instruction = printer_utils.get_instruction_html(
            self.database, self.system_settings, case_row['CaseKey'], medicine_set=1
        )

        clinic_name = self.system_settings.field('院所名稱')
        patient_key = string_utils.xstr(patient_row['PatientKey'])
        name = string_utils.xstr(patient_row['Name'])
        gender = string_utils.xstr(patient_row['Gender'])
        birthday = string_utils.xstr(patient_row['Birthday'])
        patient_id = string_utils.xstr(patient_row['ID'])
        telephone = string_utils.xstr(patient_row['Telephone'])
        cellphone = string_utils.xstr(patient_row['Cellphone'])
        address = string_utils.xstr(patient_row['Address'])
        occupation = string_utils.xstr(patient_row['Occupation'])
        education = string_utils.xstr(patient_row['Education'])
        marriage = string_utils.xstr(patient_row['Marriage'])
        history = string_utils.get_str(patient_row['History'], 'utf-8')
        symptom = html.escape(string_utils.get_str(case_row['Symptom'], 'utf-8'))
        tongue = string_utils.get_str(case_row['Tongue'], 'utf-8')
        pulse = string_utils.get_str(case_row['Pulse'], 'utf-8')
        distinct = string_utils.get_str(case_row['Distincts'], 'utf-8')

        disease_line = ''

        disease_code1 = string_utils.xstr(case_row['DiseaseCode1'])
        if disease_code1 != '':
            disease_name1 = string_utils.xstr(case_row['DiseaseName1'])
            disease_line += f'主診斷碼: {disease_code1}  病名: {disease_name1}<br>'

        disease_code2 = string_utils.xstr(case_row['DiseaseCode2'])
        if disease_code2 != '':
            disease_name2 = string_utils.xstr(case_row['DiseaseName2'])
            disease_line += f'次診斷碼1: {disease_code2}  病名: {disease_name2}<br>'

        disease_code3 = string_utils.xstr(case_row['DiseaseCode3'])
        if disease_code3 != '':
            disease_name3 = string_utils.xstr(case_row['DiseaseName3'])
            disease_line += f'次診斷碼1: {disease_code3}  病名: {disease_name3}<br>'

        cure = string_utils.xstr(case_row['Cure'])

        html_str = f'''
            <html>
              <body>
                <h2 style="text-align: center">{clinic_name} 病歷表</h2>
                <table align=center width="98%" cellspacing="0">
                  <tbody>
                    <tr>
                        <td>病歷號碼: {patient_key}</td>
                        <td style="text-align: right">初診日期: {init_date}</td>
                    </tr>
                  </tbody>
                </table>
                <table align=center cellpadding="2" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                  <tbody>
                    <tr>
                        <th>姓名</th>
                        <td width="20%">{name}</td>
                        <th>出生日期</th>
                        <td>{birthday}</td>
                        <th>性別</th>
                        <td>{gender}</td>
                    </tr>
                    <tr>
                        <th>身份證號</th>
                        <td>{patient_id}</td>
                        <th>電話</th>
                        <td>{telephone}</td>
                        <th>行動電話</th>
                        <td>{cellphone}</td>
                    </tr>
                    <tr>
                        <th>地址</th>
                        <td colspan="5">{address}</td>
                    </tr>
                    <tr>
                        <th>職業</th>
                        <td>{occupation}</td>
                        <th>教育程度</th>
                        <td>{education}</td>
                        <th>婚姻狀況</th>
                        <td>{marriage}</td>
                    </tr>
                  </tbody>
                </table>
                <table align=center cellpadding="10" cellspacing="0" width="98%"
                 style="border-width: 1px; border-style: solid;">
                  <tbody>
                    <tr>
                        <th width="15%" style="vertical-align: middle">病史</th>
                        <td>{history}<br></td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle">主訴</th>
                        <td>{symptom}<br><br></td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle">四診</th>
                        <td>
                            <br>舌診: {tongue}<br>
                            <br>脈象: {pulse}<br>
                            <br>辨證: {distinct}<br>
                        </td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle">病理檢驗</th>
                        <td><br><br></td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle">診斷治則</th>
                        <td>
                            <br>疑似:<br>
                            {disease_line}
                            <br>{cure}<br>
                        </td>
                    </tr>
                    <tr>
                        <th style="vertical-align: middle">治療處方</th>
                        <td>
                            <table align=center width="98%" cellspacing="0">
                              <tbody>
                                {prescript_record}
                              </tbody>
                            </table>
                            <br><br>
                            {instruction}
                            <br>
                        </td>
                    </tr>
              </body>
            </html>
        '''

        return html_str

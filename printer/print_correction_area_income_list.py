
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils


# 列印矯正機關預約現金日報表 / 列印照護機構線今日報表 2024-06-27 安聲
# 2022.08.28
class PrintCorrectionAreaReservationList:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.tableWidget_medical_record_list = args[2]
        self.columns = args[3]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None
        self.font_size = '16px'

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
            f'{self.start_date}-{self.end_date}{self.doctor}矯正機關內門診現金日報表.pdf',
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
        income_list = self._get_income_list_html()
        clinic_name = self.system_settings.field('院所名稱')
        correction_area = self.system_settings.field('矯正機關')

        try:
            case_date = self.tableWidget_medical_record_list.item(0, self.columns['CaseDate']).text()
            regist_type = self.tableWidget_medical_record_list.item(0, self.columns['RegistType']).text()
            case_date = date_utils.date_to_zh_tw_date(case_date)
            case_date = case_date.split(' ')[0]
        except Exception:
            case_date = ''

        if regist_type == '矯正機關':
            title = f'{clinic_name} 矯正機關內門診現金日報表'
            offical_name = f'機關名稱: 法務部矯正署{correction_area}'
        elif regist_type == '照護機構':
            title = f'{clinic_name} 照護機構門診現金日報表'
            patient_key = self.tableWidget_medical_record_list.item(0, self.columns['PatientKey']).text()
            sql = f'''
                SELECT NursingHome FROM patient
                WHERE
                    PatientKey = {patient_key} 
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                care_institution = ''
            else:
                row = rows[0]
                care_institution = string_utils.xstr(row['NursingHome'])

            offical_name = f'照護機構: {care_institution}'
        else:
            title = f'{clinic_name} 門診現金日報表'
            offical_name = f'院所名稱: {clinic_name}'

        html = f'''
            <html>
                <body>
                    <br>
                    <p align=center style="font-size: 28px; font-weight: 700">{title}</p>
                    <div align="left" style="margin-left: 30; font-size: {self.font_size}">
                        {offical_name}<br>
                        統計日期: {case_date}
                    </div>
                    {income_list}
                    <br><br>
                </body>
            </html>
        '''

        return html

    def _get_patient_data(self, patient_key):
        sql = f'''
            SELECT ChartNo FROM patient
            WHERE
                PatientKey = {patient_key}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ''

        row = rows[0]
        chart_no = string_utils.xstr(row['ChartNo'])

        return chart_no

    def _get_income_list_html(self):
        medical_record_list_rows = ''

        alternative_row_color = self.system_settings.field('列印報表雙色印刷')

        total_regist_fee, total_diag_share_fee, total_drug_share_fee, total_total_fee, total_subtotal = 0, 0, 0, 0, 0
        person_count = 0
        for row_no in range(self.tableWidget_medical_record_list.rowCount()):
            try:
                check_box_print_mark = self.tableWidget_medical_record_list.cellWidget(
                    row_no, self.columns['PrintMark'])
                if not check_box_print_mark.isChecked():
                    continue
            except Exception:
                continue

            person_count += 1
            bgcolor = 'white'
            if alternative_row_color == 'Y' and row_no % 2 > 0:
                bgcolor = '#E3E3E3'

            case_date = self.tableWidget_medical_record_list.item(row_no, self.columns['CaseDate']).text()
            try:
                case_date = date_utils.date_to_zh_tw_date(case_date)
            except Exception:
                pass

            period = self.tableWidget_medical_record_list.item(row_no, self.columns['Period']).text()
            if period == '早班':
                period = '上午'
            elif period == '午班':
                period = '下午'
            elif period == '晚班':
                period = '夜間'

            regist_no = self.tableWidget_medical_record_list.item(row_no, self.columns['RegistNo']).text()
            patient_key = self.tableWidget_medical_record_list.item(row_no, self.columns['PatientKey']).text()
            chart_no = self._get_patient_data(patient_key)

            name = self.tableWidget_medical_record_list.item(row_no, self.columns['Name']).text()
            ins_type = self.tableWidget_medical_record_list.item(row_no, self.columns['InsType']).text()
            card = self.tableWidget_medical_record_list.item(row_no, self.columns['Card']).text()
            share_type = self.tableWidget_medical_record_list.item(row_no, self.columns['Share']).text()
            doctor = self.tableWidget_medical_record_list.item(row_no, self.columns['Doctor']).text()

            regist_fee = number_utils.get_integer(
                self.tableWidget_medical_record_list.item(row_no, self.columns['RegistFee']).text())
            diag_share_fee = number_utils.get_integer(
                self.tableWidget_medical_record_list.item(row_no, self.columns['DiagShareFee']).text())
            drug_share_fee = number_utils.get_integer(
                self.tableWidget_medical_record_list.item(row_no, self.columns['DrugShareFee']).text())
            total_fee = number_utils.get_integer(
                self.tableWidget_medical_record_list.item(row_no, self.columns['TotalFee']).text())
            subtotal = regist_fee + diag_share_fee + drug_share_fee + total_fee

            total_regist_fee += regist_fee
            total_diag_share_fee += diag_share_fee
            total_drug_share_fee += drug_share_fee
            total_total_fee += total_fee
            total_subtotal += subtotal

            medical_record_list_rows += f'''
                <tr bgcolor={bgcolor}>
                    <td align=center>{regist_no}</td>
                    <td align=center>{patient_key}</td>
                    <td align=center>{chart_no:0>4}</td>
                    <td align=center>{name}</td>
                    <td align=center>{case_date}</td>
                    <td align=center>{period}</td>
                    <td align=center>{ins_type}</td>
                    <td align=center>{card}</td>
                    <td align=center>{share_type}</td>
                    <td align=center>{regist_fee}</td>
                    <td align=center>{diag_share_fee}</td>
                    <td align=center>{drug_share_fee}</td>
                    <td align=center>{total_fee}</td>
                    <td align=center>{subtotal}</td>
                    <td align=center>{doctor}</td>
                </tr>
            '''

        medical_record_list_rows += f'''
            <tr>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td align=center>合計</td>
                <td></td>
                <td></td>
                <td></td>
                <td></td>
                <td align=center>{total_regist_fee}</td>
                <td align=center>{total_diag_share_fee}</td>
                <td align=center>{total_drug_share_fee}</td>
                <td align=center>{total_total_fee}</td>
                <td align=center>{total_subtotal}</td>
                <td align=center></td>
            </tr>
        '''

        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="font-size: {self.font_size}; border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th>診號</th>
                        <th>病歷號</th>
                        <th>呼號</th>
                        <th>姓名</th>
                        <th>就醫日期</th>
                        <th>時段</th>
                        <th>保險</th>
                        <th>健保卡序</th>
                        <th>負擔類別</th>
                        <th>掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負擔</th>
                        <th>自費金額</th>
                        <th>合計</th>
                        <th>主治醫師</th>
                    </tr>
                </thead>
                <tbody>
                    {medical_record_list_rows}
                </tbody>
            </table>
            <br><br>
            <div align="left" style="margin-left: 800; font-size: 24px">
                合計人數: {person_count} 人<br>
                合計金額: {total_subtotal} 元<br>
            </div>
        '''

        return html

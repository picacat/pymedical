
# -*- coding: UTF-8 -*-

import os

from libs import (date_utils, nhi_utils, patient_utils, personnel_utils,
                  printer_utils, string_utils, system_utils)
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox


# 列印診斷證明書
# 2018.07.09
class PrintCertificateDiagnosis:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.certificate_key = args[2]
        self.title = args[3]

        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, '申報路徑')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

        if self.system_settings.field('列印報表雙色印刷') == 'Y':
            self.html_bg_color = ' bgcolor="LightGray"'
        else:
            self.html_bg_color = ''

        self.font_size = 'font-size: 18px'

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
        export_dir = f'{self.ins_apply_path}/certificate'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/certificate_{self.certificate_key}.pdf'

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        export_dir = f'{self.ins_apply_path}/certificate'
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f'{export_dir}/certificate_{self.certificate_key}.pdf'

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent, "匯出診斷證明pdf",
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
            '<font size="5" color="red"><b>診斷證明pdf檔案已匯出完成</b></font>',
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
        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        sql = f'''
            SELECT * FROM certificate
            WHERE
                CertificateKey = {self.certificate_key}
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]
        html_title = self._get_html_title(row)
        html_patient = self._get_html_patient(row)
        html_detail = self._get_html_detail(row)
        html_remark = self._get_html_remark()

        html = f'''
            <html>
              <body>
                <br>
                {html_title}
                {html_patient}
                {html_detail}
                {html_remark}
              </body>
            </html>
        '''

        return html

    def _get_html_title(self, row):
        certificate_key = f"{row['CertificateKey']:0>8}"
        clinic_name = self.system_settings.field('院所名稱')

        english_title = ''
        if self.title == '診斷證明書':
            english_title = 'CERTIFICATE OF DIAGNOSIS'
        elif self.title == '就醫證明書':
            english_title = 'CERTIFICATE OF MEDICAL RECORD'
        elif self.title == '病歷摘要':
            english_title = 'SUMMARY OF MEDICAL RECORD'

        html = f'''
            <center style="font-size: 24px; font-weight: bold">{clinic_name} {self.title}<br>{english_title}</center>
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td style="font-size: 14px">編號Certificate No.{certificate_key}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    def _get_case_list(self, row):
        sql = f'''
            SELECT CaseDate FROM certificate_items
            WHERE
                CertificateKey = {self.certificate_key}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            rows = self._get_rows_by_script(row)

        case_list = []
        for row in rows:
            case_date = date_utils.date_to_zh_tw_date(string_utils.xstr(row['CaseDate'].date()))
            case_list.append(case_date)

        return case_list

    def _get_rows_by_script(self, row):
        start_date = row['StartDate']
        start_date = f'{start_date} 00:00:00'

        end_date = row['EndDate']
        end_date = f'{end_date} 23:59:59'

        patient_key = row['PatientKey']

        treat_type_dict = {
            '針傷科': nhi_utils.INS_TREAT,
            '針灸科': nhi_utils.ACUPUNCTURE_TREAT,
            '傷骨科': nhi_utils.MASSAGE_TREAT,
        }

        condition = ''
        ins_type = string_utils.xstr(row['InsType'])
        treat_type = string_utils.xstr(row['TreatType'])
        if treat_type == '':
            treat_type = '全部'

        if ins_type in ['健保', '自費']:
            condition = f' AND InsType = "{ins_type}" '

        if treat_type == '內科':
            condition += ' AND TreatType = "內科" '
        elif treat_type != '全部':
            treat_type_list = tuple(treat_type_dict[treat_type])
            condition += f' AND TreatType IN {treat_type_list} '

        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                PatientKey = {patient_key} AND
                TreatType != "自購"
                {condition}
            GROUP BY DATE(CaseDate)
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_html_patient(self, row):
        patient_row = patient_utils.get_patient_row(self.database, row['PatientKey'])

        case_date = date_utils.date_to_zh_tw_date(string_utils.xstr(row['StartDate']))
        e_case_date = string_utils.xstr(row['StartDate'])
        if row['EndDate'] != row['StartDate']:
            end_date = date_utils.date_to_zh_tw_date(string_utils.xstr(row["EndDate"]))
            e_end_date = string_utils.xstr(row["EndDate"])
            case_date += f' 至 {end_date}'
            e_case_date = f'between<br>{e_case_date} and {e_end_date}'
        else:
            e_case_date = 'on ' + e_case_date

        case_list = self._get_case_list(row)
        case_times = len(case_list)

        if self.system_settings.field('列印診斷證明日期明細') == 'Y':
            case_list = ', '.join(case_list)
            case_list_row = f'''
                <tr>
                    <th{self.html_bg_color}>診療日期明細<br><font size="5">List of Date</font></th>
                    <td colspan="5" style="text-align: left; vertical-align: middle">{case_list}</td>
                </tr>
            '''
        else:
            case_list_row = ''

        telephone = string_utils.xstr(patient_row['Telephone'])
        if telephone == '':
            telephone = string_utils.xstr(patient_row['Cellphone'])

        patient_key = f"{row['PatientKey']:0>6}"
        name = string_utils.xstr(row['Name'])
        gender = string_utils.xstr(patient_row['Gender'])
        if gender == '男':
            e_gender = 'Male'
        elif gender == '女':
            e_gender = 'Female'
        else:
            e_gender = ''

        birthday = string_utils.xstr(patient_row['Birthday'])
        chinese_birthday = date_utils.west_date_to_nhi_date(patient_row['Birthday'], '-')
        patient_id = string_utils.xstr(patient_row['ID'])
        address = string_utils.xstr(patient_row['Address'])

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
                style="font-size: 16px; border-width: 2px; border-style: solid; border-color: black; border-collapse: collapse">
                <tbody>
                    <tr>
                        <th{self.html_bg_color} style="vertical-align: middle" width="12%">姓名<br><font size="5">Name</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle" width="18%">{name}</td>
                        <th{self.html_bg_color} style="vertical-align: middle" width="12%">性別<br><font size="5">Gender</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle" width="20%">
                            {gender}<br>{e_gender}</td>
                        <th{self.html_bg_color} width="12%">出生日期<br><font size="5">Date of Birth</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle" width="26%">
                            {birthday}<br>(民國{chinese_birthday})
                        </td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color}>病歷號碼<br><font size="5">Chart No.</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle">{patient_key}</td>
                        <th{self.html_bg_color}>身份證號<br><font size="5">ID No.</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle">{patient_id}</td>
                        <th{self.html_bg_color}>電話<br><font size="5">Telephone</font></th>
                        <td style="{self.font_size}; text-align: center; vertical-align: middle">{telephone}</td>
                    <tr>
                        <th{self.html_bg_color}>地址<br><font size="5">Address</font></th>
                        <td colspan="5" style="{self.font_size}; text-align: left; vertical-align: middle">{address}</td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color} style="vertical-align: middle">
                            科別<br>
                            <font size="5">Speciality</font>
                        </th>
                        <td style="{self.font_size};text-align: center; vertical-align: middle">中醫科<br>TCM</td>
                        <th{self.html_bg_color}>診療日期<br><font size="5">Date of Examination</font></th>
                        <td colspan="3" style="{self.font_size}; text-align: center; vertical-align: middle">
                            {case_date} 共{case_times}次<br>
                            Visit: {case_times} time{"s" if case_times != 1 else ''} {e_case_date}.
                        </td>
                    </tr>
                    {case_list_row}
                </tbody>
            </table>
        '''

        return html

    def _get_html_detail(self, row):
        year = row['CertificateDate'].year
        month = row['CertificateDate'].month
        day = row['CertificateDate'].day
        certificate_date = f'{year} 年 {month} 月 {day} 日'

        physician = string_utils.xstr(row['Doctor'])
        physician_cert_no = personnel_utils.get_person_field_value(
            self.database, physician, 'Certificate')
        president = self.system_settings.field('負責醫師')
        license_no = self.system_settings.field('院所代號')
        clinic_telephone = self.system_settings.field('院所電話')
        clinic_address = self.system_settings.field('院所地址')
        diagnosis = string_utils.get_str(row['Diagnosis'], 'utf-8')
        doctor_comment = string_utils.get_str(row['DoctorComment'], 'utf-8')

        html = f'''
            <table align=center cellpadding="10" cellspacing="0" width="98%"
                style="font-size: 16px; border-width: 2px; border-style: solid; border-color: black; border-collapse: collapse">
                <tbody>
                    <tr>
                        <th{self.html_bg_color} style="{self.font_size}; text-align: left; vertical-align: middle">
                            診斷 <font size="5">Diagnosis</font>
                        </th>
                    </tr>
                    <tr>
                        <td style="{self.font_size}; white-space:pre-line">{diagnosis}<br></td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color} style="{self.font_size}; text-align: left; vertical-align: middle">
                            醫囑 <font size="5">Doctor's Comment</font>
                        </th>
                    </tr>
                    <tr>
                        <td style="{self.font_size}; white-space:pre-line">{doctor_comment}<br></td>
                    </tr>
                    <tr>
                        <td>
                            <h2>
                                以上病人經本院(所)醫師診斷屬實特予證明<br>
                                <font size="5">
                                    This certificate is invalid without the seal of the Hospital Director.
                                </font>
                            </h2>
                            <h2>
                                主治醫師 <font size="5">Physician</font>: {physician}<br>
                                醫師證書號碼 <font size="5">Physician Certificate No.</font>: {physician_cert_no}<br><br>
                                院長 <font size="5">President</font>: {president}<br>
                                開業執照號碼 <font size="5">License Number</font>: {license_no}
                            </h2>
                            <h2>
                                院所電話 <font size="5">Telephone</font>: {clinic_telephone}<br>
                                院所地址 <font size="5">Address</font>: {clinic_address}
                            </h2>
                            <h2>
                                開立{self.title}日期 <font size="5">Certificate Date</font>: {certificate_date}
                            </h2>
                        </td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

    @staticmethod
    def _get_html_remark():
        html = '''
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td>本證明書經塗改或未加蓋本院印章者無效</td>
                    </tr>
                    <tr>
                        <td>本證明書訴訟無效</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

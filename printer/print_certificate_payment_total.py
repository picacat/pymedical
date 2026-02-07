# -*- coding: UTF-8 -*-

import os

from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import (
    certificate_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    printer_utils,
    string_utils,
    system_utils,
)


# 費用明細總表
# 2018.09.26
class PrintCertificatePaymentTotal:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.certificate_key = args[2]
        try:
            self.print_ins_fee = args[3]
        except Exception:
            self.print_ins_fee = True

        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, "報表印表機")
        self.ins_apply_path = nhi_utils.get_dir(self.system_settings, "申報路徑")
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

        if self.system_settings.field("列印報表雙色印刷") == "Y":
            self.html_bg_color = ' bgcolor="LightGray"'
        else:
            self.html_bg_color = ""

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
        self.preview_dialog.resize(
            geometry.width(), geometry.height()
        )  # for use in Linux
        self.preview_dialog.setWindowState(QtCore.Qt.WindowMaximized)
        self.preview_dialog.exec_()

    def save_to_pdf(self):
        export_dir = f"{self.ins_apply_path}/certificate"
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f"{export_dir}/certificate_total{self.certificate_key}.pdf"
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def save_to_pdf_by_dialog(self):
        export_dir = f"{self.ins_apply_path}/certificate"
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)

        pdf_file_name = f"{export_dir}/certificate_total{self.certificate_key}.pdf"

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出費用總表pdf",
            pdf_file_name,
            "所有檔案 (*);;pdf檔 (*.pdf)",
            options=options,
        )
        if not file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(file_name)
        self.print_html(True)
        system_utils.show_message_box(
            QMessageBox.Information,
            "匯出完成",
            '<font size="5" color="red"><b>費用總表pdf檔案已匯出完成</b></font>',
            "",
        )

    def print_painter(self):
        self.current_print = self.print_painter
        self.printer.setPaperSize(QtCore.QSizeF(80, 80), QPrinter.Millimeter)

        painter = QtGui.QPainter()
        painter.setFont(self.font)
        painter.begin(self.printer)
        painter.drawText(0, 10, "print test line1 中文測試")
        painter.drawText(0, 30, "print test line2 中文測試")
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
        sql = f"""
            SELECT * FROM certificate
            WHERE
                CertificateKey = {self.certificate_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        html_title = self._get_html_title(row)
        html_patient = self._get_html_patient(row)
        html_payment = self._get_html_payment(row)
        html_summary = self._get_html_summary(row)
        html_remark = self._get_html_remark()

        html = f"""
            <html>
              <body>
                {html_title}
                {html_patient}
                {html_payment}
                {html_summary}
                {html_remark}
              </body>
            </html>
        """

        return html

    def _get_html_title(self, row):
        clinic_name = self.system_settings.field("院所名稱")
        certificate_key = f"{row['CertificateKey']:0>8}"

        html = f"""
            <h1 style="text-align: center">{clinic_name} 醫療費用收據</h1>
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td><h3>編號: {certificate_key}</h3></td>
                    </tr>
                </tbody>
            </table>
        """

        return html

    def _get_html_patient(self, row):
        patient_row = patient_utils.get_patient_row(self.database, row["PatientKey"])
        case_date = string_utils.xstr(row["StartDate"])

        if row["EndDate"] != row["StartDate"]:
            case_date += f" 至 {row['EndDate']}"

        case_time = self._get_case_time(row)
        patient_key = f"{row['PatientKey']:0>6}"
        name = string_utils.xstr(row["Name"])
        gender = string_utils.xstr(patient_row["Gender"])
        birthday = string_utils.xstr(patient_row["Birthday"])
        patient_id = string_utils.xstr(patient_row["ID"])
        telephone = string_utils.xstr(patient_row["Telephone"])
        if telephone in ["", None]:
            telephone = string_utils.xstr(patient_row["Cellphone"])

        address = string_utils.xstr(patient_row["Address"])

        html = f"""
            <table align=center cellpadding="2" cellspacing="0" width="98%"
                style="font-size: 18px; border-width: 1px; border-style: solid; border-collapse: collapse">
                <tbody>
                    <tr>
                        <th{self.html_bg_color}>姓名</th>
                        <td style="text-align: center; vertical-align: middle">{name}</td>
                        <th{self.html_bg_color}>性別</th>
                        <td style="text-align: center; vertical-align: middle">{gender}</td>
                        <th{self.html_bg_color}>出生日期</th>
                        <td style="text-align: center; vertical-align: middle">{birthday}</td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color}>病歷號碼</th>
                        <td style="text-align: center; vertical-align: middle">{patient_key}</td>
                        <th{self.html_bg_color}>身份證號</th>
                        <td style="text-align: center; vertical-align: middle">{patient_id}</td>
                        <th{self.html_bg_color}>電話</th>
                        <td style="text-align: center; vertical-align: middle">{telephone}</td>
                    <tr>
                        <th{self.html_bg_color}>地址</th>
                        <td colspan="5" style="text-align: left; vertical-align: middle">{address}</td>
                    </tr>
                    <tr>
                        <th{self.html_bg_color} style="vertical-align: middle">科別</th>
                        <td style="text-align: center; vertical-align: middle">60 中醫科</td>
                        <th{self.html_bg_color}>門診期間</th>
                        <td colspan="3" style="text-align: center; vertical-align: middle">
                            {case_date} 共{case_time}次
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        return html

    def _get_case_time(self, row):
        sql = f"""
            SELECT certificate_items.InsType, certificate_items.CaseDate, cases.TreatType FROM certificate_items
                LEFT JOIN cases ON cases.CaseKey = certificate_items.CaseKey
            WHERE
                CertificateKey = {self.certificate_key} AND
                cases.TreatType != "開立證明"
            ORDER BY CaseDate
        """
        rows = self.database.select_record(sql)

        case_time = 0
        for row in rows:
            # if string_utils.xstr(row['InsType']) == '健保':  # 2022-03-29 光隆 只算自費
            #     case_time += 1
            case_time += 1

        return case_time

    def _get_rows_by_script(self, row):
        start_date = row["StartDate"]
        start_date = f"{start_date} 00:00:00"

        end_date = row["EndDate"]
        end_date = f"{end_date} 23:59:59"

        patient_key = row["PatientKey"]

        treat_type_dict = {
            "針傷科": nhi_utils.INS_TREAT,
            "針灸科": nhi_utils.ACUPUNCTURE_TREAT,
            "傷骨科": nhi_utils.MASSAGE_TREAT,
        }

        condition = ""
        ins_type = string_utils.xstr(row["InsType"])
        treat_type = string_utils.xstr(row["TreatType"])
        if treat_type == "":
            treat_type = "全部"

        if ins_type in ["健保", "自費"]:
            condition = f' AND InsType = "{ins_type}" '

        if treat_type == "內科":
            condition += ' AND TreatType = "內科" '
        elif treat_type != "全部":
            treat_type_list = tuple(treat_type_dict[treat_type])
            condition += f" AND TreatType IN {treat_type_list} "

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

    def _get_html_payment(self, row):
        ins_type = string_utils.xstr(row["InsType"])
        fees_detail = self._get_fees_detail(ins_type)
        fees_detail = certificate_utils.get_total_certificate_fees(
            self.database, self.certificate_key
        )

        name = string_utils.xstr(row["Name"])
        start_date = string_utils.xstr(row["StartDate"])
        end_date = string_utils.xstr(row["EndDate"])
        total_cash_fee = fees_detail["total_cash_fee"]

        regist_fee = fees_detail["total_regist_fee"]
        diag_share_fee = fees_detail["total_diag_share_fee"]
        drug_share_fee = fees_detail["total_drug_share_fee"]

        total_self_drug_fee = fees_detail["total_self_drug_fee"]
        total_self_treat_fee = fees_detail["total_self_treat_fee"]
        total_misc_fee = fees_detail["total_misc_fee"]
        total_certificate_fee = fees_detail["total_certificate_fee"]

        diag_fee = fees_detail["total_diag_fee"]
        drug_fee = fees_detail["total_drug_fee"]
        pharmacy_fee = fees_detail["total_pharmacy_fee"]
        acupuncture_fee = fees_detail["total_acupuncture_fee"]
        massage_fee = fees_detail["total_massage_fee"]
        dislocate_fee = fees_detail["total_dislocate_fee"]
        ins_apply_fee = fees_detail["total_ins_apply_fee"]

        treat_fee = acupuncture_fee + massage_fee + dislocate_fee

        extra_fee = (
            ins_apply_fee
            - diag_fee
            - drug_fee
            - pharmacy_fee
            - treat_fee
            + (diag_share_fee + drug_share_fee)
        )
        treat_fee += extra_fee

        medicine_fee_field_name = self.system_settings.field(
            "醫療費用證明自費藥費欄位名稱"
        )
        if medicine_fee_field_name in ["", None]:
            medicine_fee_field_name = "自費藥費"

        treat_fee_field_name = self.system_settings.field(
            "醫療費用證明自費處置欄位名稱"
        )
        if treat_fee_field_name in ["", None]:
            treat_fee_field_name = "處置費用"

        misc_fee_field_name = self.system_settings.field("醫療費用證明其他費用欄位名稱")
        if misc_fee_field_name in ["", None]:
            misc_fee_field_name = "其他費用"

        if self.system_settings.field("費用總表合併處置費至藥費") == "Y":
            total_self_drug_fee += total_self_treat_fee
            drug_fee_str = f"""
                {medicine_fee_field_name}: {total_self_drug_fee}
            """
        else:
            drug_fee_str = f"""
                {medicine_fee_field_name}: {total_self_drug_fee}<br>
                {treat_fee_field_name}: {total_self_treat_fee}
            """

        case_html = f"""
            <tr>
                <td>
                    <b>醫療費用明細表</b><br><br>
                    茲收到 {name} 君於本院就診醫療費用共NT${total_cash_fee}元整, 費用明細如下:
                    <div align="left" style="margin-left: 40px">
                        掛號金額: {regist_fee}<br>
                        門診負擔: {diag_share_fee}<br>
                        藥品負擔: {drug_share_fee}<br>
                        {drug_fee_str}<br>
                        {misc_fee_field_name}: {total_misc_fee}<br>
                        診斷證明: {total_certificate_fee}
                    </div>
                </td>
            </tr>
        """
        ins_html = f"""
            <tr>
                <td>
                    <b>健保給付點數表</b><br><br>
                    {name} 君於本院就診期間 {start_date} 至 {end_date}, 健保醫療給付點數共{ins_apply_fee}點整<br>
                    給付點數明細如下:
                    <div align="left" style="margin-left: 40px">
                        門診診察費: {diag_fee}<br>
                        健保內服藥: {drug_fee}<br>
                        藥事服務費: {pharmacy_fee}<br>
                        治療處置費: {treat_fee}<br>
                    </div><br>
                    扣除門診負擔NT${diag_share_fee}及藥品負擔NT${drug_share_fee}後, 實付淨額為{ins_apply_fee}點整<br>
                    (以上所列點數僅供參考)
                </td>
            </tr>
        """
        if not self.print_ins_fee:
            ins_html = ""

        html = f"""
            <table align=center cellpadding="10" cellspacing="0" width="98%"
                   style="font-size: 18px; border-width: 1px; border-style: solid; border-collapse: collapse">
                <tbody>
                    {case_html}
                    {ins_html}
                </tbody>
            </table>
        """
        return html

    def _get_fees_detail(self, ins_type):
        sql = f"""
            SELECT certificate_items.*, cases.TreatType FROM certificate_items
                LEFT JOIN cases ON certificate_items.CaseKey = cases.CaseKey
            WHERE
                CertificateKey = {self.certificate_key}
            ORDER BY CaseDate
        """
        rows = self.database.select_record(sql)

        fees_detail = {
            "total_cash_fee": 0,
            "total_regist_fee": 0,
            "total_diag_share_fee": 0,
            "total_drug_share_fee": 0,
            "total_diag_fee": 0,
            "total_drug_fee": 0,
            "total_pharmacy_fee": 0,
            "total_acupuncture_fee": 0,
            "total_massage_fee": 0,
            "total_dislocate_fee": 0,
            "total_total_fee": 0,
            "total_ins_apply_fee": 0,
        }

        for row in rows:
            regist_fee = number_utils.get_integer(row["RegistFee"])
            diag_share_fee = number_utils.get_integer(row["SDiagShareFee"])
            drug_share_fee = number_utils.get_integer(row["SDrugShareFee"])
            total_fee = number_utils.get_integer(row["TotalFee"])
            # if ins_type in ['健保'] or string_utils.xstr(row['TreatType']) in ['開立證明']:
            #     total_fee = 0

            diag_fee = number_utils.get_integer(row["DiagFee"])
            drug_fee = number_utils.get_integer(row["InterDrugFee"])
            pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
            acupuncture_fee = number_utils.get_integer(row["AcupunctureFee"])
            massage_fee = number_utils.get_integer(row["MassageFee"])
            dislocate_fee = number_utils.get_integer(row["DislocateFee"])
            ins_apply_fee = number_utils.get_integer(row["InsApplyFee"])

            fees_detail["total_regist_fee"] += regist_fee
            fees_detail["total_diag_share_fee"] += diag_share_fee
            fees_detail["total_drug_share_fee"] += drug_share_fee
            fees_detail["total_diag_fee"] += diag_fee
            fees_detail["total_drug_fee"] += drug_fee
            fees_detail["total_pharmacy_fee"] += pharmacy_fee
            fees_detail["total_acupuncture_fee"] += acupuncture_fee
            fees_detail["total_massage_fee"] += massage_fee
            fees_detail["total_dislocate_fee"] += dislocate_fee

            fees_detail["total_total_fee"] += total_fee
            fees_detail["total_cash_fee"] += (
                regist_fee + diag_share_fee + drug_share_fee + total_fee
            )
            fees_detail["total_ins_apply_fee"] += ins_apply_fee

        return fees_detail

    def _get_html_summary(self, row):
        physician = string_utils.xstr(row["Doctor"])
        physician_cert_no = personnel_utils.get_person_field_value(
            self.database, physician, "Certificate"
        )
        president = self.system_settings.field("負責醫師")
        license_no = self.system_settings.field("院所代號")
        clinic_telephone = self.system_settings.field("院所電話")
        clinic_address = self.system_settings.field("院所地址")

        year = row["CertificateDate"].year
        month = row["CertificateDate"].month
        day = row["CertificateDate"].day
        certificate_date = f"{year} 年 {month} 月 {day} 日"

        html = f"""
            <table align=center cellpadding="10" cellspacing="0" width="98%"
                style="font-size: 18px; border-width: 1px; border-style: solid; border-collapse: collapse">
                <tbody>
                    <tr>
                        <td>
                            <b>本收據可為報稅之憑證，請妥善保存，遺失恕不補發。</b>
                            <div align="left" style="margin-left: 0px">
                                主治醫師: {physician}<br>
                                醫師證書號碼: {physician_cert_no}<br>
                                院長: {president}<br>
                                開業執照號碼: {license_no}<br>
                                院所電話: {clinic_telephone}<br>
                                院所地址: {clinic_address}<br>
                            </div>
                            <br>
                            開立醫療費用收據日期: {certificate_date}
                        </td>
                    </tr>
                </tbody>
            </table>
        """
        return html

    @staticmethod
    def _get_html_remark():
        html = """
            <table align=center width="98%" cellspacing="0">
                <tbody>
                    <tr>
                        <td>本證明書經塗改或未加蓋本院印章者無效</td>
                    </tr>
                </tbody>
            </table>
        """

        return html


# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import date_utils


# 列印結帳日報表
# 2019.03.38
class PrintIncome:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.orientation = args[2]
        self.income_date = args[3]
        self.income_period = args[4]
        self.tableWidget_income_list = args[5]
        self.tableWidget_total = args[6]
        self.columns = args[7]
        self.ui = None

        self.printer = printer_utils.get_printer(self.system_settings, '報表印表機')
        self.preview_dialog = QtPrintSupport.QPrintPreviewDialog(self.printer)
        self.current_print = None

        if self.system_settings.field('列印報表雙色印刷') == 'Y':
            self.html_bg_color = ' bgcolor="LightGray"'
        else:
            self.html_bg_color = ''

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
        self.font = QtGui.QFont(font, 7, QtGui.QFont.PreferQuality)

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
            f'{self.income_date}-{self.income_period}-門診現金收入報表.pdf',
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
        if self.orientation == 'portrait':
            self.printer.setOrientation(QPrinter.Portrait)
        elif self.orientation == 'landscape':
            self.printer.setOrientation(QPrinter.Landscape)
            font = system_utils.get_font(self.system_settings)
            self.font = QtGui.QFont(font, 10, QtGui.QFont.PreferQuality)

        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')

        table_income = self._get_table_income_portrait_html()
        if self.orientation == 'portrait':
            table_income = self._get_table_income_portrait_html()
        elif self.orientation == 'landscape':
            table_income = self._get_table_income_landscape_html()

        table_total = self._get_table_total_html()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 門診現金收入日報表</h2>
                    <div align="left" style="margin-left: 40px">統計日期: {self.income_date} {self.income_period}</div>
                    {table_income}
                    <br><br>
                    {table_total}
                </body>
            </html>
        '''

        return html

    def _get_income_rows(self):
        income_rows = ''

        for row_no in range(self.tableWidget_income_list.rowCount()):
            case_date = self.tableWidget_income_list.item(row_no, self.columns['case_date']).text()[11:16]
            # case_date = date_utils.date_to_zh_tw_date(case_date)
            period = self.tableWidget_income_list.item(row_no, self.columns['period']).text()
            patient_key = self.tableWidget_income_list.item(row_no, self.columns['patient_key']).text()
            name = self.tableWidget_income_list.item(row_no, self.columns['name']).text()
            ins_type = self.tableWidget_income_list.item(row_no, self.columns['ins_type']).text()
            share_type = self.tableWidget_income_list.item(row_no, self.columns['share_type']).text()[:2]
            treat_type = self.tableWidget_income_list.item(row_no, self.columns['treat_type']).text()[:4]
            discount_type = self.tableWidget_income_list.item(row_no, self.columns['discount_type']).text()
            card = self.tableWidget_income_list.item(row_no, self.columns['card']).text()
            regist_fee = self.tableWidget_income_list.item(row_no, self.columns['regist_fee']).text()
            diag_share_fee = self.tableWidget_income_list.item(row_no, self.columns['diag_share_fee']).text()
            drug_share_fee = self.tableWidget_income_list.item(row_no, self.columns['drug_share_fee']).text()
            deposit_fee = self.tableWidget_income_list.item(row_no, self.columns['deposit_fee']).text()
            refund = self.tableWidget_income_list.item(row_no, self.columns['refund_fee']).text()
            repayment = self.tableWidget_income_list.item(row_no, self.columns['repayment']).text()
            total_fee = self.tableWidget_income_list.item(row_no, self.columns['self_total_fee']).text()
            debt = self.tableWidget_income_list.item(row_no, self.columns['debt']).text()
            regist_debt = self.tableWidget_income_list.item(row_no, self.columns['regist_debt']).text()
            massage_fee = self.tableWidget_income_list.item(row_no, self.columns['massage_fee']).text()
            receipt_fee = self.tableWidget_income_list.item(row_no, self.columns['receipt_fee']).text()
            try:
                regist_no = self.tableWidget_income_list.item(row_no, self.columns['regist_no']).text()
            except Exception:
                regist_no = ''

            sequence = row_no + 1

            if self.tableWidget_income_list.item(row_no, 4).text() == '合計':
                sequence = ''

            pres_days = self.tableWidget_income_list.item(row_no, self.columns['pres_days'])
            if pres_days is not None:
                pres_days = pres_days.text()
            else:
                pres_days = '0'

            registrar = self.tableWidget_income_list.item(row_no, self.columns['registrar'])
            if registrar is not None:
                registrar = registrar.text()
            else:
                registrar = ''

            cashier = self.tableWidget_income_list.item(row_no, self.columns['cashier'])
            if cashier is not None:
                cashier = cashier.text()
            else:
                cashier = ''

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and row_no % 2 > 0:
                bg_color = ' bgcolor="#E3E3E3"'

            if self.orientation == 'portrait':
                share_type = share_type[:2]
                discount_type = discount_type[:2]
            else:
                share_type = share_type[:4]
                discount_type = discount_type[:4]

            if name == '合計':
                sequence = ''

            income_rows += f'''
                <tr{bg_color}>
                    <td align=center>{sequence}</td>
                    <td align=right>{regist_no}</td>
                    <td align=center>{case_date}</td>
                    <td align=right>{patient_key}</td>
                    <td align=left>{name}</td>
                    <td align=center>{ins_type}</td>
                    <td align=center>{share_type}</td>
                    <td align=center>{discount_type[:2]}</td>
                    <td align=center>{treat_type}</td>
                    <td align=center>{card}</td>
                    <td align=center>{pres_days}</td>
                    <td align=right>{regist_fee}</td>
                    <td align=right>{diag_share_fee}</td>
                    <td align=right>{drug_share_fee}</td>
                    <td align=right>{deposit_fee}</td>
                    <td align=right>{refund}</td>
                    <td align=right>{repayment}</td>
                    <td align=right>{total_fee}</td>
                    <td align=right>{debt}</td>
                    <td align=right>{regist_debt}</td>
                    <td align=right>{massage_fee}</td>
                    <td align=right>{receipt_fee}</td>
                    <td align=center>{registrar}</td>
                    <td align=center>{cashier}</td>
                </tr>
            '''
        return income_rows

    def _get_table_income_portrait_html(self):
        income_rows = self._get_income_rows()
        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>診號</th>
                        <th>時間</th>
                        <th>病號</th>
                        <th>姓名</th>
                        <th>保險</th>
                        <th>負擔</th>
                        <th>優待</th>
                        <th>就醫別</th>
                        <th>卡序</th>
                        <th>藥</th>
                        <th>掛號</th>
                        <th>診負</th>
                        <th>藥負</th>
                        <th>欠卡</th>
                        <th>還卡</th>
                        <th>還款</th>
                        <th>自費</th>
                        <th>欠款</th>
                        <th>掛欠</th>
                        <th>民俗</th>
                        <th>實收</th>
                        <th>掛號者</th>
                        <th>批價者</th>
                    </tr>
                </thead>
                <tbody>
                    {income_rows}
                </tbody>
            </table>
        '''

        return html

    def _get_table_income_landscape_html(self):
        income_rows = self._get_income_rows()
        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>診號</th>
                        <th>時間</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>保險</th>
                        <th>負擔別</th>
                        <th>優待</th>
                        <th>就醫別</th>
                        <th>卡序</th>
                        <th>藥日</th>
                        <th>掛號費</th>
                        <th>診負擔</th>
                        <th>藥負擔</th>
                        <th>欠卡費</th>
                        <th>還卡費</th>
                        <th>還款</th>
                        <th>自費</th>
                        <th>欠款</th>
                        <th>掛號欠</th>
                        <th>民俗</th>
                        <th>實收</th>
                        <th>掛號員</th>
                        <th>批價員</th>
                    </tr>
                </thead>
                <tbody>
                    {income_rows}
                </tbody>
            </table>
        '''

        return html

    def _get_table_total_html(self):
        regist_fee = self.tableWidget_total.item(0, 1).text()
        diag_share_fee = self.tableWidget_total.item(1, 1).text()
        drug_share_fee = self.tableWidget_total.item(2, 1).text()
        deposit_fee = self.tableWidget_total.item(3, 1).text()
        refund = self.tableWidget_total.item(4, 1).text()
        repayment = self.tableWidget_total.item(5, 1).text()
        total_fee = self.tableWidget_total.item(6, 1).text()
        receipt_fee = self.tableWidget_total.item(7, 1).text()
        regist_debt = self.tableWidget_total.item(8, 1).text()
        cashier_debt = self.tableWidget_total.item(9, 1).text()
        receipt_total = self.tableWidget_total.item(10, 1).text()

        html = f'''
            <h2 align=center>門診現金收入總表</h2>
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負擔</th>
                        <th>欠卡費</th>
                        <th>還卡費</th>
                        <th>自費還款</th>
                        <th>自費應收</th>
                        <th>自費實收</th>
                        <th>掛號欠款</th>
                        <th>批價欠款</th>
                        <th>實收現金</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td align=right>{regist_fee}</td>
                        <td align=right>{diag_share_fee}</td>
                        <td align=right>{drug_share_fee}</td>
                        <td align=right>{deposit_fee}</td>
                        <td align=right>{refund}</td>
                        <td align=right>{repayment}</td>
                        <td align=right>{total_fee}</td>
                        <td align=right>{receipt_fee}</td>
                        <td align=right>{regist_debt}</td>
                        <td align=right>{cashier_debt}</td>
                        <td align=right>{receipt_total}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

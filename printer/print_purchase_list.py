
# -*- coding: UTF-8 -*-

from libs import number_utils, printer_utils, purchase_utils, system_utils
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import QFileDialog


# 列印銷售明細
# 2021.10.11
class PrintPurchaseList:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.tableWidget_purchase_list = args[4]
        self.tableWidget_purchase_list_agent = args[5]
        self.no_zero_bonus = args[6]
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
            f'{self.income_date}-{self.income_period}-自費銷售明細.pdf',
            "pdf檔案 (*.pdf);;Text Files (*.txt)", options=options
        )
        if not pdf_file_name:
            return

        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(pdf_file_name)
        self.print_html(True)

    def print_html(self, printing):
        self.current_print = self.print_html

        # self.printer.setOrientation(QPrinter.Portrait)
        self.printer.setOrientation(QPrinter.Landscape)

        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')

        table_purchase_list = self._get_table_purchase_list_html(self.tableWidget_purchase_list)
        table_purchase_list_agent = self._get_table_purchase_list_html(self.tableWidget_purchase_list_agent)
        if table_purchase_list_agent != '':
            table_purchase_list_agent = '<br><h3 align=center>代收費用自費銷售明細表</h3>' + table_purchase_list_agent

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 自費銷售明細表</h2>
                    <div align="left" style="margin-left: 40px">統計日期: 從 {self.start_date} 至 {self.end_date}</div>
                    {table_purchase_list}
                    {table_purchase_list_agent}
                </body>
            </html>
        '''

        return html

    def _get_purchse_list_rows(self, table_widget_purchase_list):
        if table_widget_purchase_list is None:
            return ''
        
        purchase_list_rows = ''
        index = 0
        for row_no in range(table_widget_purchase_list.rowCount()-1):
            doctor_commission = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['doctor_commission']).text()
            doctor_commission = number_utils.get_float(doctor_commission)

            if self.no_zero_bonus and doctor_commission <= 0:
                continue

            index += 1
            case_date = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['case_date']).text()
            period = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['period']).text()
            invoice_no = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['invoice_no']).text()
            patient_key = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['patient_key']).text()
            name = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['name']).text()
            doctor = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['doctor']).text()
            massager = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['massage_assistant']).text()
            massager_commission = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['massager_commission']).text()
            cashier = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['nursing_assistant']).text()
            cashier_commission = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['cashier_commission']).text()
            medicine_name = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['medicine_name']).text()
            unit = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['unit']).text()
            quantity = number_utils.get_float(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['total_dosage']).text())
            price = number_utils.get_float(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['price']).text())
            amount = quantity * price
            discount = number_utils.get_integer(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['discount']).text())
            total_fee = number_utils.get_integer(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['total_fee']).text())
            receipt_fee = number_utils.get_integer(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['receipt_fee']).text())
            debt = number_utils.get_integer(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['debt']).text())
            repayment_date = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['repayment_date']).text()
            repayment = number_utils.get_integer(table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['repayment']).text())
            remark = table_widget_purchase_list.item(
                row_no, purchase_utils.PURCHASE_COL_NO['remark']).text()

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and row_no % 2 > 0:
                bg_color = ' bgcolor="#e3e3e3"'

            purchase_list_rows += f'''
                <tr{bg_color}>
                    <td align=right>{index}</td>
                    <td align=center>{case_date}</td>
                    <td align=center>{period}</td>
                    <td align=left>{invoice_no}</td>
                    <td align=right>{patient_key}</td>
                    <td align=left>{name}</td>

                    <td align=left>{doctor}</td>
                    <td align=right>{doctor_commission}</td>
                    <td align=left>{massager}</td>
                    <td align=right>{massager_commission}</td>
                    <td align=left>{cashier}</td>
                    <td align=right>{cashier_commission}</td>

                    <td align=left>{medicine_name}</td>
                    <td align=center>{unit}</td>
                    <td align=right>{quantity:.1f}</td>
                    <td align=right>{price}</td>
                    <td align=right>{amount:.1f}</td>
                    <td align=right>{discount}</td>
                    <td align=right>{total_fee}</td>
                    <td align=right>{receipt_fee}</td>
                    <td align=right>{debt}</td>
                    <td align=center>{repayment_date}</td>
                    <td align=right>{repayment}</td>
                    <td align=left>{remark}</td>
                </tr>
            '''
        return purchase_list_rows

    def _get_total_row(self, table_widget_purchase_list):
        row_no = table_widget_purchase_list.rowCount() - 1
        doctor_commission = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['doctor_commission']).text())
        massager_commission = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['massager_commission']).text())
        cashier_commission = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['cashier_commission']).text())
        discount = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['discount']).text())
        total_fee = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['total_fee']).text())
        receipt_fee = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['receipt_fee']).text())
        debt = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['debt']).text())
        repayment = number_utils.get_integer(table_widget_purchase_list.item(
            row_no, purchase_utils.PURCHASE_COL_NO['repayment']).text())

        subtotal = total_fee + discount

        total_row = f'''
            <tr{self.html_bg_color}>
                <td colspan="6" align=center>合計</td>
                <td align=right></td>
                <td align=right>{doctor_commission}</td>
                <td align=right></td>
                <td align=right>{massager_commission}</td>
                <td align=right></td>
                <td align=right>{cashier_commission}</td>
                <td align=right></td>
                <td align=right></td>
                <td align=right></td>
                <td align=right></td>
                <td align=right>{subtotal}</td>
                <td align=right>{discount}</td>
                <td align=right>{total_fee}</td>
                <td align=right>{receipt_fee}</td>
                <td align=right>{debt}</td>
                <td align=right></td>
                <td align=right>{repayment}</td>
                <td align=right></td>
            </tr>
        '''

        return total_row

    def _get_table_purchase_list_html(self, table_widget_purchase_list):
        purchase_rows = self._get_purchse_list_rows(table_widget_purchase_list)
        if len(purchase_rows) == 0:
            return ''

        total_row = self._get_total_row(table_widget_purchase_list)
        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="95%"
                style="border-collapse: collapse; border-width: 1px; border-style: solid;">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>日期</th>
                        <th>班別</th>
                        <th>單據號</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>醫師</th>
                        <th>抽成</th>
                        <th>傷助</th>
                        <th>抽成</th>
                        <th>護佐</th>
                        <th>抽成</th>
                        <th>品名</th>
                        <th>單位</th>
                        <th>總量</th>
                        <th>單價</th>
                        <th>小計</th>
                        <th>折扣</th>
                        <th>應收</th>
                        <th>實收</th>
                        <th>欠款</th>
                        <th>還款日期</th>
                        <th>還款</th>
                        <th>備註</th>
                    </tr>
                </thead>
                <tbody>
                    {purchase_rows}
                    {total_row}
                </tbody>
            </table>
        '''

        return html

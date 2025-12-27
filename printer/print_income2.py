
# -*- coding: UTF-8 -*-

from PyQt5 import QtGui, QtCore, QtPrintSupport, QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtPrintSupport import QPrinter

from libs import printer_utils
from libs import system_utils
from libs import number_utils
from libs import case_utils
from libs import string_utils
from libs import nhi_utils


# 列印結帳日報表
# 2019.03.38
class PrintIncome2:
    # 初始化
    def __init__(self, parent=None, *args):
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.orientation = args[2]
        self.tab_income_cash_flow = args[3]
        self.tab_income_list = args[4]
        self.columns = args[5]

        self.ui = None

        self.income_date = self.tab_income_cash_flow.label_income_date.text()
        self.income_period = self.tab_income_cash_flow.period
        self.income_doctor = self.tab_income_cash_flow.doctor
        self.income_room = self.tab_income_cash_flow.room
        self.income_cashier = self.tab_income_cash_flow.cashier
        self.income_calculate_by_cashier = self.tab_income_cash_flow.calculate_by_cashier
        self.income_source = self.tab_income_cash_flow.income_source
        self.income_regist_type = self.tab_income_cash_flow.regist_type

        self.tableWidget_income_list = self.tab_income_list.tableWidget_income
        self.tableWidget_total = self.tab_income_list.tableWidget_total

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
        self.font = QtGui.QFont(font, 11, QtGui.QFont.PreferQuality)

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

        self.printer.setPaperSize(printer_utils.get_paper_size(self.system_settings))

        document = printer_utils.get_document(self.printer, self.font)
        document.setDocumentMargin(5)
        document.setHtml(self._get_html())
        if printing:
            document.print(self.printer)

    def _get_deposit_list_html(self):
        sql = f'''
            SELECT cases.*, deposit.Fee FROM cases
                LEFT JOIN deposit ON deposit.CaseKey = cases.CaseKey
            WHERE
                DATE(cases.CaseDate) = "{self.income_date}" AND
                cases.InsType = "健保" AND
                deposit.Fee > 0
        '''

        if self.income_period != '全部':
            if self.income_period == '早午班':
                sql += ' AND cases.Period IN("早班", "午班") '
            elif self.income_period == '午晚班':
                sql += ' AND cases.Period IN("午班", "晚班") '
            else:
                sql += f' AND cases.Period = "{self.income_period}"'

        if self.income_doctor != '全部':
            sql += f' AND cases.Doctor = "{self.income_doctor}"'
        if self.income_room != '全部':
            sql += f' AND Room = {self.income_room}'
        if self.income_cashier != '全部':
            if self.income_calculate_by_cashier:
                sql += f' AND cases.Cashier = "{self.income_cashier}"'
            else:
                sql += f' AND cases.Register = "{self.income_cashier}"'

        else:
            if self.income_source == '櫃台':
                sql += ' AND Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Register = "掛號機"'

        if self.income_regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.income_regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' GROUP BY cases.CaseKey ORDER BY cases.CaseDate, FIELD(cases.Period, {period_list})'

        deposit_rows = self.database.select_record(sql)
        if len(deposit_rows) <= 0:
            return ''

        deposit_rows_html = ''
        i = 0
        for row in deposit_rows:
            i += 1
            deposit_rows_html += f'''
                <tr>
                    <td align="center">{i}</td>
                    <td align="center">{row["CaseDate"].date()}</td>
                    <td align="center">{row["Period"]}</td>
                    <td align="right" style="padding-right: 10px">{row["PatientKey"]}</td>
                    <td align="center">{string_utils.xstr(row["Name"])}</td>
                    <td align="right" style="padding-right: 10px">{row["Fee"]}</td>
                    <td align="center">{string_utils.xstr(row["Register"])}</td>
                </tr>
            '''

        html = f'''
            <h2 align=center> 欠卡明細</h2>
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>欠卡日期</th>
                        <th>班別</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>欠卡費</th>
                        <th>掛號員</th>
                    </tr>
                    {deposit_rows_html}
                </tbody>
            </table>
        '''

        return html

    def _get_refund_list_html(self):
        sql = f'''
            SELECT
                deposit.*,
                cases.CaseDate, cases.InsType, cases.Share, cases.Card, cases.TreatType,
                cases.Continuance, cases.RefundFee, cases.RegistPaymentType
            FROM deposit
                LEFT JOIN cases ON deposit.CaseKey = cases.CaseKey
            WHERE
                DATE(ReturnDate) = "{self.income_date}" AND
                Fee > 0
        '''

        if self.income_period != '全部':
            if self.income_period == '早午班':
                sql += ' AND cases.Period IN("早班", "午班") '
            elif self.income_period == '午晚班':
                sql += ' AND cases.Period IN("午班", "晚班") '
            else:
                sql += f' AND cases.Period = "{self.income_period}"'

        if self.income_doctor != '全部':
            sql += f' AND cases.Doctor = "{self.income_doctor}"'

        if self.income_cashier != '全部':
            sql += f' AND Refunder = "{self.income_cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND Refunder != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Refunder = "掛號機"'

        if self.income_regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.income_regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' ORDER BY DepositDate, FIELD(deposit.Period, {period_list})'

        refund_rows = self.database.select_record(sql)
        if len(refund_rows) <= 0:
            return ''

        refund_rows_html = ''
        i = 0
        for row in refund_rows:
            i += 1
            refund_rows_html += f'''
                <tr>
                    <td align="center" >{i}</td>
                    <td align="center" >{row["CaseDate"].date()}</td>
                    <td align="center">{row["ReturnDate"].date()}</td>
                    <td align="center">{row["Period"]}</td>
                    <td align="right" style="padding-right: 10px">{row["PatientKey"]}</td>
                    <td align="center">{string_utils.xstr(row["Name"])}</td>
                    <td align="right" style="padding-right: 10px">{-row["Fee"]}</td>
                    <td align="center">{string_utils.xstr(row["Refunder"])}</td>
                </tr>
            '''

        html = f'''
            <h2 align=center> 還卡明細</h2>
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>就醫日期</th>
                        <th>還卡日期</th>
                        <th>班別</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>還卡費</th>
                        <th>還款員</th>
                    </tr>
                    {refund_rows_html}
                </tbody>
            </table>
        '''

        return html

    def _get_debt_list_html(self):
        sql = f'''
            SELECT
                debt.*, cases.Register, cases.Doctor
            FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                DATE(debt.CaseDate) = "{self.income_date}" AND
                Fee > 0
        '''

        if self.income_period != '全部':
            if self.income_period == '早午班':
                sql += ' AND debt.Period IN("早班", "午班") '
            elif self.income_period == '午晚班':
                sql += ' AND debt.Period IN("午班", "晚班") '
            else:
                sql += f' AND debt.Period = "{self.income_period}"'

        if self.income_doctor != '全部':
            sql += f' AND cases.Doctor = "{self.income_doctor}"'

        if self.income_cashier != '全部':
            sql += f' AND cases.Register = "{self.income_cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND cases.Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND cases.Register = "掛號機"'

        if self.income_regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.income_regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' ORDER BY debt.CaseDate, FIELD(debt.Period, {period_list})'

        debt_row = self.database.select_record(sql)
        if len(debt_row) <= 0:
            return ''

        debt_rows_html = ''
        i = 0
        for row in debt_row:
            i += 1
            debt_rows_html += f'''
                <tr>
                    <td align="center" >{i}</td>
                    <td align="center" >{row["CaseDate"].date()}</td>
                    <td align="center">{row["Period"]}</td>
                    <td align="right" style="padding-right: 10px">{row["PatientKey"]}</td>
                    <td align="center">{string_utils.xstr(row["Name"])}</td>
                    <td align="center">{string_utils.xstr(row["DebtType"])}</td>
                    <td align="right" style="padding-right: 10px">{-row["Fee"]}</td>
                    <td align="center">{string_utils.xstr(row["Doctor"])}</td>
                    <td align="center">{string_utils.xstr(row["Register"])}</td>
                </tr>
            '''

        html = f'''
            <h2 align=center>欠款明細</h2>
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>欠款日期</th>
                        <th>班別</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>欠款類別</th>
                        <th>欠款金額</th>
                        <th>主治醫師</th>
                        <th>掛號員</th>
                    </tr>
                    {debt_rows_html}
                </tbody>
            </table>
        '''

        return html

    def _get_repayment_list_html(self):
        sql = f'''
            SELECT
                debt.*, cases.Register, cases.Doctor
            FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                DATE(debt.ReturnDate1) = "{self.income_date}" AND
                TotalReturn > 0
        '''

        if self.income_period != '全部':
            if self.income_period == '早午班':
                sql += ' AND debt.Period IN("早班", "午班") '
            elif self.income_period == '午晚班':
                sql += ' AND debt.Period IN("午班", "晚班") '
            else:
                sql += f' AND debt.Period = "{self.income_period}"'

        if self.income_doctor != '全部':
            sql += f' AND cases.Doctor = "{self.income_doctor}"'

        if self.income_cashier != '全部':
            sql += f' AND cases.Register = "{self.income_cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND cases.Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND cases.Register = "掛號機"'

        if self.income_regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.income_regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' ORDER BY debt.CaseDate, FIELD(debt.Period, {period_list})'

        debt_row = self.database.select_record(sql)
        if len(debt_row) <= 0:
            return ''

        debt_rows_html = ''
        i = 0
        for row in debt_row:
            i += 1
            debt_rows_html += f'''
                <tr>
                    <td align="center" >{i}</td>
                    <td align="center" >{row["CaseDate"].date()}</td>
                    <td align="center" >{row["ReturnDate1"].date()}</td>
                    <td align="center">{row["Period1"]}</td>
                    <td align="right" style="padding-right: 10px">{row["PatientKey"]}</td>
                    <td align="center">{row["Name"]}</td>
                    <td align="right" style="padding-right: 10px">{-row["Fee"]}</td>
                    <td align="right" style="padding-right: 10px">{row["Fee1"]}</td>
                    <td align="center">{row["Register"]}</td>
                </tr>
            '''

        html = f'''
            <h2 align=center>還款明細</h2>
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>欠款日期</th>
                        <th>還款日期</th>
                        <th>班別</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>欠款金額</th>
                        <th>還款金額</th>
                        <th>掛號員</th>
                    </tr>
                    {debt_rows_html}
                </tbody>
            </table>
        '''

        return html

    def _get_html(self):
        clinic_name = self.system_settings.field('院所名稱')

        table_income = self._get_table_income_portrait_html()
        if self.orientation == 'portrait':
            table_income = self._get_table_income_portrait_html()
        elif self.orientation == 'landscape':
            table_income = self._get_table_income_landscape_html()

        deposit_list = self._get_deposit_list_html()
        return_card_list = self._get_refund_list_html()
        debt_list = self._get_debt_list_html()
        repayment_list = self._get_repayment_list_html()

        table_total = self._get_table_total_html()

        html = f'''
            <html>
                <body>
                    <br>
                    <h2 align=center>{clinic_name} 門診現金收入日報表</h2>
                    <div align="left" style="margin-left: 40px">統計日期: {self.income_date} {self.income_period}</div>
                    {table_income}
                    <br><hr>
                    {deposit_list}
                    {return_card_list}
                    {debt_list}
                    {repayment_list}
                    {table_total}
                </body>
            </html>
        '''

        return html

    def _get_income_rows(self):
        income_rows = ''

        for row_no in range(self.tableWidget_income_list.rowCount()):
            case_key = self.tableWidget_income_list.item(row_no, self.columns['case_key']).text()
            patient_key = self.tableWidget_income_list.item(row_no, self.columns['patient_key']).text()
            name = self.tableWidget_income_list.item(row_no, self.columns['name']).text()
            ins_type = self.tableWidget_income_list.item(row_no, self.columns['ins_type']).text()
            share_type = self.tableWidget_income_list.item(row_no, self.columns['share_type']).text()
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
            receipt_fee = self.tableWidget_income_list.item(row_no, self.columns['receipt_fee']).text()
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

            # doctor = self.tableWidget_income_list.item(row_no, self.columns['cashier'])
            # if doctor is not None:
            #     doctor = doctor.text()
            # else:
            #     doctor = ''
            doctor = case_utils.get_case_field_value(self.database, case_key, 'Doctor')
            if doctor is None:
                doctor = ''
            else:
                doctor = string_utils.xstr(doctor)

            bg_color = ''
            if self.system_settings.field('列印報表雙色印刷') == 'Y' and row_no % 2 > 0:
                bg_color = ' bgcolor="#E3E3E3"'

            if self.orientation == 'portrait':
                share_type = share_type[:2]
                discount_type = discount_type[:2]
            else:
                share_type = share_type[:4]
                discount_type = discount_type[:4]

            income_rows += f'''
                <tr{bg_color}>
                    <td align=right>{sequence}</td>
                    <td align=left>{name}</td>
                    <td align=right>{patient_key}</td>
                    <td align=center>{ins_type}</td>
                    <td align=left>{share_type}</td>
                    <td align=left>{discount_type}</td>
                    <td align=left>{card}</td>
                    <td align=right>{regist_fee}</td>
                    <td align=right>{diag_share_fee}</td>
                    <td align=right>{drug_share_fee}</td>
                    <td align=right>{deposit_fee}</td>
                    <td align=right>{refund}</td>
                    <td align=right>{repayment}</td>
                    <td align=right>{total_fee}</td>
                    <td align=right>{debt}</td>
                    <td align=right>{regist_debt}</td>
                    <td align=right>{receipt_fee}</td>
                    <td align=left>{doctor}</td>
                </tr>
            '''
        return income_rows

    def _get_table_income_portrait_html(self):
        income_rows = self._get_income_rows()
        html = f'''
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; ">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th align="left">姓名</th>
                        <th>病歷號</th>
                        <th>保險</th>
                        <th>負擔</th>
                        <th>優待</th>
                        <th>卡序</th>
                        <th>掛號</th>
                        <th>診負</th>
                        <th>藥負</th>
                        <th>欠卡</th>
                        <th>還卡</th>
                        <th>還款</th>
                        <th>自費</th>
                        <th>欠款</th>
                        <th>掛欠</th>
                        <th>實收</th>
                        <th>醫師</th>
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
                style="font-size: 12px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <thead>
                    <tr{self.html_bg_color}>
                        <th>序</th>
                        <th>門診日期</th>
                        <th>班別</th>
                        <th>病歷號</th>
                        <th>姓名</th>
                        <th>保險</th>
                        <th>負擔類別</th>
                        <th>優待</th>
                        <th>卡序</th>
                        <th>就醫類別</th>
                        <th>卡序</th>
                        <th>藥日</th>
                        <th>掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負單</th>
                        <th>欠卡費</th>
                        <th>還卡費</th>
                        <th>自費還款</th>
                        <th>自費應收</th>
                        <th>自費欠款</th>
                        <th>掛號欠款</th>
                        <th>民俗調理</th>
                        <th>實收現金</th>
                        <th>掛號人員</th>
                        <th>主治醫師</th>
                    </tr>
                </thead>
                <tbody>
                    {income_rows}
                </tbody>
            </table>
        '''

        return html

    def _get_table_total_html(self):
        ins_regist_fee = number_utils.get_integer(self.tableWidget_total.item(1, 1).text())
        diag_share_fee = number_utils.get_integer(self.tableWidget_total.item(1, 2).text())
        drug_share_fee = number_utils.get_integer(self.tableWidget_total.item(1, 3).text())
        deposit_fee = number_utils.get_integer(self.tableWidget_total.item(1, 4).text())
        refund = number_utils.get_integer(self.tableWidget_total.item(1, 5).text())
        regist_debt = number_utils.get_integer(self.tableWidget_total.item(1, 6).text())
        ins_total = number_utils.get_integer(self.tableWidget_total.item(1, 7).text())

        self_regist_fee = number_utils.get_integer(self.tableWidget_total.item(3, 1).text())
        self_total_fee = number_utils.get_integer(self.tableWidget_total.item(3, 2).text())
        total_fee = number_utils.get_integer(self.tableWidget_total.item(3, 3).text())
        debt = number_utils.get_integer(self.tableWidget_total.item(3, 4).text())
        receipt_total = number_utils.get_integer(self.tableWidget_total.item(3, 5).text())
        repayment = number_utils.get_integer(self.tableWidget_total.item(3, 6).text())
        self_total = number_utils.get_integer(self.tableWidget_total.item(3, 7).text())

        massage_fee = number_utils.get_integer(self.tableWidget_total.item(1, 8).text())
        cash_total = number_utils.get_integer(self.tableWidget_total.item(1, 9).text())

        html = f'''
            <h2 align=center> 門診現金收入總表</h2>
            <table align=center cellpadding="1" cellspacing="0" width="100%"
                style="font-size: 15px; border-collapse: collapse; border-width: 1px; border-style: solid; border-color: black">
                <tbody>
                    <tr{self.html_bg_color}>
                        <th rowspan="2" style="text-align: center; vertical-align: middle">健保</th>
                        <th>掛號費</th>
                        <th>門診負擔</th>
                        <th>藥品負擔</th>
                        <th>欠卡費</th>
                        <th>還卡費</th>
                        <th>掛號欠款</th>
                        <th>健保合計</th>
                        <th>民俗調理</th>
                        <th>現金總計</th>
                    </tr>
                    <tr>
                        <td align=right style="padding-right: 10px">{ins_regist_fee:,}</td>
                        <td align=right style="padding-right: 10px">{diag_share_fee:,}</td>
                        <td align=right style="padding-right: 10px">{drug_share_fee:,}</td>
                        <td align=right style="padding-right: 10px">{deposit_fee:,}</td>
                        <td align=right style="padding-right: 10px">{refund:,}</td>
                        <td align=right style="padding-right: 10px">{regist_debt:,}</td>
                        <td align=right style="padding-right: 10px">{ins_total:,}</td>
                        <td rowspan="3" style="text-align:center; vertical-align:middle">{massage_fee:,}</td>
                        <td rowspan="3" style="text-align:center; vertical-align:middle">{cash_total:,}</td>
                    </tr>
                    <tr{self.html_bg_color}>
                        <th rowspan="2" style="text-align: center; vertical-align: middle">自費</th>
                        <th>掛號費</th>
                        <th>自費金額</th>
                        <th>應收合計</th>
                        <th>欠款</th>
                        <th>實收合計</th>
                        <th>還款</th>
                        <th>自費合計</th>
                    </tr>
                    <tr>
                        <td align=right style="padding-right: 10px">{self_regist_fee:,}</td>
                        <td align=right style="padding-right: 10px">{self_total_fee:,}</td>
                        <td align=right style="padding-right: 10px">{total_fee:,}</td>
                        <td align=right style="padding-right: 10px">{debt:,}</td>
                        <td align=right style="padding-right: 10px">{receipt_total:,}</td>
                        <td align=right style="padding-right: 10px">{repayment:,}</td>
                        <td align=right style="padding-right: 10px">{self_total:,}</td>
                    </tr>
                </tbody>
            </table>
        '''

        return html

# 掛號櫃台結帳 2018.11.15
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (case_utils, class_utils, date_utils, nhi_utils, number_utils,
                  personnel_utils, string_utils, system_utils, ui_utils)


# 掛號櫃台結帳
class IncomeCashFlow(QtWidgets.QMainWindow):
    program_name = '掛號櫃台結帳'

    # 初始化
    def __init__(self, parent=None, *args):
        super(IncomeCashFlow, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.regist_type = args[5]
        self.doctor = args[6]
        self.room = args[7]
        self.cashier = args[8]
        self.income_source = args[9]
        self.calculate_by_cashier = args[10]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.problem_records = []

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_income(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INCOME_CASH_FLOW, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_registration = class_utils.get_table_widget(self.ui.tableWidget_registration, self.database)
        self.table_widget_registration.set_column_hidden([0])

        self.table_widget_charge = class_utils.get_table_widget(self.ui.tableWidget_charge, self.database)
        self.table_widget_charge.set_column_hidden([0])

        self.table_widget_total = class_utils.get_table_widget(self.ui.tableWidget_total, self.database)
        self.table_widget_payment_type = class_utils.get_table_widget(self.ui.tableWidget_payment_type, self.database)
        self._set_table_width()
        self._set_payment_type_table()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_registration.doubleClicked.connect(self.open_medical_record)
        self.ui.tableWidget_charge.doubleClicked.connect(self.open_medical_record)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100,
            160, 50, 75, 90, 50, 90, 100, 90, 80, 80, 80, 70, 70, 70, 70, 90, 100, 100, 60
        ]
        self.table_widget_registration.set_table_heading_width(width)

        width = [
            100,
            160, 50, 75, 90, 50, 90, 100, 90, 80, 50, 80, 80, 80, 80, 70, 90, 100, 100, 60
        ]
        self.table_widget_charge.set_table_heading_width(width)
        self.table_widget_total.set_table_heading_width([160, 100])
        self.table_widget_payment_type.set_table_heading_width([160, 100])

    def _set_payment_type_table(self):
        payment_type_list = nhi_utils.PAYMENT_TYPE + ['合計']
        self.ui.tableWidget_payment_type.setRowCount(len(payment_type_list))
        for row_no, payment_type in enumerate(payment_type_list):
            self.ui.tableWidget_payment_type.setItem(row_no, 0, QtWidgets.QTableWidgetItem(payment_type))
            self.ui.tableWidget_payment_type.setItem(row_no, 1, QtWidgets.QTableWidgetItem('0'))
            self.ui.tableWidget_payment_type.item(row_no, 1).setTextAlignment(
                QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            )

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, self.program_name, '進入病歷', self.user_name) != 'Y'):
            return

        sender_name = self.sender().objectName()

        if sender_name == 'tableWidget_registration':
            case_key = self.table_widget_registration.field_value(0)
        elif sender_name == 'tableWidget_charge':
            case_key = self.table_widget_charge.field_value(0)
        else:
            return

        if case_key == '':
            return

        self.parent.open_medical_record(case_key, '掛號櫃台結帳')

    # 開始統計現金交帳
    def read_data(self):
        self.problem_records = []
        self._read_registration_data()
        self._read_charge_data()
        self._calculate_total()
        self._calculate_payment_type()
        if len(self.problem_records) > 0:
            self._display_problem_info()

    # 讀取健保卡基本資料
    def _display_problem_info(self):
        problem_list = ''
        for item_no, item in enumerate(self.problem_records):
            sequence = item_no + 1
            name = item[0]
            total_fee = item[1]
            debt = item[2]
            receipt_fee = item[2]
            problem_list += f'''
                <tr>
                    <td align=center>{sequence}</td>
                    <td>{name}</td>
                    <td align="right">{total_fee}</td>
                    <td align="right">{debt}</td>
                    <td align="right">{receipt_fee}</td>
                </tr>
            '''

        html = f'''
            <table align=center cellpadding="2" cellspacing="0" width="98%"
             style="border-width: 1px; border-style: solid;">
                <thead>
                    <tr bgcolor="LightGray">
                        <th style="text-align: center; padding: 8px">序</th>
                        <th style="padding: 8px">病患姓名</th>
                        <th style="padding: 8px">應收金額</th>
                        <th style="padding: 8px">欠款</th>
                        <th style="padding: 8px">實收金額</th>
                    </tr>
                </thead>
                    {problem_list}
                <tbody>
                </tbody>
            </table>
        '''
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle('實收金額疑問')
        msg_box.setText(f'''
            <font color="red"><h3>應收與實收金額不平衡, 名單如下:</h3></font>
            {html}
        ''')
        msg_box.setInformativeText('實收金額有問題')
        msg_box.addButton(QPushButton("確定"), QMessageBox.AcceptRole)
        msg_box.exec_()

    # 計算掛號收費
    def _read_registration_data(self):
        self._set_registration_fees()
        self._set_refund_fees()
        self._set_repayment_fees()

        self._calculate_registration_total()

    def _set_registration_fees(self):
        sql = f'''
            SELECT cases.*, debt.Fee FROM cases
                LEFT JOIN debt ON debt.CaseKey = cases.CaseKey
            WHERE
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                (cases.InsType = "健保" OR RegistFee > 0 OR (DebtType = "掛號欠款" and debt.Fee > 0)) AND
                {case_utils.exclude_xx_card()}
        '''

        if self.period != '全部':
            if self.period == '早午班':
                sql += ' AND cases.Period IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += ' AND cases.Period IN("午班", "晚班") '
            else:
                sql += f' AND cases.Period = "{self.period}"'

        if self.doctor != '全部':
            sql += f' AND cases.Doctor = "{self.doctor}"'
        if self.room != '全部':
            sql += f' AND Room = {self.room}'
        if self.cashier != '全部':
            if self.calculate_by_cashier:
                sql += f' AND cases.Cashier = "{self.cashier}"'
            else:
                sql += f' AND cases.Register = "{self.cashier}"'

        else:
            if self.income_source == '櫃台':
                sql += ' AND Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Register = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' GROUP BY cases.CaseKey ORDER BY cases.CaseDate, FIELD(cases.Period, {period_list})'

        self.table_widget_registration.set_db_data(sql, self._set_registration_table_data)

    def _set_registration_table_data(self, row_no, row):
        case_key = number_utils.get_integer(row['CaseKey'])
        patient_key = string_utils.xstr(row['PatientKey'])

        regist_fee = number_utils.get_integer(row['RegistFee'])
        diag_share_fee = number_utils.get_integer(row['SDiagShareFee'])
        deposit_fee = number_utils.get_integer(row['DepositFee'])

        debt_fee = self._get_debt(case_key, '掛號欠款')

        discount_type = self._get_discount_type(patient_key, row['CaseDate'])
        subtotal = regist_fee + diag_share_fee + deposit_fee + debt_fee

        card = case_utils.get_full_card(row['Card'], row['Continuance'])
        payment_type = string_utils.xstr(row['RegistPaymentType'])
        regist_no = number_utils.get_integer(row['RegistNo'])

        medical_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].strftime('%Y-%m-%d %H:%M')),
            string_utils.xstr(row['Period']),
            patient_key,
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            discount_type,
            card,
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(deposit_fee),
            '0',
            string_utils.xstr(debt_fee),
            '0',  # 還款另外增加一筆
            string_utils.xstr(subtotal),
            string_utils.xstr(row['Register']),
            payment_type,
            regist_no,
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_registration.setItem(row_no, col_no, item)

            if col_no in [3, 10, 11, 12, 13, 14, 15, 16, 19]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            if string_utils.xstr(row['InsType']) == '自費':
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('blue')
                )

    def _set_refund_fees(self):
        sql = f'''
            SELECT
                deposit.*,
                cases.InsType, cases.Share, cases.Card, cases.TreatType,
                cases.Continuance, cases.RefundFee, cases.RegistPaymentType
            FROM deposit
                LEFT JOIN cases ON deposit.CaseKey = cases.CaseKey
            WHERE
                ReturnDate BETWEEN "{self.start_date}" AND "{self.end_date}"
        '''

        if self.period != '全部':
            if self.period == '早午班':
                sql += ' AND deposit.Period IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += ' AND deposit.Period IN("午班", "晚班") '
            else:
                sql += f' AND deposit.Period = "{self.period}"'

        if self.doctor != '全部':
            sql += f' AND cases.Doctor = "{self.doctor}"'

        if self.cashier != '全部':
            sql += f' AND Refunder = "{self.cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND Refunder != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Refunder = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' ORDER BY DepositDate, FIELD(deposit.Period, {period_list})'

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row_no = self.ui.tableWidget_registration.rowCount()
        for row in rows:
            if number_utils.get_integer(row['RefundFee']) == 0:  # 沒有還卡費就不要列出
                continue

            self._set_refund_table_data(row_no, row)
            row_no += 1

    def _registration_data_case_key_exist(self, in_case_key):
        for row_no in range(self.ui.tableWidget_registration.rowCount()):
            case_key_item = self.ui.tableWidget_registration.item(row_no, 0)
            if case_key_item is None:
                continue

            case_key = number_utils.get_integer(case_key_item.text())

            if in_case_key == case_key:
                return True

        return False

    def _set_refund_table_data(self, row_no, row):
        self.ui.tableWidget_registration.setRowCount(row_no+1)

        case_key = number_utils.get_integer(row['CaseKey'])
        patient_key = string_utils.xstr(row['PatientKey'])
        return_fee = -number_utils.get_integer(row['RefundFee'])
        subtotal = return_fee

        card = case_utils.get_full_card(row['Card'], row['Continuance'])
        discount_type = self._get_discount_type(patient_key, row['DepositDate'])
        payment_type = string_utils.xstr(row['RegistPaymentType'])

        medical_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['DepositDate'].strftime('%Y-%m-%d %H:%M')),
            string_utils.xstr(row['Period']),
            patient_key,
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            discount_type,
            card,
            '0',
            '0',
            '0',
            string_utils.xstr(return_fee),
            '0',
            '0',
            string_utils.xstr(subtotal),
            string_utils.xstr(row['Refunder']),
            payment_type,
        ]

        for col_no in range(len(medical_record)):
            self.ui.tableWidget_registration.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record[col_no])
            )
            if col_no in [3, 10, 11, 12, 13, 14, 15, 16]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if subtotal < 0:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('red')
                )

    def _set_repayment_fees(self):
        sql = f'''
            SELECT
                debt.*,
                cases.InsType, cases.Share, cases.Card, cases.TreatType, cases.Continuance,
                cases.RegistPaymentType
            FROM debt
                LEFT JOIN cases ON debt.CaseKey = cases.CaseKey
            WHERE
                (ReturnDate1 BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                 ReturnDate2 BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                 ReturnDate3 BETWEEN "{self.start_date}" AND "{self.end_date}")
        '''

        if self.period != '全部':
            if self.period == '早午班':
                sql += ' AND debt.Period1 IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += ' AND debt.Period1 IN("午班", "晚班") '
            else:
                sql += f''' AND
                    (
                      debt.Period1 = "{self.period}" OR
                      debt.Period2 = "{self.period}" OR
                      debt.Period3 = "{self.period}"
                    )
                '''

        if self.cashier != '全部':
            sql += f''' AND (debt.Cashier1 = "{self.cashier}" OR
                debt.Cashier2 = "{self.cashier}" OR
                debt.Cashier3 = "{self.cashier}")
            '''
        else:
            if self.income_source == '櫃台':
                sql += ' AND debt.Cashier1 != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND debt.Cashier1 = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f' ORDER BY debt.CaseDate, FIELD(debt.Period1, {period_list})'

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row_no = self.ui.tableWidget_registration.rowCount()
        for row in rows:
            self._set_repayment_table_data(row_no, row)
            row_no += 1

    def _set_repayment_table_data(self, row_no, row):
        self.ui.tableWidget_registration.setRowCount(row_no+1)
        case_key = number_utils.get_integer(row['CaseKey'])
        patient_key = string_utils.xstr(row['PatientKey'])
        payment_type = string_utils.xstr(row['PaymentType'])

        repayment = 0
        case_date = self.start_date[:10]
        period = self.period

        if row['ReturnDate1'] is not None:
            if case_date == string_utils.xstr(row['ReturnDate1'].strftime('%Y-%m-%d')):
                if period == '全部' or (period != '全部' and period == string_utils.xstr(row['Period1'])):
                    repayment += number_utils.get_integer(row['Fee1'])
        if row['ReturnDate2'] is not None:
            if case_date == string_utils.xstr(row['ReturnDate2'].strftime('%Y-%m-%d')):
                if period == '全部' or (period != '全部' and period == string_utils.xstr(row['Period2'])):
                    repayment += number_utils.get_integer(row['Fee2'])
        if row['ReturnDate3'] is not None:
            if case_date == string_utils.xstr(row['ReturnDate3'].strftime('%Y-%m-%d')):
                if period == '全部' or (period != '全部' and period == string_utils.xstr(row['Period3'])):
                    repayment += number_utils.get_integer(row['Fee3'])

        subtotal = repayment

        card = case_utils.get_full_card(row['Card'], row['Continuance'])
        discount_type = self._get_discount_type(patient_key, row['CaseDate'])

        medical_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].strftime('%Y-%m-%d %H:%M')),
            string_utils.xstr(row['Period']),
            patient_key,
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            discount_type,
            card,
            '0',
            '0',
            '0',
            '0',
            '0',
            string_utils.xstr(repayment),
            string_utils.xstr(subtotal),
            string_utils.xstr(row['Cashier1']),
            payment_type,
        ]

        for col_no in range(len(medical_record)):
            self.ui.tableWidget_registration.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record[col_no])
            )
            if col_no in [3, 10, 11, 12, 13, 14, 15, 16]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_registration.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _calculate_registration_total(self):
        row_count = self.ui.tableWidget_registration.rowCount()
        regist_fee, diag_share_fee, deposit_fee, refund_fee, debt_fee, repayment, subtotal = 0, 0, 0, 0, 0, 0, 0
        for row_no in range(row_count):
            regist_fee += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 10).text())
            diag_share_fee += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 11).text())
            deposit_fee += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 12).text())
            refund_fee += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 13).text())
            debt_fee += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 14).text())
            repayment += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 15).text())
            subtotal += number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 16).text())

        total_record = [
            None, None, None, None,
            '合計',
            None, None, None, None, None,
            string_utils.xstr(regist_fee),
            string_utils.xstr(diag_share_fee),
            string_utils.xstr(deposit_fee),
            string_utils.xstr(refund_fee),
            string_utils.xstr(debt_fee),
            string_utils.xstr(repayment),
            string_utils.xstr(subtotal),
        ]

        self.ui.tableWidget_registration.setRowCount(row_count+1)

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_registration.setItem(
                row_count, col_no,
                QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [10, 11, 12, 13, 14, 15, 16]:
                self.ui.tableWidget_registration.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_registration.item(row_count, col_no).setFont(font)

    # 計算批價收費
    def _read_charge_data(self):
        self._set_charge_fees()
        self._calculate_charge_total()

    def _set_charge_fees(self):
        if self.system_settings.field('櫃台結帳班別') == '掛號班別':
            date_field = 'CaseDate'
            period_field = 'Period'
        else:
            date_field = 'ChargeDate'
            period_field = 'ChargePeriod'

        charge_done_condition = 'AND ChargeDone = "True"'
        if self.system_settings.field('櫃台結帳列出未完診名單') == 'Y':
            date_field = 'CaseDate'
            period_field = 'Period'
            charge_done_condition = ''

        sql = f'''
            SELECT * FROM cases
            WHERE
                (cases.{date_field} BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                {case_utils.exclude_xx_card()} AND
                ((TreatType != "民俗調理") OR
                 (TreatType = "民俗調理" AND TotalFee > 0))
                {charge_done_condition}
        '''
        if self.period != '全部':
            if self.period == '早午班':
                sql += f' AND cases.{period_field} IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += f' AND cases.{period_field} IN("午班", "晚班") '
            else:
                sql += f' AND cases.{period_field} = "{self.period}"'

        if self.doctor != '全部':
            sql += f' AND cases.Doctor = "{self.doctor}"'
        if self.room != '全部':
            sql += f' AND Room = {self.room}'
        if self.cashier != '全部':
            if self.calculate_by_cashier:
                sql += f' AND cases.Cashier = "{self.cashier}"'
            else:
                sql += f' AND cases.Register = "{self.cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND cases.Cashier != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND cases.Cashier = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        # sql += f' ORDER BY cases.PatientKey, FIELD(cases.InsType, "健保", "自費"), cases.CaseDate, FIELD(cases.{period_field}, {period_list})'
        sql += f' ORDER BY cases.CaseDate, FIELD(cases.{period_field}, {period_list})'

        self.table_widget_charge.set_db_data(sql, self._set_charge_table_data)

    def _get_debt(self, case_key, debt_type):
        sql = f'''
            SELECT Fee FROM debt
            WHERE
                CaseKey = {case_key} AND
                DebtType = "{debt_type}"
        '''
        rows = self.database.select_record(sql)

        total_debt = 0

        for row in rows:
            total_debt += -number_utils.get_integer(row['Fee'])

        return total_debt

    def _get_repayment(self, case_key, debt_type):
        sql = f'''
            SELECT Fee1 FROM debt
            WHERE
                CaseKey = {case_key} AND
                DebtType = "{debt_type}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            repayment = 0
        else:
            repayment = number_utils.get_integer(rows[0]['Fee1'])

        return repayment

    def _set_charge_table_data(self, row_no, row):
        case_key = number_utils.get_integer(row['CaseKey'])
        patient_key = string_utils.xstr(row['PatientKey'])
        pres_days = case_utils.get_pres_days(self.database, case_key)

        drug_share_fee = number_utils.get_integer(row['SDrugShareFee'])
        debt_fee = self._get_debt(case_key, '批價欠款')

        receipt_fee = number_utils.get_integer(row['ReceiptFee'])
        total_fee = number_utils.get_integer(row['TotalFee'])
        receipt_subtotal = total_fee + drug_share_fee
        subtotal = receipt_subtotal + debt_fee

        name = string_utils.xstr(row['Name'])
        card = case_utils.get_full_card(row['Card'], row['Continuance'])
        discount_type = self._get_discount_type(patient_key, row['CaseDate'])
        payment_type = string_utils.xstr(row['ChargePaymentType'])
        regist_no = number_utils.get_integer(row['RegistNo'])

        medical_record = [
            string_utils.xstr(case_key),
            string_utils.xstr(row['CaseDate'].strftime('%Y-%m-%d %H:%M')),
            string_utils.xstr(row['Period']),
            patient_key,
            name,
            string_utils.xstr(row['InsType']),
            string_utils.xstr(row['Share']),
            string_utils.xstr(row['TreatType']),
            discount_type,
            card,
            string_utils.xstr(pres_days),
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(total_fee),
            string_utils.xstr(receipt_subtotal),
            string_utils.xstr(debt_fee),
            string_utils.xstr(subtotal),
            string_utils.xstr(row['Cashier']),
            payment_type,
            regist_no
        ]

        for col_no in range(len(medical_record)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, medical_record[col_no])
            self.ui.tableWidget_charge.setItem(row_no, col_no, item)

            if col_no in [3, 10, 12, 13, 14, 15, 16, 19]:
                self.ui.tableWidget_charge.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_charge.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if total_fee > 0:
                self.ui.tableWidget_charge.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('blue')
                )
            if string_utils.xstr(row['TreatType']) == '自購':
                self.ui.tableWidget_charge.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('darkgreen')
                )
            if total_fee + debt_fee != receipt_fee:
                self.ui.tableWidget_charge.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('red')
                )

        if debt_fee < 0:
            self.ui.tableWidget_charge.item(
                row_no, 15).setForeground(
                QtGui.QColor('red')
            )
        if drug_share_fee + total_fee + debt_fee != subtotal:
            self.problem_records.append(
                [name, total_fee, debt_fee, receipt_fee]
            )

    def _calculate_charge_total(self):
        row_count = self.ui.tableWidget_charge.rowCount()
        drug_share_fee, debt_fee, total_fee, receipt_fee, subtotal = 0, 0, 0, 0, 0
        for row_no in range(row_count):
            drug_share_fee += number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 12).text())
            total_fee += number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 13).text())
            receipt_fee += number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 14).text())
            debt_fee += number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 15).text())
            subtotal += number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 16).text())

        total_record = [
            None, None, None, None,
            '合計',
            None, None, None, None, None, None, None,
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(total_fee),
            string_utils.xstr(receipt_fee),
            string_utils.xstr(debt_fee),
            string_utils.xstr(subtotal),
        ]

        self.ui.tableWidget_charge.setRowCount(row_count+1)

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(total_record)):
            self.ui.tableWidget_charge.setItem(
                row_count, col_no,
                QtWidgets.QTableWidgetItem(total_record[col_no])
            )
            if col_no in [12, 13, 14, 15, 16]:
                self.ui.tableWidget_charge.item(
                    row_count, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_charge.item(row_count, col_no).setFont(font)

    def _calculate_total(self):
        self.ui.tableWidget_total.setRowCount(0)

        total_fee = (
                number_utils.get_integer(self.ui.tableWidget_registration.item(
                    self.ui.tableWidget_registration.rowCount()-1, 16).text()) +
                number_utils.get_integer(self.ui.tableWidget_charge.item(
                    self.ui.tableWidget_charge.rowCount()-1, 16).text())
        )

        total_rows = [
            ['掛號費', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 10).text()],
            ['門診負擔', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 11).text()],
            ['藥品負擔', self.ui.tableWidget_charge.item(self.ui.tableWidget_charge.rowCount()-1, 12).text()],
            ['欠卡費', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 12).text()],
            ['還卡費', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 13).text()],
            ['自費還款', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 15).text()],
            ['自費金額', self.ui.tableWidget_charge.item(self.ui.tableWidget_charge.rowCount()-1, 13).text()],
            ['批價收費', self.ui.tableWidget_charge.item(self.ui.tableWidget_charge.rowCount()-1, 14).text()],
            ['掛號欠款', self.ui.tableWidget_registration.item(self.ui.tableWidget_registration.rowCount()-1, 14).text()],
            ['批價欠款', self.ui.tableWidget_charge.item(self.ui.tableWidget_charge.rowCount()-1, 15).text()],
            ['實收現金', string_utils.xstr(total_fee)],
        ]

        for row_no, row in enumerate(total_rows):
            self.ui.tableWidget_total.setRowCount(row_no+1)
            for col_no in range(len(row)):
                self.ui.tableWidget_total.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(row[col_no]))
                )
                if col_no in [1]:
                    self.ui.tableWidget_total.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                if row_no in [4, 8, 9]:
                    self.ui.tableWidget_total.item(
                        row_no, col_no).setForeground(
                        QtGui.QColor('red')
                    )

    def _get_discount_type(self, patient_key, case_date):
        sql = f'''
            SELECT Birthday, DiscountType FROM patient
            WHERE
                PatientKey = {patient_key}
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        discount_type = string_utils.xstr(row['DiscountType'])
        if discount_type == '':
            age_year, _ = date_utils.get_age(row['Birthday'], case_date)
            old_man_age = number_utils.get_integer(self.system_settings.field('老人優待年齡'))
            if number_utils.get_integer(age_year) >= old_man_age:
                discount_type = '年長病患'

        return discount_type

    def _calculate_payment_type(self):
        for row_no in range(self.ui.tableWidget_registration.rowCount()):
            try:
                payment_type = self.ui.tableWidget_registration.item(row_no, 18).text()
            except Exception:
                continue

            total_fee = number_utils.get_integer(self.ui.tableWidget_registration.item(row_no, 16).text())
            self._set_payment_type(total_fee, payment_type)

        for row_no in range(self.ui.tableWidget_charge.rowCount()):
            try:
                payment_type = self.ui.tableWidget_charge.item(row_no, 18).text()
            except Exception:
                continue

            total_fee = number_utils.get_integer(self.ui.tableWidget_charge.item(row_no, 16).text())

            self._set_payment_type(total_fee, payment_type)

        for row_no in range(self.ui.tableWidget_payment_type.rowCount()-1):
            total_fee = number_utils.get_integer(self.ui.tableWidget_payment_type.item(row_no, 1).text())
            self._set_payment_type(total_fee, '合計')

    def _set_payment_type(self, total_fee, payment_type):
        row_no = self._get_payment_type_row_no(payment_type)
        if row_no is None:
            return

        item = self.ui.tableWidget_payment_type.item(row_no, 1)
        if item is None:
            payment_total = 0
        else:
            payment_total = int(item.text())

        payment_total += total_fee
        self.ui.tableWidget_payment_type.setItem(
            row_no, 1, QtWidgets.QTableWidgetItem(string_utils.xstr(payment_total)))
        self.ui.tableWidget_payment_type.item(row_no, 1).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _get_payment_type_row_no(self, payment_type):
        for row_no in range(self.ui.tableWidget_payment_type.rowCount()):
            item_name = self.ui.tableWidget_payment_type.item(row_no, 0).text()
            if payment_type == item_name:
                return row_no

        return None

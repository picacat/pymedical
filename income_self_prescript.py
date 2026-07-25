
# 掛號櫃台結帳 2018.11.15
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from libs import class_utils
from libs import ui_utils
from libs import personnel_utils
from libs import system_utils
from libs import export_utils
from libs import string_utils
from libs import nhi_utils
from libs import number_utils
from libs import case_utils
from libs import charge_utils


# 掛號櫃台結帳 - 收費一覽表
class IncomeSelfPrescript(QtWidgets.QMainWindow):
    program_name = '掛號櫃台結帳'

    # 初始化
    def __init__(self, parent=None, *args):
        super(IncomeSelfPrescript, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.regist_type = args[5]
        self.doctor = args[6]
        self.room = args[7]
        self.cashier = args[8]
        self.income_source = args[9]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()
        self._read_medical_record()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INCOME_SELF_PRESCRIPT, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_self_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_self_prescript, self.database
        )
        self.table_widget_self_prescript.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_self_prescript.doubleClicked.connect(self.open_medical_record)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100, 130, 50, 75, 90, 50, 90, 65,
            250, 50, 50, 50, 90, 90, 90, 90,
            300,
        ]
        self.table_widget_self_prescript.set_table_heading_width(width)

    def open_medical_record(self):
        if (self.user_name != '超級使用者' and
                personnel_utils.get_permission(self.database, self.program_name, '進入病歷', self.user_name) != 'Y'):
            return

        case_key = self.table_widget_self_prescript.field_value(0)
        if case_key is None:
            return

        self.parent.open_medical_record(case_key, '掛號櫃台結帳')

    def export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出自費銷售明細",
            f'{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}自費銷售明細表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_self_prescript, [0], [10, 12, 13]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>自費銷售明細表{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

    def _read_medical_record(self):
        sql = f'''
            SELECT cases.* FROM cases
                LEFT JOIN prescript ON prescript.CaseKey = cases.CaseKey
            WHERE
                (cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" OR
                 cases.ChargeDate BETWEEN "{self.start_date}" AND "{self.end_date}") AND
                (prescript.MedicineSet >= 2) AND
                {case_utils.exclude_xx_card()}
        '''
        if self.period != '全部':
            if self.period == '早午班':
                sql += ' AND cases.ChargePeriod IN("早班", "午班") '
            elif self.period == '午晚班':
                sql += ' AND cases.ChargePeriod IN("午班", "晚班") '
            else:
                sql += f' AND cases.ChargePeriod = "{self.period}"'

        if self.doctor != '全部':
            sql += f' AND cases.Doctor = "{self.doctor}"'
        if self.room != '全部':
            sql += f' AND Room = {self.room}'
        if self.cashier != '全部':
            sql += f' AND Register = "{self.cashier}"'
        else:
            if self.income_source == '櫃台':
                sql += ' AND Register != "掛號機"'
            elif self.income_source == '掛號機':
                sql += ' AND Register = "掛號機"'

        if self.regist_type != '全部':
            sql += case_utils.get_regist_type_sql(self.regist_type)

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql += f'''
            GROUP BY cases.CaseKey
            ORDER BY cases.CaseDate, FIELD(cases.Period, {period_list})
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        self._set_medical_record(rows)

    def _set_medical_record(self, rows):
        row_no = 0

        total_fee = 0
        for row in rows:
            self.ui.tableWidget_self_prescript.setRowCount(
                self.ui.tableWidget_self_prescript.rowCount() + 1
            )
            case_key = string_utils.xstr(row['CaseKey'])
            case_total_fee = number_utils.get_integer(
                self._set_medical_record_data(case_key, row_no, row)
            )
            row_no += 1
            prescript_row_count, prescript_total_fee = self._read_self_prescript(case_key, row_no)
            row_no += prescript_row_count
            if case_total_fee != prescript_total_fee and self.system_settings.field('手動批價') != 'Y':
                remark = '金額不平衡'
            else:
                remark = None

            if prescript_total_fee > 0:
                self._add_prescript_total(case_key, row_no, number_utils.round_up(prescript_total_fee), '合計', remark)
                row_no += 1

            # total_fee += prescript_total_fee
            total_fee += case_total_fee

        self._add_prescript_total(None, row_no, round(total_fee), '總計')

    def _set_medical_record_data(self, case_key, row_no, row):
        ins_type = string_utils.xstr(row['InsType'])
        if string_utils.xstr(row['TreatType']) == '自購':
            ins_type = '自購'

        self_total_fee = f"{number_utils.get_integer(row['SelfTotalFee']):,}"
        total_fee = f"{number_utils.get_integer(row['TotalFee']):,}"

        medical_record = [
            case_key,
            string_utils.xstr(row['CaseDate'].date()),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['PatientKey']),
            string_utils.xstr(row['Name']),
            ins_type,
            self_total_fee,
            None, None, None, None,
            '折扣',
            string_utils.xstr(row['DiscountFee']),
            total_fee,
            string_utils.xstr(row['Doctor']),
            string_utils.xstr(row['Cashier']),
        ]

        for col_no in range(len(medical_record)):
            if medical_record[col_no] is None:
                continue

            self.ui.tableWidget_self_prescript.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(medical_record[col_no])
            )
            if col_no in [3, 6, 12, 13]:
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2, 5]:
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
            if self.ui.tableWidget_self_prescript.item(row_no, col_no) is None:
                continue

            if ins_type == '自費':
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('blue')
                )
            elif ins_type == '自購':
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setForeground(
                    QtGui.QColor('green')
                )

        return total_fee.replace(',', '')

    def _read_self_prescript(self, case_key, row_no):
        sql = f'''
            SELECT MedicineSet FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet >= 2 AND
                MedicineSet != 11
            GROUP BY MedicineSet ORDER BY MedicineSet
        '''
        rows = self.database.select_record(sql)

        total_prescript_row_count = 0
        total_fee = 0
        for row in rows:
            prescript_row_count, subtotal = self._read_self_prescript_by_medicine_set(
                case_key, row['MedicineSet'], row_no
            )
            row_no += prescript_row_count
            total_fee += subtotal
            total_prescript_row_count += prescript_row_count

        return number_utils.round_up(total_prescript_row_count), number_utils.round_up(total_fee)

    def _read_self_prescript_by_medicine_set(self, case_key, medicine_set, row_no):
        sql = f'''
            SELECT * FROM prescript
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set}
            ORDER BY MedicineSet, PrescriptNo, PrescriptKey
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows)
        if row_count <= 0:
            return 0

        self.ui.tableWidget_self_prescript.setRowCount(
            self.ui.tableWidget_self_prescript.rowCount() + row_count
        )
        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
        discount_rate = case_utils.get_discount_rate(self.database, case_key, medicine_set)
        discount_fee = number_utils.get_integer(
            case_utils.get_discount_fee(self.database, case_key, medicine_set)
        )
        if pres_days <= 0:
            pres_days = 1

        total_fee = 0
        for row in rows:
            medicine_set = number_utils.get_integer(row['MedicineSet'])
            price = number_utils.get_float(row['Price'])
            amount = number_utils.get_float(row['Amount'])
            subtotal = charge_utils.get_subtotal_fee(amount, pres_days)
            total_fee += subtotal

            prescript_record = [
                case_key,
                None, None, None, None, None, None,
                f'自費{medicine_set-1}',
                string_utils.xstr(row['MedicineName']),
                pres_days,
                string_utils.xstr(number_utils.get_float(row['Dosage'])),
                string_utils.xstr(row['Unit']),
                f'{price:,}',
                f'{subtotal:,}',
            ]

            for col_no in range(len(prescript_record)):
                if prescript_record[col_no] is None:
                    continue

                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, prescript_record[col_no])
                self.ui.tableWidget_self_prescript.setItem(row_no, col_no, item)

                if col_no in [9, 10, 12, 13]:
                    self.ui.tableWidget_self_prescript.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                    )
                elif col_no in [7, 11]:
                    self.ui.tableWidget_self_prescript.item(
                        row_no, col_no).setTextAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                    )

                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setBackground(
                    QtGui.QColor('lightGray')
                )
            row_no += 1

        if discount_fee > 0:
            self._add_discount(case_key, medicine_set, row_no, discount_rate, -discount_fee)
            row_no += 1
            row_count += 1

        total_fee -= discount_fee
        self._add_prescript_total(case_key, row_no, number_utils.round_up(total_fee), '小計')
        row_no += 1
        row_count += 1

        return row_count, total_fee

    def _add_prescript_total(self, case_key, row_no, total_fee, label, remark=None):
        self.ui.tableWidget_self_prescript.setRowCount(
            self.ui.tableWidget_self_prescript.rowCount() + 1
        )
        if label == '總計':
            filler = ''
            remark = ''
            item_name = '當日自費銷售總額'
        else:
            filler = None
            item_name = ''
        prescript_record = [
            case_key,
            filler, filler, filler, filler, filler, filler,
            '',
            item_name, '', '',
            label,
            '',
            f'{total_fee:,}',
            filler, filler,
            remark
        ]

        font = QtGui.QFont()
        font.setBold(True)
        for col_no in range(len(prescript_record)):
            if prescript_record[col_no] is None:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, prescript_record[col_no])
            self.ui.tableWidget_self_prescript.setItem(row_no, col_no, item)

            if col_no in [13]:
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            self.ui.tableWidget_self_prescript.item(row_no, col_no).setFont(font)

            color = 'lightGray'
            if label == '總計':
                color = 'gray'

            self.ui.tableWidget_self_prescript.item(
                row_no, col_no).setBackground(
                QtGui.QColor(color)
            )

    def _add_discount(self, case_key, medicine_set, row_no, discount_rate, discount_fee):
        self.ui.tableWidget_self_prescript.setRowCount(
            self.ui.tableWidget_self_prescript.rowCount() + 1
        )
        prescript_record = [
            case_key,
            None, None, None, None, None, None,
            f'自費{medicine_set-1}',
            '優待',
            '',
            string_utils.xstr(discount_rate),
            '%',
            '',
            f'{discount_fee:,}',
        ]

        for col_no in range(len(prescript_record)):
            if prescript_record[col_no] is None:
                continue

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, prescript_record[col_no])
            self.ui.tableWidget_self_prescript.setItem(row_no, col_no, item)

            if col_no in [10, 13]:
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [7, 11]:
                self.ui.tableWidget_self_prescript.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            self.ui.tableWidget_self_prescript.item(
                row_no, col_no).setForeground(
                QtGui.QColor('red')
            )
            self.ui.tableWidget_self_prescript.item(
                row_no, col_no).setBackground(
                QtGui.QColor('lightGray')
            )

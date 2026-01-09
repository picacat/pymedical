# -*- coding: UTF-8 -*-

import dis
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import case_utils
from libs import charge_utils
from libs import nhi_utils


# 醫師金額收入統計 2023.07.08
class StatisticsDoctorAmountSalary(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorAmountSalary, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.ins_type = args[5]
        self.doctor = args[6]
        self.option = args[7]
        self.weekday_list = args[8]
        self.ui = None

        apply_year = int(self.start_date[:4])
        apply_month = int(self.start_date[5:7])

        self.apply_date = f'{apply_year-1911:0>3}{apply_month:0>2}'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_AMOUNT_SALARY, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor = class_utils.get_table_widget(self.ui.tableWidget_doctor, self.database)
        self._set_table_width()

    def _set_table_width(self):
        width = [
            120,
            80, 80, 80, 70, 70, 90, 90, 90, 90,
            90, 90, 90, 90, 80, 90, 90, 80, 80,
        ]
        self.table_widget_doctor.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_doctor_excel.clicked.connect(self._export_to_doctor_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_doctor.setRowCount(0)
        self._set_statistics_doctor_table_heading()
        self._calculate_data()

    @staticmethod
    def _get_doctor(doctor, treat_type):
        if doctor in ['', None]:
            if treat_type == '自購':
                doctor = treat_type
            else:
                doctor = '空白'

        return doctor

    def _set_statistics_doctor_table_heading(self):
        doctor_list = []
        rows = self._read_data(group_by_doctor=True)

        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row['Doctor']),
                string_utils.xstr(row['TreatType']),
            )
            if doctor in ['自購', '空白']:
                continue

            if doctor not in doctor_list:
                doctor_list.append(doctor)

        row_count = len(doctor_list)
        # self.ui.tableWidget_doctor.setRowCount(row_count + 1)
        self.ui.tableWidget_doctor.setRowCount(row_count)

        for row_no, doctor in enumerate(doctor_list):
            self.ui.tableWidget_doctor.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(doctor)
            )

        # self.ui.tableWidget_doctor.setItem(
        #     row_count, 0, QtWidgets.QTableWidgetItem('總計')
        # )

    def _calculate_data(self):
        self._reset_data()
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        self.progress_dialog = QtWidgets.QProgressDialog(
            '門診收入統計中, 請稍後...', '取消', 0, row_count, self
        )

        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        self.progress_dialog.setValue(0)
        self._calculate_doctor_period(rows)
        self._get_period_fee()
        self._get_diag_fee()
        self._get_treat_fee()
        self._get_self_fee()
        self._calculate_salary()

        self.progress_dialog.setValue(row_count)
        self.progress_dialog.deleteLater()

    def _reset_data(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            for col_no in range(1, self.ui.tableWidget_doctor.columnCount()):
                self.ui.tableWidget_doctor.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem('0')
                )
                self.ui.tableWidget_doctor.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _read_data(self, group_by_doctor=False):
        period_condition = ''
        if self.period != '全部':
            period_condition = ' AND Period = "{0}"'.format(self.period)

        ins_type_condition = ''
        if self.ins_type != '全部':
            ins_type_condition = ' AND InsType = "{0}"'.format(self.ins_type)

        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = ' AND Doctor = "{0}"'.format(self.doctor)

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        group_condition = ''
        if group_by_doctor:
            group_condition = ' GROUP BY Doctor, TreatType'

        sql = f'''
            SELECT
                CaseKey, Name, CaseDate, Period, TreatType, Doctor,
                RegistFee, SDiagShareFee, SDrugShareFee, DepositFee,
                SDiagFee, SDrugFee, SHerbFee, SExpensiveFee,
                SAcupunctureFee, SMassageFee, SDislocateFee,
                SMaterialFee, SelfTotalFee, DiscountFee, TotalFee, ReceiptFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            {group_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _calculate_doctor_period(self, rows):
        total_period_count = {}
        day_list = []

        for row in rows:
            doctor = self._get_doctor(
                string_utils.xstr(row['Doctor']),
                string_utils.xstr(row['TreatType']),
            )
            if doctor in ['自購', '空白']:
                continue

            row_no = self._get_doctor_row_no(doctor)
            case_date = row['CaseDate'].date().strftime('%Y-%m-%d')
            period = string_utils.xstr(row['Period'])
            period_index = f'{case_date}{period}{doctor}'
            if period_index not in day_list:
                day_list.append(period_index)
                try:
                    total_period_count[doctor] += 1
                except Exception:
                    total_period_count[doctor] = 1

            self._set_doctor_item_data(row_no, 1, string_utils.xstr(total_period_count[doctor]))

    def _get_period_fee(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                continue

            doctor = doctor.text()
            if doctor == '總計':
                continue

            period_count = self.ui.tableWidget_doctor.item(row_no, 1).text()
            period_count = number_utils.get_integer(period_count)
            period_fee = charge_utils.get_doctor_period_fee(self.database, doctor)
            self._set_doctor_item_data(row_no, 2, string_utils.xstr(period_fee))
            self._set_doctor_item_data(row_no, 3, string_utils.xstr(period_count * period_fee), bold=True)

    def _get_ins_apply_diag_fee(self, rows, doctor):
        diag_fee_dict = {
            'A02': charge_utils.get_ins_fee_from_ins_code(self.database, 'A02'),
            'A04': charge_utils.get_ins_fee_from_ins_code(self.database, 'A04'),
            'A06': charge_utils.get_ins_fee_from_ins_code(self.database, 'A06'),
        }
        total_diag_fee = 0
        for row in rows:
            doctor_name = string_utils.xstr(row['DoctorName'])
            if doctor_name != doctor:
                continue

            diag_code = string_utils.xstr(row['DiagCode'])
            if diag_code == 'A01':
                diag_code = 'A02'
            elif diag_code == 'A03':
                diag_code = 'A04'
            elif diag_code == 'A05':
                diag_code = 'A06'

            diag_fee = diag_fee_dict[diag_code]
            total_diag_fee += diag_fee

        return total_diag_fee

    def _get_ins_apply_treat_fee(self, rows, doctor):
        total_treat_fee = 0
        for row in rows:
            for i in range(1, nhi_utils.MAX_COURSE+1):
                case_key = number_utils.get_integer(row[f'CaseKey{i}'])
                if case_key == 0:
                    continue

                case_doctor = case_utils.get_case_field_value(self.database, case_key, 'Doctor')
                if case_doctor != doctor:
                    continue

                treat_fee = number_utils.get_integer(row[f'TreatFee{i}'])
                total_treat_fee += treat_fee

        return total_treat_fee

    def _get_diag_fee(self):
        diag_percent = self.system_settings.field('診察費抽成率')
        sql = f'''
            SELECT DoctorName, DiagCode FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                DiagCode IS NOT NULL
        '''
        rows = self.database.select_record(sql)

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                continue

            doctor = doctor.text()
            if doctor == '總計':
                continue

            total_diag_fee = self._get_ins_apply_diag_fee(rows, doctor)
            self._set_doctor_item_data(row_no, 4, string_utils.xstr(total_diag_fee))
            self._set_doctor_item_data(row_no, 5, string_utils.xstr(diag_percent + '%'))

            diag_commission = total_diag_fee * int(diag_percent) / 100
            diag_commission = number_utils.get_integer(diag_commission)
            self._set_doctor_item_data(row_no, 6, string_utils.xstr(diag_commission), bold=True)

    def _get_treat_fee(self):
        treat_percent = self.system_settings.field('診療費抽成率')
        sql = f'''
            SELECT * FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                TreatFee > 0
        '''
        rows = self.database.select_record(sql)

        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                continue

            doctor = doctor.text()
            if doctor == '總計':
                continue

            total_treat_fee = self._get_ins_apply_treat_fee(rows, doctor)
            self._set_doctor_item_data(row_no, 7, string_utils.xstr(total_treat_fee))
            self._set_doctor_item_data(row_no, 8, string_utils.xstr(treat_percent + '%'))

            treat_commission = total_treat_fee * int(treat_percent) / 100
            treat_commission = number_utils.get_integer(treat_commission)
            self._set_doctor_item_data(row_no, 9, string_utils.xstr(treat_commission), bold=True)

    def _read_self_data(self, doctor):
        discount_case_key = []
        self.min_discount_rate = charge_utils.get_min_discount_rate(self.database)
        self.ignore_discount = charge_utils.ignore_discount(self.database)

        period_condition = ''
        if self.period != '全部':
            period_condition = f' AND Period = "{self.period}"'

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(cases.CaseDate) IN({",".join(self.weekday_list)})'

        doctor_condition = f'''
            AND (cases.Doctor = "{doctor}")
        '''

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        sql = f'''
            SELECT
                prescript.*,
                cases.CaseKey, cases.PatientKey, cases.Name, cases.CaseDate, cases.Doctor, cases.Register,
                cases.InsType, cases.TreatType, cases.DiscountFee
            FROM
                prescript
            LEFT JOIN cases
                ON prescript.CaseKey = cases.CaseKey
            WHERE
                prescript.MedicineSet >= 2 AND
                Dosage > 0 AND
                cases.CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
                {period_condition}
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY cases.CaseKey, prescript.PrescriptKey
        '''
        rows = self.database.select_record(sql)

        total_amount, total_commission = 0, 0
        total_discount = 0
        for row in rows:
            case_key = row['CaseKey']
            medicine_key = row['MedicineKey']
            medicine_set = row['MedicineSet']

            pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
            if pres_days == 0:
                pres_days = 1

            quantity = number_utils.get_float(row['Dosage'])
            amount = number_utils.round_up(
                charge_utils.get_subtotal_fee(number_utils.get_float(row['Amount']), pres_days))

            medicine_name = string_utils.xstr(row['MedicineName'])
            if medicine_name in ['自費粉藥', '自費水藥']:
                commission_rate = charge_utils.get_commission_rate(
                    self.database, medicine_key, doctor, treat_type=medicine_name, only_doctor=False)
            else:
                commission_rate = charge_utils.get_commission_rate(
                    self.database, medicine_key, doctor, only_doctor=False)

            discount_fee = number_utils.get_integer(row['DiscountFee'])
            if case_key not in discount_case_key:
                discount_case_key.append(case_key)
                total_discount += discount_fee

            discount_rate = case_utils.calculate_discount_rate(self.database, case_key)        
            if discount_fee > 0 and discount_rate <= self.min_discount_rate:
                commission_rate = ''

            commission = charge_utils.calc_commission(quantity, amount, commission_rate)
            commission = number_utils.round_up(commission)

            total_amount += amount
            total_commission += commission

        return total_amount-total_discount, total_commission

    def _get_self_fee(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                continue

            doctor = doctor.text()
            if doctor == '總計':
                continue

            total_amount, total_commission = self._read_self_data(doctor)
            self._set_doctor_item_data(row_no, 10, string_utils.xstr(total_amount))
            self._set_doctor_item_data(row_no, 11, string_utils.xstr(total_commission), bold=True)

    def _calculate_salary(self):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor is None:
                continue

            doctor = doctor.text()
            if doctor == '總計':
                continue
            
            period_fee = self._get_doctor_cell_fee(row_no, 3)
            diag_fee = self._get_doctor_cell_fee(row_no, 6)
            treat_fee = self._get_doctor_cell_fee(row_no, 9)
            self_fee = self._get_doctor_cell_fee(row_no, 11)
            salary = period_fee + diag_fee + treat_fee + self_fee

            self._set_doctor_item_data(row_no, 12, string_utils.xstr(salary), bold=True)

    def _get_doctor_row_no(self, doctor):
        for row_no in range(self.ui.tableWidget_doctor.rowCount()):
            doctor_field = self.ui.tableWidget_doctor.item(row_no, 0)
            if doctor_field is None:
                doctor = '空白'

            if doctor == doctor_field.text():
                return row_no

        return None

    def _get_doctor_cell_fee(self, row_no, col_no):
        cell = self.ui.tableWidget_doctor.item(row_no, col_no)

        if cell is None:
            cell_fee = 0
        else:
            cell_fee = number_utils.get_integer(cell.text())

        return cell_fee

    def _set_doctor_item_data(self, row_no, col_no, data, bold=False):
        self.ui.tableWidget_doctor.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(data)
        )
        self.ui.tableWidget_doctor.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )
        if bold:
            font = QtGui.QFont()
            font.setBold(True)
            self.ui.tableWidget_doctor.item(row_no, col_no).setFont(font)

        if col_no > 0 and number_utils.get_integer(data) < 0:
            self.ui.tableWidget_doctor.item(row_no, col_no).setForeground(
                QtGui.QColor('red')
            )

    def _export_to_doctor_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}醫師薪資統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor,
            title=f'{self.system_settings.field("院所名稱")} 醫師薪資統計表',
            numeric_cell=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            calc_total=False
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            '<h3>醫師薪資統計表{0}匯出完成.</h3>'.format(excel_file_name),
            'Microsoft Excel 格式.'
        )

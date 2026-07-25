# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore

import datetime
from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import personnel_utils
from libs import number_utils
from libs import nhi_utils
from libs import date_utils


# 健保指標 2020.09.25
class InsApplyIndicator(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(InsApplyIndicator, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_date = args[2]
        self.apply_period = args[3]
        self.apply_type_code = args[4]
        self.clinic_id = args[5]
        self.ui = None

        self.indicator_item_list = [
            '每位醫師申請點數',
            '用藥日數重複率',
            '重複就診率',
            '隔日申報診察費率',
            '平均就醫次數',
            f'申請診察費次數>={nhi_utils.MAX_DIAG+1}次以上病患',
            '29案件每位醫師平均每件申請點數',
            f'22, 24, 29案件當月就醫針灸、傷科次數>{nhi_utils.MAX_TREAT}次',
            '慢性病案件平均每件給藥日份',
            '中醫職災申報率',
            '當月院所週日開診天數',
            '慢性病案件申報件數佔率',
        ]
        self._set_ui()
        self._set_signal()
        self._check_ins_indicator()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_INS_APPLY_INDICATOR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_indicator = class_utils.get_table_widget(
            self.ui.tableWidget_indicator, self.database)
        self.table_widget_incorrect = class_utils.get_table_widget(
            self.ui.tableWidget_incorrect, self.database)

        self._set_table_width()

    def _set_table_width(self):
        width = [420, 100, 100, 160]
        self.table_widget_indicator.set_table_heading_width(width)
        width = [380, 100, 100, 100, 100]
        self.table_widget_incorrect.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        pass

    def _set_indicator_table(self):
        self.ui.tableWidget_indicator.setRowCount(0)
        for item_name in self.indicator_item_list:
            self._insert_indicator_item(item_name)

    def _insert_incorrect_row(self, ins_apply_row, item_no):
        self.ui.tableWidget_incorrect.setRowCount(self.ui.tableWidget_incorrect.rowCount()+1)
        row_no = self.ui.tableWidget_incorrect.rowCount() - 1
        row = [
            self.indicator_item_list[item_no],
            ins_apply_row['CaseType'],
            ins_apply_row['Sequence'],
            ins_apply_row['PatientKey'],
            ins_apply_row['Name'],
        ]

        for col_no in range(len(row)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, row[col_no])
            self.ui.tableWidget_incorrect.setItem(row_no, col_no, item)
            if col_no in [1, 2, 3]:
                self.ui.tableWidget_incorrect.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _insert_indicator_item(self, item_name):
        self.ui.tableWidget_indicator.setRowCount(self.ui.tableWidget_indicator.rowCount()+1)
        row_no = self.ui.tableWidget_indicator.rowCount() - 1

        self.ui.tableWidget_indicator.setItem(
            row_no, 0,
            QtWidgets.QTableWidgetItem(item_name)
        )

    def _set_table_widget_indicator_items(self, row_no, value1, value2, value3, show_number=True, show_percent=True):
        if value1 is not None:
            self.ui.tableWidget_indicator.setItem(
                row_no, 1,
                QtWidgets.QTableWidgetItem(f'{value1}')
            )
        if value2 is not None:
            self.ui.tableWidget_indicator.setItem(
                row_no, 2,
                QtWidgets.QTableWidgetItem(f'{value2}')
            )

        if value1 is None and value2 is None:
            result = f'{value3}'
        else:
            if show_percent:
                percent_sign = '%'
            else:
                percent_sign = ''

            if show_number:
                result = f'{value3:.2f}{percent_sign}'
            else:
                result = f'{value3}'

        self.ui.tableWidget_indicator.setItem(
            row_no, 3,
            QtWidgets.QTableWidgetItem(result)
        )
        for col_no in [1, 2, 3]:
            try:
                self.ui.tableWidget_indicator.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            except AttributeError:
                pass

    def _check_ins_indicator(self):
        self.ui.tableWidget_incorrect.setRowCount(0)
        self._set_indicator_table()

        self._calculate_doctor_apply_fee(0)
        self._calculate_duplicate_pres_days(1)
        self._calculate_duplicate_days(2)
        self._calculate_next_day_diag_fee(3)
        self._calculate_avg_case_count(4)
        self._calculate_diag_fee_count(5)
        self._calculate_case_type_29_apply_fee(6)
        self._calculate_treat_count(7)
        self._calculate_case_type_24_avg_pres_days(8)
        self._calculate_case_type_B6_rate(9)
        self._calculate_sunday_count(10)
        self._calculate_case_type_24_rate(11)

        self.ui.tableWidget_indicator.resizeRowsToContents()
        self.ui.tableWidget_incorrect.resizeRowsToContents()

    # 每位醫師申請點數
    def _calculate_doctor_apply_fee(self, row_no):
        sql = f'''
            SELECT SUM(InsApplyFee) AS ApplyFee, DoctorID FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}"
            GROUP BY DoctorID
            ORDER BY SUM(InsApplyFee) DESC
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0)
            return

        doctor_list = []
        for row in rows:
            doctor_name = personnel_utils.person_id_to_name(self.database, string_utils.xstr(row['DoctorID']))
            doctor_list.append(f'{doctor_name}: {row["ApplyFee"]}')

        self._set_table_widget_indicator_items(
            row_no, None, None, '\n'.join(doctor_list),
            show_number=False,
            show_percent=False
        )

    # 用藥重複率
    def _calculate_duplicate_pres_days(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name, PresDays FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType NOT IN ("24", "26", "27", "28", "29", "B6", "C5") AND
                PresDays > 0
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        last_case_date = rows[0]['CaseDate']
        last_pres_days = number_utils.get_integer(rows[0]['PresDays'])

        total_pres_days = 0
        duplicate_days = 0

        include_today = self.system_settings.field('當日用藥重複檢查')
        last_patient_key = 0
        for row in rows:
            total_pres_days += number_utils.get_integer(row['PresDays'])
            if row['PatientKey'] == last_patient_key:
                days = (last_case_date + datetime.timedelta(days=last_pres_days-1) - row['CaseDate']).days - 1  # 最後一天不算
                if include_today == 'Y':
                    days -= 1
                if days > 0:
                    duplicate_days += days
                    self._insert_incorrect_row(row, row_no)

            last_patient_key = row['PatientKey']
            last_case_date = row['CaseDate']
            last_pres_days = number_utils.get_integer(row['PresDays'])

        duplicate_rate = duplicate_days / total_pres_days * 100
        self._set_table_widget_indicator_items(row_no, duplicate_days, total_pres_days, duplicate_rate)

    # 重複就診率
    def _calculate_duplicate_days(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        duplicate_days = 0
        total_person = 0

        last_patient_key = 0
        last_case_date = rows[0]['CaseDate']
        for row in rows:
            if row['PatientKey'] == last_patient_key:
                if last_case_date == row['CaseDate']:
                    duplicate_days += 1
                    self._insert_incorrect_row(row, row_no)
            else:
                total_person += 1

            last_patient_key = row['PatientKey']
            last_case_date = row['CaseDate']

        duplicate_rate = duplicate_days / total_person * 100
        self._set_table_widget_indicator_items(row_no, duplicate_days, total_person, duplicate_rate)

    # 隔日申報診察費率
    def _calculate_next_day_diag_fee(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0)
            return

        next_days = 0
        total_case_count = 0

        last_patient_key = 0
        last_case_date = rows[0]['CaseDate']
        for row in rows:
            total_case_count += 1
            if row['PatientKey'] == last_patient_key:
                if (row['CaseDate'] - last_case_date).days == 1:
                    next_days += 1
                    self._insert_incorrect_row(row, row_no)

            last_patient_key = row['PatientKey']
            last_case_date = row['CaseDate']

        rate = next_days / total_case_count * 100
        self._set_table_widget_indicator_items(row_no, next_days, total_case_count, rate)

    # 平均就醫次數
    def _calculate_avg_case_count(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        person_count = 0
        total_case_count = 0

        last_patient_key = 0
        for row in rows:
            total_case_count += 1
            if row['PatientKey'] == last_patient_key:
                pass
            else:
                person_count += 1

            last_patient_key = row['PatientKey']

        avg_count = total_case_count / person_count
        self._set_table_widget_indicator_items(
            row_no, total_case_count, person_count, avg_count,
            show_percent=False,
        )

    # 診察費>=7次以上
    def _calculate_diag_fee_count(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0)
            return

        error_count = 0
        diag_count = 0

        last_patient_key = 0
        for row in rows:
            if row['PatientKey'] == last_patient_key:
                diag_count += 1
            else:
                diag_count = 0

            if diag_count > nhi_utils.MAX_DIAG:
                error_count += 1
                self._insert_incorrect_row(row, row_no)

            last_patient_key = row['PatientKey']

        self._set_table_widget_indicator_items(row_no, None, None, error_count, show_percent=False)

    # 29案件每位醫師申請點數
    def _calculate_case_type_29_apply_fee(self, row_no):
        sql = f'''
            SELECT SUM(InsApplyFee) AS ApplyFee, COUNT(InsApplyFee) AS RowCount, DoctorID FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "29"
            GROUP BY DoctorID
            ORDER BY SUM(InsApplyFee)/COUNT(InsApplyFee) DESC
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0, show_percent=False)
            return

        numerator_list = []
        denominator_list = []
        doctor_list = []
        for row in rows:
            doctor_name = personnel_utils.person_id_to_name(self.database, string_utils.xstr(row['DoctorID']))
            numerator_list.append(f'{row["ApplyFee"]}')
            denominator_list.append(f'{row["RowCount"]}')
            doctor_list.append(f'{doctor_name}: {int(row["ApplyFee"]/row["RowCount"])}')

        self._set_table_widget_indicator_items(
            row_no,
            '\n'.join(numerator_list),
            '\n'.join(denominator_list),
            '\n'.join(doctor_list),
            show_number=False,
            show_percent=False
        )

    # 29案件每位醫師申請點數
    def _calculate_treat_count(self, row_no):
        sql = f'''
            SELECT CaseType, Sequence, CaseDate, PatientKey, Name,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("22", "24", "29")
            ORDER BY PatientKey, CaseDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0, show_percent=False)
            return

        error_count = 0
        treat_count = 0

        last_patient_key = 0
        for row in rows:
            if row['PatientKey'] == last_patient_key:
                pass
            else:
                treat_count = 0

            for i in range(1, 7):
                treat_code = string_utils.xstr(row[f'TreatCode{i}'])
                if treat_code in nhi_utils.TREAT_ALL_CODE:
                    treat_count += 1

            if treat_count > nhi_utils.MAX_TREAT:
                error_count += 1
                treat_count = 0
                self._insert_incorrect_row(row, row_no)

            last_patient_key = row['PatientKey']

        self._set_table_widget_indicator_items(row_no, None, None, error_count, show_percent=False)

    # 慢性病平均給藥日份
    def _calculate_case_type_24_avg_pres_days(self, row_no):
        sql = f'''
            SELECT COUNT(PresDays) AS CaseCount, SUM(PresDays) AS TotalPresDays FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "24" AND
                DrugFee > 0
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0 or number_utils.get_integer(rows[0]['TotalPresDays']) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        row = rows[0]
        total_pres_days = number_utils.get_integer(row['TotalPresDays'])
        total_case_count = number_utils.get_integer(row['CaseCount'])
        avg_count = total_pres_days / total_case_count

        self._set_table_widget_indicator_items(
            row_no, total_pres_days, total_case_count,
            avg_count,
            show_percent=False,
        )

    # 職災申報率
    def _calculate_case_type_B6_rate(self, row_no):
        sql = f'''
            SELECT CaseType FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}"
                ORDER BY CaseType
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        total_case_count = 0
        total_B6_count = 0
        for row in rows:
            total_case_count += 1
            if string_utils.xstr(row['CaseType']) == 'B6':
                total_B6_count += 1

        rate = total_B6_count / total_case_count * 100

        self._set_table_widget_indicator_items(
            row_no, total_B6_count, total_case_count, rate,
            show_percent=True,
        )

    # 週日開診天數
    def _calculate_sunday_count(self, row_no):
        sql = f'''
            SELECT StopDate FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}"
                GROUP BY StopDate
                ORDER BY StopDate
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, None, None, 0, show_percent=False)
            return

        sunday_count = 0
        for row in rows:
            case_date = row['StopDate']
            if case_date is None:
                continue
            
            weekday = datetime.datetime(
                case_date.year, case_date.month, case_date.day
            ).weekday()
            weekday_name = date_utils.get_weekday_name(weekday)

            if weekday_name == '星期日':
                sunday_count += 1

        self._set_table_widget_indicator_items(
            row_no, None, None, sunday_count,
            show_percent=False,
        )

    # 慢性病案件申報件數佔率
    def _calculate_case_type_24_rate(self, row_no):
        sql = f'''
            SELECT CaseType FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.apply_period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("21", "24", "28")
                ORDER BY CaseType
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            self._set_table_widget_indicator_items(row_no, 0, 0, 0, show_percent=False)
            return

        total_case_count = 0
        total_24_count = 0
        for row in rows:
            total_case_count += 1
            if string_utils.xstr(row['CaseType']) in ['24', '28']:
                total_24_count += 1

        rate = total_24_count / total_case_count * 100

        self._set_table_widget_indicator_items(
            row_no, total_24_count, total_case_count, rate,
            show_percent=True,
        )

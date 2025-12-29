
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtChart, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import calendar
import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import date_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import nhi_utils
from libs import chart_utils
from libs import case_utils


# 醫師月報表人數統計 2025.01.18 耀康
class StatisticsDoctorMonthlyPersonCount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDoctorMonthlyPersonCount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.year = args[2]
        self.month = args[3]
        self.doctor = args[4]
        self.ui = None

        self.last_day = calendar.monthrange(int(self.year), int(self.month))[1]
        self.start_date = f'{self.year}-{self.month}-01 00:00:00'
        self.end_date = f'{self.year}-{self.month}-{self.last_day} 23:59:59'

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_MONTHLY_PERSON_COUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_person = class_utils.get_table_widget(
            self.ui.tableWidget_person, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [
            80, 60,
            80, 80, 80, 80, 80, 80, 80, 80, 80, 80,
            80, 80, 80, 80, 80, 80, 80, 80, 80, 80,
        ]
        self.table_widget_person.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_to_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.label_doctor.setText(f'統計醫師: {self.doctor}')
        self.ui.tableWidget_person.setRowCount(0)
        self._set_calendar_heading()

        rows = self._read_data()

        for row in rows:
            row_no = self._get_row_no(row['CaseDate'])
            if row_no is None:
                continue

            self._count_person(row, row_no)

        self._calculate_total()

    def _read_data(self):
        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        sql = f'''
            SELECT CaseKey, PatientKey, CaseDate, InsType, Treatment FROM cases
                LEFT JOIN person ON person.Name = cases.Doctor
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                (Doctor IS NOT NULL AND LENGTH(Doctor) > 0) AND
                (person.Position IN ("醫師", "支援醫師"))
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows


    def _get_row_no(self, case_date):
        date_item = case_date.strftime('%m/%d')
        for row_no in range(self.ui.tableWidget_person.rowCount()):
            if self.ui.tableWidget_person.item(row_no, 0).text() == date_item:
                return row_no

        return None

    def _set_calendar_heading(self):
        start_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S').date()
        end_date = datetime.datetime.strptime(self.end_date, '%Y-%m-%d %H:%M:%S').date()
        day_count = (end_date - start_date).days + 1

        calendar_list = []
        for date in (start_date + datetime.timedelta(n) for n in range(day_count)):
            try:
                week_day_name = date_utils.get_weekday_name(date.weekday(), 'zh_TW')
                case_date = date.strftime(f'%m/%d')
            except Exception:
                week_day_name = ''
                case_date = date.strftime('%m/%d')

            if case_date not in calendar_list:
                calendar_list.append([case_date, week_day_name[2]])

        row_count = len(calendar_list)
        self.ui.tableWidget_person.setRowCount(row_count+1)

        for row_no, case_date in enumerate(calendar_list):
            self.ui.tableWidget_person.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(case_date[0])
            )
            self.ui.tableWidget_person.setItem(
                row_no, 1, QtWidgets.QTableWidgetItem(case_date[1])
            )
            self.ui.tableWidget_person.item(
                row_no, 0).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_person.item(
                row_no, 1).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _count_person(self, row, row_no):
        internal_medicine = 0
        general_acupuncture = 0
        moderate_acupuncture = 0
        highly_acupuncture = 0
        general_massage = 0
        moderate_massage = 0
        highly_massage = 0
        acupuncture_with_medicine = 0
        m_acupuncture_with_medicine = 0
        h_acupuncture_with_medicine = 0
        massage_with_medicine = 0
        merge_treat = 0
        merge_treat_with_medicine = 0

        own_expense = 0

        ins_type = string_utils.xstr(row['InsType'])
        treatment = string_utils.xstr(row['Treatment'])
        pres_days = case_utils.get_pres_days(self.database, row['CaseKey'])
        if ins_type == '健保':
            if treatment in nhi_utils.MERGE_TREAT_LIST:
                if pres_days > 0:
                    merge_treat_with_medicine = 1
                else:
                    merge_treat = 1
            elif treatment in nhi_utils.ACUPUNCTURE_TREAT:
                if treatment in nhi_utils.ORDINARY_ACUPUNCTURE_TREAT:
                    if pres_days > 0:
                        acupuncture_with_medicine = 1
                    else:
                        general_acupuncture = 1
                elif treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
                    if pres_days > 0:
                        m_acupuncture_with_medicine = 1
                    else:
                        moderate_acupuncture = 1
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
                    if pres_days > 0:
                        h_acupuncture_with_medicine = 1
                    else:
                        highly_acupuncture = 1
            elif treatment in nhi_utils.MASSAGE_TREAT:
                if pres_days > 0:
                    massage_with_medicine = 1
                elif treatment in nhi_utils.ORDINARY_MASSAGE_TREAT:
                    general_massage = 1
                elif treatment in nhi_utils.MODERATE_COMPLICATED_MASSAGE_TREAT:
                    moderate_massage = 1
                elif treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT:
                    highly_massage = 1
            else:
                internal_medicine = 1
        elif ins_type == '自費':
            own_expense = 1

        acupuncture_subtotal = (
            general_acupuncture + moderate_acupuncture + highly_acupuncture + acupuncture_with_medicine + \
                m_acupuncture_with_medicine + h_acupuncture_with_medicine
        )
        massage_subtotal = general_massage + moderate_massage + highly_massage + massage_with_medicine
        merge_subtotal = merge_treat + merge_treat_with_medicine

        treat_total = acupuncture_subtotal + massage_subtotal + merge_subtotal

        subtotal = internal_medicine + acupuncture_subtotal + massage_subtotal + merge_subtotal
        total = subtotal + own_expense

        self._set_table_item(row_no, 2, internal_medicine)
        self._set_table_item(row_no, 3, general_acupuncture)
        self._set_table_item(row_no, 4, moderate_acupuncture)
        self._set_table_item(row_no, 5, highly_acupuncture)
        self._set_table_item(row_no, 6, acupuncture_with_medicine)
        self._set_table_item(row_no, 7, m_acupuncture_with_medicine)
        self._set_table_item(row_no, 8, h_acupuncture_with_medicine)
        self._set_table_item(row_no, 9, acupuncture_subtotal)

        self._set_table_item(row_no, 10, general_massage)
        self._set_table_item(row_no, 11, moderate_massage)
        self._set_table_item(row_no, 12, highly_massage)
        self._set_table_item(row_no, 13, massage_with_medicine)
        self._set_table_item(row_no, 14, massage_subtotal)

        self._set_table_item(row_no, 15, merge_treat)
        self._set_table_item(row_no, 16, merge_treat_with_medicine)
        self._set_table_item(row_no, 17, merge_subtotal)

        self._set_table_item(row_no, 18, treat_total)

        self._set_table_item(row_no, 19, subtotal)
        self._set_table_item(row_no, 20, own_expense)
        self._set_table_item(row_no, 21, total)

    def _set_table_item(self, row_no, col_no, data):
        current_item = self.ui.tableWidget_person.item(row_no, col_no)
        if current_item is None:
            count = 0
        else:
            count = number_utils.get_integer(current_item.text())

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, data + count)
        self.ui.tableWidget_person.setItem(row_no, col_no, item)
        self.ui.tableWidget_person.item(
            row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    def _calculate_total(self):
        row_count = self.ui.tableWidget_person.rowCount()
        for col_no in range(2, self.ui.tableWidget_person.columnCount()):
            total = 0
            for row_no in range(row_count):
                item = self.ui.tableWidget_person.item(row_no, col_no)
                if item is not None:
                    total += number_utils.get_integer(item.text())

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, total)
            self.ui.tableWidget_person.setItem(row_count-1, col_no, item)
            self.ui.tableWidget_person.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, '總計')
        self.ui.tableWidget_person.setItem(row_count-1, 0, item)
        self.ui.tableWidget_person.item(
            row_count-1, 0).setTextAlignment(
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
        )

    def _export_to_excel(self):
        options = QtWidgets.QFileDialog.Options()
        excel_file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.parent,
            "匯出月報表",
            f'{self.year}年{self.month}月份人數統計.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_person,
            None, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
            f'{self.year}年{self.month}月份人數統計',
            
        )

        system_utils.show_message_box(
            QtWidgets.QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

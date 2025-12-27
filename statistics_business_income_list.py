# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui, QtChart
from PyQt5.QtWidgets import QMessageBox, QFileDialog

import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import case_utils
from libs import export_utils
from libs import system_utils
from libs import personnel_utils


# 執行業務所得統計 2024.07.19
class StatisticsBusinessIncomeList(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsBusinessIncomeList, self).__init__(parent)
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
        self.program_name = '自費印花稅統計'
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()


        self.item_list = [
            '科中藥品', '水藥', '丸散', '保健食品', '三伏貼', '三九貼',
            '推拿', '整復', '拔罐', '針灸', '護具', '膏藥', '藥膏', '貼布', '噴劑',
            '減肥', '診斷證明書'
        ]

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_BUSINESS_INCOME_LIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_case_amount = class_utils.get_table_widget(self.ui.tableWidget_case_amount, self.database)
        self._set_table_width()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.toolButton_export_excel.setEnabled(False)

    def _set_table_width(self):
        width = [
            180, 100, 120, 100,
        ]
        self.table_widget_case_amount.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_export_excel.clicked.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    def start_calculate(self):
        self.ui.tableWidget_case_amount.setRowCount(0)
        self._calculate_data()

    def _calculate_data(self):
        self._set_items()
        self._calculate_case_amount()
        self._calculate_table_widget_total(self.ui.tableWidget_case_amount)

    def _set_items(self):
        self.ui.tableWidget_case_amount.setRowCount(len(self.item_list)+1)
        for row_no, item_name in enumerate(self.item_list):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, item_name) 
            self.ui.tableWidget_case_amount.setItem(row_no, 0, item)

    def _get_row_no(self, item_type):
        for row_no, item_name in enumerate(self.item_list):
            if item_name == item_type:
                return row_no

    def _calculate_case_amount(self):
        rows = self._get_case_rows()
        for row in rows:
            case_key = row['CaseKey']
            total_fee = number_utils.get_integer(row['TotalFee'])
            item_type = self._get_item_type(case_key)
            row_no = self._get_row_no(item_type)
            if row_no is None:
                print(item_type)
                continue

            self._set_data(row_no, total_fee)

    def _set_data(self, row_no, total_fee):
        person_item = self.ui.tableWidget_case_amount.item(row_no, 1)
        if person_item is None:
            person_item = 0
        else:
            person_item = number_utils.get_integer(person_item.text())

        total_fee_item = self.ui.tableWidget_case_amount.item(row_no, 2)
        if total_fee_item is None:
            total_fee_item = 0
        else:
            total_fee_item = number_utils.get_integer(total_fee_item.text())

        self._set_item_data(self.ui.tableWidget_case_amount, row_no, 1, person_item+1)
        self._set_item_data(self.ui.tableWidget_case_amount, row_no, 2, total_fee_item + total_fee)

    def _get_case_rows(self):
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

        sql = f'''
            SELECT
                CaseKey, TotalFee
            FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                TotalFee > 0
                {period_condition}
                {weekday_condition}
                {ins_type_condition}
                {regist_condition}
                {doctor_condition}
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_item_type(self, case_key):
        sql = f'''
            SELECT
                MedicineName, MedicineType
            FROM 
                prescript
            WHERE
                CaseKey = "{case_key}" AND
                MedicineSet >= 2
        '''
        rows = self.database.select_record(sql)

        item_type = None
        for row in rows:
            medicine_type = string_utils.xstr(row['MedicineType'])
            medicine_name = string_utils.xstr(row['MedicineName'])
            for item_name in self.item_list:
                if item_name in medicine_name or item_name in medicine_type:
                    return item_name

        if item_type is None:
            for row in rows:
                if medicine_type in ['單方', '複方']:
                    item_type = '科中藥品'
                    break
                elif '丸' in medicine_type and '丸' in medicine_name:
                    item_type = '丸散'
                    break
                elif '散' in medicine_type and '散' in medicine_name:
                    item_type = '丸散'
                    break
                elif 'OTC' in medicine_type:
                    item_type = '保健食品'
                    break
                elif '埋線' in medicine_type or '埋線' in medicine_name:
                    item_type = '埋線減肥'
                    break
                elif medicine_type in ['器材']:
                    item_type = '護具'
                    break
                elif medicine_type in ['外用']:
                    item_type = '膏藥'
                    break
                elif medicine_type in ['穴道']:
                    item_type = '針灸'
                    break
                elif medicine_type in ['處置']:
                    item_type = '推拿'
                    break
                else:
                    item_type = '保健食品'

        return item_type

    def _calculate_table_widget_total(self, tableWidget):
        row_count = tableWidget.rowCount()
        total_person, total_fee, total_avg = 0, 0, 0
        for row_no in range(row_count- 1):
            person_item = tableWidget.item(row_no, 1)
            if person_item is None:
                continue

            person_count = number_utils.get_integer(person_item.text())
            total_person += person_count

            total_fee_item = tableWidget.item(row_no, 2)
            if total_fee_item is None:
                continue

            total_fee_count = number_utils.get_integer(total_fee_item.text())
            total_fee += total_fee_count

            avg_fee = round(total_fee_count / person_count)
            total_avg += avg_fee
            self._set_item_data(self.ui.tableWidget_case_amount, row_no, 3, avg_fee)

        self._set_item_data(self.ui.tableWidget_case_amount, row_count-1, 0, '合計')
        self._set_item_data(self.ui.tableWidget_case_amount, row_count-1, 1, total_person)
        self._set_item_data(self.ui.tableWidget_case_amount, row_count-1, 2, total_fee)
        self._set_item_data(self.ui.tableWidget_case_amount, row_count-1, 3, total_avg)

    def _set_item_data(self, tableWidget, row_no, col_no, data):
        tableWidget.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(data))
        )
        tableWidget.item(row_no, col_no).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _export_to_excel(self):
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            f'{self.start_date[:10]}至{self.end_date[:10]}{self.doctor}執行業務所得統計表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_case_amount, [],
            [1, 2, 3], title=None,
            column_width=[15]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

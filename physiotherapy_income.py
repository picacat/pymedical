
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QPushButton
import datetime
import calendar
import re

from libs import number_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import personnel_utils


# 物理治療收入統計 2023.06.13
class PhysiotherapyIncome(QtWidgets.QMainWindow):
    program_name = '物理治療收入統計'

    # 初始化
    def __init__(self, parent=None, *args):
        super(PhysiotherapyIncome, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.time_list = self.parent.time_list

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHYSIOTHERAPY_INCOME, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)

        physiotherapy_list = personnel_utils.get_person(self.database, '物理治療師')
        ui_utils.set_combo_box(self.ui.comboBox_physiotherapy, physiotherapy_list, '全部')
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        last_day = calendar.monthrange(year, month)[1]

        self.ui.dateEdit_start_date.setDate(QtCore.QDate(year, month, 1))
        self.ui.dateEdit_end_date.setDate(QtCore.QDate(year, month, last_day))
        # self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_template)
        self.ui.pushButton_calculate.clicked.connect(self._calculate_income)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_template(self):
        self.close_all()
        self.close_tab()

    def _calculate_income(self):
        self._set_calendar_table()
        self._start_calculate()
        self._calculate_subtotal()
        self._calculate_total()

        self.ui.tableWidget_income.resizeColumnsToContents()
        self.ui.tableWidget_income.resizeRowsToContents()

    def _set_calendar_table(self):
        self.ui.tableWidget_income.clear()
        header_list = []
        for time in self.time_list:
            header_list.append(time)

        header_list.append('小計')
        self.ui.tableWidget_income.setColumnCount(len(header_list))
        self.ui.tableWidget_income.setHorizontalHeaderLabels(header_list)

        start_date = self.ui.dateEdit_start_date.date()
        end_date = self.ui.dateEdit_end_date.date()
        dates = []
        while start_date <= end_date:
            dates.append(start_date.toString('yyyy-MM-dd'))
            start_date = start_date.addDays(1)

        dates.append('合計')
        self.ui.tableWidget_income.setRowCount(len(dates))
        self.ui.tableWidget_income.setVerticalHeaderLabels(dates)

    def _start_calculate(self):
        for row_no in range(self.ui.tableWidget_income.rowCount()):
            for col_no in range(self.ui.tableWidget_income.columnCount()):
                date = self.tableWidget_income.verticalHeaderItem(row_no).text()
                time = self.tableWidget_income.horizontalHeaderItem(col_no).text()
                if date == '合計':
                    break

                self._calculate_data(row_no, col_no, date, time)

    def _calculate_data(self, row_no, col_no, date, time):
        physiotherapy = self.ui.comboBox_physiotherapy.currentText()
        physiotherapy_condition = ''
        if physiotherapy != '全部':
            physiotherapy_condition = f' AND Physiotherapy = "{physiotherapy}"'

        sql = f'''
            SELECT * FROM physiotherapy_schedule
            WHERE
                PhysiotherapyDate = "{date}" AND
                PhysiotherapyTime = "{time}"
                {physiotherapy_condition}
        '''

        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        content = []
        for row in rows:
            receipt_fee = number_utils.get_integer(row['ReceiptFee'])
            if receipt_fee <= 0:
                continue

            if physiotherapy == '全部':
                cell = f"{receipt_fee}({row['Physiotherapy']})"
            else:
                cell = f"{receipt_fee}"

            content.append(cell)

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, '\n'.join(content))
        self.ui.tableWidget_income.setItem(row_no, col_no, item)
        self.ui.tableWidget_income.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        )

    def _calculate_subtotal(self):
        for row_no in range(self.ui.tableWidget_income.rowCount()):
            subtotal = 0
            for col_no in range(self.ui.tableWidget_income.columnCount()):
                item = self.tableWidget_income.item(row_no, col_no)
                if item is None:
                    continue

                cells = item.text().split('\n')
                for cell in cells:
                    fee = re.sub(r'\(.*?\)', '', cell)
                    subtotal += number_utils.get_integer(fee)

            if subtotal > 0:
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, subtotal)
                self.ui.tableWidget_income.setItem(row_no, col_no, item)
                self.ui.tableWidget_income.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _calculate_total(self):
        for col_no in range(self.ui.tableWidget_income.columnCount()):
            total = 0
            for row_no in range(self.ui.tableWidget_income.rowCount()):
                item = self.tableWidget_income.item(row_no, col_no)
                if item is None:
                    continue

                cells = item.text().split('\n')
                for cell in cells:
                    fee = re.sub(r'\(.*?\)', '', cell)
                    total += number_utils.get_integer(fee)

            if total > 0:
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, total)
                self.ui.tableWidget_income.setItem(row_no, col_no, item)
                self.ui.tableWidget_income.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import calendar
import os

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import system_utils
from libs import dialog_utils
from libs import number_utils
from libs import export_utils


# 年度診次統計 2025-05-20
class StatisticsPeriodYear(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsPeriodYear, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.sql = None

        self._set_ui()
        self._set_signal()

        self.dialog_setting = {
            "dialog_executed": False,
            "year": None,
        }

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_PERIOD_YEAR, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_year = class_utils.get_table_widget(
            self.ui.tableWidget_year, self.database)

    # 設定信號
    def _set_signal(self):
        self.ui.action_requery.triggered.connect(self.open_dialog)
        self.ui.action_close.triggered.connect(self.close_form)
        self.ui.action_export_to_excel.triggered.connect(self._export_to_excel)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_form(self):
        self.close_all()
        self.close_tab()

    # 讀取病歷
    def open_dialog(self):
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, 'by_year')

        if self.dialog_setting['dialog_executed']:
            dialog.ui.comboBox_year.setCurrentText(self.dialog_setting['year'])

        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = dialog.ui.comboBox_year.currentText()

        self.dialog_setting['dialog_executed'] = True
        self.dialog_setting['year'] = year

        dialog.deleteLater()

        self._start_calculate()

    def _start_calculate(self):
        self._set_table_cells()
        for month in range(1, 13):
            self._set_period_data(month)

    def _set_table_cells(self):
        self.ui.tableWidget_year.setRowCount(13)     # 12個月 + 合計
        self.ui.tableWidget_year.setColumnCount(33)  # 1~31日 + 合計 + 平均診次

        headers = [str(d) for d in range(1, 32)] + ['合計', '平均診次']
        self.ui.tableWidget_year.setHorizontalHeaderLabels(headers)
        self.ui.tableWidget_year.setVerticalHeaderLabels(
            [f"{m}月" for m in range(1, 13)] + ['合計']
        )
            # 欄位寬度設定
        for col in range(31):  # 1~31日
            self.ui.tableWidget_year.setColumnWidth(col, 28)  # 窄一點的寬度
            self.ui.tableWidget_year.setColumnWidth(31, 55)  # 合計
            self.ui.tableWidget_year.setColumnWidth(32, 80)  # 平均診次

        # 初始化所有格子為空字串
        for row in range(13):
            for col in range(33):
                self.ui.tableWidget_year.setItem(row, col, QtWidgets.QTableWidgetItem(''))

    def _set_period_data(self, month):
        year = self.dialog_setting['year']

        start_date = f'{year}-{month}-01'
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_date = f'{year}-{month}-{last_day}'

        sql = f'''
            SELECT DayOfMonth(CaseDate) AS Day, COUNT(DISTINCT Period) AS PeriodCount from cases
            WHERE
                DATE(CaseDate) between "{start_date}" AND "{end_date}"
            GROUP BY DATE(CaseDate)
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        row_no = month - 1
        monthly_total = 0
        valid_day_count = 0

        for row in rows:
            day = int(row['Day'])
            count = int(row['PeriodCount'])

            col_no = day - 1
            self._set_item(row_no, col_no, count)

            monthly_total += count
            valid_day_count += 1

            # 年度合計欄更新（第12列）
            current_value = self.ui.tableWidget_year.item(12, col_no)
            current_sum = int(current_value.text()) if current_value and current_value.text().isdigit() else 0
            self._set_item(12, col_no, current_sum + count)

        # 填入每月合計與平均
        self._set_item(row_no, 31, monthly_total)
        avg = round(monthly_total / valid_day_count, 2) if valid_day_count else 0
        self._set_item(row_no, 32, avg)

        # 更新年度合計總和（第12列，合計與平均）
        year_total_item = self.ui.tableWidget_year.item(12, 31)
        year_total = int(year_total_item.text()) if year_total_item and year_total_item.text().isdigit() else 0
        self._set_item(12, 31, year_total + monthly_total)

        # 年度平均診次（總和 ÷ 365）
        year_total = int(self.ui.tableWidget_year.item(12, 31).text())
        year_avg = round(year_total / 365, 2)
        self._set_item(12, 32, year_avg)

    def _set_item(self, row_no, col_no, value):
        item = QtWidgets.QTableWidgetItem(string_utils.xstr(value))
        self.ui.tableWidget_year.setItem(row_no, col_no, item)
        if item is not None:
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _export_to_excel(self):
        last_dir = system_utils.get_last_directory('年度診次統計表')
        options = QFileDialog.Options()
        excel_filename = os.path.join(last_dir, f"{self.dialog_setting['year']}年度診次統計表.xlsx")
        excel_filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出年度診次統計表",excel_filename,
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_filename:
            return

        export_utils.export_table_widget_to_excel(
            excel_filename, self.ui.tableWidget_year,
            None, [
                0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
                24, 25, 26, 27, 28, 29, 30, 31, 32],
            f"{self.dialog_setting['year']}年度診次統計表",
        )
        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>{excel_filename}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QFileDialog
import datetime

from libs import class_utils
from libs import ui_utils
from libs import string_utils
from libs import number_utils
from libs import export_utils
from libs import system_utils
from libs import date_utils
from libs import case_utils


# 門診指定醫師初複診統計 2022.01.27
class StatisticsDesignatedDoctorVisitCount(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(StatisticsDesignatedDoctorVisitCount, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.start_date = args[2]
        self.end_date = args[3]
        self.period = args[4]
        self.doctor = args[5]
        self.option = args[6]
        self.weekday_list = args[7]
        self.ui = None

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_STATISTICS_DOCTOR_VISIT_COUNT, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_count = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_count, self.database
        )

    def _set_table_header(self):
        start_year = (self.start_date.split(' ')[0]).split('-')[0]
        start_month = (self.start_date.split(' ')[0]).split('-')[1]
        start_day = (self.start_date.split(' ')[0]).split('-')[2]

        end_day = (self.end_date.split(' ')[0]).split('-')[2]
        interval = (int(end_day) - int(start_day) + 1)
        visit_columns = interval * 2
        self.ui.tableWidget_doctor_count.setColumnCount(visit_columns + 7)
        self.ui.tableWidget_doctor_count.setRowCount(3)

        width = [100, 50]
        for col_no in range(visit_columns):
            width += [40]
            if col_no % 2 == 0:
                visit = '初'
            else:
                visit = '複'

            self.ui.tableWidget_doctor_count.setItem(2, col_no+2, QtWidgets.QTableWidgetItem(visit))

        width += [70, 70, 100, 100, 100]
        for i, w in enumerate(width):
            self.ui.tableWidget_doctor_count.setColumnWidth(i, w)

        day = int(start_day)
        for col_no in range(2, visit_columns + 2, 2):
            self.ui.tableWidget_doctor_count.setSpan(0, col_no, 1, 2)
            self.ui.tableWidget_doctor_count.setSpan(1, col_no, 1, 2)
            self.ui.tableWidget_doctor_count.setItem(0, col_no, QtWidgets.QTableWidgetItem(str(day)))
            current_week_day = datetime.datetime(int(start_year), int(start_month), day).weekday()
            week_day_name = date_utils.get_weekday_name(current_week_day)[2]
            self.ui.tableWidget_doctor_count.setItem(1, col_no, QtWidgets.QTableWidgetItem(week_day_name))
            day += 1

        self.ui.tableWidget_doctor_count.setSpan(0, 0, 2, 1)
        self.ui.tableWidget_doctor_count.setItem(0, 0, QtWidgets.QTableWidgetItem(f'{start_month}月份'))
        self.ui.tableWidget_doctor_count.setItem(0, 1, QtWidgets.QTableWidgetItem('日'))
        self.ui.tableWidget_doctor_count.setItem(1, 1, QtWidgets.QTableWidgetItem('星期'))
        self.ui.tableWidget_doctor_count.setItem(2, 0, QtWidgets.QTableWidgetItem('醫師'))
        self.ui.tableWidget_doctor_count.setItem(2, 1, QtWidgets.QTableWidgetItem('時段'))

        self.ui.tableWidget_doctor_count.setSpan(0, visit_columns + 2, 2, 2)
        self.ui.tableWidget_doctor_count.setSpan(0, visit_columns + 4, 3, 1)
        self.ui.tableWidget_doctor_count.setSpan(0, visit_columns + 5, 3, 1)
        self.ui.tableWidget_doctor_count.setSpan(0, visit_columns + 6, 3, 1)

        self.ui.tableWidget_doctor_count.setItem(0, visit_columns + 2, QtWidgets.QTableWidgetItem('總人數'))
        self.ui.tableWidget_doctor_count.setItem(2, visit_columns + 2, QtWidgets.QTableWidgetItem('初診'))
        self.ui.tableWidget_doctor_count.setItem(2, visit_columns + 3, QtWidgets.QTableWidgetItem('複診'))
        self.ui.tableWidget_doctor_count.setItem(0, visit_columns + 4, QtWidgets.QTableWidgetItem('總人數'))
        self.ui.tableWidget_doctor_count.setItem(0, visit_columns + 5, QtWidgets.QTableWidgetItem('總節數'))
        self.ui.tableWidget_doctor_count.setItem(0, visit_columns + 6, QtWidgets.QTableWidgetItem('每節人數'))

        self._set_doctor_columns()
        self._center_cell()

    def _center_cell(self):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
                if item is not None:
                    item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _set_doctor_columns(self):
        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND Doctor = "{self.doctor}"'

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'

        sql = f'''
            SELECT Doctor FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0 AND
                DesignatedDoctor = "True"
                {weekday_condition}
                {doctor_condition}
            GROUP BY Doctor
        '''
        rows = self.database.select_record(sql)
        row_count = len(rows) * 4
        self.ui.tableWidget_doctor_count.setRowCount(self.ui.tableWidget_doctor_count.rowCount() + row_count)

        doctor_rows = 4
        for i, row in enumerate(rows):
            row_no = (i * doctor_rows) + 3
            self.ui.tableWidget_doctor_count.setItem(
                row_no, 0, QtWidgets.QTableWidgetItem(string_utils.xstr(row['Doctor'])))
            self.ui.tableWidget_doctor_count.setItem(row_no, 1, QtWidgets.QTableWidgetItem('早'))
            self.ui.tableWidget_doctor_count.setItem(row_no+1, 1, QtWidgets.QTableWidgetItem('午'))
            self.ui.tableWidget_doctor_count.setItem(row_no+2, 1, QtWidgets.QTableWidgetItem('晚'))
            self.ui.tableWidget_doctor_count.setItem(row_no+3, 1, QtWidgets.QTableWidgetItem('合計'))
            self.ui.tableWidget_doctor_count.setSpan(row_no, 0, doctor_rows, 1)

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
        self.ui.tableWidget_doctor_count.setRowCount(0)
        self._set_table_header()

        self._calculate_data()
        self._calculate_total()

    def _read_data(self):
        doctor_condition = ''
        if self.doctor != '全部':
            doctor_condition = f' AND cases.Doctor = "{self.doctor}"'

        regist_condition = case_utils.get_regist_type_exclude_sql(self.option)

        weekday_condition = ''
        if len(self.weekday_list) > 0:
            weekday_condition = f' AND WEEKDAY(CaseDate) IN({",".join(self.weekday_list)})'


        sql = f'''
            SELECT CaseDate, Period, Doctor, Visit FROM cases
            WHERE
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                Doctor IS NOT NULL AND LENGTH(Doctor) > 0 AND
                DesignatedDoctor = "True"
                {weekday_condition}
                {regist_condition}
                {doctor_condition}
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_row_no(self, doctor, period):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            doctor_item = self.ui.tableWidget_doctor_count.item(row_no, 0)
            if doctor_item is None:
                continue

            if doctor == doctor_item.text():
                if period == '早班':
                    return row_no
                elif period == '午班':
                    return row_no + 1
                elif period == '晚班':
                    return row_no + 2
                elif period == '合計':
                    return row_no + 2

        return None

    def _get_col_no(self, case_date, visit):
        day = case_date.day
        for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
            day_item = self.ui.tableWidget_doctor_count.item(0, col_no)
            if day_item is None:
                continue

            if str(day) == day_item.text():
                if visit == '初診':
                    return col_no
                elif visit == '複診':
                    return col_no + 1

        return None

    def _calculate_data(self):
        rows = self._read_data()
        row_count = len(rows)
        if row_count <= 0:
            return

        progress_dialog = QtWidgets.QProgressDialog(
            '門診資料統計中, 請稍後...', '取消', 0, row_count, self
        )

        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)
        for i, row in enumerate(rows):
            progress_dialog.setValue(i)

            case_date = row['CaseDate']
            period = string_utils.xstr(row['Period'])
            doctor = string_utils.xstr(row['Doctor'])
            visit = string_utils.xstr(row['Visit'])
            row_no = self._get_row_no(doctor, period)
            if row_no is None:
                continue

            col_no = self._get_col_no(case_date, visit)
            if col_no is None:
                continue

            item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
            if item is None:
                value = 0
            else:
                value = number_utils.get_integer(item.text())

            value += 1
            self._set_item_data(row_no, col_no, visit, value)

        progress_dialog.setValue(row_count)
        progress_dialog.deleteLater()

    def _set_item_data(self, row_no, col_no, visit, value):
        self.ui.tableWidget_doctor_count.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem(string_utils.xstr(value)))
        self.ui.tableWidget_doctor_count.item(row_no, col_no).setTextAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        if visit in ['初', '初診']:
            self.ui.tableWidget_doctor_count.item(row_no, col_no).setForeground(QtGui.QColor('red'))
        elif visit in ['複', '複診']:
            self.ui.tableWidget_doctor_count.item(row_no, col_no).setForeground(QtGui.QColor('blue'))
        elif visit in ['合計']:
            self.ui.tableWidget_doctor_count.item(row_no, col_no).setForeground(QtGui.QColor('darkMagenta'))

    def _calculate_total(self):
        self._calculate_visit_total()
        self._calculate_visit_subtotal('初')
        self._calculate_visit_subtotal('複')
        self._calculate_total_person()
        self._calculate_total_period()
        self._calculate_summary()
        self._calculate_avg_period()
        self._fill_zero()
        self._set_cell_background_color()

    def _calculate_visit_total(self):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            doctor_item = self.ui.tableWidget_doctor_count.item(row_no, 0)
            if doctor_item is None:
                continue

            if '月份' in doctor_item.text() or '醫師' in doctor_item.text():
                continue

            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                visit_item = self.ui.tableWidget_doctor_count.item(2, col_no)
                if visit_item is None:
                    continue

                visit = visit_item.text()
                if visit not in ['初', '複']:
                    continue

                period1 = self._get_cell_value(row_no, col_no)
                period2 = self._get_cell_value(row_no+1, col_no)
                period3 = self._get_cell_value(row_no+2, col_no)
                if period1 == 0 and period2 == 0 and period3 == 0:
                    continue

                self._set_item_data(row_no+3, col_no, '合計', period1 + period2 + period3)
                # font = QtGui.QFont()
                # font.setBold(True)
                # self.ui.tableWidget_doctor_count.item(row_no+3, col_no).setFont(font)

    def _calculate_visit_subtotal(self, visit):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            period_item = self.ui.tableWidget_doctor_count.item(row_no, 1)
            if period_item is None:
                continue

            period = period_item.text()
            if period not in ['早', '午', '晚', '合計']:
                continue

            subtotal = 0
            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                visit_item = self.ui.tableWidget_doctor_count.item(2, col_no)
                if visit_item is None:
                    continue

                current_visit = visit_item.text()
                if current_visit != visit:
                    continue

                value = self._get_cell_value(row_no, col_no)
                subtotal += value

            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                visit_item = self.ui.tableWidget_doctor_count.item(2, col_no)
                if visit_item is None:
                    continue

                current_visit = visit_item.text()
                if current_visit == f'{visit}診':
                    self._set_item_data(row_no, col_no, visit, subtotal)
                    break

    def _calculate_total_person(self):
        total_person = 0
        col_count = self.ui.tableWidget_doctor_count.columnCount()

        for row_no in range(3, self.ui.tableWidget_doctor_count.rowCount()):
            item = self.ui.tableWidget_doctor_count.item(row_no, col_count-5)
            if item is None:
                continue

            period1 = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, col_count-5).text())
            period2 = number_utils.get_integer(
                self.ui.tableWidget_doctor_count.item(row_no, col_count-4).text())
            total_person = period1 + period2
            self._set_item_data(row_no, col_count-3, None, total_person)

    # 計算總節數
    def _calculate_total_period(self):
        col_count = self.ui.tableWidget_doctor_count.columnCount()

        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            period_item = self.ui.tableWidget_doctor_count.item(row_no, 1)
            if period_item is None:
                continue

            period = period_item.text()
            if period not in ['早', '午', '晚']:
                continue

            total_period = 0
            for col_no in range(col_count):
                week_item = self.ui.tableWidget_doctor_count.item(1, col_no)
                if week_item is None:
                    continue

                week = week_item.text()
                if week not in ['日', '一', '二', '三', '四', '五', '六']:
                    continue

                visit1 = self._get_cell_value(row_no, col_no)
                visit2 = self._get_cell_value(row_no, col_no+1)

                if visit1 + visit2 > 0:
                    total_period += 1

            self._set_item_data(row_no, col_count-2, None, total_period)

        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            period_item = self.ui.tableWidget_doctor_count.item(row_no, 1)
            if period_item is None:
                continue

            period = period_item.text()
            if period not in ['合計']:
                continue

            period1 = self._get_cell_value(row_no-3, col_count-2)
            period2 = self._get_cell_value(row_no-2, col_count-2)
            period3 = self._get_cell_value(row_no-1, col_count-2)
            self._set_item_data(row_no, col_count-2, period, period1 + period2 + period3)

    def _calculate_avg_period(self):
        col_count = self.ui.tableWidget_doctor_count.columnCount()

        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            period_item = self.ui.tableWidget_doctor_count.item(row_no, 1)
            if period_item is None:
                continue

            period = period_item.text()
            if period not in ['早', '午', '晚', '合計']:
                continue

            total_person = self._get_cell_value(row_no, col_count-3)
            total_period = self._get_cell_value(row_no, col_count-2)

            if total_period == 0:
                avg_person = 0
            else:
                avg_person = total_person / total_period

            self._set_item_data(row_no, col_count-1, None, round(avg_person, 1))

    def _calculate_summary(self):
        self._set_summary_header()
        self._calculate_summary_total()

    def _set_summary_header(self):
        row_count = self.ui.tableWidget_doctor_count.rowCount()
        self.ui.tableWidget_doctor_count.setRowCount(row_count + 4)
        self.ui.tableWidget_doctor_count.setSpan(row_count, 0, 4, 1)
        self.ui.tableWidget_doctor_count.setItem(row_count, 0, QtWidgets.QTableWidgetItem('總計'))
        self.ui.tableWidget_doctor_count.setItem(row_count, 1, QtWidgets.QTableWidgetItem('早'))
        self.ui.tableWidget_doctor_count.setItem(row_count+1, 1, QtWidgets.QTableWidgetItem('午'))
        self.ui.tableWidget_doctor_count.setItem(row_count+2, 1, QtWidgets.QTableWidgetItem('晚'))
        self.ui.tableWidget_doctor_count.setItem(row_count+3, 1, QtWidgets.QTableWidgetItem('合計'))
        if self.ui.tableWidget_doctor_count.item(row_count, 0) is not None:
            self.ui.tableWidget_doctor_count.item(row_count, 0).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_doctor_count.item(row_count, 1).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_doctor_count.item(row_count+1, 1).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_doctor_count.item(row_count+2, 1).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_doctor_count.item(row_count+3, 1).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _calculate_summary_total(self):
        row_count = self.ui.tableWidget_doctor_count.rowCount()

        for col_no in range(self.ui.tableWidget_doctor_count.columnCount()-1):
            visit_item = self.ui.tableWidget_doctor_count.item(2, col_no)
            if visit_item is not None and visit_item.text() in ['醫師', '時段']:
                continue

            total_period1, total_period2, total_period3 = 0, 0, 0
            for row_no in range(row_count):
                doctor_item = self.ui.tableWidget_doctor_count.item(row_no, 0)
                if doctor_item is None:
                    continue

                if '月份' in doctor_item.text() or '醫師' in doctor_item.text() or '總計' in doctor_item.text():
                    continue

                period1 = self._get_cell_value(row_no, col_no)
                period2 = self._get_cell_value(row_no+1, col_no)
                period3 = self._get_cell_value(row_no+2, col_no)

                total_period1 += period1
                total_period2 += period2
                total_period3 += period3

                self._set_item_data(row_count-4, col_no, None, total_period1)
                self._set_item_data(row_count-3, col_no, None, total_period2)
                self._set_item_data(row_count-2, col_no, None, total_period3)
                self._set_item_data(row_count-1, col_no, None, total_period1 + total_period2 + total_period3)

    def _get_cell_value(self, row_no, col_no):
        item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
        if item is None:
            value = 0
        else:
            value = number_utils.get_integer(item.text())

        return value

    def _fill_zero(self):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                item = self.ui.tableWidget_doctor_count.item(row_no, col_no)
                if item is None:
                    self._set_item_data(row_no, col_no, None, 0)
                    self.ui.tableWidget_doctor_count.item(row_no, col_no).setForeground(QtGui.QColor('gray'))

    def _set_cell_background_color(self):
        for row_no in range(self.ui.tableWidget_doctor_count.rowCount()):
            if self.ui.tableWidget_doctor_count.item(row_no, 1) is None:
                continue

            period = self.ui.tableWidget_doctor_count.item(row_no, 1).text()

            for col_no in range(self.ui.tableWidget_doctor_count.columnCount()):
                if col_no == 0:
                    self.ui.tableWidget_doctor_count.item(row_no, 0).setBackground(QtGui.QColor('lightGray'))
                elif col_no == 1 or period == '合計':
                    self.ui.tableWidget_doctor_count.item(row_no, col_no).setBackground(QtGui.QColor('#D7DBDD'))

        for col_no in range(2, self.ui.tableWidget_doctor_count.columnCount()):
            self.ui.tableWidget_doctor_count.item(0, col_no).setBackground(QtGui.QColor('#D7DBDD'))
            self.ui.tableWidget_doctor_count.item(2, col_no).setBackground(QtGui.QColor('#D7DBDD'))

    def _export_to_excel(self):
        start_date = self.start_date[:10]
        end_date = self.end_date[:10]
        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "資料匯出",
            f'{start_date}至{end_date}{self.doctor}門診收入一覽表.xlsx',
            "excel檔案 (*.xlsx);;Text Files (*.txt)", options=options
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_doctor_count, None, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            '資料匯出完成',
            f'<h3>門診收入一覽檔{excel_file_name}匯出完成.</h3>',
            'Microsoft Excel 格式.'
        )

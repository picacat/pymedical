
# 櫃台購藥 2014.09.22
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox
import datetime
import calendar

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import personnel_utils
from libs import date_utils
from libs import registration_utils
from libs import number_utils
from libs import dialog_utils
from libs import nhi_utils
from libs import db_utils


# 養生館掛號
class MassageRegistration(QtWidgets.QMainWindow):
    program_name = '養生館掛號'

    # 初始化
    def __init__(self, parent=None, *args):
        super(MassageRegistration, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.interval_time = 10  # 間隔10分鐘
        self.interval = int(60 / self.interval_time)

        self._set_db()
        self._set_ui()
        self._set_signal()
        self._read_timeline()

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

    # 設定資料庫來源
    def _set_db(self):
        self.massage_database = db_utils.get_external_host_database(self.database, '養生館')

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_MASSAGE_REGISTRATION, self)
        system_utils.set_css(self, self.system_settings)
        self.ui.dateEdit_reservation_date.setDate(datetime.datetime.today())
        self.ui.dateEdit_start_date.setDate(datetime.datetime.today())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.today())
        self.table_widget_reservation_list = class_utils.get_table_widget(
            self.ui.tableWidget_reservation_list, self.massage_database
        )
        self.table_widget_reservation_list.set_column_hidden([0])
        self._set_table_width()
        self._set_week_day()
        self._set_reservation_tool_button(False)
        self._set_current_period()
        self.ui.tabWidget_reservation.setCurrentIndex(0)

    def _set_table_width(self):
        width = [
            100, 110, 120, 60, 80, 100, 120, 120, 100, 100, 80, 80,
        ]
        self.table_widget_reservation_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_add_reservation.triggered.connect(self._add_reservation)
        self.ui.action_modify_reservation.triggered.connect(self._modify_reservation)
        self.ui.action_cancel_reservation.triggered.connect(self._cancel_reservation)
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_off_day_setting.triggered.connect(self._off_day_setting)

        self.ui.radioButton_period1.clicked.connect(self._read_timeline)
        self.ui.radioButton_period2.clicked.connect(self._read_timeline)
        self.ui.radioButton_period3.clicked.connect(self._read_timeline)
        self.ui.dateEdit_reservation_date.dateChanged.connect(self._read_timeline)
        self.ui.tableWidget_schedule.itemSelectionChanged.connect(self._schedule_item_selection_changed)
        self.ui.tableWidget_schedule.doubleClicked.connect(self._schedule_double_clicked)
        self.ui.tableWidget_calendar.cellClicked.connect(self._calendar_changed)

        self.ui.dateEdit_start_date.dateChanged.connect(self._read_reservation_list)
        self.ui.dateEdit_end_date.dateChanged.connect(self._read_reservation_list)

        self.ui.tabWidget_reservation.currentChanged.connect(self._tab_changed)                   # 切換分頁
        self.ui.toolButton_previous.clicked.connect(self._previous_calendar)
        self.ui.toolButton_next.clicked.connect(self._next_calendar)

    def _set_permission(self):
        if self.user_name == '超級使用者':
            return

    def _set_current_period(self):
        period = registration_utils.get_current_period(self.system_settings)

        if period == '早班':
            self.ui.radioButton_period1.setChecked(True)
        elif period == '午班':
            self.ui.radioButton_period2.setChecked(True)
        elif period == '晚班':
            self.ui.radioButton_period3.setChecked(True)
        else:
            self.ui.radioButton_period1.setChecked(True)

    def _set_week_day(self):
        week_day_name = self._get_week_day_name()
        self.ui.label_weekday_name.setText(week_day_name)

    def _get_week_day_name(self):
        current_week_day = datetime.datetime(
            self.ui.dateEdit_reservation_date.date().year(),
            self.ui.dateEdit_reservation_date.date().month(),
            self.ui.dateEdit_reservation_date.date().day(),
        ).weekday()

        week_day_name = date_utils.get_weekday_name(current_week_day)

        return week_day_name

    def _read_timeline(self):
        self._set_schedule_table()
        self._set_calendar()
        self._set_reservation_tool_button(False)
        self._read_reservation_list()

    def _set_schedule_table(self):
        self._set_schedule_table_header()
        self._set_schedule_table_color()
        self._set_schedule_data()
        self._set_off_day_list()

    def _get_massager_off_day_list(self, reservation_date, period, massager):
        off_day = False
        start_date = f'{reservation_date} 00:00:00'
        end_date = f'{reservation_date} 23:59:59'

        sql = f'''
            SELECT * FROM massage_off_day_list
            WHERE
                (OffDate BETWEEN "{start_date}" AND "{end_date}") AND
                (Period = "{period}") AND
                (Massager = "{massager}" OR Massager IS NULL)
        '''
        rows = self.massage_database.select_record(sql)
        if len(rows) > 0:
            off_day = True

        return off_day

    def _set_off_day_list(self):
        reservation_date = self.ui.dateEdit_reservation_date.date().toPyDate()
        period = self._get_period()
        for row_no in range(self.ui.tableWidget_schedule.rowCount(), 1, -1):
            item = self.ui.tableWidget_schedule.item(row_no, 1)
            if item is None:
                continue

            massager = item.text()
            if self._get_massager_off_day_list(reservation_date, period, massager):
                self.ui.tableWidget_schedule.removeRow(row_no)

    def _set_schedule_data(self):
        start_date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd 23:59:59')
        period = self._get_period()

        sql = f'''
            SELECT * FROM massage_cases
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Period = "{period}" AND
                InsType = "自費" AND
                TreatType = "養生館" AND
                Massager IS NOT NULL AND LENGTH(Massager) > 0
            ORDER BY CaseDate
        '''
        rows = self.massage_database.select_record(sql)
        for row in rows:
            self._set_medical_record_timeline(row)

    def _get_massager_color(self, massager):
        color_list = [
            QtGui.QColor('#F8BBD0'),
            QtGui.QColor('#F48FB1'),
            QtGui.QColor('#F06292'),

            QtGui.QColor('#E1BEE7'),
            QtGui.QColor('#CE93D8'),
            QtGui.QColor('#BA68C8'),

            QtGui.QColor('#FFECB3'),
            QtGui.QColor('#FFF176'),
            QtGui.QColor('#FDD835'),

            QtGui.QColor('#DCEDC8'),
            QtGui.QColor('#C5E1A5'),
            QtGui.QColor('#AED581'),

            QtGui.QColor('#B2EBF2'),
            QtGui.QColor('#80DEEA'),
            QtGui.QColor('#4DD0E1'),
        ]

        massager_list = personnel_utils.get_person(self.massage_database, '推拿師父')

        color_dict = {}
        for item_no, name in enumerate(massager_list):
            color_dict[name] = color_list[item_no]

        return color_dict[massager]

    def _set_medical_record_timeline(self, row):
        massager = string_utils.xstr(row['Massager'])
        massager_row_no = self._get_row_no(massager)
        if massager_row_no is None:
            return

        start_time_col_no = self._get_col_no(row['CaseDate'], 'start')
        if start_time_col_no is None:
            return

        end_time_col_no = self._get_col_no(row['FinishDate'], 'end')

        interval = end_time_col_no - start_time_col_no + 1
        name = string_utils.xstr(row['Name'])
        color = self._get_massager_color(massager)

        self.ui.tableWidget_schedule.setSpan(
            massager_row_no, start_time_col_no, 1, interval
        )
        self.ui.tableWidget_schedule.setItem(
            massager_row_no, start_time_col_no,
            QtWidgets.QTableWidgetItem(name)
        )
        item = self.ui.tableWidget_schedule.item(massager_row_no, start_time_col_no)
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        item.setBackground(color)

    def _get_row_no(self, massager):
        massager_row_no = None

        for row_no in range(2, self.ui.tableWidget_schedule.rowCount()):
            item = self.ui.tableWidget_schedule.item(row_no, 1)
            if item is None:
                continue

            if item.text() == massager:
                massager_row_no = row_no
                break

        return massager_row_no

    def _get_col_no(self, case_date, time_type):
        time_col_no = None

        case_hour = case_date.time().strftime('%H')
        if number_utils.get_integer(case_hour) >= self._get_start_hour() + 5:
            return self.ui.tableWidget_schedule.columnCount() - 1

        case_minute = case_date.time().strftime('%M')
        for col_no in range(self.ui.tableWidget_schedule.columnCount()):
            item = self.ui.tableWidget_schedule.item(0, col_no)
            if item is None:
                continue

            if item.text()[-1] != '時':
                continue

            hour = item.text().split('時')[0]
            hour_no = f'{hour:0>2}'
            if case_hour == hour_no:
                for time_col in range(col_no, col_no + self.interval+1):
                    item = self.ui.tableWidget_schedule.item(1, time_col)
                    if item is None:
                        continue

                    if case_minute == item.text():
                        time_col_no = time_col
                        break

        if time_col_no is not None and time_type == 'end':
            time_col_no -= 1

        return time_col_no

    def _get_start_hour(self):
        if self.ui.radioButton_period2.isChecked():
            start_hour = 13
        elif self.ui.radioButton_period3.isChecked():
            start_hour = 18
        else:
            start_hour = 8

        return start_hour

    def _set_schedule_table_header(self):
        self.ui.tableWidget_schedule.clearSelection()
        self.ui.tableWidget_schedule.clearSpans()

        massager_list = personnel_utils.get_person(self.massage_database, '推拿師父')
        row_count = len(massager_list) + 2

        hour = 5
        column_count = hour * self.interval + 2

        self.ui.tableWidget_schedule.clear()
        self.ui.tableWidget_schedule.setColumnCount(column_count)
        self.ui.tableWidget_schedule.setRowCount(row_count)

        self.ui.tableWidget_schedule.setColumnWidth(0, 25)
        self.ui.tableWidget_schedule.setColumnWidth(1, 110)
        self.ui.tableWidget_schedule.setSpan(0, 0, 1, 2)
        self.ui.tableWidget_schedule.setItem(
            0, 0,
            QtWidgets.QTableWidgetItem('預約時間')
        )
        item = self.ui.tableWidget_schedule.item(0, 0)
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        item.setBackground(QtGui.QColor('lightgray'))
        item.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tableWidget_schedule.setItem(
            1, 0,
            QtWidgets.QTableWidgetItem('序')
        )
        item = self.ui.tableWidget_schedule.item(1, 0)
        item.setBackground(QtGui.QColor('lightgray'))
        item.setFlags(QtCore.Qt.ItemIsEnabled)

        self.ui.tableWidget_schedule.setItem(
            1, 1,
            QtWidgets.QTableWidgetItem('推拿師父')
        )
        item = self.ui.tableWidget_schedule.item(1, 1)
        item.setBackground(QtGui.QColor('lightgray'))
        item.setFlags(QtCore.Qt.ItemIsEnabled)

        start_hour = self._get_start_hour()
        start_col = 2
        start_row = 2
        interval_hour = start_hour
        row_no = 0
        for i in range(1, hour+1):
            col_no = (i-1) * self.interval + start_col
            self.ui.tableWidget_schedule.setSpan(row_no, col_no, 1, self.interval)
            self.ui.tableWidget_schedule.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(f'{interval_hour:0>2}時')
            )
            item = self.ui.tableWidget_schedule.item(row_no, col_no)
            item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setBackground(QtGui.QColor('lightgray'))

            interval_hour += 1

        interval_minute = 0
        row_no = 1
        for col_no in range(start_col, self.ui.tableWidget_schedule.columnCount()):
            self.ui.tableWidget_schedule.setColumnWidth(col_no, 30)
            self.ui.tableWidget_schedule.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(f'{interval_minute:0>2}')
            )
            item = self.ui.tableWidget_schedule.item(row_no, col_no)
            item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            item.setBackground(QtGui.QColor('lightgray'))

            interval_minute += self.interval_time
            if interval_minute >= 60:
                interval_minute = 0

        for item_no, massager in enumerate(massager_list):
            sequence = item_no + 1
            row_no = item_no + start_row
            color = self._get_massager_color(massager)
            data = [
                string_utils.xstr(sequence),
                string_utils.xstr(massager),
            ]
            for col_no in range(len(data)):
                self.ui.tableWidget_schedule.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(data[col_no])
                )
                item = self.ui.tableWidget_schedule.item(row_no, col_no)
                item.setFlags(QtCore.Qt.ItemIsEnabled)
                item.setBackground(color)

    def _set_schedule_table_color(self):
        for row_no in range(2, self.ui.tableWidget_schedule.rowCount()):
            for col_no in range(2, self.ui.tableWidget_schedule.columnCount()):
                self.ui.tableWidget_schedule.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem('')
                )
                item = self.ui.tableWidget_schedule.item(row_no, col_no)
                hour = self._get_hour(col_no)
                if hour % 2 == 1:
                    item.setBackground(QtGui.QColor('#F2F3F4'))

    def _set_calendar(self):
        for i in range(0, self.ui.tableWidget_calendar.columnCount()):
            self.ui.tableWidget_calendar.setColumnWidth(i, 84)

        for i in range(0, self.ui.tableWidget_calendar.rowCount()):
            self.ui.tableWidget_calendar.setRowHeight(i, 108)

        calendar_list = {
            0:  [0, 0], 1:  [0, 1], 2:  [0, 2], 3:  [0, 3], 4:  [0, 4], 5:  [0, 5], 6:  [0, 6],
            7:  [1, 0], 8:  [1, 1], 9:  [1, 2], 10: [1, 3], 11: [1, 4], 12: [1, 5], 13: [1, 6],
            14: [2, 0], 15: [2, 1], 16: [2, 2], 17: [2, 3], 18: [2, 4], 19: [2, 5], 20: [2, 6],
            21: [3, 0], 22: [3, 1], 23: [3, 2], 24: [3, 3], 25: [3, 4], 26: [3, 5], 27: [3, 6],
            28: [4, 0], 29: [4, 1], 30: [4, 2], 31: [4, 3], 32: [4, 4], 33: [4, 5], 34: [4, 6],
            35: [5, 0], 36: [5, 1], 37: [5, 2], 38: [5, 3], 39: [5, 4], 40: [5, 5], 41: [5, 6],
        }

        year = self.ui.dateEdit_reservation_date.date().year()
        month = self.ui.dateEdit_reservation_date.date().month()

        self.ui.label_calendar.setText(f'<b>{year}</b>年<b>{month}</b>月份 預約狀況一覽表')

        start_day = datetime.datetime(year, month, 1).weekday()
        if start_day == 6:
            start_day = 0
        else:
            start_day += 1

        week_list = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
        period_list = ['日期', '早班', '午班', '晚班']

        self.ui.tableWidget_calendar.clear()
        for i in range(len(week_list)):
            self.ui.tableWidget_calendar.setHorizontalHeaderItem(
                i, QtWidgets.QTableWidgetItem(week_list[i])
            )
        for i in range(self.ui.tableWidget_calendar.rowCount()):
            self.ui.tableWidget_calendar.setVerticalHeaderItem(
                i, QtWidgets.QTableWidgetItem('\n'.join(period_list))
            )

        last_day = calendar.monthrange(year, month)[1]
        current_month = datetime.date.today().month
        today = datetime.date.today().day

        for i in range(0, last_day):
            day = i + 1
            reservation_date = f'{year}-{month}-{day}'
            reservation1 = self._get_reservation_status(reservation_date, '早班')
            reservation2 = self._get_reservation_status(reservation_date, '午班')
            reservation3 = self._get_reservation_status(reservation_date, '晚班')

            row_no = calendar_list[start_day + i][0]
            col_no = calendar_list[start_day + i][1]
            content = f'{day}\n{reservation1}\n{reservation2}\n{reservation3}'
            self.ui.tableWidget_calendar.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(content)
            )

            color = 'white'
            if current_month == month and i == today - 1:
                color = 'lightSteelBlue'
            elif calendar_list[start_day+i][1] == 0:
                color = '#EBDEF0'

            self.ui.tableWidget_calendar.item(row_no, col_no).setBackground(QtGui.QColor(color))

    def _get_off_day_list(self, reservation_date, period):
        off_day = False
        start_date = f'{reservation_date} 00:00:00'
        end_date = f'{reservation_date} 23:59:59'

        sql = f'''
            SELECT * FROM massage_off_day_list
            WHERE
                (OffDate BETWEEN "{start_date}" AND "{end_date}") AND
                (Period = "{period}") AND
                (Massager IS NULL)
        '''
        rows = self.massage_database.select_record(sql)
        if len(rows) > 0:
            off_day = True

        return off_day

    def _get_reservation_status(self, reservation_date, period):
        status = ''

        if self._get_off_day_list(reservation_date, period):
            return '暫停預約'

        start_date = f'{reservation_date} 00:00:00'
        end_date = f'{reservation_date} 23:59:59'
        sql = f'''
            SELECT MassageCaseKey FROM massage_cases
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (Period = "{period}") AND
                InsType = "自費" AND
                TreatType = "養生館" AND
                Massager IS NOT NULL AND LENGTH(Massager) > 0
        '''
        rows = self.massage_database.select_record(sql)
        reservation_count = len(rows)

        if reservation_count > 0:
            status = f'預約{reservation_count}人'

        return status

    def _set_reservation_tool_button(self, enabled):
        self.ui.action_add_reservation.setEnabled(enabled)
        self.ui.action_modify_reservation.setEnabled(enabled)
        self.ui.action_cancel_reservation.setEnabled(enabled)
        self.ui.action_print_reservation.setEnabled(enabled)

    def _schedule_item_selection_changed(self):
        self._set_reservation_tool_button(False)

        current_row = self.ui.tableWidget_schedule.currentRow()
        current_column = self.ui.tableWidget_schedule.currentColumn()
        item = self.ui.tableWidget_schedule.item(current_row, current_column)
        if item is not None and item.text() != '':
            self.ui.action_add_reservation.setEnabled(False)
            self.ui.action_modify_reservation.setEnabled(True)
            self.ui.action_cancel_reservation.setEnabled(True)
            self.ui.action_print_reservation.setEnabled(True)
        elif self._get_massager() is not None:
            self.ui.action_add_reservation.setEnabled(True)

            left_column = self.ui.tableWidget_schedule.selectedRanges()[0].leftColumn()
            right_column = self.ui.tableWidget_schedule.selectedRanges()[-1].rightColumn()
            for col_no in range(left_column, right_column+1):
                select_item = self.ui.tableWidget_schedule.item(current_row, col_no)
                if select_item is not None and select_item.text() != '':
                    self._set_reservation_tool_button(False)

    def _get_period(self):
        if self.ui.radioButton_period1.isChecked():
            period = '早班'
        elif self.ui.radioButton_period2.isChecked():
            period = '午班'
        elif self.ui.radioButton_period3.isChecked():
            period = '晚班'
        else:
            period = '早班'

        return period

    def _get_schedule_massage_case_key(self):
        item = self.ui.tableWidget_schedule.item(
            self.ui.tableWidget_schedule.currentRow(),
            self.ui.tableWidget_schedule.currentColumn(),
        )
        if item is None:
            return None

        patient_name = item.text()
        massager = self._get_massager()
        reservation_date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd')
        start_time, _ = self._get_period_time()
        case_date = f'{reservation_date} {start_time}'
        period = self._get_period()

        sql = f'''
            SELECT MassageCaseKey FROM massage_cases
            WHERE
                Name = "{patient_name}" AND
                CaseDate = "{case_date}" AND
                Period = "{period}" AND
                InsType = "自費" AND
                TreatType = "養生館" AND
                Massager = "{massager}"
        '''
        rows = self.massage_database.select_record(sql)
        if len(rows) <= 0:
            return None

        case_key = rows[0]['MassageCaseKey']

        return case_key

    def _get_case_key(self):
        tab_name = self.ui.tabWidget_reservation.tabText(self.ui.tabWidget_reservation.currentIndex())
        if tab_name == '預約一覽表':
            case_key = self._get_schedule_massage_case_key()
        else:
            case_key = self.table_widget_reservation_list.field_value(0)

        return case_key

    def _modify_reservation(self):
        case_key = self._get_case_key()
        if case_key is None:
            return

        dialog = dialog_utils.get_dialog_massage_reservation(
            self, self.massage_database, self.system_settings, None, None, None, None, None, case_key,
        )
        try:
            if dialog.exec_():
                self._read_timeline()
        finally:
            dialog.close_all()
            dialog.deleteLater()

    def _cancel_reservation(self):
        case_key = self._get_case_key()
        if case_key is None:
            return

        msg_box = dialog_utils.get_message_box(
            '刪除預約', QMessageBox.Warning,
            '<font size="5" color="red"><b>確定刪除預約資料"?</b></font>',
            '注意！刪除預約後, 將無法回復!'
        )
        cancel_reservation = msg_box.exec_()
        if not cancel_reservation:
            return

        self.massage_databasedatabase.exec_sql(f'''
            DELETE FROM massage_cases
            WHERE
                MassageCaseKey = {case_key}
        ''')
        self.massage_database.exec_sql(f'''
            DELETE FROM prescript
            WHERE
                MassageCaseKey = {case_key}
        ''')
        self.massage_database.exec_sql(f'''
            DELETE FROM massage_payment
            WHERE
                MassageMassageCaseKey = {case_key}
        ''')
        self._read_timeline()

    # 新增預約
    def _add_reservation(self):
        massager = self._get_massager()
        reservation_date = self.ui.dateEdit_reservation_date.date().toString('yyyy-MM-dd')
        start_time, end_time = self._get_period_time()
        period = self._get_period()

        dialog = dialog_utils.get_dialog_massage_reservation(
            self, self.database, self.system_settings, massager,
            reservation_date, period, start_time, end_time, None,
        )
        try:
            if dialog.exec_():
                self._read_timeline()
        finally:
            dialog.close_all()
            dialog.deleteLater()

    def _get_massager(self):
        if self.ui.tableWidget_schedule.currentRow() <= 1:
            return None

        if self.ui.tableWidget_schedule.currentColumn() <= 1:
            return None

        if len(self.ui.tableWidget_schedule.selectedRanges()) <= 0:
            return None

        row_no = self.ui.tableWidget_schedule.selectedRanges()[0].topRow()
        last_row_no = self.ui.tableWidget_schedule.selectedRanges()[-1].topRow()
        if row_no != last_row_no:
            return None

        return self.ui.tableWidget_schedule.item(row_no, 1).text()

    def _get_hour(self, col_no):
        start_hour_no = self._get_start_hour()
        start_no = 2

        hour1 = [i for i in range(start_no, self.interval+start_no)]
        hour2 = [i for i in range(hour1[-1]+1, hour1[-1] + self.interval+1)]
        hour3 = [i for i in range(hour2[-1]+1, hour2[-1] + self.interval+1)]
        hour4 = [i for i in range(hour3[-1]+1, hour3[-1] + self.interval+1)]
        hour5 = [i for i in range(hour4[-1]+1, hour4[-1] + self.interval+1)]
        if col_no in hour1:
            start_hour = start_hour_no
        elif col_no in hour2:
            start_hour = start_hour_no + 1
        elif col_no in hour3:
            start_hour = start_hour_no + 2
        elif col_no in hour4:
            start_hour = start_hour_no + 3
        elif col_no in hour5:
            start_hour = start_hour_no + 4
        else:
            return None

        return start_hour

    def _get_period_time(self):
        column_no = self.ui.tableWidget_schedule.selectedRanges()[0].leftColumn()
        last_column_no = self.ui.tableWidget_schedule.selectedRanges()[-1].rightColumn()

        start_hour = self._get_hour(column_no)
        end_hour = self._get_hour(last_column_no)

        start_minute = self.ui.tableWidget_schedule.item(1, column_no).text()
        try:
            end_minute = self.ui.tableWidget_schedule.item(1, last_column_no+1).text()
            if end_minute == '00':
                end_hour += 1
        except AttributeError:
            end_hour += 1
            end_minute = '00'

        start_time = f'{start_hour:0>2}:{start_minute:0>2}'
        end_time = f'{end_hour:0>2}:{end_minute:0>2}'

        return start_time, end_time

    def _calendar_changed(self):
        current_row = self.ui.tableWidget_calendar.currentRow()
        current_column = self.ui.tableWidget_calendar.currentColumn()
        item = self.ui.tableWidget_calendar.item(
            current_row, current_column
        )

        if item is None:
            return

        year = int(self.ui.dateEdit_reservation_date.date().year())
        month = int(self.ui.dateEdit_reservation_date.date().month())
        day = int(item.text().split('\n')[0])
        self.ui.dateEdit_reservation_date.setDate(QtCore.QDate(year, month, day))

    def _schedule_double_clicked(self):
        if not self.ui.action_modify_reservation.isEnabled():
            return

        self._modify_reservation()

    def _read_reservation_list(self):
        self.ui.tableWidget_reservation_list.setRowCount(1)

        start_date = self.ui.dateEdit_start_date.date().toString('yyyy-MM-dd 00:00:00')
        end_date = self.ui.dateEdit_end_date.date().toString('yyyy-MM-dd 23:59:59')

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql = f'''
            SELECT
                massage_cases.*, massage_customer.Telephone, massage_customer.Cellphone
            FROM massage_cases
                LEFT JOIN massage_customer
                ON massage_cases.MassageCustomerKey = massage_customer.MassageCustomerKey
            WHERE
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                massage_cases.InsType = "自費" AND
                massage_cases.TreatType = "養生館"
            ORDER BY CaseDate, FIELD(Period, {period_list}), MassageCaseKey
        '''
        self.table_widget_reservation_list.set_db_data(sql, self._set_table_data)
        if self.ui.tableWidget_reservation_list.rowCount() > 0:
            self._set_reservation_tool_button(True)
        else:
            self._set_reservation_tool_button(False)

    def _set_table_data(self, row_no, row):
        start_time = row['CaseDate'].strftime('%H:%M')
        end_time = row['FinishDate'].strftime('%H:%M')
        time = f'{start_time} - {end_time}'

        reservation_list_data = [
            string_utils.xstr(row['MassageCaseKey']),
            string_utils.xstr(row['CaseDate'].date()),
            time,
            string_utils.xstr(row['Period']),
            number_utils.get_integer(row['MassageCustomerKey']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Telephone']),
            string_utils.xstr(row['Cellphone']),
            string_utils.xstr(row['Massager']),
            string_utils.xstr(row['Registrar']),
            number_utils.get_integer(row['TotalFee']),
            number_utils.get_integer(row['ReceiptFee']),
        ]

        for col_no in range(len(reservation_list_data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, reservation_list_data[col_no])
            self.ui.tableWidget_reservation_list.setItem(row_no, col_no, item)
            if col_no in [4, 10, 11]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [3]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

    def _tab_changed(self, i):
        self.tab_name = self.ui.tabWidget_reservation.tabText(i)

        if self.tab_name == '預約一覽表':
            self._read_timeline()
        else:
            self._read_reservation_list()

            self.ui.action_add_reservation.setEnabled(False)
            self.ui.action_modify_reservation.setEnabled(False)
            self.ui.action_cancel_reservation.setEnabled(False)
            self.ui.action_print_reservation.setEnabled(False)

            if self.table_widget_reservation_list.row_count() > 0:
                enabled = True
            else:
                enabled = False

            self.ui.action_modify_reservation.setEnabled(enabled)
            self.ui.action_cancel_reservation.setEnabled(enabled)
            self.ui.action_print_reservation.setEnabled(enabled)

    def _previous_calendar(self):
        current_date = self.ui.dateEdit_reservation_date.date().toPyDate()
        self.ui.dateEdit_reservation_date.setDate(
            date_utils.add_months(current_date, -1)
        )

    def _next_calendar(self):
        current_date = self.ui.dateEdit_reservation_date.date().toPyDate()
        self.ui.dateEdit_reservation_date.setDate(
            date_utils.add_months(current_date, 1)
        )

    def _off_day_setting(self):
        dialog = dialog_utils.get_dialog_off_day_setting(
            self, self.database, self.system_settings, 'massage_off_day_list',
        )

        dialog.exec_()
        dialog.deleteLater()
        self._read_timeline()

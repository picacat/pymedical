# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QMessageBox, QInputDialog
import datetime

from libs import system_utils
from libs import ui_utils
from libs import class_utils
from libs import dialog_utils
from libs import personnel_utils
from libs import patient_utils
from libs import string_utils
from libs import number_utils
from libs import date_utils

SUNDAY_COLOR = QtGui.QColor('#F5F5F5')  # 星期日
TODAY_COLOR = QtGui.QColor('#F0F8FF')  # 今天
OFF_COLOR = QtGui.QColor('#F6DDE4')  # 暫停預約
TREATED_COLOR = QtGui.QColor('#f4f0ec')  # 已就診
FIRST_VISIT_COLOR = QtGui.QColor('#b0e0e6')  # 初診
RESERVED_COLOR = QtGui.QColor('#ffe4b5')  # 預約未報到
REMARK_COLOR = QtGui.QColor('#7dcea0')  # 預約未報到


# 物理治療預約主畫面
class PhysiotherapySchedule(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PhysiotherapySchedule, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.current_date = datetime.datetime.now()
        self.week_list = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        self.time_list = self.parent.time_list
        self.week_count = 2

        self._set_ui()
        self._set_signal()
        self._set_week_number()
        self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHYSIOTHERAPY_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_calendar = class_utils.get_table_widget(
            self.ui.tableWidget_calendar, self.database
        )
        self.ui.tableWidget_calendar.setDragEnabled(True)
        self.ui.tableWidget_calendar.setAcceptDrops(True)
        self.ui.tableWidget_calendar.setDragDropOverwriteMode(False)

        physiotherapy_list = personnel_utils.get_person(self.database, '物理治療師')
        ui_utils.set_combo_box(self.ui.comboBox_physiotherapy, physiotherapy_list)
        # self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self._set_table_width()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115, 115]
        self.table_widget_calendar.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_previous.clicked.connect(self._set_previous_week)
        self.ui.toolButton_next.clicked.connect(self._set_next_week)
        self.ui.tableWidget_calendar.doubleClicked.connect(self._open_booking_dialog)
        self.ui.tableWidget_calendar.itemSelectionChanged.connect(self._calendar_selection_changed)
        self.ui.comboBox_physiotherapy.currentTextChanged.connect(self._read_data)
        self.ui.toolButton_cancel_reservation.clicked.connect(self._cancel_reservation)
        self.ui.toolButton_stop_reservation.clicked.connect(self._stop_reservation)
        self.ui.toolButton_copy_to.clicked.connect(self._copy_to)
        self.ui.toolButton_move_to.clicked.connect(self._move_to)
        self.ui.toolButton_refresh.clicked.connect(self._refresh_calendar)
        self.ui.toolButton_get_calendar.clicked.connect(self._set_custom_calendar)
        self.ui.tableWidget_calendar.dropEvent = self.calendar_drop_event

    def _popup_menu(self, current_row_no, current_col_no, target_row, target_col):
        m = QtWidgets.QMenu()
        move_action = QtWidgets.QAction('移到此處', self)
        move_action.triggered.connect(
            lambda: self._move_cell(current_row_no, current_col_no, target_row, target_col))
        duplicate_action = QtWidgets.QAction('複製到此處', self)
        duplicate_action.triggered.connect(
            lambda: self._duplicate_cell(current_row_no, current_col_no, target_row, target_col))
        cancel_action = QtWidgets.QAction('取消', self)
        m.addAction(move_action)
        m.addAction(duplicate_action)
        m.addAction(cancel_action)
        m.exec_(QtGui.QCursor.pos())

    def calendar_drop_event(self, event):
        current_row_no = self.ui.tableWidget_calendar.currentRow()
        current_col_no = self.ui.tableWidget_calendar.currentColumn()
        current_item = self.tableWidget_calendar.item(current_row_no, current_col_no)
        if current_item.text() in ['', None]:
            return

        current_table_widget = event.source()
        target_item = current_table_widget.itemAt(event.pos())

        target_row = target_item.row()
        target_col = target_item.column()
        drop_item_text = self.tableWidget_calendar.item(target_row, target_col).text()
        if drop_item_text != '':
            return

        row = self._get_row_data(current_row_no, current_col_no)
        if row is None:
            return

        self._set_schedule_data(target_row, target_col, row)
        self._popup_menu(current_row_no, current_col_no, target_row, target_col)
        self._read_data()

        self.ui.tableWidget_calendar.setCurrentCell(target_row, target_col)

    def _move_cell(self, current_row_no, current_col_no, target_row, target_col):
        date = self.tableWidget_calendar.horizontalHeaderItem(current_col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(current_row_no).text()
        dest_date = self.tableWidget_calendar.horizontalHeaderItem(target_col).text().split('\n')[0]
        dest_time = self.tableWidget_calendar.verticalHeaderItem(target_row).text()

        self._move_schedule(date, time, dest_date, dest_time)

    def _move_schedule(self, current_date, current_time, dest_date, dest_time):
        if self._is_schedule_exists(dest_date, dest_time):
            system_utils.show_message_box(
                QMessageBox.Critical,
                '重複預約',
                '<font color="red"><h3>該時段已有預約, 無法複製!</h3></font>',
                '請選擇其他日期與時間.'
            )
            return

        physiotherapy = self.ui.comboBox_physiotherapy.currentText()

        sql = f'''
            UPDATE physiotherapy_schedule
            SET
                PhysiotherapyDate = "{dest_date}",
                PhysiotherapyTime = "{dest_time}",
                ArrivalTime = "{dest_time}"
            WHERE
                PhysiotherapyDate = "{current_date}" AND PhysiotherapyTime = "{current_time}" AND
                Physiotherapy = "{physiotherapy}"
        '''
        self.database.exec_sql(sql)

    def _duplicate_cell(self, current_row_no, current_col_no, target_row, target_col):
        date = self.tableWidget_calendar.horizontalHeaderItem(current_col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(current_row_no).text()
        dest_date = self.tableWidget_calendar.horizontalHeaderItem(target_col).text().split('\n')[0]
        dest_time = self.tableWidget_calendar.verticalHeaderItem(target_row).text()

        self._duplicate_schedule(date, time, dest_date, dest_time)

    def _is_schedule_exists(self, date, time):
        physiotherapy = self.ui.comboBox_physiotherapy.currentText()

        sql = f'''
            SELECT * FROM physiotherapy_schedule
            WHERE
                PhysiotherapyDate = "{date}" AND PhysiotherapyTime = "{time}" AND
                Physiotherapy = "{physiotherapy}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            return True
        else:
            return False

    def _duplicate_schedule(self, current_date, current_time, dest_date, dest_time):
        if self._is_schedule_exists(dest_date, dest_time):
            system_utils.show_message_box(
                QMessageBox.Critical,
                '重複預約',
                '<font color="red"><h3>該時段已有預約, 無法複製!</h3></font>',
                '請選擇其他日期與時間.'
            )
            return

        rows = self._get_schedule_data(current_date, current_time)
        if len(rows) <= 0:
            return

        row = rows[0]

        remark = string_utils.xstr(row['Remark'])
        if '(已報到)' in remark and '(初診)' in remark:
            remark = remark.replace('(初診)', '')

        remark = remark.replace('(已報到)', '')

        row['PhysiotherapyDate'] = date_utils.str_to_date(dest_date)
        row['PhysiotherapyTime'] = dest_time
        row['ArrivalTime'] = dest_time
        row['ReceiptFee'] = 0

        fields = [
            'PhysiotherapyDate', 'PhysiotherapyTime', 'Physiotherapy', 'PatientKey', 'ArrivalTime',
            'TreatFee', 'ReceiptFee', 'Remark'
        ]
        data = [
            row['PhysiotherapyDate'], row['PhysiotherapyTime'], row['Physiotherapy'],
            row['PatientKey'], row['ArrivalTime'], row['TreatFee'], row['ReceiptFee'],
            remark,
        ]
        self.database.insert_record('physiotherapy_schedule', fields, data)

    def _calendar_selection_changed(self):
        row_no = self.ui.tableWidget_calendar.currentRow()
        col_no = self.ui.tableWidget_calendar.currentColumn()
        item = self.tableWidget_calendar.item(row_no, col_no).text()
        if item in [None, '']:
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_cancel_reservation.setText('取消預約')
        self.ui.toolButton_cancel_reservation.setEnabled(enabled)
        self.ui.toolButton_copy_to.setEnabled(enabled)
        self.ui.toolButton_move_to.setEnabled(enabled)
        self.ui.toolButton_stop_reservation.setEnabled(not enabled)

        if item == '暫停預約':
            self.ui.toolButton_cancel_reservation.setText('取消暫停')

    def _set_week_number(self):
        # current_year = datetime.datetime.now().year
        # current_month = datetime.datetime.now().month
        current_year = self.current_date.year
        current_month = self.current_date.month

        first_day = datetime.date(int(current_year), int(current_month), 1).isocalendar()
        self.current_week_no = first_day[1]
        self.week_no = self.current_week_no

    def _set_next_week(self):
        self.week_no += 1
        self._read_data()

    def _set_previous_week(self):
        self.week_no -= 1
        # if self.week_no < self.current_week_no:
        #     self.week_no = self.current_week_no

        self._read_data()

    def _refresh_calendar(self):
        self.current_date = datetime.datetime.now()

        self._set_week_number()
        self._read_data()

    def _read_data(self):
        self._set_calendar()
        self._clear_data()
        self._set_data()

    def _set_calendar(self):
        week_days = 7
        weekday = self.current_date.weekday()
        start_no = (self.week_no - self.current_week_no) * self.week_count * week_days
        end_no = start_no + self.week_count * week_days

        header_list = []
        for i in range(start_no, end_no):
            weekday_no = i % week_days 
            # case_date = datetime.datetime.now().date() - datetime.timedelta(days=weekday-i)
            case_date = self.current_date.date() - datetime.timedelta(days=weekday-i)
            header_list.append(case_date.strftime('%Y-%m-%d') + '\n' + str(self.week_list[weekday_no]))

        v_header_list = []
        for time in self.time_list:
            v_header_list.append(time)

        self.ui.tableWidget_calendar.clear()
        self.ui.tableWidget_calendar.setRowCount(len(self.time_list))
        self.ui.tableWidget_calendar.setColumnCount(self.week_count * week_days)  # 2 weeks
        self.ui.tableWidget_calendar.setHorizontalHeaderLabels(header_list)
        self.ui.tableWidget_calendar.setVerticalHeaderLabels(v_header_list)

    def _get_calendar_datetime(self):
        row_no = self.ui.tableWidget_calendar.currentRow()
        col_no = self.ui.tableWidget_calendar.currentColumn()
        date = self.tableWidget_calendar.horizontalHeaderItem(col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(row_no).text()
        text = self.tableWidget_calendar.item(row_no, col_no)
        if text is not None:
            text = text.text()

        return date, time, text

    def _get_physiotherapy_data(self):
        current_date, current_time, text = self._get_calendar_datetime()
        physiotherapy = self.ui.comboBox_physiotherapy.currentText()

        return current_date, current_time, physiotherapy, text

    def _open_booking_dialog(self):
        current_date, current_time, physiotherapy, text = self._get_physiotherapy_data()
        if text == '暫停預約':
            return

        dialog = dialog_utils.get_dialog_physiotherapy_booking(
            self, self.database, self.system_settings,
            current_date, current_time, physiotherapy)

        dialog.exec_()
        self._read_data()

        dialog.deleteLater()

    def _clear_data(self):
        row_count = self.ui.tableWidget_calendar.rowCount()
        col_count = self.ui.tableWidget_calendar.columnCount()

        for row_no in range(row_count):
            for col_no in range(col_count):
                item = QtWidgets.QTableWidgetItem()
                item.setData(QtCore.Qt.EditRole, None)
                self.ui.tableWidget_calendar.setItem(row_no, col_no, item)

    def _set_data(self):
        today = datetime.date.today().strftime('%Y-%m-%d')

        row_count = self.ui.tableWidget_calendar.rowCount()
        col_count = self.ui.tableWidget_calendar.columnCount()

        for row_no in range(row_count):
            for col_no in range(col_count):
                date = self.tableWidget_calendar.horizontalHeaderItem(col_no).text().split('\n')[0]
                if (col_no + 1) % 7 == 0:  # 星期日底色
                    self.ui.tableWidget_calendar.item(row_no, col_no).setBackground(SUNDAY_COLOR)
                elif date == today:  # 今日底色
                    self.ui.tableWidget_calendar.item(row_no, col_no).setBackground(TODAY_COLOR)

                row = self._get_row_data(row_no, col_no)
                if row is None:
                    continue

                self._set_schedule_data(row_no, col_no, row)

    def _get_row_data(self, row_no, col_no):
        date = self.tableWidget_calendar.horizontalHeaderItem(col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(row_no).text()
        rows = self._get_schedule_data(date, time)

        if len(rows) <= 0:
            return None
        else:
            return rows[0]

    def _set_schedule_data(self, row_no, col_no, row):
        remark = string_utils.xstr(row['Remark'])

        if remark == '暫停預約':
            display_label = remark
        else:
            patient_row = patient_utils.get_patient_row(self.database, row['PatientKey'])
            if '(初診)' in remark:
                temp_patient_row = patient_utils.get_temp_patient(self.database, row['PatientKey'], '*')
                if temp_patient_row is not None:
                    patient_row = temp_patient_row

            if patient_row is not None:
                name = string_utils.xstr(patient_row['Name'])
                arrival_time = '\n' + string_utils.xstr(row['ArrivalTime'])
                receipt_fee = number_utils.get_integer(row["ReceiptFee"])
            else:
                receipt_fee = 0
                arrival_time = ''
                name = '暫停預約'

            display_label = f'{name}{arrival_time}'

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, display_label)
        self.ui.tableWidget_calendar.setItem(row_no, col_no, item)
        self.ui.tableWidget_calendar.item(
            row_no, col_no).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        if remark == '暫停預約':
            color = OFF_COLOR
        elif receipt_fee > 0:       # 已就診
            color = TREATED_COLOR
        elif '(初診)' in remark:     # 初診
            color = FIRST_VISIT_COLOR
        elif remark not in ['', None]:     # 初診
            color = REMARK_COLOR
        else:
            color = RESERVED_COLOR      # 預約中

        self.ui.tableWidget_calendar.item(row_no, col_no).setBackground(color)

    def _get_schedule_data(self, date, time):
        sql = f'''
            SELECT * FROM physiotherapy_schedule
            WHERE
                PhysiotherapyDate = "{date}" AND
                PhysiotherapyTime = "{time}" AND
                Physiotherapy = "{self.ui.comboBox_physiotherapy.currentText()}"
        '''
        rows = self.database.select_record(sql)

        return rows

    def _cancel_reservation(self):
        date, time, physiotherapy, text = self._get_physiotherapy_data()
        if text != '暫停預約':
            msg_box = dialog_utils.get_message_box(
                '取消預約', QMessageBox.Warning,
                '<font size="5" color="red"><b>確定取消此筆預約資料?</b></font>',
                '注意！預約資料取消後, 將無法回復!'
            )
            remove_record = msg_box.exec_()
            if not remove_record:
                return

        sql = f'''
            DELETE FROM physiotherapy_schedule
            WHERE
                PhysiotherapyDate = "{date}" AND
                PhysiotherapyTime = "{time}" AND
                Physiotherapy = "{physiotherapy}"
        '''
        self.database.exec_sql(sql)

        self._read_data()

    def _stop_reservation(self):
        # msg_box = dialog_utils.get_message_box(
        #     '暫停預約', QMessageBox.Warning,
        #     '<font size="5" color="red"><b>確定將此時段設為暫時預約?</b></font>',
        #     '提醒！您可以隨時取消暫停!'
        # )
        # stop_reservation = msg_box.exec_()
        # if not stop_reservation:
        #     return

        date, time, physiotherapy, _ = self._get_physiotherapy_data()
        fields = [
            'PhysiotherapyDate', 'PhysiotherapyTime', 'Physiotherapy', 'Remark'
        ]
        physiotherapy_date = date_utils.str_to_date(date)
        physiotherapy_time = time
        physiotherapy = self.ui.comboBox_physiotherapy.currentText()
        remark = '暫停預約'

        data = [
            physiotherapy_date, physiotherapy_time, physiotherapy, remark,
        ]

        self.database.insert_record('physiotherapy_schedule', fields, data)

        self._read_data()

    def _set_custom_calendar(self):
        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, '開立診斷證明')

        dialog.ui.calendarWidget.setSelectedDate(datetime.date.today())

        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_date = dialog.ui.calendarWidget.selectedDate()
        year = current_date.year()
        month = current_date.month()
        day = current_date.day()
        selected_date = f'{year}-{month:0>2}-{day:0>2}'

        current_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d')
        self.current_date = current_date

        self._read_data()

    def _copy_to(self):
        dialog = dialog_utils.get_dialog_schedule(self, self.database, self.system_settings, self.time_list)

        dialog.ui.calendarWidget.setSelectedDate(datetime.datetime.today())

        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_row_no = self.ui.tableWidget_calendar.currentRow()
        current_col_no = self.ui.tableWidget_calendar.currentColumn()
        date = self.tableWidget_calendar.horizontalHeaderItem(current_col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(current_row_no).text()

        selected_date = dialog.get_selected_date()
        selected_time = dialog.get_selected_time()

        self.current_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d')
        self._read_data()

        self._duplicate_schedule(date, time, selected_date, selected_time)
        self._read_data()

    def _move_to(self):
        dialog = dialog_utils.get_dialog_schedule(self, self.database, self.system_settings, self.time_list)

        dialog.ui.calendarWidget.setSelectedDate(datetime.datetime.today())

        if not dialog.exec_():
            dialog.deleteLater()
            return

        current_row_no = self.ui.tableWidget_calendar.currentRow()
        current_col_no = self.ui.tableWidget_calendar.currentColumn()
        date = self.tableWidget_calendar.horizontalHeaderItem(current_col_no).text().split('\n')[0]
        time = self.tableWidget_calendar.verticalHeaderItem(current_row_no).text()

        selected_date = dialog.get_selected_date()
        selected_time = dialog.get_selected_time()

        self.current_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d')
        self._read_data()

        self._move_schedule(date, time, selected_date, selected_time)
        self._read_data()


# 醫師整月值班表
# -*- coding: UTF-8 -*-

import calendar
import datetime

from libs import (alleypin_utils, date_utils, number_utils, system_utils,
                  ui_utils)
from PyQt5 import QtWidgets


# 主視窗
class DialogDoctorMonthSchedule(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogDoctorMonthSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.doctor = args[2]
        self.year = args[3]
        self.month = args[4]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_calendar_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_DOCTOR_MONTH_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        self.setFixedSize(self.size())  # non resizable dialog
        self._set_calendar_table()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_clear_calendar.clicked.connect(self._clear_calendar)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self._save_calendar()
        if self.system_settings.field('alleypin') == 'Y':
            alleypin_utils.set_alleypin_reservation_table(
                self, self.database, self.system_settings, self.year, self.month, self.doctor)
            system_utils.show_message_box(
                QtWidgets.QMessageBox.Information,
                '上傳成功',
                '<font size="5" color="blue"><b>醫師班表全部同步完成.</b></font>',
                '資料上傳成功.'
            )

    def _set_calendar_table(self):
        for i in range(0, self.ui.tableWidget_calendar.columnCount()):
            self.ui.tableWidget_calendar.setColumnWidth(i, 120)

        for i in range(0, self.ui.tableWidget_calendar.rowCount()):
            self.ui.tableWidget_calendar.setRowHeight(i, 109)

        calendar_list = {
            0:  [0, 0], 1:  [0, 1], 2:  [0, 2], 3:  [0, 3], 4:  [0, 4], 5:  [0, 5], 6:  [0, 6],
            7:  [1, 0], 8:  [1, 1], 9:  [1, 2], 10: [1, 3], 11: [1, 4], 12: [1, 5], 13: [1, 6],
            14: [2, 0], 15: [2, 1], 16: [2, 2], 17: [2, 3], 18: [2, 4], 19: [2, 5], 20: [2, 6],
            21: [3, 0], 22: [3, 1], 23: [3, 2], 24: [3, 3], 25: [3, 4], 26: [3, 5], 27: [3, 6],
            28: [4, 0], 29: [4, 1], 30: [4, 2], 31: [4, 3], 32: [4, 4], 33: [4, 5], 34: [4, 6],
            35: [5, 0], 36: [5, 1], 37: [5, 2], 38: [5, 3], 39: [5, 4], 40: [5, 5], 41: [5, 6],
        }

        self.ui.label_calendar.setText(
            f'<b>{self.doctor}</b>醫師 <b>{self.year}</b>年<b>{self.month}</b>月份 醫師班表')

        start_day = datetime.datetime(self.year, self.month, 1).weekday()
        if start_day == 6:
            start_day = 0
        else:
            start_day += 1

        week_list = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

        self.ui.tableWidget_calendar.clear()
        for i in range(len(week_list)):
            self.ui.tableWidget_calendar.setHorizontalHeaderItem(
                i, QtWidgets.QTableWidgetItem(week_list[i])
            )

        last_day = calendar.monthrange(self.year, self.month)[1]
        for i in range(0, last_day):
            day = i + 1
            row_no = calendar_list[start_day + i][0]
            col_no = calendar_list[start_day + i][1]
           
            label = QtWidgets.QLabel(str(day))
            v_layout = QtWidgets.QVBoxLayout()
            v_layout.addWidget(label)

            check_box1 = QtWidgets.QCheckBox()
            check_box1.setText('早班')
            check_box1.clicked.connect(self._check_on_duty)
            v_layout.addWidget(check_box1)

            check_box2 = QtWidgets.QCheckBox()
            check_box2.setText('午班')
            check_box2.clicked.connect(self._check_on_duty)
            v_layout.addWidget(check_box2)

            check_box3 = QtWidgets.QCheckBox()
            check_box3.setText('晚班')
            check_box3.clicked.connect(self._check_on_duty)
            v_layout.addWidget(check_box3)

            widget = QtWidgets.QWidget()
            widget.setLayout(v_layout)

            color = 'white'
            if calendar_list[start_day+i][1] == 0:
                color = '#EBDEF0'

            widget.setStyleSheet(f'background-color: {color}')
            self.ui.tableWidget_calendar.setCellWidget(row_no, col_no, widget)

    def _clear_calendar(self):
        for row_no in range(self.ui.tableWidget_calendar.rowCount()):
            for col_no in range(self.ui.tableWidget_calendar.columnCount()):
                widget = self.ui.tableWidget_calendar.cellWidget(row_no, col_no)
                if widget is None:
                    continue

                check_box_list = widget.findChildren(QtWidgets.QCheckBox)
                check_box1 = check_box_list[0]
                check_box2 = check_box_list[1]
                check_box3 = check_box_list[2]

                check_box1.setChecked(False)
                check_box2.setChecked(False)
                check_box3.setChecked(False)

        self._check_on_duty()

    def _check_on_duty(self):
        for row_no in range(self.ui.tableWidget_calendar.rowCount()):
            for col_no in range(self.ui.tableWidget_calendar.columnCount()):
                widget = self.ui.tableWidget_calendar.cellWidget(row_no, col_no)
                if widget is None:
                    continue

                check_box_list = widget.findChildren(QtWidgets.QCheckBox)
                for check_box in check_box_list:
                    if check_box.isChecked():
                        check_box.setStyleSheet('color:red; font-weight:bold')
                    else:
                        check_box.setStyleSheet(None)

    def _set_calendar_data(self):
        sql = f'''
            SELECT * FROM doctor_month_schedule
            WHERE
                Year = {self.year} AND
                Month = {self.month} AND
                Doctor = "{self.doctor}"
        '''
        doctor_schedule_rows = self.database.select_record(sql)
        if len(doctor_schedule_rows) <= 0:
            self._preset_calendar_by_doctor_schedule()
            self.ui.label_calendar.setText(
                self.ui.label_calendar.text() + \
                '   [<span style="color: red; font-weight: bold;">班表尚未存檔</span>]'
            )
            return

        for row_no in range(self.ui.tableWidget_calendar.rowCount()):
            for col_no in range(self.ui.tableWidget_calendar.columnCount()):
                widget = self.ui.tableWidget_calendar.cellWidget(row_no, col_no)
                if widget is None:
                    continue

                label = widget.findChildren(QtWidgets.QLabel)[0]
                check_box_list = widget.findChildren(QtWidgets.QCheckBox)
                check_box1 = check_box_list[0]
                check_box2 = check_box_list[1]
                check_box3 = check_box_list[2]

                day = number_utils.get_integer(label.text())
                if self._is_doctor_on_schedule(doctor_schedule_rows, day, '早班'):
                    check_box1.setChecked(True)
                if self._is_doctor_on_schedule(doctor_schedule_rows, day, '午班'):
                    check_box2.setChecked(True)
                if self._is_doctor_on_schedule(doctor_schedule_rows, day, '晚班'):
                    check_box3.setChecked(True)

        self._check_on_duty()

    def _is_doctor_on_schedule(self, doctor_schedule_rows, day, period):
        on_duty = False

        for row in doctor_schedule_rows:
            if row['Day'] == day and row['Period'] == period:
                if row['CanReservation'] == 'True':
                    on_duty = True
                else:
                    on_duty = False

                break

        return on_duty

    def _preset_calendar_by_doctor_schedule(self):
        sql = 'SELECT * FROM doctor_schedule'
        doctor_schedule_rows = self.database.select_record(sql)

        for row_no in range(self.ui.tableWidget_calendar.rowCount()):
            for col_no in range(self.ui.tableWidget_calendar.columnCount()):
                widget = self.ui.tableWidget_calendar.cellWidget(row_no, col_no)
                if widget is None:
                    continue

                label = widget.findChildren(QtWidgets.QLabel)[0]
                check_box_list = widget.findChildren(QtWidgets.QCheckBox)
                check_box1 = check_box_list[0]
                check_box2 = check_box_list[1]
                check_box3 = check_box_list[2]

                day = number_utils.get_integer(label.text())
                weekday = datetime.datetime(
                    self.year, self.month, day
                ).weekday()
                weekday_name = date_utils.get_weekday_name(weekday, region='en_US')
                if self._is_doctor_on_duty(doctor_schedule_rows, weekday_name, '早班', self.doctor):
                    check_box1.setChecked(True)
                if self._is_doctor_on_duty(doctor_schedule_rows, weekday_name, '午班', self.doctor):
                    check_box2.setChecked(True)
                if self._is_doctor_on_duty(doctor_schedule_rows, weekday_name, '晚班', self.doctor):
                    check_box3.setChecked(True)

        self._check_on_duty()

    def _is_doctor_on_duty(self, doctor_schedule_rows, weekday, period, doctor):
        on_duty = False

        for row in doctor_schedule_rows:
            if row['Period'] == period and row[weekday] == doctor:
                on_duty = True
                break

        return on_duty

    def _get_schedule_key(self, *args):
        year = args[0][0]
        month = args[0][1]
        day = args[0][2]
        period = args[0][3]
        doctor = args[0][4]

        sql = f'''
            SELECT * FROM doctor_month_schedule
            WHERE
                Year = {year} AND
                Month = {month} AND
                Day = {day} AND
                Period = "{period}" AND
                Doctor = "{doctor}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            schedule_key = None
        else:
            schedule_key = rows[0]['DoctorMonthScheduleKey']

        return schedule_key

    def _save_calendar(self):
        fields = ['Year', 'Month', 'Day', 'Period', 'Doctor', 'CanReservation']
        for row_no in range(self.ui.tableWidget_calendar.rowCount()):
            for col_no in range(self.ui.tableWidget_calendar.columnCount()):
                widget = self.ui.tableWidget_calendar.cellWidget(row_no, col_no)
                if widget is None:
                    continue

                label = widget.findChildren(QtWidgets.QLabel)[0]
                day = number_utils.get_integer(label.text())
                check_box_list = widget.findChildren(QtWidgets.QCheckBox)
                data1 = [self.year, self.month, day, '早班', self.doctor]
                data2 = [self.year, self.month, day, '午班', self.doctor]
                data3 = [self.year, self.month, day, '晚班', self.doctor]
                schedule_key1 = self._get_schedule_key(data1)
                schedule_key2 = self._get_schedule_key(data2)
                schedule_key3 = self._get_schedule_key(data3)

                data_list = [data1, data2, data3]
                schedule_key_list = [schedule_key1, schedule_key2, schedule_key3]

                for i in range(3):
                    if check_box_list[i].isChecked():
                        data_list[i].append('True')
                    else:
                        data_list[i].append('False')

                    if schedule_key_list[i] is None:
                        self.database.insert_record('doctor_month_schedule', fields, data_list[i])
                    else:
                        self.database.update_record(
                            'doctor_month_schedule', fields, 'DoctorMonthScheduleKey',
                            schedule_key_list[i], data_list[i])

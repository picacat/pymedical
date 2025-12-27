# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QPushButton

from libs import class_utils, dialog_utils, nhi_utils, string_utils, ui_utils


# 醫師班表 2018.01.31
class DoctorSchedule(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DoctorSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self._set_ui()
        self._set_signal()
        self.tab_name = self.ui.tabWidget_schedule.tabText(0)
        self.week_list = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        self._read_doctor_schedule_by_room()
        self._read_doctor_schedule_by_period()
        self._read_temporary_schedule()
        self._read_special_schedule()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DOCTOR_SCHEDULE, self)
        self.table_widget_doctor_schedule = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_schedule, self.database
        )
        self.table_widget_doctor_schedule_period = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_schedule_period, self.database
        )
        # 特約門診
        self.table_widget_special_schedule = class_utils.get_table_widget(
            self.ui.tableWidget_special_schedule, self.database
        )

        self.table_widget_temporary_schedule = class_utils.get_table_widget(
            self.ui.tableWidget_temporary_schedule, self.database
        )
        self.table_widget_doctor_schedule.set_column_hidden([0])
        self.table_widget_temporary_schedule.set_column_hidden([0])
        self._set_table_width()

        self.ui.tabWidget_schedule.setCurrentIndex(0)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [100, 60, 60, 120, 120, 120, 120, 120, 120, 120]
        self.table_widget_doctor_schedule.set_table_heading_width(width)

        width = [120, 120, 120, 120, 120, 120, 120]
        self.table_widget_doctor_schedule_period.set_table_heading_width(width)

        width = [120, 120, 120, 120, 120, 120, 120]
        self.table_widget_special_schedule.set_table_heading_width(width)

        width = [100, 130, 60, 60, 60, 100, 100, 80]
        self.table_widget_temporary_schedule.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_add_schedule.triggered.connect(self._add_schedule)
        self.ui.action_edit_schedule.triggered.connect(self._edit_schedule)
        self.ui.action_remove_schedule.triggered.connect(self._remove_schedule)

        self.ui.action_add_temporary_schedule.triggered.connect(self._add_temporary_schedule)
        self.ui.action_edit_temporary_schedule.triggered.connect(self._edit_temporary_schedule)
        self.ui.action_remove_temporary_schedule.triggered.connect(self._remove_temporary_schedule)
        self.ui.action_close.triggered.connect(self._close_doctor_schedule)
        self.ui.tableWidget_doctor_schedule.doubleClicked.connect(self._edit_schedule)
        self.ui.tableWidget_doctor_schedule_period.doubleClicked.connect(self._edit_schedule)
        self.ui.tableWidget_special_schedule.doubleClicked.connect(self._edit_special_schedule)
        self.ui.tabWidget_schedule.currentChanged.connect(self._schedule_tab_changed)   # 切換分頁
        self.ui.tableWidget_temporary_schedule.doubleClicked.connect(self._edit_temporary_schedule)

    def _read_doctor_schedule_by_room(self):
        period_list = str(nhi_utils.PERIOD)[1:-1]
        sql = f'''
            SELECT * FROM doctor_schedule
            ORDER BY Room, FIELD(Period, {period_list})
        '''
        self.table_widget_doctor_schedule.set_db_data(sql, self._set_doctor_schedule_room_data)

    def _read_temporary_schedule(self):
        sql = '''
            SELECT * FROM temporary_schedule
            WHERE
                Position = "醫師"
            ORDER BY CaseDate DESC
        '''
        self.table_widget_temporary_schedule.set_db_data(sql, self._set_temporary_schedule_data)

    def _set_doctor_schedule_room_data(self, row_no, row):
        doctor_schedule_row = [
            string_utils.xstr(row['DoctorScheduleKey']),
            string_utils.xstr(row['Room']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['Monday']),
            string_utils.xstr(row['Tuesday']),
            string_utils.xstr(row['Wednesday']),
            string_utils.xstr(row['Thursday']),
            string_utils.xstr(row['Friday']),
            string_utils.xstr(row['Saturday']),
            string_utils.xstr(row['Sunday']),
        ]

        for column in range(len(doctor_schedule_row)):
            self.ui.tableWidget_doctor_schedule.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(doctor_schedule_row[column])
            )

            align = QtCore.Qt.AlignLeft
            if column in [1, 2]:
                align = QtCore.Qt.AlignCenter

            self.ui.tableWidget_doctor_schedule.item(
                row_no, column).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )

    def _set_temporary_schedule_data(self, row_no, row):
        temporary_schedule_row = [
            string_utils.xstr(row['TemporaryScheduleKey']),
            string_utils.xstr(row['CaseDate']),
            string_utils.xstr(row['ScheduleType']),
            string_utils.xstr(row['Room']),
            string_utils.xstr(row['Period']),
            string_utils.xstr(row['Name']),
            string_utils.xstr(row['Agent']),
            string_utils.xstr(row['Remark']),
        ]

        for column in range(len(temporary_schedule_row)):
            self.ui.tableWidget_temporary_schedule.setItem(
                row_no, column,
                QtWidgets.QTableWidgetItem(temporary_schedule_row[column])
            )

            align = QtCore.Qt.AlignLeft
            if column in [2, 3, 4]:
                align = QtCore.Qt.AlignCenter

            self.ui.tableWidget_temporary_schedule.item(
                row_no, column).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )

    def _add_schedule(self):
        if self.tab_name == '診別顯示':
            self._edit_schedule_room(None)
        else:
            self._edit_schedule_period()

    def _edit_schedule(self):
        if self.tab_name == '診別顯示':
            self._edit_schedule_room(self.table_widget_doctor_schedule.field_value(0))
        else:
            self._edit_schedule_period()

    def _edit_special_schedule(self):
        col_no = self.ui.tableWidget_special_schedule.currentColumn()
        row_no = self.ui.tableWidget_special_schedule.currentRow()

        sql = '''
            SELECT * FROM person
            WHERE
                Position IN ("醫師", "支援醫師") AND
                ID IS NOT NULL AND LENGTH(ID) > 0 AND
                Password IS NOT NULL AND LENGTH(Password) > 0
            ORDER BY PersonKey
        '''
        rows = self.database.select_record(sql)
        
        items = [None, '特約門診']
        for row in rows:
            items.append(string_utils.xstr(row['Name']))

        doctor, ok = QInputDialog.getItem(
            self, "選擇醫師", "請選擇醫師", items, 0, False
        )

        if not ok:
            return


        # msg_box = QMessageBox()
        # msg_box.setIcon(QMessageBox.Information)
        # msg_box.setWindowTitle('更新內容')
        # msg_box.setText(
        #     f'''
        #     <font size="5" color="red">
        #       <b>{message}</b>
        #     </font>
        # ''')
        # msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        # msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        # apply_change = msg_box.exec_()
        # if not apply_change:
        #     return

        self._update_special_schedule(row_no, col_no, doctor)

    def _update_special_schedule(self, row_no, col_no, doctor):
        doctor_schedule_col = [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ]

        field = doctor_schedule_col[col_no]
        if row_no == 0:
            period = '早班'
        elif row_no == 1:
            period = '午班'
        else:
            period = '晚班'

        if doctor in ['', None]:
            self.ui.tableWidget_special_schedule.setItem(row_no, col_no, None)
            sql = f'''
                UPDATE special_schedule
                SET
                    {field} = NULL
                WHERE
                    Period = "{period}"
            '''
        else:
            self.ui.tableWidget_special_schedule.setItem(row_no, col_no, QtWidgets.QTableWidgetItem(doctor))
            self.ui.tableWidget_special_schedule.item(
                row_no, col_no).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            sql = f'''
                UPDATE special_schedule
                SET
                    {field} = "{doctor}"
                WHERE
                    Period = "{period}"
            '''

        self.database.exec_sql(sql)

    def _cancel_special_schedule(self, row_no, col_no):
        self.ui.tableWidget_special_schedule.setItem(row_no, col_no, None)

    def _edit_schedule_room(self, schedule_key):
        dialog = dialog_utils.get_dialog_doctor_schedule(
            self, self.database, self.system_settings, schedule_key,
        )
        if dialog.exec_():
            self._read_doctor_schedule_by_room()

        dialog.deleteLater()

    def _edit_schedule_period(self):
        weekday = self._get_weekday()
        period = self._get_period()

        dialog = dialog_utils.get_dialog_doctor_schedule_period(
            self, self.database, self.system_settings, weekday, period,
        )
        if dialog.exec_():
            self._read_doctor_schedule_by_period()

        dialog.deleteLater()

    def _get_weekday(self):
        current_column = self.ui.tableWidget_doctor_schedule_period.currentColumn()

        return self.week_list[current_column]

    def _get_period(self):
        current_row = self.ui.tableWidget_doctor_schedule_period.currentRow()

        return nhi_utils.PERIOD[current_row]

    def _remove_schedule(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除班表資料')
        msg_box.setText("<font size='4' color='red'><b>確定刪除此筆班表資料?</b></font>")
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        if self.tab_name == '診別顯示':
            self._remove_schedule_room()

    def _remove_schedule_room(self):
        self.database.delete_record(
            'doctor_schedule', 'DoctorScheduleKey',
            self.table_widget_doctor_schedule.field_value(0),
        )

        self._read_doctor_schedule_by_room()

    def _add_temporary_schedule(self):
        dialog = dialog_utils.get_dialog_temporary_schedule(self, self.database, self.system_settings)
        if dialog.exec_():
            self._read_temporary_schedule()

        dialog.deleteLater()

    def _edit_temporary_schedule(self):
        temporary_schedule_key = self.table_widget_temporary_schedule.field_value(0)
        dialog = dialog_utils.get_dialog_temporary_schedule(
            self, self.database, self.system_settings, temporary_schedule_key)
        if dialog.exec_():
            self._read_temporary_schedule()

        dialog.deleteLater()

    def _remove_temporary_schedule(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('刪除臨時班表資料')
        msg_box.setText("<font size='4' color='red'><b>確定刪除此筆臨時班表資料?</b></font>")
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        temporary_schedule_key = self.table_widget_temporary_schedule.field_value(0)
        self.database.delete_record('temporary_schedule', 'TemporaryScheduleKey', temporary_schedule_key)

        self._read_temporary_schedule()

    def _close_doctor_schedule(self):
        self.close_all()
        self.close_tab()

    def _read_doctor_schedule_by_period(self):
        for row_no in range(self.ui.tableWidget_doctor_schedule_period.rowCount()):
            for col_no in range(self.ui.tableWidget_doctor_schedule_period.columnCount()):
                self.ui.tableWidget_doctor_schedule_period.setItem(row_no, col_no, None)

        self._set_schedule_period('早班', row_no=0)
        self._set_schedule_period('午班', row_no=1)
        self._set_schedule_period('晚班', row_no=2)

    def _set_schedule_period(self, period, row_no):
        room_list = [
            '⓪', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
            '⑪', '⑫', '⑬', '⑭', '⑮', '⑯', '⑰', '⑱', '⑲', '⑳',
        ]
        for weekday in self.week_list:
            sql = f'''
                SELECT {weekday} AS Doctor, Room FROM doctor_schedule
                WHERE
                    Period = "{period}" AND
                    {weekday} IS NOT NULL
                ORDER BY Room
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                continue

            doctor_list = []
            for row in rows:
                doctor = f"{room_list[row['Room']]}{row['Doctor']}"
                doctor_list.append(doctor)

            col_no = self.week_list.index(weekday)
            if len(doctor_list) >= 2:
                doctor_label = '\n'.join(doctor_list)
            elif len(doctor_list) == 1:
                doctor_label = doctor_list[0]
            else:
                doctor_label = ''

            self.ui.tableWidget_doctor_schedule_period.setItem(
                row_no, col_no,
                QtWidgets.QTableWidgetItem(doctor_label)
            )
            self.ui.tableWidget_doctor_schedule_period.item(
                row_no, col_no).setTextAlignment(
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
            )

        self.ui.tableWidget_doctor_schedule_period.resizeRowsToContents()

    def _schedule_tab_changed(self, i):
        self.tab_name = self.ui.tabWidget_schedule.tabText(i)

        if self.tab_name == '診別顯示':
            self._read_doctor_schedule_by_room()
        else:
            self._read_doctor_schedule_by_period()

    def _read_special_schedule(self):
        sql = '''
            SELECT * FROM special_schedule
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._create_special_schedule()

        self._set_special_schedule('早班')
        self._set_special_schedule('午班')
        self._set_special_schedule('晚班')

    def _create_special_schedule(self):
        self.database.exec_sql('''
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("早班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        ''')
        self.database.exec_sql('''
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("午班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        ''')
        self.database.exec_sql('''
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("晚班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        ''')

    def _set_special_schedule(self, period):
        sql = f'''
            SELECT * FROM special_schedule WHERE Period = "{period}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        doctor_schedule_col = [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ]
        if period == '早班':
            row_no = 0
        elif period == '午班':
            row_no = 1
        else:
            row_no = 2

        for col_no in range(len(doctor_schedule_col)):
            text = row[doctor_schedule_col[col_no]]
            if text not in ['', None]:
                self.ui.tableWidget_special_schedule.setItem(
                    row_no, col_no,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(text))
                )
                self.ui.tableWidget_special_schedule.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

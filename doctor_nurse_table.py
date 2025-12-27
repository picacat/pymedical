
# -*- coding: UTF-8 -*-

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox
import datetime
import calendar
import os
import csv

from libs import class_utils
from libs import ui_utils
from libs import system_utils
from libs import string_utils
from libs import personnel_utils
from libs import nhi_utils
from libs import date_utils
from libs import dialog_utils


# 醫護班表 2018.01.31
class DoctorNurseTable(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DoctorNurseTable, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DOCTOR_NURSE_TABLE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_doctor_nurse_table = class_utils.get_table_widget(
            self.ui.tableWidget_doctor_nurse_table, self.database
        )

        self._set_table_width()
        self._set_combo_box()
        self._select_combo_box()
        if personnel_utils.get_permission(self.database, '系統作業', '關閉匯出功能', self.user_name) == 'Y':
            self.ui.action_export_csv.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_follow_doctor.triggered.connect(self._follow_doctor)
        self.ui.action_save.triggered.connect(self._save_button_clicked)
        self.ui.action_export_csv.triggered.connect(self._export_csv_file)
        self.ui.action_delete_schedule.triggered.connect(self._delete_schedule)
        self.ui.action_close.triggered.connect(self.close_app)
        # database.ui.pushButton_query.clicked.connect(database.read_schedule)
        self.ui.tableWidget_doctor_nurse_table.cellDoubleClicked.connect(self._open_input_dialog)
        self.ui.radioButton_doctor.clicked.connect(self._select_combo_box)
        self.ui.radioButton_nurse.clicked.connect(self._select_combo_box)
        self.ui.comboBox_year.currentTextChanged.connect(self.read_schedule)
        self.ui.comboBox_month.currentTextChanged.connect(self.read_schedule)
        self.ui.comboBox_doctor.currentTextChanged.connect(self.read_schedule)
        self.ui.comboBox_nurse.currentTextChanged.connect(self.read_schedule)

    def _save_button_clicked(self):
        self.save_schedule()

        system_utils.show_message_box(
            QMessageBox.Information,
            '存檔完畢',
            '<h3>班表已全部存檔完成</h3>',
            '資料正確.'
        )

    def _set_table_width(self):
        for i in range(0, self.ui.tableWidget_doctor_nurse_table.columnCount()):
            self.ui.tableWidget_doctor_nurse_table.setColumnWidth(i, 120)

        for i in range(0, self.ui.tableWidget_doctor_nurse_table.rowCount()):
            self.ui.tableWidget_doctor_nurse_table.setRowHeight(i, 112)

    def _select_combo_box(self):
        if self.ui.radioButton_doctor.isChecked():
            self.ui.comboBox_doctor.setEnabled(True)
            self.ui.comboBox_nurse.setEnabled(False)
            self.ui.action_follow_doctor.setEnabled(False)
        else:
            self.ui.comboBox_doctor.setEnabled(False)
            self.ui.comboBox_nurse.setEnabled(True)
            self.ui.action_follow_doctor.setEnabled(True)

        self.read_schedule()

    def _set_combo_box(self):
        self._set_combo_box_date()
        self._set_combo_box_doctor()
        self._set_combo_box_nurse()

    # 設定日期
    def _set_combo_box_date(self):
        year_list = []
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        for i in range(current_year+1, current_year - 10, -1):
            year_list.append(str(i))

        ui_utils.set_combo_box(self.ui.comboBox_year, year_list)
        self.ui.comboBox_year.setCurrentText(str(current_year))
        self.ui.comboBox_month.setCurrentText(str(current_month))

    # 設定醫師
    def _set_combo_box_doctor(self):
        script = '''
            SELECT * FROM person
            WHERE
                Position = "醫師" AND
                (ID IS NOT NULL AND LENGTH(ID) > 0)
        '''
        rows = self.database.select_record(script)

        doctor_list = []
        for row in rows:
            doctor_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)

    # 設定護理師
    def _set_combo_box_nurse(self):
        script = '''
            SELECT * FROM person
            WHERE
                Position IN ("護士", "護理師")
        '''
        rows = self.database.select_record(script)

        nurse_list = []
        for row in rows:
            nurse_list.append(row['Name'])

        ui_utils.set_combo_box(self.ui.comboBox_nurse, nurse_list)

    def _open_input_dialog(self):
        current_row = self.ui.tableWidget_doctor_nurse_table.currentRow()
        current_column = self.ui.tableWidget_doctor_nurse_table.currentColumn()
        item = self.ui.tableWidget_doctor_nurse_table.item(
            current_row, current_column
        )

        if item is None:
            return

        if self.ui.radioButton_doctor.isChecked():
            schedule_data = self._get_schedule_data_by_doctor(item)
            schedule_type = '醫師'
        else:
            schedule_data = self._get_schedule_data_by_nurse(item)
            schedule_type = '護理師'

        dialog = dialog_utils.get_dialog_nurse_schedule(
            self.ui, self.database, self.system_settings,
            schedule_type,
            schedule_data[0],
            schedule_data[1],
            schedule_data[2],
            schedule_data[3],
            schedule_data[4],
        )

        if dialog.exec_():
            nurse1 = dialog.ui.comboBox_person1.currentText()
            nurse2 = dialog.ui.comboBox_person2.currentText()
            nurse3 = dialog.ui.comboBox_person3.currentText()
            self.ui.tableWidget_doctor_nurse_table.setItem(
                current_row, current_column,
                QtWidgets.QTableWidgetItem(
                    item.text().split('\n')[0] + '\n' +
                    nurse1 + '\n' +
                    nurse2 + '\n' +
                    nurse3
                )
            )
            self.save_schedule()

        dialog.close_all()
        dialog.deleteLater()

    def _get_calendar(self):
        calendar_list = {
            0:  [0, 0], 1:  [0, 1], 2:  [0, 2], 3:  [0, 3], 4:  [0, 4], 5:  [0, 5], 6:  [0, 6],
            7:  [1, 0], 8:  [1, 1], 9:  [1, 2], 10: [1, 3], 11: [1, 4], 12: [1, 5], 13: [1, 6],
            14: [2, 0], 15: [2, 1], 16: [2, 2], 17: [2, 3], 18: [2, 4], 19: [2, 5], 20: [2, 6],
            21: [3, 0], 22: [3, 1], 23: [3, 2], 24: [3, 3], 25: [3, 4], 26: [3, 5], 27: [3, 6],
            28: [4, 0], 29: [4, 1], 30: [4, 2], 31: [4, 3], 32: [4, 4], 33: [4, 5], 34: [4, 6],
            35: [5, 0], 36: [5, 1], 37: [5, 2], 38: [5, 3], 39: [5, 4], 40: [5, 5], 41: [5, 6],
        }

        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())

        start_day = datetime.datetime(year, month, 1).weekday()
        if start_day == 6:
            start_day = 0
        else:
            start_day += 1

        return calendar_list, year, month, start_day

    def read_schedule(self):
        calendar_list, year, month, start_day = self._get_calendar()
        doctor = self.ui.comboBox_doctor.currentText()
        nurse = self.ui.comboBox_nurse.currentText()

        self._clear_calendar()
        if self.ui.radioButton_doctor.isChecked():
            self._get_schedule_by_doctor(calendar_list, year, month, start_day, doctor)
        else:
            self._get_schedule_by_nurse(calendar_list, year, month, start_day, nurse)

    def _set_schedule_table(self, calendar_list, year, month, start_day):
        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            self.ui.tableWidget_doctor_nurse_table.setItem(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
                QtWidgets.QTableWidgetItem(str(day))
            )
            self.ui.tableWidget_doctor_nurse_table.item(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
            ).setBackground(QtGui.QColor('white'))

    def _get_schedule_by_doctor(self, calendar_list, year, month, start_day, doctor):
        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            schedule_date = f'{year}-{month}-{day}'
            nurse1 = personnel_utils.get_doctor_nurse(self.database, schedule_date, '早班', doctor)
            nurse2 = personnel_utils.get_doctor_nurse(self.database, schedule_date, '午班', doctor)
            nurse3 = personnel_utils.get_doctor_nurse(self.database, schedule_date, '晚班', doctor)
            self.ui.tableWidget_doctor_nurse_table.setItem(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
                QtWidgets.QTableWidgetItem(
                    str(day) + '\n' +
                    nurse1 + '\n' +
                    nurse2 + '\n' +
                    nurse3
                )
            )
            self.ui.tableWidget_doctor_nurse_table.item(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
            ).setBackground(QtGui.QColor('white'))

    def _get_schedule_by_nurse(self, calendar_list, year, month, start_day, nurse):
        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            schedule_date = f'{year}-{month}-{day}'
            nurse1 = personnel_utils.get_nurse_doctor(self.database, schedule_date, '早班', nurse)
            nurse2 = personnel_utils.get_nurse_doctor(self.database, schedule_date, '午班', nurse)
            nurse3 = personnel_utils.get_nurse_doctor(self.database, schedule_date, '晚班', nurse)
            self.ui.tableWidget_doctor_nurse_table.setItem(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
                QtWidgets.QTableWidgetItem(
                    str(day) + '\n' +
                    nurse1 + '\n' +
                    nurse2 + '\n' +
                    nurse3
                )
            )
            self.ui.tableWidget_doctor_nurse_table.item(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
            ).setBackground(QtGui.QColor('white'))

    def _get_doctor_name(self, schedule_date, period, nurse):
        nurse_fields = ['Nurse1', 'Nurse2', 'Nurse3']
        doctor_fields = ['', '', '']

        for i in range(len(nurse_fields)):
            sql = f'''
                SELECT * FROM nurse_schedule
                WHERE
                    ScheduleDate = "{schedule_date}" AND
                    {nurse_fields[i]} = "{nurse}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                doctor_fields[i] = rows[0]['Doctor']

        doctor_list = {
            '早班': string_utils.xstr(doctor_fields[0]),
            '午班': string_utils.xstr(doctor_fields[1]),
            '晚班': string_utils.xstr(doctor_fields[2]),
        }

        return doctor_list[period]

    def _clear_calendar(self):
        week_list = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
        period_list = ['日期', '早班', '午班', '晚班']
        self.ui.tableWidget_doctor_nurse_table.clear()

        for i in range(len(week_list)):
            self.ui.tableWidget_doctor_nurse_table.setHorizontalHeaderItem(
                i, QtWidgets.QTableWidgetItem(week_list[i])
            )
        for i in range(self.ui.tableWidget_doctor_nurse_table.rowCount()):
            self.ui.tableWidget_doctor_nurse_table.setVerticalHeaderItem(
                i, QtWidgets.QTableWidgetItem('\n'.join(period_list))
            )

    def _get_schedule_data_by_doctor(self, item):
        schedule_list = item.text().split('\n')
        year = self.ui.comboBox_year.currentText()
        month = self.ui.comboBox_month.currentText()
        day = schedule_list[0]

        schedule_date = f'{year}-{month:0>2}-{day:0>2}'
        doctor = self.ui.comboBox_doctor.currentText()
        nurse1 = schedule_list[1]
        nurse2 = schedule_list[2]
        nurse3 = schedule_list[3]

        return [schedule_date, doctor, nurse1, nurse2, nurse3]

    def _get_schedule_data_by_nurse(self, item):
        schedule_list = item.text().split('\n')
        year = self.ui.comboBox_year.currentText()
        month = self.ui.comboBox_month.currentText()
        day = schedule_list[0]
        schedule_date = f'{year}-{month:0>2}-{day:0>2}'

        nurse = self.ui.comboBox_nurse.currentText()
        doctor1 = schedule_list[1]
        doctor2 = schedule_list[2]
        doctor3 = schedule_list[3]

        return [schedule_date, nurse, doctor1, doctor2, doctor3]

    # 班表存檔
    def save_schedule(self):
        if self.ui.radioButton_doctor.isChecked():
            self._save_schedule_by_doctor()
        else:
            self._save_schedule_by_nurse()

        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        sql = f'''
            DELETE FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}" AND
                Nurse1 IS NULL AND
                Nurse2 IS NULL AND
                Nurse3 IS NULL
        '''
        self.database.exec_sql(sql)

    # 醫師班表
    def _save_schedule_by_doctor(self):
        self._delete_existing_schedule_by_doctor()

        for i in range(self.ui.tableWidget_doctor_nurse_table.rowCount()):
            for j in range(self.ui.tableWidget_doctor_nurse_table.columnCount()):
                item = self.ui.tableWidget_doctor_nurse_table.item(i, j)
                if item is None:
                    continue

                schedule_data = self._get_schedule_data_by_doctor(item)
                fields = [
                    'ScheduleDate', 'Doctor',
                    'Nurse1', 'Nurse2', 'Nurse3',
                ]

                data = [
                    schedule_data[0],
                    schedule_data[1],
                    schedule_data[2],
                    schedule_data[3],
                    schedule_data[4],
                ]

                self.database.insert_record('nurse_schedule', fields, data)

    # 護理師表
    def _save_schedule_by_nurse(self):
        self._delete_existing_schedule_by_nurse()

        for row_no in range(self.ui.tableWidget_doctor_nurse_table.rowCount()):
            for col_no in range(self.ui.tableWidget_doctor_nurse_table.columnCount()):
                item = self.ui.tableWidget_doctor_nurse_table.item(row_no, col_no)
                if item is None:
                    continue

                schedule_data = self._get_schedule_data_by_nurse(item)
                schedule_date = schedule_data[0]
                nurse = schedule_data[1]
                nurse_fields = ['Nurse1', 'Nurse2', 'Nurse3']

                for i in range(len(nurse_fields)):
                    doctor = string_utils.xstr(schedule_data[i+2])
                    if doctor == '':  # nurse 已經被清除(delete_existing_schedule_by_nurse), 可以直接跳過
                        continue

                    sql = f'''
                        SELECT * FROM nurse_schedule
                        WHERE
                            ScheduleDate = "{schedule_date}" AND
                            Doctor = "{doctor}"
                    '''
                    rows = self.database.select_record(sql)
                    if len(rows) <= 0:
                        fields = [
                            'ScheduleDate', 'Doctor', nurse_fields[i],
                        ]

                        data = [
                            schedule_date, doctor,
                            nurse,
                        ]

                        self.database.insert_record('nurse_schedule', fields, data)
                    else:
                        sql = f'''
                            UPDATE nurse_schedule
                            SET
                                {nurse_fields[i]} = "{nurse}"
                            WHERE
                                ScheduleDate = "{schedule_date}" AND
                                Doctor = "{doctor}"
                        '''
                        self.database.exec_sql(sql)

    # 清除醫師班表
    def _delete_existing_schedule_by_doctor(self):
        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        doctor = self.ui.comboBox_doctor.currentText()
        sql = f'''
            DELETE FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}" AND
                Doctor = "{doctor}"
        '''
        self.database.exec_sql(sql)

    # 清除護理師班表
    def _delete_existing_schedule_by_nurse(self):
        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        nurse = self.ui.comboBox_nurse.currentText()

        nurse_field = ['Nurse1', 'Nurse2', 'Nurse3']
        for i in range(len(nurse_field)):
            sql = f'''
                UPDATE nurse_schedule
                SET
                    {nurse_field[i]} = NULL
                WHERE
                    ScheduleDate BETWEEN "{start_date}" AND "{end_date}" AND
                    {nurse_field[i]} = "{nurse}"
            '''
            self.database.exec_sql(sql)

        sql = f'''
            DELETE FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}" AND
                Nurse1 IS NULL AND
                Nurse2 IS NULL AND
                Nurse3 IS NULL
        '''
        self.database.exec_sql(sql)

    def _export_csv_file(self):
        last_dir = system_utils.get_last_directory('護理師跟診表')
        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())

        csv_filename = os.path.join(
            last_dir,
            f'{year-1911:0>3}{month:0>2}.csv'
        )
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        csv_filename, _ = QFileDialog.getSaveFileName(
            self, "匯出護理師跟診表",
            csv_filename,
            "所有檔案 (*);;csv檔 (*.csv)", options=options
        )
        if not csv_filename:
            return

        system_utils.set_last_directory('護理師跟診表', csv_filename)

        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        sql = f'''
            SELECT * FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
            ORDER BY ScheduleDate
        '''
        rows = self.database.select_record(sql)

        with open(csv_filename, 'w', newline='', encoding='Big5') as csv_file:
            schedule = csv.writer(csv_file)
            schedule.writerow(['院區', '資料年月', '主治醫師ID', '看診日期', '看診時段', '診次', '護理人員ID'])

            for row in rows:
                for i in range(1, 4):
                    field_name = f'Nurse{i}'
                    if row[field_name] is not None:
                        schedule_row = [
                            'X',
                            f'{year-1911:0>3}{month:0>2}',
                            personnel_utils.get_person_field_value(
                                self.database, string_utils.xstr(row['Doctor']), 'ID'
                            ),
                            date_utils.west_date_to_nhi_date(row['ScheduleDate']),
                            string_utils.xstr(i),
                            '1',
                            personnel_utils.get_person_field_value(
                                self.database, string_utils.xstr(row[field_name]), 'ID'
                            ),
                        ]
                        schedule.writerow(schedule_row)

        system_utils.show_message_box(
            QMessageBox.Information,
            '匯出完成',
            '<h4>中醫護理師跟診表匯出完成 !</h4>',
            '請至健保VPN網站完成中醫護理人員跟診表上傳作業'
        )

    def _follow_doctor(self):
        self._follow_doctor_from_medical_record()
        self.save_schedule()

    def _follow_doctor_from_medical_record(self):
        doctor_list = personnel_utils.get_person(self.database, '醫師')
        doctor, ok = QInputDialog.getItem(self, "QInputDialog.getItem()", "跟診醫師:", doctor_list, 0, False)
        if not ok or not doctor:
            return

        self._clear_calendar()
        calendar_list, year, month, start_day = self._get_calendar()
        self._set_schedule_table(calendar_list, year, month, start_day)
        for i in range(self.ui.tableWidget_doctor_nurse_table.rowCount()):
            for j in range(self.ui.tableWidget_doctor_nurse_table.columnCount()):
                item = self.ui.tableWidget_doctor_nurse_table.item(i, j)
                if item is None:
                    continue

                case_day = item.text().strip()
                start_date = f'{year}-{month}-{case_day} 00:00:00'
                end_date = f'{year}-{month}-{case_day} 23:59:59'
                sql = f'''
                    SELECT Period FROM cases
                    WHERE
                        InsType = "健保" AND
                        CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                        Doctor = "{doctor}"
                    GROUP BY Period
                '''
                rows = self.database.select_record(sql)
                doctor_list = ['', '', '']
                for row in rows:
                    if string_utils.xstr(row['Period']) == '早班':
                        doctor_list[0] = doctor
                    elif string_utils.xstr(row['Period']) == '午班':
                        doctor_list[1] = doctor
                    elif string_utils.xstr(row['Period']) == '晚班':
                        doctor_list[2] = doctor

                self.ui.tableWidget_doctor_nurse_table.setItem(
                    i, j,
                    QtWidgets.QTableWidgetItem(
                        item.text().split('\n')[0] + '\n' +
                        doctor_list[0] + '\n' +
                        doctor_list[1] + '\n' +
                        doctor_list[2]
                    )
                )
                self.ui.tableWidget_doctor_nurse_table.item(
                    i, j,
                ).setBackground(QtGui.QColor('white'))

    # 刪除班表
    def _delete_schedule(self):
        dialog = dialog_utils.get_dialog_date_picker(self, self.database, self.system_settings, None)
        if not dialog.exec_():
            dialog.deleteLater()
            return

        year = int(dialog.ui.comboBox_year.currentText())
        month = int(dialog.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month:0>2}-01'
        end_date = f'{year}-{month:0>2}-{last_day:0>2}'

        self.database.exec_sql(f'''
            DELETE FROM nurse_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
        ''')

        dialog.deleteLater()
        self.read_schedule()

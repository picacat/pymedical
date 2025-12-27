# -*- coding: utf-8 -*-

import calendar
import datetime

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox

from libs import (class_utils, dialog_utils, personnel_utils, string_utils,
                  system_utils, ui_utils)


# 藥師班表 2021.09.08
class PharmacistSchedule(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(PharmacistSchedule, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()

        self.read_schedule()

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
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHARMACIST_SCHEDULE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_pharmacist_table = class_utils.get_table_widget(
            self.ui.tableWidget_pharmacist_table, self.database
        )

        self._set_table_width()
        self._set_combo_box()

    # 設定信號
    def _set_signal(self):
        self.ui.action_follow_doctor.triggered.connect(self._follow_doctor)
        self.ui.action_save.triggered.connect(self._save_button_clicked)
        self.ui.action_delete_schedule.triggered.connect(self._delete_schedule)
        self.ui.action_close.triggered.connect(self.close_app)
        self.ui.action_adjust_pharmacy_type.triggered.connect(self._adjust_pharmacy_type)
        self.ui.tableWidget_pharmacist_table.cellDoubleClicked.connect(self._open_input_dialog)
        self.ui.comboBox_year.currentTextChanged.connect(self.read_schedule)
        self.ui.comboBox_month.currentTextChanged.connect(self.read_schedule)

    def _save_button_clicked(self):
        self.save_schedule()

        system_utils.show_message_box(
            QMessageBox.Information,
            '存檔完畢',
            '<h3>班表已全部存檔完成</h3>',
            '資料正確.'
        )

    def _set_table_width(self):
        for i in range(0, self.ui.tableWidget_pharmacist_table.columnCount()):
            self.ui.tableWidget_pharmacist_table.setColumnWidth(i, 130)

        for i in range(0, self.ui.tableWidget_pharmacist_table.rowCount()):
            self.ui.tableWidget_pharmacist_table.setRowHeight(i, 120)

    def _set_combo_box(self):
        self._set_combo_box_date()

    # 設定日期
    def _set_combo_box_date(self):
        year_list = []
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month

        for i in range(current_year, current_year - 10, -1):
            year_list.append(str(i))

        ui_utils.set_combo_box(self.ui.comboBox_year, year_list)
        self.ui.comboBox_year.setCurrentText(str(current_year))
        self.ui.comboBox_month.setCurrentText(str(current_month))

    def _open_input_dialog(self):
        current_row = self.ui.tableWidget_pharmacist_table.currentRow()
        current_column = self.ui.tableWidget_pharmacist_table.currentColumn()
        item = self.ui.tableWidget_pharmacist_table.item(
            current_row, current_column
        )

        if item is None:
            return

        schedule_data = self._get_schedule_data(item)
        dialog = dialog_utils.get_dialog_pharmacist_schedule(
            self.ui, self.database, self.system_settings,
            schedule_data[0],
            schedule_data[1],
            schedule_data[2],
            schedule_data[3],
        )

        if dialog.exec_():
            pharmacist1 = dialog.ui.comboBox_person1.currentText()
            pharmacist2 = dialog.ui.comboBox_person2.currentText()
            pharmacist3 = dialog.ui.comboBox_person3.currentText()
            self.ui.tableWidget_pharmacist_table.setItem(
                current_row, current_column,
                QtWidgets.QTableWidgetItem(
                    item.text().split('\n')[0] + '\n' +
                    pharmacist1 + '\n' +
                    pharmacist2 + '\n' +
                    pharmacist3
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

        self._clear_calendar()
        self._get_schedule(calendar_list, year, month, start_day)

    def _set_schedule_table(self, calendar_list, year, month, start_day):
        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            self.ui.tableWidget_pharmacist_table.setItem(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
                QtWidgets.QTableWidgetItem(str(day))
            )
            self.ui.tableWidget_pharmacist_table.item(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
            ).setBackground(QtGui.QColor('white'))

    def _get_schedule(self, calendar_list, year, month, start_day):
        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            schedule_date = f'{year}-{month}-{day}'
            pharmacist1 = personnel_utils.get_pharmacist(self.database, schedule_date, '早班')
            pharmacist2 = personnel_utils.get_pharmacist(self.database, schedule_date, '午班')
            pharmacist3 = personnel_utils.get_pharmacist(self.database, schedule_date, '晚班')
            content = f'{day}\n{pharmacist1}\n{pharmacist2}\n{pharmacist3}'

            self.ui.tableWidget_pharmacist_table.setItem(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
                QtWidgets.QTableWidgetItem(content)
            )
            self.ui.tableWidget_pharmacist_table.item(
                calendar_list[start_day+i][0],
                calendar_list[start_day+i][1],
            ).setBackground(QtGui.QColor('white'))

    def _clear_calendar(self):
        week_list = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
        period_list = ['日期', '早班', '午班', '晚班']
        self.ui.tableWidget_pharmacist_table.clear()

        for i in range(len(week_list)):
            self.ui.tableWidget_pharmacist_table.setHorizontalHeaderItem(
                i, QtWidgets.QTableWidgetItem(week_list[i])
            )
        for i in range(self.ui.tableWidget_pharmacist_table.rowCount()):
            self.ui.tableWidget_pharmacist_table.setVerticalHeaderItem(
                i, QtWidgets.QTableWidgetItem('\n'.join(period_list))
            )

    def _get_schedule_data(self, item):
        schedule_list = item.text().split('\n')
        year = self.ui.comboBox_year.currentText()
        month = self.ui.comboBox_month.currentText()
        day = schedule_list[0]

        schedule_date = f'{year}-{month:0>2}-{day:0>2}'
        pharmacist1 = schedule_list[1]
        pharmacist2 = schedule_list[2]
        pharmacist3 = schedule_list[3]

        return [schedule_date, pharmacist1, pharmacist2, pharmacist3]

    # 班表存檔
    def save_schedule(self):
        self._save_schedule_data()

        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        sql = f'''
            DELETE FROM pharmacist_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}" AND
                Pharmacist1 IS NULL AND
                Pharmacist2 IS NULL AND
                Pharmacist3 IS NULL
        '''
        self.database.exec_sql(sql)

    # 藥師班表
    def _save_schedule_data(self):
        self._delete_existing_schedule()

        fields = ['ScheduleDate', 'Pharmacist1', 'Pharmacist2', 'Pharmacist3']
        for row_no in range(self.ui.tableWidget_pharmacist_table.rowCount()):
            for col_no in range(self.ui.tableWidget_pharmacist_table.columnCount()):
                item = self.ui.tableWidget_pharmacist_table.item(row_no, col_no)
                if item is None:
                    continue

                schedule_data = self._get_schedule_data(item)
                data = [
                    schedule_data[0],
                    schedule_data[1],
                    schedule_data[2],
                    schedule_data[3],
                ]

                self.database.insert_record('pharmacist_schedule', fields, data)

    # 清除藥師班表
    def _delete_existing_schedule(self):
        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'

        sql = f'''
            DELETE FROM pharmacist_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
        '''
        self.database.exec_sql(sql)

    def _follow_doctor(self):
        self._follow_doctor_from_medical_record()
        self.save_schedule()

    def _follow_doctor_from_medical_record(self):
        doctor_list = personnel_utils.get_person(self.database, '醫師')
        doctor, ok = QInputDialog.getItem(self, "請選擇跟診醫師", "跟診醫師:", doctor_list, 0, False)
        if not ok or not doctor:
            return

        pharmacist_list = personnel_utils.get_person(self.database, '藥師')
        pharmacist, ok = QInputDialog.getItem(self, "請選擇藥師", "值班藥師:", pharmacist_list, 0, False)
        if not ok or not pharmacist:
            return

        self._clear_calendar()
        calendar_list, year, month, start_day = self._get_calendar()
        self._set_schedule_table(calendar_list, year, month, start_day)
        for i in range(self.ui.tableWidget_pharmacist_table.rowCount()):
            for j in range(self.ui.tableWidget_pharmacist_table.columnCount()):
                item = self.ui.tableWidget_pharmacist_table.item(i, j)
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
                pharmacist_list = ['', '', '']
                for row in rows:
                    if string_utils.xstr(row['Period']) == '早班':
                        pharmacist_list[0] = pharmacist
                    elif string_utils.xstr(row['Period']) == '午班':
                        pharmacist_list[1] = pharmacist
                    elif string_utils.xstr(row['Period']) == '晚班':
                        pharmacist_list[2] = pharmacist

                self.ui.tableWidget_pharmacist_table.setItem(
                    i, j,
                    QtWidgets.QTableWidgetItem(
                        item.text().split('\n')[0] + '\n' +
                        pharmacist_list[0] + '\n' +
                        pharmacist_list[1] + '\n' +
                        pharmacist_list[2]
                    )
                )
                self.ui.tableWidget_pharmacist_table.item(i, j).setBackground(QtGui.QColor('white'))

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
            DELETE FROM pharmacist_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
        ''')

        dialog.deleteLater()
        self.read_schedule()

    def _adjust_pharmacy_type(self):
        year = int(self.ui.comboBox_year.currentText())
        month = int(self.ui.comboBox_month.currentText())
        last_day = calendar.monthrange(year, month)[1]
        start_date = f'{year}-{month}-1'
        end_date = f'{year}-{month}-{last_day}'
        self._reset_pharmacy_type(start_date, end_date)
        
        sql = f'''
            SELECT * FROM pharmacist_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
            ORDER BY ScheduleDate
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            case_date = row['ScheduleDate'].strftime('%Y-%m-%d')
            pharmacist1 = row['Pharmacist1']
            pharmacist2 = row['Pharmacist2']
            pharmacist3 = row['Pharmacist3']
            
            if pharmacist1 not in ['', None]:
                period = '早班'
                self._set_pharmacy_type(case_date, period, pharmacist1)
                
            if pharmacist2 not in ['', None]:                
                period = '午班'
                self._set_pharmacy_type(case_date, period, pharmacist2)      
          
                
            if pharmacist3 not in ['', None]:                
                period = '晚班'
                self._set_pharmacy_type(case_date, period, pharmacist3)

        system_utils.show_message_box(
            QMessageBox.Information,
            '調整完成',
            '<h3>調劑方式已經全部變更完成</h3>',
            '請重新執行申報檢查.'
        )


    def _reset_pharmacy_type(self, start_date, end_date):
        sql = f'''
            UPDATE cases
                SET PharmacyType = "不申報",
                Pharmacist = NULL
            WHERE
                DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}" AND
                InsType = "健保"
        '''
        self.database.exec_sql(sql)        
        
    def _set_pharmacy_type(self, case_date, period, pharmacist):
        sql = f'''
            UPDATE cases
            SET
                PharmacyType = "申報",
                Pharmacist = "{pharmacist}"        
            WHERE
                DATE(CaseDate) = "{case_date}" AND
                Period = "{period}" AND
                InsType = "健保"
        '''
        self.database.exec_sql(sql)




        

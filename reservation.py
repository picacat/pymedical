# -*- coding: utf-8 -*-
"""預約掛號2025-07-26修改."""

import calendar
import datetime
import json

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QPushButton

from libs import (
    alleypin_utils,
    class_utils,
    date_utils,
    db_utils,
    dialog_utils,
    export_utils,
    hainachuan_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


class Reservation(QtWidgets.QMainWindow):
    """預約掛號"""

    program_name = "預約掛號"

    def __init__(self, parent=None, *args):
        """初始化."""
        super(Reservation, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.reserve_key = args[2]
        self.patient_key = args[3]
        self.doctor = args[4]
        try:
            self.vhc_ic_card = args[5]
        except Exception:
            self.vhc_ic_card = None

        self.ui = None

        self.max_reservation_table_times = 4
        self.max_reservation_table_rows = 40

        self.table_header = ["時間", "診號", "姓名", "reserve_key"]
        self.table_header_width = [60, 50, 94, 60]

        self.wide_table_header = ["時間", "診號", "姓名", "備註", "reserve_key"]
        self.wide_table_header_width = [60, 50, 100, 204, 60]
        self.no_reservation_time = self.system_settings.field("預約班表不顯示時間")
        self.show_remain = self.system_settings.field("預約班表顯示剩餘次數")
        self.show_last_case_remark = self.system_settings.field(
            "預約名單顯示上次病歷備註"
        )

        self.col_no_dict = {
            0: 0,
            4: 5,
            8: 10,
            12: 15,
        }

        self.tab_name = "預約一覽表"

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()
        # self.read_reservation()  # pymedical 已經驅動

        if self.patient_key is not None:  # 醫師預約
            self._set_reservation_by_doctor()

    # 解構
    def __del__(self):
        """解構."""
        self.close_all()

    # 關閉
    def close_all(self):
        """關閉."""
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_RESERVATION, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_reservation = class_utils.get_table_widget(
            self.ui.tableWidget_reservation, self.database
        )
        self.table_widget_reservation_list = class_utils.get_table_widget(
            self.ui.tableWidget_reservation_list, self.database
        )
        self.table_widget_cancel_list = class_utils.get_table_widget(
            self.ui.tableWidget_cancel_list, self.database
        )

        self.ui.dateEdit_reservation_date.setDate(datetime.datetime.today())
        self._set_week_day()

        self.ui.dateEdit_start_date.setDate(datetime.datetime.today())
        self.ui.dateEdit_end_date.setDate(datetime.datetime.today())

        self.table_widget_reservation_list.set_column_hidden([0])
        self.ui.tabWidget_reservation.setCurrentIndex(0)

        self.table_widget_cancel_list.set_column_hidden([0])

        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)

        self.ui.action_add_reservation.setEnabled(False)
        self.ui.action_reserve_reservation.setEnabled(False)
        self.ui.action_cancel_reservation.setEnabled(False)
        self.ui.action_modify_reservation.setEnabled(False)
        self.ui.action_print_reservation.setEnabled(False)
        # database.ui.action_reservation_arrival.setEnabled(False)

        self._set_permission()
        self._preset_combo_box_doctor()
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, "全部")

        self.ui.tableWidget_reservation_list.setColumnHidden(8, True)  # 隱藏診別

        if self.no_reservation_time == "Y":
            self.ui.toolButton_hide_calendar.setVisible(False)

        header = [
            "reserve_key",
            "預約日期",
            "預約時間",
            "班別",
            "病歷號",
            "姓名",
            "生日",
            "預約醫師",
            "診別",
            "診號",
            "報到",
            "預約來源",
            "掛號人員",
            "聯絡電話",
            "行動電話",
            "登錄時間",
            "備註",
        ]

        if self.show_last_case_remark == "Y":
            self.ui.tableWidget_reservation_list.setColumnCount(
                self.ui.tableWidget_reservation_list.columnCount() + 1
            )
            header.append("上次病歷備註")

        self.ui.tableWidget_reservation_list.setHorizontalHeaderLabels(header)

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "新增預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_add_reservation.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "更改預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_modify_reservation.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "刪除預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_cancel_reservation.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "預約報到", self.user_name
            )
            != "Y"
        ):
            self.ui.action_reservation_arrival.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "查詢預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_reservation_query.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "匯出預約名單", self.user_name
            )
            != "Y"
        ):
            self.ui.action_export_reservation_excel.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "班表設定", self.user_name
            )
            != "Y"
        ):
            self.ui.menu_reservation_table.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "暫停預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_off_day_setting.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "保留預約", self.user_name
            )
            != "Y"
        ):
            self.ui.action_reserve_reservation.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, "系統作業", "關閉匯出功能", self.user_name
            )
            == "Y"
        ):
            self.ui.action_export_reservation_excel.setEnabled(False)
            self.ui.action_export_web_reservation_excel.setEnabled(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_reservation)
        self.ui.action_save_general_table.triggered.connect(self._save_general_table)
        self.ui.action_save_assigned_table.triggered.connect(self._save_assigned_table)
        self.ui.action_save_assigned_null_table.triggered.connect(
            self._save_assigned_null_table
        )
        self.ui.action_copy_general_table.triggered.connect(self._copy_general_table)
        self.ui.action_remove_assigned_table.triggered.connect(
            self._remove_assigned_table
        )
        self.ui.action_remove_general_table.triggered.connect(
            self._remove_general_table
        )
        self.ui.action_modify_reservation.triggered.connect(self._modify_reservation)
        self.ui.action_cancel_reservation.triggered.connect(self._cancel_reservation)
        self.ui.action_lock_reservation.triggered.connect(self._lock_reservation)

        self.ui.action_print_reservation.triggered.connect(self._print_reservation)
        self.ui.action_print_reservation_list.triggered.connect(
            self._print_reservation_list
        )
        self.ui.action_print_reservation_list2.triggered.connect(
            lambda: self._print_reservation_list(print_less=True)
        )
        self.ui.action_print_correction_area_reservation_list.triggered.connect(
            self._print_correction_area_reservation_list
        )

        self.ui.action_medical_record_past_history.triggered.connect(
            self._open_past_history
        )
        self.ui.action_reservation_arrival.triggered.connect(self.reservation_arrival)
        self.ui.action_reservation_query.triggered.connect(self._reservation_query)
        self.ui.action_export_reservation_excel.triggered.connect(
            self._export_reservation_excel
        )
        self.ui.action_export_web_reservation_excel.triggered.connect(
            self._export_web_reservation_excel
        )
        self.ui.action_off_day_setting.triggered.connect(self._off_day_setting)
        self.ui.action_auto_reservation_table.triggered.connect(
            self._auto_reservation_table
        )
        self.ui.action_set_not_arrival.triggered.connect(self._set_not_arrival)

        self.ui.action_first_visit_info.triggered.connect(
            self._display_first_visit_info
        )

        self.ui.dateEdit_reservation_date.dateChanged.connect(self.read_reservation)
        self.ui.radioButton_period1.clicked.connect(self.read_reservation_by_period)
        self.ui.radioButton_period2.clicked.connect(self.read_reservation_by_period)
        self.ui.radioButton_period3.clicked.connect(self.read_reservation_by_period)

        self.ui.tableWidget_reservation.doubleClicked.connect(self._booking_reservation)
        self.ui.tableWidget_reservation_list.doubleClicked.connect(
            self.reservation_arrival
        )
        self.ui.action_add_reservation.triggered.connect(self._booking_reservation)
        self.ui.action_reserve_reservation.triggered.connect(self._reserve_reservation)
        self.ui.action_hide_on_web.triggered.connect(self._hide_on_web)
        self.ui.action_permission_list_setting.triggered.connect(
            self._permission_list_setting
        )

        self.ui.tabWidget_reservation.currentChanged.connect(
            self._tab_changed
        )  # 切換分頁
        self.ui.dateEdit_start_date.dateChanged.connect(self._read_reservation_list)
        self.ui.dateEdit_end_date.dateChanged.connect(self._read_reservation_list)
        self.ui.radioButton_arrival1.clicked.connect(self._read_reservation_list)
        self.ui.radioButton_arrival2.clicked.connect(self._read_reservation_list)
        self.ui.radioButton_arrival3.clicked.connect(self._read_reservation_list)
        self.ui.tableWidget_reservation.itemSelectionChanged.connect(
            self._reservation_table_item_changed
        )
        self.ui.tableWidget_reservation.itemChanged.connect(
            self._reservation_item_changed
        )
        self.ui.tableWidget_reservation_list.itemSelectionChanged.connect(
            self._reservation_list_changed
        )

        self.ui.comboBox_doctor.currentTextChanged.connect(
            self._combo_box_doctor_changed
        )
        self.ui.comboBox_period.currentTextChanged.connect(self._read_reservation_list)
        self.ui.comboBox_list_doctor.currentTextChanged.connect(
            self._read_reservation_list
        )

        self.ui.dateEdit_reservation_date.dateChanged.connect(self._set_week_day)
        self.ui.tableWidget_calendar.cellClicked.connect(self._calendar_changed)

        self.ui.toolButton_previous.clicked.connect(self._previous_calendar)
        self.ui.toolButton_next.clicked.connect(self._next_calendar)
        self.ui.toolButton_export_reservation.clicked.connect(
            self._export_reservation_excel
        )
        self.ui.toolButton_doctor_month_schedule.clicked.connect(
            self._doctor_month_schedule
        )
        self.ui.toolButton_hide_calendar.clicked.connect(self._collapse_calendar)
        self.ui.toolButton_auto_reservation.clicked.connect(self._auto_reservation)
        self.ui.toolButton_visit1.clicked.connect(self._set_reservation_type)
        self.ui.toolButton_visit2.clicked.connect(self._set_reservation_type)
        self.ui.toolButton_clear_visit.clicked.connect(self._set_reservation_type)
        self.ui.toolButton_allow.clicked.connect(self._set_reservation_allow)

        self.ui.dateEdit_cancel_start_date.dateChanged.connect(self._read_cancel_list)
        self.ui.dateEdit_cancel_end_date.dateChanged.connect(self._read_cancel_list)
        self.ui.lineEdit_cancel_patient_key.textChanged.connect(self._read_cancel_list)
        self.ui.tabWidget_reservation.currentChanged.connect(
            self.tab_changed
        )  # 切換分頁

        self.ui.action_set_reserve_type2.triggered.connect(
            lambda: self._set_reserve_type("複診")
        )
        self.ui.action_set_reserve_type3.triggered.connect(
            lambda: self._set_reserve_type("初複診")
        )

    def _collapse_calendar(self):
        expand_column_list = [3, 8, 13, 18]

        if self.ui.verticalFrame.isVisible():
            self._expand_reservation_table(expand_column_list)
        else:
            self._collapse_reservation_table(expand_column_list)

        self.ui.verticalFrame.setVisible(not self.ui.verticalFrame.isVisible())
        self.read_reservation()

    def _expand_reservation_table(self, expand_column_list):
        for col_no in expand_column_list:
            self.ui.tableWidget_reservation.insertColumn(col_no)
            self.ui.tableWidget_reservation.setColumnWidth(col_no, 190)

        self.ui.tableWidget_reservation.setHorizontalHeaderLabels(
            self.wide_table_header * self.max_reservation_table_times
        )

    def _collapse_reservation_table(self, expand_column_list):
        expand_column_list.reverse()
        for col_no in expand_column_list:
            self.ui.tableWidget_reservation.removeColumn(col_no)

    # 設定欄位寬度
    def _set_table_width(self):
        if self.ui.verticalFrame.isVisible():
            table_header_width = self.table_header_width
        else:
            table_header_width = self.wide_table_header_width

        width = table_header_width * self.max_reservation_table_times
        self.table_widget_reservation.set_table_heading_width(width)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_reservation(self):
        self.close_all()
        self.close_tab()

    def _set_week_day(self):
        week_day_name = self._get_week_day_name()
        self.ui.label_weekday_name.setText(week_day_name)

    def _get_week_day_name(self, region="zh_TW"):
        current_week_day = datetime.datetime(
            self.ui.dateEdit_reservation_date.date().year(),
            self.ui.dateEdit_reservation_date.date().month(),
            self.ui.dateEdit_reservation_date.date().day(),
        ).weekday()

        week_day_name = date_utils.get_weekday_name(current_week_day, region)

        return week_day_name

    def _set_combo_box_current_doctor(self):
        self._preset_combo_box_doctor()
        current_doctor = self.ui.comboBox_doctor.currentText()
        weekday_name = self._get_week_day_name("en_US")
        period = self._get_period()
        in_duty_doctor_list = registration_utils.get_schedule_doctor_by_date_period(
            self.database, weekday_name, period
        )
        reservation_date = self.ui.dateEdit_reservation_date.date().toString(
            "yyyy-MM-dd"
        )
        registration_utils.set_temporary_doctor_schedule(
            self.database, period, in_duty_doctor_list, case_date=reservation_date
        )

        if current_doctor is not None and current_doctor in in_duty_doctor_list:
            self.ui.comboBox_doctor.setCurrentText(current_doctor)

        ui_utils.set_combo_box(self.ui.comboBox_doctor, in_duty_doctor_list)

        in_duty_doctor = registration_utils.get_temporary_in_duty_doctor(
            self.database, reservation_date, period
        )
        if in_duty_doctor is not None:
            agent_doctor = registration_utils.get_temporary_agent_doctor(
                self.database, reservation_date, period, in_duty_doctor
            )

            if agent_doctor is not None:
                self.ui.comboBox_doctor.setCurrentText(agent_doctor)

    def _get_doctor_list(self):
        week_list = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        doctor_lists = []
        sql = """
            SELECT * FROM doctor_schedule
        """
        rows = self.database.select_record(sql)
        for row in rows:
            for weekday in week_list:
                doctor = row[weekday]
                if doctor is not None and doctor not in doctor_lists:
                    doctor_lists.append(doctor)

        return doctor_lists

    def _preset_combo_box_doctor(self):
        if self.doctor is not None:  # 醫師預約不設定
            ui_utils.set_combo_box(self.ui.comboBox_doctor, [self.doctor])
            return

        doctor_list = personnel_utils.get_person(self.database, "無逗點醫師")
        # doctor_list = self._get_doctor_list()
        ui_utils.set_combo_box(self.ui.comboBox_doctor, doctor_list)
        ui_utils.set_combo_box(self.ui.comboBox_list_doctor, doctor_list, "全部")

        room = self.system_settings.field("診療室")  # 取得預設診療室
        period = registration_utils.get_current_period(self.system_settings)
        doctor = registration_utils.get_schedule_doctor(self.database, room, period)

        reservation_date = self.ui.dateEdit_reservation_date.date().toString(
            "yyyy-MM-dd"
        )
        if doctor is None or doctor == "":
            for i in range(1, 20):
                room = string_utils.xstr(i)
                doctor = registration_utils.get_schedule_doctor(
                    self.database, room, period, reservation_date=reservation_date
                )
                if doctor is not None and doctor != "":
                    break

        self.ui.comboBox_doctor.setCurrentText(doctor)

    # 設定醫師
    def set_combo_box_doctor(self):
        if (
            self.doctor is None
            and self.system_settings.field("預約選擇當診醫師") == "Y"
        ):
            self._set_combo_box_current_doctor()

    def _set_radio_button_period(self, period):
        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def read_reservation_by_period(self, set_combo_doctor=True):
        self._set_reservation_table()
        self._set_reservation_data()
        if set_combo_doctor:
            self.set_combo_box_doctor()

    def _combo_box_doctor_changed(self):
        self.read_reservation()

    def read_reservation(self, set_combo_doctor=False):
        self._set_reservation_table()
        self._set_reservation_data()
        self._set_calendar()
        if set_combo_doctor:
            self.set_combo_box_doctor()

    # tab 切換
    def tab_changed(self, i):
        tab_name = self.ui.tabWidget_reservation.tabText(i)
        if tab_name == "預約名單":
            self._set_reservation_list_date(self.ui.dateEdit_reservation_date.date())
        elif tab_name == "爽約名單":
            self._set_absent_list(self.ui.dateEdit_reservation_date.date())
        elif tab_name == "取消預約名單":
            self._set_cancel_list()

    def _set_reservation_list_date(self, reservation_date):
        self.ui.dateEdit_start_date.setDate(reservation_date)
        self.ui.dateEdit_end_date.setDate(reservation_date)

        period = self._get_period()
        self.ui.comboBox_period.setCurrentText(period)

        self.ui.comboBox_list_doctor.setCurrentText(
            self.ui.comboBox_doctor.currentText()
        )
        self.ui.radioButton_arrival3.setChecked(True)

    def _clear_reservation_table(self):
        self.ui.tableWidget_reservation.clear()

        if self.ui.verticalFrame.isVisible():
            table_header = self.table_header
        else:
            table_header = self.wide_table_header

        max_reservation_table_columns = (
            len(table_header) * self.max_reservation_table_times
        )
        self.ui.tableWidget_reservation.setColumnCount(max_reservation_table_columns)
        self.ui.tableWidget_reservation.setRowCount(self.max_reservation_table_rows)
        self.ui.tableWidget_reservation.setHorizontalHeaderLabels(
            table_header * self.max_reservation_table_times
        )
        self._set_table_width()

        hidden_columns = [
            i * len(table_header) - 1
            for i in range(1, self.max_reservation_table_times + 1)
        ]
        self.table_widget_reservation.set_column_hidden(hidden_columns)

        if self.no_reservation_time == "Y":
            new_hidden_columns = []
            for col_no in hidden_columns:
                new_hidden_columns.append(col_no - 3)
                new_hidden_columns.append(col_no)

            self.table_widget_reservation.set_column_hidden(new_hidden_columns)

    def _set_reservation_table(self):
        self.ui.tableWidget_reservation.setUpdatesEnabled(False)
        self.ui.tableWidget_reservation.blockSignals(True)

        try:
            self._set_reservation_list_date(self.ui.dateEdit_reservation_date.date())
            weekday = self._get_week_day_name()
            reservation_date = self.ui.dateEdit_reservation_date.date().toString(
                "yyyy-MM-dd"
            )
            period = self.ui.comboBox_period.currentText()
            doctor = self.ui.comboBox_list_doctor.currentText()

            self._clear_reservation_table()
            reservation_table_rows = self._get_reservation_table_rows()

            for row in reservation_table_rows:
                row_no = number_utils.get_integer(row["RowNo"])
                col_no = number_utils.get_integer(row["ColumnNo"])
                reserve_no = string_utils.xstr(row["ReserveNo"])
                reserve_type = string_utils.xstr(row["ReserveType"])

                if not self.ui.verticalFrame.isVisible():
                    col_no = self.col_no_dict[col_no]

                self.ui.tableWidget_reservation.setItem(
                    row_no,
                    col_no,
                    QtWidgets.QTableWidgetItem(string_utils.xstr(row["Time"])),
                )
                self.ui.tableWidget_reservation.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )
                self.ui.tableWidget_reservation.item(row_no, col_no).setBackground(
                    QtGui.QColor("#EAEDED")
                )
                self.ui.tableWidget_reservation.item(row_no, col_no).setForeground(
                    QtGui.QColor("black")
                )

                self.ui.tableWidget_reservation.setItem(
                    row_no, col_no + 1, QtWidgets.QTableWidgetItem(reserve_no)
                )
                self.ui.tableWidget_reservation.item(
                    row_no, col_no + 1
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                self.ui.tableWidget_reservation.item(row_no, col_no + 1).setBackground(
                    QtGui.QColor("#EBDEF0")
                )
                self.ui.tableWidget_reservation.item(row_no, col_no + 1).setForeground(
                    QtGui.QColor("black")
                )

                if registration_utils.is_reservation_table_hide(
                    self.database, weekday, period, doctor, reserve_no
                ):
                    self.ui.tableWidget_reservation.item(row_no, col_no).setBackground(
                        QtGui.QColor("#D5F5E3")
                    )
                    self.ui.tableWidget_reservation.item(
                        row_no, col_no + 1
                    ).setBackground(QtGui.QColor("#D5F5E3"))

                if reserve_type == "初診":
                    self.ui.tableWidget_reservation.item(row_no, col_no).setForeground(
                        QtGui.QColor("red")
                    )
                elif reserve_type == "複診":
                    self.ui.tableWidget_reservation.item(row_no, col_no).setForeground(
                        QtGui.QColor("blue")
                    )
        finally:
            self.ui.tableWidget_reservation.blockSignals(False)
            self.ui.tableWidget_reservation.setUpdatesEnabled(True)

    def _get_reservation_table_rows(self):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()
        weekday_name = self._get_week_day_name()

        sql = f'''
            SELECT * FROM reservation_table
            WHERE
                (Doctor="{doctor}") AND
                (Period = "{period}") AND
                (Weekday = "{weekday_name}")
            ORDER BY RowNo, ColumnNo
        '''
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            sql = f'''
                SELECT * FROM reservation_table
                WHERE
                    (Doctor="{doctor}") AND
                    (Period = "{period}") AND
                    (ReserveNo IS NOT NULL) AND
                    (Weekday IS NULL)
                ORDER BY RowNo, ColumnNo
            '''
            rows = self.database.select_record(sql)

        return rows

    def _get_reserve_table_rows(self, start_date, end_date, period, doctor):
        sql = f'''
            SELECT * FROM reserve
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Period = "{period}" AND
                Doctor = "{doctor}"
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_reservation_row_by_no(self, rows, reserve_no):
        for row in rows:
            if row["ReserveNo"] == number_utils.get_integer(reserve_no):
                return row

        return None

    def _get_reservation_row_by_time(self, rows, reserve_time):
        for row in rows:
            if string_utils.xstr(row["ReserveDate"].time())[:5] == reserve_time:
                return row

        return None

    def _is_regist_number_all_zeroes(self, reservation_rows):
        is_all_zeroes = True
        for row in reservation_rows:
            if number_utils.get_integer(reservation_rows[0]["ReserveNo"]) > 0:
                is_all_zeroes = False
                break

        return is_all_zeroes

    def _set_reservation_allow_table(
        self, reservation_date, period, doctor, reserve_no, row_no, col_no
    ):
        sql = f'''
            SELECT * FROM reservation_allow_table
            WHERE
                ReserveDate = "{reservation_date}" AND
                Period = "{period}" AND
                Doctor = "{doctor}" AND
                ReserveNo = "{reserve_no}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            if self.ui.verticalFrame.isVisible():
                col_count = 3
            else:
                col_count = 4

            for i in range(col_count):
                item = self.ui.tableWidget_reservation.item(row_no, col_no + i)
                if item is not None:
                    item.setForeground(QtGui.QColor("white"))
                    item.setBackground(QtGui.QColor("#5a5aad"))

    def _set_reservation_data(self):
        default_color = ui_utils.get_default_color(self.ui.tableWidget_reservation)
        reservation_date = self.ui.dateEdit_reservation_date.date().toString(
            "yyyy-MM-dd"
        )
        period = self._get_period()
        doctor = self.ui.comboBox_doctor.currentText()
        start_date = f"{reservation_date} 00:00:00"
        end_date = f"{reservation_date} 23:59:59"

        year = self.ui.dateEdit_reservation_date.date().year()
        month = self.ui.dateEdit_reservation_date.date().month()
        off_day_rows = self._get_off_day_rows(year, month)
        if self._get_off_day_list(off_day_rows, reservation_date, period, doctor):
            self._clear_reservation_table()
            return

        reservation_rows = self._get_reserve_table_rows(
            start_date, end_date, period, doctor
        )
        if self._is_regist_number_all_zeroes(reservation_rows):
            search_by_no = False  # search by time 友杏的班表預約掛號都沒有預約號
        else:
            search_by_no = True  # search by number

        for row_no in range(self.ui.tableWidget_reservation.rowCount()):
            for i in range(1, self.max_reservation_table_times + 1):
                col_no = (i - 1) * len(self.table_header)
                if not self.ui.verticalFrame.isVisible():
                    col_no = self.col_no_dict[col_no]

                time = self.ui.tableWidget_reservation.item(row_no, col_no)
                if time is None:
                    continue

                reserve_no = self.ui.tableWidget_reservation.item(row_no, col_no + 1)
                if reserve_no is None or reserve_no.text() == "":
                    continue

                reserve_time = time.text()
                reserve_no = reserve_no.text()

                if search_by_no:
                    row = self._get_reservation_row_by_no(reservation_rows, reserve_no)
                else:
                    row = self._get_reservation_row_by_time(
                        reservation_rows, reserve_time
                    )

                if not self.ui.verticalFrame.isVisible():
                    remark = registration_utils.get_reserve_temp_remark(
                        self.database,
                        reservation_date,
                        period,
                        doctor,
                        row_no,
                        col_no + 3,
                    )
                    if remark not in [None, ""]:
                        self.ui.tableWidget_reservation.setItem(
                            row_no, col_no + 3, QtWidgets.QTableWidgetItem(remark)
                        )

                if row is None:
                    self._set_reservation_allow_table(
                        reservation_date, period, doctor, reserve_no, row_no, col_no
                    )
                    continue

                reserve_key = string_utils.xstr(row["ReserveKey"])
                name = string_utils.xstr(row["Name"])
                if row["Frozen"]:
                    name = "🔒" + name

                remark = string_utils.xstr(row["Remark"])

                if self.ui.verticalFrame.isVisible():
                    col_count = 3
                    self.ui.tableWidget_reservation.setItem(
                        row_no, col_no + 3, QtWidgets.QTableWidgetItem(reserve_key)
                    )
                    if remark != "":
                        name += "!"
                else:
                    col_count = 4
                    self.ui.tableWidget_reservation.setItem(
                        row_no, col_no + 3, QtWidgets.QTableWidgetItem(remark)
                    )
                    self.ui.tableWidget_reservation.setItem(
                        row_no, col_no + 4, QtWidgets.QTableWidgetItem(reserve_key)
                    )

                self.ui.tableWidget_reservation.setItem(
                    row_no, col_no + 2, QtWidgets.QTableWidgetItem(name)
                )
                if "!" in name:
                    font = QtGui.QFont()
                    # font.setItalic(True)
                    font.setBold(True)
                    self.ui.tableWidget_reservation.item(row_no, col_no + 2).setFont(
                        font
                    )

                if row["Arrival"] == "True":
                    color = "gray"
                elif string_utils.xstr(row["Source"]) == "網路預約":
                    color = "blue"
                elif string_utils.xstr(row["Source"]) == "特殊預約":
                    color = "#FF7F50"
                elif string_utils.xstr(row["Source"]) in ["視訊預約", "視訊初診預約"]:
                    color = "fuchsia"
                elif string_utils.xstr(row["Source"]) in ["初診預約", "網路初診預約"]:
                    color = "green"
                elif string_utils.xstr(row["Name"]) in ["保留預約", "不預約"]:
                    color = "red"
                else:
                    # color = 'black'
                    color = default_color

                for i in range(col_count):
                    self.ui.tableWidget_reservation.item(
                        row_no, col_no + i + 1
                    ).setForeground(QtGui.QColor(color))

        if self.system_settings.field("現場掛號給號模式") == "連續號":
            self._set_waiting_data(start_date, end_date, period, doctor)

    def _set_waiting_data(self, start_date, end_date, period, doctor):
        for row_no in range(self.ui.tableWidget_reservation.rowCount()):
            for i in range(1, self.max_reservation_table_times + 1):
                col_no = (i - 1) * len(self.table_header)
                time = self.ui.tableWidget_reservation.item(row_no, col_no)
                if time is None:
                    continue

                reserve_no = self.ui.tableWidget_reservation.item(row_no, col_no + 1)
                name = self.ui.tableWidget_reservation.item(row_no, col_no + 2)
                if reserve_no.text() == "":
                    continue
                elif name is not None and name.text() != "":
                    continue

                sql = f'''
                    SELECT * FROM wait
                    WHERE
                        DATE(CaseDate) BETWEEN "{start_date}" AND "{end_date}" AND
                        Period = "{period}" AND
                        Doctor = "{doctor}" AND
                        RegistNo = {reserve_no.text()}
                '''
                rows = self.database.select_record(sql)
                if len(rows) <= 0:
                    continue

                self.ui.tableWidget_reservation.setItem(
                    row_no, col_no + 2, QtWidgets.QTableWidgetItem("現場掛號")
                )
                for i in range(3):
                    self.ui.tableWidget_reservation.item(
                        row_no, col_no + i
                    ).setForeground(QtGui.QColor("red"))

    def _save_general_table(self):
        doctor = self.ui.comboBox_doctor.currentText()
        self._save_table(doctor)
        self.read_reservation()

    def _save_assigned_table(self):
        doctor = self.ui.comboBox_doctor.currentText()
        weekday_name = self._get_week_day_name()
        self._save_table(doctor, weekday_name)
        self.read_reservation()

    def _save_assigned_null_table(self):
        doctor = self.ui.comboBox_doctor.currentText()
        weekday_name = self._get_week_day_name()
        period = self._get_period()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("設定指定班表")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定設定{doctor}醫師 {weekday_name}{period}的預約班表表格為不預約?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料設定後後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        null_record = msg_box.exec_()
        if not null_record:
            return

        self._save_null_table(doctor, weekday_name, period)
        self.read_reservation()

    def _remove_general_table(self):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除指定班表")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定刪除{doctor}醫師{period}的預約班表表格(不含指定班表)?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        self._remove_reservation_table(doctor, period, "NULL")
        self.read_reservation()

    def _remove_assigned_table(self):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()
        weekday_name = self._get_week_day_name()

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除指定班表")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定刪除{doctor}醫師{weekday_name}{period}的預約班表表格?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        self._remove_reservation_table(doctor, period, weekday_name)
        self.read_reservation()

    def _copy_general_table(self):
        table_doctor = self.ui.comboBox_doctor.currentText()
        doctor_list = personnel_utils.get_person(
            self.database, "醫師", exclude_person=table_doctor
        )
        assign_doctor, ok = QInputDialog.getItem(
            self, "複製預約班表", "請選擇要複製給哪位醫師?", doctor_list, 0, False
        )

        if not ok:
            return

        self._save_table(assign_doctor)

        system_utils.show_message_box(
            QMessageBox.Information,
            "複製班表完成",
            f"""
                <font color="red">
                    <h3>已經將{table_doctor}醫師的預約班表複製給{assign_doctor}醫師.</h3>
                </font>
            """,
            "請選擇預約醫師欄位確認資料是否正確.",
        )

    def _save_table(self, doctor, weekday=None):
        period = self._get_period()

        self._remove_reservation_table(doctor, period, weekday)

        for row_no in range(self.ui.tableWidget_reservation.rowCount()):
            for i in range(1, self.max_reservation_table_times + 1):
                col_no = (i - 1) * len(self.table_header)
                reserve_no = self.ui.tableWidget_reservation.item(row_no, col_no + 1)
                if reserve_no is None:
                    continue

                time = self.ui.tableWidget_reservation.item(row_no, col_no)
                if time is None:
                    self.ui.tableWidget_reservation.setItem(
                        row_no, col_no, QtWidgets.QTableWidgetItem("00:00")
                    )
                    time = self.ui.tableWidget_reservation.item(row_no, col_no)

                if time.text().strip() != "" and reserve_no.text().strip() != "":
                    self._insert_reservation_table(
                        period,
                        weekday,
                        doctor,
                        row_no,
                        col_no,
                        time.text().strip(),
                        reserve_no.text().strip(),
                    )

    def _save_null_table(self, doctor, weekday, period):
        self._remove_reservation_table(doctor, period, weekday)

        for row_no in range(self.ui.tableWidget_reservation.rowCount()):
            for i in range(1, self.max_reservation_table_times + 1):
                col_no = (i - 1) * len(self.table_header)
                time = None
                reserve_no = None
                self._insert_reservation_table(
                    period, weekday, doctor, row_no, col_no, time, reserve_no
                )

    def _remove_reservation_table(self, doctor, period, weekday):
        if weekday is None:
            weekday_condition = ""
        elif weekday == "NULL":
            weekday_condition = f"AND Weekday IS {weekday}"
        else:
            weekday_condition = f'AND Weekday = "{weekday}"'

        sql = f'''
            DELETE FROM reservation_table
            WHERE
                Doctor = "{doctor}" AND
                Period = "{period}"
                {weekday_condition}
        '''
        self.database.exec_sql(sql)

    def _insert_reservation_table(
        self, period, weekday, doctor, row_no, col_no, time, reserve_no
    ):
        fields = [
            "Period",
            "Weekday",
            "Doctor",
            "RowNo",
            "ColumnNo",
            "Time",
            "ReserveNo",
        ]

        data = [period, weekday, doctor, row_no, col_no, time, reserve_no]

        self.database.insert_record("reservation_table", fields, data)

    def _get_period(self):
        period = None
        if self.ui.radioButton_period1.isChecked():
            period = "早班"
        elif self.ui.radioButton_period2.isChecked():
            period = "午班"
        elif self.ui.radioButton_period3.isChecked():
            period = "晚班"

        return period

    def _get_patient_key_from_list(self, patient_key_list):
        items = []
        for patient in patient_key_list:
            items.append(", ".join(patient))

        item, ok = QInputDialog.getItem(
            self, "選擇病患", "請選擇預約病患:", items, 0, False
        )

        if ok:
            patient_key = item.split(",")[0].strip()
        else:
            patient_key = None

        return patient_key

    def _refresh_patient_key(self):
        patient_key_list = []
        for i in range(self.parent.tabWidget_window.count()):
            if "病歷資料" in self.parent.tabWidget_window.tabText(i):
                current_tab = self.parent.tabWidget_window.widget(i)
                patient_key = string_utils.xstr(current_tab.patient_key)
                name = current_tab.medical_record["Name"]
                patient_key_list.append([patient_key, name])

        if len(patient_key_list) <= 0:
            patient_key = None
        elif len(patient_key_list) == 1:
            patient_key = patient_key_list[0][0]
        else:
            patient_key = self._get_patient_key_from_list(patient_key_list)

        return patient_key

    def _booking_reservation(self):
        if self.doctor is not None:
            if self.patient_key is not None:
                patient_key = self.patient_key
            else:
                patient_key = self._refresh_patient_key()
        else:
            patient_key = None

        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is None:
            return

        if header.text() != "姓名":
            return

        name = self.ui.tableWidget_reservation.item(current_row, current_column)
        if name is not None:  # 已被預約, 呼叫報到程序
            if name.text() in ["保留預約", "取消預約"]:
                return

            self.reservation_arrival()
            return

        time = self.ui.tableWidget_reservation.item(current_row, current_column - 2)
        reserve_no = self.ui.tableWidget_reservation.item(
            current_row, current_column - 1
        )
        if time is not None:
            time = time.text()
        else:
            time = ""

        if reserve_no is not None:
            reserve_no = reserve_no.text()
        else:
            reserve_no = ""

        if time == "" and reserve_no == "":
            return

        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()
        date = self.ui.dateEdit_reservation_date.date().toString("yyyy-MM-dd")
        reservation_date = f"{date} {time}"

        dialog = dialog_utils.get_dialog_reservation_booking(
            self,
            self.database,
            self.system_settings,
            reservation_date,
            period,
            doctor,
            reserve_no,
            patient_key,
        )

        if dialog.exec_():
            self.patient_key = None  # 清除病患資料

        self.read_reservation(
            set_combo_doctor=False
        )  # 重新讀取預約資料，其他電腦可能有變動
        dialog.deleteLater()

    def _open_past_history(self):
        current_column = self.ui.tableWidget_reservation.currentColumn()
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is None or header.text() != "姓名":
            return

        current_row = self.ui.tableWidget_reservation.currentRow()
        name = self.ui.tableWidget_reservation.item(current_row, current_column)
        if name is None:
            return

        if self.ui.verticalFrame.isVisible():
            reserve_key_item = self.ui.tableWidget_reservation.item(
                current_row, current_column + 1
            )
        else:
            reserve_key_item = self.ui.tableWidget_reservation.item(
                current_row, current_column + 2
            )

        if reserve_key_item is None:
            return

        reserve_key = reserve_key_item.text()
        if reserve_key in [None, ""]:
            return

        sql = """
            SELECT PatientKey FROM reserve
            WHERE
                ReserveKey = %s
        """
        rows = self.database.select_record(sql, (reserve_key,))
        if len(rows) <= 0:
            return

        patient_key = rows[0]["PatientKey"]
        dialog = dialog_utils.get_dialog_medical_record_past_history(
            self, self.database, self.system_settings, None, patient_key, "預約掛號"
        )

        dialog.exec_()
        dialog.deleteLater()

    # 保留預約
    def _reserve_reservation(self):
        current_column = self.ui.tableWidget_reservation.currentColumn()
        current_row = self.ui.tableWidget_reservation.currentRow()

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is None:
            return

        if header.text() != "姓名":
            return

        if self.ui.action_reserve_reservation.text() == "取消保留":
            reserve_key = self._get_reserve_key_by_table(current_row, current_column)
            if reserve_key is None:
                return

            self.database.exec_sql(f"""
                DELETE FROM reserve
                WHERE
                    ReserveKey = {reserve_key}
            """)
            if self.system_settings.field("hainachuan") == "Y":  # 取消虛擬預約
                patient_key = "0"
                hainachuan_utils.cancel_reservation(
                    system_settings=self.system_settings,
                    patient_key=patient_key,
                    reserve_key=reserve_key,
                )
            self.read_reservation()
            self._reservation_table_item_changed()
            return

        time = self.ui.tableWidget_reservation.item(current_row, current_column - 2)
        reserve_no = self.ui.tableWidget_reservation.item(
            current_row, current_column - 1
        )
        if time is not None:
            time = time.text()
        else:
            time = ""

        if reserve_no is not None:
            reserve_no = reserve_no.text()
        else:
            reserve_no = ""

        if time == "" and reserve_no == "":
            return

        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()
        date = self.ui.dateEdit_reservation_date.date().toString("yyyy-MM-dd")
        reservation_date = f"{date} {time}"
        room = registration_utils.get_room(self.database, period, doctor)

        registrar = self.system_settings.field("使用者")
        create_time = date_utils.now_to_str()
        fields = [
            "PatientKey",
            "Name",
            "ReserveDate",
            "Period",
            "Room",
            "Doctor",
            "ReserveNo",
            "Source",
            "Registrar",
            "CreateTime",
        ]
        data = [
            "0",
            "保留預約",
            reservation_date,
            period,
            room,
            doctor,
            reserve_no,
            None,
            registrar,
            create_time,
        ]
        reserve_key = self.database.insert_record("reserve", fields, data)
        if self.system_settings.field("hainachuan") == "Y":  # 虛擬預約, 卡位用
            hainachuan_utils.add_reservation(
                self.database, self.system_settings, reserve_key
            )

        self.read_reservation()

    def _tab_changed(self, i):
        self.tab_name = self.ui.tabWidget_reservation.tabText(i)

        if self.tab_name == "預約一覽表":
            self.ui.action_save_general_table.setEnabled(True)
            self.ui.action_save_assigned_table.setEnabled(True)
            self.ui.action_remove_assigned_table.setEnabled(True)

            self.read_reservation()
            self.ui.tableWidget_reservation.setCurrentCell(0, 0)
            self.ui.tableWidget_reservation.setFocus()

            self._reservation_table_item_changed()
        else:
            self._read_reservation_list()

            self.ui.action_add_reservation.setEnabled(False)
            self.ui.action_reserve_reservation.setEnabled(False)
            self.ui.action_save_general_table.setEnabled(False)
            self.ui.action_save_assigned_table.setEnabled(False)
            self.ui.action_remove_assigned_table.setEnabled(False)
            # database.ui.action_reservation_arrival.setEnabled(False)

            if self.table_widget_reservation_list.row_count() > 0:
                enabled = True
            else:
                enabled = False

            self.ui.action_cancel_reservation.setEnabled(enabled)
            self.ui.action_modify_reservation.setEnabled(enabled)
            self.ui.action_print_reservation.setEnabled(enabled)
            self._set_permission()

    def _read_reservation_list(self):
        self.ui.tableWidget_reservation_list.setRowCount(1)

        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")

        arrival = ""
        if self.ui.radioButton_arrival1.isChecked():
            arrival = 'AND Arrival = "False"'
        elif self.ui.radioButton_arrival2.isChecked():
            arrival = 'AND Arrival = "True"'

        doctor_condition = ""
        doctor = self.ui.comboBox_list_doctor.currentText()
        if doctor != "全部":
            doctor_condition = f'AND Doctor = "{doctor}"'

        period_condition = ""
        period = self.ui.comboBox_period.currentText()
        if period != "全部":
            period_condition = f'AND Period = "{period}"'

        period_list = string_utils.xstr(nhi_utils.PERIOD)[1:-1]
        sql = f'''
            SELECT reserve.*, patient.Birthday, patient.Telephone, patient.Cellphone FROM reserve
                LEFT JOIN patient ON patient.PatientKey = reserve.PatientKey
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}"
                {period_condition}
                {doctor_condition}
                {arrival}
            ORDER BY DATE(ReserveDate), FIELD(Period, {period_list}), ReserveNo
        '''

        self.table_widget_reservation_list.set_db_data(sql, self._set_table_data)
        if self.table_widget_reservation_list.row_count() > 0:
            self.ui.action_reservation_arrival.setEnabled(True)
        else:
            self.ui.action_reservation_arrival.setEnabled(True)

        self._set_permission()

    def _set_table_data(self, row_no, row_data):
        if string_utils.xstr(row_data["Arrival"]) == "True":
            arrival = "已報到"
        else:
            arrival = "未報到"

        reservation_datetime = string_utils.xstr(row_data["ReserveDate"])
        reservation_date = reservation_datetime[:10]
        reservation_time = reservation_datetime[11:16]
        patient_key = string_utils.xstr(row_data["PatientKey"])
        name = string_utils.xstr(row_data["Name"])
        birthday = string_utils.xstr(row_data["Birthday"])
        telephone = string_utils.xstr(row_data["Telephone"])
        cellphone = string_utils.xstr(row_data["Cellphone"])

        if string_utils.xstr(row_data["Source"]) in [
            "網路初診",
            "網路初診預約",
            "初診預約",
            "視訊初診",
            "視訊初診預約",
        ]:
            patient_key = string_utils.xstr(row_data["Source"])[:4]
            birthday = patient_utils.get_temp_patient(
                self.database, row_data["PatientKey"], "Birthday"
            )
            birthday = string_utils.xstr(birthday)
            telephone = patient_utils.get_temp_patient(
                self.database, row_data["PatientKey"], "PhoneNo"
            )
            cellphone = patient_utils.get_temp_patient(
                self.database, row_data["PatientKey"], "Cellphone"
            )

        reservation_list_data = [
            string_utils.xstr(row_data["ReserveKey"]),
            reservation_date,
            reservation_time,
            string_utils.xstr(row_data["Period"]),
            patient_key,
            name,
            birthday,
            string_utils.xstr(row_data["Doctor"]),
            string_utils.xstr(row_data["Room"]),
            string_utils.xstr(row_data["ReserveNo"]),
            arrival,
            string_utils.xstr(row_data["Source"]),
            string_utils.xstr(row_data["Registrar"]),
            telephone,
            cellphone,
            string_utils.xstr(row_data["CreateTime"]),
            string_utils.xstr(row_data["Remark"]),
        ]

        if self.show_last_case_remark == "Y":
            try:
                last_case_remark = self._get_last_case_remark(patient_key)
            except Exception:
                last_case_remark = None

            reservation_list_data.append(last_case_remark)

        for column in range(len(reservation_list_data)):
            self.ui.tableWidget_reservation_list.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(reservation_list_data[column]),
            )
            if column in [4, 9]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif column in [2, 3, 8]:
                self.ui.tableWidget_reservation_list.item(
                    row_no, column
                ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        if string_utils.xstr(row_data["Source"]) == "網路預約":
            color = "blue"
        elif string_utils.xstr(row_data["Source"]) in ["視訊預約", "視訊初診預約"]:
            color = "fuchsia"
        elif string_utils.xstr(row_data["Source"]) in ["初診預約", "網路初診預約"]:
            color = "green"
        elif name == "保留預約":
            color = "red"
        else:
            color = "black"

        for col_no in range(self.ui.tableWidget_reservation_list.columnCount()):
            item = self.ui.tableWidget_reservation_list.item(row_no, col_no)
            if item is not None:
                item.setForeground(QtGui.QColor(color))

    def _get_last_case_remark(self, patient_key):
        if patient_key in ["網路初診", "初診預約", "視訊初診", "視訊初診預約"]:
            return None

        sql = f"""
            SELECT Remark FROM cases
            WHERE
                PatientKey = {patient_key}
            ORDER BY CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        remark = string_utils.get_str(row["Remark"], "utf8")

        return remark

    def _get_reserve_key_by_table(
        self, row_no, col_no, warning=False, allow_arrival=False
    ):
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(col_no)
        if header is None:
            return None

        header = header.text()
        if header != "姓名":
            return None

        name = self.ui.tableWidget_reservation.item(row_no, col_no)
        if name is None:
            return None

        if self.ui.verticalFrame.isVisible():
            reserve_key = self.ui.tableWidget_reservation.item(row_no, col_no + 1)
        else:
            reserve_key = self.ui.tableWidget_reservation.item(row_no, col_no + 2)

        if reserve_key is None:
            return None

        if not allow_arrival:
            arrival = self._check_reservation_arrival(reserve_key.text())
            if arrival:  # 已報到
                return None

        reserve_key = reserve_key.text()

        return reserve_key

    def _get_name_by_table(self, row_no, col_no):
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(col_no)
        if header is None:
            return None

        header = header.text()
        if header != "姓名":
            return None

        name = self.ui.tableWidget_reservation.item(row_no, col_no)
        if name is None:
            return None

        return name.text()

    def _cancel_reservation(self):
        if self.tab_name == "預約一覽表":
            self._cancel_reservation_by_table()
        else:
            self._cancel_reservation_by_list()

    def _lock_reservation(self):
        if self.tab_name == "預約一覽表":
            self._lock_reservation_by_table()
        else:
            self._lock_reservation_by_list()

    def _cancel_reservation_by_table(self):
        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()

        reserve_key = self._get_reserve_key_by_table(current_row, current_column, True)
        if reserve_key is None:
            return

        name = self._get_name_by_table(current_row, current_column)
        if self._delete_reserve_record(reserve_key, name):
            self.read_reservation()

    def _cancel_reservation_by_list(self):
        reserve_key = self.table_widget_reservation_list.field_value(0)
        name = self.table_widget_reservation_list.field_value(5)
        if self._delete_reserve_record(reserve_key, name):
            self._read_reservation_list()

    def _lock_reservation_by_table(self):
        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()

        reserve_key = self._get_reserve_key_by_table(current_row, current_column, True)
        if reserve_key is None:
            return

        name = self._get_name_by_table(current_row, current_column)
        if self._lock_reserve_record(reserve_key, name):
            self.read_reservation()

    def _lock_reservation_by_list(self):
        reserve_key = self.table_widget_reservation_list.field_value(0)
        name = self.table_widget_reservation_list.field_value(4)
        if self._lock_reserve_record(reserve_key, name):
            self._read_reservation_list()

    def _modify_reservation(self):
        if self.tab_name == "預約一覽表":
            i = 0
            current_row = self.ui.tableWidget_reservation.currentRow()
            current_column = self.ui.tableWidget_reservation.currentColumn()
            reserve_key = self._get_reserve_key_by_table(
                current_row, current_column, True
            )
        else:
            i = 1
            reserve_key = self.table_widget_reservation_list.field_value(0)

        if reserve_key is None:
            return

        if self._modify_reserve_record(reserve_key):
            self._tab_changed(i)

    def _modify_reserve_record(self, reserve_key):
        dialog = dialog_utils.get_dialog_reservation_modify(
            self, self.database, self.system_settings, reserve_key
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return False

        dialog.deleteLater()

        return True

    def _delete_reserve_record(self, reserve_key, name):
        patient_key = self._get_patient_key(reserve_key)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("取消預約掛號")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定取消病歷號{patient_key}{name}的預約掛號?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！預約掛號取消後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        cancel_reservation = msg_box.exec_()
        if not cancel_reservation:
            return False

        if self.system_settings.field("alleypin") == "Y":
            alleypin_utils.cancel_reservation_alleypin_appointments(
                self.database, self.system_settings, reserve_key
            )

        if self.system_settings.field("hainachuan") == "Y":
            hainachuan_utils.cancel_reservation(
                system_settings=self.system_settings,
                patient_key=patient_key,
                reserve_key=reserve_key,
            )

        first_reserve_row = self._check_reservation_first_visit(
            reserve_key
        )  # 檢查是否為初診預約
        if first_reserve_row is not None:
            self.database.exec_sql(f"""
                DELETE FROM temp_patient
                WHERE
                    TempPatientKey = {patient_key}
            """)

        sql = f"SELECT * FROM reserve WHERE ReserveKey = {reserve_key}"
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            backup_json = db_utils.mysql_to_json(row)
        else:
            backup_json = None

        fields = [
            "CancelDate",
            "ReserveKey",
            "PatientKey",
            "Name",
            "Source",
            "Remark",
            "ReserveBackup",
        ]
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        registrar = self.system_settings.field("使用者")

        data = [
            current_time,
            row["ReserveKey"],
            row["PatientKey"],
            row["Name"],
            row["Source"],
            f"使用者: {registrar} 在醫療系統內取消",
            backup_json,
        ]
        try:
            self.database.insert_record("reserve_cancel", fields, data)
        except Exception:
            pass

        self.database.exec_sql(f"""
            DELETE FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """)

        return True

    def _reservation_table_item_changed(self):
        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()

        reserve_key = self._get_reserve_key_by_table(current_row, current_column)
        name = self.ui.tableWidget_reservation.item(current_row, current_column)

        if reserve_key is None:
            enabled = False
        else:
            enabled = True

        self.ui.action_reserve_reservation.setEnabled(True)
        if name is not None and name.text() not in [
            "保留預約",
            "保留預約!",
            "取消保留",
        ]:
            self.ui.action_reserve_reservation.setEnabled(False)
        else:
            enabled = False

        self.ui.action_reserve_reservation.setText("保留預約")
        if name is not None and "保留預約" in name.text():
            self.ui.action_reserve_reservation.setText("取消保留")

        self.ui.action_cancel_reservation.setEnabled(enabled)
        self.ui.action_modify_reservation.setEnabled(enabled)
        self.ui.action_print_reservation.setEnabled(enabled)
        self.ui.action_reservation_arrival.setEnabled(enabled)

        self._set_action_add_reservation()

        reserve_date = self.ui.dateEdit_reservation_date.date()
        if reserve_date != datetime.datetime.today():
            self.ui.action_reservation_arrival.setEnabled(False)

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is not None and header.text() in ["時間", "診號", "姓名"]:
            weekday = self._get_week_day_name()
            period = self.ui.comboBox_period.currentText()
            doctor = self.ui.comboBox_list_doctor.currentText()

            if header.text() == "時間":
                col_no = current_column + 1
            elif header.text() == "診號":
                col_no = current_column
            elif header.text() == "姓名":
                col_no = current_column - 1
            else:
                col_no = current_column

            reserve_no_item = self.ui.tableWidget_reservation.item(current_row, col_no)
            if reserve_no_item is not None:
                reserve_no = reserve_no_item.text()
                if registration_utils.is_reservation_table_hide(
                    self.database, weekday, period, doctor, reserve_no
                ):
                    self.ui.action_hide_on_web.setText("網頁顯示")
                else:
                    self.ui.action_hide_on_web.setText("網頁隱藏")

        self._set_permission()

    def _reservation_item_changed(self):
        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is None or header.text() != "備註":
            return

        remark_item = self.ui.tableWidget_reservation.item(current_row, current_column)
        if remark_item is None:
            return

        remark = remark_item.text()
        reserve_key_time = self.ui.tableWidget_reservation.item(
            current_row, current_column + 1
        )

        if reserve_key_time is None:
            self._write_temp_remark(current_row, current_column, remark)
            return

        reserve_key = reserve_key_time.text()
        if remark == "":
            sql = f"""
                UPDATE reserve
                SET
                    Remark = NULL
                WHERE
                    ReserveKey = {reserve_key}
            """
        else:
            sql = f'''
                UPDATE reserve
                SET
                    Remark = "{remark}"
                WHERE
                    ReserveKey = {reserve_key}
            '''
        self.database.exec_sql(sql)

    def _write_temp_remark(self, row_no, col_no, remark):
        reservation_date = self.ui.dateEdit_reservation_date.date().toString(
            "yyyy-MM-dd"
        )
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()

        registration_utils.set_reserve_temp_remark(
            self.database, reservation_date, period, doctor, row_no, col_no, remark
        )

    def _set_action_add_reservation(self):
        current_row = self.ui.tableWidget_reservation.currentRow()
        current_column = self.ui.tableWidget_reservation.currentColumn()

        self.ui.action_add_reservation.setEnabled(False)
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is not None and header.text() == "姓名":
            time = self.ui.tableWidget_reservation.item(current_row, current_column - 2)
            reservation_no = self.ui.tableWidget_reservation.item(
                current_row, current_column - 1
            )
            name = self.ui.tableWidget_reservation.item(current_row, current_column)

            if time is not None:
                time = time.text()
            else:
                time = ""

            if reservation_no is not None:
                reservation_no = reservation_no.text()
            else:
                reservation_no = ""

            if name is not None:
                name = name.text()
            else:
                name = ""

            if time != "" and reservation_no != "" and name == "":
                self.ui.action_add_reservation.setEnabled(True)

        self._set_permission()

    def reservation_arrival(self):
        if self.doctor is not None:  # 醫師預約不可報到
            return

        if self.tab_name == "預約一覽表":
            self._arrival_by_table()
        else:
            self._arrival_by_list()

    # 預約一覽表報到
    def _arrival_by_table(self):
        current_column = self.ui.tableWidget_reservation.currentColumn()
        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is None or header.text() != "姓名":
            return

        current_row = self.ui.tableWidget_reservation.currentRow()
        name = self.ui.tableWidget_reservation.item(current_row, current_column)
        if name is None:
            return

        if self.ui.verticalFrame.isVisible():
            reserve_key_item = self.ui.tableWidget_reservation.item(
                current_row, current_column + 1
            )
        else:
            reserve_key_item = self.ui.tableWidget_reservation.item(
                current_row, current_column + 2
            )

        if reserve_key_item is None:
            return

        reserve_key = reserve_key_item.text()
        name = name.text()

        self._ready_to_arrival(reserve_key, name)

    # 預約名單報到
    def _arrival_by_list(self):
        if not self.ui.action_reservation_arrival.isEnabled():
            return

        current_row = self.ui.tableWidget_reservation_list.currentRow()
        reserve_key_item = self.ui.tableWidget_reservation_list.item(current_row, 0)
        if reserve_key_item is None:
            return

        name_item = self.ui.tableWidget_reservation_list.item(current_row, 4)
        if name_item is None:
            return

        reserve_key = reserve_key_item.text()
        name = name_item.text()

        arrival = self._check_reservation_arrival(reserve_key)
        if arrival:  # 已報到
            return

        self._ready_to_arrival(reserve_key, name)

    def _get_patient_key(self, reserve_key):
        sql = f"""
            SELECT PatientKey FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        patient_key = number_utils.get_integer(row["PatientKey"])

        return patient_key

    def _ready_to_arrival(self, reserve_key, name):
        arrival = self._check_reservation_arrival(reserve_key)
        if arrival:  # 已報到
            return

        first_reserve_row = self._check_reservation_first_visit(
            reserve_key
        )  # 檢查是否為初診預約報到
        if first_reserve_row is not None:
            self._first_visit_arrival(first_reserve_row)
        else:
            self._normal_arrival(reserve_key, name)

    def _is_first_visit(self, patient_key, name):
        sql = f'''
            SELECT * FROM patient
            WHERE
                PatientKey = {patient_key} AND
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        if rows:
            return False

        sql = f'''
            SELECT * FROM temp_patient
            WHERE
                TempPatientKey = {patient_key} AND
                Name = "{name}"
        '''
        rows = self.database.select_record(sql)
        if rows:
            return True
        else:
            return False

    def _check_reservation_first_visit(self, reserve_key):
        if reserve_key is None:
            return None

        sql = f"""
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]

        patient_key = string_utils.xstr(row["PatientKey"])
        name = string_utils.xstr(row["Name"])

        if self._is_first_visit(patient_key, name):
            sql = f"""
                SELECT ID FROM temp_patient
                WHERE
                    TempPatientKey = {row["PatientKey"]}
            """
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return None

            temp_patient_row = rows[0]
            temp_patient_id = string_utils.xstr(temp_patient_row["ID"])
            if temp_patient_id != "":
                sql = f'''
                    SELECT PatientKey FROM patient
                    WHERE
                        ID = "{temp_patient_id}"
                '''
                rows = self.database.select_record(sql)
                if len(rows) > 0:  # 已經有病患資料了
                    patient_row = rows[0]
                    sql = f"""
                        UPDATE reserve SET PatientKey = {patient_row["PatientKey"]}
                        WHERE
                            ReserveKey = {reserve_key}
                    """
                    self.database.exec_sql(sql)
                    return None

            return row
        else:
            return None

    def _check_arrival_late(self, reserve_key):
        sql = f"""
            SELECT Doctor, ReserveNo FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]

        reserve_no = number_utils.get_integer(row["ReserveNo"])
        doctor = string_utils.xstr(row["Doctor"])
        period = registration_utils.get_current_period(self.system_settings)

        # DoctorDone = True 只查已經看完診的，還在候診的不算過號
        sql = f'''
            SELECT RegistNo FROM wait
            WHERE
                Period = "{period}" AND
                Doctor = "{doctor}" AND
                RegistNo > 0 AND
                DoctorDone = "True"
            ORDER BY RegistNo DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return False

        row = rows[0]
        regist_no = number_utils.get_integer(row["RegistNo"])

        if regist_no > reserve_no:  # 過號
            return True
        else:
            return False

    def _is_arrival_ontime(self, reserve_key):
        ontime = True

        sql = f"""
            SELECT ReserveDate FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ontime

        row = rows[0]

        reserve_time = row["ReserveDate"].strftime("%Y-%m-%d %H:%M")
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        if current_time > reserve_time:
            ontime = False

        return ontime

    def _normal_arrival(self, reserve_key, name):
        information = "注意！預約掛號報到後, 將無法回復!"

        ontime = self._is_arrival_ontime(reserve_key)
        if self.system_settings.field("預約遲到寫入掛號備註") == "Y" and not ontime:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("預約報到遲到")
            msg_box.setText(f"""
                <font size='4' color='red'>
                    <b>{name}預約掛號報到已經遲到，是否繼續報到?</b>
                </font>
            """)
            msg_box.setInformativeText(information)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("繼續報到"), QMessageBox.YesRole)
            arrival = msg_box.exec_()
            if arrival:
                self.parent.registration_arrival(
                    reserve_key,
                    late=True,
                    late_remark="預約報到遲到",
                    vhc_ic_card=self.vhc_ic_card,
                )
                self.vhc_ic_card = None

            return

        arrival_late = self._check_arrival_late(reserve_key)
        if self.system_settings.field("預約過號寫入掛號備註") == "Y" and arrival_late:
            if self.system_settings.field("預約過號顯示過號序號") == "Y":
                late_label = self._get_late_label()
            else:
                late_label = "過號"

            self.parent.registration_arrival(
                reserve_key,
                late=True,
                late_remark=late_label,
                vhc_ic_card=self.vhc_ic_card,
            )
            self.vhc_ic_card = None

            return

        if arrival_late and ontime:
            arrival_late = False

        if arrival_late:
            information = """
                <br>
                <font size='3' color='red'>
                    注意! 預約掛號報到已經過號!<br>
                </font>
            """

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("預約掛號報到")
        msg_box.setText(f"""
            <font size='4' color='blue'>
                <b>{name}確定預約掛號報到?</b>
            </font>
        """)
        msg_box.setInformativeText(information)
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        arrival = msg_box.exec_()
        if not arrival:
            return

        self.parent.registration_arrival(
            reserve_key, late=arrival_late, vhc_ic_card=self.vhc_ic_card
        )
        self.vhc_ic_card = None

    def _get_late_label(self):
        sql = """
            SELECT Remark FROM wait
            WHERE
                Remark LIKE "過號-%"
            ORDER BY Remark DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return "過號-1"

        row = rows[0]
        last_late_label = string_utils.xstr(row["Remark"])
        late_number = number_utils.get_integer(last_late_label.split("過號-")[1])

        return f"過號-{late_number + 1}"

    def _first_visit_arrival(self, first_reserve_row):
        temp_patient_key = first_reserve_row["PatientKey"]
        sql = f"""
            SELECT * FROM temp_patient
            WHERE
                TempPatientKey = {temp_patient_key}
        """
        temp_patient_rows = self.database.select_record(sql)
        if len(temp_patient_rows) <= 0:  # 可能已經報到且有病患基本資料
            self._normal_arrival(
                first_reserve_row["ReserveKey"], first_reserve_row["Name"]
            )
            return

        temp_patient_row = temp_patient_rows[0]

        name = string_utils.xstr(temp_patient_row["Name"])
        patient_id = string_utils.xstr(temp_patient_row["ID"])
        birthday = string_utils.xstr(temp_patient_row["Birthday"])
        phone_no = string_utils.xstr(temp_patient_row["PhoneNo"])
        cellphone = string_utils.xstr(temp_patient_row["Cellphone"])
        address = string_utils.xstr(temp_patient_row["Address"])

        if name != first_reserve_row["Name"]:  # 已經有基本資料, 與初診基本資料不同
            self._normal_arrival(
                first_reserve_row["ReserveKey"], first_reserve_row["Name"]
            )
            return

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("網路初診預約掛號報到")
        msg_box.setText(f"""
            <font size="5" color="blue">
                <b>{name}確定初診預約掛號報到?</b>
            </font><br>
            請確認以下的初診預約資料是否正確:<br><br>
            病患姓名: {name}<br>
            身分證號: {patient_id}<br>
            出生日期: {birthday}<br>
            聯絡電話: {phone_no}<br>
            行動電話: {cellphone}<br>
            居住地址: {address}<br>
        """)
        msg_box.setInformativeText(
            "注意！初診預約掛號報到後, 將會新增一筆正式的病患基本資料!"
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        arrival = msg_box.exec_()
        if not arrival:
            return

        new_patient_key = self._update_new_patient(temp_patient_row)

        if new_patient_key is None:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "插錯健保卡",
                f'<font color="red"><h3>此健保卡非{name}的健保卡, 請重新插入正確的健保卡!</h3></font>',
                "請確認插入的健保卡是否正確.",
            )
            return

        reserve_key = first_reserve_row["ReserveKey"]
        sql = f"""
            UPDATE reserve
            SET
                PatientKey = {new_patient_key}
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)
        self.database.exec_sql(
            f"DELETE FROM temp_patient WHERE TempPatientKey = {temp_patient_key}"
        )  # 刪除初診預約病患資料

        self.parent.registration_arrival(reserve_key, vhc_ic_card=self.vhc_ic_card)
        self.vhc_ic_card = None

    def _update_new_patient(self, temp_patient_row):
        try:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        except Exception:
            ic_card = None

        if ic_card is not None and ic_card.read_basic_data(show_error=False):
            if (
                string_utils.xstr(temp_patient_row["ID"])
                != ic_card.basic_data["patient_id"]
            ):
                return None

            patient_id = ic_card.basic_data["patient_id"]
            patient_birthday = ic_card.basic_data["birthday"]
        else:
            patient_id = string_utils.xstr(temp_patient_row["ID"])
            patient_birthday = string_utils.xstr(temp_patient_row["Birthday"])

        gender = None
        if len(patient_id) >= 2:
            gender = patient_utils.get_gender(patient_id[1])

        remark = string_utils.get_str(temp_patient_row["Remark"], "utf8")
        if "json" in remark:
            remark = None

        field = [
            "Name",
            "ID",
            "Gender",
            "Birthday",
            "Telephone",
            "Cellphone",
            "Address",
            "Remark",
            "InitDate",
        ]

        data = [
            string_utils.xstr(temp_patient_row["Name"]),
            patient_id,
            gender,
            patient_birthday,
            string_utils.xstr(temp_patient_row["PhoneNo"]),
            string_utils.xstr(temp_patient_row["Cellphone"]),
            string_utils.xstr(temp_patient_row["Address"]),
            remark,
            date_utils.now_to_str(),
        ]
        new_patient_key = self.database.insert_record("patient", field, data)

        remark = string_utils.get_str(temp_patient_row["Remark"], "utf-8")
        if remark not in ["", "None"] and "json" in remark:
            remark = json.loads(remark)
            email = remark["email"]
            occupation = remark["occupation"]
            history = remark["history"]
            allergy = remark["allergy"]

            # if email not in [None, ""]:
            #     self.database.exec_sql(
            #         f'UPDATE patient SET Email = "{email}" WHERE PatientKey = {new_patient_key}'
            #     )
            # if occupation not in [None, ""]:
            #     self.database.exec_sql(
            #         f'UPDATE patient SET Occupation = "{occupation}" WHERE PatientKey = {new_patient_key}'
            #     )
            # if history not in [None, ""]:
            #     self.database.exec_sql(
            #         f'UPDATE patient SET History = "{history}" WHERE PatientKey = {new_patient_key}'
            #     )
            # if allergy not in [None, ""]:
            #     self.database.exec_sql(
            #         f'UPDATE patient SET Allergy = "{allergy}" WHERE PatientKey = {new_patient_key}'
            #     )

            update_fields = []
            update_values = []

            for field_name, value in [
                ("Email", email),
                ("Occupation", occupation),
                ("History", history),
                ("Allergy", allergy),
            ]:
                if value not in [None, ""]:
                    update_fields.append(f"{field_name} = %s")
                    update_values.append(value)

            if update_fields:
                sql = f"UPDATE patient SET {', '.join(update_fields)} WHERE PatientKey = %s"
                update_values.append(new_patient_key)
                self.database.exec_sql(sql, params=update_values)

        return new_patient_key

    def _check_reservation_arrival(self, reserve_key):
        arrival = False

        sql = f"""
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return arrival

        if rows[0]["Arrival"] == "True":
            arrival = True

        return arrival

    def set_reservation_arrival(self, reserve_key=None, vhc_ic_card=None):
        self.vhc_ic_card = vhc_ic_card

        sql = f"""
            SELECT * FROM reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        row = rows[0]

        self.ui.dateEdit_reservation_date.setDate(datetime.datetime.today())
        period = string_utils.xstr(row["Period"])
        self._set_radio_button_period(period)
        self.ui.comboBox_doctor.setCurrentText(string_utils.xstr(row["Doctor"]))
        self.read_reservation()

        current_row, current_col = 0, 0
        for row_no in range(self.ui.tableWidget_reservation.rowCount()):
            for col_no in range(self.ui.tableWidget_reservation.columnCount()):
                reservation_key = self.ui.tableWidget_reservation.item(row_no, col_no)
                if (
                    reservation_key is not None
                    and reservation_key.text() == string_utils.xstr(reserve_key)
                ):
                    current_row = row_no
                    current_col = col_no - 1
                    break

        self.ui.tableWidget_reservation.setCurrentCell(current_row, current_col)
        self.ui.tableWidget_reservation.setFocus()

    def _reservation_list_changed(self):
        reserve_key = self.table_widget_reservation_list.field_value(0)
        if reserve_key is None:
            return

        arrival = self._check_reservation_arrival(reserve_key)
        if arrival:  # 已報到
            enabled = False
        else:
            enabled = True

        # self.ui.action_cancel_reservation.setEnabled(enabled)
        self.ui.action_modify_reservation.setEnabled(enabled)
        self.ui.action_print_reservation.setEnabled(enabled)
        self._set_permission()

        enabled = True
        reserve_date = self.ui.tableWidget_reservation_list.item(
            self.ui.tableWidget_reservation_list.currentRow(), 1
        )

        if reserve_date is None:
            enabled = False

        reserve_date = reserve_date.text()[:10]
        today = datetime.datetime.today().strftime("%Y-%m-%d")
        if reserve_date != today:
            enabled = False

        self.ui.action_reservation_arrival.setEnabled(enabled)
        self._set_permission()

    def _reservation_query(self):
        dialog = dialog_utils.get_dialog_reservation_query(
            self, self.database, self.system_settings
        )
        dialog.exec()
        dialog.deleteLater()

    def _set_calendar(self):
        for i in range(0, self.ui.tableWidget_calendar.columnCount()):
            self.ui.tableWidget_calendar.setColumnWidth(i, 111)

        for i in range(0, self.ui.tableWidget_calendar.rowCount()):
            self.ui.tableWidget_calendar.setRowHeight(i, 111)

        calendar_list = {
            0: [0, 0],
            1: [0, 1],
            2: [0, 2],
            3: [0, 3],
            4: [0, 4],
            5: [0, 5],
            6: [0, 6],
            7: [1, 0],
            8: [1, 1],
            9: [1, 2],
            10: [1, 3],
            11: [1, 4],
            12: [1, 5],
            13: [1, 6],
            14: [2, 0],
            15: [2, 1],
            16: [2, 2],
            17: [2, 3],
            18: [2, 4],
            19: [2, 5],
            20: [2, 6],
            21: [3, 0],
            22: [3, 1],
            23: [3, 2],
            24: [3, 3],
            25: [3, 4],
            26: [3, 5],
            27: [3, 6],
            28: [4, 0],
            29: [4, 1],
            30: [4, 2],
            31: [4, 3],
            32: [4, 4],
            33: [4, 5],
            34: [4, 6],
            35: [5, 0],
            36: [5, 1],
            37: [5, 2],
            38: [5, 3],
            39: [5, 4],
            40: [5, 5],
            41: [5, 6],
        }

        year = self.ui.dateEdit_reservation_date.date().year()
        month = self.ui.dateEdit_reservation_date.date().month()
        doctor = self.ui.comboBox_doctor.currentText()
        self.ui.label_calendar.setText(
            f"<b>{doctor}</b>醫師 <b>{year}</b>年<b>{month}</b>月份 預約狀況一覽表"
        )

        start_day = datetime.datetime(year, month, 1).weekday()
        if start_day == 6:
            start_day = 0
        else:
            start_day += 1

        week_list = [
            "星期日",
            "星期一",
            "星期二",
            "星期三",
            "星期四",
            "星期五",
            "星期六",
        ]
        period_list = ["日期", "早班", "午班", "晚班"]

        self.ui.tableWidget_calendar.clear()
        for i in range(len(week_list)):
            item = QtWidgets.QTableWidgetItem(week_list[i])
            item.setForeground(QtGui.QBrush(QtGui.QColor("black")))  # 字體顏色

            self.ui.tableWidget_calendar.setHorizontalHeaderItem(i, item)

        for i in range(self.ui.tableWidget_calendar.rowCount()):
            item = QtWidgets.QTableWidgetItem("\n".join(period_list))
            item.setForeground(QtGui.QBrush(QtGui.QColor("black")))

            self.ui.tableWidget_calendar.setVerticalHeaderItem(i, item)

        current_month = datetime.date.today().month
        today = datetime.date.today().day

        reservation_rows = self._get_reservation_rows(year, month)
        off_day_rows = self._get_off_day_rows(year, month)

        last_day = calendar.monthrange(year, month)[1]
        for i in range(0, last_day):
            day = i + 1
            reservation_date = f"{year}-{month:0>2}-{day:0>2}"
            reservation1 = self._get_reservation_status(
                reservation_rows, off_day_rows, reservation_date, "早班", doctor
            )
            reservation2 = self._get_reservation_status(
                reservation_rows, off_day_rows, reservation_date, "午班", doctor
            )
            reservation3 = self._get_reservation_status(
                reservation_rows, off_day_rows, reservation_date, "晚班", doctor
            )

            row_no = calendar_list[start_day + i][0]
            col_no = calendar_list[start_day + i][1]
            content = f"{day}\n{reservation1}\n{reservation2}\n{reservation3}"
            self.ui.tableWidget_calendar.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(content)
            )
            color = "white"
            if current_month == month and i == today - 1:
                color = "lightSteelBlue"
            elif calendar_list[start_day + i][1] == 0:
                color = "#EBDEF0"

            # default_color = ui_utils.get_default_color(self.ui.tableWidget_calendar)
            self.ui.tableWidget_calendar.item(row_no, col_no).setBackground(
                QtGui.QColor(color)
            )
            # self.ui.tableWidget_calendar.item(row_no, col_no).setForeground(default_color)
            self.ui.tableWidget_calendar.item(row_no, col_no).setForeground(
                QtGui.QColor("black")
            )

    def _get_reservation_rows(self, year, month):
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:0>2}-01 00:00:00"
        end_date = f"{year}-{month:0>2}-{last_day:0>2} 23:59:59"

        sql = f'''
            SELECT ReserveDate, Period, Doctor FROM reserve
            WHERE
                (ReserveDate BETWEEN "{start_date}" AND "{end_date}") AND
                (Name != "保留預約")
        '''
        rows = self.database.select_record(sql)

        return rows

    def _get_off_day_rows(self, year, month):
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:0>2}-01"
        end_date = f"{year}-{month:0>2}-{last_day:0>2}"

        sql = f'''
            SELECT OffDate, Period, Doctor FROM off_day_list
            WHERE
                (OffDate BETWEEN "{start_date}" AND "{end_date}")
        '''
        rows = self.database.select_record(sql)

        return rows

    @staticmethod
    def _get_off_day_list(off_day_rows, reservation_date, period, doctor):
        for row in off_day_rows:
            year = row["OffDate"].year
            month = row["OffDate"].month
            day = row["OffDate"].day
            off_period = string_utils.xstr(row["Period"])
            off_doctor = string_utils.xstr(row["Doctor"])

            off_date = f"{year}-{month:0>2}-{day:0>2}"

            if off_doctor == "":
                if reservation_date == off_date and period == off_period:
                    return True
            else:
                if (
                    reservation_date == off_date
                    and period == off_period
                    and doctor == off_doctor
                ):
                    return True

        return False

    def _get_reservation_status(
        self, reservation_rows, off_day_rows, reservation_date, period, doctor
    ):
        status = ""

        if self._get_off_day_list(off_day_rows, reservation_date, period, doctor):
            return "暫停預約"

        reservation_count = 0
        for row in reservation_rows:
            year = row["ReserveDate"].year
            month = row["ReserveDate"].month
            day = row["ReserveDate"].day
            row_period = string_utils.xstr(row["Period"])
            row_doctor = string_utils.xstr(row["Doctor"])

            row_reservation_date = f"{year}-{month:0>2}-{day:0>2}"

            if (
                reservation_date == row_reservation_date
                and period == row_period
                and doctor == row_doctor
            ):
                reservation_count += 1

        if reservation_count > 0:
            if self.show_remain == "Y":
                remain = self._get_reservation_remain(reservation_date, period, doctor)
                status = f"{period[:1]}: {reservation_count} 餘{remain}"
            else:
                status = f"{period[:1]}: {reservation_count}人"

        return status

    def _get_reservation_remain(self, reservation_date, period, doctor):
        # 1. 取得星期
        date_obj = datetime.datetime.strptime(reservation_date, "%Y-%m-%d")
        weekday_name = date_utils.get_weekday_name(date_obj.weekday())

        # 2. 用一條 SQL 搞定：計算「時段表中有」但「預約表中沒有」的數量
        # 我們利用 LEFT JOIN 結合 IS NULL 來過濾
        sql = f'''
            SELECT COUNT(T.Time) as remain_count
            FROM (
                -- 這是你的時段樣板子查詢
                SELECT Time FROM reservation_table
                WHERE Doctor = "{doctor}" 
                AND Period = "{period}"
                AND (Weekday = "{weekday_name}" OR (Weekday IS NULL AND ReserveNo IS NOT NULL))
            ) AS T
            LEFT JOIN reserve AS R ON 
                R.ReserveDate = CONCAT("{reservation_date} ", T.Time, ":00") AND
                R.Period = "{period}" AND
                R.Doctor = "{doctor}"
            WHERE R.ReserveKey IS NULL
        '''

        result = self.database.select_record(sql)

        if result and len(result) > 0:
            return result[0]["remain_count"]

        return 0

    def _calendar_changed(self):
        current_row = self.ui.tableWidget_calendar.currentRow()
        current_column = self.ui.tableWidget_calendar.currentColumn()
        item = self.ui.tableWidget_calendar.item(current_row, current_column)

        if item is None:
            return

        text = item.text()  # 🔥 在表格刷新前先備份文字
        lines = text.split("\n")

        lines = item.text().split("\n")
        row_height = self.ui.tableWidget_calendar.rowHeight(current_row)
        line_height = row_height / 4  # 固定為 4 行：日期、早班、午班、晚班

        pos = self.ui.tableWidget_calendar.viewport().mapFromGlobal(QtGui.QCursor.pos())
        cell_rect = self.ui.tableWidget_calendar.visualItemRect(item)
        y_offset = pos.y() - cell_rect.top()

        clicked_line = int(y_offset // line_height)

        try:
            content = lines[clicked_line]
        except Exception:
            content = ""

        if "早" in content:
            self.ui.radioButton_period1.setChecked(True)
        elif "午" in content:
            self.ui.radioButton_period2.setChecked(True)
        elif "晚" in content:
            self.ui.radioButton_period3.setChecked(True)

        self.read_reservation_by_period()

        year = int(self.ui.dateEdit_reservation_date.date().year())
        month = int(self.ui.dateEdit_reservation_date.date().month())
        day = int(lines[0])  # 🔥 使用之前備份的 lines
        self.ui.dateEdit_reservation_date.setDate(QtCore.QDate(year, month, day))

        self.set_combo_box_doctor()

    def _export_reservation_excel(self):
        if self.ui.tabWidget_reservation.currentIndex != 1:
            self.ui.tabWidget_reservation.setCurrentIndex(1)

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "QFileDialog.getSaveFileName()",
            "預約門診資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        export_utils.export_table_widget_to_excel(
            excel_file_name, self.ui.tableWidget_reservation_list, [0]
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>預約資料檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _export_web_reservation_excel(self):
        dialog = dialog_utils.get_dialog_date_duration(
            self, self.database, self.system_settings
        )
        dialog.set_title("請選擇匯出日期")
        if not dialog.exec_():
            dialog.deleteLater()
            return

        options = QFileDialog.Options()
        excel_file_name, _ = QFileDialog.getSaveFileName(
            self.parent,
            "匯出Excel資料",
            "網路初診預約門診資料.xlsx",
            "excel檔案 (*.xlsx);;Text Files (*.txt)",
            options=options,
        )
        if not excel_file_name:
            return

        start_date = dialog.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = dialog.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")
        dialog.deleteLater()

        sql = f'''
            SELECT
                reserve.ReserveDate, reserve.Period, reserve.ReserveNo,
                temp_patient.Name ,temp_patient.Gender, temp_patient.ID, temp_patient.Birthday,
                temp_patient.PhoneNo, temp_patient.Cellphone, temp_patient.Address,
                temp_patient.TreatType
            FROM reserve
                LEFT JOIN temp_patient ON temp_patient.TempPatientKey = reserve.PatientKey
            WHERE
                ReserveDate BETWEEN "{start_date}" AND "{end_date}" AND
                Source = "網路初診預約" AND
                Arrival = "False"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Information,
                "資料匯出完成",
                "<h3>這段期間內查無網路初診預約資料.</h3>",
                "Microsoft Excel 格式.",
            )
            return

        header_list = [
            "預約日期",
            "班別",
            "預約號",
            "姓名",
            "性別",
            "身份證號",
            "出生日期",
            "聯絡電話",
            "行動電話",
            "聯絡地址",
            "就診原因",
        ]
        patient_rows = []
        for row in rows:
            patient_rows.append(
                [
                    row["ReserveDate"],
                    row["Period"],
                    row["ReserveNo"],
                    row["Name"],
                    row["Gender"],
                    row["ID"],
                    row["Birthday"],
                    row["PhoneNo"],
                    row["Cellphone"],
                    row["Address"],
                    row["TreatType"],
                ]
            )

        export_utils.export_list_to_excel(
            excel_file_name,
            header_list,
            patient_rows,
            None,
            "網路初診預約資料",
        )

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料匯出完成",
            f"<h3>預約資料檔{excel_file_name}匯出完成.</h3>",
            "Microsoft Excel 格式.",
        )

    def _print_reservation(self):
        if self.tab_name == "預約一覽表":
            current_row = self.ui.tableWidget_reservation.currentRow()
            current_column = self.ui.tableWidget_reservation.currentColumn()
            reservation_key = self._get_reserve_key_by_table(
                current_row, current_column, True
            )
        else:
            reservation_key = self.table_widget_reservation_list.field_value(0)

        if reservation_key is None:
            return

        self.print_reservation_form("系統設定", reservation_key)

    # 列印收據
    def print_reservation_form(self, printable, reservation_key=False):
        if not reservation_key:
            reservation_key = self.table_widget_wait.field_value(1)

        printer_utils.print_reservation(
            self, self.database, self.system_settings, reservation_key, printable
        )

    def _print_reservation_list(self, print_less=False):
        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()

        printer_utils.print_reservation_list(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            doctor,
            self.ui.tableWidget_reservation_list,
            print_less=print_less,
        )

    def _print_correction_area_reservation_list(self):
        start_date = self.ui.dateEdit_start_date.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.ui.dateEdit_end_date.date().toString("yyyy-MM-dd 23:59:59")
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()

        printer_utils.print_correction_area_reservation_list(
            self,
            self.database,
            self.system_settings,
            start_date,
            end_date,
            period,
            doctor,
            self.ui.tableWidget_reservation_list,
        )

    # 由醫師預約
    def _set_reservation_by_doctor(self):
        self.ui.action_reservation_arrival.setEnabled(False)
        self.ui.comboBox_doctor.setEnabled(False)

        if self.doctor is not None:
            self.ui.comboBox_doctor.setCurrentText(self.doctor)

    def _off_day_setting(self):
        dialog = dialog_utils.get_dialog_off_day_setting(
            self, self.database, self.system_settings, "off_day_list"
        )

        dialog.exec_()
        dialog.deleteLater()
        self.read_reservation()

    # 預約權限設定
    def _permission_list_setting(self):
        dialog = dialog_utils.get_dialog_permission_list_setting(
            self, self.database, self.system_settings
        )

        dialog.exec_()
        dialog.deleteLater()

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

    def _auto_reservation_table(self):
        period = self._get_period()
        dialog = dialog_utils.get_dialog_auto_reservation_table(
            self, self.database, self.system_settings, period
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        start_time = dialog.ui.timeEdit_start_time.time()
        end_time = dialog.ui.timeEdit_end_time.time()
        interval_time = dialog.ui.spinBox_interval_time.value()
        start_no = dialog.ui.spinBox_start_no.value()
        interval_no = dialog.ui.spinBox_interval_no.value()
        self._set_auto_reservation_table(
            start_time, end_time, interval_time, start_no, interval_no
        )

        dialog.deleteLater()

    def _set_auto_reservation_table(
        self, start_time, end_time, interval_time, start_no, interval_no
    ):
        self._clear_reservation_table()

        start_hour = start_time.hour()
        start_minute = start_time.minute()
        end_time_str = end_time.toString("hh:mm")

        hour = start_hour
        minute = start_minute
        col_no = 0
        row_no = 0
        reservation_no = start_no

        while True:
            current_time = f"{hour:0>2}:{minute:0>2}"
            if current_time >= end_time_str:
                break

            self.ui.tableWidget_reservation.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(current_time)
            )
            self.ui.tableWidget_reservation.setItem(
                row_no,
                col_no + 1,
                QtWidgets.QTableWidgetItem(string_utils.xstr(reservation_no)),
            )
            minute += interval_time
            row_no += 1
            reservation_no += interval_no

            if minute >= 60:
                minute = 0
                hour += 1
                row_no = 0
                col_no += 4

    def _display_first_visit_info(self):
        if self.tab_name == "預約一覽表":
            current_column = self.ui.tableWidget_reservation.currentColumn()
            current_row = self.ui.tableWidget_reservation.currentRow()
            reserve_key = self._get_reserve_key_by_table(current_row, current_column)
        else:
            current_row = self.ui.tableWidget_reservation_list.currentRow()
            reserve_key_item = self.ui.tableWidget_reservation_list.item(current_row, 0)
            if reserve_key_item is None:
                return

            reserve_key = reserve_key_item.text()

        if not self._check_reservation_first_visit(reserve_key):
            return

        temp_patient_key = self._get_patient_key(reserve_key)
        sql = f"""
            SELECT * FROM temp_patient
            WHERE
                TempPatientKey = {temp_patient_key}
        """
        temp_patient_rows = self.database.select_record(sql)
        if len(temp_patient_rows) <= 0:  # 可能已經報到且有病患基本資料
            return

        temp_patient_row = temp_patient_rows[0]

        name = string_utils.xstr(temp_patient_row["Name"])
        patient_id = string_utils.xstr(temp_patient_row["ID"])
        birthday = string_utils.xstr(temp_patient_row["Birthday"])
        phone_no = string_utils.xstr(temp_patient_row["PhoneNo"])
        cellphone = string_utils.xstr(temp_patient_row["Cellphone"])
        address = string_utils.xstr(temp_patient_row["Address"])
        try:
            remark = string_utils.get_str(temp_patient_row["Remark"], "utf8")
        except Exception:
            remark = ""

        remark = remark.replace("\n", "<br>")
        if remark != "":
            html = remark
        else:
            html = f"""
                <font size="5" color="blue">
                    <b>{name}初診預約資料</b>
                </font><br>
                以下是初診預約的詳細資料:<br><br>
                病患姓名: {name}<br>
                身分證號: {patient_id}<br>
                出生日期: {birthday}<br>
                聯絡電話: {phone_no}<br>
                行動電話: {cellphone}<br>
                居住地址: {address}<br>
            """

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("網路初診預約掛號報到")
        msg_box.setText(html)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()

    def _doctor_month_schedule(self):
        doctor = self.ui.comboBox_doctor.currentText()
        year = self.ui.dateEdit_reservation_date.date().year()
        month = self.ui.dateEdit_reservation_date.date().month()

        dialog = dialog_utils.get_dialog_doctor_month_schedule(
            self, self.database, self.system_settings, doctor, year, month
        )

        dialog.exec_()

    def _hide_on_web(self):
        current_column = self.ui.tableWidget_reservation.currentColumn()
        current_row = self.ui.tableWidget_reservation.currentRow()

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)

        if header is not None and header.text() in ["時間", "診號", "姓名"]:
            if header.text() == "時間":
                col_no = current_column + 1
            elif header.text() == "診號":
                col_no = current_column
            elif header.text() == "姓名":
                col_no = current_column - 1
        else:
            return

        reserve_no_item = self.ui.tableWidget_reservation.item(current_row, col_no)
        if reserve_no_item is None:
            return

        weekday = self._get_week_day_name()
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()
        reserve_no = reserve_no_item.text()

        if self.ui.action_hide_on_web.text() == "網頁顯示":
            self.database.exec_sql(f'''
                DELETE FROM reservation_table_hide
                WHERE
                    Weekday = "{weekday}" AND
                    Period = "{period}" AND
                    Doctor = "{doctor}" AND
                    ReserveNo = "{reserve_no}"
            ''')
            self.read_reservation()
            self._reservation_table_item_changed()
            self.ui.tableWidget_reservation.setFocus()
            self.ui.tableWidget_reservation.setCurrentCell(current_row, current_column)
            return

        fields = ["Weekday", "Period", "Doctor", "ReserveNo"]
        data = [weekday, period, doctor, reserve_no]
        self.database.insert_record("reservation_table_hide", fields, data)
        self.read_reservation()

        self.ui.tableWidget_reservation.setFocus()
        self.ui.tableWidget_reservation.setCurrentCell(current_row, current_column)

    def _auto_reservation(self):
        doctor = self.ui.comboBox_doctor.currentText()
        period = self._get_period()
        date = self.ui.dateEdit_reservation_date.date().toString("yyyy-MM-dd")

        reservation_date = f"{date}"
        dialog = dialog_utils.get_dialog_reservation_booking(
            self,
            self.database,
            self.system_settings,
            reservation_date,
            period,
            doctor,
            None,
            self.patient_key,
        )

        dialog.exec_()
        self.read_reservation()

        dialog.deleteLater()

    def _set_reservation_type(self):
        col_no = None

        current_column = self.ui.tableWidget_reservation.currentColumn()
        current_row = self.ui.tableWidget_reservation.currentRow()

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is not None and header.text() in ["時間", "診號", "姓名"]:
            if header.text() == "時間":
                col_no = current_column + 1
            elif header.text() == "診號":
                col_no = current_column
            elif header.text() == "姓名":
                col_no = current_column - 1

        if col_no is None:
            return

        reserve_no_item = self.ui.tableWidget_reservation.item(current_row, col_no)
        if reserve_no_item is None:
            return

        if self.sender().objectName() == "toolButton_visit1":
            reserve_type = '"初診"'
        elif self.sender().objectName() == "toolButton_visit2":
            reserve_type = '"複診"'
        elif self.sender().objectName() == "toolButton_clear_visit":
            reserve_type = "NULL"
        else:
            return

        weekday = self._get_week_day_name()
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()
        reserve_no = reserve_no_item.text()

        self.database.exec_sql(f'''
            UPDATE reservation_table
                SET ReserveType = {reserve_type}
            WHERE
                (Weekday = "{weekday}" OR Weekday IS NULL) AND
                Period = "{period}" AND
                Doctor = "{doctor}" AND
                ReserveNo = "{reserve_no}"
        ''')
        self.read_reservation()
        self._reservation_table_item_changed()

    def _set_reservation_allow(self):
        col_no = None

        current_column = self.ui.tableWidget_reservation.currentColumn()
        current_row = self.ui.tableWidget_reservation.currentRow()

        header = self.ui.tableWidget_reservation.horizontalHeaderItem(current_column)
        if header is not None and header.text() in ["時間", "診號", "姓名"]:
            if header.text() == "時間":
                col_no = current_column + 1
            elif header.text() == "診號":
                col_no = current_column
            elif header.text() == "姓名":
                col_no = current_column - 1

        if col_no is None:
            return

        reserve_no_item = self.ui.tableWidget_reservation.item(current_row, col_no)
        if reserve_no_item is None:
            return

        reservation_date = self.ui.dateEdit_reservation_date.date().toString(
            "yyyy-MM-dd"
        )
        period = self.ui.comboBox_period.currentText()
        doctor = self.ui.comboBox_list_doctor.currentText()
        reserve_no = reserve_no_item.text()

        sql = f'''
            SELECT * FROM reservation_allow_table
            WHERE
                ReserveDate = "{reservation_date}" AND
                Period = "{period}" AND
                Doctor = "{doctor}" AND
                ReserveNo = "{reserve_no}"
        '''
        rows = self.database.select_record(sql)

        if len(rows) > 0:
            sql = f'''
                DELETE  FROM reservation_allow_table
                WHERE
                    ReserveDate = "{reservation_date}" AND
                    Period = "{period}" AND
                    Doctor = "{doctor}" AND
                    ReserveNo = "{reserve_no}"
            '''
            self.database.exec_sql(sql)
        else:
            fields = ["ReserveDate", "Period", "Doctor", "ReserveNo"]
            data = [reservation_date, period, doctor, reserve_no]
            self.database.insert_record("reservation_allow_table", fields, data)

        self.read_reservation()
        self._reservation_table_item_changed()

    def _set_not_arrival(self):
        if self.tab_name == "預約一覽表":
            current_row = self.ui.tableWidget_reservation.currentRow()
            current_column = self.ui.tableWidget_reservation.currentColumn()
            reserve_key = self._get_reserve_key_by_table(
                current_row, current_column, warning=True, allow_arrival=True
            )
        else:
            reserve_key = self.table_widget_reservation_list.field_value(0)

        if reserve_key is None:
            return

        sql = f"""
            UPDATE reserve
            SET
                Arrival = "False"
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

        system_utils.show_message_box(
            QMessageBox.Information,
            "還原完成",
            """
                <font color="blue">
                    <h3>已經還原成未預約狀態.</h3>
                </font>
            """,
            "還原成功.",
        )
        self.read_reservation()

    def _set_absent_list(self, reservation_date):
        self.ui.dateEdit_absent_start_date.setDate(reservation_date)
        self.ui.dateEdit_absent_end_date.setDate(reservation_date)
        ui_utils.set_combo_box(self.ui.comboBox_absent_period, nhi_utils.PERIOD, "全部")

        doctor_list = personnel_utils.get_person(self.database, "無逗點醫師")
        ui_utils.set_combo_box(self.ui.comboBox_absent_doctor, doctor_list, "全部")

    def _set_cancel_list(self):
        self.ui.dateEdit_cancel_start_date.blockSignals(True)
        self.ui.dateEdit_cancel_end_date.blockSignals(True)

        current_date = QtCore.QDate.currentDate()
        start_of_this_year = QtCore.QDate(current_date.year(), 1, 1)

        self.ui.dateEdit_cancel_start_date.setMaximumDate(current_date)
        self.ui.dateEdit_cancel_end_date.setMaximumDate(current_date)

        self.ui.dateEdit_cancel_start_date.setDate(start_of_this_year)
        self.ui.dateEdit_cancel_end_date.setDate(current_date)

        self.ui.dateEdit_cancel_start_date.blockSignals(False)
        self.ui.dateEdit_cancel_end_date.blockSignals(False)

        self._read_cancel_list()

    def _read_cancel_list(self):
        start_date = self.ui.dateEdit_cancel_start_date.date().toString(
            "yyyy-MM-dd 00:00:00"
        )
        end_date = self.ui.dateEdit_cancel_end_date.date().toString(
            "yyyy-MM-dd 23:59:59"
        )
        patient_key = self.ui.lineEdit_cancel_patient_key.text()
        if len(patient_key) > 0 and not patient_key.isdigit():
            patient_key = ""
            self.ui.lineEdit_cancel_patient_key.setText("")
            return

        if len(patient_key) > 0:
            patient_key_condition = f" AND PatientKey = {patient_key}"
        else:
            patient_key_condition = ""

        sql = f'''
            SELECT * FROM reserve_cancel
            WHERE
                CancelDate BETWEEN "{start_date}" AND "{end_date}"
                {patient_key_condition}
            ORDER BY DATE(CancelDate)
        '''

        self.table_widget_cancel_list.set_db_data(sql, self._set_cancel_data)

        if len(patient_key) > 0:
            self.ui.lineEdit_cancel_patient_key.setFocus()

    def _set_cancel_data(self, row_no, row):
        reserve_backup = string_utils.get_str(row["ReserveBackup"], "utf-8")
        try:
            backup_row = json.loads(reserve_backup)
        except Exception:
            backup_row = None

        patient_key = string_utils.xstr(row["PatientKey"])
        if backup_row is not None:
            row["ReserveDate"] = backup_row["ReserveDate"]
            row["CreateTime"] = backup_row["CreateTime"]
            row["Period"] = backup_row["Period"]
            row["ReserveNo"] = backup_row["ReserveNo"]
            row["Doctor"] = backup_row["Doctor"]
            row["Registrar"] = backup_row["Registrar"]
        else:
            row["ReserveDate"] = None
            row["CreateTime"] = None
            row["Period"] = None
            row["ReserveNo"] = None
            row["Doctor"] = None
            row["Registrar"] = None

        name = string_utils.xstr(row["Name"])

        if string_utils.xstr(row["Source"]) in [
            "網路初診",
            "網路初診預約",
            "初診預約",
            "視訊初診",
            "視訊初診預約",
        ]:
            patient_key = string_utils.xstr(row["Source"])[:4]

        cancel_list_data = [
            string_utils.xstr(row["ReserveKey"]),
            string_utils.xstr(row["ReserveDate"]),
            string_utils.xstr(row["Period"]),
            patient_key,
            name,
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(row["ReserveNo"]),
            string_utils.xstr(row["Source"]),
            string_utils.xstr(row["Registrar"]),
            string_utils.xstr(row["CreateTime"]),
            string_utils.xstr(row["CancelDate"]),
            string_utils.xstr(row["Remark"]),
        ]

        if self.show_last_case_remark == "Y":
            try:
                last_case_remark = self._get_last_case_remark(patient_key)
            except Exception:
                last_case_remark = None

            cancel_list_data.append(last_case_remark)

        for col_no in range(len(cancel_list_data)):
            self.ui.tableWidget_cancel_list.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(cancel_list_data[col_no])
            )
            if col_no in [3, 6]:
                self.ui.tableWidget_cancel_list.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [2]:
                self.ui.tableWidget_cancel_list.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        if string_utils.xstr(row["Source"]) == "網路預約":
            color = "blue"
        elif string_utils.xstr(row["Source"]) in ["視訊預約", "視訊初診預約"]:
            color = "fuchsia"
        elif string_utils.xstr(row["Source"]) in ["初診預約", "網路初診預約"]:
            color = "green"
        elif name == "保留預約":
            color = "red"
        else:
            color = "black"

        for col_no in range(self.ui.tableWidget_cancel_list.columnCount()):
            item = self.ui.tableWidget_cancel_list.item(row_no, col_no)
            if item is not None:
                item.setForeground(QtGui.QColor(color))

    def _set_reserve_type(self, reserve_type):
        current_doctor = self.ui.comboBox_doctor.currentText()

        if reserve_type in ["初診", "複診"]:
            sql = f'''
                UPDATE reservation_table
                SET
                    ReserveType = "{reserve_type}"
                WHERE
                    Doctor = "{current_doctor}"
            '''
        else:
            sql = f'''
                UPDATE reservation_table
                SET
                    ReserveType = NULL
                WHERE
                    Doctor = "{current_doctor}"
            '''
        self.database.exec_sql(sql)
        self.read_reservation()

    def set_doctor_and_patient(self, doctor, patient_key, vhc_ic_card=None):
        self.doctor = doctor
        self.patient_key = patient_key
        self.vhc_ic_card = vhc_ic_card

    def _lock_reserve_record(self, reserve_key, name):
        patient_key = self._get_patient_key(reserve_key)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("鎖定網路預約掛號")
        msg_box.setText(f"""
            <font size='4' color='red'>
                <b>確定鎖定或解除病歷號{patient_key}{name}的網路預約掛號?</b>
            </font>
        """)
        msg_box.setInformativeText("注意！預約掛號鎖定後, 將無法透過網路取消預約!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        lock_reservation = msg_box.exec_()
        if not lock_reservation:
            return False

        sql = f"""
            SELECT Frozen From reserve
            WHERE
                ReserveKey = {reserve_key}
        """
        rows = self.database.select_record(sql)
        if not rows:
            return False

        frozen = rows[0]["Frozen"]

        sql = f"""
            UPDATE reserve
            SET
                Frozen = {not frozen}
            WHERE
                ReserveKey = {reserve_key}
        """
        self.database.exec_sql(sql)

        return True

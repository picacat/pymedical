# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from libs import class_utils, dialog_utils, nhi_utils, string_utils, ui_utils


class MultiChoiceDialog(QDialog):
    def __init__(self, title, label, items, checked_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        for item in items:
            list_item = QListWidgetItem(item)
            # 讓項目變成可以打勾
            list_item.setFlags(list_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            # 如果原本就已經有這位醫師，預設打勾
            if item in checked_items:
                list_item.setCheckState(QtCore.Qt.Checked)
            else:
                list_item.setCheckState(QtCore.Qt.Unchecked)
            self.list_widget.addItem(list_item)

        layout.addWidget(self.list_widget)

        # 加上確定/取消按鈕
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_items(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                selected.append(item.text())
        return selected


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
        self.week_list = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

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

        self.ui.action_add_temporary_schedule.triggered.connect(
            self._add_temporary_schedule
        )
        self.ui.action_edit_temporary_schedule.triggered.connect(
            self._edit_temporary_schedule
        )
        self.ui.action_remove_temporary_schedule.triggered.connect(
            self._remove_temporary_schedule
        )
        self.ui.action_close.triggered.connect(self._close_doctor_schedule)
        self.ui.tableWidget_doctor_schedule.doubleClicked.connect(self._edit_schedule)
        self.ui.tableWidget_doctor_schedule_period.doubleClicked.connect(
            self._edit_schedule
        )
        self.ui.tableWidget_special_schedule.doubleClicked.connect(
            self._edit_special_schedule
        )
        self.ui.tabWidget_schedule.currentChanged.connect(
            self._schedule_tab_changed
        )  # 切換分頁
        self.ui.tableWidget_temporary_schedule.doubleClicked.connect(
            self._edit_temporary_schedule
        )

    def _read_doctor_schedule_by_room(self):
        period_list = str(nhi_utils.PERIOD)[1:-1]
        sql = f"""
            SELECT * FROM doctor_schedule
            ORDER BY Room, FIELD(Period, {period_list})
        """
        self.table_widget_doctor_schedule.set_db_data(
            sql, self._set_doctor_schedule_room_data
        )

    def _read_temporary_schedule(self):
        sql = """
            SELECT * FROM temporary_schedule
            WHERE
                Position = "醫師"
            ORDER BY CaseDate DESC
        """
        self.table_widget_temporary_schedule.set_db_data(
            sql, self._set_temporary_schedule_data
        )

    def _set_doctor_schedule_room_data(self, row_no, row):
        doctor_schedule_row = [
            string_utils.xstr(row["DoctorScheduleKey"]),
            string_utils.xstr(row["Room"]),
            string_utils.xstr(row["Period"]),
            string_utils.xstr(row["Monday"]),
            string_utils.xstr(row["Tuesday"]),
            string_utils.xstr(row["Wednesday"]),
            string_utils.xstr(row["Thursday"]),
            string_utils.xstr(row["Friday"]),
            string_utils.xstr(row["Saturday"]),
            string_utils.xstr(row["Sunday"]),
        ]

        for column in range(len(doctor_schedule_row)):
            self.ui.tableWidget_doctor_schedule.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(doctor_schedule_row[column])
            )

            align = QtCore.Qt.AlignLeft
            if column in [1, 2]:
                align = QtCore.Qt.AlignCenter

            self.ui.tableWidget_doctor_schedule.item(row_no, column).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )

    def _set_temporary_schedule_data(self, row_no, row):
        temporary_schedule_row = [
            string_utils.xstr(row["TemporaryScheduleKey"]),
            string_utils.xstr(row["CaseDate"]),
            string_utils.xstr(row["ScheduleType"]),
            string_utils.xstr(row["Room"]),
            string_utils.xstr(row["Period"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Agent"]),
            string_utils.xstr(row["Remark"]),
        ]

        for column in range(len(temporary_schedule_row)):
            self.ui.tableWidget_temporary_schedule.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(temporary_schedule_row[column]),
            )

            align = QtCore.Qt.AlignLeft
            if column in [2, 3, 4]:
                align = QtCore.Qt.AlignCenter

            self.ui.tableWidget_temporary_schedule.item(
                row_no, column
            ).setTextAlignment(align | QtCore.Qt.AlignVCenter)

    def _add_schedule(self):
        if self.tab_name == "診別顯示":
            self._edit_schedule_room(None)
        else:
            self._edit_schedule_period()

    def _edit_schedule(self):
        if self.tab_name == "診別顯示":
            self._edit_schedule_room(self.table_widget_doctor_schedule.field_value(0))
        else:
            self._edit_schedule_period()

    def _edit_special_schedule(self):
        col_no = self.ui.tableWidget_special_schedule.currentColumn()
        row_no = self.ui.tableWidget_special_schedule.currentRow()
        if col_no < 0 or row_no < 0:
            return

        # 先取得目前格位上已經有哪些醫師 (用 \n 拆開)
        current_item = self.ui.tableWidget_special_schedule.item(row_no, col_no)
        current_doctors = []
        if current_item and current_item.text():
            current_doctors = [
                d.strip() for d in current_item.text().split("\n") if d.strip()
            ]

        # 撈出所有醫師名單
        sql = """
            SELECT * FROM person
            WHERE
                Position IN ("醫師", "支援醫師") AND
                ID IS NOT NULL AND LENGTH(ID) > 0 AND
                Password IS NOT NULL AND LENGTH(Password) > 0
            ORDER BY PersonKey
        """
        rows = self.database.select_record(sql)

        # 準備選單項目 (不包含 None 和 特約門診，這些可以另外處理，這裡純粹放醫師)
        items = []
        for row in rows:
            items.append(string_utils.xstr(row["Name"]))

        # 彈出複選視窗
        dialog = MultiChoiceDialog(
            "選擇醫師", "請勾選此時段的醫師 (可多選):", items, current_doctors, self
        )
        if dialog.exec_() == QDialog.Accepted:
            selected_doctors = dialog.get_selected_items()
            # 呼叫更新邏輯，把整組選好的醫師丟進去
            self._update_special_schedule(row_no, col_no, selected_doctors)

    def _update_special_schedule(self, row_no, col_no, selected_doctors):
        doctor_schedule_col = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        field = doctor_schedule_col[col_no]

        if row_no == 0:
            period = "早班"
        elif row_no == 1:
            period = "午班"
        else:
            period = "晚班"

        # 1. 為了保持資料整潔，最安全的做法是「先刪除該班別舊的所有紀錄」，再依據新的醫師數量重新寫入
        # 這樣就不會發生 UPDATE 把多筆資料搞混的問題
        delete_sql = f'DELETE FROM special_schedule WHERE Period = "{period}"'
        self.database.exec_sql(delete_sql)

        # 2. 如果使用者把醫生都勾掉了 (清空)
        if not selected_doctors:
            self.ui.tableWidget_special_schedule.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem("")
            )
            # 雖然刪除了，但資料庫最好留一筆空白的 Period 紀錄，確保讀取時不會完全沒資料
            insert_empty_sql = (
                f'INSERT INTO special_schedule (Period) VALUES ("{period}")'
            )
            self.database.exec_sql(insert_empty_sql)

            self.ui.tableWidget_special_schedule.resizeRowToContents(row_no)
            return

        # 3. 畫面更新：將勾選的醫師用 \n 串接顯示
        combined_text = "\n".join(selected_doctors)
        item = QtWidgets.QTableWidgetItem(combined_text)
        item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.ui.tableWidget_special_schedule.setItem(row_no, col_no, item)

        # 4. 資料庫寫入：有幾位醫師，我們就寫入幾筆紀錄
        # 這樣上一話寫的 `_set_special_schedule` 用 `for row in rows:` 讀取時，就能完美對接！
        for doctor in selected_doctors:
            insert_sql = f'''
                INSERT INTO special_schedule (Period, {field}) 
                VALUES ("{period}", "{doctor}")
            '''
            self.database.exec_sql(insert_sql)

        # 自動調整列高
        self.ui.tableWidget_special_schedule.resizeRowToContents(row_no)

    def _edit_schedule_room(self, schedule_key):
        dialog = dialog_utils.get_dialog_doctor_schedule(
            self,
            self.database,
            self.system_settings,
            schedule_key,
        )
        if dialog.exec_():
            self._read_doctor_schedule_by_room()

        dialog.deleteLater()

    def _edit_schedule_period(self):
        weekday = self._get_weekday()
        period = self._get_period()

        dialog = dialog_utils.get_dialog_doctor_schedule_period(
            self,
            self.database,
            self.system_settings,
            weekday,
            period,
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
        msg_box.setWindowTitle("刪除班表資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆班表資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        if self.tab_name == "診別顯示":
            self._remove_schedule_room()

    def _remove_schedule_room(self):
        self.database.delete_record(
            "doctor_schedule",
            "DoctorScheduleKey",
            self.table_widget_doctor_schedule.field_value(0),
        )

        self._read_doctor_schedule_by_room()

    def _add_temporary_schedule(self):
        dialog = dialog_utils.get_dialog_temporary_schedule(
            self, self.database, self.system_settings
        )
        if dialog.exec_():
            self._read_temporary_schedule()

        dialog.deleteLater()

    def _edit_temporary_schedule(self):
        temporary_schedule_key = self.table_widget_temporary_schedule.field_value(0)
        dialog = dialog_utils.get_dialog_temporary_schedule(
            self, self.database, self.system_settings, temporary_schedule_key
        )
        if dialog.exec_():
            self._read_temporary_schedule()

        dialog.deleteLater()

    def _remove_temporary_schedule(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除臨時班表資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆臨時班表資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        temporary_schedule_key = self.table_widget_temporary_schedule.field_value(0)
        self.database.delete_record(
            "temporary_schedule", "TemporaryScheduleKey", temporary_schedule_key
        )

        self._read_temporary_schedule()

    def _close_doctor_schedule(self):
        self.close_all()
        self.close_tab()

    def _read_doctor_schedule_by_period(self):
        for row_no in range(self.ui.tableWidget_doctor_schedule_period.rowCount()):
            for col_no in range(
                self.ui.tableWidget_doctor_schedule_period.columnCount()
            ):
                self.ui.tableWidget_doctor_schedule_period.setItem(row_no, col_no, None)

        self._set_schedule_period("早班", row_no=0)
        self._set_schedule_period("午班", row_no=1)
        self._set_schedule_period("晚班", row_no=2)

    def _set_schedule_period(self, period, row_no):
        room_list = [
            "⓪",
            "①",
            "②",
            "③",
            "④",
            "⑤",
            "⑥",
            "⑦",
            "⑧",
            "⑨",
            "⑩",
            "⑪",
            "⑫",
            "⑬",
            "⑭",
            "⑮",
            "⑯",
            "⑰",
            "⑱",
            "⑲",
            "⑳",
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
                doctor_label = "\n".join(doctor_list)
            elif len(doctor_list) == 1:
                doctor_label = doctor_list[0]
            else:
                doctor_label = ""

            self.ui.tableWidget_doctor_schedule_period.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(doctor_label)
            )
            self.ui.tableWidget_doctor_schedule_period.item(
                row_no, col_no
            ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_doctor_schedule_period.resizeRowsToContents()

    def _schedule_tab_changed(self, i):
        self.tab_name = self.ui.tabWidget_schedule.tabText(i)

        if self.tab_name == "診別顯示":
            self._read_doctor_schedule_by_room()
        else:
            self._read_doctor_schedule_by_period()

    def _read_special_schedule(self):
        sql = """
            SELECT * FROM special_schedule
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._create_special_schedule()

        self._set_special_schedule("早班")
        self._set_special_schedule("午班")
        self._set_special_schedule("晚班")

    def _create_special_schedule(self):
        self.database.exec_sql("""
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("早班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """)
        self.database.exec_sql("""
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("午班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """)
        self.database.exec_sql("""
            INSERT INTO special_schedule (Period, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
            VALUES ("晚班", NULL, NULL, NULL, NULL, NULL, NULL, NULL)
        """)

    def _set_special_schedule(self, period):
        # 1. 安全性建議：改用參數化查詢避免 SQL Injection (雖然此處 period 可能是內定字串，但養成習慣較好)
        sql = f"SELECT * FROM special_schedule WHERE Period = '{period}'"
        rows = self.database.select_record(sql)

        if not rows:
            return

        # 定義星期欄位對應
        doctor_schedule_col = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        # 對應班別的列號
        if period == "早班":
            row_no = 0
        elif period == "午班":
            row_no = 1
        else:
            row_no = 2

        # 2. 先初始化這一個班別（row_no）七天份的醫師列表
        # 格式會變成：[[], [], [], [], [], [], []] 分別代表週一到週日
        weekly_doctors = [[] for _ in range(len(doctor_schedule_col))]

        # 3. 走訪所有撈出來的紀錄 (處理多位醫師)
        for row in rows:
            for col_no, col_name in enumerate(doctor_schedule_col):
                doctor_name = row.get(col_name)
                # 確保有名字才加入
                if doctor_name not in ["", None]:
                    clean_name = string_utils.xstr(doctor_name).strip()
                    weekly_doctors[col_no].append(clean_name)

        # 4. 將收集好的醫師名單用 '\n' 串接，並填入 UI
        for col_no, doctor_list in enumerate(weekly_doctors):
            if doctor_list:
                # 組合後的字串：例如 "王醫師\n陳醫師"
                combined_text = "\n".join(doctor_list)

                item = QtWidgets.QTableWidgetItem(combined_text)
                item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

                self.ui.tableWidget_special_schedule.setItem(row_no, col_no, item)
            else:
                # 如果這天沒人值班，清空該單元格（避免殘留舊資料）
                self.ui.tableWidget_special_schedule.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem("")
                )

        # 5. 關鍵：自動調整列高，讓換行的文字能完整顯示
        self.ui.tableWidget_special_schedule.resizeRowToContents(row_no)

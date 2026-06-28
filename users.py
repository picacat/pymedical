# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    class_utils,
    dialog_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 使用者管理 2018.06.26
class Users(QtWidgets.QMainWindow):
    program_name = "使用者管理"

    # 初始化
    def __init__(self, parent=None, *args):
        super(Users, self).__init__(parent)
        self.parent = parent
        self.args = args
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self._read_users()

    def reload_permissions(self):
        self._set_permission()
        self._read_users()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_USERS, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_users = class_utils.get_table_widget(
            self.ui.tableWidget_users, self.database
        )
        self.table_widget_users.set_column_hidden([0])
        # self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_template)
        self.ui.tableWidget_users.doubleClicked.connect(self.open_user_dialog)
        self.ui.toolButton_add_user.clicked.connect(self.add_user)
        self.ui.toolButton_remove_user.clicked.connect(self.remove_user)
        self.ui.toolButton_edit_user.clicked.connect(self.open_user_dialog)
        self.ui.toolButton_show_all.clicked.connect(self._toggle_show_all)
        self.ui.toolButton_permission.clicked.connect(self._open_permission_dialog)
        self.ui.toolButton_permission_duplicate.clicked.connect(
            self._duplicate_permission
        )

    def _toggle_show_all(self):
        self._read_users(show_all=True)

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "新增使用者", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_add_user.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "刪除使用者", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_remove_user.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "編輯使用者", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_edit_user.setEnabled(False)
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "設定權限", self.user_name
            )
            != "Y"
        ):
            self.ui.toolButton_permission.setEnabled(False)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_template(self):
        self.close_all()
        self.close_tab()

    # 設定欄位寬度
    def _set_table_width(self):
        width = [
            100,
            80,
            100,
            130,
            50,
            130,
            150,
            100,
            50,
            60,
            200,
            180,
            120,
            150,
            150,
            400,
            250,
            100,
            120,
            120,
            120,
            300,
        ]
        self.table_widget_users.set_table_heading_width(width)

    def _read_users(self, show_all=False):
        if not show_all:
            condition = """
               WHERE (
                    Fulltime IS NULL OR LENGTH(Fulltime) = 0 OR
                    Fulltime NOT IN ("已離職")
               )
            """
        else:
            condition = ""

        sql = f"""
            SELECT * FROM person
                {condition}
            ORDER BY FIELD(
                Position, "醫師", "支援醫師", "藥師", "護士", "護理師", "助理", "職員", "理療師", "推拿師父", NULL),
                Code, PersonKey
        """
        self.table_widget_users.set_db_data(sql, self._set_user_data)

    def _set_user_data(self, row_no, row):
        password = "********"
        if (
            self.system_settings.field("使用者") == "超級使用者"
            or personnel_utils.get_permission(
                self.database, self.program_name, "查看使用者密碼", self.user_name
            )
            == "Y"
        ):
            password = string_utils.xstr(row["Password"])

        position = string_utils.xstr(row["Position"])
        id_no = string_utils.xstr(row["ID"])
        user_row = [
            string_utils.xstr(row["PersonKey"]),
            string_utils.xstr(row["Code"]),
            string_utils.xstr(row["Title"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Gender"]),
            string_utils.xstr(row["Birthday"]),
            id_no,
            position,
            string_utils.xstr(row["Room"]),
            string_utils.xstr(row["FullTime"]),
            string_utils.xstr(row["Certificate"]),
            string_utils.xstr(row["CertCardNo"]),
            password,
            string_utils.xstr(row["Telephone"]),
            string_utils.xstr(row["Cellphone"]),
            string_utils.xstr(row["Address"]),
            string_utils.xstr(row["Email"]),
            string_utils.xstr(row["Department"]),
            string_utils.xstr(row["InitDate"]),
            string_utils.xstr(row["QuitDate"]),
            string_utils.xstr(row["InputDate"]),
            string_utils.xstr(row["IME"]),
            string_utils.xstr(row["Remark"]),
        ]

        if position in ["醫師"] and id_no != "":
            color = QtGui.QBrush(QtCore.Qt.darkMagenta)
        elif position in ["支援醫師"] and id_no != "":
            color = QtGui.QBrush(QtCore.Qt.darkGreen)
        elif position in ["藥師"]:
            color = QtGui.QBrush(QtCore.Qt.darkCyan)
        elif position in ["護士"]:
            color = QtGui.QBrush(QtCore.Qt.blue)
        elif position in ["推拿師父"]:
            color = QtGui.QBrush(QtCore.Qt.darkRed)
        elif password == "":
            color = QtGui.QBrush(QtCore.Qt.darkGray)
        else:
            color = None

        for column in range(len(user_row)):
            self.ui.tableWidget_users.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(user_row[column])
            )

            if column in [4, 8]:
                self.ui.tableWidget_users.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if color is not None:
                self.ui.tableWidget_users.item(row_no, column).setForeground(color)

    def open_user_dialog(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "編輯使用者", self.user_name
            )
            != "Y"
        ):
            return

        person_key = self.table_widget_users.field_value(0)
        dialog = dialog_utils.get_dialog_input_user(
            self, self.database, self.system_settings, person_key
        )

        dialog.exec_()
        dialog.deleteLater()

        sql = f"""
            SELECT * FROM person
            WHERE
                PersonKey = {person_key}
        """
        row_data = self.database.select_record(sql)[0]
        self._set_user_data(self.ui.tableWidget_users.currentRow(), row_data)

    # 新增使用者資料
    def add_user(self):
        person_key = None
        dialog = dialog_utils.get_dialog_input_user(
            self, self.database, self.system_settings, person_key
        )
        result = dialog.exec_()

        if result != 0 and dialog.ui.lineEdit_name.text().strip() != "":
            sql = """
                SELECT * FROM person
                ORDER BY PersonKey DESC
                LIMIT 1
            """
            row_data = self.database.select_record(sql)[0]
            row_no = self.ui.tableWidget_users.rowCount()
            self.ui.tableWidget_users.insertRow(row_no)
            self._set_user_data(row_no, row_data)

        dialog.close_all()
        dialog.deleteLater()

    # 移除使用者資料
    def remove_user(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除使用者資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆使用者資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        key = self.table_widget_users.field_value(0)
        self.database.delete_record("person", "PersonKey", key)
        self.ui.tableWidget_users.removeRow(self.ui.tableWidget_users.currentRow())

    # 編輯使用者資料
    def edit_user(self):
        self.open_user_dialog()

    # 設定權限
    def _open_permission_dialog(self):
        person_key = self.table_widget_users.field_value(0)
        if person_key is None:
            return

        dialog = dialog_utils.get_dialog_permission(
            self, self.database, self.system_settings, person_key
        )
        dialog.exec_()
        dialog.deleteLater()

    def _duplicate_permission(self):
        input_dialog = QtWidgets.QInputDialog()
        input_dialog.setOkButtonText("確定")
        input_dialog.setCancelButtonText("取消")

        current_user_key = self.table_widget_users.field_value(0)
        if current_user_key is None:
            return

        current_user = self.table_widget_users.field_value(3)
        user_list = []
        for row_no in range(self.ui.tableWidget_users.rowCount()):
            user = self.ui.tableWidget_users.item(row_no, 3).text()
            if user != current_user:
                user_list.append(user)

        to_whom, ok = input_dialog.getItem(
            self, "複製權限", "要複製權限給誰?", user_list, 0, False
        )
        if not ok or not to_whom:
            return

        print(to_whom)

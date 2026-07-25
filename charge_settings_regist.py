# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    charge_utils,
    class_utils,
    dialog_utils,
    number_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 收費設定 2018.04.14
class ChargeSettingsRegist(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self._set_ui()
        self._set_signal()
        self._read_charge()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉帖

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHARGE_SETTINGS_REGIST, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_regist_fee = class_utils.get_table_widget(
            self.ui.tableWidget_regist_fee, self.database
        )
        self.table_widget_regist_fee.set_column_hidden([0, 1])
        self.table_widget_discount = class_utils.get_table_widget(
            self.ui.tableWidget_discount, self.database
        )
        self.table_widget_discount.set_column_hidden([0])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_regist_fee_add.clicked.connect(self._regist_fee_add)
        self.ui.toolButton_regist_fee_delete.clicked.connect(self._regist_fee_delete)
        self.ui.toolButton_regist_fee_edit.clicked.connect(self._regist_fee_edit)
        self.ui.tableWidget_regist_fee.doubleClicked.connect(self._regist_fee_edit)
        self.ui.toolButton_discount_add.clicked.connect(self._discount_add)
        self.ui.toolButton_discount_delete.clicked.connect(self._discount_delete)
        self.ui.toolButton_discount_edit.clicked.connect(self._discount_edit)
        self.ui.tableWidget_discount.doubleClicked.connect(self._discount_edit)

        self.ui.checkBox_old_man.clicked.connect(self._set_old_man_discount)
        self.ui.checkBox_child.clicked.connect(self._set_child_discount)
        self.ui.spinBox_old_man_age.valueChanged.connect(
            self._spin_box_old_man_value_changed
        )
        self.ui.spinBox_child_age.valueChanged.connect(
            self._spin_box_child_value_changed
        )

    # 設定欄位寬度
    def _set_table_width(self):
        regist_fee_width = [60, 60, 300, 100, 100, 100, 100, 100, 310]
        self.table_widget_regist_fee.set_table_heading_width(regist_fee_width)
        discount_width = [60, 150, 180, 100]
        self.table_widget_discount.set_table_heading_width(discount_width)

    # 關閉
    def close_all(self):
        pass

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

    def _read_charge(self):
        self._read_regist_fee()
        self._read_discount()

    # 掛號費 ************************************************************************************************************
    def _regist_fee_add(self):
        dialog = dialog_utils.get_dialog_input_regist(
            self, self.database, self.system_settings, None
        )
        result = dialog.exec_()
        if result != 0:
            current_row = self.ui.tableWidget_regist_fee.rowCount()
            self.ui.tableWidget_regist_fee.insertRow(current_row)
            fields = [
                "ChargeType",
                "ItemName",
                "InsType",
                "ShareType",
                "TreatType",
                "Course",
                "Amount",
                "Remark",
            ]
            data = [
                "掛號費",
                dialog.ui.lineEdit_item_name.text(),
                dialog.ui.comboBox_ins_type.currentText(),
                dialog.ui.comboBox_share_type.currentText(),
                dialog.ui.comboBox_treat_type.currentText(),
                dialog.ui.comboBox_course.currentText(),
                dialog.ui.spinBox_amount.value(),
                dialog.ui.lineEdit_remark.text(),
            ]
            self.database.insert_record("charge_settings", fields, data)
            sql = 'SELECT * FROM charge_settings WHERE ChargeType = "掛號費" ORDER BY ChargeSettingsKey desc limit 1'
            row_data = self.database.select_record(sql)[0]
            self._set_regist_fee_data(current_row, row_data)
            self.ui.tableWidget_regist_fee.setCurrentCell(current_row, 3)

        dialog.close_all()
        dialog.deleteLater()

    def _regist_fee_edit(self):
        charge_settings_key = self.table_widget_regist_fee.field_value(0)
        dialog = dialog_utils.get_dialog_input_regist(
            self, self.database, self.system_settings, charge_settings_key
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {charge_settings_key}
        """
        row_data = self.database.select_record(sql)[0]
        self._set_regist_fee_data(self.ui.tableWidget_regist_fee.currentRow(), row_data)

    def _regist_fee_delete(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除掛號費資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆掛號收費資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        key = self.table_widget_regist_fee.field_value(0)
        self.database.delete_record("charge_settings", "ChargeSettingsKey", key)
        self.ui.tableWidget_regist_fee.removeRow(
            self.ui.tableWidget_regist_fee.currentRow()
        )

    def _read_regist_fee(self):
        sql = 'SELECT * FROM charge_settings WHERE ChargeType = "掛號費" ORDER BY ChargeSettingsKey'
        self.table_widget_regist_fee.set_db_data(sql, self._set_regist_fee_data)
        row_count = self.table_widget_regist_fee.row_count()
        if row_count <= 0:
            charge_utils.set_regist_fee_basic_data(self.database)
            self._read_regist_fee()

        self._set_old_man_regist_fee()
        self._set_child_regist_fee()

    def _set_old_man_regist_fee(self):
        if self.system_settings.field("老人優待") == "Y":
            enabled = True
        else:
            enabled = False

        self.ui.checkBox_old_man.setChecked(enabled)

        old_man_age = self.system_settings.field("老人優待年齡")
        if old_man_age is None:
            old_man_age = 65

        self.ui.spinBox_old_man_age.setValue(number_utils.get_integer(old_man_age))

    def _set_child_regist_fee(self):
        if self.system_settings.field("兒童優待") == "Y":
            enabled = True
        else:
            enabled = False

        self.ui.checkBox_child.setChecked(enabled)

        child_age = self.system_settings.field("兒童優待年齡")
        if child_age is None:
            child_age = 6

        self.ui.spinBox_child_age.setValue(number_utils.get_integer(child_age))

    def _set_regist_fee_data(self, rec_no, rec):
        regist_fee_rec = [
            str(rec["ChargeSettingsKey"]),
            string_utils.xstr(rec["ChargeType"]),
            string_utils.xstr(rec["ItemName"]),
            string_utils.xstr(rec["InsType"]),
            string_utils.xstr(rec["ShareType"]),
            string_utils.xstr(rec["TreatType"]),
            string_utils.xstr(rec["Course"]),
            string_utils.xstr(rec["Amount"]),
            string_utils.xstr(rec["Remark"]),
        ]

        for column in range(len(regist_fee_rec)):
            self.ui.tableWidget_regist_fee.setItem(
                rec_no, column, QtWidgets.QTableWidgetItem(regist_fee_rec[column])
            )
            if column in [7]:
                self.ui.tableWidget_regist_fee.item(rec_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    # 掛號費優待 *********************************************************************************************************
    def _read_discount(self):
        charge_type = tuple(charge_utils.DISCOUNT_TYPE)
        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeType IN {charge_type}
            ORDER BY ChargeType, ChargeSettingsKey
        """
        self.table_widget_discount.set_db_data(sql, self._set_discount_data)
        row_count = self.table_widget_discount.row_count()
        if row_count <= 0:
            charge_utils.set_discount_basic_data(self.database)
            self._read_discount()

    def _set_discount_data(self, rec_no, rec):
        discount_rec = [
            string_utils.xstr(rec["ChargeSettingsKey"]),
            string_utils.xstr(rec["ChargeType"]),
            string_utils.xstr(rec["ItemName"]),
            string_utils.xstr(rec["Amount"]),
        ]

        for column in range(len(discount_rec)):
            self.ui.tableWidget_discount.setItem(
                rec_no, column, QtWidgets.QTableWidgetItem(discount_rec[column])
            )
            if column in [3]:
                self.ui.tableWidget_discount.item(rec_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _discount_add(self):
        dialog = dialog_utils.get_dialog_input_discount(
            self, self.database, self.system_settings, None
        )
        result = dialog.exec_()
        if result != 0:
            current_row = self.ui.tableWidget_discount.rowCount()
            self.ui.tableWidget_discount.insertRow(current_row)
            fields = ["ChargeType", "ItemName", "Amount"]
            data = [
                dialog.ui.comboBox_charge_type.currentText(),
                dialog.ui.lineEdit_item_name.text(),
                dialog.ui.spinBox_amount.value(),
            ]
            self.database.insert_record("charge_settings", fields, data)
            charge_type = tuple(charge_utils.DISCOUNT_TYPE)
            sql = f"""
                SELECT * FROM charge_settings
                WHERE
                    ChargeType IN {charge_type}
                ORDER BY ChargeSettingsKey DESC LIMIT 1
            """
            row_data = self.database.select_record(sql)[0]
            self._set_discount_data(current_row, row_data)
            self.ui.tableWidget_discount.setCurrentCell(current_row, 2)

        dialog.close_all()
        dialog.deleteLater()

    def _discount_delete(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除優待資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆優待資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        key = self.table_widget_discount.field_value(0)
        self.database.delete_record("charge_settings", "ChargeSettingsKey", key)
        self.ui.tableWidget_discount.removeRow(
            self.ui.tableWidget_discount.currentRow()
        )

    def _discount_edit(self):
        charge_settings_key = self.table_widget_discount.field_value(0)
        dialog = dialog_utils.get_dialog_input_discount(
            self, self.database, self.system_settings, charge_settings_key
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {charge_settings_key}
        """
        row_data = self.database.select_record(sql)[0]
        self._set_discount_data(self.ui.tableWidget_discount.currentRow(), row_data)

    def _set_old_man_discount(self):
        if self.ui.checkBox_old_man.isChecked():
            self.system_settings.post("老人優待", "Y")
        else:
            self.system_settings.post("老人優待", "N")

    def _set_child_discount(self):
        if self.ui.checkBox_child.isChecked():
            self.system_settings.post("兒童優待", "Y")
        else:
            self.system_settings.post("兒童優待", "N")

    def _spin_box_old_man_value_changed(self):
        age = self.ui.spinBox_old_man_age.value()
        old_man_age = number_utils.get_integer(
            self.system_settings.field("老人優待年齡")
        )

        if age != old_man_age:  # 資料被修改過才寫檔
            self.system_settings.post("老人優待年齡", age)

    def _spin_box_child_value_changed(self):
        age = self.ui.spinBox_child_age.value()
        child_age = number_utils.get_integer(self.system_settings.field("兒童優待年齡"))

        if age != child_age:  # 資料被修改過才寫檔
            self.system_settings.post("兒童優待年齡", age)

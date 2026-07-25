# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    charge_utils,
    class_utils,
    dialog_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 收費設定-自費 2021.08.02
class ChargeSettingsSelf(QtWidgets.QMainWindow):
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

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CHARGE_SETTINGS_SELF, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_self = class_utils.get_table_widget(
            self.ui.tableWidget_self, self.database
        )
        self.table_widget_self.set_column_hidden([0, 1])
        self.table_widget_herb_fee = class_utils.get_table_widget(
            self.ui.tableWidget_herb_fee, self.database
        )
        self.table_widget_herb_fee.set_column_hidden([0, 1])
        self._set_table_width()

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_regist_fee_add.clicked.connect(self._regist_fee_add)
        self.ui.toolButton_regist_fee_delete.clicked.connect(self._regist_fee_delete)
        self.ui.toolButton_regist_fee_edit.clicked.connect(self._regist_fee_edit)
        self.ui.tableWidget_self.doubleClicked.connect(self._regist_fee_edit)

        self.ui.toolButton_add_herb_fee.clicked.connect(self._add_herb_fee)
        self.ui.toolButton_remove_herb_fee.clicked.connect(self._remove_herb_fee)
        self.ui.toolButton_edit_herb_fee.clicked.connect(self._edit_herb_fee)
        self.ui.tableWidget_herb_fee.doubleClicked.connect(self._edit_herb_fee)

        self.ui.checkBox_herb_fee.clicked.connect(self._activate_herb_fee)

    # 設定欄位寬度
    def _set_table_width(self):
        self_fee_width = [60, 60, 300, 80, 80, 300]
        self.table_widget_self.set_table_heading_width(self_fee_width)

        herb_fee_width = [60, 60, 300, 100, 300]
        self.table_widget_herb_fee.set_table_heading_width(herb_fee_width)

    # 主程式控制關閉此分頁
    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    # 關閉分頁
    def close_charge_settings(self):
        self.close_all()
        self.close_tab()

    def _read_charge(self):
        self._read_self_fee()
        self._read_herb_fee()

    # 掛號費 ************************************************************************************************************
    def _regist_fee_add(self):
        dialog = dialog_utils.get_dialog_input_regist(
            self, self.database, self.system_settings, None
        )
        if not dialog.exec_():
            return

        current_row = self.ui.tableWidget_self.rowCount()
        self.ui.tableWidget_self.insertRow(current_row)
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
            "自費",
            dialog.ui.lineEdit_item_name.text(),
            dialog.ui.comboBox_ins_type.currentText(),
            dialog.ui.comboBox_share_type.currentText(),
            dialog.ui.comboBox_treat_type.currentText(),
            dialog.ui.comboBox_course.currentText(),
            dialog.ui.spinBox_amount.value(),
            dialog.ui.lineEdit_remark.text(),
        ]
        self.database.insert_record("charge_settings", fields, data)
        sql = 'SELECT * FROM charge_settings WHERE ChargeType = "自費" ORDER BY ChargeSettingsKey desc limit 1'
        row_data = self.database.select_record(sql)[0]
        self._set_self_fee_data(current_row, row_data)
        self.ui.tableWidget_self.setCurrentCell(current_row, 3)

        dialog.close_all()
        dialog.deleteLater()

    def _regist_fee_edit(self):
        charge_settings_key = self.table_widget_self.field_value(0)
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
        self._set_self_fee_data(self.ui.tableWidget_self.currentRow(), row_data)

    def _regist_fee_delete(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除自費資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆掛號收費資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        key = self.table_widget_self.field_value(0)
        self.database.delete_record("charge_settings", "ChargeSettingsKey", key)
        self.ui.tableWidget_self.removeRow(self.ui.tableWidget_self.currentRow())

    def _read_self_fee(self):
        sql = 'SELECT * FROM charge_settings WHERE ChargeType IN ("自費", "證明書費") ORDER BY ChargeSettingsKey'
        self.table_widget_self.set_db_data(sql, self._set_self_fee_data)

    def _read_herb_fee(self):
        sql = 'SELECT * FROM charge_settings WHERE ChargeType = "自費水藥" ORDER BY ChargeSettingsKey'
        self.table_widget_herb_fee.set_db_data(sql, self._set_herb_fee_data)
        row_count = self.table_widget_herb_fee.row_count()
        if row_count <= 0:
            charge_utils.set_herb_fee_basic_data(self.database)
            self._read_herb_fee()

        self._read_herb_fee_activation()

    def _set_self_fee_data(self, row_no, row):
        self_fee_row = [
            str(row["ChargeSettingsKey"]),
            string_utils.xstr(row["ChargeType"]),
            string_utils.xstr(row["ItemName"]),
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["Amount"]),
            string_utils.xstr(row["Remark"]),
        ]

        for col_no in range(len(self_fee_row)):
            self.ui.tableWidget_self.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(self_fee_row[col_no])
            )
            if col_no in [3]:
                self.ui.tableWidget_self.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            elif col_no in [4]:
                self.ui.tableWidget_self.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _set_herb_fee_data(self, row_no, row):
        herb_fee_row = [
            str(row["ChargeSettingsKey"]),
            string_utils.xstr(row["ChargeType"]),
            string_utils.xstr(row["ItemName"]),
            string_utils.xstr(row["Amount"]),
            string_utils.xstr(row["Remark"]),
        ]

        for col_no in range(len(herb_fee_row)):
            self.ui.tableWidget_herb_fee.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(herb_fee_row[col_no])
            )
            if col_no in [3]:
                self.ui.tableWidget_herb_fee.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _add_herb_fee(self):
        dialog = dialog_utils.get_dialog_herb_fee_setting(
            self, self.database, self.system_settings, None
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        charge_type = "自費水藥"
        min_weight = dialog.ui.spinBox_min_weight.value()
        max_weight = dialog.ui.spinBox_max_weight.value()

        weight_range = f"{min_weight}-{max_weight}"

        current_row = self.ui.tableWidget_herb_fee.rowCount()
        self.ui.tableWidget_herb_fee.insertRow(current_row)
        fields = ["ChargeType", "ItemName", "Amount", "Remark"]
        data = [
            charge_type,
            weight_range,
            dialog.ui.spinBox_herb_fee.value(),
            dialog.ui.lineEdit_remark.text(),
        ]
        self.database.insert_record("charge_settings", fields, data)
        sql = f'''
            SELECT * FROM charge_settings
            WHERE
                ChargeType = "{charge_type}"
            ORDER BY ChargeSettingsKey DESC LIMIT 1
        '''
        row = self.database.select_record(sql)[0]
        self._set_herb_fee_data(current_row, row)
        self.ui.tableWidget_herb_fee.setCurrentCell(current_row, 3)

        dialog.deleteLater()

    def _remove_herb_fee(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("刪除自費水藥批價資料")
        msg_box.setText(
            "<font size='4' color='red'><b>確定刪除此筆自費水藥批價資料?</b></font>"
        )
        msg_box.setInformativeText("注意！資料刪除後, 將無法回復!")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        delete_record = msg_box.exec_()
        if not delete_record:
            return

        key = self.table_widget_herb_fee.field_value(0)
        self.database.delete_record("charge_settings", "ChargeSettingsKey", key)
        self.ui.tableWidget_herb_fee.removeRow(
            self.ui.tableWidget_herb_fee.currentRow()
        )

    def _edit_herb_fee(self):
        charge_settings_key = self.table_widget_herb_fee.field_value(0)

        dialog = dialog_utils.get_dialog_herb_fee_setting(
            self, self.database, self.system_settings, charge_settings_key
        )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        charge_type = "自費水藥"
        min_weight = dialog.ui.spinBox_min_weight.value()
        max_weight = dialog.ui.spinBox_max_weight.value()

        weight_range = f"{min_weight}-{max_weight}"

        current_row = self.ui.tableWidget_herb_fee.currentRow()
        fields = ["ChargeType", "ItemName", "Amount", "Remark"]
        data = [
            charge_type,
            weight_range,
            dialog.ui.spinBox_herb_fee.value(),
            dialog.ui.lineEdit_remark.text(),
        ]
        self.database.update_record(
            "charge_settings", fields, "ChargeSettingsKey", charge_settings_key, data
        )
        sql = f"""
            SELECT * FROM charge_settings
            WHERE
                ChargeSettingsKey = {charge_settings_key}
        """
        row = self.database.select_record(sql)[0]
        self._set_herb_fee_data(current_row, row)
        self.ui.tableWidget_herb_fee.setCurrentCell(current_row, 3)

        dialog.deleteLater()

    def _read_herb_fee_activation(self):
        if self.system_settings.field("自費水藥批價原則") == "Y":
            enabled = True
        else:
            enabled = False

        self.ui.checkBox_herb_fee.setChecked(enabled)

    def _activate_herb_fee(self):
        if self.ui.checkBox_herb_fee.isChecked():
            self.system_settings.post("自費水藥批價原則", "Y")
        else:
            self.system_settings.post("自費水藥批價原則", "N")

# 處方詞庫-滑鼠輸入 2014.09.22
# -*- coding: UTF-8 -*-


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, QSettings, QSize, Qt, QTimer
from PyQt5.QtWidgets import QMessageBox

from libs import (
    class_utils,
    number_utils,
    prescript_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 處方詞庫-滑鼠輸入
class DialogMedicine(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicine, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.table_widget_prescript = args[2]
        self.medicine_set = args[3]
        self.dict_type = args[4]  # 藥品, 處置

        self.settings = QSettings("__settings.ini", QSettings.IniFormat)
        self.ui = None
        self.set_medicine = True
        self.no_deactivate_medicine = self.system_settings.field("不要顯示停用的藥品")

        self._set_ui()
        self._set_signal()
        self._read_data()
        QTimer.singleShot(0, self._bring_to_front)

    def _bring_to_front(self):
        self.raise_()
        # self.activateWindow()
        self._set_focus()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def done(self, r: int) -> None:
        ui_utils.save_settings(self, "dialog_full_medicine")
        super().done(r)

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICINE, self)
        system_utils.set_css(self, self.system_settings)

        display_mode = self.system_settings.field("詞庫視窗顯示方式")
        if display_mode == "彈出式視窗":
            self.setWindowFlags(QtCore.Qt.Popup)
            self.setWindowModality(Qt.ApplicationModal)
        else:
            self.setWindowFlags(
                QtCore.Qt.Dialog
                | QtCore.Qt.WindowTitleHint
                | QtCore.Qt.CustomizeWindowHint
            )
            self.setWindowModality(QtCore.Qt.ApplicationModal)

        ui_utils.restore_settings(
            self, "dialog_full_medicine", QSize(635, 930), QPoint(1054, 225)
        )

        self.table_widget_dict_groups = class_utils.get_table_widget(
            self.ui.tableWidget_dict_groups, self.database
        )
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self.table_widget_groups = class_utils.get_table_widget(
            self.ui.tableWidget_groups, self.database
        )

        self.table_widget_dict_groups.set_column_hidden([0])
        self.table_widget_medicine.set_column_hidden([0, 1])

        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Close).setText("關閉")
        self._set_table_width()
        self.ui.tabWidget_keyboard.setCurrentIndex(0)
        self._set_medicine_groups()

    def _set_focus(self):
        if self.dict_type == "健保傷科處置":
            self.ui.tableWidget_dict_groups.setCurrentCell(1, 1)
        else:
            self.ui.tableWidget_dict_groups.setCurrentCell(0, 1)

        self.lineEdit_input_code.setFocus()

    def _set_medicine_groups(self):
        sql = """
            SELECT MedicineMode FROM medicine
            WHERE
                MedicineType = '穴道' AND
                LENGTH(MedicineMode) > 0
            GROUP BY MedicineMode
        """
        self.table_widget_groups.set_db_data_without_heading(sql, "MedicineMode")

    # 設定信號
    def _set_signal(self):
        self.ui.tableWidget_dict_groups.itemSelectionChanged.connect(
            self.dict_groups_changed
        )
        self.ui.tableWidget_medicine.clicked.connect(self._add_prescript)
        self.ui.lineEdit_input_code.textChanged.connect(self.input_code_changed)
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.buttonBox.rejected.connect(self.rejected_button_clicked)
        self.ui.pushButton_show_all.clicked.connect(self._show_all)

        self.ui.tableWidget_groups.itemSelectionChanged.connect(self._groups_changed)
        self.ui.tabWidget_keyboard.currentChanged.connect(self._tab_changed)  # 切換分頁
        self.ui.toolButton_backspace.clicked.connect(self._input_code_backspace)

        self.ui.lineEdit_input_code.keyPressEvent = self._line_edit_input_code_key_press

        for tool_button in self.findChildren(QtWidgets.QToolButton):
            if tool_button is self.ui.toolButton_backspace:
                continue

            tool_button.clicked.connect(self.phonetic_button_clicked)

    def _line_edit_input_code_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self._add_prescript()

        return QtWidgets.QLineEdit.keyPressEvent(self.ui.lineEdit_input_code, event)

    def _tab_changed(self, i):
        tab_name = self.ui.tabWidget_keyboard.tabText(i)
        if tab_name == "經絡分類":
            self._groups_changed()

    # 設定欄位寬度
    def _set_table_width(self):
        dict_groups_width = [100, 100]
        self.table_widget_dict_groups.set_table_heading_width(dict_groups_width)

        medicine_width = [100, 100, 200, 50, 80, 90, 70, 120]
        self.table_widget_medicine.set_table_heading_width(medicine_width)

    def accepted_button_clicked(self):
        self.accept()

    def rejected_button_clicked(self):
        self.set_medicine = False
        self.reject()

    def _read_data(self):
        self._read_dict_groups()

    # 健保藥品, 藥品, 處置
    def _read_dict_groups(self):
        if self.dict_type in ["處置", "健保針灸處置", "健保傷科處置"]:
            sql = """
                SELECT * FROM dict_groups
                WHERE
                    (DictGroupsType = "處置類別" AND DictGroupsName IN ("穴道", "處置")) OR
                    (DictGroupsName IN ("外用"))
                ORDER BY DictOrderNo, DictGroupsKey
            """
        elif self.dict_type == "健保藥品":
            sql = """
                SELECT * FROM dict_groups
                WHERE
                    (DictGroupsType = "健保藥品類別") OR
                    (DictGroupsType = "成方類別")
                ORDER BY FIELD(DictGroupsName, "複方", "單方", "成方")
            """
        elif self.dict_type == "成方":
            sql = """
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "藥品類別" OR
                    DictGroupsType = "處置類別"
                ORDER BY DictOrderNo, DictGroupsKey
            """
        elif self.dict_type == "養生館":
            sql = """
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsName LIKE "養生館%"
                ORDER BY DictOrderNo, DictGroupsKey
            """
        else:  # 自費處方
            sql = """
                SELECT * FROM dict_groups
                WHERE
                    DictGroupsType = "藥品類別" OR
                    (DictGroupsType = "處置類別" AND DictGroupsName NOT IN ("檢驗", "照護")) OR
                    DictGroupsType = "成方類別" OR
                    (DictGroupsType = "藥品類別" AND
                     DictGroupsName NOT IN ("單方", "複方", "水藥", "外用", "高貴", "器材"))
                GROUP BY DictGroupsName
                ORDER BY
                    FIELD(DictGroupsName, "成方", "其他", "處置", "穴道", "器材", "高貴", "外用", "水藥", "複方", "單方") DESC,
                    DictOrderNo
            """

        self.table_widget_dict_groups.set_db_data(sql, self._set_dict_groups_data)

    def _set_dict_groups_data(self, rec_no, rec):
        dict_groups_rec = [
            string_utils.xstr(rec["DictGroupsKey"]).strip(),
            string_utils.xstr(rec["DictGroupsName"]),
        ]

        for column in range(len(dict_groups_rec)):
            self.ui.tableWidget_dict_groups.setItem(
                rec_no, column, QtWidgets.QTableWidgetItem(dict_groups_rec[column])
            )

    def dict_groups_changed(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        self._read_medicine(dict_groups_type)
        # self.ui.tableWidget_dict_groups.setFocus(True)
        self.lineEdit_input_code.setText(None)
        self.lineEdit_input_code.setFocus()

    def _read_medicine(self, dict_groups_type, input_code=None, is_phonetic=False):
        input_code_str = ""
        if self.system_settings.field("詞庫排序") == "點擊率":
            order_type = "ORDER BY HitRate DESC"
        elif self.system_settings.field("詞庫排序") == "最後點擊時戳":
            order_type = "ORDER BY TimeStamp DESC"
        else:
            order_type = """
                ORDER BY LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
            """

        if input_code is not None:
            if is_phonetic:
                input_code_str = f'''
                    AND (
                        (MedicineName LIKE "%{input_code}%") OR
                        (InputCode LIKE "{input_code}%")
                    )
                '''
            else:
                input_code_str = f'''
                    AND (
                        (MedicineName LIKE "%{input_code}%") OR
                        (InputCode LIKE "{input_code}%") OR
                        (MedicineCode LIKE "{input_code}%")
                    )
                '''

        unit_condition = ""
        if self.dict_type == "健保藥品":
            unit_condition = ' AND (Unit != "錢")'

        medicine_type_condition = f'(MedicineType = "{dict_groups_type.strip()}")'
        # medicine_type_condition = '(MedicineType IN ("單方", "複方", "成方"))'

        if self.no_deactivate_medicine == "Y":
            no_deactivate = " AND (Deactivate IS NULL OR LENGTH(Deactivate) = 0)"
        else:
            no_deactivate = ""

        sql = f"""
            SELECT * FROM medicine
            WHERE
                {medicine_type_condition}
                {unit_condition}
                {input_code_str}
                {no_deactivate}
                {order_type}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            if input_code is None:
                self.lineEdit_input_code.setText(None)
                self.ui.tableWidget_medicine.setRowCount(0)
            else:
                input_code = string_utils.str_to_phonetic(input_code[:-1])
                self.lineEdit_input_code.setText(input_code)
                self.lineEdit_input_code.setFocus()

            return

        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _set_medicine_data(self, row_no, row):
        safe_quantity = number_utils.get_integer(row["SafeQuantity"])
        quantity = number_utils.get_integer(row["Quantity"])
        price = string_utils.get_formatted_str("單價", row["SalePrice"])
        deactivate = string_utils.xstr(row["Deactivate"])
        non_nhi = string_utils.xstr(row["NonNHI"])

        if deactivate == "":
            if safe_quantity > 0 and quantity <= safe_quantity:
                deactivate = "庫存量不足"
            elif self.medicine_set == 1 and non_nhi == "Y":
                deactivate = "僅用於自費"

        dosage_mode = self.system_settings.field("劑量模式")
        if dosage_mode in [None, ""]:
            dosage_mode = "日劑量"

        medicine_name = string_utils.xstr(row["MedicineName"])
        ins_code = string_utils.xstr(row["InsCode"])

        medicine_type = string_utils.xstr(row["MedicineType"])
        header_item = self.ui.tableWidget_medicine.horizontalHeaderItem(5)
        if medicine_type not in ["單方", "複方"]:
            if header_item:
                header_item.setText("庫存量")

            ins_code = string_utils.xstr(quantity)
            if ins_code == "0":
                ins_code = ""
        else:
            if header_item:
                header_item.setText("健保代碼")

        medicine_row = [
            string_utils.xstr(row["MedicineKey"]),
            string_utils.xstr(row["MedicineType"]),
            medicine_name,
            string_utils.xstr(row["Unit"]),
            price,
            ins_code,
            string_utils.get_formatted_str(dosage_mode, row["Dosage"]),
            deactivate,
        ]

        for col_no in range(len(medicine_row)):
            self.ui.tableWidget_medicine.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(medicine_row[col_no])
            )

            align = QtCore.Qt.AlignLeft
            if col_no in [3]:
                align = QtCore.Qt.AlignCenter
            elif col_no in [5]:
                if medicine_type not in ["單方", "複方"]:
                    align = QtCore.Qt.AlignRight
                else:
                    align = QtCore.Qt.AlignLeft
            elif col_no in [4, 6]:
                align = QtCore.Qt.AlignRight

            self.ui.tableWidget_medicine.item(row_no, col_no).setTextAlignment(
                align | QtCore.Qt.AlignVCenter
            )
            if deactivate == "庫存量不足":
                self.ui.tableWidget_medicine.item(row_no, col_no).setForeground(
                    QtGui.QColor("red")
                )
            elif deactivate != "":
                self.ui.tableWidget_medicine.item(row_no, col_no).setForeground(
                    QtGui.QColor("gray")
                )

    def phonetic_button_clicked(self):
        input_code = string_utils.xstr(self.ui.lineEdit_input_code.text()).strip()
        press_key = string_utils.xstr(self.sender().text()).strip()
        input_code += press_key

        # 暫時阻斷訊號，避免重複觸發 input_code_changed 造成邏輯混亂
        self.ui.lineEdit_input_code.blockSignals(True)
        self.ui.lineEdit_input_code.setText(input_code)
        self.ui.lineEdit_input_code.blockSignals(False)
        # 手動觸發一次查詢
        self.input_code_changed()

    def _show_all(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        self._read_medicine(dict_groups_type)

        self.ui.lineEdit_input_code.setText(None)
        self.ui.lineEdit_input_code.setFocus()

    def input_code_changed(self):
        dict_groups_type = self.table_widget_dict_groups.field_value(1)
        input_code = string_utils.xstr(self.ui.lineEdit_input_code.text()).strip()
        if input_code == "":
            # self._read_medicine(dict_groups_type)
            self.ui.lineEdit_input_code.setFocus()
            return

        if input_code[0] in string_utils.phonetic_list:
            input_code = string_utils.phonetic_to_str(input_code)
            self._read_medicine(dict_groups_type, input_code, is_phonetic=True)
        else:
            self._read_medicine(dict_groups_type, input_code)

        self.ui.lineEdit_input_code.setFocus()
        self.ui.lineEdit_input_code.setCursorPosition(len(input_code))

    def _add_prescript(self):
        deactivate = self.table_widget_medicine.field_value(7)
        medicine_name = self.table_widget_medicine.field_value(2)
        if self.table_widget_prescript != "進貨單" and deactivate != "":
            if deactivate == "庫存量不足":
                if self.system_settings.field("庫存量不足不要提醒") == "Y":
                    pass
                else:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "庫存量不足",
                        f"""
                            <font color="red">
                                <h3>「{medicine_name}」低於安全庫存量, 庫存量不足</h3>
                            </font>
                        """,
                        "請盡速補貨",
                    )
            else:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "藥品已停用",
                    f'<font color="red"><h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3></font>',
                    "請開立其他藥品",
                )
                return

        self._add_medicine()

    def _add_compound_medicine(self):
        row = prescript_utils.get_medicine_row(self.table_widget_medicine)
        self.parent.add_ref_compound(row)
        self.ui.lineEdit_input_code.setText(None)

    def get_medicine(self):
        if not self.set_medicine:
            medicine_row = None
        else:
            medicine_row = {
                "medicine_key": self.table_widget_medicine.field_value(0),
                "medicine_type": self.table_widget_medicine.field_value(1),
            }

        return medicine_row

    def _add_medicine(self):
        if self.table_widget_prescript is None:
            self.close()
            return

        try:
            tab_prescript = self.parent.tab_list[
                self.medicine_set - 1
            ]  # call by ins_prescript/self_prescript
        except AttributeError:
            try:
                self._add_compound_medicine()
                return
            except AttributeError:
                self._add_independent_medicine()
                return

        medicine_key = self.table_widget_medicine.field_value(0)
        medicine_type = self.table_widget_medicine.field_value(1)
        if self.dict_type == "養生館":
            self._add_massage_prescript()
        elif medicine_type == "成方":
            prescript_utils.extract_compound(
                tab_prescript,
                self.database,
                self.system_settings,
                medicine_key,
                self.table_widget_medicine,
            )
        elif medicine_type in ["穴道", "處置", "外用"] and self.medicine_set <= 1:
            prescript_utils.add_treat(tab_prescript, self.table_widget_medicine)
        else:
            prescript_utils.add_medicine(tab_prescript, self.table_widget_medicine)

        self.ui.lineEdit_input_code.setText(None)
        self.ui.lineEdit_input_code.setFocus()

    def _add_independent_medicine(self):
        row = prescript_utils.get_medicine_row(self.table_widget_medicine)
        if self.dict_type == "盤點藥品":
            self.parent.insert_inventory_item(row)
        else:
            self.parent.insert_prescript_row(row)

    def _add_massage_prescript(self):
        self.table_widget_prescript.setRowCount(
            self.table_widget_prescript.rowCount() + 1
        )
        data = [
            None,
            None,
            self.table_widget_medicine.field_value(0),
            self.table_widget_medicine.field_value(2),
            1,
            self.table_widget_medicine.field_value(4),
            number_utils.get_float(self.table_widget_medicine.field_value(5)),
            number_utils.get_float(self.table_widget_medicine.field_value(5)),
            None,
        ]
        row_no = self.table_widget_prescript.rowCount() - 1
        for col_no in range(len(data)):
            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, data[col_no])
            self.table_widget_prescript.setItem(row_no, col_no, item)
            if col_no in [4, 6, 7]:
                self.table_widget_prescript.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif col_no in [5]:
                self.table_widget_prescript.item(row_no, col_no).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

        self.parent.calculate_total_fee()

    def _groups_changed(self):
        if not self.ui.tableWidget_groups.selectedItems():
            return

        groups = self.ui.tableWidget_groups.selectedItems()[0].text()
        order_type = """
            ORDER BY LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        """
        if self.system_settings.field("詞庫排序") == "點擊率":
            order_type = "ORDER BY HitRate DESC"
        elif self.system_settings.field("詞庫排序") == "最後點擊時戳":
            order_type = "ORDER BY TimeStamp DESC"

        sql = f'''
            SELECT * FROM medicine
            WHERE
                (MedicineType = "穴道") AND
                (MedicineMode = "{groups}")
            {order_type}
        '''
        self.table_widget_medicine.set_db_data(sql, self._set_medicine_data)

    def _input_code_backspace(self):
        input_code = self.ui.lineEdit_input_code.text().strip()
        input_code = input_code[: len(input_code) - 1]
        self.ui.lineEdit_input_code.setText(input_code)

        if input_code == "":
            dict_groups_type = self.table_widget_dict_groups.field_value(1)
            self._read_medicine(dict_groups_type)

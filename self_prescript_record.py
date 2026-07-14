# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    db_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    prescript_utils,
    stock_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 輸入自費處方 2018.04.14.
class SelfPrescriptRecord(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super(SelfPrescriptRecord, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.medicine_set = args[3]
        self.call_from = args[4]
        if self.case_key is None:
            self.case_date = None
        else:
            self.case_date = self.parent.medical_record["CaseDate"]

        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)
        self.warned = False
        self.prescript_edit_mode = self.system_settings.field("處方輸入編輯模式")
        self.dict_dialog = self.system_settings.field("詞庫視窗顯示方式")
        self.dosage_mode = self.system_settings.field("劑量模式")
        self.dosage_percent = self.system_settings.field("比例法劑量")
        self.popup_menu = self.system_settings.field("刪除處方啟用彈出式選單")
        self.medicine_sort = self.system_settings.field("處方排序")
        self.refresh_price = self.system_settings.field("拷貝處方藥價更新")
        self.no_zero_price = self.system_settings.field("單日計價輸入藥品不要歸零")
        self.no_instruction_pres_days = self.system_settings.field(
            "單一處方服法不可取代用藥天數"
        )
        self.clinic_name = self.system_settings.field("院所名稱")
        self.ratio = charge_utils.get_ratio(
            self.database
        )  # 2026-02-05 初蘊-自費藥品售價倍率

        self._do_set_dosage_percent = True
        self.is_vegetarian = False

        if (
            patient_utils.get_patient_extension_settings(
                self.database, self.parent.patient_key, "吃素"
            )
            == "Y"
        ):
            self.is_vegetarian = True

        self._set_ui()
        self._set_signal()
        if self.case_key is not None:
            self._read_prescript()

        self._set_permission()
        self._set_patient_discount_rate()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_SELF_PRESCRIPT_RECORD, self)
        system_utils.set_css(self, self.system_settings)
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database
        )
        self.table_widget_prescript.set_column_hidden([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.table_widget_prescript.set_parent(self.parent.parent)

        self.ui.tableWidget_prescript.setDragEnabled(True)
        self.ui.tableWidget_prescript.setAcceptDrops(True)
        system_utils.disable_mouse_wheel(self, QtWidgets.QComboBox)
        system_utils.disable_mouse_wheel(self, QtWidgets.QSpinBox)

        if self.system_settings.field("處方劑量欄位可以排序") == "Y":
            self.ui.tableWidget_prescript.horizontalHeader().setSectionsClickable(True)
        else:
            self.ui.tableWidget_prescript.horizontalHeader().setSectionsClickable(False)

        self.read_only_columns = [
            prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            prescript_utils.SELF_PRESCRIPT_COL_NO["Info"],
        ]
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, "病歷資料", "修改單價", self.user_name
            )
            != "Y"
        ):
            self.read_only_columns.append(
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
            )

        self._set_table_width()
        self._set_combo_box()
        self._set_discount_visible()
        self.ui.tableWidget_prescript.viewport().installEventFilter(self)
        self.ui.label_total_dosage_setting.setVisible(False)
        self.ui.doubleSpinBox_total_dosage.setVisible(False)
        for i in range(self.ui.horizontalLayout_dosage_percent.count()):
            widget = self.ui.horizontalLayout_dosage_percent.itemAt(i).widget()
            if widget:
                widget.hide()

        if self.dosage_percent == "Y":
            self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                13, QtWidgets.QTableWidgetItem("比例")
            )
            self.ui.label_total_dosage_setting.setVisible(True)
            self.ui.doubleSpinBox_total_dosage.setVisible(True)
            spacer = QtWidgets.QSpacerItem(
                40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
            )
            self.ui.horizontalLayout_dosage_percent.addItem(spacer)

        try:
            if self.is_vegetarian:
                item = QtWidgets.QTableWidgetItem("處方名稱 (病人吃素)")
                item.setForeground(
                    QtGui.QBrush(QtGui.QColor("red"))
                )  # 設定字體顏色為紅色

                self.ui.tableWidget_prescript.setHorizontalHeaderItem(
                    prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], item
                )
        except Exception:
            pass

    def eventFilter(self, source, event):
        if self.popup_menu == "Y":
            return False

        if (
            event.type() == QtCore.QEvent.MouseButtonRelease
            and event.button() == QtCore.Qt.RightButton
        ):
            if source is self.ui.tableWidget_prescript.viewport():
                self.remove_medicine()

        try:
            return super(SelfPrescriptRecord, self).eventFilter(source, event)
        except Exception:
            return False

    def _set_patient_discount_rate(self):
        if self.system_settings.field("自費折扣方式") == "統一折扣":
            return

        try:
            discount_type = patient_utils.get_patient_discount_type(
                self.database, self.parent.patient_key
            )
        except Exception:
            return

        if discount_type in ["", None]:
            return

        self.ui.label_discount.setText(f"{discount_type[:4]}優待")
        if self.case_key is not None:
            sql = """
                SELECT DiscountRate FROM dosage
                WHERE
                    CaseKey = %s AND
                    MedicineSet = %s
            """
            row = self.database.select_record(sql, (self.case_key, self.medicine_set))
            if len(row) > 0:  # 已經設定過了
                return

        discount_rate = charge_utils.get_self_fee_discount_rate(
            self.database, discount_type
        )
        if discount_rate is not None:
            self.ui.spinBox_discount_rate.setValue(discount_rate)

    def _set_discount_visible(self):
        if self.system_settings.field("自費折扣方式") == "個別折扣":
            return

        enabled = False
        self.ui.label_discount.setVisible(enabled)
        self.ui.spinBox_discount_rate.setVisible(enabled)
        self.ui.label_percent.setVisible(enabled)
        self.ui.lineEdit_discount_fee.setVisible(enabled)

    # 設定信號
    def _set_signal(self):
        self.ui.toolButton_add_medicine.clicked.connect(
            lambda: self.append_null_medicine(insert_row_no=None)
        )
        self.ui.toolButton_remove_medicine.clicked.connect(self.remove_medicine)
        self.ui.toolButton_dictionary.clicked.connect(self.open_medicine_dictionary)
        self.ui.toolButton_project.clicked.connect(self._open_project)
        self.ui.toolButton_dosage.clicked.connect(self._open_dosage)
        self.ui.toolButton_dict_examination.clicked.connect(self._open_dict_examination)
        self.ui.toolButton_show_costs.clicked.connect(self._show_costs)
        self.ui.toolButton_medicine_info.clicked.connect(
            self._show_medicine_description
        )
        self.ui.toolButton_copy_to_previous.clicked.connect(
            self._copy_to_previous_prescript
        )
        self.ui.toolButton_copy_to_next.clicked.connect(self._copy_to_next_prescript)
        self.ui.toolButton_clear_medicine.clicked.connect(
            lambda: self._clear_medicine(warning=True)
        )
        self.ui.toolButton_set_prescript_remark.clicked.connect(
            self._set_prescript_remark
        )
        self.ui.toolButton_set_medicine_name.clicked.connect(self._set_medicine_name)
        self.ui.toolButton_instruction.clicked.connect(self._set_instruction)
        self.ui.toolButton_compound_json.clicked.connect(
            self._open_dialog_compound_json
        )
        self.ui.toolButton_insert_compound.clicked.connect(self._insert_compound)

        self.ui.tableWidget_prescript.keyPressEvent = (
            self._table_widget_prescript_key_press
        )
        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.itemSelectionChanged.connect(
            self._prescript_item_selection_changed
        )
        self.ui.tableWidget_prescript.cellClicked.connect(self._prescript_cell_clicked)
        self.ui.tableWidget_prescript.doubleClicked.connect(self._open_prescript_dialog)

        self.ui.comboBox_pres_days.currentTextChanged.connect(self.pres_days_changed)
        self.ui.comboBox_package.currentTextChanged.connect(self.package_changed)
        self.ui.tableWidget_prescript.dropEvent = self.prescript_drop_event
        self.ui.spinBox_discount_rate.valueChanged.connect(
            lambda: self._calculate_discount(set_focus=True)
        )

        self.ui.comboBox_package.keyPressEvent = self._combo_box_package_key_press
        self.ui.comboBox_pres_days.keyPressEvent = self._combo_box_pres_days_key_press
        self.ui.comboBox_valuation.currentTextChanged.connect(self._set_price)

        self.ui.radioButton_direct_medicine.clicked.connect(self._receive_medicine)
        self.ui.radioButton_process_medicine.clicked.connect(self._receive_medicine)

        self.ui.lineEdit_discount_fee.textChanged.connect(self._discount_fee_changed)
        self.ui.lineEdit_discount_fee.textEdited.connect(self._discount_fee_edited)

        self.ui.toolButton_acupuncture_point.clicked.connect(
            self._show_acupuncture_point
        )
        self.ui.doubleSpinBox_total_dosage.valueChanged.connect(
            self._total_dosage_value_changed
        )

        if self.popup_menu == "Y":
            self.ui.tableWidget_prescript.setContextMenuPolicy(
                QtCore.Qt.CustomContextMenu
            )

        self.ui.tableWidget_prescript.customContextMenuRequested.connect(
            self._show_medicine_context_menu
        )
        self.ui.checkBox_print_receipt.clicked.connect(self._print_receipt_clicked)

    def _show_medicine_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        menu.addAction(ui_utils.ICON_REMOVE, "刪除處方", self.remove_medicine)
        menu.addAction(ui_utils.ICON_ADD, "插入處方", self.insert_medicine)
        menu.addSeparator()
        menu.addAction(
            ui_utils.ICON_REDO, "拷貝處方至前頁", self._copy_to_previous_prescript
        )
        menu.addAction(
            ui_utils.ICON_FINISH, "拷貝處方至下頁", self._copy_to_next_prescript
        )
        menu.addSeparator()
        menu.addAction(
            ui_utils.ICON_DICT, "顯示藥品詞庫", self.open_medicine_dictionary
        )
        menu.addAction(
            ui_utils.ICON_HELP, "顯示藥品說明", self._show_medicine_description
        )
        menu.addAction(ui_utils.ICON_INFO, "顯示用藥成本", self._show_costs)
        menu.addSeparator()
        menu.addAction(ui_utils.ICON_CLEAR, "刪除全部處方", self._clear_medicine)

        font = QtGui.QFont("微軟正黑體", 14)
        font.setBold(True)
        menu.setFont(font)
        menu.exec_(self.ui.tableWidget_prescript.viewport().mapToGlobal(pos))

    def _open_dosage(self):
        medicine_name_item = self.ui.tableWidget_prescript.item(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if medicine_name_item is None:
            return

        self.ui.tableWidget_prescript.setCurrentCell(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        )
        self._open_prescript_dialog()

    def _open_prescript_dialog(self):
        prescript_utils.open_prescript_dialog(
            self,
            self.database,
            self.system_settings,
            self.ui.tableWidget_prescript,
            "自費",
        )

    def _combo_box_package_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.ui.comboBox_pres_days.setFocus(True)

        return QtWidgets.QComboBox.keyPressEvent(self.ui.comboBox_package, event)

    def _combo_box_pres_days_key_press(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            self.ui.comboBox_instruction.setFocus(True)

        return QtWidgets.QComboBox.keyPressEvent(self.ui.comboBox_pres_days, event)

    def _set_permission(self):
        # if self.call_from == '醫師看診作業':
        #     return

        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, "醫師看診作業", "病歷登錄", self.user_name
            )
            == "Y"
        ):
            return

        if (
            personnel_utils.get_permission(
                self.database, "病歷資料", "病歷修正", self.user_name
            )
            == "Y"
        ):
            return

        self.ui.toolButton_add_medicine.setEnabled(False)
        self.ui.toolButton_remove_medicine.setEnabled(False)
        self.ui.toolButton_dictionary.setEnabled(False)
        self.ui.toolButton_dosage.setEnabled(False)
        self.ui.toolButton_show_costs.setEnabled(False)
        self.ui.toolButton_medicine_info.setEnabled(False)
        self.ui.toolButton_clear_medicine.setEnabled(False)
        self.ui.toolButton_copy_to_previous.setEnabled(False)
        self.ui.toolButton_copy_to_next.setEnabled(False)

        self.ui.comboBox_package.setEnabled(False)
        self.ui.comboBox_pres_days.setEnabled(False)
        self.ui.comboBox_instruction.setEnabled(False)

        self.ui.spinBox_discount_rate.setEnabled(False)

        self.ui.tableWidget_prescript.setEnabled(False)
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            for col_no in range(self.ui.tableWidget_prescript.columnCount()):
                item = self.ui.tableWidget_prescript.item(row_no, col_no)
                if item is None:
                    continue

                item.setForeground(QtGui.QColor("black"))

    def prescript_drop_event(self, event):
        current_table_widget = event.source()

        source_row = current_table_widget.currentRow()
        target_item = current_table_widget.itemAt(event.pos())

        if target_item is None:
            target_row = current_table_widget.rowCount()
        else:
            target_row = target_item.row()

        medicine_name = current_table_widget.item(
            source_row, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if medicine_name is None:
            return

        medicine_name = medicine_name.text()
        if medicine_name == "":
            return

        prescript_row = []
        for col_no in range(current_table_widget.columnCount()):
            prescript_row.append(current_table_widget.item(source_row, col_no))

        current_table_widget.insertRow(target_row)
        for col_no in range(len(prescript_row)):
            current_table_widget.setItem(
                target_row, col_no, QtWidgets.QTableWidgetItem(prescript_row[col_no])
            )

        self._adjust_prescript_column(target_row)

        # medicine_key_item = prescript_row[prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineKey']]
        # if medicine_key_item is not None:
        #     database._add_prescript_info_button(target_row, medicine_key_item.text())

        if target_row > source_row:
            remove_row = source_row
        else:
            remove_row = source_row + 1

        current_table_widget.removeRow(remove_row)
        current_table_widget.resizeRowsToContents()

        if target_row < source_row:
            move_row = target_row
        else:
            move_row = target_row - 1

        current_table_widget.setCurrentCell(
            move_row, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )

        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()

    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_package, nhi_utils.PACKAGE, None)
        ui_utils.set_combo_box(
            self.ui.comboBox_pres_days, nhi_utils.SELF_PRESDAYS, None
        )
        ui_utils.set_combo_box(self.ui.comboBox_valuation, nhi_utils.VALUATION)
        ui_utils.set_instruction_combo_box(self.database, self.ui.comboBox_instruction)

    def _discount_fee_edited(self):
        discount_fee = number_utils.get_integer(self.ui.lineEdit_discount_fee.text())
        if discount_fee <= 0:
            self.ui.spinBox_discount_rate.setValue(100)
            return

        self.ui.spinBox_discount_rate.setValue(-1)

    def _discount_fee_changed(self):
        # self_total_fee = self._get_self_total_fee()
        self_total_fee = self._compute_self_total_fee_without_discount()
        discount_fee = number_utils.get_integer(self.ui.lineEdit_discount_fee.text())
        total_fee = self_total_fee - discount_fee

        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))
        self.parent.calculate_self_fees()
        self.ui.lineEdit_discount_fee.setFocus()

    def _table_widget_prescript_key_press(self, event):
        if self.system_settings.field("不要自動切換輸入法") == "Y":
            pass
        else:
            system_utils.set_keyboard_layout("英文")

        key = event.key()
        current_row = self.ui.tableWidget_prescript.currentRow()
        current_column = self.ui.tableWidget_prescript.currentColumn()

        if key == QtCore.Qt.Key_Delete or key == QtCore.Qt.Key_F5:
            self.remove_medicine()
        elif key == QtCore.Qt.Key_Insert:
            self.insert_medicine()
        elif key == QtCore.Qt.Key_Up:
            if (
                self.ui.tableWidget_prescript.item(
                    current_row, prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"]
                )
                is None
            ):
                self.ui.tableWidget_prescript.removeRow(current_row)
                return
            if current_column in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            ]:
                self._set_dosage_format(current_row, current_column)
            elif current_column in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            ]:
                self._set_price_format(current_row, current_column)
            # elif current_column == prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction']:
            #     self._set_dosage_percent()
        elif key == QtCore.Qt.Key_Down:
            if (
                current_row == self.ui.tableWidget_prescript.rowCount() - 1
                and self.ui.tableWidget_prescript.item(
                    current_row, prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"]
                )
                is not None
            ):
                self.append_null_medicine()

            if current_column in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            ]:
                self._set_dosage_format(current_row, current_column)
            elif current_column in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            ]:
                self._set_price_format(current_row, current_column)
            # elif current_column == prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction']:
            #     self._set_dosage_percent()
        elif key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
            if current_column == prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]:
                self.open_medicine_dialog()
            elif current_column == prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]:
                if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row + 1,
                        prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
                    )
                elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                    self.append_null_medicine()
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row + 1,
                        prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"],
                    )

                if self.doubleSpinBox_total_dosage.value() > 0:
                    self._set_dosage_percent()
            elif current_column in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            ]:
                if current_column in [
                    prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                ]:
                    self._set_dosage_format(current_row, current_column)
                elif current_column in [
                    prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                    prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
                ]:
                    try:
                        self._set_price_format(current_row, current_column)
                        if (
                            current_column
                            == prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
                            and self.ui.comboBox_valuation.currentText() == "單日計價"
                        ):
                            self._check_ins_drug_single_day_price_changed()
                    except Exception:
                        pass

                if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                    if (
                        current_column
                        == prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
                    ):
                        self.ui.tableWidget_prescript.setCurrentCell(
                            current_row + 1,
                            prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                        )
                    elif (
                        current_column
                        == prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]
                    ):
                        self.ui.tableWidget_prescript.setCurrentCell(
                            current_row + 1,
                            prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
                        )
                    elif (
                        current_column == prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
                    ):
                        self.ui.tableWidget_prescript.setCurrentCell(
                            current_row + 1,
                            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                        )
                elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                    self.append_null_medicine()
                    self.ui.tableWidget_prescript.setCurrentCell(
                        current_row + 1,
                        prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"],
                    )

                self.ui.tableWidget_prescript.setFocus()
                # elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                #     if current_column == prescript_utils.SELF_PRESCRIPT_COL_NO['Dosage']:
                #         self.ui.comboBox_package.setFocus(True)

        self._adjust_prescript_column(current_row)

        self.ui.tableWidget_prescript.setFocus()
        if self.prescript_edit_mode == "Y" and current_column in [
            prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"],
            prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"],
        ]:
            self.ui.tableWidget_prescript.edit(
                self.ui.tableWidget_prescript.currentIndex()
            )

        return QtWidgets.QTableWidget.keyPressEvent(
            self.ui.tableWidget_prescript, event
        )

    def _set_dosage_format(self, row_no, col_no):
        if self.dosage_mode in ["日劑量", "總量"]:
            dosage_format = ".1f"
        else:
            dosage_format = ".2f"

        self.table_widget_prescript.set_cell_text_format(
            row_no,
            col_no,
            dosage_format,
            "float",
        )

    def _set_price_format(self, row_no, col_no):
        price_format = ".2f"

        self.table_widget_prescript.set_cell_text_format(
            row_no,
            col_no,
            price_format,
            "float",
        )

    def open_medicine_dialog(self):
        current_row = self.ui.tableWidget_prescript.currentRow()
        self.ui.tableWidget_prescript.setCurrentCell(
            current_row, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        )
        self.ui.tableWidget_prescript.setCurrentCell(
            current_row, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        item = self.ui.tableWidget_prescript.item(
            current_row, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if item is None or item.text() == "":
            if self.ui.tableWidget_prescript.rowCount() >= 2:
                self.ui.tableWidget_prescript.removeRow(current_row)
                self.ui.tableWidget_prescript.setCurrentCell(
                    0, prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"]
                )
            return

        previous_medicine_name = self.table_widget_prescript.field_value(
            prescript_utils.SELF_PRESCRIPT_COL_NO["BackupMedicineName"]
        )

        if item.text() == previous_medicine_name:
            if current_row < self.ui.tableWidget_prescript.rowCount() - 1:
                self.ui.tableWidget_prescript.setCurrentCell(
                    current_row + 1,
                    prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"],
                )
            elif current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                self.ui.tableWidget_prescript.setCurrentCell(
                    0,
                    prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"],
                )
            return

        keyword = item.text()
        # keyword = string_utils.replace_ascii_char(["\\", '"', "'"], keyword)
        sql = """
            SELECT * FROM medicine
            WHERE
                (MedicineName LIKE %s OR
                 InputCode LIKE %s OR
                 MedicineCode = %s OR
                 InsCode = %s)
        """
        params = (f"%{keyword}%", f"{keyword}%", keyword, keyword)
        rows = self.database.select_record(sql, params)

        if len(rows) <= 0:
            item.setText(previous_medicine_name)
        elif len(rows) == 1:
            medicine_type = string_utils.xstr(rows[0]["MedicineType"])
            medicine_key = string_utils.xstr(rows[0]["MedicineKey"])
            if medicine_type == "成方":
                try:
                    # self.ui.tableWidget_prescript.itemChanged.disconnect()
                    self.ui.tableWidget_prescript.blockSignals(True)
                except Exception:
                    pass

                prescript_utils.extract_compound(
                    self,
                    self.database,
                    self.system_settings,
                    medicine_key,
                    None,
                )
                # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
                self.ui.tableWidget_prescript.blockSignals(False)
                return

            deactivate = string_utils.xstr(rows[0]["Deactivate"])
            medicine_name = string_utils.xstr(rows[0]["MedicineName"])
            if deactivate != "":
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "藥品已停用",
                    f"""
                        <font color="red">
                            <h3>{medicine_name}已經停用<br>停用原因: {deactivate}</h3>
                        </font>
                    """,
                    "請開立其他藥品",
                )
                item.setText(previous_medicine_name)
                return

            dosage = rows[0]["Dosage"]
            if dosage is not None:
                dosage = number_utils.get_float(dosage)

            if not self.append_prescript(rows[0], dosage=dosage):
                return

            if current_row == self.ui.tableWidget_prescript.rowCount() - 1:
                self.append_null_medicine()
            else:
                self.ui.tableWidget_prescript.setCurrentCell(
                    current_row + 1,
                    prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"],
                )
        else:
            dialog = dialog_utils.get_dialog_input_medicine(
                self,
                self.database,
                self.system_settings,
                "所有藥品",
                self.medicine_set,
                self.ui.tableWidget_prescript,
                previous_medicine_name,
                keyword,
            )
            dialog.exec_()
            dialog.deleteLater()

    def append_prescript(
        self,
        row,
        dosage=None,
        set_valuation=True,
        set_dosage_percent=True,
        duplicate_warning=None,
    ):
        old_dosage = self.table_widget_prescript.field_value(
            prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        )
        if old_dosage not in ["", None]:
            dosage = old_dosage

        medicine_key = string_utils.xstr(row["MedicineKey"])
        in_price = prescript_utils.get_medicine_field(
            self.database, medicine_key, "InPrice"
        )
        if in_price is not None and in_price > 0:
            info = "$"
        else:
            info = ""

        medicine_type = string_utils.xstr(row["MedicineType"])
        medicine_name = string_utils.xstr(row["MedicineName"])

        if self.is_vegetarian and prescript_utils.is_animal_derived(
            self.database, medicine_key
        ):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("含動物性成份藥品")
            msg_box.setText(
                f"""
                    <font color="red"><h3>
                        注意！本藥品「{medicine_name}」動物性成份, 此病人吃素是否繼續開立?
                    </h3></font>"""
            )
            msg_box.setInformativeText("請確定是否繼續給藥.")
            msg_box.addButton(QPushButton("繼續給藥"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            append_medicine = msg_box.exec_()
            if append_medicine == QMessageBox.RejectRole:
                item = self.ui.tableWidget_prescript.item(
                    self.ui.tableWidget_prescript.currentRow(),
                    prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"],
                )
                if item is not None:
                    item.setText(None)

                return False

        if not duplicate_warning or self.dict_dialog == "彈出式視窗":
            duplicate_warning = False
        else:
            duplicate_warning = True

        if prescript_utils.check_prescript_duplicates(
            self.ui.tableWidget_prescript,
            medicine_type,
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"],
            medicine_key,
            duplicate_warning=duplicate_warning,
        ):
            return False

        dosage_mode = self.dosage_mode
        if dosage_mode in [None, ""]:
            dosage_mode = "日劑量"

        if (
            self.ui.comboBox_valuation.currentText() == "單日計價"
            and "加價" in medicine_name
            and medicine_type in ["單方", "複方"]
        ):
            system_utils.show_message_box(
                QMessageBox.Critical,
                "請注意",
                '<font size="5" color="red"><b>單日計價的加價自費粉藥, 請輸入在自費2處方內!</b></font>',
                "謝謝合作.",
            )
            return False

        try:
            price = string_utils.get_formatted_str(
                "單價", number_utils.get_float(row["SalePrice"])
            )
        except Exception:
            try:
                price = string_utils.get_formatted_str(
                    "單價", number_utils.get_float(row["Price"])
                )
            except Exception:
                price = string_utils.get_formatted_str("單價", None)

        if (
            medicine_name
            not in ["自費藥費", "自費水藥", "自費粉藥", charge_utils.PROCESS_MEDICINE]
            and self.refresh_price == "Y"
        ):
            try:
                sale_price = prescript_utils.get_medicine_field(
                    self.database, medicine_key, "SalePrice"
                )
                if sale_price is not None and sale_price > 0:
                    price = string_utils.get_formatted_str("單價", sale_price)
            except Exception:
                pass

        price = self._get_ratio_price(medicine_type, price)

        try:
            amount = number_utils.get_float(dosage) * number_utils.get_float(price)
            amount = string_utils.get_formatted_str("單價", amount)
        except Exception:
            amount = string_utils.get_formatted_str("單價", None)

        if (
            self.ui.comboBox_valuation.currentText() == "單複方不計價"
            and medicine_type in ["單方", "複方"]
        ):
            price = "0.0"
            amount = "0.0"
        elif (
            self.ui.comboBox_valuation.currentText() == "單日計價"
            and "加價" not in medicine_name
            and medicine_name
            not in ["自費藥費", "自費水藥", "自費粉藥", charge_utils.PROCESS_MEDICINE]
            and medicine_type.strip() in ["單方", "複方", "水藥"]
        ):
            if self.no_zero_price == "Y":
                pass
            else:
                price = "0.0"
                amount = "0.0"

        medicine_name = string_utils.xstr(row["MedicineName"])

        instruction = None

        try:  # 2024-08-21 曙光
            instruction = row["Instruction"]
        except Exception:
            instruction = None

        if (
            self.dosage_percent == "Y" or self.doubleSpinBox_total_dosage.value() > 0
        ):  # 2024-08-21 曙光
            if instruction in ["", None] and medicine_name not in ["自費粉藥"]:
                instruction = 1

        medicine_type = string_utils.xstr(row["MedicineType"])
        if "療程" in medicine_type:  # 2025-01-22 佳禾
            self.parent.tab_registration.comboBox_treat_type.setCurrentText("自購")
            instruction = number_utils.get_integer(dosage)
            dosage = 1

        prescript_row = [
            [prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"], "-1"],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptNo"],
                string_utils.xstr(self.ui.tableWidget_prescript.currentRow() + 1),
            ],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["CaseKey"],
                string_utils.xstr(self.case_key),
            ],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["CaseDate"],
                string_utils.xstr(self.case_date),
            ],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineSet"],
                string_utils.xstr(self.medicine_set),
            ],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"], medicine_type],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"], medicine_key],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["InsCode"],
                string_utils.xstr(row["InsCode"]),
            ],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["DosageMode"], dosage_mode],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["BackupMedicineName"],
                string_utils.xstr(row["MedicineName"]),
            ],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], medicine_name],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                string_utils.xstr(dosage),
            ],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"],
                string_utils.xstr(row["Unit"]),
            ],
            [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
                string_utils.xstr(instruction),
            ],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["Price"], price],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"], amount],
            [prescript_utils.SELF_PRESCRIPT_COL_NO["Info"], info],
        ]
        self.set_prescript(prescript_row)

        # 【新增：立即建立備份點】
        # 取得當前操作的行號
        current_row = self.ui.tableWidget_prescript.currentRow()
        if current_row != -1:
            for col_info in prescript_row:
                col_no = col_info[0]  # 取得欄位索引
                col_val = col_info[1]  # 取得寫入的值

                item = self.ui.tableWidget_prescript.item(current_row, col_no)
                if item:
                    # 將文字同步存入 UserRole，這樣 itemChanged 就不會抓到 None 了
                    item.setData(QtCore.Qt.UserRole, string_utils.xstr(col_val))

        return True

    def _get_ratio_price(self, medicine_type, price):
        if medicine_type not in ["單方", "複方"]:
            return price

        try:
            if self.ratio is not None:
                price = string_utils.xstr(number_utils.get_float(price) * self.ratio)
        except Exception:
            pass

        return price

    def _set_past_prescript_data(self, row_no, row):
        in_price = number_utils.get_float(row["InPrice"])
        if in_price is not None and in_price > 0:
            info = "$"
        else:
            info = ""

        medicine_type = string_utils.xstr(row["MedicineType"])
        medicine_name = string_utils.xstr(row["MedicineName"])
        medicine_key = string_utils.xstr(row["MedicineKey"])
        dosage = string_utils.get_formatted_str(self.dosage_mode, row["Dosage"])

        dosage_mode = self.dosage_mode
        if dosage_mode in [None, ""]:
            dosage_mode = "日劑量"

        try:
            price = string_utils.get_formatted_str(
                "單價", number_utils.get_float(row["Price"])
            )
        except Exception:
            price = None

        if number_utils.get_float(price) == 0 and self.refresh_price == "Y":
            try:
                price = string_utils.get_formatted_str(
                    "單價", number_utils.get_float(row["SalePrice"])
                )
            except Exception:
                price = string_utils.get_formatted_str("單價", None)

        if row["MedicineSet"] == 1:  # 拷貝健保才要放大倍率
            price = self._get_ratio_price(medicine_type, price)

        try:
            amount = number_utils.get_float(dosage) * number_utils.get_float(price)
            amount = string_utils.get_formatted_str("單價", amount)
        except Exception:
            amount = string_utils.get_formatted_str("單價", None)

        medicine_name = string_utils.xstr(row["MedicineName"])

        instruction = None

        try:  # 2024-08-21 曙光
            instruction = row["Instruction"]
        except Exception:
            instruction = None

        if (
            self.dosage_percent == "Y" or self.doubleSpinBox_total_dosage.value() > 0
        ):  # 2024-08-21 曙光
            if instruction in ["", None] and medicine_name not in ["自費粉藥"]:
                instruction = 1

        if (
            medicine_name
            not in ["自費藥費", "自費水藥", "自費粉藥", charge_utils.PROCESS_MEDICINE]
            and self.refresh_price == "Y"
        ):
            try:
                # sale_price = prescript_utils.get_medicine_field(self.database, medicine_key, 'SalePrice')
                sale_price = number_utils.get_float(row["SalePrice"])
                if sale_price > 0:
                    price = string_utils.get_formatted_str("單價", sale_price)
            except Exception:
                pass

        try:
            amount = number_utils.get_float(dosage) * number_utils.get_float(price)
            amount = string_utils.get_formatted_str("單價", amount)
        except Exception:
            amount = string_utils.get_formatted_str("單價", None)

        prescript_row = [
            "-1",
            string_utils.xstr(self.ui.tableWidget_prescript.currentRow() + 1),
            string_utils.xstr(self.case_key),
            string_utils.xstr(self.case_date),
            string_utils.xstr(self.medicine_set),
            medicine_type,
            medicine_key,
            string_utils.xstr(row["InsCode"]),
            dosage_mode,
            medicine_name,
            medicine_name,
            string_utils.xstr(dosage),
            string_utils.xstr(row["Unit"]),
            string_utils.xstr(instruction),
            price,
            amount,
            info,
        ]

        self.ui.tableWidget_prescript.blockSignals(True)
        for col_no in range(len(prescript_row)):
            self.ui.tableWidget_prescript.setItem(
                row_no, col_no, QtWidgets.QTableWidgetItem(prescript_row[col_no])
            )
        self.ui.tableWidget_prescript.blockSignals(False)

        self._adjust_prescript_column(row_no)

    def _set_valuation(self):
        valuation_price = self.system_settings.field("自費處方預設計價方式")
        if valuation_price != "單日計價":
            return

        self.ui.comboBox_valuation.setCurrentText(valuation_price)
        self.ui.comboBox_valuation.currentTextChanged.connect(self._set_price)

        self.append_null_medicine()

    def set_prescript(self, row, row_no=None, sort_prescript=True):
        if row_no is None:
            row_no = self.ui.tableWidget_prescript.currentRow()

        self.ui.tableWidget_prescript.blockSignals(True)
        for item in row:
            self.ui.tableWidget_prescript.setItem(
                row_no, item[0], QtWidgets.QTableWidgetItem(item[1])
            )
        self.ui.tableWidget_prescript.blockSignals(False)

        self._adjust_prescript_column(row_no)

        self.ui.tableWidget_prescript.resizeRowsToContents()

        try:
            medicine_type = string_utils.xstr(
                row[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]][1]
            )
            if (
                sort_prescript
                and self.medicine_sort == "處方類別"
                and medicine_type == "複方"
            ):
                self._sort_prescript_by_medicine_type(row, row_no, medicine_type)

        except Exception:
            pass

    def _sort_prescript_by_medicine_type(self, row, row_no, medicine_type):
        self.ui.tableWidget_prescript.blockSignals(True)
        exclude_medicine_type = "單方"

        if medicine_type == exclude_medicine_type:
            self.ui.tableWidget_prescript.blockSignals(False)
            return

        insert_index = None
        for i in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                i, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if item is None:
                continue

            current_medicine_type = item.text()
            if current_medicine_type == exclude_medicine_type:
                insert_index = i
                break

        if insert_index is None:
            self.ui.tableWidget_prescript.blockSignals(False)
            return

        if row_no <= insert_index:
            self.ui.tableWidget_prescript.blockSignals(False)
            return

        self.ui.tableWidget_prescript.removeRow(row_no)
        self.ui.tableWidget_prescript.insertRow(insert_index)
        self.set_prescript(row, insert_index, sort_prescript=False)
        self.ui.tableWidget_prescript.blockSignals(False)

    def _set_table_width(self):
        medicine_width = [
            70,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            250,
            50,
            50,
            60,
            90,
            90,
            10,
        ]
        self.table_widget_prescript.set_table_heading_width(medicine_width)

    def _read_prescript(self):
        self._read_dosage()

        try:
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        self._read_medicine()
        self.ui.tableWidget_prescript.blockSignals(False)

        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()

        if self.parent.call_from == "醫師看診作業":
            self.append_null_medicine()

        self._set_combo_box_valuation()

    def _set_combo_box_valuation(self):
        try:
            # self.ui.comboBox_valuation.disconnect()
            self.ui.comboBox_valuation.blockSignals(True)
        except Exception:
            pass

        if self._get_single_medicine_row_no() is not None:
            self.ui.comboBox_valuation.setCurrentText("單日計價")
        elif self._is_free_medicine():
            self.ui.comboBox_valuation.setCurrentText("不計價")
        else:
            self.ui.comboBox_valuation.setCurrentText("正常計價")

        # self.ui.comboBox_valuation.currentTextChanged.connect(self._set_price)
        self.ui.comboBox_valuation.blockSignals(False)

    def _read_dosage(self):
        sql = """
            SELECT * FROM dosage
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
        """
        row = self.database.select_record(sql, (self.case_key, self.medicine_set))
        if len(row) <= 0:
            return

        row = row[0]

        self.ui.comboBox_package.setCurrentText(string_utils.xstr(row["Packages"]))
        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(row["Days"]))
        self.ui.comboBox_instruction.setCurrentText(
            string_utils.xstr(row["Instruction"])
        )
        if string_utils.xstr(row["FreeInsMedicine"]) == "Y":
            self.ui.comboBox_valuation.setCurrentText("單複方不計價")

        self_total_fee = number_utils.get_integer(row["SelfTotalFee"])
        discount_rate = number_utils.get_integer(row["DiscountRate"])
        discount_fee = number_utils.get_integer(row["DiscountFee"])
        total_fee = number_utils.get_integer(row["TotalFee"])

        self.ui.spinBox_discount_rate.setValue(discount_rate)
        self.ui.lineEdit_discount_fee.setText(string_utils.xstr(discount_fee))
        self.ui.lineEdit_self_total_fee.setText(string_utils.xstr(self_total_fee))
        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))

        try:
            total_dosage = number_utils.get_float(row["TotalDosage"])
            if total_dosage > 0:
                self.ui.doubleSpinBox_total_dosage.blockSignals(True)
                self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)
                self.ui.doubleSpinBox_total_dosage.blockSignals(False)
        except Exception:
            pass

        if row["Remark"] == "本頁不印":
            self.ui.checkBox_print_receipt.setChecked(True)
            self._print_receipt_clicked(True, prompt_warning=False)

    def _read_medicine(self):
        sql = """
            SELECT prescript.*, medicine.InPrice FROM prescript
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                CaseKey = %s AND
                prescript.MedicineSet = %s
            ORDER BY PrescriptNo, PrescriptKey
        """
        self.table_widget_prescript.set_db_data(
            sql, self._set_medicine_data, params=(self.case_key, self.medicine_set)
        )

    def _set_medicine_data(self, row_no, row):
        medicine_key = row["MedicineKey"]
        medicine_name = string_utils.xstr(row["MedicineName"])
        dosage = string_utils.get_formatted_str(
            self.system_settings.field("劑量形式"), row["Dosage"]
        )
        price = string_utils.get_formatted_str("單價", row["Price"])
        amount = string_utils.get_formatted_str("單價", row["Amount"])
        in_price = number_utils.get_float(row["InPrice"])
        if in_price > 0:
            in_price_mark = "$"
        else:
            in_price_mark = ""

        prescript_row = [
            string_utils.xstr(row["PrescriptKey"]),
            string_utils.xstr(row["PrescriptNo"]),
            string_utils.xstr(row["CaseKey"]),
            string_utils.xstr(row["CaseDate"]),
            string_utils.xstr(row["MedicineSet"]),
            string_utils.xstr(row["MedicineType"]),
            string_utils.xstr(medicine_key),
            string_utils.xstr(row["InsCode"]),
            string_utils.xstr(row["DosageMode"]),
            medicine_name,
            medicine_name,
            dosage,
            string_utils.xstr(row["Unit"]),
            string_utils.xstr(row["Instruction"]),
            price,
            amount,
            in_price_mark,
        ]

        # for col_no in range(len(prescript_row)):
        #     self.ui.tableWidget_prescript.setItem(
        #         row_no, col_no, QtWidgets.QTableWidgetItem(prescript_row[col_no])
        #     )

        # self._adjust_prescript_column(row_no)
        # # database._add_prescript_info_button(row_no, medicine_key)

        # if medicine_name == "代煎水藥":
        #     self.ui.radioButton_process_medicine.setChecked(True)

        # ... 前面的程式碼保持不變 ...

        for col_no in range(len(prescript_row)):
            # 1. 建立 QTableWidgetItem
            item_text = prescript_row[col_no]
            new_item = QtWidgets.QTableWidgetItem(item_text)

            # 2. 關鍵：將初始值存入 UserRole，供日後還原使用
            new_item.setData(QtCore.Qt.UserRole, item_text)

            # 3. 放入 Table 中
            self.ui.tableWidget_prescript.setItem(row_no, col_no, new_item)

        self._adjust_prescript_column(row_no)
        if medicine_name == "代煎水藥":
            self.ui.radioButton_process_medicine.setChecked(True)

    def _add_prescript_info_button(self, row_no, medicine_key):
        description = prescript_utils.get_medicine_description(
            self.database, medicine_key
        )

        button = QtWidgets.QPushButton(self.ui.tableWidget_prescript)
        button.setIcon(QtGui.QIcon("./icons/gtk-info.svg"))
        button.setFlat(True)
        if description is None:
            button.setEnabled(False)

        button.clicked.connect(lambda: self._show_medicine_description(description))
        self.ui.tableWidget_prescript.setCellWidget(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Info"], button
        )

    def _show_medicine_description(self):
        medicine_key_item = self.ui.tableWidget_prescript.item(
            self.ui.tableWidget_prescript.currentRow(),
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"],
        )
        if medicine_key_item is None:
            return

        medicine_key = medicine_key_item.text()
        description = prescript_utils.get_medicine_description(
            self.database, medicine_key
        )
        if description is None:
            return

        dialog = dialog_utils.get_dialog_rich_text(
            self,
            self.database,
            self.system_settings,
            "rich_text",
            medicine_key,
            description,
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    # 增加處方資料
    def append_null_medicine(self, insert_row_no=None):
        row_count = self.table_widget_prescript.row_count()
        if row_count <= 0:
            self._insert_medicine_row(row_count)
            return

        if insert_row_no is not None:
            row_no = insert_row_no
            check_row_no = row_no
        else:
            row_no = row_count
            check_row_no = row_no - 1

        item = self.ui.tableWidget_prescript.item(
            check_row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if item is None or item.text().strip() == "":
            return

        self.ui.tableWidget_prescript.blockSignals(True)
        self._insert_medicine_row(row_no)
        self.ui.tableWidget_prescript.setCurrentCell(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"],
        )
        self.ui.tableWidget_prescript.blockSignals(False)

    # 插入處方資料
    def insert_medicine(self):
        current_row_no = self.ui.tableWidget_prescript.currentRow()
        self.append_null_medicine(insert_row_no=current_row_no)

    def _insert_medicine_row(self, index):
        self.ui.tableWidget_prescript.setFocus(True)
        self.ui.tableWidget_prescript.insertRow(index)
        self.ui.tableWidget_prescript.setCurrentCell(
            index, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )

        self.ui.tableWidget_prescript.setItem(
            index,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            QtWidgets.QTableWidgetItem(""),
        )
        self.ui.tableWidget_prescript.item(
            index, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        ).setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.ui.tableWidget_prescript.setFocus()

    # 刪除處方
    def remove_medicine(self):
        if self.parent.is_closed:
            return

        index = self.ui.tableWidget_prescript.currentRow()
        self.ui.tableWidget_prescript.removeRow(index)

        if self.ui.tableWidget_prescript.rowCount() <= 1:
            item = self.ui.tableWidget_prescript.item(
                0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if item is None or item.text() == "":
                self.ui.comboBox_package.setCurrentText(None)
                self.ui.comboBox_pres_days.setCurrentText(None)
                self.ui.comboBox_instruction.setCurrentText(None)
                self.ui.comboBox_valuation.setCurrentText("正常計價")
                self.append_null_medicine()

                if self.ui.spinBox_discount_rate.value() != 100:
                    self.ui.spinBox_discount_rate.setValue(100)
                    self.ui.lineEdit_discount_fee.setText("")

        self.parent.calculate_self_fees()
        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()
        self.ui.tableWidget_prescript.setFocus()

    def _clear_medicine(self, warning=False):
        if self.ui.tableWidget_prescript.rowCount() <= 0:
            return

        if warning:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("清除處方資料")
            msg_box.setText(
                "<font size='4' color='red'><b>確定清除全部的處方?</b></font>"
            )
            msg_box.setInformativeText("注意！處方清除後, 將無法回復!")
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            clear_medicine = msg_box.exec_()
            if clear_medicine:
                return

        self.ui.tableWidget_prescript.setRowCount(0)
        self.ui.comboBox_package.setCurrentText(None)
        self.ui.comboBox_pres_days.setCurrentText(None)
        self.ui.comboBox_instruction.setCurrentText(None)
        self.ui.comboBox_valuation.setCurrentText("正常計價")
        self.ui.toolButton_add_medicine.animateClick()

    # 刪除處方
    def _remove_sale_price(self):
        row_no = self.ui.tableWidget_prescript.currentRow()

        col_no = prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
        self.ui.tableWidget_prescript.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem("0.00")
        )
        self._adjust_prescript_column(row_no)

        col_no = prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
        self.ui.tableWidget_prescript.setItem(
            row_no, col_no, QtWidgets.QTableWidgetItem("0.00")
        )
        self._adjust_prescript_column(row_no)

        self.parent.calculate_self_fees()
        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()

    def _check_dosage_ok(self):
        # 建議將 col 索引先拿出來，避免在迴圈內反覆查找
        dosage_col = prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        unit_col = prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            dosage_item = self.ui.tableWidget_prescript.item(row_no, dosage_col)
            unit_item = self.ui.tableWidget_prescript.item(row_no, unit_col)

            # 只要其中一個是空的，可能代表這行還沒開始填，或是資料殘缺
            if not dosage_item or not unit_item:
                continue

            dosage_str = dosage_item.text().strip()
            unit_str = unit_item.text().strip()

            # 如果兩者皆空，視為跳過此行
            if not dosage_str and not unit_str:
                continue

            dosage = number_utils.get_float(dosage_str)

            # 核心邏輯：如果有單位但劑量為 0 或無效，則回傳不通過
            if dosage <= 0.0 and unit_str != "":
                self.ui.tableWidget_prescript.setCurrentCell(row_no, dosage_col)

                return False

        return True

    def save_prescript(self, check_prescript=True):
        if self.system_settings.field("自費開藥劑量必須大於0") == "Y":
            if not self._check_dosage_ok():
                return False

        self._check_herb_single_day_price()

        prescript_utils.check_extend_ins_drug(self.parent.tab_list[0], self)

        medicine_set = self.medicine_set
        if medicine_set >= 3:  # 有第三帖藥, 檢查前面的藥帖是否空白
            for i in range(medicine_set, 1, -1):
                medicine_set = i
                sql = """
                    SELECT MedicineSet FROM prescript
                    WHERE
                        CaseKey = %s AND
                        MedicineSet = %s
                    LIMIT 1
                """
                rows = self.database.select_record(
                    sql, (self.case_key, medicine_set - 1)
                )
                if len(rows) > 0:
                    break

        if self.system_settings.field("調整庫存量") == "即時調整":
            # ★ 先還原舊處方的庫存，再存檔，再扣新庫存
            stock_utils.restore_self_prescript(
                self.database, self.case_key, medicine_set
            )

        self._save_dosage(medicine_set)
        self._save_medicine(medicine_set)

        if self.system_settings.field("調整庫存量") == "即時調整":
            stock_utils.adjust_self_prescript(
                self.database, self.case_key, medicine_set
            )

        return True

    def _save_dosage(self, medicine_set):
        sql = """
            DELETE FROM dosage
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
        """
        self.database.exec_sql(sql, (self.case_key, medicine_set))

        fields = [
            "CaseKey",
            "MedicineSet",
            "Packages",
            "Days",
            "Instruction",
            "TotalDosage",
            "SelfTotalFee",
            "DiscountRate",
            "DiscountFee",
            "TotalFee",
            "FreeInsMedicine",
            "Remark",
        ]
        # self_total_fee = self._get_self_total_fee()
        self_total_fee = self._compute_self_total_fee_without_discount()
        total_fee = self._get_total_fee()
        if self.ui.comboBox_valuation.currentText() == "單複方不計價":
            free_ins_medicine = "Y"
        else:
            free_ins_medicine = None

        total_dosage = self.ui.doubleSpinBox_total_dosage.value()
        if total_dosage == 0.0:
            total_dosage = None

        if self.ui.checkBox_print_receipt.isChecked():
            remark = "本頁不印"
        else:
            remark = None

        data = [
            string_utils.xstr(self.case_key),
            string_utils.xstr(medicine_set),
            self.ui.comboBox_package.currentText(),
            self.ui.comboBox_pres_days.currentText(),
            self.ui.comboBox_instruction.currentText(),
            total_dosage,
            self_total_fee,
            self.ui.spinBox_discount_rate.value(),
            self.ui.lineEdit_discount_fee.text(),
            total_fee,
            free_ins_medicine,
            remark,
        ]

        self.database.insert_record("dosage", fields, data)

    def _save_medicine(self, medicine_set):
        prescript_data_set = []
        for i in range(self.ui.tableWidget_prescript.rowCount()):
            prescript_row = []
            for j in range(self.ui.tableWidget_prescript.columnCount()):
                try:
                    prescript_row.append(
                        self.ui.tableWidget_prescript.item(i, j).text().strip()
                    )
                except AttributeError:
                    prescript_row.append(None)

            prescript_data_set.append(prescript_row)

        self.delete_not_exists_prescript(prescript_data_set)

        prescript_no = 0  # 重編 PrescriptNo
        for items in prescript_data_set:
            if items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"]] is None:
                continue

            if items[prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]] == "":
                items[prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]] = None

            prescript_no += 1
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptNo"]] = str(
                prescript_no
            )

            if items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"]] == "-1":
                self.insert_prescript(items, medicine_set)
            else:
                self.update_prescript(items, medicine_set)

    # 刪除不在tableWidget內的處方
    def delete_not_exists_prescript(self, prescript_data_set):
        prescript_key_list = []
        for items in prescript_data_set:
            prescript_key_list.append(
                items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptKey"]]
            )

        sql = """
            SELECT * FROM prescript
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
        """
        rows = self.database.select_record(sql, (self.case_key, self.medicine_set))
        for row in rows:
            prescript_key = row["PrescriptKey"]
            if str(prescript_key) not in prescript_key_list:
                self.database.exec_sql(
                    "DELETE FROM prescript WHERE PrescriptKey = %s", (prescript_key,)
                )

    # 插入處方資料至資料庫內
    def insert_prescript(self, items, medicine_set=None):
        if medicine_set is None:
            medicine_set = items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineSet"]]

        fields = [
            "PrescriptNo",
            "CaseKey",
            "CaseDate",
            "MedicineSet",
            "MedicineType",
            "MedicineKey",
            "InsCode",
            "DosageMode",
            "MedicineName",
            "Dosage",
            "Unit",
            "Instruction",
            "Price",
            "Amount",
        ]

        data = [
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptNo"]],
            self.case_key,
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["CaseDate"]],
            medicine_set,
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["InsCode"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["DosageMode"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]],
        ]

        self.database.insert_record("prescript", fields, data)

    # 更新處方資料至資料庫內
    def update_prescript(self, items, medicine_set=None):
        if medicine_set is None:
            medicine_set = items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineSet"]]

        if items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]] == "":
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]] = None

        fields = [
            "PrescriptNo",
            "CaseKey",
            "CaseDate",
            "MedicineSet",
            "MedicineType",
            "MedicineKey",
            "InsCode",
            "DosageMode",
            "MedicineName",
            "Dosage",
            "Unit",
            "Instruction",
            "Price",
            "Amount",
        ]
        data = [
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["PrescriptNo"]],
            self.case_key,
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["CaseDate"]],
            medicine_set,
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["InsCode"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["DosageMode"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]],
            items[prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]],
        ]

        self.database.update_record("prescript", fields, "PrescriptKey", items[0], data)

    def copy_prescript_from_json(
        self, backup_records_key, json_medical_record, json_rows, medicine_set
    ):
        try:
            # self.ui.tableWidget_prescript.itemChanged.disconnect()
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)

        pres_days = case_utils.get_pres_days_from_json(
            self.database, backup_records_key, medicine_set
        )
        packages = case_utils.get_packages_from_json(
            self.database, backup_records_key, medicine_set
        )
        instruction = case_utils.get_instruction_from_json(
            self.database, backup_records_key, medicine_set
        )
        discount_rate = case_utils.get_discount_rate_from_json(
            self.database, backup_records_key, medicine_set
        )

        for row_no, row in enumerate(json_rows):
            if row["MedicineName"] is None:
                continue

            if row["MedicineSet"] != medicine_set:
                continue

            self.append_null_medicine()
            self.append_prescript(row, row["Dosage"])

            self._set_dosage_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
            )
            self._set_price_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
            )
            self._set_price_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(string_utils.xstr(instruction))
        self.ui.spinBox_discount_rate.setValue(discount_rate)

        self.ui.tableWidget_prescript.resizeRowsToContents()

        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.blockSignals(False)
        self.parent.calculate_self_fees()

    # 拷貝過去病歷的處方
    def copy_past_prescript(self, case_key, medicine_set=None):
        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)
        if medicine_set is None:
            medicine_set = self.medicine_set

        pres_days = case_utils.get_pres_days(self.database, case_key, medicine_set)
        packages = case_utils.get_packages(self.database, case_key, medicine_set)
        instruction = case_utils.get_instruction(self.database, case_key, medicine_set)
        discount_rate = case_utils.get_discount_rate(
            self.database, case_key, medicine_set
        )
        discount_fee = case_utils.get_discount_fee(
            self.database, case_key, medicine_set
        )

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(instruction)
        self.ui.spinBox_discount_rate.setValue(discount_rate)
        self.ui.lineEdit_discount_fee.setText(string_utils.xstr(discount_fee))

        medicine_type_script = ""
        if medicine_set == 1:
            medicine_type_script = ' AND prescript.MedicineType IN ("單方", "複方") '

        self.ui.tableWidget_prescript.blockSignals(True)
        sql = f"""
            SELECT prescript.*, medicine.InPrice, medicine.SalePrice FROM prescript
                LEFT JOIN medicine ON prescript.MedicineKey = medicine.MedicineKey
            WHERE
                CaseKey = %s AND
                prescript.MedicineSet = %s
                {medicine_type_script}
            ORDER BY PrescriptNo, PrescriptKey
        """
        self.table_widget_prescript.set_db_data(
            sql, self._set_past_prescript_data, params=(case_key, medicine_set)
        )

        self.ui.tableWidget_prescript.blockSignals(False)
        self.parent.calculate_self_fees()

    # 藥日變更重新批價
    def pres_days_changed(self):
        pres_days = self.ui.comboBox_pres_days.currentText()
        currect_pres_days = ""
        for alpha in pres_days:
            if not alpha.isdigit():
                self.ui.comboBox_pres_days.setCurrentText(currect_pres_days)
                return

            currect_pres_days += alpha

        self._calculate_self_total_fee()
        self.parent.calculate_self_fees()
        self.ui.comboBox_pres_days.setFocus()

    # 包變更
    def package_changed(self):
        package = self.ui.comboBox_package.currentText()
        currect_package = ""
        for alpha in package:
            if not alpha.isdigit():
                self.ui.comboBox_package.setCurrentText(currect_package)
                return

            currect_package += alpha

        self._calculate_self_total_fee()
        self.parent.calculate_self_fees()
        self.ui.comboBox_package.setFocus()

    def _prescript_item_selection_changed(self):
        self.ui.toolButton_remove_medicine.setEnabled(True)
        self.ui.toolButton_dictionary.setEnabled(True)
        self.ui.toolButton_dosage.setEnabled(True)
        self.ui.toolButton_medicine_info.setEnabled(True)

        if self.user_name == "超級使用者":
            enabled = True
        elif (
            self.call_from != "醫師看診作業"
            and personnel_utils.get_permission(
                self.database, "病歷資料", "病歷修正", self.user_name
            )
            != "Y"
        ):
            enabled = False
        elif self.ui.tableWidget_prescript.rowCount() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.toolButton_remove_medicine.setEnabled(enabled)
        self.ui.toolButton_dictionary.setEnabled(enabled)
        self.ui.toolButton_dosage.setEnabled(enabled)
        self.ui.toolButton_set_prescript_remark.setEnabled(enabled)
        self.ui.toolButton_set_medicine_name.setEnabled(enabled)

        medicine_key_item = self.ui.tableWidget_prescript.item(
            self.ui.tableWidget_prescript.currentRow(),
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"],
        )
        if medicine_key_item is None:
            return

        description = prescript_utils.get_medicine_description(
            self.database, medicine_key_item.text()
        )
        if description is None:
            self.ui.toolButton_medicine_info.setEnabled(False)

        medicine_type_item = self.ui.tableWidget_prescript.item(
            self.ui.tableWidget_prescript.currentRow(),
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"],
        )
        if medicine_type_item is not None and medicine_type_item.text() in [
            "",
            "備註",
            "自費另包",
        ]:
            self.ui.toolButton_set_medicine_name.setEnabled(False)

    def set_tab_icon(self):
        if (
            self.ui.tableWidget_prescript.rowCount() >= 2
            or self.ui.tableWidget_prescript.rowCount() == 1
            and self.ui.tableWidget_prescript.item(
                0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            is not None
        ):
            self.parent.tabWidget_prescript.setTabIcon(
                self.medicine_set - 1, ui_utils.ICON_STAR
            )
        else:
            self.parent.tabWidget_prescript.setTabIcon(
                self.medicine_set - 1, QtGui.QIcon()
            )

    # def _prescript_item_changed(self, item):
    #     self.set_tab_icon()

    #     if item is None:
    #         return

    #     col_no = item.column()
    #     row_no = item.row()

    #     if col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]:
    #         prescript_utils.check_extend_ins_drug(self.parent.tab_list[0], self)
    #     elif col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]:
    #         self._set_dosage_percent()

    #     if col_no not in [
    #         prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
    #         prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
    #         prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
    #     ]:
    #         return

    #     self._calculate_total_price(row_no, col_no, item)
    #     self._adjust_prescript_column_align(row_no)

    #     # self._calculate_single_price_medicine()  # 計算是否有單日計價

    #     self.ui.tableWidget_prescript.blockSignals(True)
    #     self.parent.calculate_self_fees()
    #     self._calculate_total_dosage()
    #     self._calculate_total_costs()
    #     self._calculate_self_total_fee()
    #     self.ui.tableWidget_prescript.blockSignals(False)

    def _prescript_item_changed(self, item):
        if item is None:
            return

        col_no = item.column()
        row_no = item.row()

        # 取得目前文字與舊的備份值
        current_text = item.text().strip()
        old_value = item.data(QtCore.Qt.UserRole)

        if current_text == old_value:
            return

        # 這裡以藥名、劑量、單價為例
        target_cols = [
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"],
            prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
        ]

        if col_no in target_cols:
            if not current_text:
                # 【關鍵步驟 1】：發現空白，強制還原成「舊的有效值」
                self.ui.tableWidget_prescript.blockSignals(True)
                item.setText(old_value if old_value is not None else "")
                self.ui.tableWidget_prescript.blockSignals(False)

                # 【關鍵步驟 2】：直接結束！不要執行後面的「更新 UserRole」
                return
            else:
                # 【關鍵步驟 3】：只有在確定有輸入內容時，才把新內容存成「下次的備份值」
                item.setData(QtCore.Qt.UserRole, current_text)

        # --- 以下為原本的邏輯 ---

        self.set_tab_icon()

        if col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]:
            prescript_utils.check_extend_ins_drug(self.parent.tab_list[0], self)
        elif col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]:
            self._set_dosage_percent()

        # 判斷是否需要執行計算邏輯
        if col_no not in [
            prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
            prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
        ]:
            return

        self._calculate_total_price(row_no, col_no, item)
        self._adjust_prescript_column_align(row_no)

        self.ui.tableWidget_prescript.blockSignals(True)
        self.parent.calculate_self_fees()
        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()
        self.ui.tableWidget_prescript.blockSignals(False)

    def _check_ins_drug_single_day_price_changed(self):
        row_no = 0
        item = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if item is None:
            return

        medicine_name = item.text()
        if medicine_name != "自費粉藥":
            return

        price_item = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
        )
        if price_item is None:
            return

        maximum_price = charge_utils.get_ins_drug_single_day_maximum_price(
            self.database
        )
        if maximum_price <= 0:
            return

        price = number_utils.get_integer(price_item.text())
        if price <= maximum_price:
            return

        try:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "單日計價超過上限",
                f"""
                    <font color="red">
                        <h3>自費粉藥單日計價超過上限{maximum_price}元, 系統將把單日計價金額降為{maximum_price}元</h3>
                    </font>
                """,
                "請勿超過計價上限",
            )
            self.ui.tableWidget_prescript.setItem(
                row_no,
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                QtWidgets.QTableWidgetItem(
                    string_utils.get_formatted_str("單價", maximum_price)
                ),
            )
        except Exception:
            pass

    def _get_ins_drug_single_day_price(self):
        ins_drug_single_day_price = 0

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if medicine_type is not None and medicine_type.text() not in [
                "單方",
                "複方",
            ]:  # 只統計科中
                continue

            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            try:
                amount = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            ins_drug_single_day_price += amount

        return ins_drug_single_day_price

    # call by medical_record.check_self_dosage
    def check_ins_drug_single_day_price(self):
        maximum_price = charge_utils.get_ins_drug_single_day_maximum_price(
            self.database
        )
        if maximum_price <= 0:
            return True

        total_ins_drug_fee = 0

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if medicine_type is not None and medicine_type.text() not in [
                "單方",
                "複方",
            ]:  # 只統計科中
                continue

            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            try:
                amount = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            total_ins_drug_fee += amount

        if total_ins_drug_fee == 0:  # 未開水藥不檢查
            return True

        if total_ins_drug_fee > maximum_price:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "自費科中超過收費標準",
                f"""
                    <font color="red">
                        <h3>自費科中計價不得超過每日藥費最高{maximum_price}元, 請重新調整處方內容</h3>
                    </font>
                """,
                "請重新調整處方內容",
            )
            return False
        else:
            return True

    def _check_herb_single_day_price(self):
        minimum_price = charge_utils.get_herb_single_day_minimum_price(self.database)
        if minimum_price <= 0:
            return

        total_herb_fee = 0

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if (
                medicine_type is not None and medicine_type.text() != "水藥"
            ):  # 只統計水藥費
                continue

            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if (
                medicine_name is not None and medicine_name.text() == "代煎水藥"
            ):  # 代煎水藥不計算
                continue

            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            try:
                amount = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            total_herb_fee += amount

        if total_herb_fee == 0:  # 未開水藥不檢查
            return

        if total_herb_fee < minimum_price:
            self.ui.comboBox_valuation.setCurrentText("單日計價")
            system_utils.show_message_box(
                QMessageBox.Critical,
                "自費水藥未達最低收費標準",
                f"""
                    <font color="red">
                        <h3>自費水藥計價未達最低收費標準{minimum_price}元, 系統將把單日計價金額調整為{minimum_price}元</h3>
                    </font>
                """,
                "系統將自動重新批價",
            )

    def _check_extend_ins_drug(self):
        ins_tab = self.parent.tab_list[0]
        if ins_tab is None:
            return

        extend_ins_drug = prescript_utils.is_prescript_exists(
            self.ui.tableWidget_prescript,
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"],
            "健保合包",
        )

        if not extend_ins_drug:
            return

        packages = ins_tab.comboBox_package.currentText()
        pres_days = ins_tab.comboBox_pres_days.currentText()
        instruction = ins_tab.comboBox_instruction.currentText()

        if self.ui.comboBox_package.currentText() != packages:
            self.ui.comboBox_package.setCurrentText(packages)
        if self.ui.comboBox_pres_days.currentText() != pres_days:
            self.ui.comboBox_pres_days.setCurrentText(pres_days)
        if self.ui.comboBox_instruction.currentText() != instruction:
            self.ui.comboBox_instruction.setCurrentText(instruction)

    # 拷貝過去病歷的處方
    def copy_host_prescript(self, database, case_key, medicine_set=None):
        try:
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        self.ui.tableWidget_prescript.clearContents()
        self.ui.tableWidget_prescript.setRowCount(0)
        if medicine_set is None:
            medicine_set = self.medicine_set

        pres_days = case_utils.get_host_pres_days(database, case_key, medicine_set)
        packages = case_utils.get_host_packages(database, case_key, medicine_set)
        instruction = case_utils.get_host_instruction(database, case_key, medicine_set)

        medicine_type_script = ""
        if medicine_set == 1:
            medicine_type_script = (
                ' AND MedicineType IN ("單方", "複方") '  # 拷貝健保至自費, 只讀取健保藥
            )

        sql = f"""
            SELECT * FROM prescript
            WHERE
                CaseKey = %s AND
                MedicineSet = %s
                {medicine_type_script}
            ORDER BY PrescriptKey
        """
        rows = database.select_record(sql, (case_key, medicine_set))

        for row_no, row in enumerate(rows):
            if row["MedicineName"] is None:
                continue

            self.append_null_medicine()
            self.append_prescript(row, row["Dosage"])
            self._set_dosage_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
            )
            self._set_price_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
            )
            self._set_price_format(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )

        self.ui.comboBox_pres_days.setCurrentText(string_utils.xstr(pres_days))
        self.ui.comboBox_package.setCurrentText(string_utils.xstr(packages))
        self.ui.comboBox_instruction.setCurrentText(instruction)

        self.ui.tableWidget_prescript.resizeRowsToContents()

        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.blockSignals(False)
        self.parent.calculate_self_fees()

    # def _calculate_total_price(self, row_no, col_no, item):
    #     dosage = self.ui.tableWidget_prescript.item(
    #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
    #     )
    #     sale_price = self.ui.tableWidget_prescript.item(
    #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
    #     )

    #     if col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]:
    #         dosage = item
    #     elif col_no == prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]:
    #         sale_price = item

    #     if dosage is None:
    #         dosage = 0
    #     else:
    #         dosage = dosage.text()

    #     if sale_price is None:
    #         sale_price = 0
    #     else:
    #         sale_price = sale_price.text()

    #     try:
    #         sale_price = number_utils.get_float(sale_price)
    #     except ValueError:
    #         sale_price = 0
    #     try:
    #         dosage = number_utils.get_float(dosage)
    #     except ValueError:
    #         dosage = 0

    #     subtotal = dosage * sale_price
    #     self.ui.tableWidget_prescript.setItem(
    #         row_no,
    #         prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
    #         QtWidgets.QTableWidgetItem(
    #             string_utils.get_formatted_str("單價", subtotal)
    #         ),
    #     )
    def _calculate_total_price(self, row_no, col_no, item):
        # 1. 先安全地取得表格中目前的「文字」
        dosage_item = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        )
        sale_price_item = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
        )

        # 加上 try-except 或用 python 的內建機制，確保 C++ 物件萬一真的不見時不會崩潰
        try:
            dosage_str = dosage_item.text() if dosage_item is not None else "0"
        except RuntimeError:
            # 萬一 dosage_item 在底層已經被 delete，就給它預設值
            dosage_str = "0"

        try:
            sale_price_str = (
                sale_price_item.text() if sale_price_item is not None else "0"
            )
        except RuntimeError:
            sale_price_str = "0"

        # 2. 【已移除】原本在這裡用 item.text() 覆蓋的邏輯拿掉
        # 因為上面 dosage_item / sale_price_item 拿到的就是最新畫面的數值了。

        # 3. 轉成數字
        try:
            dosage = number_utils.get_float(dosage_str)
        except (ValueError, TypeError):
            dosage = 0.0

        try:
            sale_price = number_utils.get_float(sale_price_str)
        except (ValueError, TypeError):
            sale_price = 0.0

        # 4. 計算並寫回表格
        subtotal = dosage * sale_price

        self.ui.tableWidget_prescript.blockSignals(True)

        # 建立新的 Item 寫入金額
        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            QtWidgets.QTableWidgetItem(
                string_utils.get_formatted_str("單價", subtotal)
            ),
        )

        self.ui.tableWidget_prescript.blockSignals(False)

    # 調整欄位對齊
    def _adjust_prescript_column(self, row_no):
        self._adjust_prescript_column_align(row_no)

        medicine_name = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if medicine_name is not None and (
            "自費粉藥" in medicine_name.text() or "自費水藥" in medicine_name.text()
        ):
            pass
        else:
            self._set_prescript_read_only_column(row_no)

    # 調整欄位對齊
    def _adjust_prescript_column_align(self, row_no):
        for col_no in range(self.ui.tableWidget_prescript.columnCount()):
            item = self.ui.tableWidget_prescript.item(row_no, col_no)
            if item is None:
                continue

            if col_no in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            ]:
                item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            elif col_no in [
                prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"],
                prescript_utils.SELF_PRESCRIPT_COL_NO["Info"],
            ]:
                item.setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    # 調整欄位對齊
    def _set_prescript_read_only_column(self, row_no):
        self.read_only_columns.sort()
        for col_no in self.read_only_columns:
            item = self.ui.tableWidget_prescript.item(row_no, col_no)
            if item is None:
                continue

            item.setFlags(QtCore.Qt.ItemIsEnabled)

    def _get_total_dosage(self, default_medicine_type=None):
        total_dosage = 0.00
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name is not None:
                medicine_name = medicine_name.text()
                if medicine_name in ["優待", "自費水藥", "自費粉藥", "自費藥費"]:
                    continue

                if "代煎" in medicine_name:
                    continue

            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )

            if medicine_type is not None:
                if medicine_type.text() == "成方表頭":
                    continue

                if (
                    default_medicine_type is not None
                    and medicine_type.text() != default_medicine_type
                ):
                    continue

            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
            )
            if item is None:
                continue

            try:
                dosage = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            total_dosage += dosage

        return total_dosage

    def _calculate_total_dosage(self):
        total_dosage = self._get_total_dosage()
        self.ui.label_total_dosage.setText(f"總量: {total_dosage:.1f}")

    def _calculate_total_costs(self):
        total_costs = 0.00

        # 第一輪: 收集 medicine_key 與 dosage
        dosage_list = []
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            dosage_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
            )
            if dosage_item is None:
                continue

            medicine_key_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]
            )
            if medicine_key_item is None:
                continue

            medicine_key = medicine_key_item.text()
            if medicine_key == "":
                continue

            dosage_list.append(
                (medicine_key, number_utils.get_float(dosage_item.text()))
            )

        if len(dosage_list) <= 0:
            self.ui.label_total_costs.setText(f"({total_costs:.1f})")
            return

        # 一次查回所有進價
        medicine_keys = list({medicine_key for medicine_key, _ in dosage_list})
        sql = f"""
            SELECT MedicineKey, InPrice FROM medicine
            WHERE
                MedicineKey IN ({db_utils.in_placeholders(medicine_keys)})
        """
        rows = self.database.select_record(sql, tuple(medicine_keys))
        in_price_dict = {
            string_utils.xstr(row["MedicineKey"]): number_utils.get_float(
                row["InPrice"]
            )
            for row in rows
        }

        for medicine_key, dosage in dosage_list:
            total_costs += dosage * in_price_dict.get(medicine_key, 0)

        self.ui.label_total_costs.setText(f"({total_costs:.1f})")

    def _compute_self_total_fee(self):
        self_total_fee = 0
        dosage_mode = self.dosage_mode
        by_package = self.system_settings.field("自費處方次劑量")

        # if self.system_settings.field('手動批價') == 'Y':
        #     return self_total_fee

        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if pres_days <= 0:
            pres_days = 1

        packages = number_utils.get_integer(self.ui.comboBox_package.currentText())
        if packages <= 0:
            packages = 1

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            try:
                amount = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            single_item = False
            this_pres_days = pres_days
            instruction_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"]
            )

            try:
                treat_type = (
                    self.parent.tab_registration.ui.comboBox_treat_type.currentText()
                )
            except Exception:
                treat_type = None

            if self.dosage_percent == "Y":  # 劑量比例法不要轉換
                pass
            elif (
                treat_type != "自購"
                and instruction_item is not None
                and instruction_item.text() != ""
            ):  # 代煎費次數
                if self.no_instruction_pres_days == "Y":  # 不要把服法改成藥日
                    pass
                else:
                    try:
                        this_pres_days = number_utils.get_integer(
                            instruction_item.text()
                        )
                        single_item = True
                    except Exception:
                        single_item = False

                    if this_pres_days <= 0:
                        this_pres_days = pres_days

            if this_pres_days <= 0:
                this_pres_days = 1

            medicine_name_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if (
                self.clinic_name == "專嘉中醫診所"
                and medicine_name_item is not None
                and medicine_name_item.text() == "自費粉藥"
            ):
                this_pres_days = 1

            subtotal = charge_utils.get_subtotal_fee(amount, this_pres_days)

            unit_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]
            )
            if unit_item is not None:
                unit = unit_item.text()
            else:
                unit = None

            if not single_item:
                if dosage_mode == "次劑量" or (
                    by_package == "Y" and unit in ["顆", "錠"]
                ):  # 2025-02-27 耀康
                    subtotal *= packages

            self_total_fee += subtotal

        self_total_fee = number_utils.round_up(self_total_fee)

        return self_total_fee

    def _compute_self_total_fee_without_discount(self):
        self_total_fee = 0
        dosage_mode = self.dosage_mode
        by_package = self.system_settings.field("自費處方次劑量")

        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if pres_days <= 0:
            pres_days = 1

        packages = number_utils.get_integer(self.ui.comboBox_package.currentText())
        if packages <= 0:
            packages = 1

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            medicine_key_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]
            )
            if medicine_key_item is not None:
                medicine_key = medicine_key_item.text().strip()
                if medicine_key != "":
                    if (
                        prescript_utils.get_no_discount_status(
                            self.database, medicine_key
                        )
                        == "Y"
                    ):
                        continue

            medicine_name_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name_item is not None:
                medicine_name = medicine_name_item.text()
                if self.system_settings.field(
                    "院所名稱"
                ) == "專嘉中醫診所" and medicine_name in ["自費粉藥", "自費水藥"]:
                    pres_days = 1
            try:
                amount = number_utils.get_float(item.text())
            except ValueError:
                item.setText(None)
                continue

            subtotal = charge_utils.get_subtotal_fee(amount, pres_days)
            if dosage_mode == "次劑量" or by_package == "Y":
                subtotal *= packages

            self_total_fee += subtotal

        self_total_fee = number_utils.round_up(self_total_fee)

        return self_total_fee

    def _calculate_self_total_fee(self):
        self_total_fee = self._compute_self_total_fee()
        if self.system_settings.field("自費折扣方式") == "個別折扣":
            self._calculate_discount(set_focus=False)

        discount_fee = number_utils.get_integer(self.ui.lineEdit_discount_fee.text())

        total_fee = self_total_fee - discount_fee

        self.ui.lineEdit_self_total_fee.setText(string_utils.xstr(self_total_fee))
        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))
        self.parent.calculate_self_fees()

    def _get_self_total_fee(self):
        return number_utils.get_integer(self.ui.lineEdit_self_total_fee.text())

    def _get_total_fee(self):
        return number_utils.get_integer(self.ui.lineEdit_total_fee.text())

    def open_medicine_dictionary(self):
        self.parent.open_dictionary(self.medicine_set, "自費處方")

    def _open_project(self):
        dialog = dialog_utils.get_dialog_project(
            self,
            self.database,
            self.system_settings,
            self.ui.tableWidget_prescript,
            self.medicine_set,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _open_dict_examination(self):
        self.parent.open_dict_examination(self.medicine_set)

    def _show_costs(self):
        pres_days = number_utils.get_integer(self.ui.comboBox_pres_days.currentText())
        if pres_days <= 0:
            pres_days = 1

        html = prescript_utils.get_costs_html(
            self.database,
            self.ui.tableWidget_prescript,
            pres_days,
            prescript_utils.SELF_PRESCRIPT_COL_NO,
        )
        dialog = dialog_utils.get_dialog_rich_text(
            self, self.database, self.system_settings, "html", None, html
        )
        dialog.exec_()
        dialog.close_all()
        dialog.deleteLater()

    def _prescript_cell_clicked(self):
        if self.system_settings.field("不要自動切換輸入法") == "Y":
            pass
        else:
            system_utils.set_keyboard_layout("英文")

    def _calculate_discount(self, set_focus=True):
        # if self.ui.spinBox_discount_rate.value() == 100 and \  # void 2023-05-23 龍潭懷恩堂
        #         number_utils.get_integer(self.ui.lineEdit_discount_fee.text()) > 0:  # 自訂折扣，不要重新計算
        #     return

        if self.ui.spinBox_discount_rate.value() < 0:
            return

        if (
            not self.warned
            and not self.parent.is_doctor_done()
            and self.ui.spinBox_discount_rate.value() == 0
        ):
            self.warned = True
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("折扣為0%")
            msg_box.setText(f"""
                <font size='4' color='red'><b>自費處方{self.medicine_set - 1}的折扣為0%，這份處方的金額將會變成完全免費?</b></font>
            """)
            msg_box.setInformativeText("注意！這份處方將完全免費!")
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
            accept = msg_box.exec_()
            if not accept:
                self.ui.spinBox_discount_rate.setValue(100)
                return

        # self_total_fee = self._get_self_total_fee()
        self_total_fee = self._compute_self_total_fee_without_discount()
        discount_fee = charge_utils.get_discount_fee(
            self.system_settings, self_total_fee, self.ui.spinBox_discount_rate.value()
        )

        if discount_fee is None:
            return

        self.ui.lineEdit_discount_fee.setText(string_utils.xstr(discount_fee))
        if set_focus:
            self.ui.spinBox_discount_rate.setFocus()

    # 拷貝自費處方至健保處方
    def _copy_to_previous_prescript(self):
        # dest_tab_index = self.medicine_set - 2
        dest_tab_index = 0  # 健保處方應該是0 2026-02-24 雲濤
        tab_prescript = self.parent.tab_list[dest_tab_index]

        if tab_prescript is None:
            return

        total_dosage = self.ui.doubleSpinBox_total_dosage.value()
        packages = self.ui.comboBox_package.currentText()
        pres_days = self.ui.comboBox_pres_days.currentText()
        instruction = self.ui.comboBox_instruction.currentText()
        tab_prescript.copy_from_self_prescript(
            self.ui.tableWidget_prescript,
            packages,
            pres_days,
            instruction,
            total_dosage,
        )
        self.parent.tabWidget_prescript.setCurrentIndex(dest_tab_index)
        tab_prescript.append_null_medicine()

    # 拷貝自費處方至新增的自費處方
    def _copy_to_next_prescript(self):
        dest_tab_index = self.medicine_set
        if self.parent.tab_list[dest_tab_index] is None:
            tab_prescript = self.parent.add_prescript_tab()
        else:
            tab_prescript = self.parent.tab_list[dest_tab_index]

        total_dosage = self.ui.doubleSpinBox_total_dosage.value()
        packages = self.ui.comboBox_package.currentText()
        pres_days = self.ui.comboBox_pres_days.currentText()
        instruction = self.ui.comboBox_instruction.currentText()
        tab_prescript.copy_from_self_prescript(
            self.ui.tableWidget_prescript,
            packages,
            pres_days,
            instruction,
            total_dosage,
        )
        self.parent.tabWidget_prescript.setCurrentIndex(dest_tab_index)
        tab_prescript.append_null_medicine()

    def copy_from_ins_prescript(
        self,
        table_widget_ins_prescript,
        comboBox_package,
        comboBox_pres_days,
        comboBox_instruction,
        doubleSpinBox_total_dosage,
    ):
        ratio = charge_utils.get_ratio(self.database)
        prescript_utils.duplicate_ins_table_widget(
            self.database,
            table_widget_ins_prescript,
            self.ui.tableWidget_prescript,
            ratio=ratio,
        )

        self.ui.doubleSpinBox_total_dosage.setValue(
            doubleSpinBox_total_dosage.value()
        )  # 2024-08-21 曙光

        self.ui.comboBox_package.setCurrentText(comboBox_package.currentText())
        self.ui.comboBox_pres_days.setCurrentText(comboBox_pres_days.currentText())
        self.ui.comboBox_instruction.setCurrentText(comboBox_instruction.currentText())

        self.parent.calculate_self_fees()
        self._calculate_total_dosage()
        self._calculate_total_costs()

        self._set_valuation()  # 2024-08-21 曙光

        if self.dosage_percent == "Y" or self.ui.doubleSpinBox_total_dosage.value() > 0:
            self._set_dosage_again(
                "健保",
                table_widget_ins_prescript,
                prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"],
            )

    def _set_dosage_again(self, ins_type, table_widget_from_prescript, col_no):
        medicine_name_item = self.ui.tableWidget_prescript.item(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if medicine_name_item is not None and medicine_name_item.text() in [
            "自費粉藥",
            "自費水藥",
        ]:
            single_price = True
        else:
            single_price = False

        try:
            # self.ui.tableWidget_prescript.itemChanged.disconnect()
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        for row_no in range(table_widget_from_prescript.rowCount()):
            dosage_item = table_widget_from_prescript.item(row_no, col_no)
            if dosage_item is None:
                continue

            current_row_no = row_no
            if ins_type == "健保" and single_price:
                current_row_no += 1

            item = QtWidgets.QTableWidgetItem()
            item.setData(QtCore.Qt.EditRole, dosage_item.text())
            item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.ui.tableWidget_prescript.setItem(
                current_row_no,
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
                item,
            )

        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.blockSignals(False)
        self._calculate_total_dosage()

    def table_to_list(self, table):
        rows = table.rowCount()
        cols = table.columnCount()
        data = []
        for r in range(rows):
            row_data = []
            for c in range(cols):
                it = table.item(r, c)
                if it is None:
                    row_data.append(("", None))  # 空白格也是一筆
                else:
                    txt = it.text()
                    align = it.data(QtCore.Qt.TextAlignmentRole)
                    row_data.append((txt, align))
            data.append(row_data)
        return data

    def list_to_table(self, table, data):
        table.blockSignals(True)
        was_sort = table.isSortingEnabled()
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)

        rows = len(data)
        cols = len(data[0]) if rows else 0
        table.setRowCount(rows)
        table.setColumnCount(cols)

        for r in range(rows):
            for c in range(cols):
                txt, align = data[r][c]
                it = table.item(r, c)
                if it is None:
                    it = QtWidgets.QTableWidgetItem()
                    table.setItem(r, c, it)

                it.setText(txt)
                if align is not None:
                    it.setData(QtCore.Qt.TextAlignmentRole, align)

        table.setUpdatesEnabled(True)
        table.setSortingEnabled(was_sort)
        table.blockSignals(False)

    def copy_from_self_prescript(
        self,
        table_widget_self_prescript,
        packages,
        pres_days,
        instruction,
        total_dosage,
    ):
        # self.ui.tableWidget_prescript.blockSignals(True)
        # row_count = table_widget_self_prescript.rowCount()
        # for row_no in range(row_count):
        #     row = dict()
        #     medicine_key_item = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineKey'])
        #     if medicine_key_item is None:
        #         continue

        #     medicine_key = medicine_key_item.text()
        #     row['MedicineKey'] = medicine_key
        #     row['MedicineType'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineType']).text()
        #     row['Price'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Price']).text()
        #     row['Amount'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Amount']).text()
        #     row['InsCode'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['InsCode']).text()
        #     row['MedicineName'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['MedicineName']).text()
        #     row['Unit'] = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Unit']).text()
        #     dosage = table_widget_self_prescript.item(
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Dosage']).text()
        #     row['Instruction'] = table_widget_self_prescript.item(  # 2024-08-21 曙光
        #         row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Instruction']).text()

        #     self.append_null_medicine()
        #     self.append_prescript(row, dosage, set_valuation=False, set_dosage_percent=False)
        #     self._set_dosage_format(row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Dosage'])
        #     self._set_price_format(row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Price'])
        #     self._set_price_format(row_no, prescript_utils.SELF_PRESCRIPT_COL_NO['Amount'])

        # self.ui.tableWidget_prescript.blockSignals(False)

        prescript_utils.duplicate_table_widget(
            table_widget_self_prescript, self.ui.tableWidget_prescript
        )

        self.ui.doubleSpinBox_total_dosage.setValue(total_dosage)  # 2024-08-21 曙光
        self.ui.comboBox_package.setCurrentText(packages)
        self.ui.comboBox_pres_days.setCurrentText(pres_days)
        self.ui.comboBox_instruction.setCurrentText(instruction)

        self.append_null_medicine()
        self._calculate_total_dosage()
        self._calculate_self_total_fee
        self.parent.calculate_self_fees()

        self._set_valuation()  # 2024-08-21 曙光
        if self.dosage_percent == "Y" or self.ui.doubleSpinBox_total_dosage.value() > 0:
            self._set_dosage_again(
                "自費",
                table_widget_self_prescript,
                prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"],
            )

    def _set_price(self):
        if self.ui.comboBox_valuation.currentText() == "正常計價":
            self._set_normal_price()
        elif self.ui.comboBox_valuation.currentText() == "不計價":
            self._set_free_price()
        elif self.ui.comboBox_valuation.currentText() == "單日計價":
            self._set_single_price()
        elif self.ui.comboBox_valuation.currentText() == "單複方不計價":
            self._set_additional_medicine_price()
        else:
            self._set_normal_price()

        self._calculate_self_total_fee()
        self.parent.calculate_self_fees()

    def _set_normal_price(self):
        self._remove_single_price_medicine()

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_key = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]
            )

            if medicine_key in [None, ""]:
                continue

            self._set_medicine_price(row_no, medicine_key)

    def _set_free_price(self):
        self._remove_single_price_medicine()
        self._clear_all_medicine_price()

    def _set_additional_medicine_price(self):
        self._remove_single_price_medicine()

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )

            if medicine_type in [None, ""]:
                continue

            medicine_type = medicine_type.text()
            if medicine_type in ["單方", "複方"]:
                self._clear_single_medicine_price(row_no)
            else:
                medicine_key = self.ui.tableWidget_prescript.item(
                    row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineKey"]
                )

                self._set_medicine_price(row_no, medicine_key)

    def _get_single_medicine_row_no(self):
        single_medicine = None
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name is None:
                continue

            medicine_name = medicine_name.text()
            if medicine_name in ["自費藥費", "自費水藥", "自費粉藥"]:
                single_medicine = row_no
                break

        return single_medicine

    def _is_free_medicine(self):
        is_free = True

        row_count = self.ui.tableWidget_prescript.rowCount()

        medicine_count = 0
        for row_no in range(row_count):
            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name is not None and medicine_name.text() != "":
                medicine_count += 1

            amount = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"]
            )
            if amount is not None and number_utils.get_float(amount.text()) > 0:
                is_free = False
                return is_free

        if medicine_count <= 0:
            is_free = False

        return is_free

    def _get_single_medicine_type(self):
        medicine_name = "自費藥費"
        powder, herb = 0, 0

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if item is None:
                continue

            medicine_type = item.text()
            if medicine_type == "水藥":
                herb += 1
            elif medicine_type in ["單方", "複方"]:
                powder += 1

        if herb > 0 and herb > powder:
            medicine_name = "自費水藥"
        elif powder > 0 and powder > herb:
            medicine_name = "自費粉藥"

        if medicine_name == "自費藥費":
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("要開哪種藥品")
            msg_box.setText(
                "<font size='4' color='red'><b>請問要開哪種類型的藥品?</b></font>"
            )
            msg_box.setInformativeText("請選擇以上的藥品類型")
            msg_box.addButton(QPushButton("自費粉藥"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("自費水藥"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("其他"), QMessageBox.RejectRole)
            medicine_type = msg_box.exec_()
            if medicine_type == QMessageBox.AcceptRole:
                medicine_name = "自費粉藥"
            elif medicine_type == QMessageBox.RejectRole:
                medicine_name = "自費水藥"

        return medicine_name

    def _calculate_single_price_medicine(self):
        medicine_name_item = self.ui.tableWidget_prescript.item(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )

        if medicine_name_item is None:
            return

        medicine_name = medicine_name_item.text()
        if medicine_name not in ["自費水藥", "自費粉藥", "自費藥費"]:
            return

        try:
            # self.ui.tableWidget_prescript.itemChanged.disconnect()
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        if medicine_name == "自費水藥":
            total_dosage = self._get_total_dosage(default_medicine_type="水藥")
            medicine_fee = charge_utils.get_herb_fee(
                self.database,
                self.system_settings,
                medicine_name,
                total_dosage,
                case_key=self.case_key,
                table_widget_prescript=self.ui.tableWidget_prescript,
            )
        else:
            medicine_fee = charge_utils.get_misc_fee(self.database, medicine_name)

        self._set_single_medicine_price(0, medicine_fee)
        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.blockSignals(False)

    def _add_single_price_medicine(self, medicine_name):
        if self._get_single_medicine_row_no() is not None:
            return

        self._insert_medicine_row(0)
        dosage = 1
        if medicine_name is None:
            medicine_name = self._get_single_medicine_type()

        if medicine_name in ["自費水藥", "自費粉藥", "自費藥費"]:
            if medicine_name == "自費水藥":
                total_dosage = self._get_total_dosage(default_medicine_type="水藥")
                medicine_fee = charge_utils.get_herb_fee(
                    self.database,
                    self.system_settings,
                    medicine_name,
                    total_dosage,
                    case_key=self.case_key,
                    table_widget_prescript=self.ui.tableWidget_prescript,
                )
                medicine_type = "水藥"
                unit = "帖"
            else:
                medicine_fee = charge_utils.get_misc_fee(self.database, medicine_name)
                medicine_type = "複方"
                unit = "日"

                if self.system_settings.field("院所名稱") == "專嘉中醫診所":
                    total_dosage = self._get_total_dosage()
                    pres_days = number_utils.get_integer(
                        self.ui.comboBox_pres_days.currentText()
                    )
                    dosage = int(pres_days / 7)
                    if dosage <= 0:
                        dosage = 1

                    if total_dosage > 22:
                        medicine_fee = 750
                    else:
                        medicine_fee = 420

                    medicine_type = "單方"
                    unit = "週"
        else:
            medicine_fee = 100
            medicine_type = "高貴"
            unit = "日"

        row = dict()
        row["MedicineKey"] = None
        row["MedicineType"] = medicine_type
        row["InsCode"] = None
        row["SalePrice"] = medicine_fee
        row["Price"] = medicine_fee
        row["Amount"] = medicine_fee
        row["MedicineName"] = medicine_name
        row["Unit"] = unit

        self.append_prescript(row, dosage)
        self._set_dosage_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"])
        self._set_price_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"])
        self._set_price_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"])

        self.ui.tableWidget_prescript.setCurrentCell(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        )

    def _remove_single_price_medicine(self):
        row_no = self._get_single_medicine_row_no()
        if row_no is not None:
            self.ui.tableWidget_prescript.removeRow(row_no)

    def _set_single_price(self, medicine_name=None):
        self._do_set_dosage_percent = False

        maximum_price = charge_utils.get_ins_drug_single_day_maximum_price(
            self.database
        )
        if maximum_price > 0:  # 有設定自費粉藥單日計價上限才檢查 2023.07.17 和悅
            ins_drug_single_day_price = self._get_ins_drug_single_day_price()
            if ins_drug_single_day_price > maximum_price:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "自費粉藥成本超過單日計價",
                    f"""
                        <font color="red">
                            <h3>注意！自費粉藥的成本為{ins_drug_single_day_price},
                            已經超過單日計價的{maximum_price}元上限, 無法轉為單日計價</h3>
                        </font>
                    """,
                    "請勿超過單日計價的成本",
                )
                self.ui.comboBox_valuation.setCurrentText("正常計價")
                return

        self._remove_single_price_medicine()
        self._clear_medicine_price()

        self._add_single_price_medicine(medicine_name)
        self._calculate_self_total_fee()
        self.parent.calculate_self_fees()

    def _clear_medicine_price(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if item is not None and (
                "加價" in item.text() or item.text() == charge_utils.PROCESS_MEDICINE
            ):
                continue

            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if item is not None and item.text() not in ["單方", "複方", "水藥"]:
                continue

            self._clear_single_medicine_price(row_no)

    def _clear_all_medicine_price(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if item is not None and (
                "加價" in item.text() or item.text() == charge_utils.PROCESS_MEDICINE
            ):
                continue

            self._clear_single_medicine_price(row_no)

    def _clear_single_medicine_price(self, row_no):
        try:
            # self.ui.tableWidget_prescript.itemChanged.disconnect()
            self.ui.tableWidget_prescript.blockSignals(True)
        except Exception:
            pass

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, "0.0")
        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
            item,
        )

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, "0.0")
        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
            item,
        )
        self._adjust_prescript_column_align(row_no)

        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.tableWidget_prescript.blockSignals(False)

    def _set_single_medicine_price(self, row_no, fee):
        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, fee)
        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
            item,
        )
        self._calculate_total_price(
            0, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"], item
        )
        self._adjust_prescript_column_align(row_no)

    def _set_medicine_price(self, row_no, medicine_key):
        if medicine_key is None or medicine_key.text() == "":
            return

        sql = "SELECT SalePrice FROM medicine WHERE MedicineKey = %s"
        rows = self.database.select_record(sql, (medicine_key.text(),))

        if len(rows) <= 0:
            return

        row = rows[0]
        price = string_utils.get_formatted_str("單價", row["SalePrice"])

        item = QtWidgets.QTableWidgetItem()
        item.setData(QtCore.Qt.EditRole, price)
        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["Price"],
            item,
        )

    def _receive_medicine(self):
        process_fee = 0

        receive_type = "現場領藥"
        if self.ui.radioButton_process_medicine.isChecked():
            receive_type = "代煎水藥"

        if receive_type == "代煎水藥":
            process_fee = charge_utils.get_misc_fee(self.database, "代煎費")

        if process_fee > 0:
            self._add_process_medicine_fee(process_fee)
        else:
            self._remove_process_medicine_fee()

        self.parent.calculate_self_fees()
        self._calculate_total_dosage()
        self._calculate_total_costs()
        self._calculate_self_total_fee()

    def _remove_process_medicine_fee(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
            )
            if item is None:
                continue

            medicine_name = item.text()
            if medicine_name == charge_utils.PROCESS_MEDICINE:
                self.ui.tableWidget_prescript.removeRow(row_no)
                break

    def _add_process_medicine_fee(self, process_fee):
        self._remove_process_medicine_fee()

        dosage = 1
        row = dict()
        row["MedicineKey"] = None
        row["MedicineType"] = "水藥"
        row["InsCode"] = None
        row["Dosage"] = dosage
        row["SalePrice"] = process_fee
        row["Price"] = process_fee
        row["Amount"] = process_fee * dosage
        row["MedicineName"] = charge_utils.PROCESS_MEDICINE
        row["Unit"] = "次"
        self.append_null_medicine()
        self.ui.tableWidget_prescript.setCurrentCell(
            self.ui.tableWidget_prescript.rowCount() - 1, 0
        )
        self.append_prescript(row, dosage)
        self._set_dosage_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"])
        self._set_price_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"])
        self._set_price_format(0, prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"])

    # 拷貝過去病歷的處方
    def copy_past_treat(self, case_key):
        sql = "SELECT Treatment FROM cases WHERE CaseKey = %s"
        row = self.database.select_record(sql, (case_key,))[0]

        treatment = string_utils.xstr(row["Treatment"])
        row = dict()
        row["MedicineKey"] = None
        row["MedicineType"] = "穴道"
        row["InsCode"] = None
        row["Dosage"] = 1
        row["SalePrice"] = 0
        row["Price"] = 0
        row["Amount"] = 0
        row["MedicineName"] = treatment
        row["Unit"] = "次"

        sql = """
            SELECT * FROM prescript
            WHERE
                CaseKey = %s AND
                MedicineType IN ("穴道", "處置") AND
                MedicineSet = 1
            ORDER BY PrescriptKey
        """
        rows = self.database.select_record(sql, (case_key,))
        rows.insert(0, row)

        for row in rows:
            medicine_name = string_utils.xstr(row["MedicineName"])
            if medicine_name in [None, ""]:
                continue

            self.append_null_medicine()
            self.append_prescript(row, 1)

    def _set_prescript_remark(self):
        row = prescript_utils.get_prescript_remark_row(
            self.parent, self.database, self.case_key
        )
        if row is None:
            return

        self.append_null_medicine()
        self.append_prescript(row, 0)

    def _clear_medicine_name_remark(self, medicine_name):
        medicine_name_remark_list = ["水揮", "生粉"]
        for medicine_name_remark in medicine_name_remark_list:
            if medicine_name_remark in medicine_name:
                medicine_name = medicine_name.split(f"({medicine_name_remark})")[0]

        return medicine_name

    def _set_medicine_name(self):
        row_no = self.ui.tableWidget_prescript.currentRow()
        item = self.ui.tableWidget_prescript.item(
            row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"]
        )
        if item is None:
            return

        medicine_name = item.text()
        medicine_name_remark = prescript_utils.get_medicine_name_remark(self.parent)
        medicine_name = self._clear_medicine_name_remark(medicine_name)
        if medicine_name_remark is not None:
            medicine_name += f"({medicine_name_remark})"

        self.ui.tableWidget_prescript.setItem(
            row_no,
            prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"],
            QtWidgets.QTableWidgetItem(medicine_name),
        )

    def _show_acupuncture_point(self):
        dialog = dialog_utils.get_dialog_acupuncture_point(
            self, self.database, self.system_settings
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        acupuncture_point_list = dialog.acupuncture_point_list
        dialog.deleteLater()

        if len(acupuncture_point_list) <= 0:
            return

        row = {
            "MedicineType": "穴道",
            "MedicineKey": None,
            "InsCode": None,
            "Unit": None,
        }

        for acupuncture_point in acupuncture_point_list:
            row["MedicineName"] = acupuncture_point
            self.append_null_medicine()
            self.append_prescript(row)

    def medicine_to_herb(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type_item = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"]
            )
            if medicine_type_item is None:
                continue

            medicine_type = medicine_type_item.text()
            if medicine_type not in ["單方", "複方"]:
                continue

            self.ui.tableWidget_prescript.setItem(
                row_no,
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineType"],
                QtWidgets.QTableWidgetItem("水藥"),
            )

            self.ui.tableWidget_prescript.setItem(
                row_no,
                prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"],
                QtWidgets.QTableWidgetItem("錢"),
            )
            self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Unit"]
            ).setTextAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

    def _set_instruction(self):
        dialog = dialog_utils.get_dialog_instruction(
            self, self.database, self.system_settings
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        instruction = dialog.get_instruction()
        if instruction != "":
            self.ui.comboBox_instruction.setCurrentText(instruction)

        dialog.deleteLater()

    def _open_dialog_compound_json(self):
        dialog = dialog_utils.get_dialog_compound_json(
            self,
            self.database,
            self.system_settings,
            self.medicine_set,
            self.ui.tableWidget_prescript,
        )
        dialog.exec_()
        dialog.deleteLater()

    def _total_dosage_value_changed(self):
        self._set_dosage_percent()

    def _is_manual_percent(self):
        manual_percent = False

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"], row_no
            )
            if medicine_type not in ["單方", "複方"]:
                continue

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], row_no
            )
            if medicine_name in ["自費粉藥"]:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"], row_no
            )
            if numerator == "0":
                manual_percent = True
                break

        return manual_percent

    def _is_numerator_completed(self):
        numerator_completed = False
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"], row_no
            )
            if medicine_type not in ["單方", "複方"]:
                continue

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], row_no
            )
            if medicine_name in ["自費粉藥"]:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"], row_no
            )
            if medicine_name not in ["", None] and numerator in ["", None]:
                numerator_completed = False
                self._clear_all_dosages()
                break
            else:
                numerator_completed = True

        return numerator_completed

    def _get_denominator(self):
        denominator = 0
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"], row_no
            )
            if medicine_type not in ["單方", "複方"]:
                continue

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], row_no
            )
            if medicine_name in ["自費粉藥"]:
                continue

            percent = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"], row_no
            )
            if percent in ["", None]:
                continue
            else:
                denominator += number_utils.get_float(percent)

        return denominator

    def _clear_all_dosages(self):
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            self.ui.tableWidget_prescript.setItem(
                row_no,
                prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"],
                QtWidgets.QTableWidgetItem(None),
            )

    def _get_percent_total_dosage(self):
        total_dosage = self.doubleSpinBox_total_dosage.value()

        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"], row_no
            )
            if medicine_type not in ["單方", "複方"]:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["Instruction"], row_no
            )
            numerator = number_utils.get_float(numerator)

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"], row_no
            )
            if (
                medicine_name not in ["", None, "自費粉藥", "自費水藥"]
                and numerator == 0
            ):  # 扣掉instruction = 0的劑量
                dosage = self.table_widget_prescript.field_value(
                    prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"], row_no
                )
                dosage = number_utils.get_float(dosage)
                total_dosage -= dosage

        return total_dosage

    def _set_dosage_percent(self):
        self.ui.tableWidget_prescript.blockSignals(False)
        if not self._do_set_dosage_percent:
            self._do_set_dosage_percent = True
            return

        total_dosage = self._get_percent_total_dosage()

        if total_dosage <= 0:
            return

        # if self._is_manual_percent():
        #     return

        if not self._is_numerator_completed():
            self._clear_all_dosages()
            return

        denominator = self._get_denominator()

        self.ui.tableWidget_prescript.blockSignals(True)
        col_no = prescript_utils.SELF_PRESCRIPT_COL_NO["Dosage"]
        for row_no in range(self.ui.tableWidget_prescript.rowCount()):
            medicine_type = self.table_widget_prescript.field_value(
                prescript_utils.INS_PRESCRIPT_COL_NO["MedicineType"], row_no
            )
            if medicine_type not in ["單方", "複方"]:
                continue

            medicine_name = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["MedicineName"], row_no
            )
            if medicine_name in ["自費粉藥"]:
                continue

            numerator = self.table_widget_prescript.field_value(
                prescript_utils.SELF_PRESCRIPT_COL_NO["Instruction"], row_no
            )
            if numerator in ["", None, 0, "0"]:
                continue

            try:
                numerator = number_utils.get_float(numerator)
                dosage = (total_dosage * numerator) / denominator
                dosage = round(dosage, 1)

                self.ui.tableWidget_prescript.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(str(dosage))
                )
                current_item = self.ui.tableWidget_prescript.item(row_no, col_no)
                current_item.setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            except Exception:
                pass

            price = self.ui.tableWidget_prescript.item(
                row_no, prescript_utils.SELF_PRESCRIPT_COL_NO["Price"]
            )
            if price is None:
                continue

            price = round(number_utils.get_float(price.text()), 1)
            amount = round(dosage * price, 1)
            self.ui.tableWidget_prescript.setItem(
                row_no,
                prescript_utils.SELF_PRESCRIPT_COL_NO["Amount"],
                QtWidgets.QTableWidgetItem(
                    string_utils.get_formatted_str("單價", amount)
                ),
            )
            self._adjust_prescript_column(row_no)

        self.ui.tableWidget_prescript.blockSignals(False)

        self._calculate_self_total_fee()
        self._calculate_total_dosage()
        self.parent.calculate_self_fees()
        # self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)i

    def _print_receipt_clicked(self, checked, prompt_warning=True):
        if checked and prompt_warning:
            reply = QMessageBox.question(
                self,
                "確認不印",
                "您確定要設定不印此份單據嗎？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                self.ui.checkBox_print_receipt.blockSignals(True)
                self.ui.checkBox_print_receipt.setChecked(False)
                self.ui.checkBox_print_receipt.blockSignals(False)
                self.ui.checkBox_print_receipt.setStyleSheet(None)
                return  # 提早結束，避免下面再設定紅色樣式

        # 勾選時變紅色，否則清除樣式
        style_sheet = "color: red; font-weight: bold" if checked else None
        self.ui.checkBox_print_receipt.setStyleSheet(style_sheet)

    def _insert_compound(self):
        dialog = dialog_utils.get_dialog_insert_compound(
            self,
            self.database,
            self.system_settings,
            self.ui.tableWidget_prescript,
        )
        dialog.exec_()
        dialog.deleteLater()

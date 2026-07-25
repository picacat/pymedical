# 輸入處方 2018.06.15
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets

from libs import (
    class_utils,
    dialog_utils,
    medicine_utils,
    number_utils,
    personnel_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 建立藥品詞庫
class DialogInputDrug(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogInputDrug, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.medicine_type = args[2]

        try:
            self.medicine_key = args[3]
        except IndexError:
            self.medicine_key = None

        self.ui = None
        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        if self.medicine_key is not None:
            self._edit_medicine()
            self._edit_commission()

        self._set_permission()
        self._set_medicine_type()

    def _set_medicine_type(self):
        self.ui.comboBox_medicine_type.setCurrentText(self.medicine_type)

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_INPUT_DRUG, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("存檔")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self._set_combo_box()
        self.ui.lineEdit_medicine_name.setFocus()
        self.table_widget_commission = class_utils.get_table_widget(
            self.ui.tableWidget_commission, self.database
        )
        self._set_table_width()

    def _set_table_width(self):
        width = [150, 120, 450]
        self.table_widget_commission.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)
        self.ui.toolButton_add_commission.clicked.connect(self._add_commission)
        self.ui.toolButton_remove_commission.clicked.connect(self._remove_commission)
        self.ui.toolButton_modify_commission.clicked.connect(self._modify_commission)
        self.ui.tableWidget_commission.doubleClicked.connect(self._modify_commission)
        self.ui.lineEdit_medicine_name.textChanged.connect(self._set_input_code)

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, "處方資料", "更改抽成", self.user_name
            )
            != "Y"
        ):
            self.ui.lineEdit_commission.setVisible(False)
            self.ui.label_commission.setVisible(False)
            self.ui.label_commission_hint.setVisible(False)
            self.ui.groupBox_commission.setVisible(False)

    # 設定 comboBox
    def _set_combo_box(self):
        sql = "SELECT Unit FROM medicine GROUP BY Unit ORDER BY Unit"
        rows = self.database.select_record(sql)
        unit_list = [
            None,
        ]
        for row in rows:
            if row["Unit"] is None or str(row["Unit"]).strip() == "":
                continue
            unit_list.append(str(row["Unit"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_unit, unit_list)

        sql = """
            SELECT MedicineMode FROM medicine
            WHERE
                (MedicineType != "穴道" AND MedicineType != "處置")
            GROUP BY MedicineMode
            ORDER BY LENGTH(MedicineMode)
        """
        rows = self.database.select_record(sql)
        medicine_mode_list = [
            None,
        ]
        for row in rows:
            if row["MedicineMode"] is None or str(row["MedicineMode"]).strip() == "":
                continue
            medicine_mode_list.append(str(row["MedicineMode"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_medicine_mode, medicine_mode_list)

        sql = """
            SELECT Project FROM medicine
            WHERE
                Project IS NOT NULL
            GROUP BY Project
            ORDER BY LENGTH(Project)
        """
        rows = self.database.select_record(sql)
        project_list = []
        for row in rows:
            project_list.append(str(row["Project"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_project, project_list, None)

        sql = """
            SELECT DoctorProject FROM medicine
            WHERE
                DoctorProject IS NOT NULL
            GROUP BY DoctorProject
            ORDER BY LENGTH(DoctorProject)
        """
        rows = self.database.select_record(sql)
        project_list = []
        for row in rows:
            project_list.append(str(row["DoctorProject"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_doctor_project, project_list, None)

        sql = """
            SELECT Deactivate FROM medicine
            WHERE
                Deactivate IS NOT NULL
            GROUP BY Deactivate
            ORDER BY Deactivate
        """
        rows = self.database.select_record(sql)
        deactivate_list = [
            None,
        ]
        for row in rows:
            if row["Deactivate"] is None or str(row["Deactivate"]).strip() == "":
                continue
            deactivate_list.append(str(row["Deactivate"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_deactivate, deactivate_list)

        sql = """
            SELECT MedicineType FROM medicine
            GROUP BY MedicineType
            ORDER BY FIELD(
                MedicineType,
                "單方", "複方", "水藥", "外用", "高貴", "器材", "穴道", "處置", "其他", "照護", "檢驗", "成方")
        """
        rows = self.database.select_record(sql)
        medicine_type_list = []
        for row in rows:
            if row["MedicineType"] is None or str(row["MedicineType"]).strip() == "":
                continue
            medicine_type_list.append(str(row["MedicineType"]).strip())

        ui_utils.set_combo_box(self.ui.comboBox_medicine_type, medicine_type_list)

    def _edit_medicine(self):
        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineKey = {self.medicine_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            self._insert_null_medicine(self.medicine_key)
            sql = f"""
                SELECT * FROM medicine
                WHERE
                    MedicineKey = {self.medicine_key}
            """
            rows = self.database.select_record(sql)

        row = rows[0]
        self.medicine_type = string_utils.xstr(row["MedicineType"])
        self.ui.lineEdit_medicine_code.setText(row["MedicineCode"])
        self.ui.lineEdit_input_code.setText(row["InputCode"])
        self.ui.lineEdit_medicine_name.setText(row["MedicineName"])
        self.ui.lineEdit_drug_name.setText(row["DrugName"])

        if row["AnimalDerived"] == 1:
            self.ui.checkBox_animal_derived.setChecked(True)
        else:
            self.ui.checkBox_animal_derived.setChecked(False)

        self.ui.comboBox_unit.setCurrentText(row["Unit"])
        self.ui.comboBox_medicine_mode.setCurrentText(row["MedicineMode"])
        self.ui.lineEdit_ins_code.setText(row["InsCode"])
        self.ui.lineEdit_dosage.setText(string_utils.xstr(row["Dosage"]))
        self.ui.doubleSpinBox_min.setValue(number_utils.get_float(row["MinDosage"]))
        self.ui.doubleSpinBox_max.setValue(number_utils.get_float(row["MaxDosage"]))
        self.ui.lineEdit_medicine_alias.setText(row["MedicineAlias"])
        self.ui.lineEdit_location.setText(row["Location"])
        self.ui.lineEdit_in_price.setText(string_utils.xstr(row["InPrice"]))
        self.ui.lineEdit_sale_price.setText(string_utils.xstr(row["SalePrice"]))
        self.ui.lineEdit_quantity.setText(string_utils.xstr(row["Quantity"]))
        self.ui.lineEdit_safe_quantity.setText(string_utils.xstr(row["SafeQuantity"]))
        self.ui.lineEdit_commission.setText(string_utils.xstr(row["Commission"]))
        self.ui.comboBox_project.setCurrentText(string_utils.xstr(row["Project"]))
        self.ui.comboBox_doctor_project.setCurrentText(
            string_utils.xstr(row["DoctorProject"])
        )
        self.ui.comboBox_deactivate.setCurrentText(string_utils.xstr(row["Deactivate"]))
        try:
            self.ui.textEdit_description.setPlainText(
                string_utils.get_str(row["Description"], "utf8")
            )
        except TypeError:
            pass

        if string_utils.xstr(row["Charged"]) == "Y":
            self.ui.checkBox_no_discount.setChecked(True)
        else:
            self.ui.checkBox_no_discount.setChecked(False)

        if string_utils.xstr(row["NoDosage"]) == "Y":
            self.ui.checkBox_no_dosage.setChecked(True)
        else:
            self.ui.checkBox_no_dosage.setChecked(False)

        if string_utils.xstr(row["NonNHI"]) == "Y":
            self.ui.checkBox_non_nhi.setChecked(True)
        else:
            self.ui.checkBox_non_nhi.setChecked(False)

        bonus = medicine_utils.get_medicine_extend(
            self.database, self.medicine_key, "療程實現贈送"
        )
        self.ui.lineEdit_bonus.setText(bonus)

    def _insert_null_medicine(self, medicine_key):
        fields = ["MedicineKey"]
        data = [medicine_key]
        self.database.insert_record("medicine", fields, data)

    def _edit_commission(self):
        sql = f"""
            SELECT * FROM commission
            WHERE
                MedicineKey = {self.medicine_key}
            ORDER BY CommissionKey
        """
        self.table_widget_commission.set_db_data(sql, self._set_table_data)

    def _set_table_data(self, row_no, row):
        commission_row = [
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Commission"]),
            string_utils.xstr(row["Remark"]),
        ]

        for column in range(len(commission_row)):
            self.ui.tableWidget_commission.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(commission_row[column])
            )
            if column in [1]:
                self.ui.tableWidget_commission.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def accepted_button_clicked(self):
        if self.medicine_key is None:
            medicine_key = self._insert_medicine()
            self._insert_commission(medicine_key)
        else:
            self._update_medicine()
            self._save_commission()

    def _insert_medicine(self):
        if self.ui.checkBox_no_discount.isChecked():
            no_discount = "Y"
        else:
            no_discount = None

        if self.ui.checkBox_animal_derived.isChecked():
            animal_derived = 1
        else:
            animal_derived = 0

        fields = [
            "MedicineType",
            "MedicineCode",
            "InputCode",
            "MedicineName",
            "DrugName",
            "Unit",
            "MedicineMode",
            "InsCode",
            "Dosage",
            "MinDosage",
            "MaxDosage",
            "MedicineAlias",
            "Location",
            "InPrice",
            "SalePrice",
            "Commission",
            "Quantity",
            "SafeQuantity",
            "Charged",
            "AnimalDerived",
            "Description",
        ]
        data = [
            self.ui.comboBox_medicine_type.currentText(),
            self.ui.lineEdit_medicine_code.text(),
            self.ui.lineEdit_input_code.text(),
            self.ui.lineEdit_medicine_name.text(),
            self.ui.lineEdit_drug_name.text(),
            self.ui.comboBox_unit.currentText(),
            self.ui.comboBox_medicine_mode.currentText(),
            self.ui.lineEdit_ins_code.text(),
            self.ui.lineEdit_dosage.text(),
            self.ui.doubleSpinBox_min.value(),
            self.ui.doubleSpinBox_max.value(),
            self.ui.lineEdit_medicine_alias.text(),
            self.ui.lineEdit_location.text(),
            self.ui.lineEdit_in_price.text(),
            self.ui.lineEdit_sale_price.text(),
            self.ui.lineEdit_commission.text(),
            self.ui.lineEdit_quantity.text(),
            self.ui.lineEdit_safe_quantity.text(),
            no_discount,
            animal_derived,
            self.ui.textEdit_description.toPlainText(),
        ]
        string_utils.str_to_none(data)
        medicine_key = self.database.insert_record("medicine", fields, data)

        return medicine_key

    def _insert_commission(self, medicine_key):
        fields = ["MedicineKey", "Name", "Commission", "Remark"]

        for row_no in range(self.ui.tableWidget_commission.rowCount()):
            name = self.ui.tableWidget_commission.item(row_no, 0).text()
            commission = self.ui.tableWidget_commission.item(row_no, 1).text()
            remark = self.ui.tableWidget_commission.item(row_no, 2).text()

            data = [medicine_key, name, commission, remark]
            self.database.insert_record("commission", fields, data)

    def _update_medicine(self):
        if self.ui.checkBox_no_discount.isChecked():
            no_discount = "Y"
        else:
            no_discount = None

        if self.ui.checkBox_animal_derived.isChecked():
            animal_derived = 1
        else:
            animal_derived = 0

        if self.ui.checkBox_no_dosage.isChecked():
            no_dosage = "Y"
        else:
            no_dosage = None

        if self.ui.checkBox_non_nhi.isChecked():
            non_nhi = "Y"
        else:
            non_nhi = None

        fields = [
            "MedicineType",
            "MedicineCode",
            "InputCode",
            "MedicineName",
            "DrugName",
            "Unit",
            "MedicineMode",
            "InsCode",
            "Dosage",
            "MinDosage",
            "MaxDosage",
            "MedicineAlias",
            "Location",
            "InPrice",
            "SalePrice",
            "Commission",
            "Project",
            "DoctorProject",
            "Quantity",
            "SafeQuantity",
            "Deactivate",
            "Charged",
            "NoDosage",
            "NonNHI",
            "AnimalDerived",
            "Description",
        ]
        data = [
            self.ui.comboBox_medicine_type.currentText(),
            self.ui.lineEdit_medicine_code.text(),
            self.ui.lineEdit_input_code.text(),
            self.ui.lineEdit_medicine_name.text(),
            self.ui.lineEdit_drug_name.text(),
            self.ui.comboBox_unit.currentText(),
            self.ui.comboBox_medicine_mode.currentText(),
            self.ui.lineEdit_ins_code.text(),
            self.ui.lineEdit_dosage.text(),
            self.ui.doubleSpinBox_min.value(),
            self.ui.doubleSpinBox_max.value(),
            self.ui.lineEdit_medicine_alias.text(),
            self.ui.lineEdit_location.text(),
            self.ui.lineEdit_in_price.text(),
            self.ui.lineEdit_sale_price.text(),
            self.ui.lineEdit_commission.text(),
            self.ui.comboBox_project.currentText(),
            self.ui.comboBox_doctor_project.currentText(),
            self.ui.lineEdit_quantity.text(),
            self.ui.lineEdit_safe_quantity.text(),
            self.ui.comboBox_deactivate.currentText(),
            no_discount,
            no_dosage,
            non_nhi,
            animal_derived,
            self.ui.textEdit_description.toPlainText(),
        ]

        self.database.update_record(
            "medicine", fields, "MedicineKey", self.medicine_key, data
        )

        bonus = self.ui.lineEdit_bonus.text().strip()
        extend_type = "療程實現贈送"
        if bonus == "":
            medicine_utils.remove_medicine_extend(
                self.database, self.medicine_key, extend_type
            )
        else:
            medicine_utils.set_medicine_extend(
                self.database, self.medicine_key, extend_type, bonus
            )

    def _save_commission(self):
        self.database.exec_sql(f"""
            DELETE FROM commission
            WHERE
                MedicineKey = {self.medicine_key}
        """)
        fields = ["MedicineKey", "Name", "Commission", "Remark"]

        for row_no in range(self.ui.tableWidget_commission.rowCount()):
            name = self.ui.tableWidget_commission.item(row_no, 0).text()
            commission = self.ui.tableWidget_commission.item(row_no, 1).text()
            remark = self.ui.tableWidget_commission.item(row_no, 2).text()

            data = [self.medicine_key, name, commission, remark]

            self.database.insert_record("commission", fields, data)

    def _get_person_list(self):
        person_list = personnel_utils.get_person(self.database, "全部")
        for row_no in range(self.ui.tableWidget_commission.rowCount()):
            name = self.ui.tableWidget_commission.item(row_no, 0).text()
            if name in person_list:
                person_list.remove(name)

        extra_list = [
            "醫師",
            "推拿師父",
            "櫃台",
            "醫師分成",
            "推拿師父分成",
            "櫃台分成",
            "廠房",
        ]
        for item, item_index in zip(extra_list, range(len(extra_list))):
            person_list.insert(item_index, item)

        return person_list

    def _add_commission(self):
        person_list = self._get_person_list()

        dialog = dialog_utils.get_dialog_commission(
            self, self.database, self.system_settings, person_list
        )
        if not dialog.exec_():
            dialog.deleteLater()
            return

        name = dialog.ui.comboBox_person.currentText()
        commission = dialog.ui.lineEdit_commission.text()
        remark = dialog.ui.lineEdit_remark.text()
        dialog.deleteLater()

        row_no = self.ui.tableWidget_commission.rowCount()
        self.ui.tableWidget_commission.insertRow(row_no)

        row = [name, commission, remark]
        for column in range(len(row)):
            self.ui.tableWidget_commission.setItem(
                row_no,
                column,
                QtWidgets.QTableWidgetItem(string_utils.xstr(row[column])),
            )
            if column in [1]:
                self.ui.tableWidget_commission.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )

    def _remove_commission(self):
        current_row = self.ui.tableWidget_commission.currentRow()
        self.ui.tableWidget_commission.removeRow(current_row)

    def _modify_commission(self):
        if self.ui.tableWidget_commission.rowCount() <= 0:
            return

        current_row = self.ui.tableWidget_commission.currentRow()
        person_list = self._get_person_list()

        dialog = dialog_utils.get_dialog_commission(
            self, self.database, self.system_settings, person_list
        )
        try:
            name = self.ui.tableWidget_commission.item(current_row, 0).text()
        except Exception:
            name = None

        try:
            commission = self.ui.tableWidget_commission.item(current_row, 1).text()
        except Exception:
            commission = None

        try:
            remark = self.ui.tableWidget_commission.item(current_row, 2).text()
        except Exception:
            remark = None

        dialog.ui.comboBox_person.setCurrentText(name)
        dialog.ui.lineEdit_commission.setText(commission)
        dialog.ui.lineEdit_remark.setText(remark)

        if not dialog.exec_():
            dialog.deleteLater()
            return

        name = dialog.ui.comboBox_person.currentText()
        commission = dialog.ui.lineEdit_commission.text()
        remark = dialog.ui.lineEdit_remark.text()

        dialog.deleteLater()

        row = {"Name": name, "Commission": commission, "Remark": remark}
        self._set_table_data(current_row, row)

    def _set_input_code(self):
        if self.ui.lineEdit_input_code.text() != "":
            return

        medicine_name = self.ui.lineEdit_medicine_name.text()
        try:
            input_code = string_utils.get_input_code(medicine_name)[:5]
        except Exception:
            return

        self.ui.lineEdit_input_code.setText(input_code)

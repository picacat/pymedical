# -*- coding: UTF-8 -*-
# 櫃台購藥 2021.12.11

import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    charge_utils,
    class_utils,
    dialog_utils,
    medicine_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    personnel_utils,
    printer_utils,
    purchase_utils,
    registration_utils,
    stock_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 櫃台購藥
class Purchase(QtWidgets.QMainWindow):
    program_name = "櫃台購藥"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.call_from = args[2]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)

        self._set_ui()
        self._set_signal()
        self._set_medicine_type("藥品類別")
        self._set_patient()
        self._set_permission()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "輸入折扣", self.user_name
            )
            != "Y"
        ):
            self.ui.lineEdit_discount.setEnabled(False)

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PURCHASE, self)
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.table_widget_medicine_type = class_utils.get_table_widget(
            self.ui.tableWidget_medicine_type, self.database
        )
        self.table_widget_medicine = class_utils.get_table_widget(
            self.ui.tableWidget_medicine, self.database
        )
        self.ui.tableWidget_medicine.setAlternatingRowColors(True)
        self.table_widget_prescript = class_utils.get_table_widget(
            self.ui.tableWidget_prescript, self.database
        )
        self.ui.tableWidget_prescript.setAlternatingRowColors(True)
        self.ui.dateEdit_purchase_date.setDate(datetime.datetime.now().date())
        self.ui.label_patient_key.setEnabled(False)
        self.ui.lineEdit_patient_key.setEnabled(False)
        self.ui.label_name.setEnabled(False)
        self.ui.lineEdit_name.setEnabled(False)
        self.ui.toolButton_patient_list.setEnabled(False)
        self.ui.toolButton_select_patient.setEnabled(False)
        self.ui.radioButton_medicine.setChecked(True)

        self._set_table_width()
        self._set_combo_box()

        self.ui.tableWidget_medicine_type.setCurrentCell(0, 0)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_purchase)
        self.ui.action_save.triggered.connect(self._save_purchase)
        self.ui.action_save_and_print.triggered.connect(self._save_and_print_purchase)
        self.ui.toolButton_patient_list.clicked.connect(self._patient_picker)
        self.ui.tableWidget_medicine_type.itemSelectionChanged.connect(
            self._groups_changed
        )
        self.ui.tableWidget_medicine.clicked.connect(self._set_prescript)
        self.ui.tableWidget_prescript.itemChanged.connect(self._prescript_item_changed)
        self.ui.lineEdit_input_code.textChanged.connect(self._input_code_changed)
        self.ui.lineEdit_discount.textChanged.connect(self._discount_changed)
        self.ui.lineEdit_receipt_fee.textChanged.connect(self._receipt_fee_changed)
        self.ui.radioButton_1.clicked.connect(self._set_patient)
        self.ui.radioButton_2.clicked.connect(self._set_patient)
        self.ui.comboBox_cashier.currentTextChanged.connect(self._set_sales)
        self.ui.comboBox_doctor.currentTextChanged.connect(self._set_sales)
        self.ui.comboBox_massager.currentTextChanged.connect(self._set_sales)
        self.ui.comboBox_massage_referrer.currentTextChanged.connect(
            self._exclude_assistant
        )
        self.ui.comboBox_nursing_assistant.currentTextChanged.connect(
            self._exclude_assistant
        )

        self.ui.lineEdit_patient_key.textChanged.connect(self._patient_key_changed)
        self.ui.lineEdit_name.textChanged.connect(self._patient_name_changed)
        self.ui.lineEdit_patient_key.returnPressed.connect(self._get_patient)
        self.ui.toolButton_select_patient.clicked.connect(self._select_patient)
        self.ui.radioButton_medicine.clicked.connect(self._set_medicine_group)
        self.ui.radioButton_treat.clicked.connect(self._set_treat_group)
        self.ui.toolButton_calc_discount.clicked.connect(self._calc_discount)

    # 設定欄位寬度
    def _set_table_width(self):
        width = [80, 80, 30, 200, 50, 60, 70, 80, 70, 50, 50, 50]
        self.table_widget_prescript.set_table_heading_width(width)

        self.table_widget_prescript.set_column_hidden(
            [
                purchase_utils.PRESCRIPT_COL_NO["MedicineKey"],
                purchase_utils.PRESCRIPT_COL_NO["MedicineType"],
            ]
        )
        self.table_widget_medicine.set_column_hidden([5, 6, 7, 8, 9])

    def _set_combo_box(self):
        doctor_list = personnel_utils.get_person(self.database, "全部醫師")
        cashier_list = personnel_utils.get_person(self.database, "職員")
        massager_list = personnel_utils.get_person(self.database, "推拿師父")
        ui_utils.set_combo_box(
            self.ui.comboBox_doctor,
            doctor_list,
            None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_massager,
            massager_list,
            None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_massage_referrer,
            massager_list,
            None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_cashier,
            cashier_list,
            None,
        )
        ui_utils.set_combo_box(
            self.ui.comboBox_nursing_assistant,
            cashier_list,
            None,
        )
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD)

        period = registration_utils.get_current_period(self.system_settings)
        self.ui.comboBox_period.setCurrentText(period)

        current_user = self.system_settings.field("使用者")
        if current_user in cashier_list:
            self.ui.comboBox_cashier.setCurrentText(current_user)
        elif current_user in doctor_list:
            self.ui.comboBox_doctor.setCurrentText(current_user)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_purchase(self):
        self.close_all()
        self.close_tab()

    def _set_medicine_group(self):
        self._set_medicine_type("藥品類別")

    def _set_treat_group(self):
        self._set_medicine_type("處置類別")

    def _set_medicine_type(self, medicine_type):
        sql = f'''
            SELECT * FROM dict_groups
            WHERE
                DictGroupsType IN ("{medicine_type}") AND
                DictGroupsLevel3 IS NULL
            ORDER BY DictOrderNo
        '''
        self.table_widget_medicine_type.set_db_data_without_heading(
            sql, "DictGroupsName"
        )

    def _groups_changed(self):
        self._read_medicine()
        self.ui.lineEdit_input_code.setText("")

    def _input_code_changed(self):
        input_code = self.ui.lineEdit_input_code.text()
        self._read_medicine(input_code)

    def _read_medicine(self, input_code=None):
        self.ui.tableWidget_medicine.clear()
        self.ui.tableWidget_medicine.setRowCount(0)

        try:
            groups = self.ui.tableWidget_medicine_type.selectedItems()[0].text()
        except IndexError:
            self.ui.tableWidget_medicine.setRowCount(0)
            return

        if input_code is not None and input_code != "":
            input_code_str = f'''
                AND ((InputCode LIKE "{input_code}%") OR
                     (MedicineName LIKE "{input_code}%"))
            '''
        else:
            input_code_str = f'AND MedicineType = "{groups}"'

        price_condition = ""
        if self.ui.radioButton_treat.isChecked():
            price_condition = "AND (SalePrice > 0)"

        sql = f"""
            SELECT * FROM medicine
            WHERE
                MedicineName IS NOT NULL AND
                (Deactivate IS NULL OR LENGTH(Deactivate) = 0)
                {input_code_str}
                {price_condition}
            ORDER BY LENGTH(MedicineName), CAST(CONVERT(`MedicineName` using big5) AS BINARY)
        """
        rows = self.database.select_record(sql)

        column_count = 5
        x = divmod(len(rows), column_count)
        row_count = x[0]
        if x[1] > 0:
            row_count += 1

        self.ui.tableWidget_medicine.setRowCount(row_count)

        for row_no in range(row_count):
            for col_no in range(column_count):
                rec_no = row_no * column_count + col_no
                if rec_no >= len(rows):
                    break

                sale_price = number_utils.get_float(rows[rec_no]["SalePrice"])
                if sale_price <= 0:
                    sale_price = ""
                else:
                    sale_price = f"${sale_price}"

                unit = string_utils.xstr(rows[rec_no]["Unit"]).strip()
                if unit != "":
                    unit = f"({unit})"

                medicine_name = string_utils.xstr(rows[rec_no]["MedicineName"])
                item_name = f"{medicine_name} {unit} {sale_price}"

                self.ui.tableWidget_medicine.setItem(
                    row_no, col_no, QtWidgets.QTableWidgetItem(item_name)
                )

                self.ui.tableWidget_medicine.setItem(
                    row_no,
                    col_no + column_count,
                    QtWidgets.QTableWidgetItem(
                        string_utils.xstr(rows[rec_no]["MedicineKey"])
                    ),
                )

        self.ui.tableWidget_medicine.resizeRowsToContents()
        self.ui.tableWidget_medicine.setCurrentCell(0, 0)

    def _set_prescript(self):
        current_row = self.ui.tableWidget_medicine.currentRow()
        current_col = self.ui.tableWidget_medicine.currentColumn()
        medicine_name = self.ui.tableWidget_medicine.item(current_row, current_col)
        if medicine_name is None:
            return

        medicine_key = self.ui.tableWidget_medicine.item(
            current_row, current_col + 5
        ).text()
        discount_permission = True
        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "輸入折扣", self.user_name
            )
            != "Y"
        ):
            discount_permission = False

        purchase_utils.insert_prescript_row(
            self.database,
            self.ui.tableWidget_prescript,
            medicine_key,
            [self._calculate_discount, self._calculate_debt, self._calculate_total],
            discount_permission=discount_permission,
        )
        bonus = medicine_utils.get_medicine_extend(
            self.database, medicine_key, "療程實現贈送"
        )
        if number_utils.get_integer(bonus) > 0:
            self.ui.textEdit_remark.setText(f"療程實現贈送{bonus}次")

    def _prescript_item_changed(self, item):
        if item is None:
            return

        purchase_utils.prescript_item_changed(self.ui.tableWidget_prescript, item)
        self._calculate_discount()
        self._calculate_debt()
        self._calculate_total()

    def _calculate_discount(self):
        row_count = self.ui.tableWidget_prescript.rowCount()

        total_discount = 0
        for row_no in range(row_count):
            discount_fee = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["DiscountFee"]
            )
            if discount_fee is None:
                continue

            total_discount += number_utils.get_float(discount_fee.text())

        self.ui.lineEdit_discount.setText(f"{total_discount}")

    def _calculate_debt(self):
        row_count = self.ui.tableWidget_prescript.rowCount()

        total_debt = 0
        for row_no in range(row_count):
            debt = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Debt"]
            )
            if debt is None:
                continue

            total_debt += number_utils.get_float(debt.text())

        self.ui.lineEdit_debt.setText(f"{total_debt}")

    def _calculate_total(self):
        row_count = self.ui.tableWidget_prescript.rowCount()

        subtotal = 0
        for row_no in range(row_count):
            quantity = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Quantity"]
            )
            if quantity is None:
                continue

            price = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Price"]
            )
            if price is None:
                continue

            subtotal += number_utils.get_float(
                quantity.text()
            ) * number_utils.get_float(price.text())

        discount = number_utils.get_float(self.ui.lineEdit_discount.text())
        debt = number_utils.get_float(self.ui.lineEdit_debt.text())
        total = subtotal - discount
        receipt = total - debt

        self.ui.lineEdit_subtotal.setText(f"{subtotal}")
        self.ui.lineEdit_total.setText(f"{total}")
        self.ui.lineEdit_receipt_fee.setText(f"{receipt}")

    def _discount_changed(self):
        subtotal = number_utils.get_float(self.ui.lineEdit_subtotal.text())
        discount = number_utils.get_float(self.ui.lineEdit_discount.text())
        total = subtotal - discount

        self.ui.lineEdit_total.setText(f"{total}")
        self.ui.lineEdit_receipt_fee.setText(f"{total}")

    def _receipt_fee_changed(self):
        total_fee = number_utils.get_integer(self.ui.lineEdit_total.text())
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
        debt = total_fee - receipt_fee

        if debt != 0:
            self.ui.lineEdit_debt.setText(string_utils.xstr(debt))
        else:
            self.ui.lineEdit_debt.setText(None)

    def _patient_key_changed(self):
        patient_key = self.ui.lineEdit_patient_key.text()

        if patient_key == "":
            self.ui.lineEdit_name.setText(None)

        if patient_key.isdigit() and len(patient_key) <= 6:
            self._set_line_edit_patient_data(patient_key)
        else:
            self.ui.lineEdit_name.setText("")

    def _select_patient(self):
        patient_key = patient_utils.select_patient(
            self, self.database, self.system_settings, "patient", "PatientKey", ""
        )

        self._set_line_edit_patient_data(patient_key)

    def _patient_name_changed(self):
        patient_name = self.ui.lineEdit_name.text()

        if patient_name == "":
            pass
            # self.ui.action_save.setEnabled(False)

    def _get_patient(self):
        keyword = self.ui.lineEdit_patient_key.text()

        patient_key = patient_utils.get_patient_by_keyword(
            self, self.database, self.system_settings, "patient", "PatientKey", keyword
        )
        if patient_key in ["", None]:
            return

        patient_key = string_utils.xstr(patient_key)
        self.ui.lineEdit_patient_key.setText(patient_key)
        self._set_line_edit_patient_data(patient_key)

    def _set_line_edit_patient_data(self, patient_key):
        if patient_key in [None, ""]:
            return

        sql = """
            SELECT * FROM patient
            WHERE
                PatientKey = %s
        """
        params = (patient_key,)
        rows = self.database.select_record(sql, params=params)
        if len(rows) <= 0:
            self.ui.lineEdit_name.setText("")
            return

        row = rows[0]
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(row["PatientKey"]))
        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))

    def _set_patient(self):
        if self.ui.radioButton_1.isChecked():
            self.ui.lineEdit_patient_key.setText("")
            self.ui.lineEdit_name.setText("")
            enabled = False
        else:
            self.ui.lineEdit_not_patient.setText("")
            enabled = True

        self.ui.label_not_patient.setEnabled(not enabled)
        self.ui.lineEdit_not_patient.setEnabled(not enabled)

        self.ui.label_patient_key.setEnabled(enabled)
        self.ui.lineEdit_patient_key.setEnabled(enabled)
        self.ui.label_name.setEnabled(enabled)
        self.ui.lineEdit_name.setEnabled(enabled)
        self.ui.toolButton_patient_list.setEnabled(enabled)
        self.ui.toolButton_select_patient.setEnabled(enabled)

        if self.ui.radioButton_2.isChecked():
            self.ui.lineEdit_patient_key.setFocus()

    def _save_purchase(self):
        invoice_no = self.ui.lineEdit_invoice_no.text()
        if invoice_no.strip() != "":
            sql = f'''
                SELECT CaseDate, Name FROM cases
                WHERE
                    InvoiceNo = "{invoice_no}"
                LIMIT 1
            '''
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "單據編號重複",
                    f"""
                        <h3>
                            <font color="red">
                                單據編號{invoice_no}與<br>
                                {row["CaseDate"].date()}{row["Name"]}重複<br>
                                請重新輸入!
                            </font>
                        </h3>""",
                    "請檢查單據編號是否重複輸入.",
                )
                return None

        debt = number_utils.get_integer(self.ui.lineEdit_debt.text())
        if debt > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("欠款確認")
            msg_box.setText(
                f"""
                <font size="5" color="red">
                  <b>此人實收金額不足，會產生 {debt} 的欠款, 是否繼續存檔?</b>
                </font>
            """
            )
            msg_box.setInformativeText("這樣會產生一筆欠款的資料.")
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            msg_box.addButton(QPushButton("確定存檔"), QMessageBox.YesRole)
            save = msg_box.exec_()
            if not save:
                return None

        case_key, case_date = self._save_medical_record()
        medicine_set = 2
        self._save_dosage(case_key, medicine_set)
        self._save_prescript(case_key, case_date, medicine_set)
        self._save_wait(case_key, case_date)
        if debt > 0:
            self._save_debt(case_key, debt)

        if self.system_settings.field("調整庫存量") == "即時調整":
            stock_utils.adjust_self_prescript(self.database, case_key, medicine_set)

        self.close_purchase()

        return case_key

    def _save_debt(self, case_key, debt):
        patient_key, name = self._get_patient_data()

        purchase_date = self.ui.dateEdit_purchase_date.date().toString("yyyy-MM-dd")
        purchase_time = datetime.datetime.now().time().strftime("%H:%M:%S")
        case_date = f"{purchase_date} {purchase_time}"
        period = self.ui.comboBox_period.currentText()

        fields = [
            "CaseKey",
            "PatientKey",
            "DebtType",
            "Name",
            "CaseDate",
            "Period",
            "Fee",
        ]

        data = [
            case_key,
            patient_key,
            "自購欠款",
            name,
            case_date,
            period,
            debt,
        ]
        self.database.insert_record("debt", fields, data)

    def _save_dosage(self, case_key, medicine_set):
        discount_fee = number_utils.get_integer(self.ui.lineEdit_discount.text())
        subtotal_fee = number_utils.get_integer(self.ui.lineEdit_subtotal.text())
        total_fee = number_utils.get_integer(self.ui.lineEdit_total.text())
        discount_rate = 100

        if discount_fee > 0:
            discount_rate = (total_fee / subtotal_fee) * 100

        fields = [
            "CaseKey",
            "MedicineSet",
            "Packages",
            "Days",
            "SelfTotalFee",
            "DiscountRate",
            "DiscountFee",
            "TotalFee",
        ]
        data = [
            case_key,
            medicine_set,
            1,
            1,
            subtotal_fee,
            discount_rate,
            discount_fee,
            total_fee,
        ]

        sql = f"""
            DELETE FROM dosage
            WHERE
                CaseKey = {case_key} AND
                MedicineSet = {medicine_set}
        """
        self.database.exec_sql(sql)
        self.database.insert_record("dosage", fields, data)

    def _save_and_print_purchase(self):
        case_key = self._save_purchase()
        if case_key is None:
            return

        self._print_receipt(case_key, "系統設定")

    # 列印收據
    def _print_receipt(self, case_key, print_mode):
        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, print_mode
        )

    def _get_not_patient_name(self):
        name = self.ui.lineEdit_not_patient.text()
        if name == "":
            name = "自購藥"

        return name

    def _get_patient_data(self):
        if self.ui.radioButton_1.isChecked():
            patient_key = 0
            name = self._get_not_patient_name()
        else:
            patient_key = number_utils.get_integer(self.ui.lineEdit_patient_key.text())
            name = self.ui.lineEdit_name.text()
            if name == "":
                name = "自購藥"

        return patient_key, name

    def _get_self_fees(self):
        charge_fees = {
            "diag_fee": 0,
            "drug_fee": 0,
            "herb_fee": 0,
            "expensive_fee": 0,
            "acupuncture_fee": 0,
            "massage_fee": 0,
            "material_fee": 0,
            "exam_fee": 0,
        }

        row_count = self.ui.tableWidget_prescript.rowCount()
        for row_no in range(row_count):
            item = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["MedicineType"]
            )
            if item is None:
                continue

            medicine_type = item.text()

            item = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Amount"]
            )
            if item is None:
                continue

            amount = number_utils.get_float(item.text())

            field = charge_utils.get_medicine_type_charge_field(
                self.database, medicine_type
            )
            charge_field = charge_utils.get_charge_field(field, medicine_type)
            charge_fees[charge_field] += amount

        return (
            charge_fees["diag_fee"],
            charge_fees["drug_fee"],
            charge_fees["herb_fee"],
            charge_fees["expensive_fee"],
            charge_fees["acupuncture_fee"],
            charge_fees["massage_fee"],
            charge_fees["material_fee"],
            charge_fees["exam_fee"],
        )

    def _save_medical_record(self):
        patient_key, name = self._get_patient_data()

        purchase_date = self.ui.dateEdit_purchase_date.date().toString("yyyy-MM-dd")
        purchase_time = datetime.datetime.now().time().strftime("%H:%M:%S")
        case_date = f"{purchase_date} {purchase_time}"

        doctor_done = "True"
        period = self.ui.comboBox_period.currentText()
        invoice_no = self.ui.lineEdit_invoice_no.text()
        charge_date = None
        charge_period = None
        charge_done = "False"

        if self.system_settings.field("自動完成批價作業") == "Y":
            charge_date = case_date
            charge_period = period
            charge_done = "True"

        (
            diag_fee,
            drug_fee,
            herb_fee,
            expensive_fee,
            acupuncture_fee,
            massage_fee,
            material_fee,
            exam_fee,
        ) = self._get_self_fees()

        fields = [
            "PatientKey",
            "Name",
            "CaseDate",
            "DoctorDate",
            "Period",
            "InsType",
            "TreatType",
            "Remark",
            "Register",
            "Cashier",
            "Doctor",
            "Massager",
            "MassageReferrer",
            "NursingAssistant",
            "SDiagFee",
            "SDrugFee",
            "SHerbFee",
            "SExpensiveFee",
            "SAcupunctureFee",
            "SMassageFee",
            "SMaterialFee",
            "SExamFee",
            "SelfTotalFee",
            "DiscountFee",
            "TotalFee",
            "ReceiptFee",
            "InvoiceNo",
            "DoctorDone",
            "ChargeDate",
            "ChargePeriod",
            "ChargeDone",
            "Card",
            "Share",
        ]

        data = [
            patient_key,
            name,
            case_date,
            case_date,
            period,
            "自費",
            "自購",
            self.ui.textEdit_remark.toPlainText(),
            self.system_settings.field("使用者"),
            self.ui.comboBox_cashier.currentText(),
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_massager.currentText(),
            self.ui.comboBox_massage_referrer.currentText(),
            self.ui.comboBox_nursing_assistant.currentText(),
            diag_fee,
            drug_fee,
            herb_fee,
            expensive_fee,
            acupuncture_fee,
            massage_fee,
            material_fee,
            exam_fee,
            self.ui.lineEdit_subtotal.text(),
            self.ui.lineEdit_discount.text(),
            self.ui.lineEdit_total.text(),
            self.ui.lineEdit_receipt_fee.text(),
            invoice_no,
            doctor_done,
            charge_date,
            charge_period,
            charge_done,
            "免卡",
            "基層醫療",
        ]

        case_key = self.database.insert_record("cases", fields, data)

        return case_key, case_date

    def _save_prescript(self, case_key, case_date, medicine_set):
        row_count = self.ui.tableWidget_prescript.rowCount()

        # Instruction = 療程次數
        fields = [
            "PrescriptNo",
            "CaseKey",
            "CaseDate",
            "MedicineSet",
            "MedicineType",
            "MedicineKey",
            "MedicineName",
            "Dosage",
            "Unit",
            "Price",
            "DiscountFee",
            "Amount",
            "Debt",
            "Promotion",
            "Instruction",
        ]
        for row_no in range(row_count):
            prescript_no = row_no + 1
            medicine_key = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["MedicineKey"]
            ).text()
            medicine_type = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["MedicineType"]
            ).text()
            medicine_name = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["MedicineName"]
            ).text()
            unit = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Unit"]
            ).text()
            quantity = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Quantity"]
            ).text()
            sale_price = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Price"]
            ).text()
            discount_fee = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["DiscountFee"]
            ).text()
            debt = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Debt"]
            ).text()
            amount = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Amount"]
            ).text()
            check_box = self.ui.tableWidget_prescript.cellWidget(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Promotion"]
            )
            promotion = None
            if check_box.isChecked():
                promotion = "Y"

            course = self.ui.tableWidget_prescript.item(
                row_no, purchase_utils.PRESCRIPT_COL_NO["Course"]
            )
            if course is not None:
                course = course.text()

            data = [
                prescript_no,
                case_key,
                case_date,
                medicine_set,
                medicine_type,
                medicine_key,
                medicine_name,
                quantity,
                unit,
                sale_price,
                discount_fee,
                amount,
                debt,
                promotion,
                course,
            ]

            self.database.insert_record("prescript", fields, data)

    def _save_wait(self, case_key, case_date):
        patient_key, name = self._get_patient_data()
        charge_done = "False"
        if self.system_settings.field("自動完成批價作業") == "Y":
            charge_done = "True"

        fields = [
            "CaseKey",
            "CaseDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "TreatType",
            "InsType",
            "Period",
            "Room",
            "RegistNo",
            "Doctor",
            "Massager",
            "DoctorDone",
            "ChargeDone",
        ]

        data = [
            case_key,
            case_date,
            patient_key,
            name,
            "複診",
            "一般門診",
            "自購",
            "自費",
            self.ui.comboBox_period.currentText(),
            1,
            0,
            self.ui.comboBox_doctor.currentText(),
            self.ui.comboBox_massager.currentText(),
            "True",
            charge_done,
        ]

        self.database.insert_record("wait", fields, data)

    def _patient_picker(self):
        case_date = self.ui.dateEdit_purchase_date.date().toString("yyyy-MM-dd")

        dialog = dialog_utils.get_dialog_medical_record_picker(
            self,
            self.database,
            self.system_settings,
            case_date,
            None,
        )
        result = dialog.exec_()
        if not result:
            return

        patient_key = dialog.get_patient_key()
        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))

        dialog.deleteLater()

    def _set_sales(self):
        sender_name = self.sender().objectName()

        if (
            sender_name == "comboBox_massager"
            and self.ui.comboBox_massager.currentText() != ""
        ):
            self.ui.comboBox_massage_referrer.setCurrentText(None)

        if self.system_settings.field("自購藥銷售人員") != "單選":
            return

        if (
            sender_name == "comboBox_cashier"
            and self.ui.comboBox_cashier.currentText() != ""
        ):
            self.ui.comboBox_doctor.setCurrentText(None)
            self.ui.comboBox_massager.setCurrentText(None)
        elif (
            sender_name == "comboBox_doctor"
            and self.ui.comboBox_doctor.currentText() != ""
        ):
            self.ui.comboBox_cashier.setCurrentText(None)
            self.ui.comboBox_massager.setCurrentText(None)
        elif (
            sender_name == "comboBox_massager"
            and self.ui.comboBox_massager.currentText() != ""
        ):
            self.ui.comboBox_cashier.setCurrentText(None)
            self.ui.comboBox_doctor.setCurrentText(None)
            self.ui.comboBox_massage_referrer.setCurrentText(None)

    def _exclude_assistant(self):
        sender_name = self.sender().objectName()

        if sender_name == "comboBox_massage_referrer":
            if self.ui.comboBox_massage_referrer.currentText() != "":
                self.ui.comboBox_nursing_assistant.setCurrentText(None)
                self.ui.comboBox_massager.setCurrentText(None)
        elif sender_name == "comboBox_nursing_assistant":
            if self.ui.comboBox_nursing_assistant.currentText() != "":
                self.ui.comboBox_massage_referrer.setCurrentText(None)

    def _calc_discount(self):
        total_fee = number_utils.get_integer(self.ui.lineEdit_subtotal.text())
        if total_fee == 0:
            return

        discount_rate = self.ui.spinBox_discount_rate.value()
        if discount_rate == 100:
            self.ui.lineEdit_discount.setText("0.0")
            return

        discount_fee = total_fee - number_utils.get_integer(
            total_fee * discount_rate / 100
        )
        self.ui.lineEdit_discount.setText(string_utils.xstr(discount_fee))

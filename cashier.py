# 批價作業 2018.12.10
# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    cshis_utils,
    date_utils,
    nhi_utils,
    notification_utils,
    number_utils,
    personnel_utils,
    prescript_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 批價作業
class Cashier(QtWidgets.QMainWindow):
    program_name = "批價作業"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.allow_refresh_wait_list = True
        self.socket_client = class_utils.get_socket_client()
        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station=self.program_name,
        )

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.read_wait()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_CASHIER, self)
        self.table_widget_charge_list = class_utils.get_table_widget(
            self.ui.tableWidget_charge_list, self.database
        )
        self.ui.action_print_prescription.setEnabled(False)
        self.ui.action_print_receipt.setEnabled(False)
        self.ui.action_print_misc.setEnabled(False)

        self.table_widget_charge_list.set_column_hidden([0, 1])
        self.ui.label_fee_error.setVisible(False)
        self.ui.label_fee_error2.setVisible(False)
        ui_utils.set_combo_box(self.ui.comboBox_payment_type, nhi_utils.PAYMENT_TYPE)
        ui_utils.set_combo_box(self.ui.comboBox_payment_type2, nhi_utils.PAYMENT_TYPE)

        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)
        self._set_group_box_charge()

    def _set_group_box_charge(self):
        if self.system_settings.field("掛號收費批價進行") == "Y":
            self.ui.groupBox_charge.setVisible(False)
        else:
            self.ui.groupBox_charge_all.setVisible(False)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_cashier)
        self.ui.action_save.triggered.connect(self._apply_charge)
        self.ui.action_save_without_print.triggered.connect(self._apply_charge)
        self.ui.action_print_prescription.triggered.connect(
            lambda: self._print_prescript(None)
        )
        self.ui.action_print_receipt.triggered.connect(
            lambda: self._print_receipt(None)
        )
        self.ui.action_print_misc.triggered.connect(lambda: self._print_misc(None))
        self.ui.action_open_medical_record.triggered.connect(self._open_medical_record)

        self.ui.radioButton_unpaid.clicked.connect(self.read_wait)
        self.ui.radioButton_paid.clicked.connect(self.read_wait)
        self.ui.radioButton_all.clicked.connect(self.read_wait)

        self.ui.radioButton_period_all.clicked.connect(self.read_wait)
        self.ui.radioButton_period1.clicked.connect(self.read_wait)
        self.ui.radioButton_period2.clicked.connect(self.read_wait)
        self.ui.radioButton_period3.clicked.connect(self.read_wait)

        self.ui.tableWidget_charge_list.itemSelectionChanged.connect(
            self._pharmacy_list_changed
        )
        self.ui.lineEdit_receipt_drug_share_fee.textChanged.connect(
            self._calculate_receipt_fee
        )
        self.ui.lineEdit_receipt_fee.textChanged.connect(self._calculate_receipt_fee)
        self.ui.lineEdit_receipt_fee2.textChanged.connect(self._calculate_receipt_fee2)

        self.ui.lineEdit_drug_share_fee.textChanged.connect(self._calculate_total_fee)

        self.ui.comboBox_payment_type.currentTextChanged.connect(self._set_payment_type)
        self.ui.comboBox_payment_type2.currentTextChanged.connect(
            self._set_payment_type2
        )

        self.ui.tableWidget_charge_list.doubleClicked.connect(self._open_medical_record)

        self.ui.pushButton_modify.clicked.connect(self._modify_income)

    def _set_permission(self):
        if self.user_name == "超級使用者":
            return

        if (
            personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            != "Y"
        ):
            self.ui.action_open_medical_record.setEnabled(False)

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_cashier(self):
        self.close_all()
        self.close_tab()

    def _send_socket_data(self, doctor, room):
        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                self.program_name,
                doctor,
                room,
            ]
        )

        self.socket_client.send_data(message)  # 舊管道：UDP
        self.notification_client.send_data(message)  # 新管道：資料庫

    def _set_radio_button_period(self, period):
        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def read_wait(self):
        self.ui.label_fee_error.setVisible(False)
        self.ui.pushButton_modify.setVisible(False)

        if self.ui.radioButton_unpaid.isChecked():
            payment = "未批價"
        elif self.ui.radioButton_paid.isChecked():
            payment = "已批價"
        else:
            payment = ""

        if payment == "已批價":
            self.ui.pushButton_modify.setVisible(True)

        self._read_pharmacy_list(payment)

        if self.ui.tableWidget_charge_list.rowCount() > 0:
            action_enabled = True
        else:
            action_enabled = False

        self.ui.action_print_prescription.setEnabled(action_enabled)
        self.ui.action_print_receipt.setEnabled(action_enabled)
        self.ui.action_print_misc.setEnabled(action_enabled)

        self._pharmacy_list_changed()

    def _get_period_script(self, table_name):
        period_script = ""

        if self.ui.radioButton_period1.isChecked():
            period_script = f' AND {table_name}.Period = "早班" '
        elif self.ui.radioButton_period2.isChecked():
            period_script = f' AND {table_name}.Period = "午班" '
        elif self.ui.radioButton_period3.isChecked():
            period_script = f' AND {table_name}.Period = "晚班" '

        return period_script

    def _read_pharmacy_list(self, charge_done_script=""):
        if charge_done_script == "未批價":
            charge_done_script = 'AND cases.ChargeDone = "False"'
        elif charge_done_script == "已批價":
            charge_done_script = 'AND cases.ChargeDone = "True"'
        else:
            charge_done_script = ""

        period_script = self._get_period_script("cases")

        period_list = str(nhi_utils.PERIOD)[1:-1]
        order_script = f"ORDER BY FIELD(cases.Period, {period_list}), cases.RegistNo"  # 預設為診號排序
        if self.system_settings.field("看診排序") == "時間排序":
            order_script = "ORDER BY cases.CaseDate"

        sql = f"""
            SELECT wait.WaitKey, cases.*, patient.Gender, patient.Birthday, patient.DiscountType
            FROM wait
                LEFT JOIN patient ON patient.PatientKey = wait.PatientKey
                LEFT JOIN cases ON cases.CaseKey = wait.CaseKey
            WHERE
                cases.DoctorDone = "True"
                {period_script}
                {charge_done_script}
            {order_script}
        """

        self.table_widget_charge_list.set_db_data(sql, self._set_table_data)

        self._pharmacy_list_changed()
        if self.table_widget_charge_list.row_count() <= 0:
            enabled = False
        else:
            enabled = True

        self.ui.action_open_medical_record.setEnabled(enabled)
        self.ui.action_print_prescription.setEnabled(enabled)
        self.ui.action_print_receipt.setEnabled(enabled)
        self.ui.action_print_misc.setEnabled(enabled)

        self._set_permission()

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        signature = case_utils.extract_security_xml(row["Security"], "醫令時間")
        ins_type = string_utils.xstr(row["InsType"])
        card = string_utils.xstr(row["Card"])
        xcard = string_utils.xstr(row["XCard"])

        if (
            ins_type != "健保"
            or card in ["欠卡"] + nhi_utils.ABNORMAL_CARD
            or xcard in nhi_utils.ABNORMAL_CARD
        ):
            ic_wrote = "略"
        elif signature is None:
            ic_wrote = "否"
        else:
            ic_wrote = "是"

        age_year, _ = date_utils.get_age(row["Birthday"], row["CaseDate"])
        if age_year is None:
            age = ""
        else:
            age = f"{age_year}歲"

        drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
        drug_share_discount_fee = charge_utils.get_drug_share_discount_fee(
            self.database, string_utils.xstr(row["DiscountType"])
        )
        if drug_share_discount_fee is not None:
            drug_share_fee = drug_share_discount_fee

        charge_status = "未批價"
        if row["ChargeDone"] == "True":
            charge_status = "已批價"

        charge_total = number_utils.get_integer(
            drug_share_fee
        ) + number_utils.get_integer(row["TotalFee"])

        wait_row = [
            string_utils.xstr(row["WaitKey"]),
            case_key,
            string_utils.xstr(row["Room"]),
            string_utils.xstr(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Gender"]),
            age,
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["TreatType"]),
            string_utils.xstr(row["Doctor"]),
            string_utils.xstr(drug_share_fee),
            string_utils.xstr(row["TotalFee"]),
            string_utils.xstr(charge_total),
            charge_status,
            ic_wrote,
        ]

        for column in range(len(wait_row)):
            self.ui.tableWidget_charge_list.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(wait_row[column])
            )
            if column in [2, 3, 11, 12, 13]:
                self.ui.tableWidget_charge_list.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [5, 14, 15]:
                self.ui.tableWidget_charge_list.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter
                )

            if (
                row["InsType"] == "自費"
                or number_utils.get_integer(row["TotalFee"]) > 0
            ):
                self.ui.tableWidget_charge_list.item(row_no, column).setForeground(
                    QtGui.QColor("blue")
                )

    def _pharmacy_list_changed(self):
        if self.ui.radioButton_unpaid.isChecked():
            enabled = True
        else:
            enabled = False

        if self.ui.tableWidget_charge_list.rowCount() <= 0:
            enabled = False
            self._clear_charge_item()

        self.ui.action_save.setEnabled(enabled)
        self.ui.action_save_without_print.setEnabled(enabled)

        case_key = self.table_widget_charge_list.field_value(1)
        self._show_medical_record(case_key)

    def _clear_charge_item(self):
        self.ui.textEdit_prescript.setHtml(None)

        self.ui.lineEdit_drug_share_fee.setText(None)
        self.ui.lineEdit_receipt_drug_share_fee.setText(None)
        self.ui.lineEdit_total_fee.setText(None)
        self.ui.lineEdit_receipt_fee.setText(None)
        self.ui.lineEdit_debt.setText(None)
        self.ui.lineEdit_total.setText(None)
        self.ui.lineEdit_discount_fee.setText(None)
        self.ui.comboBox_payment_type.setCurrentIndex(0)

        self.ui.lineEdit_regist_fee.setText(None)
        self.ui.lineEdit_diag_share_fee.setText(None)
        self.ui.lineEdit_drug_share_fee2.setText(None)
        self.ui.lineEdit_deposit_fee.setText(None)
        self.ui.lineEdit_total_fee2.setText(None)
        self.ui.lineEdit_discount_fee2.setText(None)
        self.ui.lineEdit_total2.setText(None)
        self.ui.lineEdit_receipt_fee2.setText(None)
        self.ui.lineEdit_debt2.setText(None)
        self.ui.comboBox_payment_type2.setCurrentIndex(0)

    def _show_medical_record(self, case_key):
        if case_key in [None, ""]:
            self.ui.textEdit_prescript.setHtml(None)
            return

        sql = f"""
            SELECT cases.*, patient.DiscountType FROM cases
                LEFT JOIN patient on patient.PatientKey = cases.PatientKey
            WHERE
                CaseKey = {case_key}
        """
        case_rows = self.database.select_record(sql)
        if len(case_rows) <= 0:
            return

        case_row = case_rows[0]
        if case_row["InsType"] == "健保":
            card = string_utils.xstr(case_row["Card"])
            if number_utils.get_integer(case_row["Continuance"]) >= 1:
                card += "-" + string_utils.xstr(case_row["Continuance"])
            card = f"<b>健保</b>: {card}"
        else:
            card = "<b>自費</b>"

        case_date = string_utils.xstr(case_row["CaseDate"].date())
        doctor = string_utils.xstr(case_row["Doctor"])
        payment_type = string_utils.xstr(case_row["ChargePaymentType"])
        medical_record = f"<b>日期</b>: {case_date} {card} <b>醫師</b>:{doctor}<hr>"
        remark = case_row["Remark"]
        if remark is not None and string_utils.xstr(remark) != "":
            remark = string_utils.get_str(remark, "utf8")
            medical_record += f"<b>備註</b>: {remark}<hr>"

        prescript_record = case_utils.get_prescript_record(
            self.database, self.system_settings, case_key
        )

        html = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {medical_record}
                    {prescript_record}
                </body>
            </html>
        """
        self.ui.textEdit_prescript.setHtml(html)

        s_diag_fee = number_utils.get_integer(case_row["SDiagFee"])
        s_drug_fee = number_utils.get_integer(case_row["SDrugFee"])
        s_herb_fee = number_utils.get_integer(case_row["SHerbFee"])
        s_expensive_fee = number_utils.get_integer(case_row["SExpensiveFee"])
        s_acupuncture_fee = number_utils.get_integer(case_row["SAcupunctureFee"])
        s_massage_fee = number_utils.get_integer(case_row["SMassageFee"])
        s_dislocate_fee = number_utils.get_integer(case_row["SDislocateFee"])
        s_material_fee = number_utils.get_integer(case_row["SMaterialFee"])
        s_exame_fee = number_utils.get_integer(case_row["SExamFee"])

        drug_share_fee = number_utils.get_integer(case_row["DrugShareFee"])
        s_drug_share_fee = number_utils.get_integer(case_row["SDrugShareFee"])
        drug_share_discount_fee = charge_utils.get_drug_share_discount_fee(
            self.database, string_utils.xstr(case_row["DiscountType"])
        )
        self_total_fee = number_utils.get_integer(case_row["SelfTotalFee"])
        discount_fee = number_utils.get_integer(case_row["DiscountFee"])
        total_fee = number_utils.get_integer(case_row["TotalFee"])
        receipt_fee = number_utils.get_integer(case_row["ReceiptFee"])
        discount_fee = number_utils.get_integer(case_row["DiscountFee"])

        if drug_share_discount_fee is not None:
            drug_share_fee = drug_share_discount_fee

        self.ui.lineEdit_drug_share_fee.setText(string_utils.xstr(drug_share_fee))
        # if self.ui.radioButton_paid.isChecked():
        if case_row["ChargeDone"] == "True":
            self.ui.lineEdit_receipt_drug_share_fee.setText(
                string_utils.xstr(s_drug_share_fee)
            )
        else:
            self.ui.lineEdit_receipt_drug_share_fee.setText(
                string_utils.xstr(drug_share_fee)
            )

        self.ui.lineEdit_total_fee.setText(string_utils.xstr(total_fee))
        self.ui.lineEdit_receipt_fee.setText(string_utils.xstr(receipt_fee))

        self.ui.label_fee_error.setVisible(False)
        if (
            s_diag_fee
            + s_drug_fee
            + s_herb_fee
            + s_expensive_fee
            + s_acupuncture_fee
            + s_massage_fee
            + s_dislocate_fee
            + s_material_fee
            + s_exame_fee
            != self_total_fee
        ):
            self.ui.label_fee_error.setVisible(True)
            self.ui.label_fee_error.setText("自費合計金額錯誤, 請至病歷內重新批價.")
        elif self_total_fee - discount_fee != total_fee:
            self.ui.label_fee_error.setVisible(True)
            self.ui.label_fee_error.setText("應收自費金額錯誤, 請至病歷內重新批價.")

        self.ui.lineEdit_total.setText(
            string_utils.xstr(
                number_utils.get_integer(drug_share_fee)
                + number_utils.get_integer(case_row["TotalFee"])
            )
        )
        if s_drug_share_fee == 0:
            self.ui.lineEdit_drug_share_fee.blockSignals(True)
            self.ui.lineEdit_drug_share_fee.setText(string_utils.xstr(s_drug_share_fee))
            self._calculate_total_fee()
            self.ui.lineEdit_drug_share_fee.blockSignals(False)

        self.ui.lineEdit_discount_fee.setText(string_utils.xstr(discount_fee))
        self.ui.comboBox_payment_type.setCurrentText(payment_type)

        if self.ui.radioButton_unpaid.isChecked():
            self.ui.lineEdit_receipt_drug_share_fee.setText(
                self.ui.lineEdit_drug_share_fee.text()
            )
            self.ui.lineEdit_receipt_fee.setText(self.ui.lineEdit_total_fee.text())

        self._calculate_receipt_fee()
        self._set_charge_all_fee(case_row)

    def _set_charge_all_fee(self, case_row):
        regist_fee = number_utils.get_integer(case_row["RegistFee"])
        diag_share_fee = number_utils.get_integer(case_row["SDiagShareFee"])
        drug_share_fee = number_utils.get_integer(case_row["SDrugShareFee"])
        deposit_fee = number_utils.get_integer(case_row["DepositFee"])
        self_total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee.text())
        discount_fee = number_utils.get_integer(self.ui.lineEdit_discount_fee.text())

        if self.system_settings.field("掛號收費批價進行") == "Y":
            total_fee = (
                regist_fee
                + diag_share_fee
                + drug_share_fee
                + deposit_fee
                + self_total_fee
            )
        else:
            total_fee = diag_share_fee + drug_share_fee + deposit_fee + self_total_fee

        if self.ui.radioButton_unpaid.isChecked():
            receipt_fee = total_fee
        else:
            if self.system_settings.field("掛號收費批價進行") == "Y":
                receipt_fee = (
                    number_utils.get_integer(case_row["ReceiptFee"])
                    + regist_fee
                    + diag_share_fee
                    + drug_share_fee
                )
            else:
                receipt_fee = number_utils.get_integer(case_row["ReceiptFee"])

        self.ui.lineEdit_regist_fee.setText(string_utils.xstr(regist_fee))
        self.ui.lineEdit_diag_share_fee.setText(string_utils.xstr(diag_share_fee))
        self.ui.lineEdit_drug_share_fee2.setText(string_utils.xstr(drug_share_fee))
        self.ui.lineEdit_deposit_fee.setText(string_utils.xstr(deposit_fee))
        self.ui.lineEdit_total_fee2.setText(string_utils.xstr(self_total_fee))
        self.ui.lineEdit_discount_fee2.setText(string_utils.xstr(discount_fee))
        self.ui.lineEdit_total2.setText(string_utils.xstr(total_fee))
        self.ui.lineEdit_receipt_fee2.setText(string_utils.xstr(receipt_fee))

        self.ui.label_fee_error2.setText(self.ui.label_fee_error.text())
        self.ui.label_fee_error2.setVisible(self.ui.label_fee_error.isVisible())
        self.ui.comboBox_payment_type2.setCurrentText(
            self.ui.comboBox_payment_type.currentText()
        )
        self._calculate_receipt_fee2()

    def refresh_wait(self):
        if not self.allow_refresh_wait_list:
            return

        self.read_wait()

    def _apply_charge(self):
        self.allow_refresh_wait_list = False

        sender_name = self.sender().objectName()
        wait_key = self.table_widget_charge_list.field_value(0)
        case_key = self.table_widget_charge_list.field_value(1)
        room = self.table_widget_charge_list.field_value(2)
        patient_key = self.table_widget_charge_list.field_value(3)
        patient_name = self.table_widget_charge_list.field_value(4)
        doctor = self.table_widget_charge_list.field_value(10)

        debt_message = ""
        debt_fee = number_utils.get_integer(self.ui.lineEdit_debt.text())
        if debt_fee > 0:
            debt_message = f'<font color="red"><b>此人有欠款{debt_fee}元</b></font>'

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("批價存檔")
        msg_box.setText(
            f"<font size='4' color='red'><b>確定將病患 {patient_name} 批價存檔?</b></font>"
        )
        msg_box.setInformativeText(
            f"注意！批價存檔後, 此筆資料將歸檔至已批價名單!<br>{debt_message}"
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        apply_charge = msg_box.exec_()
        if not apply_charge:
            self.allow_refresh_wait_list = True
            return

        ic_card = None
        need_write_ic_card = cshis_utils.need_write_ic_card(
            self.database, self.system_settings, case_key, "批價"
        )
        if need_write_ic_card:
            ic_card_type = case_utils.get_ic_card_type(self.database, case_key)
            if ic_card_type == "虛擬健保卡":
                ic_card = class_utils.get_vhccshis(
                    self, self.database, self.system_settings, None
                )
            else:
                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )

            if not ic_card.insert_correct_ic_card(patient_key):
                return

        self._save_records(wait_key, case_key)
        if sender_name == "action_save":  # 批價列印
            print_order = self.system_settings.field("病歷存檔列印順序")
            if print_order == "列印順序1":
                self._print_prescript(case_key)
                self._print_receipt(case_key)
                self._print_misc(case_key)
                self._print_misc2(case_key)
                self._print_misc3(case_key)
            elif print_order == "列印順序2":
                self._print_misc(case_key)
                self._print_misc2(case_key)
                self._print_misc3(case_key)
                self._print_prescript(case_key)
                self._print_receipt(case_key)
            elif print_order == "列印順序3":
                self._print_misc(case_key)
                self._print_misc2(case_key)
                self._print_misc3(case_key)
                self._print_receipt(case_key)
                self._print_prescript(case_key)
            else:
                self._print_receipt(case_key)
                self._print_misc(case_key)
                self._print_misc2(case_key)
                self._print_misc3(case_key)
                self._print_prescript(case_key)

            if self.system_settings.field("電子處方箋路徑") not in ["", None]:
                prescript_utils.save_electrical_prescript(
                    self.database, self.system_settings, case_key
                )

        if need_write_ic_card and ic_card is not None:
            ic_card.write_ic_medical_record(case_key, cshis_utils.NORMAL_CARD)

        self._send_socket_data(doctor, room)
        self.read_wait()
        self.allow_refresh_wait_list = True

    def _calculate_receipt_fee(self):
        receipt_drug_share_fee = number_utils.get_integer(
            self.ui.lineEdit_receipt_drug_share_fee.text()
        )
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())

        total_receipt_fee = receipt_drug_share_fee + receipt_fee
        total_fee = number_utils.get_integer(self.ui.lineEdit_total.text())

        if total_receipt_fee < total_fee:
            self.ui.lineEdit_debt.setText(
                string_utils.xstr(total_fee - total_receipt_fee)
            )
        else:
            self.ui.lineEdit_debt.setText(None)

    def _calculate_receipt_fee2(self):
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee2.text())
        total_fee = number_utils.get_integer(self.ui.lineEdit_total2.text())

        if receipt_fee < total_fee:
            self.ui.lineEdit_debt2.setText(string_utils.xstr(total_fee - receipt_fee))
        else:
            self.ui.lineEdit_debt2.setText(None)

    def _save_records(self, wait_key, case_key):
        self.allow_refresh_wait_list = False
        if wait_key not in ["", None]:
            self.database.exec_sql(
                f'UPDATE wait SET ChargeDone = "True" WHERE WaitKey = {wait_key}'
            )

        if case_key in ["", None]:
            return

        if self.ui.groupBox_charge_all.isVisible():
            regist_fee = number_utils.get_integer(self.ui.lineEdit_regist_fee.text())
            s_diag_share_fee = number_utils.get_integer(
                self.ui.lineEdit_diag_share_fee.text()
            )
            s_drug_share_fee = number_utils.get_integer(
                self.ui.lineEdit_drug_share_fee2.text()
            )
            total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee2.text())
            receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee2.text())

            # 自費實收不能包含掛號費跟部份負擔 (lineEdit_receipt_fee2 有包含掛號費)
            receipt_fee -= regist_fee + s_diag_share_fee + s_drug_share_fee

            debt = number_utils.get_integer(self.ui.lineEdit_debt2.text())
            payment_type = self.ui.comboBox_payment_type2.currentText()
        else:
            drug_share_fee = number_utils.get_integer(
                self.ui.lineEdit_drug_share_fee.text()
            )
            s_drug_share_fee = number_utils.get_integer(
                self.ui.lineEdit_receipt_drug_share_fee.text()
            )
            total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee.text())
            receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
            debt = number_utils.get_integer(self.ui.lineEdit_debt.text())
            payment_type = self.ui.comboBox_payment_type.currentText()

            if (
                drug_share_fee > 0 and debt > 0 and s_drug_share_fee <= 0
            ):  # 收入與欠款沖銷平衡
                s_drug_share_fee = drug_share_fee
            if total_fee > 0 and debt > 0 and receipt_fee <= 0:  # 收入與欠款沖銷平衡
                receipt_fee = total_fee

        fields = [
            "Cashier",
            "SDrugShareFee",
            "ReceiptFee",
            "ChargeDone",
            "ChargeDate",
            "ChargePeriod",
            "ChargePaymentType",
        ]
        data = [
            self.system_settings.field("使用者"),
            s_drug_share_fee,
            receipt_fee,
            "True",
            date_utils.now_to_str(),
            registration_utils.get_current_period(self.system_settings),
            payment_type,
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        if debt > 0:
            self._save_debt(debt, case_key)

    def _save_debt(self, debt, case_key):
        # rows = self.database.select_record(f'''
        #     SELECT * FROM debt
        #     WHERE
        #         CaseKey = {case_key} AND
        #         DebtType = "批價欠款"
        # ''')
        # if len(rows) > 0:  # 重複產生欠款檔
        #     return
        self.database.exec_sql(f"DELETE FROM debt WHERE CaseKey = {case_key}")

        rows = self.database.select_record(
            f"SELECT * FROM cases WHERE CaseKey = {case_key}"
        )
        if len(rows) <= 0:
            return

        row = rows[0]
        fields = [
            "CaseKey",
            "PatientKey",
            "DebtType",
            "Name",
            "CaseDate",
            "Period",
            "Doctor",
            "Fee",
        ]

        data = [
            row["CaseKey"],
            row["PatientKey"],
            "批價欠款",
            row["Name"],
            row["CaseDate"],
            row["Period"],
            row["Doctor"],
            debt,
        ]
        self.database.insert_record("debt", fields, data)

        fields = ["DebtFee"]
        data = [debt]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    # 列印處方箋
    def _print_prescript(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_prescription":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_prescription_form(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 列印醫療收據
    def _print_receipt(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_receipt":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_receipt_form(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 列印其他收據
    def _print_misc(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_misc":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_misc_form(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 列印其他收據2
    def _print_misc2(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_misc":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_misc_form2(
            self, self.database, self.system_settings, case_key, print_type
        )

    # 列印其他收據3
    def _print_misc3(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_misc":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_misc_form3(
            self, self.database, self.system_settings, case_key, print_type
        )

    def _open_medical_record(self):
        if (
            self.user_name != "超級使用者"
            and personnel_utils.get_permission(
                self.database, self.program_name, "調閱病歷", self.user_name
            )
            != "Y"
        ):
            return

        case_key = self.table_widget_charge_list.field_value(1)
        self.parent.open_medical_record(case_key, "批價作業")

    def _set_payment_type(self):
        if not self.ui.radioButton_paid.isChecked():
            return

        try:
            case_key = self.table_widget_charge_list.field_value(1)
        except Exception:
            return

        if case_key in ["", None]:
            return

        payment_type = self.ui.comboBox_payment_type.currentText()
        sql = f'''
            UPDATE cases
            SET
                ChargePaymentType = "{payment_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _set_payment_type2(self):
        if not self.ui.radioButton_paid.isChecked():
            return

        try:
            case_key = self.table_widget_charge_list.field_value(1)
        except Exception:
            return

        if case_key in ["", None]:
            return

        payment_type = self.ui.comboBox_payment_type2.currentText()
        sql = f'''
            UPDATE cases
            SET
                ChargePaymentType = "{payment_type}"
            WHERE
                CaseKey = {case_key}
        '''
        self.database.exec_sql(sql)

    def _modify_income(self):
        case_key = self.table_widget_charge_list.field_value(1)
        patient_name = self.table_widget_charge_list.field_value(4)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("批價存檔")
        msg_box.setText(
            f"<font size='4' color='red'><b>確定將病患 {patient_name} 批價修正存檔?</b></font>"
        )
        msg_box.setInformativeText("注意！實收金額若小於應收金額, 將會產生一筆欠款資料")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        apply_charge = msg_box.exec_()
        if not apply_charge:
            return

        if self.ui.groupBox_charge_all.isVisible():
            s_drug_share_fee = number_utils.get_integer(
                self.ui.lineEdit_drug_share_fee2.text()
            )
            receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee2.text())
            debt = number_utils.get_integer(self.ui.lineEdit_debt2.text())
            payment_type = self.ui.comboBox_payment_type2.currentText()
        else:
            s_drug_share_fee = number_utils.get_integer(
                self.ui.lineEdit_receipt_drug_share_fee.text()
            )
            receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
            debt = number_utils.get_integer(self.ui.lineEdit_debt.text())
            payment_type = self.ui.comboBox_payment_type.currentText()

        fields = [
            "Cashier",
            "SDrugShareFee",
            "ReceiptFee",
            "ChargeDone",
            "ChargeDate",
            "ChargePeriod",
            "ChargePaymentType",
        ]
        data = [
            self.system_settings.field("使用者"),
            s_drug_share_fee,
            receipt_fee,
            "True",
            date_utils.now_to_str(),
            registration_utils.get_current_period(self.system_settings),
            payment_type,
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

        if debt > 0:
            self._save_debt(debt, case_key)

        system_utils.show_message_box(
            QMessageBox.Information,
            "資料修正完成",
            "<h3>批價資料修正完成.</h3>",
            "完成.",
        )
        self.read_wait()

    def _calculate_total_fee(self):
        drug_share_fee = number_utils.get_integer(
            self.ui.lineEdit_drug_share_fee.text()
        )
        total_fee = number_utils.get_integer(self.ui.lineEdit_total_fee.text())

        self.ui.lineEdit_total.setText(string_utils.xstr(drug_share_fee + total_fee))

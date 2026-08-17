# 藥局作業 2024-05-20 邵秉家
# -*- coding: UTF-8 -*-

import json

from PyQt5 import QtCore, QtGui, QtWidgets

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    date_utils,
    nhi_utils,
    notification_utils,
    number_utils,
    personnel_utils,
    printer_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 藥局作業 2024-05-20 邵秉家
class Pharmacy(QtWidgets.QMainWindow):
    program_name = "藥局作業"

    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.ui = None

        self.user_name = system_utils.get_user_name(self.system_settings)
        self.notification_client = notification_utils.NotificationClient(
            self,
            database=self.database,
            station=self.program_name,
        )

        self._set_ui()
        self._set_signal()
        self._set_permission()

        self.read_wait()
        self._set_current_row()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_PHARMACY, self)
        self.table_widget_charge_list = class_utils.get_table_widget(
            self.ui.tableWidget_charge_list, self.database
        )
        self.ui.action_print_prescription.setEnabled(False)
        self.ui.action_print_receipt.setEnabled(False)
        self.ui.action_print_misc.setEnabled(False)
        self.ui.action_print_drug_bag.setEnabled(False)
        self.ui.action_broadcast.setEnabled(False)

        self.table_widget_charge_list.set_column_hidden([0, 1])

        period = registration_utils.get_current_period(self.system_settings)
        self._set_radio_button_period(period)
        self._set_font_size()
        self._set_table_width()

    def _set_font_size(self):
        font_size = 18
        self.ui.tableWidget_charge_list.setStyleSheet("font-size: 15pt;")
        self.ui.textEdit_prescript.setStyleSheet(f"font-size: {font_size}pt;")

    def _set_table_width(self):
        width = [100, 100, 60, 70, 100, 60, 70, 60, 100, 100, 70, 70, 70]
        self.table_widget_charge_list.set_table_heading_width(width)

    # 設定信號
    def _set_signal(self):
        self.ui.action_close.triggered.connect(self.close_cashier)
        self.ui.action_print_prescription.triggered.connect(
            lambda: self._print_prescript(None)
        )
        self.ui.action_print_receipt.triggered.connect(
            lambda: self._print_receipt(None)
        )
        self.ui.action_print_misc.triggered.connect(lambda: self._print_misc(None))
        self.ui.action_print_drug_bag.triggered.connect(
            lambda: self._print_prescript_bag(None)
        )
        self.ui.action_open_medical_record.triggered.connect(self._open_medical_record)
        self.ui.action_broadcast.triggered.connect(self._broadcast)

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
        self.ui.tableWidget_charge_list.doubleClicked.connect(self._open_medical_record)

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

    def _set_radio_button_period(self, period):
        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def _set_current_period(self):
        period = registration_utils.get_current_period(self.system_settings)

        if period == "早班":
            self.ui.radioButton_period1.setChecked(True)
        elif period == "午班":
            self.ui.radioButton_period2.setChecked(True)
        elif period == "晚班":
            self.ui.radioButton_period3.setChecked(True)

    def read_wait(self):
        if self.ui.radioButton_unpaid.isChecked():
            dispensing = "未調劑"
        elif self.ui.radioButton_paid.isChecked():
            dispensing = "已調劑"
        else:
            dispensing = ""

        self._read_pharmacy_list(dispensing)

        if self.ui.tableWidget_charge_list.rowCount() > 0:
            action_enabled = True
        else:
            action_enabled = False

        self.ui.action_print_prescription.setEnabled(action_enabled)
        self.ui.action_print_receipt.setEnabled(action_enabled)
        self.ui.action_print_misc.setEnabled(action_enabled)
        self.ui.action_print_drug_bag.setEnabled(action_enabled)
        self.ui.action_broadcast.setEnabled(action_enabled)

        self._pharmacy_list_changed()

        for row_no in range(self.ui.tableWidget_charge_list.rowCount()):
            check_box_drug_done = self.ui.tableWidget_charge_list.cellWidget(row_no, 11)
            if check_box_drug_done is not None and not check_box_drug_done.isChecked():
                break

    def _get_period_script(self, table_name):
        period_script = ""

        if self.ui.radioButton_period1.isChecked():
            period_script = f' AND {table_name}.Period = "早班" '
        elif self.ui.radioButton_period2.isChecked():
            period_script = f' AND {table_name}.Period = "午班" '
        elif self.ui.radioButton_period3.isChecked():
            period_script = f' AND {table_name}.Period = "晚班" '

        return period_script

    def _read_pharmacy_list(self, drug_done_script=""):
        if drug_done_script == "未調劑":
            drug_done_script = 'AND cases.DrugDone = "False"'
        elif drug_done_script == "已調劑":
            drug_done_script = 'AND cases.DrugDone = "True"'
        else:
            drug_done_script = ""

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
                LEFT JOIN prescript ON prescript.CaseKey = wait.CaseKey
            WHERE
                cases.DoctorDone = "True" AND
                prescript.MedicineType NOT IN ("穴道", "處置")
                {period_script}
                {drug_done_script}
            GROUP BY wait.CaseKey
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
        self.ui.action_print_drug_bag.setEnabled(enabled)
        self.ui.action_broadcast.setEnabled(enabled)

        self._set_permission()
        self._set_current_row()

    def _set_table_data(self, row_no, row):
        case_key = string_utils.xstr(row["CaseKey"])
        ins_type = string_utils.xstr(row["InsType"])
        card = string_utils.xstr(row["Card"])
        xcard = string_utils.xstr(row["XCard"])

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

        drug_status = "未調劑"
        if row["DrugDone"] == "True":
            drug_status = "已調劑"

        charge_total = number_utils.get_integer(
            drug_share_fee
        ) + number_utils.get_integer(row["TotalFee"])

        if row["ChargeDone"] == "True":
            charge_check = True
        else:
            charge_check = False

        if row["DrugDone"] == "True":
            check = True
        else:
            check = False

        if row["DrugPickupDone"] == "True":
            pickup_check = True
        else:
            pickup_check = False

        wait_row = [
            string_utils.xstr(row["WaitKey"]),
            case_key,
            string_utils.xstr(row["RegistNo"]),
            string_utils.xstr(row["DrugNo"]),
            string_utils.xstr(row["Name"]),
            string_utils.xstr(row["Gender"]),
            age,
            string_utils.xstr(row["InsType"]),
            string_utils.xstr(row["TreatType"])[:6],
            string_utils.xstr(row["Doctor"]),
            None,
            None,
            None,
        ]

        check_box_charge_done = QtWidgets.QCheckBox()
        check_box_charge_done.setStyleSheet("padding-left: 35px")
        check_box_charge_done.setChecked(charge_check)
        check_box_charge_done.clicked.connect(self._set_charge_done)
        self.ui.tableWidget_charge_list.setCellWidget(row_no, 10, check_box_charge_done)

        check_box_drug_done = QtWidgets.QCheckBox()
        check_box_drug_done.setStyleSheet("padding-left: 35px")
        check_box_drug_done.setChecked(check)
        check_box_drug_done.clicked.connect(self._set_drug_done)
        self.ui.tableWidget_charge_list.setCellWidget(row_no, 11, check_box_drug_done)

        check_box_drug_pickup_done = QtWidgets.QCheckBox()
        check_box_drug_pickup_done.setStyleSheet("padding-left: 35px")
        check_box_drug_pickup_done.setChecked(pickup_check)
        check_box_drug_pickup_done.clicked.connect(self._set_drug_pickup_done)
        self.ui.tableWidget_charge_list.setCellWidget(
            row_no, 12, check_box_drug_pickup_done
        )

        for column in range(len(wait_row)):
            self.ui.tableWidget_charge_list.setItem(
                row_no, column, QtWidgets.QTableWidgetItem(wait_row[column])
            )
            if column in [2, 3, 10, 11, 12]:
                self.ui.tableWidget_charge_list.item(row_no, column).setTextAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                )
            elif column in [5, 14]:
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

    def _set_charge_done(self):
        pass

    def _set_drug_done(self):
        current_row_no = self.ui.tableWidget_charge_list.currentRow()
        check_box_drug_done = self.ui.tableWidget_charge_list.cellWidget(
            current_row_no, 11
        )

        wait_key = self.table_widget_charge_list.field_value(0)
        case_key = self.table_widget_charge_list.field_value(1)

        if check_box_drug_done is not None and check_box_drug_done.isChecked():
            self._save_records(wait_key=wait_key, case_key=case_key)
        else:
            self._save_records(wait_key=wait_key, case_key=case_key, drug_done="False")

        if self.ui.radioButton_unpaid.isChecked():
            self.read_wait()

        self._send_broadcast_data()

    def _set_drug_pickup_done(self):
        current_row_no = self.ui.tableWidget_charge_list.currentRow()
        check_box_drug_pickup_done = self.ui.tableWidget_charge_list.cellWidget(
            current_row_no, 12
        )

        wait_key = self.table_widget_charge_list.field_value(0)
        case_key = self.table_widget_charge_list.field_value(1)

        if (
            check_box_drug_pickup_done is not None
            and check_box_drug_pickup_done.isChecked()
        ):
            self._save_drug_pickup_records(wait_key=wait_key, case_key=case_key)
        else:
            self._save_drug_pickup_records(
                wait_key=wait_key, case_key=case_key, drug_pickup_done="False"
            )

        if self.ui.radioButton_unpaid.isChecked():
            self.read_wait()

        self._send_broadcast_data()

    def _pharmacy_list_changed(self):
        case_key = self.table_widget_charge_list.field_value(1)
        self._show_medical_record(case_key)

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
        name = string_utils.xstr(case_row["Name"])
        doctor = string_utils.xstr(case_row["Doctor"])
        payment_type = string_utils.xstr(case_row["ChargePaymentType"])
        medical_record = f"<b>姓名:</b> {name} {card}<b>醫師</b>:{doctor}<hr>"
        remark = case_row["Remark"]
        if remark is not None and string_utils.xstr(remark) != "":
            remark = string_utils.get_str(remark, "utf8")
            medical_record += f"<b>備註</b>: {remark}<hr>"

        prescript_record = case_utils.get_prescript_record(
            self.database,
            self.system_settings,
            case_key,
            display_total_dosage=True,
            display_location=True,
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

    def refresh_wait(self):
        self._set_current_period()

        self.read_wait()
        self._set_current_row()

    def _set_current_row(self):
        self.ui.tableWidget_charge_list.itemSelectionChanged.disconnect()

        for row_no in range(self.ui.tableWidget_charge_list.rowCount()):
            self.ui.tableWidget_charge_list.setCurrentCell(row_no, 0)
            check_box_drug_done = self.ui.tableWidget_charge_list.cellWidget(row_no, 11)
            if check_box_drug_done is not None and not check_box_drug_done.isChecked():
                break

        self.ui.tableWidget_charge_list.itemSelectionChanged.connect(
            self._pharmacy_list_changed
        )

    def _save_records(self, wait_key, case_key, drug_done="True"):
        if wait_key not in ["", None]:
            self.database.exec_sql(
                f'UPDATE wait SET DrugDone = "{drug_done}" WHERE WaitKey = {wait_key}'
            )

        if case_key in ["", None]:
            return

        fields = ["DrugDone"]
        data = [drug_done]

        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def _save_drug_pickup_records(self, wait_key, case_key, drug_pickup_done="True"):
        if wait_key not in ["", None]:
            self.database.exec_sql(
                f'UPDATE wait SET DrugPickupDone = "{drug_pickup_done}" WHERE WaitKey = {wait_key}'
            )

        if case_key in ["", None]:
            return

        fields = ["DrugPickupDone"]
        data = [drug_pickup_done]

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

    # 列印藥袋
    def _print_prescript_bag(self, case_key=None):
        sender_name = self.sender().objectName()
        if sender_name == "action_print_misc":
            print_type = "選擇列印"
        else:
            print_type = "系統設定"

        if case_key is None:
            case_key = self.table_widget_charge_list.field_value(1)

        printer_utils.print_prescription_bag_form(
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

    def _get_drug_no(self):
        case_key = self.table_widget_charge_list.field_value(1)
        if case_key in [None, ""]:
            return 0

        sql = f"""
            SELECT DrugNo FROM cases
            WHERE
                CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return 0

        row = rows[0]
        return number_utils.get_integer(row["DrugNo"])

    def _broadcast(self):
        drug_no = self._get_drug_no()
        if drug_no <= 0:
            return

        voice_dict = {
            "clinic_name": self.system_settings.field("院所名稱"),
            "regist_no": self.table_widget_charge_list.field_value(2),
            "drug_no": string_utils.xstr(drug_no),
            "name": self.table_widget_charge_list.field_value(4),
            "room": 99,
            "program_name": self.program_name,
        }
        sentence = self._get_voice_sentence(voice_dict)
        voice_dict["sentence"] = sentence

        broadcast_json = json.dumps(voice_dict)
        self.notification_client.broadcast(
            notification_utils.CHANNEL_CALL_NUMBER, broadcast_json
        )

    def _get_voice_sentence(self, voice_dict=None):
        if voice_dict is None:
            voice_dict = self._get_voice_dict()

        room = voice_dict["room"]
        regist_no = voice_dict["regist_no"]
        drug_no = voice_dict["drug_no"]

        if self.system_settings.field("叫號包含病患姓名") == "Y":
            name = voice_dict["name"]
        else:
            name = ""

        # sentence = f"{drug_no}號{name}，請至領藥處領藥。"
        pharmacy = "藥局"
        if self.system_settings.field("院所名稱") == "林胤谷中醫診所":
            pharmacy = "櫃台"

        sentence = f"領藥號{drug_no}號{name}，請到{pharmacy}拿藥"

        return sentence

    def _send_broadcast_data(self):
        message = ",".join(
            [
                self.system_settings.field("院所名稱"),
                "領藥作業",
                "",
                "",
            ]
        )

        self.notification_client.send_data(message)  # 新管道：資料庫

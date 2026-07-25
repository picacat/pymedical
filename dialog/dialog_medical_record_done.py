# -*- coding: UTF-8 -*-


import datetime

from PyQt5 import QtWidgets

from libs import (
    nhi_utils,
    number_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 門診掛號 2018.01.22
class DialogMedicalRecordDone(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogMedicalRecordDone, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.case_key = args[2]
        self.done_type = args[3]
        self.ui = None

        self.done = False

        self._set_ui()
        self._set_signal()
        self._read_medical_records()

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_MEDICAL_RECORD_DONE, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("確定")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

        if self.done_type == "doctor_done":
            self.ui.groupBox_time.setTitle("完診時間")
            self.ui.label_person.setText("主治醫師")

        else:
            self.ui.groupBox_time.setTitle("批價時間")
            self.ui.label_person.setText("批價人員")

        self._set_combo_box()

    # 設定comboBox
    def _set_combo_box(self):
        if self.done_type == "doctor_done":
            script = """
                SELECT * FROM person
                WHERE
                    Position IN ("醫師", "支援醫師") AND
                    ID IS NOT NULL
                ORDER BY PersonKey
            """
        else:
            script = "SELECT * FROM person ORDER BY PersonKey"

        rows = self.database.select_record(script)
        person_list = []
        for row in rows:
            person_list.append(string_utils.xstr(row["Name"]))

        ui_utils.set_combo_box(self.ui.comboBox_person, person_list, None)
        ui_utils.set_combo_box(self.ui.comboBox_period, nhi_utils.PERIOD, None)

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.button_accepted)
        self.ui.buttonBox.rejected.connect(self.button_rejected)

    def _read_medical_records(self):
        sql = f"""
            SELECT * FROM cases
            WHERE
                CaseKey = {self.case_key}
        """
        rows = self.database.select_record(sql)

        if len(rows) <= 0:
            return

        self.row = rows[0]

        self._set_widgets()

    def _set_widgets(self):
        if self.done_type == "doctor_done":
            field = "Doctor"
        else:
            field = "Cashier"

        done_date = self.row["CaseDate"]
        done_time = datetime.time(
            self.row["CaseDate"].hour,
            self.row["CaseDate"].minute,
            self.row["CaseDate"].second,
        )

        self.ui.dateEdit_case_date.setDate(done_date)
        self.ui.timeEdit_case_time.setTime(done_time)

        period = string_utils.xstr(self.row["Period"])
        if period != "":
            self.ui.comboBox_period.setCurrentText(period)
        else:
            self.ui.comboBox_period.setCurrentText(
                registration_utils.get_current_period(self.system_settings)
            )

        person = string_utils.xstr((self.row[field]))
        if person != "":
            self.ui.comboBox_person.setCurrentText(person)
        else:
            self.ui.comboBox_person.setCurrentText(self.system_settings.field("使用者"))

        self.ui.lineEdit_total_fee.setText(string_utils.xstr(self.row["TotalFee"]))
        self.ui.lineEdit_receipt_fee.setText(string_utils.xstr(self.row["TotalFee"]))

        self.ui.lineEdit_drug_share_fee.setText(
            string_utils.xstr(self.row["DrugShareFee"])
        )
        self.ui.lineEdit_receipt_drug_share_fee.setText(
            string_utils.xstr(self.row["DrugShareFee"])
        )

    def button_accepted(self):
        if self.done_type == "doctor_done":
            self._update_doctor_done()
        else:
            self._update_charge_done()

    def button_rejected(self):
        pass

    def _update_doctor_done(self):
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
        drug_share_fee = number_utils.get_integer(
            self.ui.lineEdit_receipt_drug_share_fee.text()
        )
        date = self.ui.dateEdit_case_date.date().toString("yyyy-MM-dd")
        time = self.ui.timeEdit_case_time.time().toString("hh:mm:ss")
        period = self.ui.comboBox_period.currentText()
        doctor_date = f"{date} {time}"
        doctor = self.ui.comboBox_person.currentText()

        self.database.exec_sql(f'''
            UPDATE cases
            SET
                DoctorDate = "{doctor_date}",
                DoctorDone = "True",
                ReceiptFee = {receipt_fee},
                SDrugShareFee = {drug_share_fee}
            WHERE
                CaseKey = {self.case_key}
        ''')

        if period != "":
            self.database.exec_sql(f'''
                UPDATE cases
                SET
                    Period = "{period}"
                WHERE
                    CaseKey = {self.case_key}
            ''')
        if doctor != "":
            self.database.exec_sql(f'''
                UPDATE cases
                SET
                    Doctor = "{doctor}"
                WHERE
                    CaseKey = {self.case_key}
            ''')

    def _update_charge_done(self):
        date = self.ui.dateEdit_case_date.date().toString("yyyy-MM-dd")
        time = self.ui.timeEdit_case_time.time().toString("hh:mm:ss")
        charge_date = f"{date} {time}"
        period = self.ui.comboBox_period.currentText()
        cashier = self.ui.comboBox_person.currentText()
        receipt_fee = number_utils.get_integer(self.ui.lineEdit_receipt_fee.text())
        drug_share_fee = number_utils.get_integer(
            self.ui.lineEdit_receipt_drug_share_fee.text()
        )

        self.database.exec_sql(f'''
            UPDATE cases
            SET
                ChargeDate = "{charge_date}",
                ChargeDone = "True",
                ReceiptFee = {receipt_fee},
                SDrugShareFee = {drug_share_fee}
            WHERE
                CaseKey = {self.case_key}
        ''')

        if period != "":
            self.database.exec_sql(f'''
                UPDATE cases
                SET
                    ChargePeriod = "{period}"
                WHERE
                    CaseKey = {self.case_key}
            ''')
        if cashier != "":
            self.database.exec_sql(f'''
                UPDATE cases
                SET
                    Cashier = "{cashier}"
                WHERE
                    CaseKey = {self.case_key}
            ''')

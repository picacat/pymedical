# 病歷查詢 2014.09.22
# -*- coding: UTF-8 -*-

import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    case_utils,
    class_utils,
    cshis_utils,
    date_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 還卡對話框
class DialogReturnCard(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super(DialogReturnCard, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.deposit_key = args[2]
        self.case_key = args[3]
        self.patient_key = args[4]
        self.ui = None
        self.ic_card = None
        self.doctor_done = False

        self._set_ui()
        self._set_signal()
        self._read_data()
        try:
            self.user_name = self.parent.parent.user_name
        except Exception:
            self.user_name = self.system_settings.field("使用者")

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_RETURN_CARD, self)
        self.setFixedSize(self.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self._set_combo_box()
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("還卡")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    # 設定comboBox
    def _set_combo_box(self):
        ui_utils.set_combo_box(self.ui.comboBox_return_period, nhi_utils.PERIOD)
        ui_utils.set_combo_box(self.ui.comboBox_continuance, nhi_utils.COURSE, None)
        ui_utils.set_combo_box(self.ui.comboBox_share_type, nhi_utils.SHARE_TYPE, None)
        ui_utils.set_combo_box(self.ui.comboBox_treat_type, nhi_utils.TREAT_TYPE, None)
        ui_utils.set_combo_box(
            self.ui.comboBox_card, nhi_utils.ABNORMAL_CARD_WITH_HINT, "自動產生"
        )

    # 讀取資料
    def _read_data(self):
        sql = f'''
            SELECT
                deposit.*,
                cases.Card, cases.Continuance, cases.Share, cases.DiagShareFee, cases.DoctorDone, cases.Share,
                cases.TreatType,
                patient.Birthday, patient.ID, patient.CardNo, patient.InsType
            FROM deposit
                LEFT JOIN cases ON cases.CaseKey = deposit.CaseKey
                LEFT JOIN patient ON patient.PatientKey = deposit.PatientKey
            WHERE
                deposit.CaseKey = "{self.case_key}"
            ORDER BY DepositDate DESC
        '''
        row = self.database.select_record(sql)[0]

        patient_key = row["PatientKey"]
        patient_share = string_utils.xstr(row["InsType"])

        if patient_share == "健保":
            patient_share = "基層醫療"

        if string_utils.xstr(row["DoctorDone"]) == "True":
            self.doctor_done = True

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(patient_key))
        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row["Birthday"]))
        self.ui.lineEdit_id.setText(string_utils.xstr(row["ID"]))
        self.ui.lineEdit_patient_share.setText(patient_share)
        self.ui.lineEdit_card_no.setText(string_utils.xstr(row["CardNo"]))

        return_date = date_utils.now_to_str()
        period = registration_utils.get_current_period(self.system_settings)
        self.ui.lineEdit_return_date.setText(return_date)
        self.ui.comboBox_return_period.setCurrentText(period)
        self.ui.spinBox_return_fee.setValue(number_utils.get_integer(row["Fee"]))

        course = number_utils.get_integer(row["Continuance"])
        self.ui.comboBox_continuance.setCurrentText(string_utils.xstr(course))
        self.ui.comboBox_share_type.setCurrentText(string_utils.xstr(row["Share"]))
        self.ui.comboBox_treat_type.setCurrentText(string_utils.xstr(row["TreatType"]))
        if course <= 1:
            card = "自動產生"
        else:
            card = self._get_card(patient_key)

        self.ui.comboBox_card.setCurrentText(card)

        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if self.ui.comboBox_treat_type.currentText() in nhi_utils.HOME_CARE:
            card_sequence = nhi_utils.get_home_care_card(
                self.database, patient_key, today
            )
            if card_sequence is not None and card_sequence[:4] in ["F000"]:
                card_sequence = "自動取得"

            self.ui.comboBox_card.setCurrentText(card_sequence)

    def _get_card(self, patient_key):
        card = ""

        sql = f"""
            SELECT Card FROM cases
            WHERE
                PatientKey = {patient_key} AND
                InsType = "健保" AND
                Continuance = 1
            ORDER BY CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return card

        card = string_utils.xstr(rows[0]["Card"])

        return card

    # 還卡
    def accepted_button_clicked(self):
        card = string_utils.xstr(self.ui.comboBox_card.currentText()).split(" ")[0]
        card_no = string_utils.xstr(self.ui.lineEdit_card_no.text())

        if card in nhi_utils.ABNORMAL_CARD:
            self.update_cases_by_manual_card(card)
            self.update_wait_by_manual_card(card)
        else:
            if card_no == "":
                self._write_patient()

            ic_card = self._write_ic_card(cshis_utils.RETURN_CARD)
            if not ic_card:
                system_utils.show_message_box(
                    QtWidgets.QMessageBox.Critical,
                    "讀卡失敗",
                    """
                        <font size="5" color="red">
                            <b>寫卡失敗, 無法執行健保卡就醫資料寫入作業.</b>
                        </font>
                    """,
                    "請確定插入的健保卡是否正確後, 再執行一次",
                )
                return

            if ic_card is None:
                return

            self.update_cases_by_ic_card(ic_card, card)
            self.update_wait_by_ic_card(ic_card, card)

            if self.doctor_done:
                if self.system_settings.field("讀卡機控制軟體版本") == "cshis6":
                    ic_card.write_ic_medical_record(
                        self.case_key, cshis_utils.NORMAL_CARD, reset_vhc_card=False
                    )
                else:
                    ic_card.write_ic_medical_record(
                        self.case_key, cshis_utils.RETURN_CARD
                    )

        self.update_return_card()
        self.update_medical_record()

    def _write_patient(self):
        ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
        if not ic_card.read_basic_data():
            return

        patient_key = self.ui.lineEdit_patient_key.text()
        card_no = ic_card.basic_data["card_no"]

        sql = f'''
            UPDATE patient
            SET
                CardNo = "{card_no}"
            WHERE
                PatientKey = {patient_key}
        '''
        self.database.exec_sql(sql)

    def _write_ic_card(self, treat_after_check):
        patient_key = self.ui.lineEdit_patient_key.text()
        card = self.ui.comboBox_card.currentText()
        today = datetime.datetime.now().strftime("%Y-%m-%d")

        if (
            self.ui.comboBox_treat_type.currentText() == "居家醫療"
            and card != "自動取得"
        ):
            treat_type = "居家醫療"
        else:
            treat_type = None

        if self.ui.groupBox_use_vhc_card.isChecked():
            if self.ui.radioButton_qrcode.isChecked():
                qrcode = None
            else:
                patient_id = patient_utils.get_patient_id(self.database, patient_key)
                ic_card = class_utils.get_cshis(
                    self, self.database, self.system_settings
                )
                req_code = ic_card.request_token(patient_id)
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("取得病患授權")
                msg_box.setText(
                    """
                    <font size="5" color="blue">
                    <b>請問病患是否已在健保快易通授權?<br>
                    </font>
                    """
                )
                msg_box.setInformativeText("取得虛擬健保卡授權")
                msg_box.addButton(QPushButton("尚未取得"), QMessageBox.NoRole)
                msg_box.addButton(QPushButton("病患已經授權"), QMessageBox.YesRole)
                get_response = msg_box.exec_()
                if not get_response:
                    return

                qrcode = ic_card.get_response_token(req_code)
                if qrcode is None:
                    system_utils.show_message_box(
                        QMessageBox.Critical,
                        "無法寫卡",
                        '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                        "請重新取得授權.",
                    )
                    return

            ic_card = class_utils.get_vhccshis(
                self, self.database, self.system_settings, qrcode
            )
            use_vhc_card = True
        else:
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
            use_vhc_card = False

            available_date, available_count = ic_card.get_card_status()
            if available_count is None:
                return False

            if available_count <= 0 or available_date < today:
                ic_card.update_hc(False)

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            patient_key,
            self.ui.comboBox_continuance.currentText(),
            self.ui.comboBox_share_type.currentText(),
            treat_after_check,
            treat_type=treat_type,
        )

        if not ic_card_ok:
            return False

        if use_vhc_card:
            case_utils.set_case_extend(
                self.database, self.case_key, "健保卡種類", "虛擬健保卡"
            )

        return ic_card

    def update_cases_by_ic_card(self, ic_card, card=None):
        if ic_card is None:
            return

        fields = [
            "Card",
            "Security",
        ]

        security = case_utils.treat_data_to_xml(ic_card.treat_data)

        treat_after_check = "2"
        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )
        security = case_utils.update_xml_doc(
            security, "prescript_sign_time", date_utils.now_to_str()
        )
        security = case_utils.update_xml_doc(security, "upload_type", "1")

        if card in [None, "", "自動產生", "欠卡"]:
            card = ic_card.treat_data["seq_number"]
            self.database.exec_sql(
                f'UPDATE cases SET Card = "{card}" WHERE CaseKey = {self.case_key}'
            )

        data = [
            card,
            security,
        ]
        self.database.update_record("cases", fields, "CaseKey", self.case_key, data)

    def update_cases_by_manual_card(self, card):
        self.database.exec_sql(f'''
            UPDATE cases
            SET
                Card = "{card}"
            WHERE
                CaseKey = {self.case_key}
        ''')

        upload_type = "2"  # 異常卡序
        case_utils.update_xml(
            self.database,
            "cases",
            "Security",
            "upload_type",
            upload_type,
            "CaseKey",
            self.case_key,
        )

    def update_wait_by_ic_card(self, ic_card, card=None):
        if ic_card is None:
            return

        if card in ["", None, "自動產生"]:
            card = ic_card.treat_data["seq_number"]

        sql = f'''
            UPDATE wait
            SET
                Card = "{card}"
            WHERE
                CaseKey = {self.case_key}
        '''
        self.database.exec_sql(sql)

    def update_wait_by_manual_card(self, card):
        self.database.exec_sql(f'''
            UPDATE wait
            SET
                Card = "{card}"
            WHERE
                CaseKey = {self.case_key}
        ''')

    def update_return_card(self):
        fields = ["ReturnDate", "Period", "Refunder"]
        data = [
            self.ui.lineEdit_return_date.text(),
            self.ui.comboBox_return_period.currentText(),
            self.user_name,
        ]
        self.database.update_record(
            "deposit", fields, "DepositKey", self.deposit_key, data
        )

    def update_medical_record(self):
        fields = ["RefundFee"]
        data = [self.ui.spinBox_return_fee.value()]

        self.database.update_record("cases", fields, "CaseKey", self.case_key, data)

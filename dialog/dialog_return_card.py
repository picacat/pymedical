# 還卡對話框 2026-09-11
# -*- coding: UTF-8 -*-
#
# 修正重點:
#   1. 斷開 .ui 內建的 accepted -> accept(), 失敗時對話框不再關閉(呼叫端才不會誤判成功)
#   2. 卡序一取得就先落地(只寫 Card 一個欄位), Security / 就醫資料寫入失敗都不再連累卡序
#   3. Security 改用參數化寫入, XML 內的引號不會再讓整筆 UPDATE 失敗
#   4. _read_data 改用 DepositKey 查詢(原本用 CaseKey 取第一筆, 多筆 deposit 會讀到別筆)
#   5. 療程卡序 _get_card 加上就診日上界, 並排除「欠卡 / 自動產生 / 空白」等非正式卡序
#   6. 居家醫療改用本筆的就診日查詢, 並修掉 setCurrentText(None) 的 TypeError
#   7. 寫入前重新確認 cases.Card 仍是欠卡, 避免多站台重複還卡多耗一個卡序
#   8. 插卡確認身分證相符才回寫 patient.CardNo; 讀卡機只開一次
#
# 註: 本檔案的寫入動作使用 database.exec_sql(sql, params) 的參數化形式.

import datetime
import os

from PyQt5 import QtCore, QtWidgets
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

# 視為「尚未取得正式卡序」的欄位值, cases 與 wait 兩邊共用同一份
CARD_PLACEHOLDER = (None, "", "自動產生", "自動取得", "欠卡")

# 寫卡成功但資料庫寫入失敗時的補救記錄
CARD_SEQUENCE_LOG = "return_card.log"


# 還卡對話框
class DialogReturnCard(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.deposit_key = args[2]
        self.case_key = args[3]
        self.patient_key = args[4]
        self.ui = None
        self.ic_card = None
        self.doctor_done = False
        self.use_vhc_card = False

        self.case_date = None  # 本筆病歷的就診日(欠卡日), 不是今天
        self.course = 0
        self.course_card_missing = False  # 療程找不到首次卡序
        self.data_ok = False

        self.user_name = self._get_user_name()

        self._set_ui()
        self._set_signal()
        self.data_ok = self._read_data()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 取得經手人: 優先用呼叫端(欠還卡作業)已經算好的登入者
    def _get_user_name(self):
        user_name = getattr(self.parent, "user_name", None)

        if not user_name:
            try:
                user_name = system_utils.get_user_name(self.system_settings)
            except Exception:
                user_name = self.system_settings.field("使用者")

        return string_utils.xstr(user_name)

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
        # .ui 內建的 accepted -> accept() 會讓「還卡失敗」的對話框照樣以 Accepted 關閉,
        # 呼叫端的 if dialog.exec_(): 就會誤判成功. 先全部斷開,
        # 改由 accepted_button_clicked 自行決定要不要 accept().
        try:
            self.ui.buttonBox.accepted.disconnect()
        except TypeError:
            pass

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
        deposit_key = number_utils.get_integer(self.deposit_key)

        sql = f"""
            SELECT
                deposit.*,
                cases.CaseDate, cases.Card, cases.Continuance, cases.Share,
                cases.DiagShareFee, cases.DoctorDone, cases.TreatType,
                patient.Birthday, patient.ID, patient.CardNo, patient.InsType
            FROM deposit
                LEFT JOIN cases ON cases.CaseKey = deposit.CaseKey
                LEFT JOIN patient ON patient.PatientKey = deposit.PatientKey
            WHERE
                deposit.DepositKey = {deposit_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "找不到欠卡資料",
                '<font size="5" color="red"><b>找不到這筆欠卡資料, 無法執行還卡作業.</b></font>',
                "請重新整理欠還卡名單後再試一次.",
            )
            QtCore.QTimer.singleShot(0, self.reject)
            return False

        row = rows[0]

        # 以資料庫的內容為準, 避免呼叫端傳進來的 key 與實際列不一致
        self.case_key = number_utils.get_integer(row["CaseKey"])
        self.patient_key = row["PatientKey"]
        self.case_date = self._get_case_date(row)

        patient_share = string_utils.xstr(row["InsType"])
        if patient_share == "健保":
            patient_share = "基層醫療"

        if string_utils.xstr(row["DoctorDone"]) == "True":
            self.doctor_done = True

        self.ui.lineEdit_patient_key.setText(string_utils.xstr(self.patient_key))
        self.ui.lineEdit_name.setText(string_utils.xstr(row["Name"]))
        self.ui.lineEdit_birthday.setText(string_utils.xstr(row["Birthday"]))
        self.ui.lineEdit_id.setText(string_utils.xstr(row["ID"]))
        self.ui.lineEdit_patient_share.setText(patient_share)
        self.ui.lineEdit_card_no.setText(string_utils.xstr(row["CardNo"]))

        self.ui.lineEdit_return_date.setText(date_utils.now_to_str())
        self.ui.comboBox_return_period.setCurrentText(
            registration_utils.get_current_period(self.system_settings)
        )
        self.ui.spinBox_return_fee.setValue(number_utils.get_integer(row["Fee"]))

        self.course = number_utils.get_integer(row["Continuance"])
        if self.course >= 1:
            self.ui.comboBox_continuance.setCurrentText(string_utils.xstr(self.course))

        self.ui.comboBox_share_type.setCurrentText(string_utils.xstr(row["Share"]))
        self.ui.comboBox_treat_type.setCurrentText(string_utils.xstr(row["TreatType"]))

        self._set_card_sequence()

        return True

    # 本筆病歷的就診日: 沒有 CaseDate 就退而求其次用欠卡日期
    def _get_case_date(self, row):
        case_date = row["CaseDate"]
        if case_date is None:
            case_date = row["DepositDate"]

        if case_date is None:
            return datetime.datetime.now().strftime("%Y-%m-%d")

        return case_date.strftime("%Y-%m-%d")

    # 決定預設卡序
    def _set_card_sequence(self):
        if self.course <= 1:
            card = "自動產生"
        else:
            card = self._get_card(self.patient_key, self.case_date)
            if card == "":
                # 療程 2~6 診應沿用首次的卡序, 找不到就標記起來, 送出前再提醒
                self.course_card_missing = True
                card = "自動產生"

        self.ui.comboBox_card.setCurrentText(card)

        treat_type = string_utils.xstr(self.ui.comboBox_treat_type.currentText())
        if treat_type not in nhi_utils.HOME_CARE:
            return

        # 居家醫療要用本筆的就診日去查, 不是還卡當天(跨月還卡會查到別的月份)
        card_sequence = string_utils.xstr(
            nhi_utils.get_home_care_card(
                self.database, self.patient_key, self.case_date
            )
        )
        if card_sequence.startswith("F000"):
            card_sequence = "自動取得"

        if card_sequence != "":  # xstr(None) 會是空字串, 不能直接餵給 setCurrentText
            self.ui.comboBox_card.setCurrentText(card_sequence)

    # 療程 2~6 診沿用首次的卡序: 只找本筆就診日(含)以前、而且已經有正式卡序的那一筆
    def _get_card(self, patient_key, case_date):
        exclude = ", ".join([f'"{i}"' for i in CARD_PLACEHOLDER if i])

        sql = f'''
            SELECT Card FROM cases
            WHERE
                PatientKey = {patient_key} AND
                InsType = "健保" AND
                Continuance = 1 AND
                CaseDate <= "{case_date} 23:59:59" AND
                Card IS NOT NULL AND
                Card != "" AND
                Card NOT IN ({exclude})
            ORDER BY CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return ""

        return string_utils.xstr(rows[0]["Card"])

    # 送出前重新確認這筆病歷還是欠卡狀態(其他站台可能已經還過了)
    def _check_still_deposit(self):
        sql = f"SELECT Card FROM cases WHERE CaseKey = {self.case_key}"
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return True

        card = string_utils.xstr(rows[0]["Card"])
        if card in CARD_PLACEHOLDER:
            return True

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("可能已經還過卡")
        msg_box.setText(
            f"""
            <font size="5" color="red">
              <b>這筆病歷的卡序已經是 {card}, 可能已由其他站台完成還卡.<br>
            </font>
            """
        )
        msg_box.setInformativeText("繼續還卡會再向健保署取得一個新的卡序.")
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("仍要還卡"), QMessageBox.YesRole)

        return bool(msg_box.exec_())

    # 療程找不到首次卡序時的確認
    def _confirm_course_card(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("找不到療程首次卡序")
        msg_box.setText(
            f"""
            <font size="5" color="red">
              <b>這是療程第 {self.course} 次, 但是找不到首次看診的卡序.<br>
            </font>
            """
        )
        msg_box.setInformativeText(
            "繼續還卡會取得一個新的卡序, 與療程首次不同, 申報時可能被核刪."
        )
        msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
        msg_box.addButton(QPushButton("仍要還卡"), QMessageBox.YesRole)

        return bool(msg_box.exec_())

    # 還卡
    def accepted_button_clicked(self):
        if not self.data_ok:
            return

        if not self._check_still_deposit():
            return

        if self.course_card_missing and not self._confirm_course_card():
            return

        card = string_utils.xstr(self.ui.comboBox_card.currentText()).split(" ")[0]
        card_no = string_utils.xstr(self.ui.lineEdit_card_no.text())

        if card in nhi_utils.ABNORMAL_CARD:
            self.update_cases_by_manual_card(card)
            self.update_wait_by_manual_card(card)
        else:
            ic_card = self._write_ic_card(cshis_utils.RETURN_CARD, card_no)

            if ic_card is None:  # 使用者自行取消, 不必再報錯
                return

            if not ic_card:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "讀卡失敗",
                    """
                        <font size="5" color="red">
                            <b>寫卡失敗, 無法執行健保卡就醫資料寫入作業.</b>
                        </font>
                    """,
                    "請確定插入的健保卡是否正確後, 再執行一次",
                )
                return

            # 卡序一到手就先落地, 只寫 Card 一個欄位, 不牽扯任何其他作業
            card = self._save_card_sequence(ic_card, card)

            # 後續作業失敗都不能再影響已經寫好的卡序
            try:
                self._update_case_security(ic_card)
                self._write_ic_medical_record(ic_card)
            except Exception as e:
                system_utils.show_message_box(
                    QMessageBox.Warning,
                    "還卡部分完成",
                    f"""
                        <font size="5" color="red">
                            <b>卡序 {card} 已經寫入病歷, 但是後續作業失敗.</b>
                        </font>
                    """,
                    f"病歷號 {self.case_key}: {string_utils.xstr(e)}",
                )

        self.update_return_card()
        self.update_medical_record()
        self.accept()

    # 插卡確認: 只有在 patient.CardNo 空白時才回寫, 且身分證必須相符
    def _check_patient_card(self, ic_card, card_no):
        if card_no != "":
            return True

        if not ic_card.read_basic_data():
            return True  # 讀不到基本資料就跳過, 交給後面的寫卡流程去報錯

        basic_data = ic_card.basic_data
        card_id = string_utils.xstr(basic_data.get("id"))
        patient_id = string_utils.xstr(self.ui.lineEdit_id.text())

        if patient_id != "" and card_id != "" and card_id != patient_id:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "健保卡與病歷不符",
                f"""
                    <font size="5" color="red">
                        <b>健保卡的身分證字號 {card_id} 與病歷的 {patient_id} 不符.</b>
                    </font>
                """,
                "請確認插入的健保卡是否為本人的卡片.",
            )
            return False

        self.database.exec_sql(
            "UPDATE patient SET CardNo = %s WHERE PatientKey = %s",
            (string_utils.xstr(basic_data.get("card_no")), self.patient_key),
        )

        return True

    # 取得虛擬健保卡物件: 回傳物件 = 成功, None = 使用者取消, False = 失敗
    def _get_vhc_card(self):
        if self.ui.radioButton_qrcode.isChecked():
            qrcode = None
        else:
            patient_id = patient_utils.get_patient_id(self.database, self.patient_key)
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
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
            if not msg_box.exec_():
                return None  # 使用者取消

            qrcode = ic_card.get_response_token(req_code)
            if qrcode is None:
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "無法寫卡",
                    '<font size="5" color="red"><b>無法使用虛擬健保卡寫卡, 無法取得授權.</b></font>',
                    "請重新取得授權.",
                )
                return False

        return class_utils.get_vhccshis(
            self, self.database, self.system_settings, qrcode
        )

    # 寫卡: 回傳 ic_card 物件 = 成功, None = 使用者取消, False = 失敗
    def _write_ic_card(self, treat_after_check, card_no=""):
        card = string_utils.xstr(self.ui.comboBox_card.currentText())
        treat_type_text = string_utils.xstr(self.ui.comboBox_treat_type.currentText())

        if treat_type_text in nhi_utils.HOME_CARE and card != "自動取得":
            treat_type = treat_type_text
        else:
            treat_type = None

        if self.ui.groupBox_use_vhc_card.isChecked():
            ic_card = self._get_vhc_card()
            if ic_card is None:
                return None
            if not ic_card:
                return False

            self.use_vhc_card = True
        else:
            # 讀卡機只開一次, 基本資料與寫卡共用同一個物件
            ic_card = class_utils.get_cshis(self, self.database, self.system_settings)
            self.use_vhc_card = False

            if not self._check_patient_card(ic_card, card_no):
                return None  # 卡片與病歷不符, 已經報過錯了

            available_date, available_count = ic_card.get_card_status()
            if available_count is None:
                return False

            today = datetime.datetime.now().strftime("%Y-%m-%d")
            if available_count <= 0 or string_utils.xstr(available_date) < today:
                ic_card.update_hc(False)

        ic_card_ok = ic_card.write_ic_card(
            "掛號寫卡",
            self.patient_key,
            self.ui.comboBox_continuance.currentText(),
            self.ui.comboBox_share_type.currentText(),
            treat_after_check,
            treat_type=treat_type,
        )
        if not ic_card_ok:
            return False

        self.ic_card = ic_card

        return ic_card

    # 取出卡序
    def _get_seq_number(self, ic_card):
        try:
            return string_utils.xstr(ic_card.treat_data["seq_number"])
        except Exception:
            return ""

    # 寫卡成功後的第一件事: 把卡序落地, 只動 Card 欄位
    def _save_card_sequence(self, ic_card, card):
        seq_number = self._get_seq_number(ic_card)

        if card in CARD_PLACEHOLDER:
            card = seq_number

        self._log_card_sequence(card, seq_number)  # 先留底, 資料庫失敗還補得回來

        if card == "":
            system_utils.show_message_box(
                QMessageBox.Warning,
                "取不到卡序",
                '<font size="5" color="red"><b>健保卡寫卡成功, 但是取不到卡序.</b></font>',
                f"請記下病歷號 {self.case_key}, 由人工補登卡序.",
            )
            return card

        self.database.exec_sql(
            "UPDATE cases SET Card = %s WHERE CaseKey = %s", (card, self.case_key)
        )
        self.database.exec_sql(
            "UPDATE wait SET Card = %s WHERE CaseKey = %s", (card, self.case_key)
        )

        return card

    # 卡序留底
    def _log_card_sequence(self, card, seq_number):
        try:
            log_file = os.path.join(os.getcwd(), CARD_SEQUENCE_LOG)
            with open(log_file, "a", encoding="utf8") as f:
                f.write(
                    f"{date_utils.now_to_str()}\tCaseKey={self.case_key}\tDepositKey={self.deposit_key}\tCard={card}\tSeq={seq_number}\t{self.user_name}\n"
                )
        except Exception:
            pass

    # 更新健保安全簽章
    def _update_case_security(self, ic_card):
        security = case_utils.treat_data_to_xml(ic_card.treat_data)
        security = case_utils.update_xml_doc(security, "treat_after_check", "2")
        security = case_utils.update_xml_doc(
            security, "prescript_sign_time", date_utils.now_to_str()
        )
        security = case_utils.update_xml_doc(security, "upload_type", "1")

        # XML 內含引號時字串拼接的 SQL 會整筆失敗, 改用參數化
        self.database.exec_sql(
            "UPDATE cases SET Security = %s WHERE CaseKey = %s",
            (security, self.case_key),
        )

        if self.use_vhc_card:
            case_utils.set_case_extend(
                self.database, self.case_key, "健保卡種類", "虛擬健保卡"
            )

    # 健保卡就醫資料寫入
    def _write_ic_medical_record(self, ic_card):
        if not self.doctor_done:
            return

        if self.system_settings.field("讀卡機控制軟體版本") == "cshis6":
            ic_card.write_ic_medical_record(
                self.case_key, cshis_utils.NORMAL_CARD, reset_vhc_card=False
            )
        else:
            ic_card.write_ic_medical_record(self.case_key, cshis_utils.RETURN_CARD)

    # 保留給外部呼叫: 先落地卡序, 再更新安全簽章
    def update_cases_by_ic_card(self, ic_card, card=None):
        if ic_card is None:
            return

        self._save_card_sequence(ic_card, card)
        self._update_case_security(ic_card)

    def update_cases_by_manual_card(self, card):
        self.database.exec_sql(
            "UPDATE cases SET Card = %s WHERE CaseKey = %s", (card, self.case_key)
        )

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

        if card in CARD_PLACEHOLDER:
            card = self._get_seq_number(ic_card)

        if card == "":
            return

        self.database.exec_sql(
            "UPDATE wait SET Card = %s WHERE CaseKey = %s", (card, self.case_key)
        )

    def update_wait_by_manual_card(self, card):
        self.database.exec_sql(
            "UPDATE wait SET Card = %s WHERE CaseKey = %s", (card, self.case_key)
        )

    def update_return_card(self):
        return_date = string_utils.xstr(self.ui.lineEdit_return_date.text())
        if return_date == "":
            return_date = date_utils.now_to_str()

        fields = ["ReturnDate", "Period", "Refunder"]
        data = [
            return_date,
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

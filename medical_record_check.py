# -*- coding: UTF-8 -*-


import datetime
from queue import Queue
from threading import Thread

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QPushButton

from libs import (
    case_utils,
    date_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    prescript_utils,
    registration_utils,
    string_utils,
    system_utils,
)


# 存檔前檢查 2018.03.19
class MedicalRecordCheck(QtWidgets.QDialog):
    # 初始化
    def __init__(self, parent=None, **kwargs):
        super(MedicalRecordCheck, self).__init__(parent)
        self.parent = parent
        self.database = kwargs["database"]
        self.system_settings = kwargs["system_settings"]
        self.call_from = kwargs["call_from"]
        self.medical_record = kwargs["medical_record"]
        self.patient_record = kwargs["patient_record"]
        self.treat_type = kwargs["treat_type"]
        self.card = kwargs["card"]
        self.course = kwargs["course"]
        self.disease_code1 = kwargs["disease_code1"]
        self.disease_code2 = kwargs["disease_code2"]
        self.disease_code3 = kwargs["disease_code3"]
        self.disease_code4 = kwargs["disease_code4"]
        self.special_code = kwargs["special_code"]
        self.treatment = kwargs["treatment"]
        self.second_treatment = kwargs["second_treatment"]
        self.pres_days = kwargs["pres_days"]
        self.packages = kwargs["packages"]
        self.instruction = kwargs["instruction"]
        self.table_widget_ins_prescript = kwargs["table_widget_ins_prescript"]
        self.table_widget_ins_treat = kwargs["table_widget_ins_treat"]
        self.table_widget_ins_care = kwargs["table_widget_ins_care"]
        self.symptom = kwargs["symptom"]
        self.tongue = kwargs["tongue"]
        self.pulse = kwargs["pulse"]
        self.distinguish = kwargs["distinguish"]
        self.cure = kwargs["cure"]
        self.integrate_care = kwargs["integrate_care"]
        try:
            self.no_pharmacy = kwargs["no_pharmacy"]
        except Exception:
            self.no_pharmacy = "N"

        try:
            self.ins_apply_fee = kwargs["ins_apply_fee"]
        except Exception:
            self.ins_apply_fee = None

        try:
            self.deposit_fee = kwargs["deposit_fee"]
        except Exception:
            self.deposit_fee = None

        self._set_ui()
        self._set_signal()

    # 設定GUI
    def _set_ui(self):
        pass

    # 設定信號
    def _set_signal(self):
        pass

    def _get_card(self):
        try:
            card = self.parent.tab_registration.comboBox_card.currentText().split(" ")[
                0
            ]
        except Exception:
            card = string_utils.xstr(self.medical_record["Card"])

        return card

    def _get_total_medicine_set(self):
        case_key = self.medical_record["CaseKey"]

        sql = f"""
            SELECT MedicineSet FROM prescript
            WHERE
              CaseKey = {case_key} AND
              MedicineSet >= 1
            GROUP BY MedicineSet
        """
        rows = self.database.select_record(sql)

        return len(rows)

    def check_medical_record(self):
        if self.patient_record is None:  # 無病患資料不檢查
            return True

        if self.treat_type in nhi_utils.BRAIN_CARE_TREAT:
            check_ok = self._check_brain()
        elif self.treat_type == "助孕照護":
            check_ok = self._check_aid_pregnant_care()
        elif self.treat_type == "保胎照護":
            check_ok = self._check_keep_baby_care()
        elif self.treat_type in nhi_utils.CANCER_CARE_TREAT:
            check_ok = self._check_cancer_care()
        elif self.treat_type == "慢性腎病照護":
            check_ok = self._check_ckd()
        elif self.treat_type == "兒童鼻炎":
            check_ok = self._check_child_rhinitis()
        elif self.treat_type in nhi_utils.CHILD_CARE_TREAT:
            check_ok = self._check_child_care()
        else:
            check_ok = self._check_general()

        # regist_type = self.parent.tab_registration.comboBox_reg_type.currentText()
        # if regist_type in nhi_utils.SPECIAL_PHARMACY_TYPE:
        #     check_ok = self._check_special_pharmacy_type(regist_type)

        return check_ok

    # 檢查主診斷碼
    def _check_disease1_error(self, treat_type, disease_code1, disease_code2=None):
        error_message = None

        if treat_type == "腦血管疾病":
            if "G450" <= self.disease_code1[:4] <= "G468":
                pass
            elif "I60" <= self.disease_code1[:3] <= "I69":
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非腦血管疾病<br>腦血管疾病範圍範圍: G450~G468, I60~I69"
        elif treat_type == "助孕照護":
            if "N970" <= self.disease_code1[:4] <= "N979":  # 女性不孕症
                pass
            elif "N460" <= self.disease_code1[:4] <= "N469":  # 男性不孕症
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非不孕症<br>女性不孕症主診斷碼範圍: N970 ~ N979<br>男性不孕症主診斷碼範圍: N4601 ~ N469"
        elif treat_type == "小兒氣喘":
            if disease_code1[:3] == "J45":  #
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非小兒氣喘病名<br>小兒氣喘主診斷碼範圍: J45~"
                )
        elif treat_type == "小兒腦性麻痺":
            if disease_code1[:3] == "G80":  #
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非小兒腦性麻痺病名<br>小兒腦性麻痺主診斷碼範圍: G80~"
        elif treat_type == "特定癌症照護":
            if disease_code1[:3] in [
                "C18",
                "C19",
                "C20",
                "C21",
                "C22",
                "C23",
                "C24",
                "C33",
                "C34",
                "C50",
            ]:
                pass
            elif disease_code1 == "C7981":
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非特定癌症病名<br>癌症主診斷碼範圍: C18~C24, C33~C34, C7981<br>"
        elif treat_type == "乳癌照護":
            if nhi_utils.is_breast_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(disease_code1) and nhi_utils.is_breast_cancer(
                disease_code2
            ):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非乳癌病名<br>乳癌主診斷碼範圍: C50~, C7981<br>"
                )
        elif treat_type == "肝癌照護":
            if nhi_utils.is_liver_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(disease_code1) and nhi_utils.is_liver_cancer(
                disease_code2
            ):
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非肝癌病名<br>肝癌主診斷碼範圍: C22~, C23~, C24~<br>"
        elif treat_type == "肺癌照護":
            if nhi_utils.is_lung_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(disease_code1) and nhi_utils.is_lung_cancer(
                disease_code2
            ):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非肺癌病名<br>肺癌主診斷碼範圍: C33~, C34~<br>"
                )
        elif treat_type == "大腸癌照護":
            if nhi_utils.is_colorectal_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_colorectal_cancer(disease_code2):
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非大腸癌病名<br>大腸癌主診斷碼範圍: C18~, C19~, C20~, C21~<br>"
        elif treat_type == "胃癌照護":
            if nhi_utils.is_stomach_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_stomach_cancer(disease_code2):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非胃癌病名<br>胃癌主診斷碼範圍: C16~<br>"
                )
        elif treat_type == "攝護腺癌照護":
            if nhi_utils.is_prostate_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_prostate_cancer(disease_code2):
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非攝護腺癌病名<br>攝護腺癌主診斷碼範圍: C61~<br>"
        elif treat_type == "口腔癌照護":
            if nhi_utils.is_oral_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(disease_code1) and nhi_utils.is_oral_cancer(
                disease_code2
            ):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非口腔癌病名<br>口腔癌主診斷碼範圍: C01~C10<br>"
                )
        elif treat_type == "子宮頸癌照護":
            if nhi_utils.is_cervical_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_cervcial_cancer(disease_code2):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非子宮頸癌病名<br>子宮頸癌主診斷碼範圍: C53<br>"
                )
        elif treat_type == "子宮體癌照護":
            if nhi_utils.is_endometrial_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_endometrial_cancer(disease_code2):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非子宮體癌病名<br>子宮體癌主診斷碼範圍: C54<br>"
                )
        elif treat_type == "甲狀腺癌照護":
            if nhi_utils.is_thyroid_cancer(disease_code1):
                pass
            elif nhi_utils.is_main_cancer(
                disease_code1
            ) and nhi_utils.is_thyroid_cancer(disease_code2):
                pass
            else:
                error_message = (
                    "* ICD-10-CM主診斷碼非甲狀腺癌病名<br>甲狀腺癌主診斷碼範圍: C73<br>"
                )
        elif treat_type == "慢性腎病照護":
            if disease_code1[:4] in [
                "N182",
                "N183",
                "N184",
                "N185",
                "N186",
            ]:  # 慢性腎病
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非慢性臟病病名<br>慢性腎病主診斷碼範圍: N182~N186<br>"
        elif treat_type == "兒童鼻炎":
            if disease_code1 in ["J301", "J302", "J305", "J3081", "J3089", "J309"]:
                pass
            else:
                error_message = "* ICD-10-CM主診斷碼非兒童過敏性鼻炎病名<br>過敏性鼻炎主診斷碼範圍: J301, J302, J305, J3081, J3089, J309<br>"

        return error_message

    # 檢查開藥日數
    @staticmethod
    def _check_pres_days_error(treat_type, pres_days):
        error_message = None

        if treat_type in nhi_utils.PREGNANT_CARE_TREAT and pres_days < 7:
            error_message = (
                f"* {treat_type}未開立七天以上的內服藥, 請開立內服藥至少七天"
            )
        elif treat_type in nhi_utils.CANCER_CARE_TREAT and pres_days < 7:
            error_message = (
                f"* {treat_type}未開立七天以上的內服藥, 請開立內服藥至少七天"
            )
        elif treat_type in nhi_utils.CHILD_CARE_TREAT and pres_days < 5:
            error_message = (
                f"* {treat_type}照護未開立五天以上的內服藥, 請開立內服藥至少五天"
            )

        return error_message

    # 年齡範圍檢查
    @staticmethod
    def _check_age_range_error(treat_type, medical_record, patient_record, age_range):
        error_message = None

        age_year, age_month = date_utils.get_age(
            patient_record["Birthday"], medical_record["CaseDate"]
        )

        if age_year < age_range[0] or age_year > age_range[1]:
            if treat_type == "兒童鼻炎":
                error_message = f"* 兒童過敏性鼻炎病患年齡非{age_range[0]}-{age_range[1]}歲兒童, 請改為一般門診"

        return error_message

    def _check_duration_by_ins_code(
        self, patient_key, case_date, treat_type, check_ins_code, table_widget_ins_care
    ):
        error_message = None

        if treat_type in nhi_utils.CANCER_CARE_TREAT:
            if table_widget_ins_care is None:
                return None

            treat_exists = False
            for row_no in range(table_widget_ins_care.rowCount()):
                ins_code = table_widget_ins_care.item(row_no, 8)
                if ins_code is not None:
                    ins_code = ins_code.text()
                    if ins_code == check_ins_code:
                        treat_exists = True
                        break

            if not treat_exists:  # 無此醫令
                return None

            start_date = case_date.date() - datetime.timedelta(days=60)
            end_date = case_date.date() - datetime.timedelta(days=1)
            sql = f'''
                SELECT cases.CaseDate, prescript.MedicineName FROM prescript
                    LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                WHERE
                    cases.PatientKey = {patient_key} AND
                    DATE(cases.CaseDate) BETWEEN "{start_date}" AND "{end_date}" AND
                    InsCode = "{check_ins_code}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) >= 1:
                treat_name = string_utils.xstr(rows[0]["MedicineName"])
                case_date = rows[0]["CaseDate"].date()
                error_message = f"""* {treat_name}限60日申報一次, 上次申報日期為{case_date}，
                    在{case_date + datetime.timedelta(days=60)}之後才能申報，請刪除此項醫令"""
        elif treat_type == "兒童鼻炎":
            if table_widget_ins_care is None:
                return error_message

            treat_exists = False
            for row_no in range(table_widget_ins_care.rowCount()):
                ins_code = table_widget_ins_care.item(row_no, 8)
                if ins_code is not None:
                    ins_code = ins_code.text()
                    if ins_code == check_ins_code:
                        treat_exists = True
                        break

            if not treat_exists:  # 無此醫令
                return error_message

            start_date = case_date.date() - datetime.timedelta(days=105)
            end_date = case_date.date() - datetime.timedelta(days=1)
            sql = f'''
                SELECT cases.CaseDate, prescript.MedicineName FROM prescript
                    LEFT JOIN cases ON prescript.CaseKey = cases.CaseKey
                WHERE
                    cases.PatientKey = {patient_key} AND
                    cases.CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                    InsCode = "{check_ins_code}"
            '''
            rows = self.database.select_record(sql)
            if len(rows) <= 0:
                return

            first_date = rows[0]["CaseDate"]
            duration = case_date.date() - first_date.date()
            if duration.days >= 105:  # 今年度不可超過105天
                treat_name = string_utils.xstr(rows[0]["MedicineName"])
                case_date = rows[0]["CaseDate"].date()
                error_message = f"* {treat_name}限105日內完成, 上次申報日期為{case_date}, 請改為一般門診"

        return error_message

    # 小兒氣喘及小兒腦性麻痺檢查 (必須執行針灸或傷科處置)
    def _check_child_care(self):
        check_ok = True
        error_message = []

        if self.treatment == "":
            error_message.append("* 未執行針灸或傷科處置")

        error = self._check_disease1_error(
            self.treat_type, self.disease_code1, self.disease_code2
        )
        if error is not None:
            error_message.append(error)

        error = self._check_pres_days_error(self.treat_type, self.pres_days)
        if error is not None:
            error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "小兒疾病加強照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        小兒疾病加強照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 腦血管疾病檢查 (必須執行針灸或傷科處置)
    def _check_brain(self):
        check_ok = True
        error_message = []

        if self.treatment == "":
            error_message.append("* 未執行針灸或傷科處置")

        error = self._check_disease1_error(self.treat_type, self.disease_code1)
        if error is not None:
            error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "腦血管疾病加強照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        腦血管疾病加強照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 助孕照護檢查 (至少開藥七天)
    def _check_aid_pregnant_care(self):
        check_ok = True
        error_message = []

        error = self._check_disease1_error(self.treat_type, self.disease_code1)
        if error is not None:
            error_message.append(error)

        # error = self._check_pres_days_error(self.treat_type, self.pres_days)
        # if error is not None:
        #     error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "助孕照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        助孕照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 保胎照護檢查 (至少開藥七天)
    def _check_keep_baby_care(self):
        check_ok = True
        error_message = []

        # error = self._check_pres_days_error(self.treat_type, self.pres_days)
        # if error is not None:
        #     error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "保胎照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        保胎照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 癌症檢查 (至少開藥七天)
    def _check_cancer_care(self):
        check_ok = True
        error_message = []

        error = self._check_disease1_error(self.treat_type, self.disease_code1)
        if error is not None:
            error_message.append(error)

        # error = self._check_pres_days_error(self.treat_type, self.pres_days)
        # if error is not None:
        #     error_message.append(error)

        check_ins_code_list = ["P56006", "P56007"]
        for check_ins_code in check_ins_code_list:
            error = self._check_duration_by_ins_code(
                string_utils.xstr(self.patient_record["PatientKey"]),
                self.medical_record["CaseDate"],
                self.treat_type,
                check_ins_code,
                self.table_widget_ins_care,
            )
            if error is not None:
                error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "癌症照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        特定癌症照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_ckd(self):
        if not self._check_ckd_disease():
            return False

        if not self._check_ckd_duration():
            return False

        if not self._check_ckd_days("P64011", 56):
            return False

        if not self._check_ckd_days("P64012", 180):
            return False

        return True

    def _check_ckd_disease(self):
        check_ok = True
        error_message = []

        error = self._check_disease1_error(self.treat_type, self.disease_code1)
        if error is not None:
            error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "慢性腎病照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        慢性腎病照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_ckd_duration(self):
        check_ok = True

        error_message = []
        current_ckd_code = self._get_current_ckd_code()
        if current_ckd_code is not None and current_ckd_code == "P64009":
            error = self._check_last_ckd_drug()
            if error:
                error_message.append(error)
        elif current_ckd_code is not None and "P64005" <= current_ckd_code <= "P64008":
            if self.pres_days > 0 and self.course >= 2:
                error_message.append(
                    "慢性腎病ckd 療程2-6次為純針灸療程不可開藥，若要開藥，請掛號修正取得新卡序，不要續上次療程。"
                )
            else:
                error = self._check_last_ckd_treat(current_ckd_code)
                if error:
                    error_message.append(error)
        else:
            pass

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "慢性腎病照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        慢性腎病照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請改為一般門診或更正此錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_last_ckd_drug(self):
        case_key = self.medical_record["CaseKey"]
        case_date = self.medical_record["CaseDate"].date()
        patient_key = self.medical_record["PatientKey"]
        error_message = None

        sql = f"""
            SELECT cases.CaseDate, prescript.InsCode FROM prescript
                LEFT JOIN cases on cases.CaseKey = prescript.CaseKey
            WHERE
                prescript.CaseKey != {case_key} AND
                DATE(prescript.CaseDate) <= "{case_date.strftime("%Y-%m-%d")}" AND
                cases.PatientKey = {patient_key} AND
                InsCode BETWEEN "P64001" AND "P64004"
            ORDER BY cases.CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        last_case_date = rows[0]["CaseDate"].date()
        last_ins_code = string_utils.xstr(rows[0]["InsCode"])
        delta = case_date - last_case_date
        if delta.days < 28:
            error_message = f"""
            本日門診為不含藥費CKD門診(P64009),，距離上次含藥費CKD門診{last_case_date}({last_ins_code})
            只有{delta.days}天, 未滿28天 <br><br>
            健保署規定: 不含藥費之加強照護費(P64009)與含藥費之加強照護費 (P64001-P64004),需≧28天始得相互轉換
            """

        return error_message

    def _check_last_ckd_treat(self, ins_code):
        case_key = self.medical_record["CaseKey"]
        case_date = self.medical_record["CaseDate"].date()
        patient_key = self.medical_record["PatientKey"]
        error_message = None

        sql = f"""
            SELECT cases.CaseDate, cases.Card FROM prescript
                LEFT JOIN cases on cases.CaseKey = prescript.CaseKey
            WHERE
                prescript.CaseKey != {case_key} AND
                DATE(prescript.CaseDate) <= "{case_date.strftime("%Y-%m-%d")}" AND
                cases.PatientKey = {patient_key} AND
                InsCode = "P64009"
            ORDER BY cases.CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        row = rows[0]
        last_case_date = row["CaseDate"].date()
        delta = case_date - last_case_date
        if delta.days < 28:
            last_card = string_utils.xstr(row["Card"])
            sql = f"""
                SELECT cases.CaseDate, cases.Continuance FROM prescript
                    LEFT JOIN cases on cases.CaseKey = prescript.CaseKey
                WHERE
                    prescript.CaseKey != {case_key} AND
                    DATE(prescript.CaseDate) <= "{case_date.strftime("%Y-%m-%d")}" AND
                    cases.PatientKey = {patient_key} AND
                    InsCode = "P64010" AND
                    Card = "{last_card}"
                ORDER BY cases.Continuance DESC LIMIT 1
            """
            rows = self.database.select_record(sql)
            if len(rows) > 0:
                row = rows[0]
                last_course = number_utils.get_integer(row["Continuance"])
                if last_course >= 6:  # 療程結束可以掛號
                    return None

            error_message = f"""
            本日門診為含藥費CKD門診({ins_code}),，距離上次不含藥費CKD門診{last_case_date}(P64009)只有{delta.days}天, 未滿28天
            <br><br>
            健保署規定: 含藥費之加強照護費(P64001-P64008)與不含藥費之加強照護費 (P64009),需≧28天始得相互轉換
            """

        return error_message

    def _get_current_ckd_code(self):
        current_ins_code = None

        for row_no in range(self.table_widget_ins_care.rowCount()):
            current_ins_code = self.table_widget_ins_care.item(row_no, 8)
            if current_ins_code is None:
                continue

            current_ins_code = current_ins_code.text()
            if current_ins_code in [
                "P64001",
                "P64002",
                "P64003",
                "P64004",
                "P64005",
                "P64006",
                "P64007",
                "P64008",
                "P64009",
            ]:
                break

        return current_ins_code

    def _check_ckd_days(self, ins_code, max_days):
        current_ckd_code = self._get_current_ckd_code()
        if current_ckd_code is None or current_ckd_code not in [ins_code]:
            return True

        check_ok = True
        case_key = self.medical_record["CaseKey"]
        case_date = self.medical_record["CaseDate"].date()
        patient_key = self.medical_record["PatientKey"]
        error_message = None

        sql = f"""
            SELECT cases.CaseDate FROM prescript
                LEFT JOIN cases on cases.CaseKey = prescript.CaseKey
            WHERE
                prescript.CaseKey != {case_key} AND
                DATE(prescript.CaseDate) <= "{case_date.strftime("%Y-%m-%d")}" AND
                cases.PatientKey = {patient_key} AND
                InsCode = "{ins_code}"
            ORDER BY cases.CaseDate DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return True

        last_case_date = rows[0]["CaseDate"].date()
        delta = case_date - last_case_date
        if delta.days < max_days:
            error_message = f"""
            本日CKD門診({ins_code})距離上次CKD門診{last_case_date}({ins_code})只有{delta.days}天, 未滿{max_days}天
            <br><br>
            健保署規定: 申報CKD({ins_code})，限{max_days}天以上申報一次。
            """

            system_utils.show_message_box(
                QMessageBox.Critical,
                "慢性腎病照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        慢性腎病照護檢查錯誤訊息:<br>
                        <br>
                        {error_message}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_child_rhinitis(self):
        check_ok = True
        error_message = []

        age_range = [5, 14]  # 5-14兒童
        error = self._check_age_range_error(
            self.treat_type, self.medical_record, self.patient_record, age_range
        )
        if error is not None:
            error_message.append(error)

        error = self._check_disease1_error(self.treat_type, self.disease_code1)
        if error is not None:
            error_message.append(error)

        error = self._check_duration_by_ins_code(
            string_utils.xstr(self.patient_record["PatientKey"]),
            self.medical_record["CaseDate"],
            self.treat_type,
            "P58005",
            self.table_widget_ins_care,
        )
        if error is not None:
            error_message.append(error)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "兒童過敏性鼻炎照護檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        兒童過敏性鼻炎照護檢查錯誤訊息:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_no_pharmacy(self):
        if self.no_pharmacy == "N":  # 未設定不調劑不檢查
            return True

        if self.pres_days <= 0:  # 未開藥不檢查
            return True

        total_medicine_set = self._get_total_medicine_set()
        if total_medicine_set == 1:  # 只有一組藥品不正確
            system_utils.show_message_box(
                QMessageBox.Warning,
                "健保開藥調劑檢查",
                '<b><font size="5" color="red">錯誤! 本次病歷只有健保處方，且設定為不調劑</font></b>',
                "請注意! 請確認調劑方式是否設定為不調劑.",
                button_text="了解",
            )
            return False

        return True

    def _check_general(self):
        if self.system_settings.field("比例法劑量") == "Y":
            if not self._check_no_pharmacy():
                return False

        if not self._check_deposit_fee():
            return False

        if not self._check_treat_type():
            return False

        if not self._check_empty_disease():
            return False

        if not self._check_unavailable_disease():
            return False

        if not self._check_disease_duplicated():
            return False

        case_year = self.medical_record["CaseDate"].year
        if case_year <= 2023:
            pass
        else:
            if not self._check_disease_neat():
                return False

        if not self._check_disease_self_payment():
            return False

        if not self._check_course_disease():
            return False

        if self.system_settings.field("檢查相同診斷碼用藥天數") == "Y":
            if not self._check_same_disease_pres_days():
                return False

        if self.system_settings.field("療程同病名超過兩個") == "Y":
            if not self._check_same_disease_course2():
                return False

        if not self._check_ins_medicine():
            return False

        if not self._check_empty_prescript():
            return False

        if (
            not self._check_min_acupuncture_points()
        ):  # 2023-07-19 暫停  # 2026-01-10 重新啟用
            return False

        if not self._check_empty_treat():
            return False

        # if not self._check_acupuncture_level():  # 2023-07-19 暫停
        #     return False

        if not self._check_injury_treat():
            return False

        if self.system_settings.field(
            "檢查損傷診斷碼"
        ) == "Y" and self.treat_type not in ["內科", "醫療諮詢"]:
            if not self._check_injury_disease_period():
                return False

        if self.system_settings.field("檢查療程開藥超過1次") == "Y":
            if not self._check_course_pres_days_once():
                return False

        if self.system_settings.field("內科同病名超過3次") == "Y":
            if not self._check_same_disease():
                return False

        if not self._check_dosage():
            return False

        if self.treatment in [
            "高度複雜性傷科",
            "中度針灸合併高度傷科起始次",
            "高度針灸合併高度傷科起始次",
            "一般針灸合併高度傷科",
            "中度針灸合併高度傷科",
            "高度針灸合併高度傷科",
        ] or self.second_treatment in ["高度複雜性傷科", "中度複雜性傷科合併特殊疾病"]:
            if self.medical_record["RegistType"] in nhi_utils.TOUR_TYPE:
                return True

            if not self._check_highly_complicated_massage_duration():
                return False

        if self.treatment == "複雜針灸":
            if not self._check_complicated_acupuncture():
                return False
        elif self.treatment == "複雜傷科":
            if not self._check_complicated_massage():
                return False
        elif self.treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST:
            if not self._check_second_treatment():
                return False

            if not self._check_moderate_complicated_acupuncture():
                return False
        elif self.treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST:
            if not self._check_second_treatment():
                return False

            if not self._check_highly_complicated_acupuncture():
                return False
        elif self.treatment in ["中度複雜性傷科", "中度複雜性傷科合併特殊疾病"]:
            if not self._check_moderate_complicated_massage():
                return False
        elif self.treatment == "高度複雜性傷科":
            if not self._check_highly_complicated_massage():
                return False
        elif self.treatment == "脫臼整復復位":
            if not self._check_dislocate():
                return False
        elif self.treatment == "骨折復位":
            if not self._check_fracture():
                return False

        if self.system_settings.field("慢性病開藥檢查") == "Y":
            if not self._check_strict_special_code():
                return False
        else:
            if not self._check_special_code():
                return False

        if self.second_treatment in ["中度複雜性傷科", "中度複雜性傷科合併特殊疾病"]:
            if not self._check_moderate_complicated_massage():
                return False
        elif self.second_treatment == "高度複雜性傷科":
            if not self._check_highly_complicated_massage():
                return False

        if not self._check_pres_days():
            return False

        if not self._check_prescript():
            return False

        if self.system_settings.field("診斷資料必填") == "Y":
            if not self._check_diagnostic_data_required():
                return False

        if not self._check_infectious_drug_pres_days():
            return False

        if self.system_settings.field("健保處方三次相同不能存檔") == "Y":
            if not self._check_prescript_same_three_times():
                return False

        if not self._check_invalid_gender_disease():
            return False

        if self.treatment not in ["", None] and self.second_treatment not in ["", None]:
            if not self._check_merge_treats():
                return False
        elif self.treatment in nhi_utils.COMPLICATED_ACUPUNCTURE_TREAT:
            if not self._check_complicated_acupuncture_treats():
                return False
        elif self.treatment in nhi_utils.COMPLICATED_MASSAGE_TREAT:
            if not self._check_complicated_massage_treats():
                return False

        if not self._check_integrate_care():
            return False

        self._check_diag_and_treat_times()

        return True

    def _check_deposit_fee(self):
        if self.system_settings.field("欠卡申報點數檢查") != "Y":
            return True

        if self.deposit_fee in [None, 0]:
            return True

        if self.ins_apply_fee > self.deposit_fee:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("申報點數過高提醒")
            msg_box.setText(
                """<b><font size="5" color="red">
                    申報點數大於欠卡費，若病患未於申報前還卡可能會造成損失!
                </font></b>"""
            )
            msg_box.setInformativeText(
                "請注意! 可以考慮調漲欠卡費或減少開藥天數以降低損失"
            )
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("不要存檔，我要調整"), QMessageBox.NoRole)

            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                return False

        return True

    def _check_treat_type(self):
        warning_message = []

        course = number_utils.get_integer(self.medical_record["Continuance"])
        if (
            self.treatment in [None, ""]
            and self.second_treatment in [None, ""]
            and course >= 2
        ):
            card = string_utils.xstr(self.medical_record["Card"])
            warning_message.append(
                f"本次掛號卡序為 {card}-{course} 但病歷為內科病歷，請重新取得內科卡序!"
            )

        if len(warning_message) > 0:
            warning_message = "<br>".join(warning_message)
            system_utils.show_message_box(
                QMessageBox.Warning,
                "療程查結果提醒",
                f'<b><font size="5" color="red">{warning_message}</font></b>',
                "請注意! 請至醫師看診作業或掛號作業的已就診名單「重寫IC」, 以產生新的內科卡序.",
                button_text="好的，存檔後會重新IC寫卡",
            )

        return True

    def _check_diag_and_treat_times(self):
        warning_message = []

        patient_key = self.medical_record["PatientKey"]
        message = registration_utils.check_treat_times(  # 檢查當月健保針傷次數
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        message = registration_utils.check_diag_fee_times(  # 檢查當月健保診察費次數
            self.database, self.system_settings, patient_key
        )
        if message is not None:
            warning_message.append(message)

        if len(warning_message) > 0:
            warning_message = "<br>".join(warning_message)
            system_utils.show_message_box(
                QMessageBox.Warning,
                "門診次數檢查結果提醒",
                f'<b><font size="5" color="red">{warning_message}</font></b>',
                "請注意! 以上的狀況提示並非資料發生錯誤, 若有疑問, 請至 [病歷查詢] 檢查該筆資料的內容.",
            )

    def _check_second_treatment(self):
        if self.second_treatment in ["", None]:
            return True

        if self.second_treatment in ["中度複雜性傷科", "中度複雜性傷科合併特殊疾病"]:
            if not self._check_moderate_complicated_massage():
                return False
        elif self.second_treatment == "高度複雜性傷科":
            if not self._check_highly_complicated_massage():
                return False
        elif self.second_treatment == "脫臼整復復位":
            if not self._check_dislocate():
                return False
        elif self.second_treatment == "骨折復位":
            if not self._check_fracture():
                return False

        return True

    def _check_dosage(self):
        check_ok = True
        error_message = []

        row_count = self.table_widget_ins_prescript.rowCount()

        if row_count <= 0:
            return check_ok

        total_dosage = 0.0
        for row_no in range(row_count):
            self.table_widget_ins_prescript.setCurrentCell(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"]
            )
            medicine_key = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineKey"]
            )
            if medicine_key is None:
                continue

            medicine_name = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name is not None:
                medicine_name = medicine_name.text()

            if medicine_name == "":
                continue

            if "清冠一號" in medicine_name:
                continue

            dosage = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["Dosage"]
            )
            unit = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["Unit"]
            )

            # if dosage is None or dosage.text() == '':  # 2024.08.28 曙光
            # if unit not in ['', None] and unit.text() not in ['', None] and (dosage is None or dosage.text() == ''):
            #     error_message.append(f'{medicine_name} 無劑量')
            #     break

            if (
                unit not in ["", None]
                and unit.text() not in ["", None]
                and (dosage is None or dosage.text().strip() == "")
            ):
                error_message.append(f"{medicine_name} 無劑量")
                break

            try:
                dosage_value = number_utils.get_float(dosage.text().strip())
                if (
                    self.system_settings.field("健保開藥劑量必須大於0") == "Y"
                    and dosage_value <= 0
                ):
                    error_message.append(f"{medicine_name} 劑量必須 > 0")
                    break
            except Exception:
                error_message.append(f"{medicine_name} 劑量有誤")

            try:
                total_dosage += number_utils.get_float(dosage.text().strip())
            except ValueError:
                error_message.append(f"{medicine_name} 劑量有誤")

        if (
            self.medical_record["Injury"] in nhi_utils.INFECTIOUS_TYPE
            or self.medical_record["Share"] in nhi_utils.INFECTIOUS_TYPE
        ):  # 確診病歷不設限
            return check_ok

        dosage_limitation = number_utils.get_integer(
            self.system_settings.field("劑量上限")
        )
        minimum_dosage = number_utils.get_integer(
            self.system_settings.field("最低劑量")
        )
        minimum_dosage2 = number_utils.get_integer(
            self.system_settings.field("6歲以下最低劑量")
        )

        age_year, _ = date_utils.get_age(
            self.patient_record["Birthday"], self.medical_record["CaseDate"]
        )

        if (
            dosage_limitation is not None and 0 < dosage_limitation < total_dosage
        ):  # 超過劑量上限
            error_message.append(f"用藥超過系統設定內的劑量上限{dosage_limitation}克")
        elif (
            number_utils.get_integer(age_year) >= 6
            and minimum_dosage is not None
            and 0 < total_dosage < minimum_dosage
        ):  # 6歲以上低於最低劑量
            error_message.append(
                f"6歲以上用藥少於系統設定內的最低劑量{minimum_dosage}克"
            )
        elif (
            number_utils.get_integer(age_year) < 6
            and minimum_dosage2 is not None
            and 0 < total_dosage < minimum_dosage2
        ):  # 6歲以下低於最低劑量
            error_message.append(
                f"6歲以下用藥少於系統設定內的最低劑量{minimum_dosage2}克"
            )

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "劑量檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        處方及劑量檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_empty_disease(self):
        if self.call_from == "病歷查詢":
            return True

        check_ok = True
        error_message = []

        if (
            self.disease_code1 == ""
            and self.disease_code2 == ""
            and self.disease_code3 == ""
            and self.disease_code4 == ""
        ):
            error_message.append("所有診斷碼均為空白, 請確定是否遺漏輸入.")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_unavailable_disease(self):
        check_ok = True
        error_message = []

        if self.disease_code1 in ["U099", "Z8616"]:
            error_message.append(
                f"* 主診斷碼不可申報{self.disease_code1}, 請輸入在次診斷碼!"
            )
        elif self.disease_code2 in ["Z8616"]:
            pass
        elif self.disease_code3 in ["Z8616"]:
            pass
        else:
            if self.disease_code1[:1] in ["V", "W", "X", "Y", "Z"]:
                error_message.append(
                    f"主診斷碼不可申報{self.disease_code1}, 請選擇其他病名."
                )
            # if self.disease_code2[:1] in ['W', 'X', 'Y', 'Z']:
            #     error_message.append(f'次診斷碼1不可申報{self.disease_code2}, 請選擇其他病名.')
            # if self.disease_code3[:1] in ['W', 'X', 'Y', 'Z']:
            #     error_message.append(f'次診斷碼2不可申報{self.disease_code3}, 請選擇其他病名.')
            # if self.disease_code4[:1] in ['W', 'X', 'Y', 'Z']:
            #     error_message.append(f'次診斷碼4不可申報{self.disease_code4}, 請選擇其他病名.')

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_course_disease(self):
        check_ok = True
        if number_utils.get_integer(self.medical_record["Continuance"]) <= 1:
            return check_ok

        error_message = []

        case_date = self.medical_record["CaseDate"]
        last_treat_date = (case_date - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d 00:00:00"
        )
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        card = self._get_card()
        sql = f'''
            SELECT
                Name, CaseDate, Card, Continuance, DiseaseCode1, DiseaseName1 FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate >= "{last_treat_date}") AND
                (CaseDate < "{case_date.strftime("%Y-%m-%d 00:00:00")}") AND
                (InsType = "健保") AND
                (Card = "{card}") AND
                (Continuance >= 1)
            ORDER BY CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return check_ok

        row = rows[0]
        last_disease_code1 = string_utils.xstr(row["DiseaseCode1"]).strip()
        name = string_utils.xstr(row["Name"]).strip()
        case_date = string_utils.xstr(row["CaseDate"].date())
        card = string_utils.xstr(row["Card"])
        course = string_utils.xstr(row["Continuance"])
        disease_code1 = string_utils.xstr(row["DiseaseCode1"]).strip()
        disease_name1 = string_utils.xstr(row["DiseaseName1"]).strip()
        if (
            disease_code1 != "" and self.disease_code1[:3] != last_disease_code1[:3]
        ):  # 只檢查前三碼
            error_message.append(
                f"""
                    本次療程主診斷碼與上次不同, 請確定是否輸入正確!<br>
                    上次病歷為:<br>
                    <font color="navy">
                    病患姓名: {name}<br>
                    門診日期: {case_date}<br>
                    健保卡序: {card}-{course}<br>
                    主診斷碼: {disease_code1}<br>
                    中文名稱: {disease_name1}
                    </font>
                """
            )

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("診斷碼檢查錯誤")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定上次療程診斷碼與本次是否差異過大.")
            if self.system_settings.field("療程不同病名不能存檔") == "Y":
                msg_box.addButton(
                    QPushButton(f"請修改主診斷碼為 {disease_code1} 後再存檔"),
                    QMessageBox.NoRole,
                )
                msg_box.exec_()
                return False
            else:
                msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
                msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)

            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    # 療程同病名超過兩個
    def _check_same_disease_course2(self):
        check_ok = True

        case_date = self.medical_record["CaseDate"]
        last_treat_date = (case_date - datetime.timedelta(days=30)).strftime(
            "%Y-%m-01 00:00:00"
        )
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        sql = f'''
            SELECT
                DATE(CaseDate) AS CaseDate, Name, Card, DiseaseCode1, DiseaseName1 FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate >= "{last_treat_date}") AND
                (InsType = "健保") AND
                (DiseaseCode1 = "{self.disease_code1}") AND
                (Continuance = 1)
            GROUP BY Card
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)
        if len(rows) < 3:
            return check_ok

        row = rows[0]
        name = string_utils.xstr(row["Name"])
        disease_code1 = string_utils.xstr(row["DiseaseCode1"])
        disease_name1 = string_utils.xstr(row["DiseaseName1"])

        case_date_list = []
        for row in rows:
            case_date_list.append(f"{row['CaseDate']}: {row['Card']}")

        error_message = []
        error_message.append(
            f"""
                本次療程主診斷碼在兩個月內已重複超過三次, 無法存檔!<br>
                上次病歷為:<br>
                <font color="navy">
                病患姓名: {name}<br>
                主診斷碼: {disease_code1}<br>
                中文名稱: {disease_name1}<br>
                重複日期: <br>
                {"<br>".join(case_date_list)}
                </font>
            """
        )

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("診斷碼檢查錯誤")
        msg_box.setText(
            f"""
                <font size="5" color="red">
                    <b>
                    診斷碼檢查錯誤如下:<br>
                    <br>
                    {self._join_error_message(error_message)}
                    </b>
                </font>
            """,
        )
        msg_box.setInformativeText("以上資料僅供參考.")
        msg_box.addButton(QPushButton("確定"), QMessageBox.YesRole)
        msg_box.exec_()
        check_ok = False

        return check_ok

    def _check_same_disease_pres_days(self):
        check_ok = True

        if self.pres_days <= 0:
            return check_ok

        error_message = []
        case_date = self.medical_record["CaseDate"]
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        sql = f'''
            SELECT
                CaseKey, Name, CaseDate, Card, DiseaseCode1, DiseaseName1 FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate < "{case_date}") AND
                (InsType = "健保") AND
                (DiseaseCode1 = "{self.disease_code1}")
            ORDER BY CaseDate DESC LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return check_ok

        row = rows[0]

        last_case_key = row["CaseKey"]
        last_pres_days = case_utils.get_pres_days(self.database, last_case_key)
        name = string_utils.xstr(row["Name"])
        case_date = string_utils.xstr(row["CaseDate"].date())
        card = string_utils.xstr(row["Card"])
        disease_code1 = string_utils.xstr(row["DiseaseCode1"])
        disease_name1 = string_utils.xstr(row["DiseaseName1"])
        if self.pres_days < last_pres_days:
            error_message.append(
                f"""
                    本次病歷主診斷碼與{case_date}相同, 給藥天數少於上次病歷!<br>
                    <font color="navy">
                    上次病歷為:<br><br>
                    病患姓名: {name}<br>
                    門診日期: {case_date}<br>
                    健保卡序: {card}<br>
                    主診斷碼: {disease_code1}<br>
                    中文名稱: {disease_name1}<br>
                    給藥天數: {last_pres_days}<br>
                    </font>
                """
            )

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("診斷碼檢查提示")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查提示如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定本次給藥天數是否正確.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    def _check_empty_prescript(self):
        check_ok = True

        if self.treat_type == "醫療諮詢":
            return check_ok

        error_message = []

        medicine_name = self.table_widget_ins_prescript.item(
            0, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
        )
        treat_name = self.table_widget_ins_treat.item(
            0, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
        )

        if medicine_name is None and self.treatment == "" and treat_name is None:
            error_message.append("所有處方均為空白, 請確定是否遺漏輸入.")

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("處方空白")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        處方檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定是否為醫療諮詢(問診)或遺漏輸入處方.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    def _check_empty_treat(self):
        check_ok = True
        error_message = []

        treat_exists = False
        for row_no in range(self.table_widget_ins_treat.rowCount()):
            treat_name = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )

            if treat_name is not None:
                treat_exists = True
                break

        if self.treatment != "" and not treat_exists:
            error_message.append(
                "有執行針傷處置但無針灸穴道或處置手法, 請確定是否遺漏輸入."
            )

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("處置空白")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        處置檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定是否遺漏輸入處置.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    def _check_min_acupuncture_points(self):
        check_ok = True

        min_acupuncture_points = number_utils.get_integer(
            self.system_settings.field("最少針灸穴道數")
        )
        if min_acupuncture_points <= 0:
            return check_ok

        error_message = []

        if self.treatment not in nhi_utils.ACUPUNCTURE_TREAT:
            return check_ok

        acupuncture_points = 0
        for row_no in range(self.table_widget_ins_treat.rowCount()):
            medicine_name = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )
            if medicine_name is not None:
                medicine_name = medicine_name.text()
                if (
                    "波形" in medicine_name
                    or "頻率" in medicine_name
                    or "時間" in medicine_name
                ):
                    continue

                if (
                    "治療部位" in medicine_name
                    or "治療時間" in medicine_name
                    or "治療開始" in medicine_name
                    or "治療結束" in medicine_name
                    or "輔助治療" in medicine_name
                ):
                    continue

            medicine_type = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineType"]
            )
            if medicine_type is not None and medicine_type.text() == "穴道":
                acupuncture_points += 1

        if acupuncture_points < min_acupuncture_points:
            error_message.append(f"針灸穴位不足{min_acupuncture_points}個, 請補足.")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "針灸穴位檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        針灸治療檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_injury_treat(self):
        check_ok = True
        error_message = []

        if self.medical_record["Share"] == "職業傷害" and self.treatment == "":
            error_message.append(
                "此病歷為職業傷害案件, 但無針灸或傷科處置, 請確定是否遺漏輸入."
            )

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("處置空白")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        處置檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定是否遺漏輸入處置.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    def _check_injury_disease_period(self):
        check_ok = True
        error_message = []

        try:
            extension_code = self.disease_code1[6]  # 第七碼
        except IndexError:
            return check_ok

        if extension_code not in ["A", "D", "G", "K", "P", "S"]:
            return True

        if extension_code in ["A"]:  # 初期照護
            message = self._check_extension_code_a()
            if message is not None:
                error_message.append(message)
        elif extension_code in ["D", "G", "K", "P"]:  # 後續照護
            message = self._check_extension_code_d()
            if message is not None:
                error_message.append(message)
        elif extension_code in ["S"]:  # 後遺症
            message = self._check_extension_code_s()
            if message is not None:
                error_message.append(message)

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("損傷診斷碼檢查")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        損傷診斷碼檢查提示如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            instruction = """
                請確定損傷發生日期與處置診斷碼是否相符.<br>
                初期照護: 15日內<br>
                後續照護: 16~30日內<br>
                後遺症: 超過30日
            """
            msg_box.setInformativeText(instruction)
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    # 檢查療程開藥超過1次
    def _check_course_pres_days_once(self):
        check_ok = True

        if self.pres_days <= 0:  # 沒開藥不用檢查
            return check_ok

        if (
            number_utils.get_integer(self.medical_record["Continuance"]) <= 1
        ):  # 療程首次不用檢查
            return check_ok

        error_message = []

        case_date = self.medical_record["CaseDate"]
        last_treat_date = (case_date - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d 00:00:00"
        )
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        card = self._get_card()
        sql = f'''
            SELECT CaseKey, CaseDate FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate >= "{last_treat_date}") AND
                (InsType = "健保") AND
                (Card = "{card}") AND
                (Continuance >= 1)
        '''
        rows = self.database.select_record(sql)

        pres_days_count = 1  # 今天也算1次
        for row in rows:
            pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])
            if pres_days > 0:
                pres_days_count += 1

        if pres_days_count >= 2:
            error_message.append("療程期間開藥次數超過1次")

        if len(error_message) > 0:
            if self.system_settings.field("療程開藥超過1次存檔") == "無法存檔":
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "療程開藥次數檢查",
                    f"""
                        <font size="5" color="red">
                          <b>
                            療程期間開藥次數檢查提示如下:<br>
                            <br>
                            {self._join_error_message(error_message)}
                          </b>
                        </font>
                    """,
                    "請調整病歷內容，以利健保申報.",
                )
                check_ok = False
            else:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("療程開藥次數檢查")
                msg_box.setText(
                    f"""
                        <font size="5" color="red">
                          <b>
                            療程期間開藥次數檢查提示如下:<br>
                            <br>
                            {self._join_error_message(error_message)}
                          </b>
                        </font>
                    """,
                )
                msg_box.setInformativeText("請確定是否繼續存檔")
                msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
                msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
                save_file = msg_box.exec_()
                if save_file == QMessageBox.RejectRole:
                    check_ok = False

        return check_ok

    # 內科同病名超過3次
    def _check_same_disease(self):
        check_ok = True
        if number_utils.get_integer(self.medical_record["Continuance"]) >= 2:
            return check_ok

        if self.treat_type != "內科":
            return check_ok

        case_date = self.medical_record["CaseDate"]
        first_date = case_date.strftime("%Y-%m-01 00:00:00")
        end_date = case_date.strftime("%Y-%m-%d 23:59:59")
        patient_key = self.medical_record["PatientKey"]
        sql = f'''
            SELECT
                DATE(CaseDate) AS CaseDate, Name, Card, DiseaseCode1, DiseaseName1 FROM cases
            WHERE
                (PatientKey = {patient_key}) AND
                (CaseDate BETWEEN "{first_date}" AND "{end_date}") AND
                (InsType = "健保") AND
                (TreatType = "內科") AND
                (DiseaseCode1 = "{self.disease_code1}")
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)
        disease_count = len(rows)

        sql = f'''
            SELECT CaseKey FROM cases
            WHERE
                CaseKey = {self.medical_record["CaseKey"]} AND
                (DiseaseCode1 = "{self.disease_code1}")
        '''
        this_row = self.database.select_record(sql)
        if len(this_row) <= 0:  # 本次病歷尚未存檔，自己的次數也要算
            disease_count += 1

        error_message = []
        if disease_count > 3:
            error_message.append(f"本月內科同病名({self.disease_code1})超過3次")
            for row in rows:
                error_message.append(f"{row['CaseDate']}")

        if len(error_message) > 0:
            if self.system_settings.field("內科同病名超過3次存檔") == "無法存檔":
                system_utils.show_message_box(
                    QMessageBox.Critical,
                    "內科同病名次數檢查",
                    f"""
                        <font size="5" color="red">
                          <b>
                            {self._join_error_message(error_message)}
                          </b>
                        </font>
                    """,
                    "請調整病歷內容，以利健保申報.",
                )
                check_ok = False
            else:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Warning)
                msg_box.setWindowTitle("內科同病名次數檢查")
                msg_box.setText(
                    f"""
                        <font size="5" color="red">
                          <b>
                            {self._join_error_message(error_message)}
                          </b>
                        </font>
                    """,
                )
                msg_box.setInformativeText("請確定是否繼續存檔")
                msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
                msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
                save_file = msg_box.exec_()
                if save_file == QMessageBox.RejectRole:
                    check_ok = False

        return check_ok

    def _check_extension_code_a(self):
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        case_date = self.medical_record["CaseDate"]
        disease_code1 = self.disease_code1
        sql = f'''
            SELECT
                CaseDate FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate < "{case_date}") AND
                (InsType = "健保") AND
                (DiseaseCode1 = "{disease_code1}")
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None

        first_case_date = rows[0]["CaseDate"].date()
        case_date = self.medical_record["CaseDate"].date()
        delta = (case_date - first_case_date).days
        if delta > 30:
            days, hint = 30, "後遺症"
        elif delta > 15:
            days, hint = 15, "後續照護"
        else:
            return None

        message = f"""
            上次初期照護日期為{first_case_date}, 距離本次門診已超過{days}天, 應申報為{hint}
        """

        return message

    def _check_extension_code_d(self):
        new_disease_code1 = self.disease_code1[:6] + "A"  # 找出初診照護日期
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        case_date = self.medical_record["CaseDate"]

        sql = f'''
            SELECT
                CaseDate FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate < "{case_date}") AND
                (InsType = "健保") AND
                (DiseaseCode1 = "{new_disease_code1}")
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return "本次為損傷診斷首次, 應申報初診照護"

        first_case_date = rows[0]["CaseDate"].date()
        case_date = self.medical_record["CaseDate"].date()
        delta = (case_date - first_case_date).days
        if delta > 30:
            message = f"""
                上次初期照護日期為{first_case_date}, 距離本次門診已超過30天, 應申報為後遺症
            """
        elif delta <= 15:
            message = f"""
                上次初期照護日期為{first_case_date}, 距離本次門診尚未滿15天, 應申報為初診照護
            """
        else:
            return None

        return message

    def _check_extension_code_s(self):
        new_disease_code1 = self.disease_code1[:6] + "A"  # 找出初診照護日期
        case_key = self.medical_record["CaseKey"]
        patient_key = self.medical_record["PatientKey"]
        case_date = self.medical_record["CaseDate"]

        sql = f'''
            SELECT
                CaseDate FROM cases
            WHERE
                (CaseKey != {case_key}) AND
                (PatientKey = {patient_key}) AND
                (CaseDate < "{case_date}") AND
                (InsType = "健保") AND
                (DiseaseCode1 = "{new_disease_code1}")
            ORDER BY CaseDate LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return "本次為損傷診斷首次, 應申報初期照護"

        first_case_date = rows[0]["CaseDate"].date()
        case_date = self.medical_record["CaseDate"].date()
        delta = (case_date - first_case_date).days
        if delta <= 15:
            message = f"""
                上次初期照護日期為{first_case_date}, 距離本次門診尚未滿15天, 應申報為初診照護
            """
        elif delta <= 30:
            message = f"""
                上次初期照護日期為{first_case_date}, 距離本次門診已超過15天但尚未滿30天, 應申報為後續照護
            """
        else:
            return None

        return message

    def _check_pres_days(self):
        check_ok = True

        if self.pres_days <= 0:  # 沒開藥不用檢查
            return check_ok

        if self.medical_record["RegistType"] in nhi_utils.INFECTIOUS_TYPE:
            return check_ok

        message = registration_utils.check_prescription_finished(
            self.database,
            self.system_settings,
            self.medical_record["CaseKey"],
            self.patient_record["PatientKey"],
            self.medical_record["CaseDate"],
        )

        if message is not None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("用藥重複")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        用藥檢查錯誤如下:<br>
                        <br>
                        {message}
                      </b>
                    </font>
                """,
            )
            if "(用藥重複>=2日)" in message:
                msg_box.setInformativeText("用藥重複>=2日, 無法存檔.")
                msg_box.addButton(QPushButton("無法存檔"), QMessageBox.NoRole)
                msg_box.exec_()
                check_ok = False
            else:
                msg_box.setInformativeText("請注意用藥重複.")
                msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
                msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)

                save_file = msg_box.exec_()
                if save_file == QMessageBox.RejectRole:
                    check_ok = False

        return check_ok

    def _check_prescript(self):
        check_ok = True
        error_message = []

        total_dosage, infectious_drug = prescript_utils.get_total_dosage(
            self.table_widget_ins_prescript
        )
        if infectious_drug:
            return check_ok

        if total_dosage == 0:
            if self.pres_days > 0:
                error_message.append("未開藥但給藥天數 > 0")
            if self.packages > 0:
                error_message.append("未開藥但給藥包數 > 0")
            if self.instruction != "":
                error_message.append("未開藥但用藥指示非空白")
        else:
            if self.pres_days <= 0:
                error_message.append("給藥天數空白")

            if self.packages <= 0:
                error_message.append("給藥包數空白")
            elif self.packages >= 8:
                error_message.append("給藥包數超過8次")

            if self.instruction == "":
                error_message.append("用藥指示空白")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "給藥檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        給藥檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_infectious_drug_pres_days(self):
        check_ok = True
        error_message = []

        row_count = self.table_widget_ins_prescript.rowCount()

        if row_count <= 0:
            return check_ok

        use_infectious_drug = False
        for row_no in range(row_count):
            medicine_name_item = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name_item is None:
                continue

            medicine_name = medicine_name_item.text()
            if "清冠一號" in medicine_name:
                use_infectious_drug = True
                break

        case_date = self.medical_record["CaseDate"]
        case_date = case_date.strftime("%Y-%m-%d")
        if use_infectious_drug and case_date >= "2023-03-20" and self.pres_days > 5:
            error_message.append("2023-03-20日起，開立清冠一號不得超過一個療程(5天)")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "清冠一號開藥天數檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        清冠一號開藥天數檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_prescript_same_three_times(self):
        check_ok = True
        error_message = []

        if self.pres_days <= 0 or self.pres_days > 7:
            return check_ok

        patient_key = string_utils.xstr(self.patient_record["PatientKey"])
        case_date = self.medical_record["CaseDate"].date()
        end_date = (
            datetime.date(case_date.year, case_date.month, 1)
            - datetime.timedelta(days=1)
        ).replace(day=1)

        sql = f'''
            SELECT cases.CaseKey, cases.CaseDate, dosage.Days FROM cases
                LEFT JOIN dosage ON dosage.CaseKey = cases.CaseKey
            WHERE
                PatientKey = {patient_key} AND
                InsType = "健保" AND
                DATE(CaseDate) < "{case_date}" AND DATE(CaseDate) >= "{end_date}" AND
                (dosage.Days > 0) AND (dosage.Days <= 7)
                ORDER BY CaseDate DESC LIMIT 2
        '''
        rows = self.database.select_record(sql)
        if len(rows) < 2:
            return check_ok

        prescript_list = []
        current_list = []
        for row_no in range(self.table_widget_ins_prescript.rowCount()):
            medicine_name = self.table_widget_ins_prescript.item(
                row_no, prescript_utils.INS_PRESCRIPT_COL_NO["MedicineName"]
            )
            if medicine_name is None:
                continue

            medicine_name = medicine_name.text()
            current_list.append(medicine_name)

        prescript_list.append([case_date, current_list])

        for row in rows:
            case_key = row["CaseKey"]
            sql = f"""
                SELECT MedicineName FROM prescript
                WHERE
                    CaseKey = {case_key}
                ORDER BY PrescriptKey
            """
            prescript_rows = self.database.select_record(sql)
            current_list = []
            for prescript_row in prescript_rows:
                current_list.append(string_utils.xstr(prescript_row["MedicineName"]))

            prescript_list.append([row["CaseDate"].date(), current_list])

        if (
            sorted(prescript_list[0][1])
            == sorted(prescript_list[1][1])
            == sorted(prescript_list[2][1])
        ):
            error_message.append(f"""
                處方連續三次相同<br>
                本次處方: {",".join(prescript_list[0][1])}<br>
                {prescript_list[1][0]}: {",".join(prescript_list[1][1])}<br>
                {prescript_list[2][0]}: {",".join(prescript_list[2][1])}
            """)

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "處方重複給藥檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        七日以下的處方給藥檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "連續三次相同，審查醫師會認定為慢性病，請調整本次處方的藥品，以利健保抽審.",
            )
            check_ok = False

        return check_ok

    def _check_disease_self_payment(self):
        check_ok = True
        error_message = []

        disease_code_list = [
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
        ]

        for disease_code in disease_code_list:
            if disease_code == "":
                continue

            if disease_code[:3] in ["L67"]:
                error_message.append("白髮或髮色異常")
            elif disease_code[:4] in ["L812"]:
                error_message.append("雀斑")
            # elif disease_code[:3] in ['E65', 'E66']:
            #     error_message.append('肥胖症')
            # elif disease_code[:3] in ['H49', 'H50']:
            #     error_message.append('斜視')
            # elif disease_code[:4] in ['H521']:
            #     error_message.append('近視')
            # elif disease_code[:4] in ['H522']:
            #     error_message.append('散光')
            # elif disease_code[:4] in ['H524']:
            #     error_message.append('老花眼')

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}為健保中醫門診不給付項目之病名
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_disease_neat(self):
        check_ok = True

        case_date = self.medical_record["CaseDate"].strftime(
            "%Y-%m-%d"
        )  # 2024-10-01以前不要檢查
        if case_date <= "2024-09-30":
            return check_ok

        error_message = []

        disease_code_list = [
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
        ]

        for disease_code in disease_code_list:
            if disease_code in ["", None]:
                continue

            if not case_utils.is_disease_code_neat(self.database, disease_code):
                error_message.append(f"診斷碼 {disease_code} 非最細碼<br>")
            elif not case_utils.is_disease_code_exist(self.database, disease_code):
                if (
                    self.medical_record["CaseDate"].year >= 2016
                ):  # ICD-10-CM 2016年開始實施
                    error_message.append(f"診斷碼 {disease_code} 無效<br>")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_disease_duplicated(self):
        check_ok = True
        error_message = []

        disease_code_list = [
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
        ]

        disease_duplicate = [
            x for n, x in enumerate(disease_code_list) if x in disease_code_list[:n]
        ]
        if len(disease_duplicate) and "".join(disease_duplicate) != "":
            disease_duplicate = ", ".join(disease_duplicate)
            error_message.append(f"診斷碼 {disease_duplicate} 重複輸入<br>")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_special_code(self):
        check_ok = True
        error_message = []

        if (
            self.medical_record["Share"] in nhi_utils.INFECTIOUS_INJURY_TYPE
        ):  # 清冠一號開藥不受限制
            return check_ok

        if self.treatment != "":  # 有處置不受限制
            return check_ok

        if self.special_code != "" and self.pres_days < 7:
            error_message.append("慢性病開藥至少要七天")
        elif self.special_code == "" and self.pres_days > 7:
            error_message.append("非慢性病開藥不得超過七天")

        if len(error_message) > 0:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("診斷碼檢查錯誤")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定慢性病開藥天數是否正確.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False

        return check_ok

    def _check_strict_special_code(self):
        check_ok = True
        error_message = []

        if self.special_code != "" and 1 <= self.pres_days < 7:
            error_message.append("慢性病開藥至少要七天以上")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("診斷碼檢查錯誤")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請確定慢性病開藥天數是否正確.")
            msg_box.addButton(QPushButton("繼續存檔"), QMessageBox.YesRole)
            msg_box.addButton(QPushButton("取消"), QMessageBox.NoRole)
            save_file = msg_box.exec_()
            if save_file == QMessageBox.RejectRole:
                check_ok = False
        elif self.special_code == "" and self.pres_days > 7:
            error_message.append("非慢性病開藥不得超過七天")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("診斷碼檢查錯誤")
            msg_box.setText(
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼檢查錯誤如下:<br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
            )
            msg_box.setInformativeText("請更改開藥天數.")
            msg_box.addButton(QPushButton("確定"), QMessageBox.NoRole)
            msg_box.exec_()
            check_ok = False

        return check_ok

    # #################################### 以下已經作廢 ###########################################
    # 複雜性針灸檢查
    def _get_complicated_acupuncture_list_thread(self, out_queue, disease):
        complicated_acupuncture_list1 = nhi_utils.get_complicated_acupuncture_list(
            self.database, disease
        )

        out_queue.put((complicated_acupuncture_list1,))

    # 複雜性針灸檢查
    def _get_complicated_acupuncture_list(self, disease=1):
        message_box = dialog_utils.message_box(
            "複雜性針灸檢查",
            "複雜性針灸適應症病名檢查中...",
            "這樣會花費一些時間, 請稍後",
        )
        message_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(
            target=self._get_complicated_acupuncture_list_thread,
            args=(msg_queue, disease),
        )
        t.start()
        (complicated_acupuncture_list,) = msg_queue.get()
        message_box.close()

        return complicated_acupuncture_list

    # 複雜性針灸檢查
    def _check_complicated_acupuncture(self):
        check_ok = True
        error_message = []

        complicated_acupuncture_list1 = self._get_complicated_acupuncture_list(
            disease=1
        )

        if (
            self.disease_code1 in complicated_acupuncture_list1
            or self.disease_code2 in complicated_acupuncture_list1
            or self.disease_code3 in complicated_acupuncture_list1
            or self.disease_code4 in complicated_acupuncture_list1
        ):
            return check_ok

        if self.disease_code1 not in complicated_acupuncture_list1:
            error_message.append(f"主診斷碼{self.disease_code1}非複雜性針灸適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "複雜性針灸檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        複雜性針灸檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # #################################### 以上已經作廢 ###########################################

    # 中度複雜性針灸檢查
    def _check_moderate_complicated_acupuncture(self):
        check_ok = True
        error_message = []

        if not case_utils.is_moderate_complicated_acupuncture_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.moderate_complicated_acupuncture_list,
            self.parent.parent.special_disease_list,
        ):
            error_message.append("診斷碼無中度複雜性針灸適應症")

        if "中度針灸合併中度傷科" in self.treatment:
            if not case_utils.is_moderate_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無中度複雜性傷科適應症")

        if "中度針灸合併高度傷科" in self.treatment:
            if not case_utils.is_highly_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.highly_complicated_massage_list,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無高度複雜性傷科適應症")

        if "中度複雜性傷科合併特殊疾病" in self.second_treatment:
            if not case_utils.is_moderate_complicated_massage_with_special_disease_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無中度複雜性傷科合併特殊疾病適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                f"{self.treatment}檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        {self.treatment}檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 高度複雜性針灸檢查
    def _check_highly_complicated_acupuncture(self):
        check_ok = True
        error_message = []

        if not case_utils.is_highly_complicated_acupuncture_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.highly_complicated_acupuncture_list,
            self.parent.parent.moderate_complicated_acupuncture_list,
            self.parent.parent.special_disease_list,
        ):
            error_message.append("診斷碼無高度複雜性針灸適應症")

        if "高度針灸合併中度傷科" in self.treatment:
            if not case_utils.is_moderate_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無中度複雜性傷科適應症")

        if "高度針灸合併高度傷科" in self.treatment:
            if not case_utils.is_highly_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.highly_complicated_massage_list,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無高度複雜性傷科適應症")

        if "高針合併中傷" in self.treatment:
            if not case_utils.is_moderate_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無中度複雜性傷科適應症")

        if "高針合併高傷" in self.treatment:
            if not case_utils.is_highly_complicated_massage_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.highly_complicated_massage_list,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無高度複雜性傷科適應症")

        if "中度複雜性傷科合併特殊疾病" in self.second_treatment:
            if not case_utils.is_moderate_complicated_massage_with_special_disease_ok(
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
                self.parent.parent.moderate_complicated_massage_list,
                self.parent.parent.special_disease_list,
            ):
                error_message.append("診斷碼無中度複雜性傷科合併特殊疾病適應症")

        # 2025-05-02 陳立德
        if (
            "G82" in self.disease_code2
            or "G83" in self.disease_code2
            or "G82" in self.disease_code3
            or "G83" in self.disease_code3
            or "G82" in self.disease_code4
            or "G83" in self.disease_code4
        ):
            error_message.append("診斷碼G82或G83需放在主診斷碼")
        elif "G82" in self.disease_code1 or "G83" in self.disease_code1:
            if "B91" not in self.disease_code2:
                error_message.append(
                    "診斷碼G82或G83需合併B91<br>急性脊髓灰白質炎之後期影響併有提及麻痺性徵候(小兒麻痺症)"
                )

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                f"{self.treatment}檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        {self.treatment}檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # #################################### 以下已經作廢 ###########################################
    # 複雜性傷科檢查
    def _get_complicated_massage_list_thread(self, out_queue, disease):
        complicated_massage_list1 = nhi_utils.get_complicated_massage_list(
            self.database, disease
        )

        out_queue.put((complicated_massage_list1,))

    # 複雜性傷科檢查
    def _get_complicated_massage_list(self, disease=1):
        message_box = dialog_utils.message_box(
            "複雜性傷科檢查",
            "複雜性傷科適應症病名檢查中...",
            "這樣會花費一些時間, 請稍後",
        )
        message_box.show()

        msg_queue = Queue()
        QtCore.QCoreApplication.processEvents()

        t = Thread(
            target=self._get_complicated_massage_list_thread, args=(msg_queue, disease)
        )
        t.start()
        (complicated_massage_list,) = msg_queue.get()
        message_box.close()

        return complicated_massage_list

    # 複雜性傷科檢查
    def _check_complicated_massage(self):
        check_ok = True
        error_message = []

        complicated_massage_list1 = self._get_complicated_massage_list(disease=1)
        if (
            self.disease_code1 in complicated_massage_list1
            or self.disease_code2 in complicated_massage_list1
            or self.disease_code3 in complicated_massage_list1
            or self.disease_code4 in complicated_massage_list1
        ):
            return check_ok

        if self.disease_code1 not in complicated_massage_list1:
            error_message.append(f"主診斷碼{self.disease_code1}非複雜性傷科適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "複雜性傷科檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        複雜性傷科檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # #################################### 以上已經作廢 ###########################################

    # 中度複雜性傷科檢查
    def _check_moderate_complicated_massage(self):
        check_ok = True
        error_message = []

        if not case_utils.is_moderate_complicated_massage_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.moderate_complicated_massage_list,
            self.parent.parent.special_disease_list,
        ):
            error_message.append("診斷碼無中度複雜性傷科適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "中度複雜性傷科檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        中度複雜性傷科檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 傷科治療項目一次性檢查
    def _check_massage_treatment_once(self, treatment):
        check_ok = True
        error_message = []

        sql = f'''
            SELECT CaseDate FROM cases
            WHERE
                PatientKey = {self.medical_record["PatientKey"]} AND
                CaseDate < "{self.medical_record["CaseDate"].date()} 00:00:00" AND
                InsType = "健保" AND
                DiseaseCode1 = "{self.disease_code1}" AND
                Treatment = "{treatment}" AND
                RegistType NOT IN{tuple(nhi_utils.TOUR_MOUNTAIN_ISLAND)}
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            row = rows[0]
            error_message.append(
                f"已經在 {row['CaseDate'].date()} 執行過{treatment}處置"
            )

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "高度複雜性傷科檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        {treatment}檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "依健保規定，後續治療請改為一般傷科治療，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 高度複雜性傷科檢查
    def _check_highly_complicated_massage(self):
        check_ok = True
        error_message = []

        if not case_utils.is_highly_complicated_massage_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.highly_complicated_massage_list,
            self.parent.parent.moderate_complicated_massage_list,
            self.parent.parent.special_disease_list,
        ):
            error_message.append("診斷碼無高度複雜性傷科適應症")

        # if self.disease_code2 in [None, ""]:
        #     error_message.append("高度複雜性傷科(多部位損傷)需要兩個診斷碼")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "高度複雜性傷科檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        高度複雜性傷科檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 脫臼復位檢查
    def _check_dislocate(self):
        check_ok = True
        error_message = []

        if not case_utils.is_dislocate_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.dislocate_list,
        ):
            error_message.append("診斷碼無脫臼整復復位適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "脫臼整復復位檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        脫臼整復復位檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    # 骨折復位檢查
    def _check_fracture(self):
        check_ok = True
        error_message = []

        if not case_utils.is_fracture_ok(
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
            self.parent.parent.fracture_list,
        ):
            error_message.append("診斷碼無骨折復位適應症")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "骨折復位檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        骨折復位檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_ins_medicine(self):
        check_ok = True
        error_message = []

        if self.pres_days <= 0:  # 沒開藥不用檢查
            return check_ok

        ins_medicine = 0
        for row_no in range(self.table_widget_ins_prescript.rowCount()):
            ins_code = self.table_widget_ins_prescript.item(
                row_no,
                prescript_utils.INS_PRESCRIPT_COL_NO["InsCode"],
            )
            if ins_code is not None and ins_code.text() != "":
                ins_medicine += 1

        if ins_medicine <= 0:
            error_message.append("有健保開藥天數但無健保處方")

        if self.packages < 1:
            error_message.append("給藥包數不足1包")

        if self.pres_days < 2:
            if (
                self.medical_record["Share"] in nhi_utils.INFECTIOUS_TYPE
                or self.medical_record["Injury"] in nhi_utils.INFECTIOUS_TYPE
            ):
                pass
            else:
                error_message.append("給藥天數不足2日")
        elif self.pres_days > 30:
            regist_type = self.parent.tab_registration.comboBox_reg_type.currentText()
            if (
                self.medical_record["RegistType"] in nhi_utils.SPECIAL_PHARMACY_TYPE
                or regist_type in nhi_utils.SPECIAL_PHARMACY_TYPE
            ):
                pass
            else:
                error_message.append("給藥天數超過30日")

        if self.instruction in [None, ""]:
            error_message.append("服藥方式空白")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "健保藥品檢查錯誤",
                f"""
                    <font size="5" color="red">
                      <b>
                        健保藥品檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_highly_complicated_massage_duration(self):
        check_ok = True
        error_message = []

        case_date = self.medical_record["CaseDate"]
        patient_key = self.medical_record["PatientKey"]

        last_highly_complicated_massage_date = (
            case_utils.get_last_highly_complicated_massage_date(
                self.database,
                case_date,
                patient_key,
                self.disease_code1,
                self.disease_code2,
                self.disease_code3,
                self.disease_code4,
            )
        )

        if last_highly_complicated_massage_date is not None:
            error_message.append(
                f"已在{last_highly_complicated_massage_date}執行過高度複雜性傷科, 請更改治療方式"
            )

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "高度複雜性傷科",
                f"""
                    <font size="5" color="red">
                      <b>
                        高度複雜性傷科檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_invalid_gender_disease(self):
        check_ok = True
        error_message = []

        gender = string_utils.xstr(self.patient_record["Gender"])
        if gender not in ["男", "女"]:
            return check_ok

        disease_list = [
            self.disease_code1,
            self.disease_code2,
            self.disease_code3,
            self.disease_code4,
        ]
        for i in range(len(disease_list)):
            disease_code = disease_list[i]
            if disease_code == "":
                continue

            if gender == "男" and ("N7" <= disease_code[:2] <= "P9"):
                error_message.append(f"男性病患輸入女性病患診斷碼: {disease_code}")
            elif gender == "女" and ("N4" <= disease_code[:2] <= "N5"):
                error_message.append(f"女性病患輸入男性病患診斷碼: {disease_code}")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "診斷碼性別檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        診斷碼性別檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_complicated_acupuncture_treats(self):
        check_ok = True
        error_message = []

        treat_position = 0
        auxiliary_treat = 0
        treat_start_time = None
        treat_end_time = None
        treat_times = None
        for row_no in range(self.table_widget_ins_treat.rowCount()):
            treat_name = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )

            if treat_name is None:
                continue

            treat_name = treat_name.text()
            if "治療開始:" in treat_name:
                treat_start_time = True
            if "治療結束:" in treat_name:
                treat_end_time = True
            if "治療時間:" in treat_name:
                treat_times = True
            if "輔助治療:" in treat_name:
                auxiliary_treat += 1
            if "治療部位:" in treat_name:
                treat_position += 1
                position_name = treat_name.replace("治療部位:", "").strip()
                try:
                    _ = nhi_utils.POSITION_DICT[position_name]
                except Exception:
                    error_message.append(f"無此治療部位: {position_name}")

            if (
                self.treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
                and "治療時間:" in treat_name
            ):
                treat_name = string_utils.removeprefix(treat_name, "治療時間:")
                treat_name = string_utils.removesuffix(treat_name, "分鐘")
                if number_utils.get_integer(treat_name) < 20:
                    error_message.append("高度針灸治療時間不足20分鐘")

        if treat_start_time is None:
            error_message.append("無治療開始時間")
        if treat_end_time is None:
            error_message.append("無治療結束時間")
        if treat_times is None:
            error_message.append("無治療時間")
        if auxiliary_treat == 0:
            error_message.append("無輔助治療")
        if treat_position < 2:
            error_message.append("治療部位不足兩個")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "複雜性針灸處置檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        複雜性針灸處置檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_complicated_massage_treats(self):
        check_ok = True
        error_message = []

        treat_position = 0
        auxiliary_treat = 0
        treat_start_time = None
        treat_end_time = None
        treat_times = None
        for row_no in range(self.table_widget_ins_treat.rowCount()):
            treat_name = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )

            if treat_name is None:
                continue

            treat_name = treat_name.text()
            if "治療開始:" in treat_name:
                treat_start_time = True
            if "治療結束:" in treat_name:
                treat_end_time = True
            if "治療時間:" in treat_name:
                treat_times = True
            if "輔助治療:" in treat_name:
                auxiliary_treat += 1
            if "治療部位:" in treat_name:
                treat_position += 1

            if (
                self.treatment in nhi_utils.HIGHLY_COMPLICATED_MASSAGE_TREAT
                and "治療時間:" in treat_name
            ):
                treat_name = string_utils.removeprefix(treat_name, "治療時間:")
                treat_name = string_utils.removesuffix(treat_name, "分鐘")
                if number_utils.get_integer(treat_name) < 20:
                    error_message.append("高度傷科治療時間不足20分鐘")

        if treat_start_time is None:
            error_message.append("無治療開始時間")
        if treat_end_time is None:
            error_message.append("無治療結束時間")
        if treat_times is None:
            error_message.append("無治療時間")
        if auxiliary_treat == 0:
            error_message.append("無輔助治療")
        if treat_position == 0:
            error_message.append("無治療部位")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "複雜性傷科處置檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        複雜性傷科處置檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_merge_treats(self):
        if self.treatment in ["一般針灸", "電針"] and self.second_treatment in [
            "一般傷科"
        ]:
            return True

        check_ok = True
        error_message = []

        treat_position = 0
        auxiliary_treat = 0
        treat_start_time = None
        treat_end_time = None
        treat_times = None
        for row_no in range(self.table_widget_ins_treat.rowCount()):
            treat_name = self.table_widget_ins_treat.item(
                row_no, prescript_utils.INS_TREAT_COL_NO["MedicineName"]
            )

            if treat_name is None:
                continue

            treat_name = treat_name.text()
            if "治療開始:" in treat_name:
                treat_start_time = True
            if "治療結束:" in treat_name:
                treat_end_time = True
            if "治療時間:" in treat_name:
                treat_times = True
            if "輔助治療:" in treat_name:
                auxiliary_treat += 1
            if "治療部位:" in treat_name:
                treat_position += 1

            if treat_times and treat_name is not None and "治療時間" in treat_name:
                treat_name = string_utils.removeprefix(treat_name, "治療時間:")
                treat_name = string_utils.removesuffix(treat_name, "分鐘")

                if (
                    self.treatment in ["一般針灸", "電針", "中度複雜性針灸"]
                    and self.second_treatment in ["一般傷科", "中度複雜性傷科"]
                    and number_utils.get_integer(treat_name) < 10
                ):
                    error_message.append("治療時間不足10分鐘")
                elif (
                    self.treatment in ["一般針灸", "電針", "中度複雜性針灸"]
                    and self.second_treatment in ["高度複雜性傷科"]
                    and number_utils.get_integer(treat_name) < 20
                ):
                    error_message.append("治療時間不足20分鐘")
                elif (
                    self.treatment in ["高度複雜性針灸"]
                    and self.second_treatment in ["一般傷科", "中度複雜性傷科"]
                    and number_utils.get_integer(treat_name) < 20
                ):
                    error_message.append("治療時間不足20分鐘")
                elif (
                    self.treatment in ["高度複雜性針灸"]
                    and self.second_treatment
                    in [
                        "高度複雜性傷科",
                        "中度複雜性傷科合併特殊疾病",
                        "脫臼整復復位",
                        "骨折復位",
                    ]
                    and number_utils.get_integer(treat_name) < 20
                ):
                    error_message.append("治療時間不足20分鐘")

        if treat_start_time is None:
            error_message.append("無治療開始時間")
        if treat_end_time is None:
            error_message.append("無治療結束時間")
        if auxiliary_treat == 0:
            error_message.append("無輔助治療")
        if treat_position == 0:
            error_message.append("無治療部位")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "針傷合併治療處置檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        針傷合併治療處置檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_diagnostic_data_required(self):
        check_ok = True
        error_message = []

        if self.pres_days <= 0:  # 沒開藥不用檢查
            return check_ok

        if self.symptom in [None, ""]:
            error_message.append("未輸入主訴")
        if self.tongue in [None, ""]:
            error_message.append("未輸入舌診")
        if self.pulse in [None, ""]:
            error_message.append("未輸入脈象")
        # if self.distinguish in [None, '']:
        #     error_message.append('未輸入辨證')
        # if self.cure in [None, '']:
        #     error_message.append('未輸入治則')

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "必填欄位檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        病歷必填欄位檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    def _check_integrate_care(self):
        check_ok = True
        error_message = []

        if not self.integrate_care:
            return check_ok

        try:
            share_type = (
                self.parent.tab_registration.ui.comboBox_share_type.currentText()
            )
        except Exception:
            share_type = self.medical_record["Share"]

        if (
            self.medical_record["CaseDate"].date()
            < datetime.datetime.strptime("2023-03-01", "%Y-%m-%d").date()
        ):
            error_message.append(
                "整合醫療照護支付項目在2023-03-01生效, 在此之前請勿申報"
            )
        if self.disease_code2 == "":
            error_message.append("至少需要兩個以上的診斷碼")
        # if self.special_code == '':
        #     error_message.append('至少需要一個以上的慢性病診斷碼')
        if (
            self.treatment in ["", None]
            and self.special_code != ""
            and self.pres_days >= 1
            and self.pres_days <= 7
            and share_type != "重大傷病"
        ):  # 29類針傷專案不在此現 2024-03-25
            error_message.append("慢性病需開藥8天(含)以上")

        if (
            self.treatment in ["", None]
            and self.special_code == ""
            and self.pres_days >= 1
            and self.pres_days <= 7
            and share_type != "重大傷病"
        ):  # 29類針傷專案不在此現 2024-03-25
            error_message.append("一般疾病需開藥8天(含)以上")

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "整合醫療照護檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        整合醫療照護檢查錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請更正上述的錯誤，以利健保申報.",
            )
            check_ok = False

        return check_ok

    @staticmethod
    def _join_error_message(error_message):
        error_message = "<br>".join(error_message)

        return error_message

    def _check_acupuncture_level(self):
        check_ok = True
        error_message = []

        if self.course <= 1:
            return check_ok

        if self.treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT:  # 一般針灸不檢查
            return check_ok

        patient_key = self.medical_record["PatientKey"]
        case_date = self.medical_record["CaseDate"]
        last_months = datetime.date(
            case_date.year, case_date.month, 1
        ) - datetime.timedelta(30)
        start_date = last_months.replace(day=1).strftime("%Y-%m-%d 00:00:00")
        interval = case_date.date() - datetime.timedelta(1)
        end_date = f"{interval} 23:59:59"
        sql = f'''
            SELECT cases.Treatment FROM cases
            WHERE
                PatientKey = {patient_key} AND
                CaseDate BETWEEN "{start_date}" AND "{end_date}" AND
                Card = "{self.card}" AND
                Continuance = {self.course - 1}
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return check_ok

        previous_treatment = rows[0]["Treatment"]

        if (
            self.treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
            and previous_treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT
        ):
            error_message.append(
                "上次針灸治療為一般針灸，本次針灸治療不能為中度複雜性針灸"
            )
        elif (
            self.treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
            and previous_treatment in nhi_utils.GENERAL_ACUPUNCTURE_TREAT
        ):
            error_message.append(
                "上次針灸治療為一般針灸，本次針灸治療不能為高度複雜性針灸"
            )
        elif (
            self.treatment in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_LIST
            and previous_treatment in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_LIST
        ):
            error_message.append(
                "上次針灸治療為中度複雜性針灸，本次針灸治療不能為高度複雜性針灸"
            )

        if len(error_message) > 0:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "針灸複雜度檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                        針灸複雜度錯誤如下:<br>
                        <br>
                        {self._join_error_message(error_message)}
                      </b>
                    </font>
                """,
                "請注意! 針灸治療複雜度只能高度->中度->一般，不能提昇治療複雜度.",
            )
            check_ok = False

        return check_ok

    def _check_special_pharmacy_type(self, regist_type):
        check_ok = True

        if self.pres_days < 56:
            system_utils.show_message_box(
                QMessageBox.Critical,
                "慢性病連續處方箋檢查",
                f"""
                    <font size="5" color="red">
                      <b>
                       慢箋檢查如下:<br>
                        <br>
                        {regist_type}開藥不足56天.
                      </b>
                    </font>
                """,
                f"請注意! {regist_type}至少開藥56天.",
            )
            check_ok = False

        return check_ok

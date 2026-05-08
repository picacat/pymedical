# -*- coding: UTF-8 -*-
import json
import os

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from libs import (
    case_utils,
    charge_utils,
    class_utils,
    cshis_utils,
    date_utils,
    dialog_utils,
    nhi_utils,
    number_utils,
    patient_utils,
    registration_utils,
    string_utils,
    system_utils,
    ui_utils,
)


# 匯入居家藍芽資料 2022.08.29
class DialogImportHomeCare(QtWidgets.QDialog):
    # 初始化
    program_name = "匯入居家藍芽資料"

    def __init__(self, parent=None, *args):
        super(DialogImportHomeCare, self).__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]

        self.ui = None
        self.json_rows = []

        self.dialog_setting = {
            "dialog_executed": False,
            "current_date": None,
        }

        self._set_ui()
        self._set_signal()

        items = [
            "請求居家輕量藍牙就醫檔案",
            "下載居家輕量藍牙就醫資料",
            "匯入居家輕量藍牙就醫檔案",
        ]
        import_type, ok = QInputDialog.getItem(
            self, "匯入方式", "請選擇要匯入的方式", items, 0, False
        )

        if not ok:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()
            return

        if import_type == "匯入居家輕量藍牙就醫檔案":
            self._open_file_dialog()
        elif import_type == "請求居家輕量藍牙就醫檔案":
            self._request_file()
        else:
            self._import_from_nhi()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    # 設定GUI
    def _set_ui(self):
        self.ui = ui_utils.load_ui_file(ui_utils.UI_DIALOG_IMPORT_HOME_CARE, self)
        # database.setFixedSize(database.size())  # non resizable dialog
        system_utils.set_css(self, self.system_settings)
        system_utils.center_window(self)
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setText("匯入資料庫")
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).setText("取消")
        self.table_widget_medical_record = class_utils.get_table_widget(
            self.ui.tableWidget_medical_record, self.database
        )
        self.table_widget_medical_record.set_table_heading_width([770])

    # 設定信號
    def _set_signal(self):
        self.ui.buttonBox.accepted.connect(self.accepted_button_clicked)

    def accepted_button_clicked(self):
        self._import_to_database()

        self.close()

    def _request_file(self):
        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, self.program_name
        )

        if self.dialog_setting["dialog_executed"]:
            dialog.ui.calendarWidget.setSelectedDate(
                self.dialog_setting["current_date"]
            )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.dialog_setting["dialog_executed"] = True
        self.dialog_setting["current_date"] = dialog.ui.calendarWidget.selectedDate()

        dialog.deleteLater()

        year = self.dialog_setting["current_date"].year()
        month = self.dialog_setting["current_date"].month()
        day = self.dialog_setting["current_date"].day()

        file_date = f"{year - 1911:0>3}{month:0>2}{day:0>2}"
        self._nhi_dowload_b(file_date)
        system_utils.show_message_box(
            QMessageBox.Information,
            "資料請求完成",
            "<h3>正在向健保暑請求居家病歷檔案中, 請於五分鐘後再下載居家病歷檔案.</h3>",
            "資料請求完成",
        )
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()

    def _import_from_nhi(self):
        dialog = dialog_utils.get_dialog_calendar(
            self, self.database, self.system_settings, self.program_name
        )

        if self.dialog_setting["dialog_executed"]:
            dialog.ui.calendarWidget.setSelectedDate(
                self.dialog_setting["current_date"]
            )

        if not dialog.exec_():
            dialog.deleteLater()
            return

        self.dialog_setting["dialog_executed"] = True
        self.dialog_setting["current_date"] = dialog.ui.calendarWidget.selectedDate()

        dialog.deleteLater()

        year = self.dialog_setting["current_date"].year()
        month = self.dialog_setting["current_date"].month()
        day = self.dialog_setting["current_date"].day()

        file_date = f"{year - 1911:0>3}{month:0>2}{day:0>2}"
        sql = f'''
            SELECT * FROM system_log
            WHERE
                LogType = "居家輕量藍牙就醫資料" AND
                LogName = "{file_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            system_utils.show_message_box(
                QMessageBox.Warning,
                "尚未請求資料",
                "<h3>尚未向健保暑請求居家病歷檔案, 請先請求居家病歷檔案.</h3>",
                "請先請求資料",
            )
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()
            return

        row = rows[0]
        json_dict = json.loads(string_utils.xstr(row["Log"]))
        local_id = json_dict["local_id"]
        nhi_id = json_dict["nhi_id"]
        error_message = self._nhi_get_b(local_id, nhi_id)
        if error_message == "檔案下載成功":
            system_utils.show_message_box(
                QMessageBox.Information,
                "資料下載完成",
                "<h3>居家病歷資料下載完成, 請匯入居家病歷資料.</h3>",
                "資料下載完成",
            )
        self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()

    def _nhi_get_b(self, local_id, nhi_id):
        error_message = nhi_utils.NHI_GetB(self.system_settings, local_id, nhi_id)

        return error_message

    def _nhi_dowload_b(self, file_date):
        clinic_id = self.system_settings.field("院所代號")

        dest_file = os.path.join(
            nhi_utils.get_dir(self.system_settings, "申報路徑"),
            f"{clinic_id}-{file_date}-001.txt",
        )
        with open(dest_file, "w") as text_file:
            text_file.write("FORMAT=JSON\n")
            text_file.write(f"ORDER_DATE_S={file_date}\n")
            text_file.write(f"ORDER_DATE_E={file_date}\n")
            if self.system_settings.field("健保IC卡資料上傳格式") == "2.0":
                text_file.write("FILE_VERSION=v2")

        type_code = "33"  # 請求藍牙就醫資料
        local_id, nhi_id = nhi_utils.NHI_DownloadB(
            self.system_settings, type_code, dest_file
        )
        json_dict = {
            "local_id": local_id,
            "nhi_id": nhi_id,
        }
        json_str = json.dumps(json_dict)

        self.database.exec_sql(
            f'DELETE FROM system_log WHERE LogType = "居家輕量藍牙就醫資料" AND LogName = "{file_date}"'
        )

        fields = ["LogType", "LogName", "Log"]
        data = [
            "居家輕量藍牙就醫資料",
            file_date,
            json_str,
        ]
        self.database.insert_record("system_log", fields, data)

    def _open_file_dialog(self):
        options = QFileDialog.Options()

        file_name, _ = QFileDialog.getOpenFileName(
            self, "開啟病歷JSON檔", "*.json", "json 檔 (*.json);;", options=options
        )
        if not file_name:
            self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel).animateClick()
            return

        self._read_home_care_json(file_name)

    def _read_home_care_json(self, file_name):
        with open(file_name, encoding="big5", errors="ignore") as json_file:
            rows = json.load(json_file)
            for row in rows:
                self._set_medical_record(row)

        for i in range(0, self.ui.tableWidget_medical_record.rowCount()):
            self.ui.tableWidget_medical_record.setRowHeight(i, 800)

    def _get_symptom(self, json_dict):
        symptom = ""
        if string_utils.xstr(json_dict["subjective"]) not in ["", None]:
            symptom += f"主觀描述: {json_dict['subjective']}"

        if string_utils.xstr(json_dict["objective"]) not in ["", None]:
            symptom += f"客觀描述: {json_dict['objective']}"

        if string_utils.xstr(json_dict["assessment"]) not in ["", None]:
            symptom += f"評估: {json_dict['assessment']}"

        if string_utils.xstr(json_dict["memo"]) not in ["", None]:
            symptom += f"特別記載: {json_dict['memo']}"

        return symptom

    def _append_patient(self, json_dict):
        birthday = date_utils.nhi_date_to_west_date(json_dict["A13"])
        try:
            share_type = cshis_utils.INSURED_MARK_DICT[json_dict["pa_type"]]
        except Exception:
            share_type = "基層醫療"

        patient_name = json_dict["paname"]
        patient_id = json_dict["A12"]
        card_no = json_dict["A11"]
        gender = patient_utils.get_gender(patient_id[1])
        nationality = patient_utils.get_nationality(patient_id[1])
        init_date = date_utils.nhi_datetime_to_west_datetime(json_dict["A17"])

        fields = [
            "Name",
            "ID",
            "Gender",
            "Birthday",
            "CardNo",
            "InsType",
            "Nationality",
            "InitDate",
        ]
        data = [
            patient_name,
            patient_id,
            gender,
            birthday,
            card_no,
            share_type,
            nationality,
            init_date,
        ]

        patient_key = self.database.insert_record("patient", fields, data)

        return patient_key

    def _get_patient_key(self, json_dict):
        card_no = json_dict["A11"]
        patient_id = json_dict["A12"]

        sql = f'''
            SELECT PatientKey, CardNo FROM patient
            WHERE
                ID = "{patient_id}"
            LIMIT 1
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            patient_key = self._append_patient(json_dict)
        else:
            row = rows[0]
            patient_key = row["PatientKey"]
            if string_utils.xstr(row["CardNo"]) == "":
                sql = f'UPDATE patient SET CardNo = "{card_no}" WHERE PatientKey = {patient_key}'
                self.database.exec_sql(sql)

        return patient_key

    def _get_insury_type(self, json_dict):
        injury_dict = {
            "1": "職業傷害",
            "2": "職業病",
            "3": "普通傷害",
            "4": "普通疾病",
            "A": "天然災害",
            "W": "法定傳染病通報隔離",
        }

        injury_type = injury_dict[json_dict["d14"]]

        return injury_type

    def _get_patient_row(self, patient_key):
        sql = f"SELECT * FROM patient WHERE PatientKey = {patient_key}"
        row = self.database.select_record(sql)[0]

        return row

    def _get_patient_html(self, row):
        patient_row = self._get_patient_row(row["patient_key"])

        disease_code1 = string_utils.xstr(row["disease_code1"])
        disease_code2 = string_utils.xstr(row["disease_code2"])
        disease_code3 = string_utils.xstr(row["disease_code3"])

        disease_name1 = (
            f"主診斷: {case_utils.get_disease_name(self.database, disease_code1)}"
        )
        disease_name2 = (
            f"次診斷1: {case_utils.get_disease_name(self.database, disease_code2)}"
        )
        disease_name3 = (
            f"次診斷2: {case_utils.get_disease_name(self.database, disease_code3)}"
        )

        html = f"""
            <table style="border-collapse: collapse; border:1px #cccccc solid;" cellpadding="4" border="1">
                <tbody style="vertical-align: middle">
                    <tr>
                        <td>病歷號: {patient_row["PatientKey"]}</td>
                        <td>姓名: {patient_row["Name"]}</td>
                        <td>性別: {patient_row["Gender"]}</td>
                    </tr>
                    <tr>
                        <td>身份證 :{patient_row["ID"]}</td>
                        <td>保險身份 :{patient_row["InsType"]}</td>
                        <td>卡片號碼 :{patient_row["CardNo"]}</td>
                    </tr>
                    <tr>
                        <td colspan="2">
                            門診日期: {row["case_date"]}
                        </td>
                        <td>主治醫師: {row["doctor"]}</td>
                    </tr>
                    <tr>
                        <td>
                            安全模組: {row["sam_id"]}
                        </td>
                        <td colspan="2">
                            過卡簽章: {row["security_signature"]}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3">
                            就醫識別碼: {row["identification"]}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="3">
                            主訴: {row["symptom"]}
                        </td>
                    </tr>
                    <tr>
                        <td>
                            {disease_name1}
                        </td>
                        <td>
                            {disease_name2}
                        </td>
                        <td>
                            {disease_name3}
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2">
                            治療處置: {row["treatment"]}
                        </td>
                        <td>
                            治療簽章: {row["treatment_signature"]}
                        </td>
                    </tr>
                </tbody>
            </table>
        """

        return html

    def _set_medical_record(self, json_row):
        json_dict = json_row
        patient_key = self._get_patient_key(json_dict)
        try:
            share_type = cshis_utils.INSURED_MARK_DICT[json_dict["pa_type"]]
        except Exception:
            share_type = "基層醫療"

        injury_type = self._get_insury_type(json_dict)

        sam_id_tag = "<A16>"
        pos = string_utils.xstr(json_dict["ic_xml"]).find(sam_id_tag)
        if pos >= 0:
            sam_id = json_dict["ic_xml"][
                pos + len(sam_id_tag) : pos + len(sam_id_tag) + 12
            ]
        else:
            sam_id = None

        card = json_dict["A18"]
        if card == "NA":
            card = self._get_current_card(patient_key)

        treatment, treatment_signature = self._get_treatment(json_dict)
        try:
            disease_code1 = json_dict["icd"][0]["i10_code_p"]
        except Exception:
            disease_code1 = ""

        try:
            disease_code2 = (json_dict["icd"][0]["i10_code_s1"],)
        except Exception:
            disease_code2 = ""

        try:
            disease_code3 = (json_dict["icd"][0]["i10_code_s2"],)
        except Exception:
            disease_code3 = ""

        row = {
            "patient_key": patient_key,
            "case_date": date_utils.nhi_datetime_to_west_datetime(json_dict["A17"]),
            "doctor": json_dict["drname"],
            "treat_type": "居家醫療",
            "share_type": share_type,
            "injury_type": injury_type,
            "card": card,
            "sam_id": sam_id,
            "security_signature": json_dict["A22"],
            "identification": json_dict["enc"],
            "symptom": self._get_symptom(json_dict),
            "disease_code1": disease_code1,
            "disease_code2": disease_code2,
            "disease_code3": disease_code3,
            "treatment": treatment,
            "treatment_signature": treatment_signature,
            "prescript": self._get_prescript(json_dict),
        }
        self.json_rows.append(row)

        patient_html = self._get_patient_html(row)

        html = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body>
                    {patient_html}
                </body>
            </html>
        """

        row_no = self.ui.tableWidget_medical_record.rowCount()
        self.ui.tableWidget_medical_record.setRowCount(row_no + 1)
        text_edit = QtWidgets.QTextEdit(self.ui.tableWidget_medical_record)
        text_edit.setHtml(html)
        self.ui.tableWidget_medical_record.setCellWidget(row_no, 0, text_edit)

    def _get_treatment(self, json_dict):
        rows = json_dict["pres"]

        treatment = None
        treatment_signature = None
        for row in rows:
            if row["p01_2"] in ["B41", "B42", "D01", "D02"]:
                treatment = "一般針灸"
            elif row["p01_2"] in ["B43", "B44", "D03", "D04"]:
                treatment = "電針"
            elif row["p01_2"] in ["B45", "B46", "D05", "D06"]:
                treatment = "中度複雜性針灸"
            elif row["p01_2"] in ["D07", "D08"]:
                treatment = "高度複雜性針灸"
            elif row["p01_2"] in ["B53", "B54", "E01", "E02"]:
                treatment = "一般傷科"
            elif row["p01_2"] in ["E03", "E04"]:
                treatment = "中度複雜性傷科"
            elif row["p01_2"] in ["E05", "E06"]:
                treatment = "高度複雜性傷科"
            elif row["p01_2"] in ["B61", "B62", "B63"]:
                treatment = "脫臼整復復位"

            if treatment is not None and treatment_signature is None:
                treatment_signature = row["A79"]

        return treatment, treatment_signature

    def _get_prescript(self, json_dict):
        prescript = []

        return prescript

    def _import_to_database(self):
        for json_row in self.json_rows:
            case_key = self._write_cases(json_row)
            self._write_treatment_signature(case_key, json_row)
            self._write_ins_fee(case_key)

        system_utils.show_message_box(
            QMessageBox.Information,
            "JSON資料匯入完成",
            "<h3>病歷資料匯入完成.</h3>",
            "資料正確無誤",
        )

    def _write_treatment_signature(self, case_key, json_row):
        self.database.exec_sql(f"""
            DELETE FROM presextend
            WHERE
                PrescriptKey = {case_key} AND
                ExtendType = "處置簽章"
        """)
        fields = [
            "PrescriptKey",
            "ExtendType",
            "Content",
        ]
        data = [
            case_key,
            "處置簽章",
            json_row["treatment_signature"],
        ]
        self.database.insert_record("presextend", fields, data)

    def _write_ins_fee(self, case_key):
        sql = f"SELECT * FROM cases WHERE CaseKey = {case_key}"
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return

        row = rows[0]
        ins_fee = charge_utils.get_ins_fee(
            self.database,
            self.system_settings,
            case_key=case_key,
            reg_type=string_utils.xstr(row["RegistType"]),
            treat_type=string_utils.xstr(row["TreatType"]),
            share=string_utils.xstr(row["Share"]),
            course=0,
            pres_days=case_utils.get_pres_days(self.database, row["CaseKey"]),
            pharmacy_type=string_utils.xstr(row["PharmacyType"]),
            treatment=string_utils.xstr(row["Treatment"]),
            infectious_drug=None,
            isolation_position=None,
        )

        fields = [
            "DiagFee",
            "InterDrugFee",
            "PharmacyFee",
            "AcupunctureFee",
            "MassageFee",
            "DislocateFee",
            "InsTotalFee",
            "DiagShareFee",
            "DrugShareFee",
            "InsApplyFee",
            "AgentFee",
        ]
        data = [
            ins_fee["diag_fee"],
            ins_fee["drug_fee"],
            ins_fee["pharmacy_fee"],
            ins_fee["acupuncture_fee"],
            ins_fee["massage_fee"],
            ins_fee["dislocate_fee"],
            ins_fee["ins_total_fee"],
            ins_fee["diag_share_fee"],
            ins_fee["drug_share_fee"],
            ins_fee["ins_apply_fee"],
            ins_fee["agent_fee"],
        ]
        self.database.update_record("cases", fields, "CaseKey", case_key, data)

    def _get_security(self, json_row):
        security = case_utils.create_security_xml()

        upload_type = "1"  # 上傳格式
        treat_after_check = "1"  # 補卡註記

        security = case_utils.update_xml_doc(
            security, "registered_date", json_row["case_date"]
        )
        security = case_utils.update_xml_doc(security, "seq_number", json_row["card"])
        security = case_utils.update_xml_doc(
            security, "clinic_id", self.system_settings.field("院所代號")
        )
        security = case_utils.update_xml_doc(
            security, "security_signature", json_row["security_signature"]
        )
        security = case_utils.update_xml_doc(
            security, "identification", json_row["identification"]
        )
        security = case_utils.update_xml_doc(security, "sam_id", json_row["sam_id"])
        security = case_utils.update_xml_doc(security, "upload_type", upload_type)
        security = case_utils.update_xml_doc(
            security, "treat_after_check", treat_after_check
        )

        return security

    def _write_cases(self, json_row):
        patient_row = self._get_patient_row(json_row["patient_key"])
        case_date = date_utils.str_to_datetime(json_row["case_date"])
        case_time = case_date.strftime("%H:%M")
        period = registration_utils.get_current_period(self.system_settings, case_time)
        disease_code1 = json_row["disease_code1"]
        disease_code2 = json_row["disease_code2"]
        disease_code3 = json_row["disease_code3"]
        disease_name1 = case_utils.get_disease_name(self.database, disease_code1)
        disease_name2 = case_utils.get_disease_name(self.database, disease_code2)
        disease_name3 = case_utils.get_disease_name(self.database, disease_code3)

        security = self._get_security(json_row)

        fields = [
            "CaseDate",
            "DoctorDate",
            "ChargeDate",
            "PatientKey",
            "Name",
            "Visit",
            "RegistType",
            "Injury",
            "TreatType",
            "Share",
            "InsType",
            "Card",
            "Period",
            "ChargePeriod",
            "RegistNo",
            "ApplyType",
            "PharmacyType",
            "Symptom",
            "Treatment",
            "DiseaseCode1",
            "DiseaseName1",
            "DiseaseCode2",
            "DiseaseName2",
            "DiseaseCode3",
            "DiseaseName3",
            "Doctor",
            "Security",
            "DoctorDone",
            "ChargeDone",
        ]

        data = [
            case_date,
            case_date,
            case_date,
            patient_row["PatientKey"],
            patient_row["Name"],
            "複診",
            "一般門診",
            json_row["injury_type"],
            json_row["treat_type"],
            json_row["share_type"],
            "健保",
            json_row["card"],
            period,
            period,
            0,
            "申報",
            "申報" if self.system_settings.field("申報藥事服務費") == "Y" else "不申報",
            json_row["symptom"],
            json_row["treatment"],
            disease_code1,
            disease_name1,
            disease_code2,
            disease_name2,
            disease_code3,
            disease_name3,
            json_row["doctor"],
            security,
            "True",
            "True",
        ]

        case_key = self.database.insert_record("cases", fields, data)

        return case_key

    def _get_current_card(self, patient_key):
        sql = f"""
            SELECT Card FROM cases
            WHERE
                PatientKey = {patient_key} AND
                TreatType = "居家醫療"
            ORDER BY CaseKey DESC LIMIT 1
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return "NA"

        row = rows[0]
        card = string_utils.xstr(row["Card"])
        if len(card) == 4:
            card = f"{card}1"
        elif len(card) == 5:
            card1 = card[:4]
            card2 = number_utils.get_integer(card[4])
            card = f"{card1}{card2 + 1}"

        return card

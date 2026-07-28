from PyQt5 import QtCore, QtWidgets

from libs import (
    case_utils,
    charge_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    prescript_utils,
    string_utils,
)


# 資料檢查 2018.01.31
class InsApplyGenerateFile(QtWidgets.QMainWindow):
    # 初始化
    def __init__(self, parent=None, *args):
        super().__init__(parent)
        self.parent = parent
        self.database = args[0]
        self.system_settings = args[1]
        self.apply_year = args[2]
        self.apply_month = args[3]
        self.start_date = args[4]
        self.end_date = args[5]
        self.period = args[6]
        self.apply_type = args[7]
        self.clinic_id = args[8]
        self.pre_ins_apply = args[9]

        self.sequence = {
            "21": 0,
            "22": 0,
            "24": 0,
            "25": 0,
            "28": 0,
            "29": 0,
            "30": 0,
            "31": 0,
            "C5": 0,
            "B6": 0,
        }

        self.apply_date = f"{self.apply_year - 1911:0>3}{self.apply_month:0>2}"
        self.ui = None

        self._set_ui()
        self._set_signal()

    # 解構
    def __del__(self):
        self.close_all()

    # 關閉
    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    # 設定GUI
    def _set_ui(self):
        pass

    # 設定信號
    def _set_signal(self):
        pass

    def generate_ins_file(self):
        self._delete_existing_data()
        rows = self._get_medical_records()
        self._create_ins_records(rows)

    def _delete_existing_data(self):
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]
        sql = f'''
            DELETE FROM insapply
            WHERE
                (ClinicID = "{self.clinic_id}") AND
                (ApplyDate = "{self.apply_date}") AND
                (ApplyPeriod = "{self.period}") AND
                (ApplyType = "{apply_type}")
        '''
        self.database.exec_sql(sql)

    def _get_medical_records(self):
        start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")
        apply_type_sql = nhi_utils.get_apply_type_sql(
            self.apply_type
        )  # 只取得申報類別為申報或補報的資料,不申報不讀取

        sql = f'''
            SELECT
                cases.*, patient.Birthday, patient.ID
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                ({apply_type_sql})
            ORDER BY CaseDate
        '''
        rows = self.database.select_record(sql)

        return rows

    def _create_ins_records(self, rows):
        record_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生申報檔中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        for row_no, row in enumerate(rows):
            progress_dialog.setValue(row_no)
            if progress_dialog.wasCanceled():
                break

            if string_utils.xstr(row["Card"]) == "欠卡":  # 欠卡不報
                continue

            if string_utils.xstr(row["TreatType"]) == "腦血管疾病":
                ins_apply_row = self._need_merge_brain_record(row)
            elif string_utils.xstr(row["TreatType"]) == "居家醫療":
                ins_apply_row = self._need_merge_home_care_record(row)
            else:
                ins_apply_row = self._need_merge_record(row)

            if ins_apply_row is None:
                pres_days = case_utils.get_pres_days(self.database, row["CaseKey"])
                case_type = self._write_ins_record(row)
                if case_type in [
                    "C5"
                ]:  # 2022.05.10 法定傳染病多寫一筆清冠一號藥品補助費
                    self._write_ins_record(row, case_c5=True)

                if (
                    case_type in ["24", "29"]
                    and number_utils.get_integer(pres_days) > 30
                ):  # 2023.10.18 慢性病連續處方箋
                    self._write_ins_record(row, case_28=True)
            else:
                self._rewrite_ins_record(ins_apply_row, row)

        progress_dialog.setValue(record_count)
        progress_dialog.deleteLater()

    # 檢查是否需要合併病歷 (腦血管疾病案件)
    def _need_merge_brain_record(self, row):
        ins_apply_row = None
        patient_key = number_utils.get_integer(row["PatientKey"])
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]

        sql = f'''
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                CaseType = "30"
        '''
        ins_apply_rows = self.database.select_record(sql)
        if len(ins_apply_rows) > 0:
            ins_apply_row = ins_apply_rows[0]

        return ins_apply_row

    # 檢查是否需要合併病歷 (居家醫療案件)
    def _need_merge_home_care_record(self, row):
        ins_apply_row = None
        patient_key = number_utils.get_integer(row["PatientKey"])
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]

        sql = f'''
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                CaseType = "31"
        '''
        ins_apply_rows = self.database.select_record(sql)
        if len(ins_apply_rows) > 0:
            ins_apply_row = ins_apply_rows[0]

        return ins_apply_row

    # 檢查是否需要合併病歷 (一般或療程案件)
    def _need_merge_record(self, row):
        ins_apply_row = None

        course = number_utils.get_integer(row["Continuance"])
        if course <= 1:
            return ins_apply_row

        patient_key = number_utils.get_integer(row["PatientKey"])
        card = string_utils.xstr(row["Card"])[:5]
        course = string_utils.xstr(course)
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]

        # 找出同卡序且有執行療程首次的病歷
        sql = f'''
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                Card = "{card}" AND
                TreatCode1 IS NOT NULL AND
                TreatCode{course} IS NULL
        '''
        ins_apply_rows = self.database.select_record(sql)

        if len(ins_apply_rows) <= 0:  # 首次不在本月
            sql = f'''
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                Card = "{card}" AND
                TreatCode{course} IS NULL
            '''
            ins_apply_rows = self.database.select_record(sql)

        if len(ins_apply_rows) > 0:
            ins_apply_row = ins_apply_rows[0]

        return ins_apply_row

    def _is_patient_new_care_record_exists(self, patient_key):
        sql = f"""
            SELECT PatientKey FROM patient_new_care
            WHERE
                PatientKey = {patient_key}
            LIMIT 1
        """
        rows = self.database.select_record(sql)
        return len(rows) > 0

    def _check_case_error(self, row, first_visit, share_code):
        message = []
        doctor_name = string_utils.xstr(row["Doctor"]).replace(",", "")
        doctor_id = personnel_utils.get_person_field_value(
            self.database, doctor_name, "ID"
        )
        doctor_count = personnel_utils.get_person_field_count(
            self.database, doctor_name
        )
        if doctor_count >= 2:
            message.append(f"{doctor_name}醫師使用者資料重複")

        disease_code1 = string_utils.xstr(row["DiseaseCode1"])
        disease_code2 = string_utils.xstr(row["DiseaseCode2"])
        disease_code3 = string_utils.xstr(row["DiseaseCode3"])
        disease_code4 = string_utils.xstr(row["DiseaseCode4"])

        disease_list = [disease_code1, disease_code2, disease_code3, disease_code4]

        if row["Name"] is None:
            message.append("病患空白")
        if row["Birthday"] is None:
            message.append("病患生日空白")
        if row["ID"] is None:
            message.append("病患身份證空白")
        if row["Card"] is None:
            message.append("卡序空白")
        if string_utils.xstr(row["Card"]) == "欠卡":
            message.append("欠卡")
        if row["DiseaseCode1"] is None:
            message.append("主診斷碼空白")
        if share_code in ["", None]:
            message.append("負擔碼空白")

        for i, disease_code in enumerate(disease_list):
            if disease_code != "" and not case_utils.is_disease_code_exist(
                self.database, disease_code
            ):
                message.append(f"病名{i + 1}非ICD10碼")

        if doctor_name == "":
            message.append("醫師姓名空白")
        if doctor_id in ["", None]:
            message.append("醫師身份證空白")
        if first_visit == "初診照護" and not self._is_patient_new_care_record_exists(
            row["PatientKey"]
        ):
            message.append("初診照護病歷空白")

        return message

    def _write_ins_record(self, row, case_c5=False, case_28=False):
        case_key = row["CaseKey"]
        special_code = nhi_utils.get_special_code(
            self.database, self.system_settings, case_key
        )
        pres_days = case_utils.get_pres_days(self.database, case_key)
        treat_records = nhi_utils.get_treat_records(self.database, row)
        doctor_name = string_utils.xstr(row["Doctor"]).replace(",", "")
        regist_type = string_utils.xstr(row["RegistType"])
        treat_type = string_utils.xstr(row["TreatType"])
        share_type = string_utils.xstr(row["Share"])
        apply_type = string_utils.xstr(row["ApplyType"])
        case_start_date = nhi_utils.get_start_date(self.database, row)

        drug_fee = number_utils.get_integer(row["InterDrugFee"])
        if string_utils.xstr(row["TreatType"]) in ["腦血管疾病"]:
            treat_fee = treat_records[0]["TreatFee"]
        else:
            treat_fee = (
                number_utils.get_integer(row["AcupunctureFee"])
                + number_utils.get_integer(row["MassageFee"])
                + number_utils.get_integer(row["DislocateFee"])
                + number_utils.get_integer(row["ExamFee"])
            )

        diag_code = nhi_utils.get_diag_code(
            self.database,
            self.system_settings,
            doctor_name,
            regist_type,
            treat_type,
            number_utils.get_integer(row["DiagFee"]),
        )
        # 重新計算實際診察費 (病歷檔內診察費預設為第一段，僅供參考用)
        diag_fee = charge_utils.get_ins_fee_from_ins_code(
            self.database, diag_code, case_date=case_start_date
        )
        diag_fee = charge_utils.check_markup_diag_fee(
            diag_fee, string_utils.xstr(row["RegistType"])
        )  # 檢查診察費是否需要加成

        # if string_utils.xstr(row['RegistType']) in nhi_utils.TOUR_TYPE:
        #     diag_fee = number_utils.get_integer(diag_fee * 1.1)  # 巡迴醫療診察費加成10%
        # elif string_utils.xstr(row['RegistType']) in nhi_utils.CORRECTION_REG_TYPE:
        #     diag_fee = number_utils.get_integer(diag_fee * 1.1)  # 矯正機關內門診診察費加成10%

        if string_utils.xstr(row["TreatType"]) in nhi_utils.HOME_CARE:  # 居家醫療
            treat_fee += diag_fee  # home care redefine diag_fee --> treat_fee
            diag_fee = 0
            diag_code = None

        pharmacy_code = nhi_utils.get_pharmacy_code(
            self.system_settings,
            row,
            pres_days,
        )
        pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])

        ins_total_fee = drug_fee + treat_fee + diag_fee + pharmacy_fee

        diag_share_fee = number_utils.get_integer(row["DiagShareFee"])
        drug_share_fee = number_utils.get_integer(row["DrugShareFee"])
        # if drug_share_fee > 200:
        #     drug_share_fee = 200

        # 非山地離島居家醫療
        if (
            treat_type in nhi_utils.HOME_CARE
            and regist_type not in nhi_utils.TOUR_TYPE
            and share_type in ["基層醫療"]
        ):
            diag_share_fee = (ins_total_fee - drug_fee - pharmacy_fee) * 5 / 100
            # 居家醫療部份負擔為申報金額扣除藥費藥服費後的5%

        if self.system_settings.field("申報初診照護") == "Y":
            first_visit = nhi_utils.get_visit(self.database, row)
        else:
            first_visit = None

        card = string_utils.xstr(row["Card"])
        if case_c5:
            case_type = "C5"
            first_visit = None
        elif case_28:
            case_type = "28"
            if pres_days == 60:
                pres_days -= 30
            elif pres_days == 56:
                pres_days -= 28
            else:
                pres_days -= 30

            diag_code = None
            pharmacy_code = "000000"
            card = "IC02"
            diag_fee = 0
            treat_fee = 0
            pharmacy_fee = 0
            diag_share_fee = 0
            drug_share_fee = 0

            drug_fee = charge_utils.get_ins_drug_fee(
                self.database, pres_days, case_date=case_start_date
            )
            ins_total_fee = drug_fee
        else:
            case_type = nhi_utils.get_case_type(
                self.database, self.system_settings, row, diag_fee, ins_total_fee
            )
            if pres_days > 30:  # 2024.05.18 慢性病連續處方箋
                if pres_days == 56:
                    pres_days = 28  # 拆成兩筆
                elif pres_days == 60:
                    pres_days = 30
                else:
                    pres_days = 30

                ins_total_fee -= drug_fee  # 調整慢箋首次的藥費
                drug_fee = charge_utils.get_ins_drug_fee(
                    self.database, pres_days, case_date=case_start_date
                )
                ins_total_fee += drug_fee

        share_fee = diag_share_fee + drug_share_fee
        ins_apply_fee = ins_total_fee - share_fee

        sequence = self._get_sequence(case_type)

        share_code = nhi_utils.get_share_code(  # 內含2020.10 新制
            self.database,
            case_start_date,
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["Treatment"]),
            number_utils.get_integer(row["Continuance"]),
            drug_fee,
            diag_share_fee,
            drug_share_fee,
            row,
        )
        # if share_code == 'S24' and \
        #         case_type == '29' and special_code[0] == 'C4' and diag_fee == 0:
        #     share_code = 'S20'
        if case_28:
            share_code = "009"

        agent_fee = charge_utils.get_ins_agent_fee(
            self.database,
            self.system_settings,
            string_utils.xstr(row["Share"]),
            string_utils.xstr(row["Treatment"]),
            number_utils.get_integer(row["Continuance"]),
            drug_fee,
        )

        message = self._check_case_error(row, first_visit, share_code)
        if ins_apply_fee <= 0:
            message.append("申報金額<= 0")

        if case_type == "21":
            for code in special_code:
                if code in ["C3", "C4"]:
                    message.append("21類申報針傷處置")
                    break

        infectious_drug = prescript_utils.get_infectious_drug(self.database, case_key)
        if case_type == "C5":
            drug_fee = 0
            pharmacy_fee = 0

            if not case_c5:  # 遠距診療費
                isolation_position = case_utils.get_case_extend(
                    self.database, case_key, "隔離處所"
                )
                if isolation_position in ["防疫旅館", "醫院", "集檢所"]:
                    treat_fee = 0  # 不可申報遠距診療費
                else:
                    diag_code = None
                    diag_fee = 0
                    treat_fee = charge_utils.get_ins_fee_from_ins_code(
                        self.database, "E5204C", case_date=case_start_date
                    )  # 遠距診療費

                if infectious_drug in ["台灣清冠一號及科學中藥", "科學中藥"]:
                    drug_fee = charge_utils.get_ins_drug_fee(self.database, pres_days)
                    pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
                elif infectious_drug in ["台灣清冠一號"]:
                    pharmacy_code = "000000"

                ins_total_fee = diag_fee + drug_fee + pharmacy_fee + treat_fee
            else:  # 清冠一號藥品補助費
                diag_code = None  # 清冠一號只能申報藥品補助費
                diag_fee = 0
                diag_share_fee, drug_share_fee, share_fee = 0, 0, 0
                share_code = "914"
                pharmacy_code = "000000"

                if infectious_drug in [
                    "台灣清冠一號及科學中藥",
                    "台灣清冠一號",
                ]:  # 台灣清冠一號藥品補助費
                    infectious_drug_fee = charge_utils.get_ins_fee_from_ins_code(
                        self.database, "E5012C", case_date=case_start_date
                    )
                    treat_fee = infectious_drug_fee * pres_days
                else:  # 未開清冠一號不要產生紀錄
                    return

                ins_total_fee = treat_fee

            ins_apply_fee = ins_total_fee
        elif infectious_drug in ["台灣清冠一號", "台灣清冠一號及科學中藥"]:
            treat_fee = 0
            drug_fee = 0
            if infectious_drug in ["台灣清冠一號及科學中藥"]:
                drug_fee = charge_utils.get_ins_drug_fee(self.database, pres_days)
                pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
            elif infectious_drug in ["台灣清冠一號"]:
                pharmacy_code = "000000"
                pharmacy_fee = 0

            ins_total_fee = diag_fee + drug_fee + pharmacy_fee + treat_fee
            ins_apply_fee = ins_total_fee - share_fee

        if apply_type == "補報差額":
            if case_utils.get_case_extend(self.database, case_key, "補報診察費") == "Y":
                pass
            else:
                diag_code = None
                diag_fee = 0

            if case_utils.get_case_extend(self.database, case_key, "補報藥費費") == "Y":
                pass
            else:
                drug_fee = 0

            if case_utils.get_case_extend(self.database, case_key, "補報調劑費") == "Y":
                pass
            else:
                pharmacy_code = "000000"
                pharmacy_fee = 0

            if case_utils.get_case_extend(self.database, case_key, "補報診療費") == "Y":
                pass
            else:
                treat_fee = 0

            ins_total_fee = drug_fee + treat_fee + diag_fee + pharmacy_fee
            ins_apply_fee = ins_total_fee

        doctor_id = personnel_utils.get_person_field_value(
            self.database, doctor_name, "ID"
        )
        pharmacist_id = nhi_utils.get_pharmacist_id(
            self.database, self.system_settings, row
        )

        identifier = case_utils.extract_security_xml(row["Security"], "就醫識別碼")
        original_identifier = None
        if number_utils.get_integer(row["Continuance"]) >= 2:
            original_security = case_utils.get_first_course_field(
                self.database,
                row["CaseDate"],
                row["PatientKey"],
                card,
                "Security",
            )
            original_identifier = case_utils.extract_security_xml(
                original_security, "就醫識別碼"
            )

        actual_identifier = case_utils.get_case_extend(
            self.database, case_key, "原就醫識別碼"
        )

        fields = [
            "ClinicID",
            "ApplyDate",
            "ApplyPeriod",
            "ApplyType",
            "CaseType",
            "Sequence",
            "SpecialCode1",
            "SpecialCode2",
            "SpecialCode3",
            "SpecialCode4",
            "Class",
            "CaseDate",
            "StopDate",
            "Birthday",
            "ID",
            "Card",
            "Injury",
            "ShareCode",
            "Visit",
            "DiseaseCode1",
            "DiseaseCode2",
            "DiseaseCode3",
            "DiseaseCode4",
            "PresDays",
            "PresType",
            "DoctorName",
            "DoctorID",
            "PharmacistID",
            "DrugFee",
            "TreatFee",
            "DiagCode",
            "DiagFee",
            "PharmacyCode",
            "PharmacyFee",
            "InsTotalFee",
            "ShareFee",
            "DiagShareFee",
            "DrugShareFee",
            "InsApplyFee",
            "AgentFee",
            "PatientKey",
            "Name",
            "Identifier",
            "OriginalIdentifier",
            "ActualIdentifier",
            "CaseKey1",
            "TreatCode1",
            "TreatFee1",
            "Percent1",
            "CaseKey2",
            "TreatCode2",
            "TreatFee2",
            "Percent2",
            "CaseKey3",
            "TreatCode3",
            "TreatFee3",
            "Percent3",
            "CaseKey4",
            "TreatCode4",
            "TreatFee4",
            "Percent4",
            "CaseKey5",
            "TreatCode5",
            "TreatFee5",
            "Percent5",
            "CaseKey6",
            "TreatCode6",
            "TreatFee6",
            "Percent6",
            "CaseKey7",
            "TreatCode7",
            "TreatFee7",
            "Percent7",
            "CaseKey8",
            "TreatCode8",
            "TreatFee8",
            "Percent8",
            "CaseKey9",
            "TreatCode9",
            "TreatFee9",
            "Percent9",
            "CaseKey10",
            "TreatCode10",
            "TreatFee10",
            "Percent10",
            "CaseKey11",
            "TreatCode11",
            "TreatFee11",
            "Percent11",
            "CaseKey12",
            "TreatCode12",
            "TreatFee12",
            "Percent12",
            "CaseKey13",
            "TreatCode13",
            "TreatFee13",
            "Percent13",
            "CaseKey14",
            "TreatCode14",
            "TreatFee14",
            "Percent14",
            "CaseKey15",
            "TreatCode15",
            "TreatFee15",
            "Percent15",
            "Message",
        ]

        data = [
            self.clinic_id,
            self.apply_date,
            self.period,
            nhi_utils.APPLY_TYPE_DICT[self.apply_type],
            case_type,
            sequence,
            special_code[0],
            special_code[1],
            special_code[2],
            special_code[3],
            nhi_utils.INS_CLASS,
            case_start_date,
            row["CaseDate"].date(),
            row["Birthday"],
            string_utils.xstr(row["ID"]),
            card,
            nhi_utils.INJURY_DICT[string_utils.xstr(row["Injury"])],
            share_code,
            first_visit,
            string_utils.xstr(row["DiseaseCode1"]),
            string_utils.xstr(row["DiseaseCode2"]),
            string_utils.xstr(row["DiseaseCode3"]),
            string_utils.xstr(row["DiseaseCode4"]),
            pres_days,
            nhi_utils.get_pres_type(pres_days),
            doctor_name,
            doctor_id,
            pharmacist_id,
            drug_fee,
            treat_fee,
            diag_code,
            diag_fee,
            pharmacy_code,
            pharmacy_fee,
            ins_total_fee,
            share_fee,
            diag_share_fee,
            drug_share_fee,
            ins_apply_fee,
            agent_fee,  # number_utils.get_integer(row['AgentFee']), 2022.09.11 新制
            number_utils.get_integer(row["PatientKey"]),
            string_utils.xstr(row["Name"]),
            identifier,
            original_identifier,
            actual_identifier,
            treat_records[0]["CaseKey"],
            treat_records[0]["TreatCode"],
            treat_records[0]["TreatFee"],
            treat_records[0]["Percent"],
            treat_records[1]["CaseKey"],
            treat_records[1]["TreatCode"],
            treat_records[1]["TreatFee"],
            treat_records[1]["Percent"],
            treat_records[2]["CaseKey"],
            treat_records[2]["TreatCode"],
            treat_records[2]["TreatFee"],
            treat_records[2]["Percent"],
            treat_records[3]["CaseKey"],
            treat_records[3]["TreatCode"],
            treat_records[3]["TreatFee"],
            treat_records[3]["Percent"],
            treat_records[4]["CaseKey"],
            treat_records[4]["TreatCode"],
            treat_records[4]["TreatFee"],
            treat_records[4]["Percent"],
            treat_records[5]["CaseKey"],
            treat_records[5]["TreatCode"],
            treat_records[5]["TreatFee"],
            treat_records[5]["Percent"],
            treat_records[6]["CaseKey"],
            treat_records[6]["TreatCode"],
            treat_records[6]["TreatFee"],
            treat_records[6]["Percent"],
            treat_records[7]["CaseKey"],
            treat_records[7]["TreatCode"],
            treat_records[7]["TreatFee"],
            treat_records[7]["Percent"],
            treat_records[8]["CaseKey"],
            treat_records[8]["TreatCode"],
            treat_records[8]["TreatFee"],
            treat_records[8]["Percent"],
            treat_records[9]["CaseKey"],
            treat_records[9]["TreatCode"],
            treat_records[9]["TreatFee"],
            treat_records[9]["Percent"],
            treat_records[10]["CaseKey"],
            treat_records[10]["TreatCode"],
            treat_records[10]["TreatFee"],
            treat_records[10]["Percent"],
            treat_records[11]["CaseKey"],
            treat_records[11]["TreatCode"],
            treat_records[11]["TreatFee"],
            treat_records[11]["Percent"],
            treat_records[12]["CaseKey"],
            treat_records[12]["TreatCode"],
            treat_records[12]["TreatFee"],
            treat_records[12]["Percent"],
            treat_records[13]["CaseKey"],
            treat_records[13]["TreatCode"],
            treat_records[13]["TreatFee"],
            treat_records[13]["Percent"],
            treat_records[14]["CaseKey"],
            treat_records[14]["TreatCode"],
            treat_records[14]["TreatFee"],
            treat_records[14]["Percent"],
            ", ".join(message),
        ]

        self.database.insert_record("insapply", fields, data)

        if row["CaseDate"].strftime("%Y-%m-%d") >= "2023-03-20" and infectious_drug in [
            "台灣清冠一號及科學中藥",
            "台灣清冠一號",
        ]:
            case_type = "C5"

        return case_type

    def _rewrite_ins_record(self, ins_apply_row, case_row):
        ins_apply_key = number_utils.get_integer(ins_apply_row["InsApplyKey"])
        pres_days = case_utils.get_pres_days(self.database, case_row["CaseKey"])
        case_start_date = ins_apply_row["CaseDate"]

        pres_type = string_utils.xstr(ins_apply_row["PresType"])
        if pres_type == "2" and pres_days > 0:  # 首次未開處方, 但療程有開處方
            pres_type = nhi_utils.get_pres_type(pres_days)

        treat_records = nhi_utils.get_treat_records(
            self.database, case_row, ins_apply_row
        )

        if string_utils.xstr(case_row["TreatType"]) in nhi_utils.AUXILIARY_CARE_TREAT:
            treat_fee = treat_records[0]["TreatFee"]
            ins_total_fee = (  # 重新計算申報總金額, 須扣除病歷內的處置費及原本申報金額的處置費, 再加上新的處置費
                number_utils.get_integer(ins_apply_row["InsTotalFee"])
                + number_utils.get_integer(case_row["InterDrugFee"])
                + number_utils.get_integer(case_row["PharmacyFee"])
                + treat_fee
                - number_utils.get_integer(ins_apply_row["TreatFee"])
            )
        else:
            treat_fee = (
                number_utils.get_integer(ins_apply_row["TreatFee"])
                + number_utils.get_integer(case_row["AcupunctureFee"])
                + number_utils.get_integer(case_row["MassageFee"])
                + number_utils.get_integer(case_row["DislocateFee"])
                + number_utils.get_integer(case_row["ExamFee"])
            )
            if string_utils.xstr(case_row["TreatType"]) in nhi_utils.HOME_CARE:
                treat_fee += number_utils.get_integer(
                    case_row["DiagFee"]
                )  # home care redefine diag_fee --> treat_fee

            ins_total_fee = number_utils.get_integer(
                ins_apply_row["InsTotalFee"]
            ) + number_utils.get_integer(case_row["InsTotalFee"])

        diag_share_fee = number_utils.get_integer(
            ins_apply_row["DiagShareFee"]
        ) + number_utils.get_integer(case_row["DiagShareFee"])
        drug_share_fee = number_utils.get_integer(
            ins_apply_row["DrugShareFee"]
        ) + number_utils.get_integer(case_row["DrugShareFee"])
        # if drug_share_fee > 200:
        #     drug_share_fee = 200

        share_fee = diag_share_fee + drug_share_fee

        # 不能更改醫師，要以首次為主, 因為會有護理師診察費的問題
        # doctor_name = string_utils.xstr(case_row['Doctor']).replace(',', '')
        # doctor_id = personnel_utils.get_person_field_value(
        #     self.database, doctor_name, 'ID'
        # )
        drug_fee = number_utils.get_integer(
            ins_apply_row["DrugFee"]
        ) + number_utils.get_integer(case_row["InterDrugFee"])

        if string_utils.xstr(case_row["TreatType"]) in nhi_utils.HOME_CARE:
            pharmacy_code = nhi_utils.get_home_care_pharmacy_code(
                self.database,
                self.system_settings,
                treat_records,
            )
        else:
            pharmacy_code = nhi_utils.get_pharmacy_code(
                self.system_settings,
                case_row,
                pres_days,
                string_utils.xstr(ins_apply_row["PharmacyCode"]),
            )

        pharmacy_fee = number_utils.get_integer(
            ins_apply_row["PharmacyFee"]
        ) + number_utils.get_integer(case_row["PharmacyFee"])

        pharmacist_id = string_utils.xstr(ins_apply_row["PharmacistID"])
        if pharmacy_fee > 0 and pharmacist_id == "":
            pharmacist_id = nhi_utils.get_pharmacist_id(
                self.database, self.system_settings, case_row
            )

        share_code = string_utils.xstr(ins_apply_row["ShareCode"])
        if share_code == "009" and share_fee > 0:  # 療程中開藥
            share_code = "S20"

        treat_type = string_utils.xstr(case_row["TreatType"])
        share_type = string_utils.xstr(case_row["Share"])
        treatment = string_utils.xstr(case_row["Treatment"])
        course = number_utils.get_integer(case_row["Continuance"])

        if case_start_date.year < 2023 or (
            case_start_date.year == 2023 and case_start_date.month < 7
        ):  # 112.07 以前沿用舊制
            agent_fee = charge_utils.get_ins_agent_fee(
                self.database,
                self.system_settings,
                share_type,
                treatment,
                course,
                drug_fee,
            )
        else:
            share_code = nhi_utils.get_final_share_code(
                share_code, diag_share_fee, drug_share_fee
            )  # 2022.10 新制
            agent_fee = nhi_utils.get_agent_fee(
                share_code, diag_share_fee, drug_share_fee
            )

        if treat_type in nhi_utils.HOME_CARE and share_type in [
            "基層醫療"
        ]:  # 基層醫療居家醫療部份負擔 S10, S20 --> K10, K20
            # share_fee = (ins_total_fee - drug_fee - pharmacy_fee) * 5 / 100
            if drug_fee > 0:  # 開藥
                share_code = "K20"
            else:
                share_code = "K00"

        ins_apply_fee = ins_total_fee - share_fee

        disease_code_list = []
        for i in range(1, 6):
            disease_code = string_utils.xstr(ins_apply_row[f"DiseaseCode{i}"])
            if disease_code != "":
                disease_code_list.append(disease_code)

        for i in range(1, nhi_utils.MAX_DISEASE_CODE + 1):
            disease_code = string_utils.xstr(case_row[f"DiseaseCode{i}"])
            if disease_code != "" and disease_code not in disease_code_list:
                disease_code_list.append(disease_code)

        if len(disease_code_list) < 5:
            disease_code_list += [None] * (5 - len(disease_code_list))

        fields = [
            "StopDate",
            "PresDays",
            "PresType",
            "DrugFee",
            "TreatFee",
            "PharmacyCode",
            "PharmacyFee",
            "PharmacistID",
            "ShareCode",
            "InsTotalFee",
            "ShareFee",
            "DiagShareFee",
            "DrugShareFee",
            "InsApplyFee",
            "AgentFee",
            "CaseKey1",
            "TreatCode1",
            "TreatFee1",
            "Percent1",
            "CaseKey2",
            "TreatCode2",
            "TreatFee2",
            "Percent2",
            "CaseKey3",
            "TreatCode3",
            "TreatFee3",
            "Percent3",
            "CaseKey4",
            "TreatCode4",
            "TreatFee4",
            "Percent4",
            "CaseKey5",
            "TreatCode5",
            "TreatFee5",
            "Percent5",
            "CaseKey6",
            "TreatCode6",
            "TreatFee6",
            "Percent6",
            "CaseKey7",
            "TreatCode7",
            "TreatFee7",
            "Percent7",
            "CaseKey8",
            "TreatCode8",
            "TreatFee8",
            "Percent8",
            "CaseKey9",
            "TreatCode9",
            "TreatFee9",
            "Percent9",
            "CaseKey10",
            "TreatCode10",
            "TreatFee10",
            "Percent10",
            "CaseKey11",
            "TreatCode11",
            "TreatFee11",
            "Percent11",
            "CaseKey12",
            "TreatCode12",
            "TreatFee12",
            "Percent12",
            "CaseKey13",
            "TreatCode13",
            "TreatFee13",
            "Percent13",
            "CaseKey14",
            "TreatCode14",
            "TreatFee14",
            "Percent14",
            "CaseKey15",
            "TreatCode15",
            "TreatFee15",
            "Percent15",
            "DiseaseCode1",
            "DiseaseCode2",
            "DiseaseCode3",
            "DiseaseCode4",
            "DiseaseCode5",
        ]

        data = [
            # doctor_name, doctor_id,  # 不能rewrite醫師, 要以首次為主
            case_row["CaseDate"].date(),
            (number_utils.get_integer(ins_apply_row["PresDays"]) + pres_days),
            pres_type,
            drug_fee,
            treat_fee,
            pharmacy_code,
            pharmacy_fee,
            pharmacist_id,
            share_code,
            ins_total_fee,
            share_fee,
            diag_share_fee,
            drug_share_fee,
            ins_apply_fee,
            agent_fee,
            treat_records[0]["CaseKey"],
            treat_records[0]["TreatCode"],
            treat_records[0]["TreatFee"],
            treat_records[0]["Percent"],
            treat_records[1]["CaseKey"],
            treat_records[1]["TreatCode"],
            treat_records[1]["TreatFee"],
            treat_records[1]["Percent"],
            treat_records[2]["CaseKey"],
            treat_records[2]["TreatCode"],
            treat_records[2]["TreatFee"],
            treat_records[2]["Percent"],
            treat_records[3]["CaseKey"],
            treat_records[3]["TreatCode"],
            treat_records[3]["TreatFee"],
            treat_records[3]["Percent"],
            treat_records[4]["CaseKey"],
            treat_records[4]["TreatCode"],
            treat_records[4]["TreatFee"],
            treat_records[4]["Percent"],
            treat_records[5]["CaseKey"],
            treat_records[5]["TreatCode"],
            treat_records[5]["TreatFee"],
            treat_records[5]["Percent"],
            treat_records[6]["CaseKey"],
            treat_records[6]["TreatCode"],
            treat_records[6]["TreatFee"],
            treat_records[6]["Percent"],
            treat_records[7]["CaseKey"],
            treat_records[7]["TreatCode"],
            treat_records[7]["TreatFee"],
            treat_records[7]["Percent"],
            treat_records[8]["CaseKey"],
            treat_records[8]["TreatCode"],
            treat_records[8]["TreatFee"],
            treat_records[8]["Percent"],
            treat_records[9]["CaseKey"],
            treat_records[9]["TreatCode"],
            treat_records[9]["TreatFee"],
            treat_records[9]["Percent"],
            treat_records[10]["CaseKey"],
            treat_records[10]["TreatCode"],
            treat_records[10]["TreatFee"],
            treat_records[10]["Percent"],
            treat_records[11]["CaseKey"],
            treat_records[11]["TreatCode"],
            treat_records[11]["TreatFee"],
            treat_records[11]["Percent"],
            treat_records[12]["CaseKey"],
            treat_records[12]["TreatCode"],
            treat_records[12]["TreatFee"],
            treat_records[12]["Percent"],
            treat_records[13]["CaseKey"],
            treat_records[13]["TreatCode"],
            treat_records[13]["TreatFee"],
            treat_records[13]["Percent"],
            treat_records[14]["CaseKey"],
            treat_records[14]["TreatCode"],
            treat_records[14]["TreatFee"],
            treat_records[14]["Percent"],
            disease_code_list[0],
            disease_code_list[1],
            disease_code_list[2],
            disease_code_list[3],
            disease_code_list[4],
        ]
        if (
            number_utils.get_integer(ins_apply_row["CaseKey1"]) <= 0
        ):  # 如果療程首次不在本月, 抓最後一次醫師 2020.12.08 禾生堂
            doctor_name = string_utils.xstr(case_row["Doctor"]).replace(",", "")
            doctor_id = personnel_utils.get_person_field_value(
                self.database, doctor_name, "ID"
            )
            fields += ["DoctorName", "DoctorID"]
            data += [doctor_name, doctor_id]

        self.database.update_record(
            "insapply", fields, "InsApplyKey", ins_apply_key, data
        )

    def _get_sequence(self, case_type):
        self.sequence[case_type] += 1

        return self.sequence[case_type]

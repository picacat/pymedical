# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets

from libs import nhi_utils, number_utils, personnel_utils, string_utils


# 申報統計資料 2018.01.31
class InsApplyCalculate(QtWidgets.QMainWindow):
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
        self.ins_calculated_table = []
        self.ui = None

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]
        self.start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        self.end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")
        self.exclude_script = '(CaseType NOT IN ("C5"))'
        self._set_ui()
        self._set_signal()

    def __del__(self):
        self.close_all()

    def close_all(self):
        pass

    def close_tab(self):
        current_tab = self.parent.ui.tabWidget_window.currentIndex()
        self.parent.close_tab(current_tab)

    def close_app(self):
        self.close_all()
        self.close_tab()

    def _set_ui(self):
        pass

    def _set_signal(self):
        pass

    def calculate_ins_data(self):
        # 1. 收集全體醫師基礎資料 (此時內部為隨機順序)
        self._set_doctor_table()

        # 2. 排序：確保專任在前(0)，支援在後(1)
        self.ins_calculated_table.sort(
            key=lambda x: 0 if x["doctor_type"] == "醫師" else 1
        )

        # 3. 所有人到齊且排好序了，統一呼叫「一次」分段計算！
        self._calculate_diag_section()
        self._calculate_treat_section()

        # 4. 最後，統一呼叫「一次」大水庫推填遞補！
        self._set_part_time_doctor()

    def _set_doctor_table(self):
        sql = f'''
            SELECT DoctorName, DoctorID
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                {self.exclude_script}
            GROUP BY DoctorName
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            self._set_doctor_table_data(row)

    def _set_doctor_table_data(self, row):
        doctor_data = {
            "doctor_type": None,
            "doctor_name": row["DoctorName"],
            "doctor_id": row["DoctorID"],
            "diag_days": 0,
            "total_count": 0,
            "total_diag_count": 0,
            "diag_count": 0,
            "treat_count": 0,
            "internal_drug": 0,
            "treat_drug": 0,
            "total_drug": 0,
            "complicated_massage": 0,
            "moderate_complicated_acupuncture": 0,
            "highly_complicated_acupuncture": 0,
            "diag_section1": 0,
            "diag_section2": 0,
            "diag_section3": 0,
            "diag_section4": 0,
            "diag_section5": 0,
            "treat_section1": 0,
            "treat_section2": 0,
            "treat_section3": 0,
            "infectious_count": 0,
        }
        doctor_data["doctor_type"] = personnel_utils.get_person_field_value(
            self.database, doctor_data["doctor_name"], "Position"
        )
        max_progress = 10
        progress_dialog = QtWidgets.QProgressDialog(
            f"正在統計{doctor_data['doctor_name']}醫師的資料中, 請稍後...",
            "取消",
            0,
            max_progress,
            self,
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        doctor_data["diag_days"] = self._get_diag_days(doctor_data["doctor_name"])
        progress_dialog.setValue(1)

        doctor_data["total_count"] = self._get_total_count(doctor_data["doctor_name"])
        progress_dialog.setValue(2)

        doctor_data["total_diag_count"] = self._get_total_diag_count(
            doctor_data["doctor_name"]
        )
        doctor_data["diag_count"] = self._get_diag_count(doctor_data["doctor_name"])
        progress_dialog.setValue(3)

        doctor_data["treat_drug"] = self._get_treat_drug(doctor_data["doctor_name"])
        progress_dialog.setValue(4)

        doctor_data["moderate_complicated_acupuncture"] = self._get_complicated_treat(
            doctor_data["doctor_name"],
            nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_CODE,
        )
        progress_dialog.setValue(5)

        doctor_data["highly_complicated_acupuncture"] = self._get_complicated_treat(
            doctor_data["doctor_name"],
            nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_CODE,
        )
        progress_dialog.setValue(6)

        doctor_data["complicated_massage"] = self._get_complicated_massage(
            doctor_data["doctor_name"]
        )
        progress_dialog.setValue(7)

        doctor_data["treat_count"] = self._get_treat_count(
            doctor_data["doctor_name"], doctor_data["treat_drug"]
        )
        progress_dialog.setValue(8)

        doctor_data["internal_drug"] = self._get_internal_drug(
            doctor_data["doctor_name"]
        )
        progress_dialog.setValue(9)

        doctor_data["total_drug"] = (
            doctor_data["internal_drug"] + doctor_data["treat_drug"]
        )

        doctor_data["infectious_count"] = self._get_infectious_count(
            doctor_data["doctor_name"]
        )
        progress_dialog.setValue(10)

        progress_dialog.deleteLater()
        self.ins_calculated_table.append(doctor_data)

    def _get_diag_days(self, doctor_name):
        sql = f'''
            SELECT InsApplyKey FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}" AND
                {self.exclude_script} AND
                DoctorName = "{doctor_name}" AND
                (DiagFee > 0 OR SpecialCode1 = "EC")
            GROUP BY DATE(CaseDate)
        '''
        rows = self.database.select_record(sql)
        diag_days = len(rows)
        diag_days = min(diag_days, nhi_utils.MAX_DIAG_DAYS)
        return diag_days

    # def _get_total_count(self, in_doctor_name):
    #     total_count = 0
    #     sql = f'''
    #         SELECT
    #             CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5,
    #             CaseKey6, CaseKey7, CaseKey8, CaseKey9, CaseKey10,
    #             CaseKey11, CaseKey12, CaseKey13, CaseKey14, CaseKey15
    #         FROM insapply
    #         WHERE
    #             ApplyDate = "{self.apply_date}" AND
    #             ApplyType = "{self.apply_type_code}" AND
    #             ApplyPeriod = "{self.period}" AND
    #             ClinicID = "{self.clinic_id}" AND
    #             {self.exclude_script}
    #     '''
    #     rows = self.database.select_record(sql)
    #     for row in rows:
    #         for i in range(1, 16):
    #             case_key = number_utils.get_integer(row[f"CaseKey{i}"])
    #             if case_key <= 0:
    #                 continue
    #             doctor_name = self._get_doctor_name(case_key)
    #             if doctor_name == in_doctor_name:
    #                 total_count += 1
    #     return total_count

    def _get_total_count(self, in_doctor_name):
        select_parts = []
        for i in range(1, 16):
            select_parts.append(f'''
                SELECT i.CaseKey{i} as ck
                FROM insapply i
                WHERE
                    i.CaseKey{i} > 0 AND
                    i.ApplyDate = "{self.apply_date}" AND
                    i.ApplyType = "{self.apply_type_code}" AND
                    i.ApplyPeriod = "{self.period}" AND
                    i.ClinicID = "{self.clinic_id}" AND
                    {self.exclude_script}
            ''')

        union_subquery = " UNION ALL ".join(select_parts)
        sql = f'''
            SELECT COUNT(*) as cnt
            FROM (
                {union_subquery}
            ) AS all_case_keys
            JOIN cases c ON c.CaseKey = all_case_keys.ck
            WHERE REPLACE(c.Doctor, ',', '') = "{in_doctor_name}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) > 0:
            return number_utils.get_integer(rows[0]["cnt"])
        return 0

    def _get_infectious_count(self, in_doctor_name):
        infectious_count = 0
        sql = f'''
            SELECT CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("C5")
            GROUP BY PatientKey, DATE(CaseDate)
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            for i in range(1, 7):
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue
                doctor_name = self._get_doctor_name(case_key)
                if doctor_name == in_doctor_name:
                    infectious_count += 1
        return infectious_count

    def _get_treat_count(self, in_doctor_name, treat_drug):
        treat_count = 0
        sql = f'''
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("29")
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            for i in range(1, 7):
                treat_code = string_utils.xstr(row[f"TreatCode{i}"])
                if treat_code not in nhi_utils.TREAT_ALL_CODE:
                    continue
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue
                doctor_name = self._get_doctor_name(case_key)
                if doctor_name == in_doctor_name:
                    treat_count += 1
        if treat_count - treat_drug > 0:
            treat_count -= treat_drug
        return treat_count

    def _get_internal_drug(self, in_doctor_name):
        sql = f'''
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("21", "24") AND
                DoctorName = "{in_doctor_name}" AND
                PresDays > 0
        '''
        rows = self.database.select_record(sql)
        return len(rows)

    def _get_treat_drug(self, in_doctor_name):
        treat_drug = 0
        sql = f'''
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("29")
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            for i in range(1, 7):
                treat_code = string_utils.xstr(row[f"TreatCode{i}"])
                if treat_code not in nhi_utils.TREAT_DRUG_CODE:
                    continue
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue
                doctor_name = self._get_doctor_name(case_key)
                if doctor_name == in_doctor_name:
                    treat_drug += 1

        return treat_drug

    def _get_doctor_name(self, case_key):
        sql = f"""
            SELECT Doctor FROM cases
            WHERE CaseKey = {case_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None
        row = rows[0]
        return string_utils.xstr(row["Doctor"]).replace(",", "")

    def _get_complicated_massage(self, in_doctor_name):
        treat_count = 0
        sql = f'''
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("29", "C5")
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            for i in range(1, 7):
                treat_code = string_utils.xstr(row[f"TreatCode{i}"])
                if treat_code not in nhi_utils.COMPLICATED_MASSAGE_CODE:
                    continue
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue
                doctor_name = self._get_doctor_name(case_key)
                if doctor_name == in_doctor_name:
                    treat_count += 1
        return treat_count

    def _get_complicated_treat(self, in_doctor_name, complicated_treat_list):
        treat_count = 0
        sql = f'''
            SELECT
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6,
                TreatCode1, TreatCode2, TreatCode3, TreatCode4, TreatCode5, TreatCode6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN ("29", "C5")
        '''
        rows = self.database.select_record(sql)
        for row in rows:
            for i in range(1, 7):
                treat_code = string_utils.xstr(row[f"TreatCode{i}"])
                if treat_code not in complicated_treat_list:
                    continue
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue
                doctor_name = self._get_doctor_name(case_key)
                if doctor_name == in_doctor_name:
                    treat_count += 1
        return treat_count

    def _get_total_diag_count(self, doctor_name):
        sql = f'''
            SELECT CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DoctorName = "{doctor_name}" AND
                {self.exclude_script} AND
                DiagFee > 0
        '''
        rows = self.database.select_record(sql)
        return len(rows)

    def _get_diag_count(self, doctor_name):
        exclude_diag_adjust = tuple(nhi_utils.EXCLUDE_DIAG_ADJUST)
        sql = f'''
            SELECT InsApplyKey FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DoctorName = "{doctor_name}" AND
                DiagFee > 0 AND
                CaseType NOT IN {exclude_diag_adjust}
        '''
        rows = self.database.select_record(sql)
        diag_count = len(rows)

        sql = f'''
            SELECT InsApplyKey FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DoctorName = "{doctor_name}" AND
                DiagFee > 0 AND
                SpecialCode1 IN ("JA", "JB")
        '''
        rows = self.database.select_record(sql)
        diag_count -= len(rows)

        sql = f'''
            SELECT InsApplyKey FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DoctorName = "{doctor_name}" AND
                DiagFee > 0 AND
                CaseType = "22" AND
                InsApplyFee <= DiagFee
        '''
        rows = self.database.select_record(sql)
        diag_count += len(rows)
        return diag_count

    def _calculate_diag_section(self):
        for row in self.ins_calculated_table:
            diag_days = min(row["diag_days"], nhi_utils.MAX_DIAG_DAYS)
            count = row["diag_count"]

            limit_s1 = diag_days * nhi_utils.DIAG_SECTION1
            limit_s2 = diag_days * (nhi_utils.DIAG_SECTION2 - nhi_utils.DIAG_SECTION1)
            limit_s3 = diag_days * (nhi_utils.DIAG_SECTION3 - nhi_utils.DIAG_SECTION2)
            limit_s4 = diag_days * (nhi_utils.DIAG_SECTION4 - nhi_utils.DIAG_SECTION3)

            remains = count
            row["diag_section1"] = min(remains, limit_s1)
            remains -= row["diag_section1"]

            row["diag_section2"] = min(remains, limit_s2)
            remains -= row["diag_section2"]

            row["diag_section3"] = min(remains, limit_s3)
            remains -= row["diag_section3"]

            row["diag_section4"] = min(remains, limit_s4)
            remains -= row["diag_section4"]

            row["diag_section5"] = remains

    def _calculate_treat_section(self):
        for row in self.ins_calculated_table:
            treat_count = row["treat_count"]
            treat_drug = row["treat_drug"]
            moderate_acupuncture = row["moderate_complicated_acupuncture"]
            highly_acupuncture = row["highly_complicated_acupuncture"]

            # ==================== 終極精準安全修正：所有針傷級距天數一律卡死最高 26 天 ====================
            calc_days = min(row["diag_days"], nhi_utils.MAX_DIAG_DAYS)
            # ==========================================================================================

            row["treat_section1"] = self._get_treat_section1(
                calc_days,
                treat_count,
                treat_drug,
                moderate_acupuncture,
                highly_acupuncture,
            )
            row["treat_section2"] = self._get_treat_section2(
                calc_days,
                treat_count,
                row["treat_section1"],  # ✅ 已修正此處的參數錯配漏洞！
            )
            row["treat_section3"] = self._get_treat_section3(
                treat_count,
                row["treat_section1"],
                row["treat_section2"],
            )

    def _get_treat_section1(
        self,
        diag_days,
        treat_count,
        treat_drug,
        moderate_acupuncture,
        highly_acupuncture,
    ):
        treat_section1 = treat_count
        # treat_section1_limit = (diag_days * nhi_utils.TREAT_SECTION1) - treat_drug
        treat_section1_limit = max(
            0, (diag_days * nhi_utils.TREAT_SECTION1) - treat_drug
        )
        treat_section1 = min(treat_section1, treat_section1_limit)
        return treat_section1

    def _get_treat_section2(self, diag_days, treat_count, treat_section1):
        treat_section2 = treat_count - treat_section1
        treat_section2_limit = diag_days * (
            nhi_utils.TREAT_SECTION2 - nhi_utils.TREAT_SECTION1
        )
        treat_section2 = min(treat_section2, treat_section2_limit)
        return treat_section2

    def _get_treat_section3(self, treat_count, treat_section1, treat_section2):
        treat_section3 = treat_count - treat_section1 - treat_section2
        return treat_section3

    def _set_part_time_doctor(self):
        self._set_part_time_doctor_diag_balance()
        self._set_part_time_doctor_treat_balance()

    def _set_part_time_doctor_diag_balance(self):
        (section1_balance, section2_balance, section3_balance, section4_balance) = (
            self._get_full_time_doctor_diag_balance()
        )

        for ins_calculated_row in self.ins_calculated_table:
            if ins_calculated_row["doctor_type"] == "醫師":
                continue

            ins_calculated_row["diag_section1"] = 0
            ins_calculated_row["diag_section2"] = 0
            ins_calculated_row["diag_section3"] = 0
            ins_calculated_row["diag_section4"] = 0
            ins_calculated_row["diag_section5"] = 0

            diag_count = ins_calculated_row["diag_count"]
            if diag_count <= section1_balance:
                ins_calculated_row["diag_section1"] = diag_count
                diag_count = 0
            else:
                ins_calculated_row["diag_section1"] = section1_balance
                diag_count -= section1_balance

            section1_balance -= ins_calculated_row["diag_section1"]

            if diag_count <= 0:
                continue

            if diag_count <= section2_balance:
                ins_calculated_row["diag_section2"] = diag_count
                diag_count = 0
            else:
                ins_calculated_row["diag_section2"] = section2_balance
                diag_count -= section2_balance

            section2_balance -= ins_calculated_row["diag_section2"]

            if diag_count <= 0:
                continue

            if diag_count <= section3_balance:
                ins_calculated_row["diag_section3"] = diag_count
                diag_count = 0
            else:
                ins_calculated_row["diag_section3"] = section3_balance
                diag_count -= section3_balance

            section3_balance -= ins_calculated_row["diag_section3"]

            if diag_count <= 0:
                continue

            if diag_count <= section4_balance:
                ins_calculated_row["diag_section4"] = diag_count
                diag_count = 0
            else:
                ins_calculated_row["diag_section4"] = section4_balance
                diag_count -= section4_balance

            section4_balance -= ins_calculated_row["diag_section4"]

            if diag_count <= 0:
                continue

            ins_calculated_row["diag_section5"] = diag_count

    def _get_full_time_doctor_diag_balance(self):
        section1_balance = 0
        section2_balance = 0
        section3_balance = 0
        section4_balance = 0

        for ins_calculated_row in self.ins_calculated_table:
            if ins_calculated_row["doctor_type"] == "支援醫師":
                continue

            diag_days = min(ins_calculated_row["diag_days"], nhi_utils.MAX_DIAG_DAYS)

            diag_section1_limit = diag_days * nhi_utils.DIAG_SECTION1
            diag_section2_limit = diag_days * (
                nhi_utils.DIAG_SECTION2 - nhi_utils.DIAG_SECTION1
            )
            diag_section3_limit = diag_days * (
                nhi_utils.DIAG_SECTION3 - nhi_utils.DIAG_SECTION2
            )
            diag_section4_limit = diag_days * (
                nhi_utils.DIAG_SECTION4 - nhi_utils.DIAG_SECTION3
            )

            if ins_calculated_row["diag_section1"] < diag_section1_limit:
                section1_balance += (
                    diag_section1_limit - ins_calculated_row["diag_section1"]
                )
            if ins_calculated_row["diag_section2"] < diag_section2_limit:
                section2_balance += (
                    diag_section2_limit - ins_calculated_row["diag_section2"]
                )
            if ins_calculated_row["diag_section3"] < diag_section3_limit:
                section3_balance += (
                    diag_section3_limit - ins_calculated_row["diag_section3"]
                )
            if ins_calculated_row["diag_section4"] < diag_section4_limit:
                section4_balance += (
                    diag_section4_limit - ins_calculated_row["diag_section4"]
                )

        return section1_balance, section2_balance, section3_balance, section4_balance

    def _set_part_time_doctor_treat_balance(self):
        (section1_balance, section2_balance) = (
            self._get_full_time_doctor_treat_balance()
        )

        for ins_calculated_row in self.ins_calculated_table:
            if ins_calculated_row["doctor_type"] == "醫師":
                continue

            ins_calculated_row["treat_section1"] = 0
            ins_calculated_row["treat_section2"] = 0
            ins_calculated_row["treat_section3"] = 0

            treat_count = ins_calculated_row["treat_count"]
            if treat_count <= section1_balance:
                ins_calculated_row["treat_section1"] = treat_count
                treat_count = 0
            else:
                ins_calculated_row["treat_section1"] = section1_balance
                treat_count -= section1_balance

            section1_balance -= ins_calculated_row["treat_section1"]

            if treat_count <= 0:
                continue

            if treat_count <= section2_balance:
                ins_calculated_row["treat_section2"] = treat_count
                treat_count = 0
            else:
                ins_calculated_row["treat_section2"] = section2_balance
                treat_count -= section2_balance

            section2_balance -= ins_calculated_row["treat_section2"]

            if treat_count <= 0:
                continue

            ins_calculated_row["treat_section3"] = treat_count

    def _get_full_time_doctor_treat_balance(self):
        section1_balance = 0
        section2_balance = 0

        for ins_calculated_row in self.ins_calculated_table:
            if ins_calculated_row["doctor_type"] == "支援醫師":
                continue

            diag_days = min(ins_calculated_row["diag_days"], nhi_utils.MAX_DIAG_DAYS)
            treat_drug = ins_calculated_row["treat_drug"]

            # treat_section1_limit = diag_days * nhi_utils.TREAT_SECTION1 - treat_drug
            treat_section1_limit = max(
                0, diag_days * nhi_utils.TREAT_SECTION1 - treat_drug
            )
            treat_section2_limit = diag_days * (
                nhi_utils.TREAT_SECTION2 - nhi_utils.TREAT_SECTION1
            )

            if ins_calculated_row["treat_section1"] < treat_section1_limit:
                section1_balance += (
                    treat_section1_limit - ins_calculated_row["treat_section1"]
                )
            if ins_calculated_row["treat_section2"] < treat_section2_limit:
                section2_balance += (
                    treat_section2_limit - ins_calculated_row["treat_section2"]
                )

        return section1_balance, section2_balance

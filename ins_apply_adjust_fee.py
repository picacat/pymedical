# -*- coding: UTF-8 -*-

from PyQt5 import QtCore, QtWidgets

from libs import (
    case_utils,
    charge_utils,
    date_utils,
    nhi_utils,
    number_utils,
    personnel_utils,
    string_utils,
)


# 候診名單 2018.01.31
class InsApplyAdjustFee(QtWidgets.QMainWindow):
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
        self.ins_calculated_table = args[9]
        self.ui = None

        self.apply_date = nhi_utils.get_apply_date(self.apply_year, self.apply_month)
        self.apply_type_code = nhi_utils.APPLY_TYPE_CODE[self.apply_type]

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

    def adjust_ins_fee(self):
        # if self.apply_type == '補報':  # 補報不調整各項費用成數 2019.05.30
        #     return

        progress_dialog = QtWidgets.QProgressDialog(
            "正在調整申報檔各項費用中, 請稍後...", "取消", 0, 8, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setValue(0)

        self._adjust_diag_fee()
        progress_dialog.setValue(1)

        self._adjust_pharmacy_fee()
        progress_dialog.setValue(2)

        self._adjust_nurse_diag_fee()
        progress_dialog.setValue(3)

        self._adjust_child_diag_fee()
        progress_dialog.setValue(4)

        self._adjust_treat_fee()
        progress_dialog.setValue(5)

        self._adjust_treat_drug_fee()
        progress_dialog.setValue(6)

        self._adjust_first_visit_fee()
        progress_dialog.setValue(7)

        self._adjust_care_fee()
        progress_dialog.setValue(8)

        progress_dialog.deleteLater()

    # 診察費調整, 特定照護不列入計算
    def _adjust_diag_fee(self):
        for row in self.ins_calculated_table:
            diag_section1 = row["diag_section1"]
            diag_section2 = row["diag_section1"] + row["diag_section2"]
            diag_section3 = (
                row["diag_section1"] + row["diag_section2"] + row["diag_section3"]
            )
            diag_section4 = (
                row["diag_section1"]
                + row["diag_section2"]
                + row["diag_section3"]
                + row["diag_section4"]
            )
            diag_section5 = (
                row["diag_section1"]
                + row["diag_section2"]
                + row["diag_section3"]
                + row["diag_section4"]
                + row["diag_section5"]
            )

            ins_apply_rows = self._get_ins_apply_rows(
                row["doctor_id"]
            )  # 不含照護及職業傷害, 三歲兒童放在最前面
            for ins_row_no, ins_row in zip(
                range(1, len(ins_apply_rows) + 1), ins_apply_rows
            ):
                if ins_row_no <= diag_section1:  # 第一段不調整
                    pass
                elif ins_row_no <= diag_section2:
                    self._adjust_diag_section2(ins_row)
                elif ins_row_no <= diag_section3:
                    self._adjust_diag_section3(ins_row)
                elif ins_row_no <= diag_section4:
                    self._adjust_diag_section4(ins_row)
                elif ins_row_no <= diag_section5:
                    self._adjust_diag_section5(ins_row)

    def _adjust_diag_section1(self, row):
        diag_code = row["DiagCode"]
        charge_utils.update_ins_apply_diag_fee(
            self.database, self.system_settings, row["InsApplyKey"], diag_code
        )

    def _adjust_diag_section2(self, row):
        diag_code = row["DiagCode"]
        if diag_code == "A01":
            diag_code = "A03"
        elif diag_code == "A02":
            diag_code = "A04"

        charge_utils.update_ins_apply_diag_fee(
            self.database, self.system_settings, row["InsApplyKey"], diag_code
        )

    def _adjust_diag_section3(self, row):
        diag_code = row["DiagCode"]
        if diag_code == "A01":
            diag_code = "A05"
        elif diag_code == "A02":
            diag_code = "A06"

        charge_utils.update_ins_apply_diag_fee(
            self.database, self.system_settings, row["InsApplyKey"], diag_code
        )

    def _adjust_diag_section4(self, row):
        diag_code = "A07"
        charge_utils.update_ins_apply_diag_fee(
            self.database, self.system_settings, row["InsApplyKey"], diag_code
        )

    def _adjust_diag_section5(self, row):
        diag_code = "A08"
        charge_utils.update_ins_apply_diag_fee(
            self.database, self.system_settings, row["InsApplyKey"], diag_code
        )

    # 不含加強照護類及職業傷害
    def _get_ins_apply_rows(self, doctor_id):
        exclude_case_type = tuple(nhi_utils.EXCLUDE_DIAG_ADJUST)

        # CaseType: 22 DiagFee = InsTotalFee 問診也要計算
        sql = f'''
            SELECT InsApplyKey, Sequence, DoctorName, DiagCode, DiagFee, InsTotalFee, InsApplyFee
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DoctorID = "{doctor_id}" AND
                DiagFee > 0 AND
                (CaseType NOT IN {exclude_case_type} OR
                 CaseType = "22" AND DiagFee = InsTotalFee)
                ORDER BY CaseType, Field(ShareCode, '902', 'S10', 'S20', '003', '004'), Sequence
        '''
        rows = self.database.select_record(sql)

        return rows

    # 根據藥師班表調整調劑費
    def _adjust_pharmacy_fee(self):
        if (
            number_utils.get_integer(self.system_settings.field("藥師人數")) <= 0
        ):  # 無藥師, 不需調整
            return

        start_date = self.start_date.toString("yyyy-MM-dd")
        end_date = self.end_date.toString("yyyy-MM-dd")

        sql = f'''
            SELECT PharmacistScheduleKey FROM pharmacist_schedule
            WHERE
                ScheduleDate BETWEEN "{start_date}" AND "{end_date}"
        '''
        rows = self.database.select_record(sql)
        if len(rows) <= 0:  # 沒有藥師班表,  無須調整
            return

        sql = f'''
            SELECT
                InsApplyKey, CaseType, Sequence, DoctorID, PharmacyCode, PharmacyFee, InsTotalFee, InsApplyFee,
                CaseKey1, CaseKey2, CaseKey3, CaseKey4, CaseKey5, CaseKey6
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                PharmacyFee > 0
                ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        fields = [
            "PharmacistID",
            "PharmacyCode",
            "PharmacyFee",
            "InsTotalFee",
            "InsApplyFee",
        ]
        for row in rows:
            pharmacy_code = string_utils.xstr(row["PharmacyCode"])
            pharmacy_fee = number_utils.get_integer(row["PharmacyFee"])
            new_pharmacy_code = ""
            new_pharmacy_fee = 0
            new_pharmacist_id = None

            for i in range(nhi_utils.MAX_COURSE):
                if pharmacy_code[i] in ["0", None]:
                    new_pharmacy_code += "0"
                    continue

                case_key = row[f"CaseKey{i + 1}"]
                if case_key is None:
                    new_pharmacy_code += "0"
                    continue

                on_duty, pharmacist = nhi_utils.pharmacist_schedule_on_duty(
                    self.database, case_key
                )
                if on_duty:
                    code = "1"
                    new_pharmacist_id = personnel_utils.get_person_field_value(
                        self.database, pharmacist, "ID"
                    )
                else:
                    code = "2"

                new_pharmacy_code += code
                ins_code = f"A3{code}"
                case_date, _ = case_utils.get_case_date(self.database, case_key)
                fee = charge_utils.get_ins_fee_from_ins_code(
                    self.database, ins_code, case_date=case_date
                )
                new_pharmacy_fee += fee

            ins_apply_key = row["InsApplyKey"]
            ins_total_fee = (
                number_utils.get_integer(row["InsTotalFee"])
                - pharmacy_fee
                + new_pharmacy_fee
            )
            ins_apply_fee = (
                number_utils.get_integer(row["InsApplyFee"])
                - pharmacy_fee
                + new_pharmacy_fee
            )
            if new_pharmacist_id is None:
                new_pharmacist_id = string_utils.xstr(row["DoctorID"])

            data = [
                new_pharmacist_id,
                new_pharmacy_code,
                new_pharmacy_fee,
                ins_total_fee,
                ins_apply_fee,
            ]
            self.database.update_record(
                "insapply", fields, "InsApplyKey", ins_apply_key, data
            )

    def _adjust_nurse_diag_fee(self):
        if (
            number_utils.get_integer(self.system_settings.field("護士人數")) <= 0
        ):  # 無護理師, 不需調整
            return

        sql = f'''
            SELECT
                InsApplyKey, Sequence, CaseKey1, DoctorName, DiagCode, DiagFee, InsTotalFee, InsApplyFee
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
                ORDER BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            case_key = row["CaseKey1"]
            doctor_name = string_utils.xstr(row["DoctorName"])
            diag_code = row["DiagCode"]
            if not nhi_utils.nurse_schedule_on_duty(
                self.database, case_key, doctor_name
            ):
                if diag_code in ["A01", "A03", "A05"]:
                    if diag_code == "A01":
                        diag_code = "A02"
                    elif diag_code == "A03":
                        diag_code = "A04"
                    elif diag_code == "A05":
                        diag_code = "A06"

                charge_utils.update_ins_apply_diag_fee(
                    self.database, self.system_settings, row["InsApplyKey"], diag_code
                )

    # 未滿四歲加成20% 2022-03-01 實施 (之前為未滿3歲 ShareCode = '902')
    def _adjust_child_diag_fee(self):
        sql = f'''
            SELECT *
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                DiagFee > 0
                ORDER BY Sequence
        '''
        rows = self.database.select_record(sql)

        for row in rows:
            age_year, _ = date_utils.get_age(row["Birthday"], row["CaseDate"])
            if age_year is None or age_year >= 4:  # 已滿4歲
                continue
            # if string_utils.xstr(row["ShareCode"]) != "902":  # 非三歲兒童不計算加成
            #     continue

            ins_apply_key = row["InsApplyKey"]
            extra_diag_fee = int(row["DiagFee"] * 20 / 100)
            diag_fee = row["DiagFee"] + extra_diag_fee
            ins_total_fee = row["InsTotalFee"] + extra_diag_fee
            ins_apply_fee = row["InsApplyFee"] + extra_diag_fee

            fields = ["DiagFee", "InsTotalFee", "InsApplyFee"]
            data = [diag_fee, ins_total_fee, ins_apply_fee]

            self.database.update_record(
                "insapply", fields, "InsApplyKey", ins_apply_key, data
            )

    def _adjust_treat_fee(self):
        for ins_calculated_row in self.ins_calculated_table:
            doctor_name = ins_calculated_row["doctor_name"]
            sql = f'''
                SELECT *
                FROM insapply
                WHERE
                    ApplyDate = "{self.apply_date}" AND
                    ApplyType = "{self.apply_type_code}" AND
                    ApplyPeriod = "{self.period}" AND
                    ClinicID = "{self.clinic_id}" AND
                    CaseType = "29"
                    ORDER BY Sequence
            '''
            rows = self.database.select_record(sql)

            treat_section1 = ins_calculated_row["treat_section1"]
            treat_section2 = (
                ins_calculated_row["treat_section1"]
                + ins_calculated_row["treat_section2"]
            )
            treat_section3 = (
                ins_calculated_row["treat_section1"]
                + ins_calculated_row["treat_section2"]
                + ins_calculated_row["treat_section3"]
            )

            treat_count = 0
            for row in rows:
                for course in range(1, nhi_utils.MAX_COURSE + 1):
                    case_key = row[f"CaseKey{course}"]
                    if case_key in ["", None]:
                        continue

                    sql = f'''
                        SELECT CaseKey FROM cases
                        WHERE
                            CaseKey = {case_key} AND
                            Doctor = "{doctor_name}"
                    '''
                    case_rows = self.database.select_record(sql)
                    if len(case_rows) <= 0:
                        continue

                    treat_code = string_utils.xstr(row[f"TreatCode{course}"])
                    if treat_code not in nhi_utils.TREAT_ALL_CODE:  # 針傷處置才調整
                        continue

                    if treat_code in nhi_utils.TREAT_DRUG_CODE:  # 針傷給藥不調整
                        continue

                    if (
                        treat_code in nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_CODE
                    ):  # 2023-05-09 中度複針不調整, 只調整一般針灸比較划算
                        continue

                    if (
                        treat_code in nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_CODE
                    ):  # 高度複針不調整
                        continue

                    treat_fee = number_utils.get_integer(row[f"TreatFee{course}"])
                    if treat_code == "" or treat_fee <= 0:
                        continue

                    treat_count += 1

                    ins_apply_key = row["InsApplyKey"]
                    if treat_count <= treat_section1:
                        treat_percent = 100
                    elif treat_count <= treat_section2:
                        treat_percent = 90
                        charge_utils.update_treat_fee(
                            self.database, ins_apply_key, course, treat_percent
                        )
                    elif treat_count <= treat_section3:
                        treat_percent = 0

                    if treat_percent < 100:
                        charge_utils.update_treat_fee(
                            self.database, ins_apply_key, course, treat_percent
                        )

    # 計算針灸傷科給藥上限 (每位醫師平均 專任醫師數 * 120)
    def _adjust_treat_drug_fee(self):
        max_full_time_doctor = 0
        for ins_calculated_row in self.ins_calculated_table:  # 取得專任醫師數
            if ins_calculated_row["doctor_type"] == "醫師":
                max_full_time_doctor += 1

        max_treat_drug = max_full_time_doctor * nhi_utils.MAX_TREAT_DRUG

        sql = f'''
            SELECT *
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType = "29"
                ORDER BY Sequence
        '''
        rows = self.database.select_record(sql)

        treat_drug_count = 0
        for row in rows:
            for course in range(1, nhi_utils.MAX_COURSE + 1):
                treat_code = string_utils.xstr(row[f"TreatCode{course}"])
                if treat_code not in nhi_utils.TREAT_DRUG_CODE:  # 無開藥不調整
                    continue

                treat_drug_count += 1

                ins_apply_key = row["InsApplyKey"]
                if treat_drug_count > max_treat_drug:
                    treat_percent = 50
                    charge_utils.update_treat_fee(
                        self.database, ins_apply_key, course, treat_percent
                    )

    def _adjust_first_visit_fee(self):
        if self.system_settings.field("申報初診照護") == "N":
            return

        sql = f'''
            SELECT *
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseType IN("21", "29") AND
                DiagFee > 0
            GROUP BY ID
        '''
        rows = self.database.select_record(sql)
        first_visit_limit = int(len(rows) * 10 / 100)  # 初診照護為總歸戶人數的10%

        # 2021-10-12 22類不申報初診診察費加計
        sql = f'''
            SELECT * FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                Visit = "初診照護"
                GROUP BY CaseType, Sequence
        '''
        rows = self.database.select_record(sql)

        for row_no, row in zip(range(1, len(rows) + 1), rows):
            ins_apply_key = row["InsApplyKey"]
            if row_no <= first_visit_limit:
                case_date = row["CaseDate"]
                first_visit_fee = charge_utils.get_ins_fee_from_ins_code(
                    self.database, "A90", case_date=case_date
                )
                fields = ["TreatFee", "InsTotalFee", "InsApplyFee"]
                data = [
                    number_utils.get_integer(row["TreatFee"]) + first_visit_fee,
                    number_utils.get_integer(row["InsTotalFee"]) + first_visit_fee,
                    number_utils.get_integer(row["InsApplyFee"]) + first_visit_fee,
                ]
            else:
                fields = ["Visit"]
                data = [None]

            self.database.update_record(
                "insapply", fields, "InsApplyKey", ins_apply_key, data
            )

    def _adjust_care_fee(self):
        pass

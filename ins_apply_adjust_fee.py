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

# 進度對話盒延遲顯示的毫秒數
# Qt 預設 4000: 估計作業不到 4 秒就整個不顯示, 看起來像沒反應
# 0 = 一定顯示; 不想讓小資料量閃一下的話改成 500
PROGRESS_MINIMUM_DURATION = 0


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

    # ==================================================================
    # 重複調整的防呆
    # 本檔的 _adjust_child_diag_fee (加成20%)、_adjust_first_visit_fee (加A90)
    # 與 charge_utils.update_treat_fee (讀當前值再乘成數) 都是「累加型」,
    # 同一批 insapply 重跑會複利 (九折跑兩次變成八一折)。
    # 正確流程是「重新產生申報資料 -> 調整」, 這裡加一道旗標把它固定下來。
    # ==================================================================
    def _base_condition(self):
        return f'''
            ApplyDate = "{self.apply_date}" AND
            ApplyType = "{self.apply_type_code}" AND
            ApplyPeriod = "{self.period}" AND
            ClinicID = "{self.clinic_id}"
        '''

    def _ensure_adjusted_field(self):
        """確認 insapply.Adjusted 欄位存在, 沒有就補上.

        失敗時回傳 False, 呼叫端會略過防呆繼續執行——不能因為欄位加不上去
        就讓申報作業做不下去。
        """
        try:  # 探一下欄位在不在, 比 SHOW COLUMNS 可攜
            self.database.select_record("SELECT Adjusted FROM insapply LIMIT 1")
            return True
        except Exception:
            pass

        try:
            self.database.exec_sql(
                "ALTER TABLE insapply ADD COLUMN Adjusted CHAR(1) DEFAULT NULL"
            )
            return True
        except Exception as error:
            print(
                f"[申報調整] 無法建立 insapply.Adjusted 欄位, 略過重複調整防呆: {error}"
            )
            return False

    def _is_adjusted(self):
        sql = f"""
            SELECT COUNT(*) AS cnt FROM insapply
            WHERE
                {self._base_condition()} AND
                Adjusted = "Y"
        """
        try:
            rows = self.database.select_record(sql)
        except Exception:
            return False

        if len(rows) <= 0:
            return False

        return number_utils.get_integer(rows[0]["cnt"]) > 0

    def _mark_adjusted(self):
        sql = f"""
            UPDATE insapply
            SET
                Adjusted = "Y"
            WHERE
                {self._base_condition()}
        """
        try:
            self.database.exec_sql(sql)
        except Exception as error:
            print(f"[申報調整] 無法寫入 Adjusted 旗標: {error}")

    def adjust_ins_fee(self):
        # if self.apply_type == '補報':  # 補報不調整各項費用成數 2019.05.30
        #     return

        has_flag = self._ensure_adjusted_field()
        if has_flag and self._is_adjusted():
            QtWidgets.QMessageBox.warning(
                self,
                "申報資料已調整過",
                "<h3>本次申報的資料已經調整過了, 這次不再調整。</h3>"
                "<p>重複調整會讓成數累乘 (九折跑兩次變成八一折)、"
                "未滿四歲加成與初診照護加計重複累加。</p>"
                "<p>請先<b>重新產生申報資料</b>, 再執行調整。</p>",
                QtWidgets.QMessageBox.Ok,
            )
            return False

        progress_dialog = QtWidgets.QProgressDialog(
            "正在調整申報檔各項費用中, 請稍後...", "取消", 0, 8, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setMinimumDuration(PROGRESS_MINIMUM_DURATION)
        progress_dialog.setValue(0)
        progress_dialog.show()
        QtWidgets.QApplication.processEvents()

        try:
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
        finally:
            progress_dialog.deleteLater()

        if has_flag:
            self._mark_adjusted()

        return True

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
        share_code_order = "'902', 'S10', 'S20', '003', '004'"

        # CaseType: 22 DiagFee = InsTotalFee 問診也要計算
        # (這個條件與 ins_apply_calculate._count_diag_count 及
        #  nhi_utils.get_case_type() 判定案別22 的口徑一致)
        #
        # ORDER BY 的 FIELD() 找不到時回傳 0, 升冪排序會排在最前面,
        # 原本會讓 S14/S24/K20/001/007/901/903/904/906 等未列出的代號
        # 全部插到 902 前面, 三歲兒童優先的用意反而失效。
        # 多加一個 `FIELD(...) = 0` 當第一排序鍵, 把未列出的推到最後
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
                ORDER BY
                    CaseType,
                    Field(ShareCode, {share_code_order}) = 0,
                    Field(ShareCode, {share_code_order}),
                    Sequence
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
            # PharmacyCode 若為 NULL 或長度不足, 原本的 pharmacy_code[i] 會
            # IndexError, 整個調整作業會中斷在這裡, 後面五支都不會執行
            pharmacy_code = string_utils.xstr(row["PharmacyCode"]).ljust(
                nhi_utils.MAX_COURSE, "0"
            )
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

            if nhi_utils.nurse_schedule_on_duty(self.database, case_key, doctor_name):
                continue

            if diag_code == "A01":
                diag_code = "A02"
            elif diag_code == "A03":
                diag_code = "A04"
            elif diag_code == "A05":
                diag_code = "A06"
            else:
                # 原本這裡不管醫令有沒有變都會呼叫一次 update_ins_apply_diag_fee
                # (SELECT + 重算 + UPDATE), 沒有護理人員版本的醫令根本不用動
                continue

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

    # 2026-09-03 優化排序版本，金額高的處置放在treat_section1，金額低的放在後面
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

            # 第一階段: 收集這位醫師所有應納入合理門診量的針傷件數
            # 篩選條件必須與 ins_apply_calculate._get_treat_count() 一致
            treat_list = []
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

                    treat_fee = number_utils.get_integer(row[f"TreatFee{course}"])
                    if treat_code == "" or treat_fee <= 0:
                        continue

                    treat_list.append(
                        {
                            "ins_apply_key": row["InsApplyKey"],
                            "course": course,
                            "treat_code": treat_code,
                            "treat_fee": treat_fee,
                        }
                    )

            # 第二階段: 點數高的排前面, 讓它們落在 treat_section1 全額給付
            # 被調整的件數不變, 但砍到的都是點數低的, 總損失最小
            # sort 為穩定排序, 點數相同者維持原本的 Sequence 順序
            # treat_list.sort(key=lambda item: item["treat_fee"], reverse=True)

            # 第一段優先放 9 碼(避免它們落到第二段被扣) 且點數高的
            # 第三段(歸零)放點數最低的
            treat_list.sort(
                key=lambda item: (
                    item["treat_code"]
                    not in nhi_utils.TREAT_DISCOUNT_CODE,  # 9 碼排前面
                    -item["treat_fee"],
                )
            )

            # 第三階段: 依序套用遞減分段
            treat_count = 0
            for item in treat_list:
                treat_count += 1
                treat_percent = 100

                if treat_count <= treat_section1:
                    pass
                elif treat_count <= treat_section2:
                    if item["treat_code"] in nhi_utils.TREAT_DISCOUNT_CODE:
                        treat_percent = 90
                elif treat_count <= treat_section3:
                    treat_percent = 0

                if treat_percent < 100:
                    charge_utils.update_treat_fee(
                        self.database,
                        item["ins_apply_key"],
                        item["course"],
                        treat_percent,
                    )

            # 對帳哨兵: 調整件數應等於分段計算的基準件數, 不一致代表兩邊篩選條件漂開了
            expected_count = number_utils.get_integer(ins_calculated_row["treat_count"])
            if treat_count != expected_count:
                print(
                    f"[合理門診量] {doctor_name} 調整件數 {treat_count} != 基準 {expected_count}"
                )

    # 計算針灸傷科給藥上限 (每位醫師平均 專任醫師數 * 150)
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
                # 其他各支都有檢查 CaseKey, 只有這裡沒有。
                # 療程殘留的 TreatCode (CaseKey 已經是 0) 會被算成一件,
                # 既灌水了件數, 超量之後還會把五折打在不存在的療程上
                if number_utils.get_integer(row[f"CaseKey{course}"]) <= 0:
                    continue

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

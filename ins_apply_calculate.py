# -*- coding: UTF-8 -*-
from PyQt5 import QtCore, QtWidgets

from libs import nhi_utils, number_utils, personnel_utils, string_utils

# 代碼清單改用 frozenset: list 的 in 是線性搜尋, 這裡每筆病歷每個療程都要比對
TREAT_ALL_CODE_SET = frozenset(nhi_utils.TREAT_ALL_CODE)
TREAT_DRUG_CODE_SET = frozenset(nhi_utils.TREAT_DRUG_CODE)
COMPLICATED_MASSAGE_CODE_SET = frozenset(nhi_utils.COMPLICATED_MASSAGE_CODE)
MODERATE_COMPLICATED_ACUPUNCTURE_SET = frozenset(
    nhi_utils.MODERATE_COMPLICATED_ACUPUNCTURE_CODE
)
HIGHLY_COMPLICATED_ACUPUNCTURE_SET = frozenset(
    nhi_utils.HIGHLY_COMPLICATED_ACUPUNCTURE_CODE
)
EXCLUDE_DIAG_ADJUST_SET = frozenset(nhi_utils.EXCLUDE_DIAG_ADJUST)

MAX_CASE_KEY = 15  # insapply 的 CaseKey1 ~ CaseKey15
CHUNK_SIZE = 500  # 批次查詢時每一句 IN (...) 的 CaseKey 數量

# 進度對話盒延遲顯示的毫秒數
# Qt 預設 4000: 估計作業不到 4 秒就整個不顯示, 看起來像沒反應
# 0 = 一定顯示; 不想讓小資料量閃一下的話改成 500
PROGRESS_MINIMUM_DURATION = 0


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

        self._insapply_rows = []  # 本次申報的 insapply 全部資料 (一次撈回)
        self._case_doctor = {}  # {CaseKey: 去掉逗號的 cases.Doctor}

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
        # 0. 一次把需要的資料全部撈回來 (取代原本每位醫師 × 每個方法各查一次)
        self._prefetch()

        # 1. 收集全體醫師基礎資料
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

    # ==================================================================
    # SQL 語意對齊小工具
    # SQL 的 NULL 比對一律回傳 NULL (等同不符合), Python 的 == 不是,
    # 這幾支是為了讓 Python 端的判斷跟原本的 SQL 完全一致
    # ==================================================================
    @staticmethod
    def _sql_eq(value, target):
        return value is not None and value == target

    @staticmethod
    def _sql_in(value, values):
        return value is not None and value in values

    @staticmethod
    def _sql_not_in(value, values):
        return value is not None and value not in values

    # ==================================================================
    # 批次預取
    # ==================================================================
    @staticmethod
    def _chunks(key_list, size=CHUNK_SIZE):
        for i in range(0, len(key_list), size):
            yield key_list[i : i + size]

    def _prefetch(self):
        case_key_fields = ",\n                ".join(
            [f"CaseKey{i}" for i in range(1, MAX_CASE_KEY + 1)]
        )
        treat_code_fields = ",\n                ".join(
            [f"TreatCode{i}" for i in range(1, nhi_utils.MAX_COURSE + 1)]
        )

        # 原本這句 (或它的變形) 會被六個方法 × 每位醫師各跑一次, 這裡只跑一次。
        # 統一加上 CaseDate BETWEEN, 跟 _set_doctor_table / _get_diag_days 的
        # 母體一致 (原本只有那兩支有這個條件)
        sql = f'''
            SELECT
                InsApplyKey, DoctorName, DoctorID, CaseType, CaseDate, PatientKey,
                DiagFee, InsTotalFee, InsApplyFee, PresDays, SpecialCode1,
                {case_key_fields},
                {treat_code_fields}
            FROM insapply
            WHERE
                ApplyDate = "{self.apply_date}" AND
                ApplyType = "{self.apply_type_code}" AND
                ApplyPeriod = "{self.period}" AND
                ClinicID = "{self.clinic_id}" AND
                CaseDate BETWEEN "{self.start_date}" AND "{self.end_date}"
            ORDER BY InsApplyKey
        '''
        self._insapply_rows = self.database.select_record(sql)

        case_keys = set()
        for row in self._insapply_rows:
            for i in range(1, MAX_CASE_KEY + 1):
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key > 0:
                    case_keys.add(case_key)

        self._load_case_doctor(sorted(case_keys))

    def _load_case_doctor(self, case_keys):
        """一次建立 {CaseKey: 醫師姓名} 對照表.

        取代原本 `_get_doctor_name()` 每個 CaseKey 各查一次 cases 的做法。
        """
        self._case_doctor = {}
        for chunk in self._chunks(case_keys):
            in_list = ",".join([str(key) for key in chunk])
            sql = f"""
                SELECT CaseKey, Doctor FROM cases
                WHERE CaseKey IN ({in_list})
            """
            for row in self.database.select_record(sql):
                key = number_utils.get_integer(row["CaseKey"])
                self._case_doctor[key] = string_utils.xstr(row["Doctor"]).replace(
                    ",", ""
                )

    def _get_doctor_name(self, case_key):
        return self._case_doctor.get(number_utils.get_integer(case_key))

    # ==================================================================
    # 醫師清單與各項計數
    # ==================================================================
    @staticmethod
    def _new_doctor_data(doctor_name, doctor_id):
        return {
            "doctor_type": None,
            "doctor_name": doctor_name,
            "doctor_id": doctor_id,
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

    def _set_doctor_table(self):
        # 等同原本的 GROUP BY DoctorName (含 exclude_script);
        # DoctorID 取同一位醫師第一筆 (依 InsApplyKey), 原本是未定義的任意一筆
        doctor_table = {}
        for row in self._insapply_rows:
            if not self._sql_not_in(row["CaseType"], ("C5",)):
                continue

            doctor_name = row["DoctorName"]
            if doctor_name in doctor_table:
                continue

            doctor_table[doctor_name] = self._new_doctor_data(
                doctor_name, row["DoctorID"]
            )

        if len(doctor_table) <= 0:
            self.ins_calculated_table = []
            return

        for doctor_data in doctor_table.values():
            doctor_data["doctor_type"] = personnel_utils.get_person_field_value(
                self.database, doctor_data["doctor_name"], "Position"
            )

        progress_dialog = QtWidgets.QProgressDialog(
            "正在統計各醫師的申報資料中, 請稍後...", "取消", 0, 6, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        progress_dialog.setMinimumDuration(PROGRESS_MINIMUM_DURATION)
        progress_dialog.setValue(0)
        progress_dialog.show()
        QtWidgets.QApplication.processEvents()

        try:
            self._count_diag_days(doctor_table)
            progress_dialog.setValue(1)

            self._count_by_doctor_name(doctor_table)
            progress_dialog.setValue(2)

            self._count_diag_count(doctor_table)
            progress_dialog.setValue(3)

            self._count_by_case_key(doctor_table)
            progress_dialog.setValue(4)

            self._count_infectious(doctor_table)
            progress_dialog.setValue(5)

            for doctor_data in doctor_table.values():
                # 針傷給藥件數另有規定, 要從針傷件數扣掉。
                # 原本寫成 `if treat_count - treat_drug > 0:` , 兩者相等時
                # 條件為假, treat_count 會原封不動留著 (應該要變成 0)
                doctor_data["treat_count"] = max(
                    0, doctor_data["treat_count"] - doctor_data["treat_drug"]
                )
                doctor_data["total_drug"] = (
                    doctor_data["internal_drug"] + doctor_data["treat_drug"]
                )

            progress_dialog.setValue(6)
        finally:
            progress_dialog.deleteLater()

        # 依醫師姓名排序, 讓每次執行的順序固定
        # (支援醫師的先後會決定誰先領到大水庫的名額)
        self.ins_calculated_table = [
            doctor_table[key]
            for key in sorted(doctor_table, key=lambda x: string_utils.xstr(x))
        ]

    def _count_diag_days(self, doctor_table):
        """看診日數: exclude_script AND (DiagFee > 0 OR SpecialCode1 = "EC")"""
        diag_dates = {name: set() for name in doctor_table}

        for row in self._insapply_rows:
            if not self._sql_not_in(row["CaseType"], ("C5",)):
                continue

            doctor_name = row["DoctorName"]
            if doctor_name not in diag_dates:
                continue

            if not (
                number_utils.get_integer(row["DiagFee"]) > 0
                or self._sql_eq(row["SpecialCode1"], "EC")
            ):
                continue

            case_date = row["CaseDate"]
            if case_date is None:
                continue

            try:
                diag_dates[doctor_name].add(case_date.date())
            except AttributeError:
                diag_dates[doctor_name].add(string_utils.xstr(case_date)[:10])

        for doctor_name, dates in diag_dates.items():
            doctor_table[doctor_name]["diag_days"] = min(
                len(dates), nhi_utils.MAX_DIAG_DAYS
            )

    def _count_by_doctor_name(self, doctor_table):
        """直接以 insapply.DoctorName 判定歸屬的計數"""
        for row in self._insapply_rows:
            doctor_name = row["DoctorName"]
            doctor_data = doctor_table.get(doctor_name)
            if doctor_data is None:
                continue

            case_type = row["CaseType"]
            diag_fee = number_utils.get_integer(row["DiagFee"])

            # 總診察件數: exclude_script AND DiagFee > 0
            if self._sql_not_in(case_type, ("C5",)) and diag_fee > 0:
                doctor_data["total_diag_count"] += 1

            # 內科給藥件數: CaseType IN ("21", "24") AND PresDays > 0
            if (
                self._sql_in(case_type, ("21", "24"))
                and number_utils.get_integer(row["PresDays"]) > 0
            ):
                doctor_data["internal_drug"] += 1

    def _count_diag_count(self, doctor_table):
        """合理門診量的診察件數 (原本是三句 SQL 加加減減)"""
        for row in self._insapply_rows:
            doctor_data = doctor_table.get(row["DoctorName"])
            if doctor_data is None:
                continue

            if number_utils.get_integer(row["DiagFee"]) <= 0:
                continue

            case_type = row["CaseType"]
            in_adjust_range = self._sql_not_in(case_type, EXCLUDE_DIAG_ADJUST_SET)

            if in_adjust_range:
                doctor_data["diag_count"] += 1

            # 矯正機關內門診/戒護就醫不計入。
            # 原本這一句沒有 CaseType 條件, 會把「沒被加進去」的案別也扣掉;
            # 這裡補上與上一段相同的範圍限制
            if in_adjust_range and self._sql_in(row["SpecialCode1"], ("JA", "JB")):
                doctor_data["diag_count"] -= 1

            # 案別22 的問診要加回來。
            # 「問診」的定義是 DiagFee = InsTotalFee (整筆只有診察費),
            # 與 nhi_utils.get_case_type() 判定案別22 及
            # ins_apply_adjust_fee._get_ins_apply_rows() 的條件一致。
            # 原本寫的是 InsApplyFee <= DiagFee, 那是比較寬的條件,
            # 會把「有處置但部分負擔夠大」的病歷也算進來, 與 adjust 端的
            # 母體對不起來
            if (
                self._sql_eq(case_type, "22")
                and row["InsTotalFee"] is not None
                and number_utils.get_integer(row["DiagFee"])
                == number_utils.get_integer(row["InsTotalFee"])
            ):
                doctor_data["diag_count"] += 1

    def _count_by_case_key(self, doctor_table):
        """需要回查 cases.Doctor 才能判定歸屬的計數.

        原本這五種計數各自跑一次 insapply 查詢, 而且每位醫師都重跑一次,
        內層再對每個 CaseKey 查一次 cases。這裡改成走訪一次算完所有醫師。
        """
        for row in self._insapply_rows:
            case_type = row["CaseType"]

            count_total = self._sql_not_in(case_type, ("C5",))
            count_treat = self._sql_in(case_type, ("29",))
            count_complicated = self._sql_in(case_type, ("29", "C5"))

            if not (count_total or count_treat or count_complicated):
                continue

            for i in range(1, MAX_CASE_KEY + 1):
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue

                doctor_name = self._case_doctor.get(case_key)
                if doctor_name is None:
                    continue

                doctor_data = doctor_table.get(doctor_name)
                if doctor_data is None:
                    continue

                # 總件數: 不分案別 (C5 除外), CaseKey1~15
                if count_total:
                    doctor_data["total_count"] += 1

                if i > nhi_utils.MAX_COURSE:  # 針傷處置只看療程 1~6
                    continue

                treat_code = string_utils.xstr(row[f"TreatCode{i}"])

                if count_treat:
                    if treat_code in TREAT_ALL_CODE_SET:
                        doctor_data["treat_count"] += 1
                    if treat_code in TREAT_DRUG_CODE_SET:
                        doctor_data["treat_drug"] += 1

                if count_complicated:
                    if treat_code in COMPLICATED_MASSAGE_CODE_SET:
                        doctor_data["complicated_massage"] += 1
                    if treat_code in MODERATE_COMPLICATED_ACUPUNCTURE_SET:
                        doctor_data["moderate_complicated_acupuncture"] += 1
                    if treat_code in HIGHLY_COMPLICATED_ACUPUNCTURE_SET:
                        doctor_data["highly_complicated_acupuncture"] += 1

    def _count_infectious(self, doctor_table):
        """法定傳染病通報隔離件數: 同一病人同一天只算一次"""
        first_row = {}  # {(PatientKey, 日期): row}
        for row in self._insapply_rows:
            if not self._sql_in(row["CaseType"], ("C5",)):
                continue

            case_date = row["CaseDate"]
            try:
                day = case_date.date()
            except AttributeError:
                day = string_utils.xstr(case_date)[:10]

            key = (row["PatientKey"], day)
            if key not in first_row:  # 原本靠 GROUP BY, 取到哪一筆是未定義的
                first_row[key] = row

        for row in first_row.values():
            for i in range(1, nhi_utils.MAX_COURSE + 1):
                case_key = number_utils.get_integer(row[f"CaseKey{i}"])
                if case_key <= 0:
                    continue

                doctor_name = self._case_doctor.get(case_key)
                doctor_data = doctor_table.get(doctor_name)
                if doctor_data is None:
                    continue

                doctor_data["infectious_count"] += 1

    # ==================================================================
    # 分段計算
    # ==================================================================
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

            # 所有針傷級距天數一律卡死最高 26 天
            calc_days = min(row["diag_days"], nhi_utils.MAX_DIAG_DAYS)

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
                row["treat_section1"],
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
        treat_section1_limit = max(
            0, (diag_days * nhi_utils.TREAT_SECTION1) - treat_drug
        )
        treat_section1 = min(treat_count, treat_section1_limit)

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

    # ==================================================================
    # 支援醫師的大水庫推填遞補
    # ==================================================================
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
            # 原本是 `if doctor_type == "支援醫師": continue`, 與推填端的
            # `if doctor_type == "醫師": continue` 不互補——Position 查不到而
            # 變成 "" 的醫師會同時被當成專任(貢獻額度)與支援(領取額度)
            if ins_calculated_row["doctor_type"] != "醫師":
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
            # 同 _get_full_time_doctor_diag_balance 的說明: 與推填端互補
            if ins_calculated_row["doctor_type"] != "醫師":
                continue

            diag_days = min(ins_calculated_row["diag_days"], nhi_utils.MAX_DIAG_DAYS)
            treat_drug = ins_calculated_row["treat_drug"]

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

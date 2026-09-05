# -*- coding: UTF-8 -*-

import re

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

# 進度對話盒最多更新幾次
PROGRESS_UPDATES = 100

# 進度對話盒延遲顯示的毫秒數 (Qt 預設 4000, 會讓人以為當掉了)
PROGRESS_MINIMUM_DURATION = 0

# IN (...) 一次帶幾個 CaseKey
CHUNK_SIZE = 500


# 以下四個樣式用來把「一次查一筆」的 SQL 轉接到整批預取的結果。
# 比對的是把空白壓成單一空格後的 SQL；比對不到就退回正常查詢，
# 所以就算 libs 裡的 SQL 改寫過，也只會失去加速，不會算錯。
_DOSAGE_SQL = re.compile(
    r"^SELECT .+ FROM dosage WHERE CaseKey = (\d+) AND MedicineSet = 1"
    r"(?: LIMIT 1)?$"
)
_CASE_SQL = re.compile(r"^SELECT .+ FROM cases WHERE CaseKey = (\d+)$")
_PRESCRIPT_SQL = re.compile(
    r"^SELECT .+ FROM prescript WHERE CaseKey = (\d+) AND MedicineSet = 1$"
)
_CASEEXTEND_SQL = re.compile(
    r'^SELECT .+ FROM caseextend WHERE CaseKey = (\d+) AND ExtendType = "([^"]*)"$'
)


class ReadCache:
    """產生申報檔期間的唯讀查詢快取。

    產生申報檔的過程只會寫 insapply，cases / dosage / prescript /
    caseextend / charge_settings / person / icd10 / patient_new_care
    從頭到尾都不會被改動，所以同一句 SQL 的結果一定相同。

    * 只要 SQL 裡出現 insapply 就一律不快取，直接下到資料庫。
    * 另外把「一次查一筆」的 dosage / cases / prescript / caseextend
      轉接到整批預取的結果，連查詢都不用下。
    """

    def __init__(self, database):
        object.__setattr__(self, "_database", database)
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_dosage", {})
        object.__setattr__(self, "_case", {})
        object.__setattr__(self, "_prescript", {})
        object.__setattr__(self, "_caseextend", {})
        object.__setattr__(self, "_prefetched", set())
        object.__setattr__(
            self, "stats", {"prefetch": 0, "hit": 0, "miss": 0, "insapply": 0}
        )

    def __getattr__(self, name):
        # insert_record / update_record / exec_sql ... 一律直接轉給原本的物件
        return getattr(object.__getattribute__(self, "_database"), name)

    # ------------------------------------------------------------------
    @staticmethod
    def _rows_copy(rows):
        return [dict(row) for row in rows]

    def _chunks(self, values):
        values = sorted(values)
        for i in range(0, len(values), CHUNK_SIZE):
            yield values[i : i + CHUNK_SIZE]

    def prefetch(self, case_keys):
        """把整個月會用到的 dosage / cases / prescript / caseextend 一次撈回來."""
        database = object.__getattribute__(self, "_database")
        prefetched = object.__getattribute__(self, "_prefetched")

        keys = {
            number_utils.get_integer(case_key)
            for case_key in case_keys
            if number_utils.get_integer(case_key) > 0
        }
        if not keys:
            return

        prefetched.update(keys)

        for chunk in self._chunks(keys):
            in_list = ", ".join(str(key) for key in chunk)

            for row in database.select_record(
                f"SELECT * FROM dosage WHERE MedicineSet = 1 AND CaseKey IN ({in_list})"
            ):
                self._dosage.setdefault(
                    number_utils.get_integer(row["CaseKey"]), []
                ).append(row)

            for row in database.select_record(
                f"SELECT * FROM cases WHERE CaseKey IN ({in_list})"
            ):
                self._case.setdefault(
                    number_utils.get_integer(row["CaseKey"]), []
                ).append(row)

            for row in database.select_record(
                f"SELECT * FROM prescript "
                f"WHERE MedicineSet = 1 AND CaseKey IN ({in_list})"
            ):
                self._prescript.setdefault(
                    number_utils.get_integer(row["CaseKey"]), []
                ).append(row)

            for row in database.select_record(
                f"SELECT * FROM caseextend WHERE CaseKey IN ({in_list})"
            ):
                self._caseextend.setdefault(
                    (
                        number_utils.get_integer(row["CaseKey"]),
                        string_utils.xstr(row["ExtendType"]),
                    ),
                    [],
                ).append(row)

    # ------------------------------------------------------------------
    def _from_prefetch(self, sql):
        """比對得到就回傳整批預取的結果, 否則回傳 None 讓它走正常查詢."""
        prefetched = object.__getattribute__(self, "_prefetched")
        if not prefetched:
            return None

        matched = _DOSAGE_SQL.match(sql)
        if matched:
            case_key = int(matched.group(1))
            if case_key in prefetched:
                return self._dosage.get(case_key, [])
            return None

        matched = _CASE_SQL.match(sql)
        if matched:
            case_key = int(matched.group(1))
            if case_key in prefetched:
                return self._case.get(case_key, [])
            return None

        matched = _PRESCRIPT_SQL.match(sql)
        if matched:
            case_key = int(matched.group(1))
            if case_key in prefetched:
                return self._prescript.get(case_key, [])
            return None

        matched = _CASEEXTEND_SQL.match(sql)
        if matched:
            case_key = int(matched.group(1))
            if case_key in prefetched:
                return self._caseextend.get((case_key, matched.group(2)), [])
            return None

        return None

    def select_record(self, sql, params=None, dictionary=True):
        database = object.__getattribute__(self, "_database")
        cache = object.__getattribute__(self, "_cache")
        stats = object.__getattribute__(self, "stats")

        if not dictionary:
            # 回傳 tuple 的查詢不快取 (本模組不會用到)
            stats["insapply"] += 1
            return database.select_record(sql, params, dictionary)

        key = " ".join(sql.split())
        if params:
            key = f"{key} @@ {params!r}"

        # insapply 在產生過程中會被寫入, 絕對不能快取
        if "insapply" in key:
            stats["insapply"] += 1
            return database.select_record(sql, params)

        rows = None if params else self._from_prefetch(key)
        if rows is not None:
            stats["prefetch"] += 1
            return self._rows_copy(rows)

        if key in cache:
            stats["hit"] += 1
            return self._rows_copy(cache[key])

        stats["miss"] += 1
        rows = database.select_record(sql, params)
        cache[key] = rows

        return self._rows_copy(rows)


class SettingsCache:
    """system_settings.field() 每叫一次就查一次資料庫, 產生過程中設定不會變."""

    def __init__(self, system_settings):
        object.__setattr__(self, "_settings", system_settings)
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_settings"), name)

    def field(self, name):
        cache = object.__getattribute__(self, "_cache")
        if name not in cache:
            cache[name] = object.__getattribute__(self, "_settings").field(name)
        return cache[name]


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
        # 本次產生過程中已寫入的 insapply 索引 (用來取代合併病歷的搜尋查詢)
        self._ins_apply_index = []
        self._use_ins_apply_index = True
        self._transaction_started = False
        self._canceled = False
        self.cache_stats = None
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
        # 產生期間把 database / system_settings 換成有快取的版本。
        # 只有 insapply 會被寫, 其他表格不會動, 所以同一句 SQL 的結果必定相同。
        database = self.database
        system_settings = self.system_settings
        cached_database = ReadCache(database)

        # 整個產生過程包成一個交易。
        # mysql_database 的 autocommit 是開著的, 每一次 insert_record 都會
        # 自己 commit 一次 (InnoDB 就是一次 fsync); 而它的 _tx_depth 設計成
        # 「在明確交易中時 insert/update/exec_sql 不自行提交」, 所以只要在
        # 外面開一個交易, 幾千次提交就會縮成一次。
        # 順帶的好處: 中途失敗不會留下寫到一半的申報檔 (MyISAM 沒有這個
        # 保護, 資料庫類別會自己印警告)。
        self._transaction_started = self._begin_generate_transaction(database)
        self._canceled = False

        self.database = cached_database
        self.system_settings = SettingsCache(system_settings)
        self._ins_apply_index = []
        self._use_ins_apply_index = True

        try:
            self._delete_existing_data()
            rows = self._get_medical_records()
            cached_database.prefetch([row["CaseKey"] for row in rows])
            self._create_ins_records(rows)
        except Exception:
            self._rollback_generate_transaction(database)
            raise
        else:
            if self._canceled:
                # 按了取消: 整批退回, 不要留下產到一半的申報檔
                self._rollback_generate_transaction(database)
            elif self._transaction_started:
                database.commit()
                self._transaction_started = False
        finally:
            self.cache_stats = cached_database.stats
            self.database = database
            self.system_settings = system_settings

    def _begin_generate_transaction(self, database):
        """開啟交易; 資料庫類別不支援時回傳 False, 行為就跟以前一樣。"""
        begin_transaction = getattr(database, "begin_transaction", None)
        if begin_transaction is None:
            return False

        try:
            begin_transaction()
        except Exception as error:
            print(f"（無法開啟交易，改為逐筆提交：{error}）")
            return False

        return True

    def _rollback_generate_transaction(self, database):
        if not self._transaction_started:
            return

        self._transaction_started = False
        rollback = getattr(database, "rollback", None)
        if rollback is None:
            return

        try:
            rollback()
        except Exception as error:
            print(f"（回復交易失敗：{error}）")

    def _delete_existing_data(self):
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]
        sql = f"""
            DELETE FROM insapply
            WHERE
                (ClinicID = "{self.clinic_id}") AND
                (ApplyDate = "{self.apply_date}") AND
                (ApplyPeriod = "{self.period}") AND
                (ApplyType = "{apply_type}")
        """
        self.database.exec_sql(sql)

    def _get_medical_records(self):
        start_date = self.start_date.toString("yyyy-MM-dd 00:00:00")
        end_date = self.end_date.toString("yyyy-MM-dd 23:59:59")
        apply_type_sql = nhi_utils.get_apply_type_sql(
            self.apply_type
        )  # 只取得申報類別為申報或補報的資料,不申報不讀取
        sql = f"""
            SELECT
                cases.*, patient.Birthday, patient.ID
            FROM cases
                LEFT JOIN patient ON patient.PatientKey = cases.PatientKey
            WHERE
                (CaseDate BETWEEN "{start_date}" AND "{end_date}") AND
                (cases.InsType = "健保") AND
                ({apply_type_sql})
            ORDER BY CaseDate
        """
        rows = self.database.select_record(sql)
        return rows

    def _create_ins_records(self, rows):
        record_count = len(rows)
        progress_dialog = QtWidgets.QProgressDialog(
            "正在產生申報檔中, 請稍後...", "取消", 0, record_count, self
        )
        progress_dialog.setWindowModality(QtCore.Qt.WindowModal)
        # Qt 預設 minimumDuration 是 4000ms, 速度變快後對話盒會整個不出現
        progress_dialog.setMinimumDuration(PROGRESS_MINIMUM_DURATION)
        progress_dialog.setValue(0)
        progress_dialog.show()
        QtWidgets.QApplication.processEvents()
        progress_step = max(1, record_count // PROGRESS_UPDATES)

        try:
            for row_no, row in enumerate(rows):
                if row_no % progress_step == 0:
                    progress_dialog.setValue(row_no)
                    if progress_dialog.wasCanceled():
                        self._canceled = True
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
        finally:
            progress_dialog.deleteLater()

    # -----------------------------------------------------------------------
    # 本次產生的 insapply 索引
    #
    # _delete_existing_data 已經把這個 (院所, 申報年月, 期別, 申報類別) 的
    # 資料全部刪掉, 而三個 _need_merge_* 的 WHERE 也剛好就是這四個條件,
    # 所以它們能找到的每一筆, 都一定是本次產生時自己寫進去的。
    # 用索引先找出 InsApplyKey, 再用主鍵撈那一筆, 就不必每次都掃整張表。
    # -----------------------------------------------------------------------
    def _add_ins_apply_index(self, ins_apply_key, fields, data):
        if not self._use_ins_apply_index:
            return

        ins_apply_key = number_utils.get_integer(ins_apply_key)
        if ins_apply_key <= 0:
            # 拿不到主鍵就整個關掉, 退回原本的搜尋查詢
            self._use_ins_apply_index = False
            self._ins_apply_index = []
            return

        row = dict(zip(fields, data))
        self._ins_apply_index.append(
            {
                "InsApplyKey": ins_apply_key,
                # 保留原值: SQL 的 = 比對碰到 NULL 一律不成立,
                # 用 xstr() 轉成空字串會讓 NULL 誤配到 ""
                "PatientKey": row.get("PatientKey"),
                "CaseType": row.get("CaseType"),
                "Card": row.get("Card"),
                "TreatCode": {
                    i: row.get(f"TreatCode{i}")
                    for i in range(1, nhi_utils.MAX_HOME_CARE + 1)
                },
            }
        )

    def _update_ins_apply_index(self, ins_apply_key, fields, data):
        if not self._use_ins_apply_index:
            return

        ins_apply_key = number_utils.get_integer(ins_apply_key)
        row = dict(zip(fields, data))
        for entry in self._ins_apply_index:
            if entry["InsApplyKey"] != ins_apply_key:
                continue
            for i in range(1, nhi_utils.MAX_HOME_CARE + 1):
                field = f"TreatCode{i}"
                if field in row:
                    entry["TreatCode"][i] = row[field]
            break

    def _get_ins_apply_row(self, ins_apply_key):
        sql = f"""
            SELECT * FROM insapply
            WHERE
                InsApplyKey = {ins_apply_key}
        """
        rows = self.database.select_record(sql)
        if len(rows) <= 0:
            return None
        return rows[0]

    # 檢查是否需要合併病歷 (腦血管疾病案件)
    def _need_merge_brain_record(self, row):
        ins_apply_row = None
        patient_key = number_utils.get_integer(row["PatientKey"])
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]
        if self._use_ins_apply_index:
            return self._find_merge_record_by_case_type(patient_key, "30")
        sql = f"""
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                CaseType = "30"
        """
        ins_apply_rows = self.database.select_record(sql)
        if len(ins_apply_rows) > 0:
            ins_apply_row = ins_apply_rows[0]
        return ins_apply_row

    # 檢查是否需要合併病歷 (居家醫療案件)
    def _need_merge_home_care_record(self, row):
        ins_apply_row = None
        patient_key = number_utils.get_integer(row["PatientKey"])
        apply_type = nhi_utils.APPLY_TYPE_DICT[self.apply_type]
        if self._use_ins_apply_index:
            return self._find_merge_record_by_case_type(patient_key, "31")
        sql = f"""
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                CaseType = "31"
        """
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
        if self._use_ins_apply_index:
            return self._find_merge_record_by_course(
                patient_key, card, number_utils.get_integer(course)
            )
        # 找出同卡序且有執行療程首次的病歷
        sql = f"""
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
        """
        ins_apply_rows = self.database.select_record(sql)
        if len(ins_apply_rows) <= 0:  # 首次不在本月
            sql = f"""
            SELECT * FROM insapply
            WHERE
                ClinicID = "{self.clinic_id}" AND
                ApplyDate = "{self.apply_date}" AND
                ApplyPeriod = "{self.period}" AND
                ApplyType = "{apply_type}" AND
                PatientKey = {patient_key} AND
                Card = "{card}" AND
                TreatCode{course} IS NULL
            """
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
            if case_type == "24" and pres_days > 30:  # 2024.05.18 慢性病連續處方箋
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
        ins_apply_key = self.database.insert_record("insapply", fields, data)
        self._add_ins_apply_index(ins_apply_key, fields, data)
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
        self._update_ins_apply_index(ins_apply_key, fields, data)

    @staticmethod
    def _sql_eq(stored, wanted):
        """重現 SQL 的 = : 欄位是 NULL 時一律不成立。

        字串比對時去掉尾端空白, 與 MySQL 非二進位定序的行為一致。
        """
        if stored is None:
            return False

        if isinstance(stored, str) or isinstance(wanted, str):
            return (
                string_utils.xstr(stored).rstrip() == string_utils.xstr(wanted).rstrip()
            )

        return stored == wanted

    def _find_merge_record_by_case_type(self, patient_key, case_type):
        for entry in self._ins_apply_index:
            if self._sql_eq(entry["PatientKey"], patient_key) and self._sql_eq(
                entry["CaseType"], case_type
            ):
                return self._get_ins_apply_row(entry["InsApplyKey"])
        return None

    def _match_patient_card(self, entry, patient_key, card):
        return self._sql_eq(entry["PatientKey"], patient_key) and self._sql_eq(
            entry["Card"], card
        )

    def _find_merge_record_by_course(self, patient_key, card, course):
        # 第一輪: 有執行療程首次 (TreatCode1 有值) 且本次的療程欄位還是空的
        for entry in self._ins_apply_index:
            if not self._match_patient_card(entry, patient_key, card):
                continue
            if entry["TreatCode"].get(1) is None:
                continue
            if entry["TreatCode"].get(course) is None:
                return self._get_ins_apply_row(entry["InsApplyKey"])

        # 第二輪: 療程首次不在本月
        for entry in self._ins_apply_index:
            if not self._match_patient_card(entry, patient_key, card):
                continue
            if entry["TreatCode"].get(course) is None:
                return self._get_ins_apply_row(entry["InsApplyKey"])

        return None

    def _get_sequence(self, case_type):
        self.sequence[case_type] += 1
        return self.sequence[case_type]
